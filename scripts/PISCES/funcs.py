from __future__ import absolute_import, division, print_function

import os
import re
import traceback

import pyodbc

import arcpy

from . import local_vars
from . import log
from .local_vars import clean_location, winreg


def isiterable(item):
	"""
	tests whether an object is iterable

	not super useful, but prevents needing to remember the syntax and names
	"""
	return hasattr(item, '__iter__')


def index_toolbox_params(tool, params):
	"""
		Indexes parameters to ArcGIS Python script tools so that they can be looked up by name. May not work for getting data, but
		should at least allow reading of info.
	"""
	tool.params_index = {}
	for param in params:
		tool.params_index[param.name] = param


def db_connect(db_name, note=None, access=False):

	log_string = "Making database connection to %s" % db_name

	if note is not None:
		log_string += " - note added: %s" % note

	log.write(log_string)

	if not access:
		conn = pyodbc.connect('DRIVER=SQLite3 ODBC Driver;Database=%s' % db_name)
	else:
		conn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb)};DBQ='+db_name)

	return conn.cursor(), conn


def db_close(cursor, conn):
	log.write("Closing database connection")
	cursor.close()
	conn.close()


def refresh_cursor(database=None, connection=None, existing_cursor=None, close_connection=False):
	if not database and not connection:
		raise ValueError("at least one of connection or database parameter is required")

	if existing_cursor:  # close a cursor if we passed one in
		existing_cursor.close()

	if close_connection:  # if the user specified to close the connection
		connection.close()
		connection = None

	if not connection:  # connection takes priority over database, so use it if we have it
		cursor, connection = db_connect(database, "refreshing cursor")
		return connection, cursor

	return connection, connection.cursor()  # always returns connection, otherwise we'd leak the handle


def match_species_from_string(species_string, validate=True, return_all=False):
	"""
	Given a string, finds potential species codes within it - returning only the first match unless return_all is True. When validate is false, it returns whatever it finds, without checking to see if those codes exist. If validate is True, it will ensure all codes are valid first
	:param species_string: The string potentially containing species codes
	:param validate: when True (default), this function checks to ensure the species code exists. Otherwise, it assumes any pattern of three characters followed by two numbers is a species code. If validate is true, the data_setup function must have already been run (or equivalent) to populate local_vars.all_fish
	:param return_all: boolean. causes the function to return all matches. Returns a list.
	:return:
	"""

	l_fid_match = re.findall("(\w{3}\d{2})", species_string)
	if len(l_fid_match) == 0:  # if no groups matched - retur
		return None

	# this uses some rather terrible branching...but this code is also hardly used right now
	if validate and local_vars.all_fish is not None:
		species_codes = []  # container to store validated codes
		for match in l_fid_match:  # for all of the matched codes
			if match.upper() in local_vars.all_fish:  # check if that species code exists - make sure to uppercase it for the match - it's possible that a lowercase value was passed in.
				if return_all:  # if we want to return all codes matched, save a valid code in the species_codes list
					species_codes.append(match)
				else:  # otherwise, just return the first match
					return match
		else:  # if we don't return during the for loop
			if return_all:
				return species_codes  # returns a list - whether empty or full
			return None  # otherwise, explicitly return None
	elif validate and local_vars.all_fish is None:
		raise ValueError("Can't validate unless all_fish is initialized. Function match_species_from_string cannot be run with validate flag unless PISCES is running fully. Either setup the PISCES data or set validate=False when calling this function (not recommended)")
	elif not validate:
		if return_all:
			return l_fid_match  # returns a list
		# otherwise, return the individual match, whatever it is
		return l_fid_match[0]  # we just return the first item of the array since we're always doing a findall now


def create_collection(name, short_name, description, db_cursor):
	query = "insert into defs_collections (collection_name, short_name, description) values ('%s', '%s', ?)" % (name, short_name)
	db_cursor.execute(query, description)

	return get_last_insert_id(db_cursor)


def get_last_insert_id(db_cursor, access=False):
	"""
	A shortcut function to return the ID of the last insert operation.
	:param db_cursor: The pyodbc cursor that the insert occurred on.
	:return: integer ID of last record
	"""
	if access:
		l_query = "select @@IDENTITY as id_value"
	else:
		l_query = "select last_insert_rowid() as id_value"
	l_identity = db_cursor.execute(l_query).fetchone()
	return l_identity.id_value


