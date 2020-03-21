import os
import tempfile
import csv
import logging
import shutil

import arcpy

from PISCES import local_vars
from PISCES.tbx_make_matrix import make_matrix
from PISCES import script_tool_funcs
from PISCES import api
from PISCES import api_tools

log = logging.getLogger("PISCES.tools.clustering")

class Env(object):
	def __init__(self, env, value):
		self.env = env
		self.orig_value = arcpy.env.__getitem__(env)
		self.new_value = value

	def __enter__(self, *args, **kwargs):
		arcpy.env.__setitem__(self.env, self.new_value)

	def __exit__(self, *args, **kwargs):
		arcpy.env.__setitem__(self.env, self.orig_value)


def _check_output_location(output_path):
	if arcpy.Exists(output_path):
		raise ValueError("Output path {} already exists - please specify a unique output path".format(output_path))

	folder_gdb_name = os.path.split(output_path)[0]
	if not arcpy.Exists(folder_gdb_name):
		raise ValueError("Folder or geodatabase in output path {} does not exist - please specify an existing geodatabase or folder for output. If placing in a folder, make sure to use the appropriate output extension (such as .shp), but putting the result in a geodatabase is recommended".format(output_path))


def make_species_clusters(output_path, group_name="Flow_Sensitive", presence_values="1,3,9", min_species=2, num_groups=(2, 3, 4, 5, 6, 7, 8, 9), huc_regions=None, region_group_field=None, zones_field="huc_12_string", region_group_join_field="huc_12_double", aggregation=None, spatial_constraint="NO_SPATIAL_CONSTRAINT", initialization_method="FIND_SEED_LOCATIONS", report_folder=None):
	"""
		Currently won't work when not passing in a region because we need a field that's a double
	:param group_name:
	:param presence_values:
	:param min_species:
	:param num_groups:
	:param huc_regions:  Input HUC_12 layer - used even if you don't want to split by regions (in that case, set region_group_field to None). Will be split by region field if provided, otherwise uses as is
	:param region_group_field:
	:param zones_field:  The original key field for huc 12s - in this case, a string field
	:param region_group_join_field:  this one may be different than zones field because what comes out of loading the species matrix may be a different format
	:param aggregation: refers to what level of species aggregation should be used (according to make_matrix's documentation. None means keep data at taxon level. "species" aggregates subspecies up to species, "genus" aggregates all to genus, and "family" aggregates all to family
	:param spatial_constraint: passed straight into ArcGIS's Grouping Analysis tool
	:param initialization_method: passed straight into ArcGIS's Grouping Analysis tool
	:param report_folder: folder used when clustering reports are dumped by ArcGIS, but also for cluster assemblage tables
	:return:
	"""

	# Originally had a value check for multiple parameters, but I think these fields are unrelated, so cancelling this check, but not removing it yet
	#if (region_group_field or region_group_join_field) and not (region_group_field and region_group_field):
	#	raise ValueError("Parameters region_group_field, and region_group_join_field must all be supplied if one is supplied. Cannot continue")

	_check_output_location(output_path=output_path)

	working_folder = tempfile.mkdtemp(prefix="PISCES_matrix")
	log.info("Working from {}".format(working_folder))

	gdb_name = "region_cluster_data.gdb"
	working_gdb_path = os.path.join(working_folder, gdb_name)
	arcpy.CreateFileGDB_management(working_folder, gdb_name)

	try:
		# first pull the species data
		csv_name = "clustering_matrix"
		matrix_info = make_matrix(group_name, working_folder,
								  presence_types=presence_values,
								  true_value=1,
								  false_value=0,
								  qc_flag=True,  # local_vars.hq_collections gets used
								  use_scientific_name=False,
								  aggregation=aggregation,
								  out_name=csv_name)

		# matrix_info has key_field and species_fields attributes we can use later
		csv_path = matrix_info["output_path"]

		if min_species != 0:
			huc_counts = api.counts.count_species_in_group_by_huc(group_name, presence_values)
		else:
			huc_counts = (None,)

		hucs_with_species_data = join_matrix_to_hucs(csv_path, huc_regions, region_group_join_field, working_gdb_path, min_species, huc_counts, matrix_info)

		if region_group_field:
			full_paths = _split_regions(hucs_with_species_data, region_group_field, working_folder)
		else:
			full_paths = (hucs_with_species_data,)  # just make a tuple out of the input path if we don't have a region field

		with Env("workspace", working_gdb_path):
			for region in full_paths:
				_make_species_clusters_for_region(region, num_groups, matrix_info,
												  spatial_constraint=spatial_constraint,
												  initialization_method=initialization_method,
												  report_folder=report_folder,
												  zone_field=zones_field,
												  species_group=group_name,
												  presence_types=presence_values,
												  aggregation=aggregation,
												  collections=local_vars.hq_collections,
												  )

			if region_group_field:
				arcpy.Merge_management(full_paths, output=output_path)
			else:
				arcpy.CopyFeatures_management(hucs_with_species_data, output_path)  # if we don't have regions, just copy hucs to output path

		species_assemblage_dumps = ["common_name"]  # we'll always dump a common name assemblage field
		if aggregation != "common_name":
			species_assemblage_dumps.append(aggregation)  # but we'll also dump the assemblage at whatever the aggregation level is too

		# attach assemblage field(s) - at least one for common name, and another for aggregation type if that's different.
		for listing_type in species_assemblage_dumps:
			api_tools.join_assemblage_as_field(output_path,  # add the assemblage field to each HUC
										   species_or_group=group_name,
										   key_field=zones_field,
										   taxonomic_aggregation_level=listing_type,
										   presence_types=presence_values,
										   collections=local_vars.hq_collections)

	finally:
		pass
		# delete the working folder since it'll get big
		# shutil.rmtree(working_folder)


