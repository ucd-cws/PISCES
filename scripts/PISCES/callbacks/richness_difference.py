import logging

import arcpy

from .. import local_vars
from common import add_field, postprocess_zones, function_arg, _compose_simple_query, get_arg, start_query_parts

log = logging.getLogger("PISCES.callbacks")

def richness_difference(zones_layer, db_cursor, args, parent_layer):
	"""
		A callback that runs a number of different richness metrics (and obtains assemblages) for species groups.
		Takes a species group, collections to consider current, current observation types, and historic observation types
		as potential call back arguments and provides multiple richness types and current-historic differencing fields
		as an output.

		TODO: Splitting this function out into many pieces to make it easier to modify parts without worrying about the
		others as much. Trying to refactor so that it uses the new group by syntax instead of the old per-zone syntax
		tp speed up generation, especially across the network
	:param zones_layer:
	:param db_cursor:
	:param args:
	:param parent_layer:
	:return:
	"""

	log.debug("Running Richness Difference")

	group_name = get_arg(args, 0, "Native_Fish")
	observations_limit = get_arg(args, 1, local_vars.hq_collections)  # tuple of one and three represents the defaultobservation sets we're interested in
	obs_cur = get_arg(args, 2, local_vars.current_obs_types)
	obs_hist = get_arg(args, 3, local_vars.historic_obs_types)

	sql_tables, where_clauses = start_query_parts(args)

	run_losses = get_arg(args, 4, True)

	# set up grouped queries first

	current_field = "current_richness_{}".format(group_name)
	t_layer = richness_for_group(sql_tables=sql_tables,
									where_clauses=where_clauses,
									presence_types=obs_cur,
									field_name=current_field,
									zones_layer=zones_layer,
									db_cursor=db_cursor,
									parent_layer=parent_layer,
								)
	historic_field = "historic_richness_{}".format(group_name)
	t_layer = richness_for_group(sql_tables=sql_tables,
									where_clauses=where_clauses,
									presence_types=obs_hist,
									field_name=historic_field,
									zones_layer=t_layer,
									db_cursor=db_cursor,
									parent_layer=parent_layer,
								)

	# adds the current/historic assemblages and the lists and counts of losses and gains in as six fields with one DB call
	get_counts_and_assemblages(t_layer, sql_tables, where_clauses, obs_hist, obs_cur, group_name, db_cursor)

	# add the difference field
	field_name = "richness_difference_{0:s}".format(group_name)
	arcpy.AddField_management(t_layer, field_name, "LONG")
	arcpy.CalculateField_management(t_layer, field_name, "!{}! - !{}!".format(current_field, historic_field), expression_type="PYTHON_9.3")

	return t_layer


def richness_for_group(sql_tables, where_clauses, presence_types, field_name, zones_layer, db_cursor, parent_layer,
						query_base="SELECT zone_id, count(*) AS col_value FROM (SELECT DISTINCT observations.species_id, observations.zone_id FROM ",
						query_suffix=") GROUP BY Zone_ID COLLATE NOCASE",):

	where_clauses = list(where_clauses)  # copy the list so modifications will be local to this function
	where_clauses.append("observations.presence_type in ({})".format(presence_types))
	sql_query = _compose_simple_query(query_base, sql_tables, where_clauses) + query_suffix  # close the subquery

	log.debug("Richness query is %s" % sql_query)
	args = [sql_query, field_name, "LONG"]
	t_layer = add_field(zones_layer, db_cursor, args, parent_layer)

	# using this method, some values will come back null, which tanks the richness difference calculation (null - 2 = null). Set those nulls to 0
	arcpy.CalculateField_management(t_layer, field_name, "0 if !{}! is None else !{}!".format(field_name, field_name), "PYTHON_9.3")

	return t_layer


def species_list_to_string(species_list):
	return ", ".join([local_vars.all_fish[fish].species for fish in species_list])