def query_to_list_of_dicts(query, db_cursor, drop_fields=None):

	records = []

	results = db_cursor.execute(query)
	fields = [t[0] for t in db_cursor.description]  # from the pyodbc website, a way to get all the fields from a cursor

	for result in results:
		record = {}
		for field in fields:
			if drop_fields and field in drop_fields:  # if we're supposed to drop the pkeys, and this field was identified as a pkey above
				continue  # go to the next iteration

			record[str(field).lower()] = result.__getattribute__(field)  # using field for both keys because we wrote them as "as" statements in the querhy
		records.append(record)

	return records


def data_stats(db_cursor, print_to_screen=True, name_col="Parameter", value_col="Value"):

	print("\nCalculating data stats")

	l_queries = {}
	l_queries['Total Number of Valid and Active Observations'] = "select Count (*) as num from observations"
	l_queries['Total Number of Datasets Included'] = "select Count(*) as num from (select distinct set_id from Observations)"  # we use this method of gathering this because some sets have been completely tossed.
	l_queries['Total Number of Species tracked (including data bins and nonfish taxa)'] = "select Count (*) as num from species"
	l_queries['Total Number of Species tracked (no data bins, but includes nonfish)'] = "select Count (*) as num from Species where Temporary != 1"
	l_queries['Total Number of Fish Species tracked (no data bins)'] = "select Count (*) as num from all_fish where Temporary != 1"
	l_queries['Total Number of Native Fish Species tracked (no data bins)'] = "select Count (*) as num from native_fish where Temporary != 1"
	l_queries['Total Number of Non-Native Fish Species tracked (no data bins)'] = "select Count (*) as num from nonnative_fish where Temporary != 1"
	l_queries['Total Number of Valid Obervations in the Quality Controlled Set (%s)' % local_vars.hq_collections] = "select Count (*) as num from observation_collections where Collection_ID in (%s)" % local_vars.hq_collections
	l_queries['Total Number of Taxa (Including NonFish) with Data'] = "select Count(*) as num from (select distinct Species_ID from Observations)"
	l_queries['Total Number of *Native* Fish Species with Data'] = "select Count(*) as num from (select distinct Observations.Species_ID from Observations, native_fish where Observations.Species_ID = native_fish.fid)"
	l_queries['Total Number of Fish Species with Present QC Data'] = 'select count(*) as num from (select distinct all_fish.fid from observations, all_fish, observation_collections where observations.species_id = all_fish.fid and observations.presence_type in (%s) and observations.objectid = observation_collections.observation_id and observation_collections.collection_id in (%s));' % (local_vars.current_obs_types, local_vars.hq_collections)
	l_queries['Total Number of Fish Species with Historic QC Data'] = 'select count(*) as num from (select distinct all_fish.fid from observations, all_fish, observation_collections where observations.species_id = all_fish.fid and observations.presence_type in (%s) and observations.objectid = observation_collections.observation_id and observation_collections.collection_id in (%s));' % (local_vars.historic_obs_types, local_vars.hq_collections)

	values = []
	for name in l_queries.keys():
		results = db_cursor.execute(l_queries[name])
		for result in results:
			values.append({name_col: name, value_col: result.num})  # add it to the dict
			log.write("%s: %s" % (name, result.num), print_to_screen)

	return values

	# pop the info for each fish into a numpy array (numpy.array([0,1,2...]) and then print out numpy.sum() numpy.std() numpy.mean() for the natives


#switch the workspace back


def clean_workspace(softerror=False):  # gets a list of all of the feature classes in the workspace and removes them all

	log.write("Cleaning workspaces", True)

	try:
		clean_location(local_vars.workspace, "FGDB")
		clean_location(local_vars.calcs_mdb, "PGDB")
		clean_location(local_vars.temp, "Folder")
	except:
		if softerror:  # we may want to plow through errors (like when building the installer
			log.write("Unable to clean workspace - traceback: %s" % (traceback.format_exc()), True)
			log.write("Proceeding anyway due to softerror flag", True)
		else:
			raise


def is_between(check_num, num1, num2): # checks whether check_num is between num1 and num2 without assumptions of the sign of num1 or num2 since a max in ArcGIS could be in a different quadrant from the min

	if num2 < check_num < num1:
		return True
	if num2 > check_num > num1:
		return True

	return False


def get_path():

	"""
	Obtains the PISCES install path from the windows system registry - used for scripts running in ArcGIS where
	the current working directory isn't the PISCES install path.

	:return: str base_folder
	:raise: WindowsError on failure to retrive info from the registry
	"""
	try:
		registry = winreg.ConnectRegistry("", winreg.HKEY_LOCAL_MACHINE)  # open the registry
		base_folder = winreg.QueryValue(registry, "Software\CWS\PISCES\location")  # get the PISCES location
		winreg.CloseKey(registry)
	except:
		raise WindowsError("Unable to get base folder")

	return base_folder