def join_matrix_to_hucs(csv_path, huc_regions, region_group_join_field, working_gdb_path, min_species, huc_counts, matrix_info):
	with Env("workspace", working_gdb_path):
		new_table_name = "converted_matrix"
		new_table_path = os.path.join(working_gdb_path, new_table_name)
		arcpy.TableToTable_conversion(csv_path, working_gdb_path, new_table_name)

		if huc_regions:
			hucs = huc_regions
		else:
			hucs = local_vars.HUCS

		# copy it so we can make changes
		working_output_features = "working_species_data"
		arcpy.CopyFeatures_management(hucs, working_output_features)  # in the working_gdb_path

		# make it a layer so we can join
		hucs_layer = "hucs_layer"
		arcpy.MakeFeatureLayer_management(working_output_features, hucs_layer)
		try:
			new_fields = []
			for species_name in matrix_info["species_fields"]:
				new_fields.append(make_safe(species_name))  # make underscore versions to use for joining
			arcpy.JoinField_management(hucs_layer, region_group_join_field, new_table_path, matrix_info["key_field"], new_fields)  # in place join
			# arcpy.AddJoin_management(hucs_layer, region_group_join_field, new_table_path, "HUC_12")  # join the data

			if min_species > 0:
				# writing it out to a CSV and loading a table is the easiest way to get consistent results with the other table
				attach_and_filter_counts(huc_counts, min_species, hucs_layer, region_group_join_field)

			output_features = "species_data"
			output_path = os.path.join(working_gdb_path, output_features)
			arcpy.CopyFeatures_management(hucs_layer, output_features)  # in the working_gdb_path
		finally:
			arcpy.Delete_management(hucs_layer)

		return output_path


