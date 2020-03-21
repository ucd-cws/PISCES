"""
THIS SCRIPT IS PARTWAY THROUGH A TRANSLATION FROM GLOBAL TO LOCAL VARIABLES. NEEDS TO HAVE config_ VARIABLES REMOVED
FROM LOCAL FUNCTIONS.
"""

import csv
import os
import re

import six
import pandas

import arcpy
initial_dir = os.getcwd()

from PISCES import local_vars
from PISCES import funcs
from PISCES import api
from PISCES import log
from PISCES import script_tool_funcs

def get_zones(zones_table, zone_field):

	rows_index = {}
	all_zones = []
	log.write("Getting zones", 1)

	query = "select distinct %s as myvalue from %s" % (zone_field, zones_table)

	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
	try:
		results = db_cursor.execute(query)
		for row in results:
			rows_index[str(row.myvalue)] = {zone_field: row.myvalue}
			all_zones.append(row.myvalue)
	finally:
		funcs.db_close(db_cursor, db_conn)

	return all_zones, rows_index

def aggregation_level(level=None):
	"""
	:param level: Family, Genus, Species, Subspecies (== None)
	:return: a dictionar
	"""
	level = level.lower()  # so we don't get case issues
	if level == "subspecies":
		return None



def get_species(species, qc_flag, zones, rows_index, presence_types, true_value, false_value, override_query, aggregation=None):
	"""

	:param species:
	:param qc_flag:
	:param zones:
	:param rows_index:
	:param presence_types:
	:param true_value:
	:param false_value:
	:param override_query:
	:return:
	"""
	log.write("getting data for %s" % species, 1)

	if override_query:
		query = override_query
	else:
		if qc_flag:
			query = "select distinct zone_id from observations, observation_collections where observations.species_id = ? and observations.presence_type in %s and observation_collections.observation_id = observations.objectid and observation_collections.collection_id in (%s)" % (presence_types, local_vars.hq_collections)
		else:
			query = "select distinct zone_id from observations where species_id = ? and presence_type in %s" % presence_types

	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
	try:
		results = db_cursor.execute(query, species)

		present_hucs = []

		for t_row in results:
			present_hucs.append(t_row.zone_id)

		for zone in present_hucs:
			if zone in rows_index:  # it might not because our study area may be smaller than we track
				rows_index[str(zone)][species] = true_value

		not_in_hucs = list(set(zones) - set(present_hucs))
		#not_in_hucs = list(set(present_hucs) & set(all_zones)) # get the hucs it's NOT in and explicitly set those rows to False - we could also have just set them all to False beforehand. oops

		for zone in not_in_hucs:
			if zone in rows_index:
				rows_index[str(zone)][species] = false_value
	finally:
		funcs.db_close(db_cursor, db_conn)

	return rows_index

def write_csv(filename, headers, rows, sci_name_output, header_row=None):
		log.write("Writing CSV out to %s" % filename, 1)
		csvfile = open(filename, 'wb')

		csvwriter = csv.DictWriter(csvfile, headers, quoting=csv.QUOTE_NONNUMERIC)
		#csvwriter.writeheader() # writeheader is new in 2.7
		headerrow = {}
		if not header_row:
			if sci_name_output:
				for row in headers:
					headerrow[row] = local_vars.all_fish[row].sci_name  # make a dict object where the lookup that the dictwriter will use has a value of the header
			else:
				for row in headers:
					headerrow[row] = local_vars.all_fish[row].species  # make a dict object where the lookup that the dictwriter will use has a value of the header

		else:
			headerrow = header_row

		csvwriter.writerow(headerrow)  # write out the header we just made

		for tkey in rows.keys():
				csvwriter.writerow(rows[tkey])

		csvfile.close()
		del csvwriter