def text_to_species_list(text_input, multispecies_first=True, warn=False):
	"""
		TODO: Write Unit Tests!
		Given a string or a list of mixed species groups and codes, figures out whether it's a species or group and returns the species code. Accepts species codes, our ArcGIS tool format, and group names.
		If the string is a comma or semicolon separated list of such strings or groups, it splits and determines the species codes for all items involved.
	:param text_input: The string to parse for species. Optionally a list of strings (species codes or groups as well). If it's a list, it will expand groups
	:param multispecies_first:  indicates the order to run the splits and tests in. If you know you're passing in a comma/semicolon separated list of species, leave this as True. If it's a single, or you really know what you're doing, you can set it to False
	:return:
	"""

	if not local_vars.data_setup_run:
		local_vars.data_setup()

	if isiterable(text_input):
		temp_items = text_input
	else:
		text_input = str(text_input)

		temp_items = []
		if text_input.find(",") > 0:
			temp_items = text_input.split(",")
		elif text_input.find(";") > 0:
			temp_items = text_input.split(";")

	# Check if it's a comma or ; separated list of items. Split and validate each item is a fish, then return
	if multispecies_first and len(temp_items) > 0:
		return _text_to_species_list_multi(temp_items)

	# Check if it's just a fish - return it as a list
	if text_input in local_vars.all_fish:
		return [text_input]

	possible_species = parse_input_species_from_list(text_input)
	if possible_species is not None:
		return possible_species

	# Ok, maybe then it's a group - try it first as the full group name
	group_species = species_group_as_list(text_input)
	if group_species:
		return group_species

	# then try it as the short_name
	group_species = species_group_as_list(short_name=text_input, warn=warn)
	if group_species:
		return group_species

	# if we're still here, then what was passed in was NOT a single group and not a single fish, and if we didn't already check the multi-species option, then do it now
	if not multispecies_first and len(temp_items) > 0:  # don't technically need the condition, but it will speed up some other situations
		return _text_to_species_list_multi(temp_items)

	# still here? We've got nothing. Return [] - still valid for many of these items, and won't raise an error. Let them check themselves
	if warn:
		log.error("Text contains no reference to species")
	return []


def _text_to_species_list_multi(temp_items):
	"""
		Parses text to a species list for a multi species list. We made this a function because we want to run this at different positions of the calling function
	:param temp_items: the individual items to parse
	:return:
	"""
	final_list = []
	if len(temp_items) > 0:
		for item in temp_items:
			# is it a fish?
			if item in local_vars.all_fish:
				final_list.append(item)
			else:
				# maybe it's a group
				t_group = text_to_species_list(item, multispecies_first=False)  # maybe it's a group or sort of string - we could also just try the two group checks again - setting multispecies_first=False is just a guess at what will be fastest
				if len(t_group) > 0:
					final_list += t_group
		return list(set(final_list))  # it could be empty - dedupe too

	return []


def species_group_as_list(group_name=None, short_name=None, db_cursor=None, warn=False):

	if group_name:
		select_group_id = "select id from defs_species_groups where group_name='%s'" % group_name
	elif short_name:
		select_group_id = "select id from defs_species_groups where short_name='%s'" % short_name
	else:
		if warn:
			log.error("No group specified")
		return None

	created_cursor = False
	if not db_cursor:
		created_cursor = True
		db_cursor, db_conn = db_connect(local_vars.maindb)

	result = db_cursor.execute(select_group_id)
	id_row = result.fetchone()
	try:
		group_id = id_row.id
	except:
		return None

	del id_row, result

	if not group_id:
		return None

	group_query = "select fid from species_groups where group_id = ?"
	results = db_cursor.execute(group_query, group_id)

	species = []
	for row in results:
		species.append(row.fid)

	if created_cursor:
		db_close(db_cursor, db_conn)

	return species


def hucs_to_list(dataset):

	'''takes an arcgis dataset containing a field with "HUC_12" in it and transforms the unique values in that field into a list'''

	# check that we have a dataset
	if not dataset:
		log.error("No HUCs to process")
		return False

	# and check that it has a huc field
	desc = arcpy.Describe(dataset)
	for field in desc.fields:
		# probably better done with a lambda
		if local_vars.huc_field == field.name:
			break
	else: 
		log.error("dataset has no HUC_12 field - can't process")
		return False

	# cleanup
	del desc

	huc_list = []

	# get the list
	huc_cursor = arcpy.SearchCursor(dataset)
	for row in huc_cursor:
		huc_list.append(row.getValue(local_vars.huc_field))

	# dedupe it on the way out
	return list(set(huc_list))


