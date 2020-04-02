from __future__ import absolute_import, division, print_function

import os
import sys
import logging

import arcpy
from .. import arcpy_metadata as md

from .. import local_vars
from .. import funcs

from .richness_difference import richness_difference
from .common import postprocess_zones, add_field, empty_object, function_arg, query, get_arg

from ..code_library_data_files import generate_gdb_filename, fast_dissolve, make_temp

log = logging.getLogger("PISCES.callbacks")

connectivity_index = {}
network_end_hucs = ["CLOSED BASIN", "Mexico", "OCEAN"]
diversity_network = None
raster_working_gdb = None  # wll be set the first time it's used.


class watershed():
	def __init__(self):
		self.HUC_12 = None
		self.assemblage = []
		self.downstream = None
		self.upstream = []
		self.has_dam = False
		self.beta_div = None


def test_callback(zones_layer, db_cursor, args, parent_layer):
	"""
		Just a callback that prints out all of the arguments passed in, for testing purposes
	:param zones_layer:
	:param db_cursor:
	:param args:
	:param parent_layer:
	:return:
	"""
	log.info("TEST CALLBACK")
	for arg in args:
		log.info(arg)

	return zones_layer


def mega_diversity_info(zones_layer, db_cursor, args, parent_layer):
	"""
		Runs a large number of diversity functions on a single layer and returns it. These functions all add columns with data to one layer!

		Metadata: In order

		Note that since this function runs a number of other mapping functions, there will be some data duplication.
		Many of the non-qced output columns can now be deprecated since all data of interest is currently qced. They are here for legacy purposes and for any future changes

		-------- BASIC RICHNESS --------
		native_richness: integer. Raw alpha richness as count of number of native fish species in the HUC across PISCES.
		native_qc_richness: integer. Same as above, but only for species in a data collection that is qced
		native_qc_historic_richness: integer.  Same as native_qc_richness, but only for historic data types

		nonnative_richness: integer. Alpha richness of nonnatives. As of this writing, very little data on this.
		nonnative_qc_richness: integer. same as previous, but for data in qc dataset. Currently none for nonnatives, but here for future-proofing.

		all_richness: integer. Alpha richness of all fish species (native or nonnative) in PISCES, does not include amphibs and reptiles, etc.
		all_qc_richness: integer. Same as above, but for qced data. Should match native_qc_richness as of this writing.

		sens_nat_rich: integer. Richness of sensitive native species. Alpha richness of native fish taxa in PISCES where the Moyle 2011 average score <= 3 and >= 0. Uses the field Species_Aux.Average in PISCES for the score.
		sens_nat_qc_rich: integer. Same as previous except only for qced data in each HUC12

		sens_nat_assem: Assemblage of sensitive species in the HUC12 where sensitive is defined as in sens_nat_rich
		sens_nat_qc_assem: same as sens_nat_assem, but only for qc taxa

		-------- SENSITIVITY STATS --------
		avg_sensitivity_score: real (decimal). The average score (Species_Aux.Average) for all taxa in the HUC12
		avg_sensitivity_under3: real (decimal). same as above, but only including species with scores <= 3 and >= 0
		avg_sensitivity_under2: real (decimal). same as above but <=2 and >=0
		avg_sensitivity_under1: real (decimal). same as above but <=1 and >=0

		avg_qc_sensitivity_score: real (decimal). The average score (Species_Aux.Average) for all QCed taxa in the HUC12
		avg_qc_sensitivity_under3: real (decimal). same but <=3 and >=0
		avg_qc_sensitivity_under2: real (decimal). same but <=2 and >=0
		avg_qc_sensitivity_under1: real (decimal). same but <=1 and >=0

		-------- LOSSES AND EXTIRPATIONS --------
		This data is run twice, once for native fish, once for all fish - the species group (Native_Fish or Fish) will be in the field name to indicate which is which.

		current_richness: integer. QCed alpha richness for native fish species. Includes translocations
		current_assemblage: Assemblage of qced native fish species in the HUC12. Includes translocations

		historic_richness: integer. QCed *historic* alpha richness for native fish species
		historic_assemblage: Assemblage of qced native fish species historically in the HUC12

		losses: integer. Effectively, historic_richness - current_richess, except excludes translocations from current. Essentially, a count of extirpated species
		losses_list: The assemblage of species extirpated from that HUC12.
		gains: integer. How many native fish taxa have been translocated into that HUC12?
		gains_list. The assemblage of translocated species

		richness_difference: integer. count of the number of species gained-lost (so # currently - # historically). When the layer is exported without translocations included, this # may not correctly include translocations.

		-------- JACCARD DISTANCES --------
		To be updated later. Please ignore these for now

		-------- DOWNSTREAM INFO --------
		downstream_assemblage: Assemblage of species in the HUC12 downstream

	@param zones_layer:
	@param db_cursor:
	@param args:
	@param parent_layer:
	@return:
	"""

	# skip the passed in cursor - we'll make our own

	# TODO: We should make the initial crop of queries obey this group, but it'll slow the queries down a bit. Since the queries now use group joins, it'll be easy to convert
	group = get_arg(args, 0, "Native_Fish")
	collections = get_arg(args, 1, local_vars.hq_collections)
	current_presence_types = get_arg(args, 2, local_vars.current_obs_types)
	historic_precence_types = get_arg(args, 3, local_vars.historic_obs_types)
	run_non_qc = get_arg(args, 4, "0")

	args_native = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					native_fish
			   WHERE observations.zone_id = ?
				 AND observations.species_id = native_fish.fid
				 AND observations.presence_type IN (%s))""" % (
		local_vars.current_obs_types), 'native_richness', 'LONG']

	args_native_qc = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					native_fish,
					observation_collections
			   WHERE observations.zone_id = ?
				 AND observations.species_id = native_fish.fid
				 AND observations.presence_type IN (%s)
				 AND observations.objectid = observation_collections.observation_id
				 AND observation_collections.collection_id IN (%s))""" % (
		local_vars.current_obs_types, local_vars.hq_collections), 'native_qc_richness', 'LONG']

	args_native_qc_historic = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					species,
					observation_collections,
					species_groups
			   WHERE observations.zone_id = ?
				 AND species_groups.group_id = 1
				 AND species_groups.fid = species.fid
				 AND observations.species_id = species.fid
				 AND species.native = %s
				 AND observations.presence_type IN (%s)
				 AND observations.objectid = observation_collections.observation_id
				 AND observation_collections.collection_id IN (%s))""" % (
		local_vars.db_true, local_vars.historic_obs_types, local_vars.hq_collections), 'native_qc_historic_richness', 'LONG']

	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb)
	if run_non_qc == "1" or run_non_qc == 1:
		log.info("Running Native Richness")
		t_layer = postprocess_zones(zones_layer, db_cursor, args_native, parent_layer)
	else:
		t_layer = zones_layer

	log.info("Running QC Native Richness")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = postprocess_zones(t_layer, db_cursor, args_native_qc, parent_layer)

	log.info("Running QC Historic Native Richness")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = postprocess_zones(t_layer, db_cursor, args_native_qc_historic, parent_layer)

	args_nonnative = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					species,
					species_groups
			   WHERE observations.zone_id = ?
				 AND observations.species_id = species.fid
				 AND species_groups.group_id = 1
				 AND species_groups.fid = species.fid
				 AND species.native = %s
				 AND observations.presence_type IN (%s))""" % (local_vars.db_false, local_vars.current_obs_types), 'nonnative_richness', 'LONG']
	args_nonnative_qc = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					species,
					observation_collections,
					species_groups
			   WHERE observations.zone_id = ?
			   	 AND species_groups.group_id = 1
				 AND species_groups.fid = species.fid
				 AND observations.species_id = species.fid
				 AND species.native = %s
				 AND observations.presence_type IN (%s)
				 AND observations.objectid = observation_collections.observation_id
				 AND observation_collections.collection_id IN (%s))""" % (
		local_vars.db_false, local_vars.current_obs_types, local_vars.hq_collections), 'nonnative_qc_richness', 'LONG']

	if run_non_qc == "1" or run_non_qc == 1:
		log.info("Running NonNative Richness")
		db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
														existing_cursor=db_cursor, close_connection=True)
		t_layer = postprocess_zones(t_layer, db_cursor, args_nonnative, parent_layer)

	log.info("Running NonNative QC Richness")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = postprocess_zones(t_layer, db_cursor, args_nonnative_qc, parent_layer)

	args_all = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					species,
					species_groups
			   WHERE observations.zone_id = ?
			   	 AND species_groups.group_id = 1
				 AND species_groups.fid = species.fid
				 AND observations.species_id = species.fid
				 AND observations.presence_type IN (%s))""" % (
		local_vars.current_obs_types), 'all_richness', 'LONG']
	args_all_qc = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					species,
					species_groups,
					observation_collections
			   WHERE observations.zone_id = ?
				 AND observations.species_id = species.fid
				 AND species_groups.group_id = 1
				 AND species_groups.fid = species.fid
				 AND observations.presence_type IN (%s)
				 AND observations.objectid = observation_collections.observation_id
				 AND observation_collections.collection_id IN (%s))""" % (
		local_vars.current_obs_types, local_vars.hq_collections), 'all_qc_richness', 'LONG']

	if run_non_qc == "1" or run_non_qc == 1:
		log.info("Running Total Richness")
		db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
														existing_cursor=db_cursor, close_connection=True)
		t_layer = postprocess_zones(t_layer, db_cursor, args_all, parent_layer)

	log.info("Running Total QC Richness")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = postprocess_zones(t_layer, db_cursor, args_all_qc, parent_layer)

	args_sensitive = [
		"""SELECT count(*) AS col_value
		FROM
		  (SELECT DISTINCT observations.species_id
		   FROM observations,
				species_aux,
				species,
				species_groups
		   WHERE observations.zone_id = ?
			AND species_groups.group_id = 1
			AND species_groups.fid = species.fid
			 AND observations.presence_type IN (%s)
			 AND observations.species_id = species.fid
			 AND observations.species_id = species_aux.fid
			 AND species_aux.average < 3.01
			 AND species_aux.average > 0
			 AND species.native = %s)""" % (local_vars.current_obs_types, local_vars.db_true), 'sens_nat_rich',
		'LONG']

	args_sensitive_qc = [
		"""SELECT count(*) AS col_value
			FROM
			  (SELECT DISTINCT observations.species_id
			   FROM observations,
					species_aux,
					species,
					observation_collections,
					species_groups
			   WHERE observations.zone_id = ?
				 AND species_groups.group_id = 1
				 AND species_groups.fid = species.fid
				 AND observations.presence_type IN (%s)
				 AND observations.species_id = species.fid
				 AND observations.species_id = species_aux.fid
				 AND species_aux.average < 3.01
				 AND species_aux.average > 0
				 AND species.native = %s
				 AND observations.objectid = observation_collections.observation_id
				 AND observation_collections.collection_id IN (%s))""" % (
		local_vars.current_obs_types, local_vars.db_true, local_vars.hq_collections), 'sens_nat_qc_rich', 'LONG']

	if run_non_qc == "1" or run_non_qc == 1:
		log.info("Running Sensitivity Richness")
		db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
														existing_cursor=db_cursor, close_connection=True)
		t_layer = postprocess_zones(t_layer, db_cursor, args_sensitive, parent_layer)

	log.info("Running QC Sensitivity Richness")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = postprocess_zones(t_layer, db_cursor, args_sensitive_qc, parent_layer)

	log.info("Getting Sensitive Species Assemblages")
	args_sensitive_assem = [function_arg('_subfunction_convert_species', (
	"""SELECT DISTINCT observations.species_id AS col_value
		FROM observations,
			 species_aux,
			 species,
			 species_groups
		WHERE observations.zone_id = ?
		 AND species_groups.group_id = 1
		 AND species_groups.fid = species.fid
		  AND observations.presence_type IN (%s)
		  AND observations.species_id = species.fid
		  AND observations.species_id = species_aux.fid
		  AND species_aux.average < 3.01
		  AND species_aux.average > 0
		  AND species.native = %s""" % (local_vars.current_obs_types, local_vars.db_true),)), 'sens_nat_assem',
							'TEXT']
	args_sensitive_qc_assem = [function_arg('_subfunction_convert_species', (
	"""SELECT DISTINCT observations.species_id AS col_value
			FROM observations,
				 species_aux,
				 species,
				 observation_collections,
				 species_groups
			WHERE observations.zone_id = ?
			 AND species_groups.group_id = 1
			 AND species_groups.fid = species.fid
			  AND observations.presence_type IN (%s)
			  AND observations.species_id = species.fid
			  AND observations.species_id = species_aux.fid
			  AND species_aux.average < 3.01
			  AND species_aux.average > 0
			  AND species.native = %s
			  AND observations.objectid = observation_collections.observation_id
			  AND observation_collections.collection_id IN (%s)""" % (
	local_vars.current_obs_types, local_vars.db_true, local_vars.hq_collections),)), 'sens_nat_qc_assem', 'TEXT']
	t_layer = postprocess_zones(t_layer, db_cursor, args_sensitive_assem, parent_layer)
	t_layer = postprocess_zones(t_layer, db_cursor, args_sensitive_qc_assem, parent_layer)

	log.info("Generating Sensitivity Statistics")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = sensitivity_stats(t_layer, db_cursor, (1,), parent_layer)  # run it the first time with qc flag

	if run_non_qc == "1" or run_non_qc == 1:
		db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
														existing_cursor=db_cursor, close_connection=True)
		t_layer = sensitivity_stats(t_layer, db_cursor, (0,), parent_layer)  # second time without

	log.info("Generating Richness Differences for Native Fish")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = richness_difference(t_layer, db_cursor, ("Native_Fish", local_vars.hq_collections), parent_layer)

	log.info("Generating Richness Differences for All Fish")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = richness_difference(t_layer, db_cursor, ("Fish", local_vars.hq_collections), parent_layer)

	# beta diversity measures
	log.info("Generating Beta Diversities")
	args_beta_qc_native = ['native', 'nodams', 'diversity_jaccard', 'qc']
	args_beta_native = ['native', 'nodams', 'diversity_jaccard', 'no']
	args_beta_qc_all = ['nonnative', 'nodams', 'diversity_jaccard', 'qc']
	args_beta_all = ['nonnative', 'nodams', 'diversity_jaccard', 'no']

	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = diversity(t_layer, db_cursor, args_beta_qc_native, parent_layer)

	if run_non_qc == "1" or run_non_qc == 1:
		db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
														existing_cursor=db_cursor, close_connection=True)
		t_layer = diversity(t_layer, db_cursor, args_beta_native, parent_layer)
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = diversity(t_layer, db_cursor, args_beta_qc_all, parent_layer)

	if run_non_qc == "1" or run_non_qc == 1:
		db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
														existing_cursor=db_cursor, close_connection=True)
		t_layer = diversity(t_layer, db_cursor, args_beta_all, parent_layer)

	log.info("Getting Downstream Diversities")
	db_connection, db_cursor = funcs.refresh_cursor(database=local_vars.maindb, connection=db_connection,
													existing_cursor=db_cursor, close_connection=True)
	t_layer = get_downstream_diversities(t_layer, db_cursor, None, parent_layer)

	metadata = md.MetadataEditor(dataset=t_layer, temp_folder=local_vars.temp)
	metadata.abstract.prepend(mega_diversity_info.__doc__)
	metadata.title.set("All PISCES Richness Metrics")
	metadata.save()

	return t_layer


def dissolve(zones_layer, db_cursor, args, parent_layer):
	"""
		A simple callback that dissolves the zones into a single boundary so that things like outlines can be applied
	:param zones_layer: 
	:param db_cursor: 
	:param args: 
	:param parent_layer: 
	:return: 
	"""

	log.debug("Dissolving zones", True)
	new_name = generate_gdb_filename("dissolved")
	arcpy.Dissolve_management(zones_layer, new_name)

	new_layer = os.path.split(new_name)[1]  # get just the unnique part of the name so we can use it as the layer name
	arcpy.MakeFeatureLayer_management(new_name, new_layer)
	return new_layer


def ted_temp(zones_layer, db_cursor, args, parent_layer):
	args_sensitive_qc_flow_sens_assem = [function_arg('_subfunction_convert_species', (
	"""select distinct observations.species_id as col_value
        from  observations,
               species_aux,
               species,
               observation_collections,
               species_groups
        where  observations.zone_id = ?
			 AND species_groups.group_id = 1
			 AND species_groups.fid = species.fid
               and observations.presence_type in ( %s )
               and observations.species_id = species.fid
               and observations.species_id = species_aux.fid
               and species_aux.average < 3.01
               and species_aux.average > 0
               and species.native = %s
               and observations.objectid =
                   observation_collections.observation_id
               and observation_collections.collection_id in ( %s )
               and observations.species_id in (select fid
                                               from   species_groups,
                                                      defs_species_groups
                                               where
                   defs_species_groups.group_name = 'flow_sensitive'
                   and defs_species_groups.id =
                       species_groups.group_id) """ % (
	local_vars.current_obs_types, local_vars.db_true, local_vars.hq_collections),)), 'sens_nat_qc_flowsensitive_assemblage', 'TEXT']
	t_layer = postprocess_zones(zones_layer, db_cursor, args_sensitive_qc_flow_sens_assem, parent_layer)

	return t_layer


def export_raster(zones_layer, db_cursor, args, parent_layer):
	"""

	:param zones_layer:
	:param db_cursor:
	:param args:
	:param parent_layer:
	:return:

	Callback args are
	1: value code - the value to assign presence in the output raster
	2: template raster - what raster to use for cell size, extent, analysis mask, and snap raster
	3: database - what database to export the raster to (FGDB, PGDB, folder). This is not technically necessary because the raster will get saved in the layer cache with the maps, but if you want a dump of the rasters elsewhere, use this
	4: file extension to export to in database - include period where necessary. For GDBs, leave as None or empty
	"""
	# args: raster value when true, cellsize, extent=local_vars.HUCS

	global raster_working_gdb

	value_code = get_arg(args, 0, 3)  # default value of expert opinion
	template_raster = get_arg(args, 1, None)  # the raster to use as a template for snap raster, cell size, origin, and extent. Full path
	database = get_arg(args, 2, None)  # Optionally pass in a separate GDB to export the rasters to. If None, just returns the layer for use in the normal map
	export_extension = get_arg(args, 3, None)  # should include the "." - if we're exporting it (by defining "database", then what extension is it in? If None, then it's ok for GDBs, but if database is a folder, then this would include the extension

	if not os.path.isabs(template_raster):
		template_raster = os.path.join(local_vars.internal_workspace, template_raster)

	if not os.path.isabs(database):
		database = os.path.join(local_vars.internal_workspace, database)

	log.info("Converting to raster and exporting, if requested")

	bind_var, full_layer_path, layer_name = funcs.generate_layer_name(parent_layer.custom_query.bind_var,
																	  parent_layer.custom_query.id)
	export_name = layer_name

	field_name = "grid_value"

	try:
		### run a code lib fast dissolve
		dissolved = fast_dissolve(zones_layer)

		### add a field for the presence type = value_code
		arcpy.AddField_management(dissolved, field_name, "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED")
		arcpy.CalculateField_management(dissolved, field_name, value_code)  # set the new field to the value in value code so that it will get set in the raster
	except:
		if local_vars.debug:
			raise

		log.error("Raster export failed in step 1 for %s" % layer_name)
		return zones_layer  # on exception, return the HUC12 version of everything

	try:  # second block because we want to clean up the settings immediately below upon a crash in this section
		### set extent
		old_extent = arcpy.env.extent
		arcpy.env.extent = template_raster
		arcpy.env.snapRaster = template_raster
		arcpy.env.mask = template_raster

		### Make a separate workspace to prevent conflicts
		if not raster_working_gdb:
			temp_folder, raster_working_gdb = make_temp(override=True)

		### run the conversion
		out_raster = generate_gdb_filename(name_base="pisces_raster", return_full=True,
													  gdb=raster_working_gdb, scratch=False)
		arcpy.FeatureToRaster_conversion(in_features=dissolved, field=field_name, out_raster=out_raster,
										 cell_size=template_raster)

		### export if we're supposed to
		if database:
			if export_extension:  # if it's a file with an extension, include it in the name creation
				out_name = os.path.join(database, export_name + export_extension)
			else:
				out_name = os.path.join(database, export_name)

			if arcpy.Exists(out_name):  # delete it if it exists - we could turn on overwriteOutput too.
				arcpy.Delete_management(out_name)
			arcpy.CopyRaster_management(in_raster=out_raster, out_rasterdataset=out_name)

			### delete the dissolved item
			arcpy.Delete_management(dissolved)  # clean up - remove it from memory

		arcpy.env.extent = old_extent  # reset the extent so it's not totally broken
		arcpy.env.extent = None
		arcpy.env.snapRaster = None
	except:
		if local_vars.debug:
			raise

		log.error("Raster export failed for %s" % layer_name)
		if old_extent:
			arcpy.env.extent = old_extent  # reset the extent so it's not totally broken
		arcpy.env.extent = None
		arcpy.env.snapRaster = None
		return zones_layer

	return zones_layer  # TODO: Switch this line to the one below. If we export rasters, we'll run into problems during map generation.


# return out_raster  # return the location (in memory? no probably in scratch workspace)


def sensitivity_stats(zones_layer, db_cursor, args, parent_layer):
	"""

	:param zones_layer:
	:param db_cursor:
	:param args:
	:param parent_layer:
	:return:
	"""

	stats_query = query()

	if args and (args[0] == "1" or args[0] == 1):
		qc_flag = True
		qc_insert = "qc_"
		log.info("QC = True")
	else:
		qc_flag = False
		qc_insert = ""
		log.info("QC = False")

	def make_query(qc_f):
		stats_query = query()
		stats_query.set_defaults(zonal_callback=True, qc=qc_f)
		stats_query.tables.append("species_aux")
		stats_query.where_clauses.append("species_aux.fid = species.fid")

		stats_query.base = """SELECT avg(l_avg) AS col_value
								FROM (
								SELECT species_aux.fid,
												species_aux.average as l_avg"""  # no distinct needed because table already unique on FID
		stats_query.suffix = ")"

		return stats_query

	stats_query = make_query(qc_flag)
	stats_args = [stats_query.compose(), 'avg_%ssensitivity_score' % qc_insert, 'DOUBLE']
	log.info("sensitivity query is: %s" % stats_query.compose())
	t_layer = postprocess_zones(zones_layer, db_cursor, stats_args, parent_layer)

	stats_query2 = make_query(qc_flag)
	stats_query2.where_clauses.append("species_aux.average <= 3 and species_aux.average >= 0")  # change the last item
	stats_args2 = [stats_query2.compose(), 'avg_%ssensitivity_under3' % qc_insert, 'DOUBLE']
	log.info("sensitivity query is: %s" % stats_query2.compose())
	t_layer = postprocess_zones(t_layer, db_cursor, stats_args2, parent_layer)

	stats_query3 = make_query(qc_flag)
	stats_query3.where_clauses.append("species_aux.average <= 2 and species_aux.average >= 0")
	stats_args3 = [stats_query3.compose(), 'avg_%ssensitivity_under2' % qc_insert, 'DOUBLE']
	log.info("sensitivity query is: %s" % stats_query3.compose())
	t_layer = postprocess_zones(t_layer, db_cursor, stats_args3, parent_layer)

	stats_query4 = make_query(qc_flag)
	stats_query4.where_clauses.append("species_aux.average <= 1 and species_aux.average >= 0")
	stats_args4 = [stats_query4.compose(), 'avg_%ssensitivity_under1' % qc_insert, 'DOUBLE']
	log.info("sensitivity query is: %s" % stats_query4.compose())
	t_layer = postprocess_zones(t_layer, db_cursor, stats_args4, parent_layer)

	return t_layer


def get_downstream_diversities(t_layer, db_cursor, cb_args, parent_layer):
	"""
		Standard callback - takes a layer of hucs, gets the assemblage for all hucs, then adds two fields with that data
		1) contains the downstream assemblage and
		2) contains the count of downstream taxa

	@param t_layer:
	@param db_cursor:
	@param cb_args:
	@param parent_layer:
	@return: t_layer
	"""
	global diversity_network
	if not diversity_network:
		diversity_network = get_diversity_into_network(False, db_cursor, True, True, "simple", t_layer)

	log.info("Getting Downstream Diversities")

	args = ("downstream", "",)
	func_arg = function_arg("_get_assemblage_for_row", args)
	postprocess_zones(t_layer, db_cursor, (func_arg, "downstream_assemblage", "TEXT"), parent_layer)
	args2 = ("downstream", "count",)
	func_arg2 = function_arg("_get_assemblage_for_row", args2)
	postprocess_zones(t_layer, db_cursor, (func_arg2, "downstream_count", "DOUBLE"), parent_layer)

	return t_layer


def richness(zones_layer, db_cursor, cb_args, parent_layer):  # layer callback
	"""
		DEPRECATED: An old richness function - superceded by passing the correct parameters to postprocess_zones
	@param zones_layer:
	@param db_cursor:
	@param cb_args:
	@param parent_layer:
	@return:
	"""

	arcpy.env.overwriteOutput = True

	log.info("Building species richness layer - this may take some time!")

	l_temp_file = os.path.join(local_vars.workspace, "richness")
	arcpy.CopyFeatures_management(zones_layer, l_temp_file)  #copy any selected zones out

	arcpy.AddField_management(l_temp_file, "Richness", "LONG")  # add the column

	rows = arcpy.UpdateCursor(l_temp_file)

	if not (cb_args == None or cb_args is False):
		sql_ext = cb_args
	else:
		sql_ext = ""

	log.info("sql extension on callback: %s" % sql_ext)

	for row in rows:
		if row.HUC_12 == None:
			print("skipping row...")
			continue

		l_sql = """SELECT Count(*) AS l_count
					FROM (
					SELECT DISTINCT observations.species_id
					FROM observations,
						 species,
						 species_groups
					WHERE observations.zone_id = ?
					AND species_groups.group_id = 1
					AND species_groups.fid = species.fid
					  AND observations.species_id = species.fid""" + sql_ext
		db_cursor.execute(l_sql, row.HUC_12)

		l_result = db_cursor.fetchone()  # just get me the first row. There only should be one anyway...
		row.Richness = l_result.l_count  # the first row of the result and the first item in that row

		rows.updateRow(row)  # save it!

	del row
	del rows  # cleanup
	arcpy.env.overwriteOutput = False

	# read it back in
	zone_layer = "Richness_Zones"
	arcpy.MakeFeatureLayer_management(l_temp_file, zone_layer)

	# return it
	return zone_layer


def genus_family_richness(zones_layer, db_cursor, gf, parent_layer):  # layer callback
	"""
		DEPRECATED
	@param zones_layer:
	@param db_cursor:
	@param gf:
	@param parent_layer:
	@return:
	"""
	arcpy.env.overwriteOutput = True

	log.info("Building family richness layer - this may take some time!")

	l_temp_file = os.path.join(local_vars.workspace, "richness")
	arcpy.CopyFeatures_management(zones_layer, l_temp_file)  # copy any selected zones out

	arcpy.AddField_management(l_temp_file, "Richness", "LONG")  # add the column

	rows = arcpy.UpdateCursor(l_temp_file)

	for row in rows:
		l_sql = "SELECT Count(*) AS l_count FROM (SELECT DISTINCT Family FROM Species, species_groups WHERE FID = (SELECT DISTINCT Species_ID FROM Observations WHERE Zone_Id = ?) and species_groups.group_id=1 and species_groups.fid=species.fid)"
		db_cursor.execute(l_sql, row.HUC_12)

		l_result = db_cursor.fetchone()  # just get me the first row. There only should be one anyway...
		row.Richness = l_result.l_count  # the first row of the result and the first item in that row

		rows.updateRow(row)  # save it!

	del row
	del rows  # cleanup
	arcpy.env.overwriteOutput = False

	# read it back in
	zone_layer = "Richness_Zones"
	arcpy.MakeFeatureLayer_management(l_temp_file, zone_layer)

	# return it
	return zone_layer


def make_tooltip_column(zones_layer, db_cursor, args):
	arcpy.env.overwriteOutput = True

	log.info("Building tooltip")

	l_temp_file = os.path.join(local_vars.workspace, "tooltip")
	arcpy.CopyFeatures_management(zones_layer, l_temp_file)  # copy any selected zones out

	arcpy.AddField_management(l_temp_file, "Tooltip", "LONG")  # add the column

	rows = arcpy.UpdateCursor(l_temp_file)

	for row in rows:
		if row.HUC_12 is None:
			print("skipping row...")
			continue

		l_sql = """SELECT DISTINCT observation_sets.*
				FROM observation_sets,
					 observations
				WHERE observations.species_id = ?
				  AND observations.zone_id = ?
				  AND observations.set_id = observation_sets.set_id;"""
		db_cursor.execute(l_sql, row.HUC_12)  # TODO: Needs to use a query brought in by argument and needs a way to bring in the species and pass it as a bind variable - need a robust system for operators in the text that get replaced before the bind arguments are passed in.

		l_result = db_cursor.fetchone()  # just get me the first row. There only should be one anyway...
		row.Richness = l_result.l_count  # the first row of the result and the first item in that row

		rows.updateRow(row)  # save it!

	del row
	del rows  # cleanup
	arcpy.env.overwriteOutput = False

	# read it back in
	zone_layer = "Richness_Zones"
	arcpy.MakeFeatureLayer_management(l_temp_file, zone_layer)

	# return it
	return zone_layer


def representation(zones_layer, db_cursor, cb_args, parent_layer):
	'''just an alias for clipped_layer_overlay'''
	return clipped_layer_overlay(zones_layer, db_cursor, cb_args, parent_layer)


def clipped_layer_overlay(zones_layer, db_cursor, cb_args, parent_layer):
	log.info("Creating Layer Representation")
	if not cb_args or len(cb_args) == 0:  # if we don't have an argument, default to all_rivers
		clip_layer = os.path.join(local_vars.geo_aux, "all_rivers")
	else:  # callback args come in as a list, so pull the first item
		clip_layer = cb_args[0]

	clipped_layer = "clipped_layer"
	if arcpy.Exists(clipped_layer):
		# if it's already in memory, then destroy it
		arcpy.Delete_management(clipped_layer)

	log.debug("Running callback clipped_layer_overlay for feature %s" % clip_layer)

	# unique_arc_name = arcpy.CreateUniqueName("temp_",local_vars.workspace) # generate a unique name for the zones dissolve
	#arcpy.Dissolve_management(zones_layer,unique_arc_name) # dissolve the HUCs so that the input is

	unique_arc_name_2 = arcpy.CreateUniqueName("temp_mapping_result_", local_vars.workspace)
	arcpy.Clip_analysis(clip_layer, zones_layer,
						unique_arc_name_2)  # clip the input to the dissolved zones and put it in unique_arc_name_2

	t_layer = arcpy.MakeFeatureLayer_management(unique_arc_name_2, clipped_layer)

	# return clip_layer
	return clipped_layer


def connectivity(zones_layer, db_cursor, args, map_layer):
	att_types = args[0]
	attributes = args[1:]

	arcpy.env.overwriteOutput = True

	new_layer = os.path.join(local_vars.workspace, "connectivity_temp")

	arcpy.CopyFeatures_management(zones_layer, new_layer)  # copy it out
	arcpy.MakeFeatureLayer_management(new_layer,
									  zones_layer)  # copy it back - need to do this to not modify original hucs

	arcpy.AddField_management(zones_layer, "connectivity_upstream_count", "LONG")

	select_vars = ""
	for att in attributes:
		# for every attribute, add a column to the layer and add it to the list of variables we want to collect info on in order to select appropriately
		try:
			arcpy.AddField_management(zones_layer, "connectivity_%s" % att, att_types)
		except:
			raise local_vars.MappingError(
				"Couldn't add field in callback 'connectivity' - make sure you are specifying an appropriate data type for the column")

		select_vars += "%s; " % att

	huc_cursor = arcpy.UpdateCursor(zones_layer)
	sys.setrecursionlimit(6000)  # set it to far higher than the number of HUCs - we shouldn't even get close to it...

	h_num = 0
	for huc in huc_cursor:
		h_num += 1
		print("%s - Next" % h_num)
		connectivity_recurse(zones_layer, huc, select_vars, attributes, huc_cursor)
		del huc

	# this function short circuits if we've already evaluated a given huc, so the attributes and upstream of any given huc will only be run once for speed

	del huc_cursor

	log.info("Deleting EVERYTHING from table connectivity to insert new values!")
	db_cursor.execute("delete * from Connectivity")

	global connectivity_index
	sql = "insert into connectivity (zoned,zoneu) values (?,?)"
	for huc in connectivity_index.keys():
		for up_huc in connectivity_index[huc]:
			db_cursor.execute(sql, huc, up_huc)

	return zones_layer


def connectivity_recurse(zones_layer, huc, select_vars, atts, huc_cursor):  # atts = attributes to look at

	global connectivity_index

	if huc.getValue(
			"connectivity_upstream_count") is not None:  # if attributes are already set then we don't need to continue upstream of it - just use the current value
		return_obj = empty_object()
		return_obj.connectivity_upstream_count = huc.getValue("connectivity_upstream_count")
		for item in atts:  # it's an object just for ease of access
			return_obj.__dict__[item] = huc.getValue(item)  # add the value for the current huc
			return_obj.__dict__["connectivity_%s" % item] = huc.getValue(
				"connectivity_%s" % item)  # and the value for all upstream hucs
			return_obj.hucs = connectivity_index[huc.HUC_12]  # set the list of upstream hucs
		return return_obj

	upstream_hucs = arcpy.UpdateCursor(zones_layer, "\"HU_12_DS\" = '%s'" % huc.getValue("HUC_12"), "", "",
									   "")  # needs to be an update cursor because we need to use the cursor that a row came from to update
	# select huc_12, attributes from local_vars.HUCS where HUC12FullState.HU_12_DS = huc_id

	conn_count = 0  # the number of hucs upstream
	return_obj = empty_object()
	return_obj.hucs = []

	for item in atts:
		return_obj.__dict__[item] = huc.getValue(item)  # add the value for the current huc
		return_obj.__dict__["connectivity_%s" % item] = None

	hucs_upstream = False
	# we have hucs upstream!
	for up_huc in upstream_hucs:
		hucs_upstream = True
		conn_count += 1  # each huc here is an additional huc

		# Recurse!
		upstream_atts = connectivity_recurse(zones_layer, up_huc, select_vars, atts, upstream_hucs)

		conn_count += upstream_atts.connectivity_upstream_count  # now also add the number of upstream hucs the upstream huc hadd
		for item in atts:
			if upstream_atts.__dict__["connectivity_%s" % item] is None:
				upstream_atts.__dict__["connectivity_%s" % item] = 0
			if upstream_atts.__dict__[item] is None:
				upstream_atts.__dict__[item] = 0
			if return_obj.__dict__["connectivity_%s" % item] is None:
				return_obj.__dict__["connectivity_%s" % item] = 0

			return_obj.__dict__["connectivity_%s" % item] += upstream_atts.__dict__["connectivity_%s" % item] + \
															 upstream_atts.__dict__[
																 item]  # add the value of the upstream huc to its upstream values and assign it to the spot on this huc
			return_obj.hucs.append(up_huc.HUC_12)
			return_obj.hucs.extend(upstream_atts.hucs)

	if hucs_upstream is False:  # if nothing is upstream, then we didn't enter the loop!
		for item in atts:
			return_obj.__dict__[item] = huc.getValue(item)  # add the value for the current huc
			return_obj.__dict__[
				"connectivity_%s" % item] = 0  # WARNING - this doesn't scale to different data types...

	return_obj.connectivity_upstream_count = conn_count
	huc.setValue("connectivity_upstream_count", conn_count)
	for field in atts:  #set the fields to the row
		try:
			huc.setValue("connectivity_%s" % field, return_obj.__dict__["connectivity_%s" % field])
		except:
			log.error("Unable to set value of field connectivity_%s for huc %s" % (field, huc.HUC_12))

		try:
			connectivity_index[huc.HUC_12] = return_obj.hucs
		except:
			log.error("Unable to save upstream hucs")

	huc_cursor.updateRow(huc)
	return return_obj


def network_distance(zones_layer, db_cursor, args, map_layer):
	log.info("Getting network distances")

	# set up the lookup
	zones_info = {}
	zones_cursor = arcpy.SearchCursor(zones_layer)
	for zone in zones_cursor:
		zones_info[zone.HUC_12] = zone.HU_12_DS
	del zones_cursor

	if args[0] is None:
		return zones_layer

	arcpy.env.overwriteOutput = True

	new_layer = os.path.join(local_vars.workspace, "network_dist_temp")

	arcpy.CopyFeatures_management(zones_layer, new_layer)  # copy it out
	arcpy.MakeFeatureLayer_management(new_layer,
									  zones_layer)  # copy it back - need to do this to not modify original hucs
	arcpy.AddField_management(zones_layer, "network_distance", "INTEGER")

	if not type(
			args) == 'list':  # if we don't have a second huc, then just get the distance from every huc in the layer to this one
		l_curs = arcpy.UpdateCursor(zones_layer)
		ind = 0
		for huc in l_curs:
			ind += 1
			print("%s..." % ind)  # print how many we've done!
			if huc.HUC_12 == args:
				huc.setValue("network_distance", 0)
			else:
				distance = network_get_distance(args, huc.HUC_12,
												zones_info)  # we could save a TON of time on this by caching the path for args[0]
				huc.setValue("network_distance", distance)
			l_curs.updateRow(huc)
	else:  # just do these two hucs, setting the attribute on the new huc
		distance = network_get_distance(args[0], args[1], zones_info)
		l_curs = arcpy.UpdateCursor(zones_layer, "\"HUC_12\" = '%s'" % args[1])
		for huc in l_curs:
			huc.setValue("network_distance", distance)
			l_curs.updateRow(huc)

	return zones_layer


def network_get_distance(zone1, zone2, zones_info):
	huc1_path = []
	huc2_path = []

	network_get_path(zone=zone1, zones_downstream=zones_info, path_list=huc1_path)
	network_get_path(zone=zone2, zones_downstream=zones_info, path_list=huc2_path)

	distance = 0
	for index in range(len(huc1_path)):
		if huc1_path[index] in huc2_path:  # figure out where they meet first
			distance = index
			huc2_index = huc2_path.index(huc1_path[index])
			if not huc2_index == -1:
				return distance + huc2_index
			else:
				return 20000  # it's not actually there, which also shouldn't happen

	# 20000 is a number large enough to not ever appear naturally - we can exclude it in symbology
	return 20000  # if we get here, there was a problem, OR they aren't in the same basin (so, one is klamath and the other Sac, etc


def network_get_path(zone, zones_downstream, path_list):
	global network_end_hucs

	current_DS = zone
	while (current_DS is not None):

		if current_DS in network_end_hucs:
			break
		path_list.append(current_DS)
		try:
			current_DS = zones_downstream[current_DS]
		except KeyError:  # we have hucs that reference downstream hucs, but because we clip to CA, they are missing - we need to tolerate that
			break


def find_upstream(watershed, all_watersheds, dams_flag=False):
	if len(all_watersheds[watershed].upstream) > 0:  # if we've already run for this watershed
		return all_watersheds[watershed].upstream

	if dams_flag and all_watersheds[watershed].has_dam:
		return []  # if this is a dam and we're account for that, return nothing upstream - can't go further

	all_us = []
	for wat in all_watersheds:
		if all_watersheds[wat].downstream == watershed:
			us = find_upstream(wat, all_watersheds, dams_flag)
			all_us.append(wat)
			all_us += us

	all_watersheds[watershed].upstream = all_us
	return all_us


def get_diversity_into_network(dams_flag, db_cursor, native_flag, qc_flag, upstream_flag, zones_layer):
	all_watersheds = {}
	# some setup

	log.info("Setting up watersheds")
	reader = arcpy.SearchCursor(zones_layer)
	for record in reader:
		t_ws = watershed()
		t_ws.HUC_12 = record.HUC_12
		t_ws.downstream = record.HU_12_DS
		all_watersheds[record.HUC_12] = t_ws
	del reader
	del record

	log.info("Getting upstream hucs - this may take some time")

	for l_wat in all_watersheds.keys():
		if upstream_flag == "simple":
			try:
				all_watersheds[all_watersheds[l_wat].downstream].upstream.append(
					l_wat)  # add this huc to the list of upstream hucs for the one downstream
			except:
				pass  # it just doesn't exist
		elif upstream_flag == "trace":
			# the following function has a return value...untested code...
			all_watersheds[all_watersheds[l_wat].downstream].upstream += find_upstream(l_wat, all_watersheds, dams_flag)

	if dams_flag:
		log.info("getting dam information")

		# get the dam info
		sql = "SELECT zone from zones_aux where rim_dam = %s" % local_vars.db_true
		results = db_cursor.execute(sql)
		for lz in results:
			all_watersheds[lz.Zone].has_dam = True
		del results

	non_native_query = """
		SELECT DISTINCT species_id
		FROM observations
		WHERE presence_type IN (%s)
		  AND zone_id = ?
	 """ % (local_vars.current_obs_types)
	native_query = """SELECT DISTINCT observations.species_id
					FROM observations,
						 species,
						 species_groups
					WHERE observations.zone_id = ?
						AND species_groups.group_id = 1
						AND species_groups.fid = species.fid
					  AND observations.presence_type IN (%s)
					  AND species.FID = Observations.Species_ID
					  AND species.Native = %s""" % (local_vars.current_obs_types, local_vars.db_true)
	qc_ext = "and observations.objectid = observation_collections.observation_id and observation_collections.collection_id in (%s)" % local_vars.hq_collections
	non_native_qc_query = """SELECT DISTINCT species_id
							FROM observations,
								 observation_collections
							WHERE presence_type IN (%s)
							  AND zone_id = ? %s""" % (
		local_vars.current_obs_types, qc_ext)
	native_qc_query = """SELECT DISTINCT observations.species_id
						FROM observations,
							 species,
							 observation_collections,
							 species_groups
						WHERE observations.zone_id = ?
							AND species_groups.group_id = 1
							AND species_groups.fid = species.fid
							AND observations.presence_type IN (%s)
							AND species.fid = observations.species_id
							AND species.native = %s %s""" % (local_vars.current_obs_types, local_vars.db_true, qc_ext)

	log.info("getting assemblage information")
	# get the assemblage data
	if native_flag:
		if qc_flag:
			query = native_qc_query
		else:
			query = native_query
	else:
		if qc_flag:
			query = non_native_qc_query
		else:
			query = non_native_query

	for l_wat in all_watersheds.keys():
		results = db_cursor.execute(query, l_wat)

		for species in results:  # add all the species to the assemblage
			all_watersheds[l_wat].assemblage.append(species.species_id)

	return all_watersheds


def diversity(zones_layer, db_cursor, args, map_layer):
	"""
		Generates 4 different layers based upon args
		args = native/non,dams/no,divtype,qc/noqc
	"""

	try:
		if args[0] == "native":
			native_flag = True
		else:
			native_flag = False
	except:
		native_flag = True

	try:
		if args[1] == "dams":
			dams_flag = True
		else:
			dams_flag = False
	except:
		dams_flag = False

	try:
		div_func = args[2]
	except:
		div_func = "diversity_jaccard"

	try:
		if args[3] == "qc":
			qc_flag = True
		else:
			qc_flag = False
	except:
		qc_flag = False

	try:
		if args[4] == "upstream_simple":
			upstream_flag = "simple"
		else:
			upstream_flag = "trace"
	except:
		upstream_flag = "simple"

	all_watersheds = get_diversity_into_network(dams_flag, db_cursor, native_flag, qc_flag, upstream_flag, zones_layer)

	log.info("calculating diversity")
	# calculate the diversity

	diversity_func = globals()[div_func]

	for l_wat in all_watersheds.keys():
		all_watersheds[l_wat].beta_div = diversity_func(all_watersheds[l_wat], all_watersheds)

	log.info("updating data")

	if dams_flag and native_flag:
		sql = "UPDATE zones_aux SET beta_div_nat_cur = ? WHERE zone = ?"
		layer_name = "div_native_dams"
		assemblage_field_name = "assemblage_native_dams"
	elif native_flag:
		sql = "UPDATE zones_aux SET beta_div_nat_hist = ? WHERE zone = ?"
		layer_name = "div_native"
		assemblage_field_name = "assemblage_native"
	elif dams_flag:
		sql = "UPDATE zones_aux SET beta_div_nn_cur = ? WHERE zone = ?"
		layer_name = "div_all_dams"
		assemblage_field_name = "assemblage_all_dams"
	else:
		sql = "UPDATE zones_aux SET beta_div_nn_hist = ? WHERE zone = ?"
		layer_name = "div_all"
		assemblage_field_name = "assemblage_all"

	if qc_flag:
		layer_name = "%s_qc" % layer_name
		assemblage_field_name = "%s_qc" % assemblage_field_name

	for l_wat in all_watersheds.keys():
		db_cursor.execute(sql, all_watersheds[l_wat].beta_div, l_wat)

	new_layer = arcpy.CreateUniqueName(layer_name, local_vars.workspace)
	layer_name = os.path.split(new_layer)[1]

	arcpy.env.overwriteOutput = True

	arcpy.CopyFeatures_management(zones_layer, new_layer)  # copy it out
	arcpy.MakeFeatureLayer_management(new_layer,
									  zones_layer)  # copy it back - need to do this to not modify original hucs

	arcpy.AddField_management(zones_layer, layer_name, "DOUBLE")
	arcpy.AddField_management(zones_layer, assemblage_field_name, "TEXT", "", "", 10000)
	updater = arcpy.UpdateCursor(zones_layer)
	for row in updater:
		cname_assemblage = diversity_assemblage_to_cname(all_watersheds[row.HUC_12].assemblage)
		# try:
		#	t_set = None
		#if type(all_watersheds[row.HUC_12].beta_div) == "int" or type(all_watersheds[row.HUC_12].beta_div) == "float":
		t_set = float(all_watersheds[row.HUC_12].beta_div)
		#except:
		#	t_set = None
		#log.debug("layer_name: [%s], t_set: [%s], assemblage: [%s]" % (layer_name,t_set,str(cname_assemblage)))
		row.setValue(layer_name, t_set)
		row.setValue(assemblage_field_name, str(cname_assemblage))
		updater.updateRow(row)

	del updater

	return zones_layer


def diversity_assemblage_to_cname(assemblage):
	output_assemblage = []
	for species in assemblage:
		species = unicode(species)
		if species in local_vars.all_fish:
			output_assemblage.append(local_vars.all_fish[species].species)  # append the common name
		else:
			log.error("Species in observations, but not recorded in all_fish - species code %s" % species)
	return output_assemblage


def diversity_count(current_watershed, all_watersheds):
	diversity = 0
	if current_watershed.downstream is None:
		return 0

	# if downstream is a network ending, then set the assemblage to 0
	if current_watershed.downstream in network_end_hucs:
		return 0

	for species in current_watershed.assemblage:
		try:
			if species not in all_watersheds[current_watershed.downstream].assemblage:
				diversity += 1
			for l_up in current_watershed.upstream:  # check upstream too
				if species not in all_watersheds[l_up].assemblage:
					diversity += 1
		except:
			diversity = 0

	return diversity


def diversity_jaccard(current_watershed, all_watersheds):  # should already have the assemblages
	'''returns Jaccard DISSIMILARITY'''
	connected_assemblage = []  # set it here in case the next step fails
	try:
		if current_watershed.downstream not in network_end_hucs:  # if it's not a network end huc
			connected_assemblage += all_watersheds[current_watershed.downstream].assemblage
	except KeyError:
		pass  # no downstream huc existing

	for l_up in current_watershed.upstream:  # check upstream too
		connected_assemblage += all_watersheds[l_up].assemblage  # add those to the connected assemblage
	connected_assemblage = list(set(connected_assemblage))  # remove duplicates
	assem_union = list(set(connected_assemblage) | set(current_watershed.assemblage))
	assem_intersect = list(set(connected_assemblage) & set(current_watershed.assemblage))

	len_assem_intersect = len(assem_intersect)
	len_assem_union = len(assem_union)

	if len_assem_union != 0:  # don't divide by zero - the universe doesn't like that
		return (1 - (float(len_assem_intersect) / float(len_assem_union)))  # return jaccard diversity (intersect/union)
	else:
		return 0;


def diversity_difference():
	pass


def forest_listing(zones_layer, db_cursor, args):  # map callback
	pass


def _get_assemblage_for_row(t_layer, db_cursor, args, parent_layer):
	"""
		Given a huc in args[1], it returns the assemblage of the downstream huc

	@param t_layer:
	@param db_cursor:
	@param args:
		A three item tuple:
			0: location to get assemblage for - default is the current zone. If args[0] == "downstream" then the downstream
				zone assemblage is returned
			1: return assemblage or count of assemblage? returns assemblage by default and count when args[1] == "count"
			2: whether to return common name or FID values for assemblage. returns common name by default and FIDs
				when args[2] == "FID"

	@param parent_layer:
	@return:
	"""
	# TODO: Document - this is a kluge - Nick was sick and wrote it in a rush

	huc_id = args[1]
	func_args = args[0].argument

	if func_args and len(func_args) > 1 and func_args[1] == "count":
		# set this up once so it's not done multiple times below
		empty = 0
	else:
		empty = []

	try:
		if func_args and len(func_args) > 0 and func_args[0] == "downstream":
			downstream_id = diversity_network[huc_id].downstream
			if downstream_id not in diversity_network:  # doesn't exist - return 0 or empty list
				return empty
			#check if it exists, and return an empty list if it doesn't to signify unknown or none - this way, we don't run up into a "NoneType has no attribute __iter__" later
			if func_args and len(func_args) > 1 and func_args[1] == "count":
				return len(diversity_network[downstream_id].assemblage)
			else:
				return_data = diversity_network[downstream_id].assemblage
		else:
			if huc_id not in diversity_network:
				return empty  # check if it exists, and return an empty list if it doesn't to signify unknown or none - this way, we don't run up into a "NoneType has no attribute __iter__" later
			if func_args and len(func_args) > 1 and func_args[1] == "count":
				return len(diversity_network[huc_id].assemblage)
			else:
				return_data = diversity_network[huc_id].assemblage
	except IndexError:
		# not sure why we're doing this on error handling
		return diversity_network[huc_id].assemblage

	if func_args and len(func_args) > 2 and func_args[2] == "FID":
		return return_data
	else:
		return diversity_assemblage_to_cname(return_data)


def _subfunction_convert_species(zones_layer, db_cursor, args, parent_layer):
	'''an assemblage based function. If you pass in a query to the function_arg that returns an assemblage in pisces codes, this will convert them to common names first'''
	# args[0] contains the function_arg object
	#args[1] contains the bind variable (the huc)
	#args[2] contains all of the args to postprocess_zones

	query = args[0].argument[0]

	results = db_cursor.execute(query, args[1])
	species = []
	for row in results:
		species.append(row.col_value)
	return str(diversity_assemblage_to_cname(species))