def make_matrix(species_list, output_folder, presence_types="1,3,6,7,9", true_value=1, false_value=0, qc_flag=True, use_scientific_name=False, override_query=False, zones_table="HUC12FullState", zone_field="HUC_12", out_name="", aggregation=None):
	"""
		Produces a matrix of species presence information where the rows are zone ids (huc 12s) and the columns are species names.
		Presence is denoted using a true or false value in each cell
	:param species_list: A python list of species codes, or a single species group as a string. It currently does not
		behave like other tools where a mix of types works. If you do need to mix types, do so as a string with
		semicolons separating values to emulate the behavior of ArcGIS script tools.
	:param output_folder: The folder that the matrix should be placed in. The name is automatically determined
	:param presence_types: A string separated list of PISCES presence types to look for. Default is "1,3,6,7,9" for current presence.
	:param true_value: What value should be used in the matrix when a species is present in the zone? Defaults to "1"
	:param false_value: What value should be used in the matrix when a species is *not* present in the zone? Defaults to "0?
	:param qc_flag: Indicates whether only QCed data should be used. In the future this may be migrated to a collection ID input
	:param use_scientific_name: When True, column headers will use the species scientific name. When False (default), uses common name
	:param override_query: Advanced option allowing you to pass in your own query that retrieves the relevant records
			for a species. Should be of the form "select distinct zone_id from observations where species_id = ?"
	:param zones_table: If using an alternative set of zones, provide the table name
	:param zone_field: If using an alternative set of zones, provide the key field that indicates zones.
	:param aggregation: default None. By default, each distinct taxon in the group of species is used. When aggregation
			is set (options are "species", "genus", and "family"), columns will be created for the chosen aggregation
			level instead of individual taxa, and the column will show presence if at least one taxa in that aggregated
			level of the taxonomic tree is presence in a zone.
	:return dict: keys key_field and species_fields. key_field is the field the matrix can join on and species_fields
			is a list of all of the fields with species data
	"""

	# VALIDATION OF SPECIES PROVIDED IS DONE IN get_presence_by_taxa

	all_zones, rows_index = get_zones(zones_table, zone_field)

	headers = [zone_field]
	header_row = {}
	header_row[zone_field] = zone_field

	if qc_flag:
		collections = local_vars.hq_collections
	else:
		collections = None

	species_presence_data = api.presence.get_presence_by_taxa(species_list,
															  taxonomic_aggregation_level=aggregation,
															  presence_types=presence_types,
															  collections=collections)

	all_taxa = [record.taxon for record in species_presence_data]  # get a list of just the taxa
	distinct_taxa = list(set(all_taxa))  # dedupe - this is now the order that we'll go through them in
	del all_taxa  # it'll be large, so get rid of it quickly

	# Now, let's make a pandas data frame with the same number of rows
	# as we have zones and same number of columns as taxa - we need to be careful about the column data
	# types - since we know they'll all eventually get exported to CSVs, we can probably safely use text
	# for all, but if we think we might want to just use the pandas data frame for other purposes later,
	# then we might want to check if our presence/absence values are numbers and set column data types
	# accordingly. If we can just name numpy array fields, then skip pandas, as we'll then need to add
	# it as a dependency.

	# alternatively, we can just index all of the zones in the records, then go through them one by one
	# and check for each species in order - that seems slower than filling an array with our false value
	# then setting presence for each record.

	# could probably also have gotten exactly what we wanted with SQL statements, but using the API seems
	# better and more tested, even if less performant

	if not aggregation:
		if use_scientific_name:
			species_name_attribute = "sci_name"
		else:
			species_name_attribute = "species"
	else:
		species_name_attribute = None
	out_name = "{}_{}_presence_matrix.csv".format(os.path.join(output_folder, zones_table), out_name)

	taxa_fields = [_make_safe_field_name(taxon, taxa_info=local_vars.all_fish, name_attribute=species_name_attribute) for taxon in distinct_taxa]

	main_df = _make_empty_matrix(columns=taxa_fields, rows=all_zones, false_value=false_value)
	for record in species_presence_data:  # go through and set the actual present values
		main_df[_make_safe_field_name(record.taxon, taxa_info=local_vars.all_fish, name_attribute=species_name_attribute)][record.zone_id] = true_value

	main_df.to_csv(out_name, index_label="HUC_12")

	return {"key_field": zone_field, "species_fields": taxa_fields, "output_path": out_name, "data_frame": main_df}


def _make_empty_matrix(columns, rows, false_value):
	"""
		Makes an empty data frame with the specified rows and columns and fills it with the false value - from here
		we'll just set the true values based on the pulled data
	:param columns:
	:param rows:
	:param false_value:
	:return:
	"""
	base_matrix = pandas.DataFrame(columns=columns, index=rows)
	return base_matrix.fillna(false_value)


def _make_safe_field_name(name, taxa_info, name_attribute=None):
	"""
		When name_attribute is None, it means we're not using taxa level fields, so just make the field name safe. When
		name_attribute is provided, it looks up that attribute on each taxa to use as the field name
	:param name:
	:param taxa_info:
	:param name_attribute:
	:return:
	"""

	if name_attribute:
		main_string = getattr(taxa_info[name], name_attribute)
	else:
		main_string = name
	return re.sub(r'[)(\-\s\]\[]', '_', main_string).lower()


if __name__ == "__main__":

	config_species_picker = arcpy.GetParameterAsText(0)
	config_species_list = arcpy.GetParameterAsText(1)
	config_presence_values = arcpy.GetParameterAsText(2)
	config_outfolder = arcpy.GetParameterAsText(3)
	config_true = arcpy.GetParameterAsText(4)
	config_false = arcpy.GetParameterAsText(5)
	config_qc_flag = arcpy.GetParameter(6)
	config_scientific_name = arcpy.GetParameter(7)
	config_zones_table = arcpy.GetParameterAsText(8)
	config_zone_field = arcpy.GetParameterAsText(9)
	config_query_override = arcpy.GetParameterAsText(10)

	local_vars.start(arc_script=1)

	# new presence value code
	presence_values = script_tool_funcs.obs_type_selection_box_to_list(config_presence_values)
	config_presence_values = ",".join([six.text_type(val) for val in presence_values])  # need to cast back to string to use in a join operation

	# old presence value code
	"""
	if not config_presence_values:
		config_presence_values = "(1,3,6,7,9)"
	elif config_presence_values == "current":
		config_presence_values = "(1,3,6,7,9)"
	elif config_presence_values == "historic":
		config_presence_values = "(2,5,10)"
		log.write('using historic and non-translocated current presence values (%s)' % config_presence_values, 1)
	elif config_presence_values == "notrans":
		config_presence_values = "(1,3,9)"
	else:
		#elif (str(config_presence_values).find(",") > 0 or str(config_presence_values).find(";") > 0) and not str(config_presence_values).find("("):  # if it's a list of numbers that doesn't include parens
		config_presence_values = "(%s)" % config_presence_values
	"""

	if not config_zones_table:
		config_zones_table = "HUC12FullState"
	if not config_zone_field:
		config_zone_field = "HUC_12"

	if not config_outfolder:
		config_outfolder = initial_dir

	if not config_true:
		config_true = True

	if not config_false:
		config_false = False

	if not config_qc_flag:
		config_qc_flag = True

	if not config_scientific_name:
		config_scientific_name = False

	make_matrix(config_species_list, config_outfolder, config_presence_values, config_true, config_false, config_qc_flag, config_scientific_name, config_query_override, config_zones_table, config_zone_field)