def refresh_layer_cache(l_db_cursor=None):
	"""
		deletes the existing layer cache and recreates it
		:param layer_cache_location: relative path to layer cache
	"""

	if not l_db_cursor:
		l_db_cursor, l_db_conn = db_connect(local_vars.maindb, "Cleaning Layer Cache")

	layer_cache = local_vars.layer_cache

	log.write("Deleting layer cache - will recreate", 1)

	if os.path.exists(layer_cache):  # if it currently exists
		arcpy.Delete_management(layer_cache)

	arcpy.CreateFileGDB_management(os.path.split(layer_cache)[0], os.path.split(layer_cache)[1], "CURRENT")

	query = "delete from Layer_Cache"  # delete the records too!
	l_db_cursor.execute(query)

	if l_db_conn:
		l_db_cursor.close()
		l_db_conn.close()


def get_species_in_dataset(dataset_id, db_cursor):
	query = "select distinct species_id from observations, observation_collections where observations.objectid = observation_collections.observation_id and observation_collections.collection_id = %s" % dataset_id
	results = db_cursor.execute(query)

	species_list = []
	for record in results:
		species_list.append(record.species_id)

	return species_list

def run_query(query):
	"""
		A simple helper function that helps run a query with less fuss
	"""

	db_cursor, db_conn = db_connect(local_vars.maindb, "run_query")

	return db_cursor, db_conn, db_cursor.execute(query)


def fully_qualified_path(relative_item):
	"""
		takes a path relative to the PISCES root and returns its full path. Somewhat trivial, but complicated when the
		fully PISCES code isn't running. Does no validation of inputs to ensure it's a true path
	"""

	if not local_vars.internal_workspace:
		local_vars.set_workspace_vars()  # run the first setup if this code hasn't been run yet

	return os.path.join(local_vars.internal_workspace, local_vars.relative_item)



def change_config_item(regex, value, fiu):
	"""
		Changes a single value in the config.py
	:param regex:
	:param value:
	:return:
	"""
	pass


def parse_input_species_from_list(l_search_species):
	"""
	takes a species from an ArcGIS 10 Script tool dropdown in the form of "Code - Common Name" and parses out the code and returns it
	:param str l_search_species: species listing from script tool
	:return: str FID
	"""
	species_re = re.search("^'?(\w{3}\d{2})", l_search_species)
	try:
		return species_re.group(1)
	except:
		return None  # if it didn't work, we probably don't have a species


def parse_multi_species_group_list(l_species_and_groups):
	"""

	:param l_species_and_groups:
	:return:
	"""
	listing = l_species_and_groups.split(";")
	new_listing = []
	for item in listing:
		if "-" in item:  # if we have a separator - this is clunky, but the best way
							#  I can think of since we're parsing species and groups
			new_item = parse_input_species_from_list(item)
		else:
			#if isiterable(item) and type(item) is not str and type(item) is not unicode:  # basically, do we have some kind of list like thing
			#	#for individual in item:  # we need to expand this out - it's likely then th
			if local_vars.debug:
				log.write("Getting species group!", True)
			new_item = text_to_species_list(item)

		if item != '':  # we might get some empty items from the split
			if type(new_item) is list:  # basically, if we got a group back from text_to_species_list
				new_listing.extend(new_item)
			else:
				new_listing.append(new_item)

	return new_listing


def generate_layer_name(bind_var, query_id, map_layer_object):

	if map_layer_object and map_layer_object.custom_query.name_formula and map_layer_object.parent_map:
		#log.warning("going to replace")
		# use the formula given, but it has to be part of a map in order to use the parent methods and replacements
		out_layer_name = "{}_{}".format(map_layer_object.parent_map.replace_variables(map_layer_object.custom_query.name_formula, fill_spaces=True), query_id)

	elif bind_var is None:
		#log.warning("No bind variable")
		out_layer_name = "layer_q" + str(query_id)
		bind_var = "NULL"
		out_layer_name = arcpy.CreateUniqueName(out_layer_name, local_vars.layer_cache)

	else:
		#log.warning("backup plan")
		out_layer_name = "f_%s_%s" % (bind_var, query_id)  # can't start with a digit

	out_layer_name = out_layer_name.replace("-", "_")  # replacement variables might introduce hyphens - make them safe again
	full_layer_path = os.path.join(local_vars.layer_cache, out_layer_name)  # set the full path to the layer on disk
	return bind_var, full_layer_path, out_layer_name