def attach_and_filter_counts(counts_data, min_species, hucs_layer, target_join_field):

	# first dump out the counts data
	count_huc_field = "counts_huc_id"
	count_field = "taxa_count"
	csv_path = tempfile.mktemp(prefix="species_count_data", suffix=".csv")
	with open(csv_path, 'wb') as csv_file:
		dictwriter = csv.DictWriter(csv_file, fieldnames=(count_huc_field, count_field))
		dictwriter.writeheader()
		for record in counts_data:
			dictwriter.writerow({count_huc_field: record[0], count_field: record[1]})

	new_table_name = "species_counts"   # we're still in the gdb path as the workspace, so the name is OK
	arcpy.TableToTable_conversion(csv_path, arcpy.env.workspace, new_table_name)
	arcpy.JoinField_management(hucs_layer, target_join_field, new_table_name, count_huc_field, [count_field,])  # in place join
	# arcpy.AddJoin_management(hucs_layer, target_join_field, new_table_name, count_huc_field)  # join the data

	arcpy.SelectLayerByAttribute_management(hucs_layer, "NEW_SELECTION", "\"{}\" > {}".format(count_field, min_species-1))

	# no need to return because the layer already exists in parent context


def _split_regions(huc_regions, region_group_field, working_folder):
	# split the regions out if they exist
	if huc_regions:
		gdb_name = "regions.gdb"
		gdb_path = os.path.join(working_folder, gdb_name)
		arcpy.CreateFileGDB_management(working_folder, gdb_name)

		# now split the regions out
		arcpy.SplitByAttributes_analysis(huc_regions, gdb_path, region_group_field)

		# get the list of new features to work with
		with Env("workspace", gdb_path):
			new_features = arcpy.ListFeatureClasses()

		full_paths = [os.path.join(gdb_path, fc) for fc in new_features]
	else:
		full_paths = [local_vars.HUCS]

	return full_paths


def _make_species_clusters_for_region(hucs, num_groups, matrix_info, spatial_constraint, initialization_method, report_folder=None, **assemblage_dump_params):
	"""

	:param hucs:
	:param num_groups:
	:param matrix_info:
	:param spatial_constraint:
	:param initialization_method:
	:param report_folder:  Folder to dump ArcGIS reports, but also used for cluster assemblage dump files
	:param assemblage_dump_params: for providing to assemblage dumping code, but params that aren't otherwise needed here,
								includes zone_field: the field with the HUC or Zone IDs - used for dumping cluster assemblages
								species_group=,
							  presence_types=,
							  aggregation=,
							  collections=,
	:return:
	"""

	region_name = os.path.split(hucs)[1]

	desc = arcpy.Describe(hucs)
	if not desc.hasOID:
		raise ValueError("The input features must have a unique integer object ID field")
	oid_field = desc.OIDFieldName

	# we need to copy the OID field to an integer field because the grouping tool wants integers, not ObjectIDs
	oid_copy_field = "oid_int_copy"
	arcpy.AddField_management(hucs, oid_copy_field, "LONG",)
	arcpy.CalculateField_management(hucs, oid_copy_field, "!{}!".format(oid_field), "PYTHON_9.3")

	for group_size in num_groups:
		output_name = os.path.join(arcpy.env.workspace, "{}_{}_groups".format(region_name, group_size))
		if report_folder:  # constructing this this way so that we can pass in no args if no report folder is provided
			if not os.path.exists(report_folder):
				os.makedirs(report_folder)
				log.debug("Making report folder {}".format(report_folder))
			extra_args = {"Output_Report_File": os.path.join(report_folder,"{}_{}_groups_report.pdf".format(region_name, group_size))}
		else:
			extra_args = {}  # extra_args will be expanded into keyworkd args when we run GroupingAnalysis

		species_fields = normalize_fields(matrix_info["species_fields"])
		arcpy.GroupingAnalysis_stats(hucs, oid_copy_field, output_name, group_size,
									 Analysis_Fields=species_fields,
									 Spatial_Constraints=spatial_constraint,
									 Initialization_Method=initialization_method,
									 **extra_args)

		# now, copy the cluster info back to the original - start with a unique name
		new_field_name = "{}_{}groups_num".format(region_name, group_size)
		arcpy.AddField_management(output_name, new_field_name, "LONG")
		arcpy.CalculateField_management(output_name, new_field_name, "!SS_GROUP!", "PYTHON_9.3")
		arcpy.JoinField_management(hucs, oid_copy_field, output_name, oid_copy_field, new_field_name)

		# Finally dump the cluster assemblage tables
		log.info("Dumping Assemblages from cluster file {}".format(hucs))
		dump_assemblage_table(clusters=hucs,
							  cluster_field=new_field_name,
							  output_folder=report_folder,
							  **assemblage_dump_params)

	return hucs