def get_counts_and_assemblages(layer, sql_tables, where_clauses, historic_presence_types, current_presence_types, group_name, db_cursor):
	"""
		read queries into a dictionary with two subkeys (current, historic) each storing the appropriate assemblage
		then use that for both counts, extirpations, gains, and assemblages. Not for use as a direct callback - use
		richness_difference. Should probably be prefixed with an underscore - not today.
	:return:
	"""

	log.info("Getting Counts and Assemblages")
	# Retrieve the data from the database and store in dictionary keyed by huc, then by current/historic, then a list with species codes
	result_data = get_species_in_hucs(sql_tables, where_clauses, current_presence_types, "current", {}, db_cursor)
	result_data = get_species_in_hucs(sql_tables, where_clauses, historic_presence_types, "historic", result_data, db_cursor)

	# do calculations
	for key in result_data:  # each key is a HUC ID
		# first make lists of the gained and lost species
		result_data[key]["gains"] = list(frozenset(result_data[key]["current"]) - frozenset(result_data[key]["historic"]))
		result_data[key]["losses"] = list(frozenset(result_data[key]["historic"]) - frozenset(result_data[key]["current"]))

		# then make the common name versions that will be actually added as attributes, including joining the lists as strings
		result_data[key]["gains_common"] = species_list_to_string(result_data[key]["gains"])
		result_data[key]["losses_common"] = species_list_to_string(result_data[key]["losses"])

		result_data[key]["current_common"] = species_list_to_string(result_data[key]["current"])  # make common name lists of the assemblages
		result_data[key]["historic_common"] = species_list_to_string(result_data[key]["historic"])  # make common name lists of the historic assemblage

	# add fields
	current_assemblage_field = "current_assemblage_{0:s}".format(group_name)
	historic_assemblage_field = "historic_assemblage_{0:s}".format(group_name)
	losses_field = "losses_{0:s}".format(group_name)
	gains_field = "gains_{0:s}".format(group_name)
	losses_list_field = "losses_list_{0:s}".format(group_name)
	gains_list_field = "gains_list_{0:s}".format(group_name)

	for field in (losses_field, gains_field):
		arcpy.AddField_management(layer, field, "LONG")

	for field in (current_assemblage_field, historic_assemblage_field, losses_list_field, gains_list_field):
		arcpy.AddField_management(layer, field, "TEXT", field_length=65535)

	updater = arcpy.UpdateCursor(layer)
	for record in updater:
		huc_id = record.getValue(local_vars.huc_field)
		log.debug(huc_id)
		if not huc_id in result_data:
			log.warning("Zone {} missing from result data - output may be incomplete or incorrect in this HUC. There is likely a presence_type mismatch between the query that created the mapping hucs layer and the queries being used for richness difference".format(huc_id))
			continue
		data = result_data[huc_id]  # just get the dict with the data for this record
		record.setValue(current_assemblage_field, data["current_common"])
		record.setValue(historic_assemblage_field, data["historic_common"])
		record.setValue(losses_field, len(data["losses"]))
		record.setValue(gains_field, len(data["gains"]))
		record.setValue(losses_list_field, data["losses_common"])
		record.setValue(gains_list_field, data["gains_common"])
		updater.updateRow(record)


def get_species_in_hucs(sql_tables, where_clauses, presence_types, current_historic, result_data, db_cursor):
	"""
		This should be converted to use the API at some point instead of reimplementing retrieval of species presence here.
		Also not today - we'd want to compare before and after change and can't do that today.
	:param sql_tables:
	:param where_clauses:
	:param presence_types:
	:param current_historic:
	:param result_data:
	:param db_cursor:
	:return:
	"""
	where_clauses = list(where_clauses)  # copy the list so modifications will be local to this function
	where_clauses.append("observations.presence_type in ({})".format(presence_types))
	results = db_cursor.execute(_compose_simple_query("SELECT DISTINCT observations.species_id as species_id, observations.zone_id as zone_id FROM ", sql_tables, where_clauses))

	for item in results:
		if not item.zone_id in result_data:
			result_data[item.zone_id] = {"current": [], "historic": []}
		result_data[item.zone_id][current_historic].append(item.species_id)

	return result_data

def subprocess_losses(zones_layer, db_cursor, cb_args, parent_layer):
	"""
	a subfunction for use with postprocess_zones.
	This entire function could be done in a single query, but Access won't run it. So...here we are.
	#cb_args[0] contains the function_arg object
	#cb_args[1] contains the bind variable (the huc)
	#cb_args[2] contains all of the args to postprocess_zones
	"""

	query_hist = cb_args[0].argument[0]  # the first item in args is a tuple, the second is the args originally passed to postprocess_zones
	query_current = cb_args[0].argument[1]
	order = cb_args[0].argument[2]
	in_list_form = cb_args[0].argument[3]
	if in_list_form is None:
		in_list_form = False
	query_bind = cb_args[1]

	if order not in (0, 1):  # order specifies whether we mean losses or gains
		log.error("Order parameter not correctly specified. It must be defined and it must be either 0 (historic) or 1 (current)")
		raise ValueError("Order parameter not correctly specified. It must be defined and it must be either 0 (historic) or 1 (current)")

	results = db_cursor.execute(query_hist, query_bind)
	list_hist = [item.species_id for item in results]

	results_cur = db_cursor.execute(query_current, query_bind)
	list_cur = [item.species_id for item in results_cur]

	if order == 1:  # gains
		new_set = frozenset(list_cur) - frozenset(list_hist)  # set of species only in current
	else:  # losses = 0 - can safely be written as else due to error checking up higher - faster this way too and satisfies PyCharm's error checker
		new_set = frozenset(list_hist) - frozenset(list_cur)  # set of species only in historic

	distinct_items = list(new_set)

	if in_list_form:
		common_names = []
		for item in distinct_items:
			common_names.append(local_vars.all_fish[item].species)
		return common_names
	else:
		return len(distinct_items)


def subprocess_assemblage(zones_layer, db_cursor, cb_args, parent_layer):
	'''a subfunction for use with postprocess_zones.
	This entire function could be done in a single query, but Access won't run it. So...here we are.'''
	# cb_args[0] contains the function_arg object
	#cb_args[1] contains the bind variable (the huc)
	#cb_args[2] contains all of the args to postprocess_zones

	query = cb_args[0].argument[0]  # the first item in args is a tuple, the second is the args originally passed to postprocess_zones
	query_bind = cb_args[1]
	try:
		in_list_form = cb_args[0].argument[1]
	except:
		in_list_form = True
	if in_list_form is None:
		in_list_form = True

	results = db_cursor.execute(query, query_bind)
	distinct_items = []

	for item in results:
		distinct_items.append(item.species_id)

	if in_list_form:
		common_names = []
		for item in distinct_items:
			common_names.append(local_vars.all_fish[item].species)
		return common_names
	else:
		return len(distinct_items)
