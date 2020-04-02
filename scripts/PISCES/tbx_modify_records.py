from __future__ import absolute_import, division, print_function

import os
import sys
import re

import arcpy

from PISCES import local_vars
from PISCES import log
from PISCES import funcs
from PISCES import api
from PISCES import script_tool_funcs

'''This script is meant to be run only as an ArcGIS script tool - messages will be passed out using arcpy'''
'''This is the primary toolbox function from before they were prefixed with tbx_ - it handles modifications of records directly from within ArcGIS'''


print("This script should only be run as an ArcGIS script tool. If you can see this message, you should exit or you better know what you are doing")

local_vars.start(arc_script=1)

local_vars.config_metadata = False  # don't generate metadata for maps when they have it enabled

# general
layer = arcpy.GetParameterAsText(0)
species = arcpy.GetParameterAsText(1)
operation = arcpy.GetParameterAsText(2)  # add, remove, transfer
new_species = arcpy.GetParameterAsText(3)
reason_message = arcpy.GetParameterAsText(4)
where_string = arcpy.GetParameterAsText(5)

# for adding new records
default_input_filter = arcpy.GetParameterAsText(6)
default_observation_set = arcpy.GetParameterAsText(7)

observation_types = arcpy.GetParameterAsText(9)
update_range = arcpy.GetParameter(10)

# do a sanity check
if arcpy.GetCount_management(layer).getOutput(0) == arcpy.GetCount_management(local_vars.HUCS).getOutput(0):  # if we have all of the HUCs selected
	arcpy.AddError("Whoa - are you trying to destroy a whole species here? You selected the whole state! (Check to make sure that the HUC12 layer you selected in the tool is the one with the selection for modifications). Since it was probably an error, we're going to just exit the program right now. If you intended to run that operation, do us a favor and select all of the polygons, then deselect just one so we know you are in your right mind. Then try again.")
	sys.exit()

if default_input_filter is None:  # if one wasn't specified
	default_input_filter = "CWS"
else:
	default_input_filter = script_tool_funcs.parse_input_filter_picker(default_input_filter)[1]  # a tuple is returned. We want the part with the filter code to align with the existing code in this tool

if species is None and new_species is None:
	log.error("No species to work on, exiting")
	sys.exit()

observation_types = script_tool_funcs.obs_type_selection_box_to_list(observation_types)

if len(observation_types) == 0 and operation == "Add":
	arcpy.AddError("No Observation Type set for addition. Please select at least one observation type")
	sys.exit()


species_in = species
species = funcs.parse_input_species_from_list(species)

new_species_in = new_species
if len(new_species) > 0:
	new_species = funcs.parse_input_species_from_list(new_species)

log.write("Making changes to species %s" % species)
	
db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "Connecting to database to modify HUC data")


def get_zones(layer, zones_array, column):
	
	dataset = arcpy.SearchCursor(layer)
	for row in dataset:
		zones_array.append(row.getValue(column))  # append the zones id to the array


def get_obs_set_id():

	select_string = "select Set_ID from Observation_Sets where Input_Filter = ?"  # will select the first one
	results = db_cursor.execute(select_string, default_input_filter)
	
	for row in results:  # return the first one we get
		return row.set_id


def get_defaults():
	if default_observation_set == "auto" or default_observation_set is None:
		set_id = get_obs_set_id()

	select_string = "select ifm.objectid, ifm.default_observation_type, ifm.default_certainty from defs_if_methods as ifm, defs_input_filters as dif where ifm.input_filter = dif.objectid and dif.code = ?"
	results = db_cursor.execute(select_string, str(default_input_filter))
	
	for row in results:
		return set_id, row.default_certainty, row.default_observation_type, row.objectid


def new_records(zones, obs_types):  # to be used for adding entirely new records to the database

	set_id, certainty, presence_type, if_method = get_defaults()
	
	import datetime
	l_date = datetime.datetime.now()
	l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year, l_date.month, l_date.day, l_date.hour, l_date.minute, l_date.second)
		
	insert_string = "insert into observations (set_id,species_id,zone_id,presence_type,if_method,certainty,observation_date, date_added, notes) values (?,?,?,?,?,?,?,?,?)"

	for zone in zones:
		for pres_type in obs_types:
			db_cursor.execute(insert_string, set_id, species, zone, pres_type, if_method, certainty, l_date_string, l_date_string, reason_message)

			# The following were a temporary hack as a result of database inconsistencies during the migration from access to sqlite
			#id_value = db_cursor.execute("select last_insert_rowid() as recordid").fetchone().recordid
			#db_cursor.execute("update observations set geodb_oid=%s, objectid=%s where OGC_FID=%s" % (id_value, id_value, id_value))

	# I think the following lines duplicate functionality further down in modify_records where transactions are added.
	#transaction_string = "insert into transactions (fid,species_in,fid_to,species_to,operation,input_filter,message,subset,result) values (?,?,?,?,?,?,?,?,?)"
	#db_cursor.execute(transaction_string, species, species_in, new_species, new_species_in, operation, default_input_filter, reason_message, where_string, "success")