def dump_assemblage_table(clusters, cluster_field, output_folder, zone_field, species_group, presence_types, aggregation, collections):
	"""
		Given a set of clusters and a field with cluster IDs, dumps a table with the assemblages of all species in each cluster as common names
	:param clusters:
	:param cluster_field:
	:param output_folder:
	:param zone_field:
	:param species_group:
	:param presence_types:
	:param aggregation:
	:param collections:
	:return:
	"""
	## Make output name
	log.debug("Cluster Assemblage: Dumping Cluster Assemblage Tables")
	if not os.path.exists(output_folder):
		os.makedirs(output_folder)

	output_name = os.path.join(output_folder, "{}.csv".format(cluster_field))

	## Filter records to just the ones in that region (field is not null)
	all_records = arcpy.SearchCursor(clusters, where_clause="{} is not Null".format(cluster_field))

	## Read all HUCs in as a dictionary - cluster key and hucs in list as values
	debug_cluster_count = 0
	clusters = {}
	for record in all_records:
		debug_cluster_count += 1
		cluster = record.getValue(cluster_field)
		zone = record.getValue(zone_field)

		if cluster not in clusters:  # if we haven't seen this cluster before, then add a key with an empty list
			clusters[cluster] = []

		clusters[cluster].append(zone)  # and append the new zone into the list
	log.debug("Cluster Assemblage: Cluster Count: {}".format(debug_cluster_count))
	del all_records  # clear the cursor out

	## for each key in dictionary
	outputs = []
	for cluster_id in clusters:
		#### Get the assemblage
		#### make dict with cluster id and assemblage
		output_dict = dict(cluster_name=cluster_id)
		output_dict["cluster_assemblage"] = api.presence.get_presence_by_huc_set(species_or_group=species_group,
											 zone_list=clusters[cluster_id],
											 taxonomic_aggregation_level=aggregation,
											 presence_types=presence_types,
											 collections=collections)

		if aggregation.lower() in ("species", "genus", "family"):
			# if we have an aggregation level, get the common name from the species string as a new list
			common_name_assemblage = [api_tools.get_common_name_from_species_string(scientific_name=sci_name, level=aggregation) for sci_name in output_dict["cluster_assemblage"]]
			output_dict["cluster_assemblage"] = ", ".join(sorted(common_name_assemblage))  # then join those common names into a string
		else:
			output_dict["cluster_assemblage"] = ", ".join(sorted(output_dict["cluster_assemblage"]))  # make it print nicer by making it a string

		outputs.append(output_dict)
		log.debug("Cluster Assemblage: Assemblage for {}: {}".format(cluster_id, output_dict["cluster_assemblage"]))
	log.debug("Cluster Assemblage: Output Length: {}".format(len(outputs)))

	## With DictWriter, write out all clusters/assemblages to csv table
	with open(output_name, 'wb') as output_file:
		writer = csv.DictWriter(output_file, fieldnames=("cluster_name", "cluster_assemblage"))
		writer.writeheader()
		writer.writerows(outputs)

def make_safe(field_name):
	return field_name.replace(" ", "_").replace("(", "_").replace(")", "_").replace("-", "_")

def normalize_fields(fields):
	return [make_safe(field) for field in fields]