def modify_records(zones):

	# save the transaction
	transaction_string = "insert into transactions (fid, species_in, fid_to, species_to,operation,input_filter,message,subset,result) values (?,?,?,?,?,?,?,?,?)"
	db_cursor.execute(transaction_string, species, species_in, new_species, new_species_in, operation, default_input_filter, reason_message, where_string, "failed")

	# get the ID to attach to the records
	transaction_id = funcs.get_last_insert_id(db_cursor)

	for zone in zones:
		
		w_clause = "Species_ID = ? and Zone_ID = ?"
				
		if where_string:
			w_clause = "%s and %s" % (w_clause, where_string)

		invalidate_records(w_clause, species, zone, transaction_id)
		
		if operation == "Remove":  # if we're not moving it, then delete the records
			delete_string = "delete from observations where %s" % w_clause
			db_cursor.execute(delete_string, species, zone)
		elif operation == "Transfer":  # we have a fish to move to
			update_string = "update observations set species_id = ? where %s" % w_clause
			db_cursor.execute(update_string, new_species, species, zone)
		else:
			arcpy.AddError("Specified operation: %s - however, the other parameters specified are insufficient to complete that operation" % operation)
			sys.exit()

		# we made it through, set the result to success
		db_cursor.execute("update transactions set result='success' where id=?", transaction_id)


def invalidate_records(w_clause, species, zone, transaction_id):
	"""
		Copies records over from observations to invalid_observations that match the specified where clause, species code, and huc 12 ID.
	:param w_clause: a where clause for SQL - should include parameter markers for species and zone_ID columns to be passed in
	:param species: A PISCES species code to filter the records to
	:param zone: HUC 12 ID, as used in PISCES - used to filter the species
	:param transaction_id: the transaction ID to associate the records with
	:return:
	"""
	# move the records over to Invalid_Observations

	if w_clause == "":  # if it's empty:
		raise local_vars.DataStorageError("Can't invalidate records without a where clause - are you trying to nuke the whole database???")

	select_string = "select * from observations where %s" % w_clause
	records = db_cursor.execute(select_string, species, zone)
	l_cursor = db_conn.cursor()
	
	insert_string = "insert into invalid_observations (objectid, set_id, species_id, zone_id, presence_type, if_method, certainty, longitude, latitude, survey_method, notes, observation_date, other_data, invalid_notes, transaction_id) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
	
	for record in records:
		l_cursor.execute(insert_string, record.objectid, record.set_id, record.species_id, record.zone_id, record.presence_type, record.if_method, record.certainty, record.longitude, record.latitude, record.survey_method, record.notes, record.observation_date, record.other_data, reason_message, transaction_id)
	
	# close the subcursor
	l_cursor.close()


def modify_range(l_layer, l_species, l_operation, l_new_species, l_reason_message, l_where_string, l_input_filter, l_observation_set, l_observation_types, l_update_range):
	"""
		WARNING: Doesn't work yet because this whole script uses damn globals.
	:param l_layer:
	:param l_species:
	:param l_operation:
	:param l_new_species:
	:param l_reason_message:
	:param l_where_string:
	:param l_input_filter:
	:param l_observation_set:
	:param l_observation_types:
	:param l_update_range:
	:return:
	"""
	# open the database connection
	log.write("Getting Zones")
	zones = []
	get_zones(l_layer, zones, "HUC_12")  # fills the zones array with the zones to work with

	if operation == "Add":  # if we have a species, but not a current one, then we're adding new records
		new_records(zones, observation_types)
	else:  # otherwise, we're modifying existing records
		modify_records(zones)  # handles records whether they are being modified or deleted entirely

	db_conn.commit()
	log.write("Completed modifications", 1)

	if l_update_range is True:
		log.write("Generating new layer", 1)
		new_layer = api.get_query_as_layer("select distinct Zone_ID from Observations where Species_ID = '%s' And Presence_Type = 3" % l_species)
		if new_layer:
			params = arcpy.GetParameterInfo()
			params[8].symbology = os.path.join(local_vars.internal_workspace, "mxds", "base", "gen_3.lyr")
			arcpy.SetParameterAsText(8, new_layer)

		# close the database connection
		funcs.db_close(db_cursor, db_conn)


if script_tool_funcs.is_in_arcgis():
	arcmap_layers, running_in_arcmap = script_tool_funcs.deactivate_map("CURRENT")

	try:
		modify_range(layer, species, operation, new_species, reason_message, where_string, default_input_filter, default_observation_set, observation_types, update_range)

	finally:
		script_tool_funcs.reactivate_map("CURRENT", arcmap_layers, running_in_arcmap)
