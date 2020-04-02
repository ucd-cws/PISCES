"""
	This module contains a suite of functions relevant to the loading and running of the ArcGIS Toolbox tools for PISCES.
	While these tools may use functions in the broader set of PISCES code, this code tends to be specific to cross-tool
	needs within the PISCES toolbox. Examples would be code to set up and process the species and groups control,
	code that loads and sets up the observation types picker control, etc.
"""


import os
import sys
import re
import csv
from datetime import datetime
import shutil

import arcpy
import input_filters.common

from sqlalchemy.exc import OperationalError

import local_vars
import funcs
import log
import orm_models
import mapping

from funcs import index_toolbox_params as index_params


class Filter_Tool_Template(object):
	"""
		The Filter_Tool_Template class was meant to be a first crack at a common suite of code for a 10.1 and above compatible
		Python toolbox for PISCES. Due to time constraints, we haven't migrated the PISCES code to a pure Python toolbox,
		but this code would be the initial suite of code that reduces redundancy and sets up its own tools when they have
		species pickers, etc. Still not fully functional, and needs work, but worth keeping for future development.
	"""
	def __init__(self):
		"""Define the tool (tool name is the name of the class)."""
		self.label = "Get Species List from HUCs"
		self.description = ""
		self.canRunInBackground = False
		self.blank = ""
		self.params_index = {}

	def filter_params(self):
		"""Define parameter definitions"""
		hucs_layer = arcpy.Parameter(name="hucs_layer",
									 displayName="Selected HUC12s",
									 direction="input",
									 parameterType="required",
									 enabled=True,
									 multiValue=False,
									 datatype="GPFeatureLayer")

		limit_to = arcpy.Parameter(name="limit_to",
									 displayName="Limit to these taxa or groups",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=False,
									 datatype="GPString")

		limit_to_holder = arcpy.Parameter(name="limit_to_holder",
									displayName="Limit holder",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=True,
									 datatype="GPString")

		datasets = arcpy.Parameter(name="datasets",
									 displayName="Limit to these datasets within PISCES",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=False,
									 datatype="GPString")

		datasets_holder = arcpy.Parameter(name="datasets_holder",
									displayName="Dataset limit holder",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=True,
									 datatype="GPString")
		datasets_holder.value = "Best available knowledge 8/2013;Non native QC 12/12/13"
		datasets_holder.category = "Advanced Options"

		params = [hucs_layer, limit_to, limit_to_holder, datasets, datasets_holder]
		toolbox.index_params(self, params)

		make_species_group_picker(self, limit_to, limit_to_holder, objects_passed=True)
		return params

	def isLicensed(self):
		"""Set whether tool is licensed to execute."""
		return True

	def updateParameters(self, parameters):
		"""Modify the values and properties of parameters before internal
		validation is performed.  This method is called whenever a parameter
		has been changed."""

		add_selection(self, parameters[1], parameters[2], objects_passed=True)

	def updateMessages(self, parameters):
		"""Modify the messages created by internal validation for each tool
		parameter.  This method is called after internal validation."""
		return

	def execute(self, parameters, messages):
		"""The source code of the tool."""
		return


def get_location():
	"""
		This function is required primarily for script tools, but can be useful in other contexts too (it's embedded in
		the code to set up workspaces as well.) For ArcGIS script tools, scripts run with no current working directory,
		so determining where the PISCES data is requires a global way to look it up. This function provides that by looking
		up the registry key Software\CWS\PISCES\location (note that on 64 bit computers running 32 bit Python, the
		key is at Software\Wow6432Node\CWS\PISCES\location. This key contains the absolute path of the root PISCES folder.
		This function then checks to see if the current running copy of PISCES already knows where that base folder is,
		and if it doesn't sets up the PISCES workspace (local_vars.set_workspace_vars()) with the retrieved value before
		returning the value to the caller.
	:return:
	"""
	try:
		import _winreg
		registry = _winreg.ConnectRegistry("", _winreg.HKEY_LOCAL_MACHINE)  # open the registry
		base_folder = _winreg.QueryValue(registry, "Software\CWS\PISCES\location")  # get the PISCES location
		_winreg.CloseKey(registry)
	except:
		log.error("Unable to get base folder")
		sys.exit()

	if local_vars.internal_workspace != base_folder:  # essentially, if we haven't already run this
		local_vars.set_workspace_vars(base_folder)  # set up the workspace to the location

	return base_folder


def is_in_arcgis(arcmap_only=False):
	"""
		For purposes of testing, we need to sometimes check whether or not a tool is being run by ArcGIS or standalone.
		Allows script tools to return items to the table of contents unless we are running unit tests outside of ArcMap.

		:param arcmap_only: boolean. Default is False. When set to true, only detects whether the interpreter is running
		in arcmap, otherwise, ArcCatalog is allowed as part of the test as well. Will likely need updating for ArcGIS
		Professional code.
	"""
	if "ArcMap" in sys.executable:
		return True
	elif not arcmap_only and "ArcCatalog" in sys.executable:
		return True
	else:
		return False


def deactivate_map(document="CURRENT"):
	"""
		A wrapper around turn_off_all_layers that dots our Is and crosses our Ts - makes sure that we check if we're running in ArcMap or not, etc
	:param document: path of map document to operate on, or the keyword "CURRENT" as used in arcpy.mapping
	:return: 2 items. dict index of visible layers, and a boolean value indicating whether the code is running within arcmap (ie, whether CURRENT is valid, if it was tried
	"""

	try:
		log.write("Turning off map layers to speed up processing - they'll be turned on when work is complete", True)
		mydocument = arcpy.mapping.MapDocument(document)
		visible_layers_index = turn_off_all_layers(document)
		running_as_arcmap_tool = True
		del mydocument
	except RuntimeError:
		log.write("Not running as arcmap tool - not turning off layers")
		running_as_arcmap_tool = False
		visible_layers_index = {}

	return visible_layers_index, running_as_arcmap_tool


def reactivate_map(document, activate_layers, running_in_arcmap):
	"""
		A wrapper around turn_on_layers that checks the output of deactivate_map to see if we need to do anything
	:param document:
	:param running_in_arcmap:
	:param activate_layers:
	:return:
	"""
	if running_in_arcmap and len(activate_layers.keys()) > 0:
		turn_on_layers(document, activate_layers)
	arcpy.RefreshActiveView()  # refresh the map document


def turn_off_all_layers(document="CURRENT"):
	"""
		A speedup function for map generation in ArcMap - turns off all layers so that it doesn't try to rerender them while we're using tools (since these tools need
		to run in the foreground and background processesing didn't seem to speed it up).

		Creates a dictionary keyed on the arcpy layer value longName which contains True or False values for whether or not the layers were enabled before running this.
		Allows us to then use turn_on_layers on the same document to reenable those layers

	:param document: a map document. defaults to "CURRENT"
	:return: dict: a dictionary keyed on layer longName values with True or False values for whether the layer was enabled.
	"""
	visiblity = {}

	doc = arcpy.mapping.MapDocument(document)
	for lyr in arcpy.mapping.ListLayers(doc):
		if lyr.visible is True:
			try:
				visiblity[lyr.longName] = True
				lyr.visible = False
			except NameError:
				visiblity[lyr.longName] = False  # if we have trouble setting it, then let's not mess with it later
		else:
			visiblity[lyr.longName] = False

	del doc
	return visiblity


def turn_on_layers(document="CURRENT", storage_dict=None, only_change_visible=True):

	if not storage_dict:
		raise ValueError("storage_dict must be defined and set to a list of layer names with values of False or True based on whether the layer should be on or off")

	doc = arcpy.mapping.MapDocument(document)
	for lyr in arcpy.mapping.ListLayers(doc):
		if lyr.longName in storage_dict:
			if not only_change_visible or (only_change_visible is True and storage_dict[lyr.longName] is True):  # if we're only supposed to set the ones we want to make visible and it is one, or if we want to set all
				try:
					lyr.visible = storage_dict[lyr.longName]  # set the visibility back to what we cached
				except NameError:
					log.warning("Couldn't turn layer %s back on - you may need to turn it on manually" % lyr.longName)  # we couldn't turn a layer back on... too bad

	del doc


def get_fish_filter(prepend=None):
	"""
		In cases where we just want the fish filter (as opposed to fish and groups), this function provides just a listing of species codes and species

	:param prepend: list of items to appear at the beginning of the picker
	:return:
	"""
	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
	get_fish = "select fid,common_name from species order by common_name asc"

	if prepend:
		l_fish = prepend
	else:
		l_fish = []

	fishies = db_cursor.execute(get_fish)
	for fish in fishies:
		l_str = "%s - %s" % (fish.fid, fish.common_name)
		l_fish.append(l_str)

	funcs.db_close(db_cursor, db_conn)
	return l_fish


def make_species_group_picker(validation_class, selector_index, storage_index, objects_passed=False, include_all=True):
	"""

	:param validation_class: the arcmap tool validation class object
	:param selector_index:
	:param storage_index:
	:param objects_passed: indicates whether or not the index values passed in are actually the objects themselves (for new-style toolboxes)
	:return:
	"""
	validation_class.selected_species = ""
	validation_class.blank = ""

	try:
		l_fish = get_fish_and_groups_filter(prepend_blank=True, sep="-----", include_all=include_all)  # add a blank item to the beginning
	except:
		l_fish = []

	if not objects_passed:
		if len(validation_class.params) > 1:  # stupid arcgis fix because it won't validate otherwise
			validation_class.params[selector_index].filter.list = l_fish
			validation_class.params[selector_index].value = validation_class.blank
	else:
		selector_index.filter.list = l_fish
		storage_index.value = validation_class.blank


def add_selection(val_class, selector_index, storage_index, objects_passed=False):

	single_species = autocomplete_full_field(val_class, selector_index, objects_passed)

	if objects_passed:
		selector_obj = selector_index
		storage_obj = storage_index
	else:
		selector_obj = val_class.params[selector_index]
		storage_obj = val_class.params[storage_index]

	# move species lookups to storage field
	if single_species:  # if we actually found a species in our autocomplete - thus can add it to the list
		val_class.selected_species = str(storage_obj.value)
		if val_class.selected_species == "None":  # starts out this way
			val_class.selected_species = selector_obj.value  # so replace it
		else:
			val_class.selected_species += ";%s" % selector_obj.value  # otherwise append it
		val_class.selected_species.replace("None;", "")  # it tends to get placed in the beginning
		storage_obj.value = val_class.selected_species  # assign the string to the field
		selector_obj.value = val_class.blank  # set the species selector to blank
	#else:  # we didn't find a species via autocomplete - but it's still possible that we manually selected a species
	#	if val_class.params[selector_index].value in val_class.params[storage_index].value:
	#		val_class.params[selector_index].value = val_class.blank # set the species selector to blank


def get_collections_filter():
	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
	get_collection = "select collection_name from defs_collections order by collection_name asc"

	l_collections = []

	collections = db_cursor.execute(get_collection)
	for collection in collections:
		l_collections.append(collection.collection_name)

	funcs.db_close(db_cursor, db_conn)
	return l_collections


def make_collections_picker(validation_class, selector_index, storage_index):
	"""

	:param validation_class: the arcmap tool validation class object
	:param selector_index:
	:param storage_index:
	:return:
	"""
	validation_class.blank = ""

	try:
		l_collections = get_collections_filter()
	except:
		l_collections = []

	validation_class.params[selector_index].filter.list = l_collections
	validation_class.params[storage_index].value = validation_class.blank


def get_groups_filter():
	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
	get_group = "select group_name from defs_species_groups order by group_name asc"

	l_group = []

	groupies = db_cursor.execute(get_group)
	for group in groupies:
		l_group.append(group.group_name)

	funcs.db_close(db_cursor, db_conn)
	return l_group


def get_fish_and_groups_filter(prepend_blank=True, sep="----", include_all=True):
	"""

	:param prepend_blank: Boolean. Adds a " " at the beginning to be selectable
	:param sep: a separator between the groups and the fish
	:return:
	"""

	return_list = []
	if prepend_blank:
		return_list.append(" ")

	if include_all:
		return_list.append("all")

	if sep and include_all:
		return_list.append(sep)

	return_list += get_groups_filter()

	if sep:  # append the separator
		return_list.append(sep)

	return_list += get_fish_filter()

	return return_list


def validate_species(field):

	if field.hasBeenValidated:
		return

	if field.value and (str(field.value.lower()) == "load" or str(field.value.lower()) == "last"):
		trans = load_transaction("last")
		field.value = trans['Species_In']


def load_transaction(l_id="last", db_cursor=None):

	opened_db = False
	if db_cursor is None:
		opened_db = True

		db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "loading transactions")

	results = None
	if l_id == "last":
		sql = "select * from transactions order by id desc"
		results = db_cursor.execute(sql)
	else:
		sql = "select * from transactions where id = ?"
		results = db_cursor.execute(sql)

	t = results.fetchone()

	transaction = {}
	if t:
		transaction['Species_In'] = t.species_in
		transaction['Message'] = t.message
		transaction['Species_To'] = t.species_to
		transaction['Operation'] = t.operation
	else:
		transaction['Species_In'] = ""
		transaction['Message'] = ""
		transaction['Species_To'] = ""
		transaction['Operation'] = ""

	if opened_db:
		funcs.db_close(db_cursor, db_conn)

	return transaction


def autocomplete_full_field(obj, field_num=1, objects_passed=False):  # given a script tool field, it will search it for what you typed to autocomplete
	"""

	:param obj: the validation object from arcgis
	:param field_num: the validator class params index of the field to autocomplete
	:param objects_passed: If True, then you can pass the actual params object (instead of the index) in the field_num parameter. When False, the index must be passed
	:return: boolean indicating whether a single, valid species is currently selected
	"""

	if objects_passed:
		field = field_num
	else:
		field = obj.params[field_num]

	min_length = 5  # set the min length for trying a subset match

	if field.hasBeenValidated:  # if this field hasn't changed since the last time we validated it
		return

	# Sanity and length checks first. If it's not None, it was probably typed - if it was perfectly typed it would be caught above, so check for partials
	if field.value is None or len(field.value) < min_length:  # if it's short, don't autoselect - not specific enough
		return False

	# check if it's already in the list - ie, we selected from the list
	for item in field.filter.list:
		if field.value == item:
			return True

	t_count = 0
	ts = None
	for species in field.filter.list:
		if str(species).lower().find(str(field.value).lower()) > -1:  # if what they typed is in this species - lowercase matching
			ts = species
			t_count += 1

	if t_count > 1:
		field.value = "%s items found..." % t_count
		return False
	if t_count == 1:
		field.value = ts
		return True


def load_map_sets(username="CWS"):
	"""
	Loads the currently available maps in the database - just the attributes Set_Name, Map_Title, and Set_Description.
	Returns a list of objects with those attributes.

	:param username: a string indicating the username to bring up maps for. Not a security issue, but a convenience issue. "CWS" shows all maps, and others may show a subset to not clutter the UI.
	:return: list of map objects, descriptive map string list
	"""

	class t_map(object):
		"""
			A light mapping object to store parts information for constructing the strings in the mapping window and for being able to check parameters.
			Not sure why we're using a separate class for it - now it could be replaced with an ORM object, in all likelihood and this code could be cut down
		"""
		def __init__(self, name, title, desc, iterator):
			self.Set_Name = name
			self.Map_Title = title
			self.Set_Description = desc
			self.string_rep = name
			self.Iterator = iterator

	db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "Loading maps")

	map_query = "select maps.set_name, maps.map_title, maps.set_description, maps.iterator from defs_query_sets as maps, map_users, users where users.name=? and users.id=map_users.user_id and maps.id=map_users.map_id  order by maps.set_name asc"

	results = db_cursor.execute(map_query, username)

	last_desc = "Runs the last map configuration that was set. If you just ran this tool it will output the same set"

	last_map = t_map("Last Map Configuration", "", last_desc, False)

	maps = [last_map, ]
	map_strings = ["Last Map Configuration", ]
	for result in results:

		l_map = t_map(result.set_name, result.map_title, result.set_description, result.iterator)

		maps.append(l_map)
		map_strings.append(l_map.string_rep)

	funcs.db_close(db_cursor, db_conn)

	return maps, map_strings


def switch_iterator_field(new_table_field, old_table_field, validation_class, picker_index, storage_index):
	"""
		When the mapping tool switches maps, the possible values to pass as arguments might change. This function
		handles the switching of those possible values and clears the existing selections when necessary and changes the
		selection list
	:param new_table_field: the table and field (such as Species_Groups:FID) to pull values from
	:param old_table_field: the current table and field in the same format (to see if it changed
	:param validation_class: the mapping tool's validation class
	:param picker_index: the index of the picker field in the params list
	:param storage_index: the index of the value storage field in the params list
	:return: None - modifications are made in place by the tool
	"""

	if new_table_field == old_table_field:
		return  # in that case, we're ok,  don't do anything

	if new_table_field == "Species_Groups:FID":  # if it's the special case, use this code
		make_species_group_picker(validation_class, picker_index, storage_index)
	else:  # otherwise, get the generic unique codes
		get_generic_filter_picker(new_table_field, validation_class, picker_index)

	validation_class.params[storage_index].values = []


def write_table_from_observation_records(observations, return_gdb_table=True):
	"""
		Given a set of PISCES orm_models.Observation instances, writes a CSV out for use in the Query HUC sources tool
	:param observations: a PISCES orm set of observations
	:param return_gdb_table: boolean: if True, returns a File Geodatabase Table. If False, returns the CSV name
	:return:
	"""

	output_csv = os.path.join(local_vars.temp, "records_%s.csv" % datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
	#output_csv = tempfile.mkstemp(prefix="records_", suffix="_%s.csv" % datetime.now().strftime("%Y_%m_%d_%H_%M_%S"), dir=local_vars.temp)[1]

	output_list = []
	try:
		for record in observations:
			output_list.append({
				"{0:s}_Double".format(local_vars.huc_field): record.zone_id,
				"Common_Name": record.species.common_name,  # we do it twice because in the CSV, we want HUC_12 to be valid. In the GDB version, we'll delete HUC_12 and recreate it with the proper data type, since I didn't see a way to do a field map for the import in scripting.
				"Scientific_Name": record.species.scientific_name,
				"FID": record.species_id,
				"Presence_Type": record.presence_type.short_description,
				"Data_Source_Name": record.set.name,
				"Data_Source_Path": record.set.source_data,
				"Notes": record.notes,
				"Observation_Date": record.observation_date,
				"Collections": str([collection.name for collection in record.collections]).replace("[", "").replace("u'", "").replace("'", "").replace("]", "")
			})
	except OperationalError:
		log.error("Could not execute the request against the database. It's likely that the request was too complex. Please try fewer HUC12s, fewer species/a smaller group, and/or removing collections limiters.")

	with open(output_csv, 'wb') as write_handle:
		writer = csv.DictWriter(write_handle, fieldnames=["Common_Name", "Scientific_Name", "FID", "Presence_Type", "Data_Source_Name", "Data_Source_Path", "Notes", "Observation_Date", "Collections", "{0:s}_Double".format(local_vars.huc_field)])

		writer.writeheader()
		writer.writerows(output_list)

	if return_gdb_table:
		gdb_name = os.path.split(os.path.splitext(output_csv)[0])[1]
		arcpy.TableToTable_conversion(output_csv, local_vars.workspace, gdb_name)
		full_dataset = os.path.join(local_vars.workspace, gdb_name)

		# now make the text version of the HUC_12 field by deleting the HUC12 field and copying it from the HUC_12_Double field
		arcpy.AddField_management(full_dataset, local_vars.huc_field, "TEXT")
		arcpy.CalculateField_management(full_dataset, local_vars.huc_field, "!%s_Double!" % (local_vars.huc_field), "PYTHON_9.3")
		arcpy.DeleteField_management(full_dataset, "{0:s}_Double".format(local_vars.huc_field))
		return full_dataset
	else:
		return output_csv


def reverse_transaction(transaction_id, db_cursor):

	sql_statement = """INSERT INTO Observations ( Set_ID, Species_ID, Zone_ID, Presence_Type, IF_Method, Certainty, Longitude, Latitude, Survey_Method, Notes, Observation_Date, Other_Data )
					SELECT Set_ID, Species_ID, Zone_ID, Presence_Type, IF_Method, Certainty, Longitude, Latitude, Survey_Method, Notes, Observation_Date, Other_Data
					FROM Invalid_Observations
					WHERE transaction_id = ?;
					"""

	db_cursor.execute(sql_statement, transaction_id)


def get_generic_filter_picker(table_column, validation_class, selector_index):

	if table_column is not None and table_column != "":
		db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
		values = mapping.get_bind_values(table_column, db_cursor)
		funcs.db_close(db_cursor, db_conn)
	else:
		raise ValueError("table_column must be provided and cannot be null - otherwise we can't get a list of items")

	validation_class.params[selector_index].filter.list = values
	validation_class.params[selector_index].value = validation_class.blank


def get_transactions_picker(validation_class, selector_index, minimum_transaction=2027):
	"""

	:param validation_class: the arcmap tool validation class object
	:param selector_index: the index of the field we're adding the filter list for in the validation class
	:param minimum_transaction: the lowest transaction ID to show in the picker. Transactions older than 2027 aren't reversible since records weren't associated with transactions at that point.
	:return: None - sets the value on the validation class parameter
	"""

	session = orm_models.new_session()

	try:
		# get the last 100 removal transactions that completed
		l_transactions = session.query(orm_models.Transaction).filter(orm_models.Transaction.pkey > minimum_transaction).filter_by(operation="Remove", result="success").order_by("datetime_conducted desc").limit(100)
	except:
		if not local_vars.debug:
			raise IOError("Unable to communicate with the PISCES database")
		else:
			raise

	text_filters = []
	for transaction in l_transactions:
		if not transaction.message:
			message = "(no message logged for transaction)"
		else:
			message = transaction.message
		text_filters.append("{0:s} - {1:s}".format(str(transaction.pkey), message))

	validation_class.params[selector_index].filter.list = text_filters
	validation_class.params[selector_index].value = validation_class.blank

	session.close()


def parse_transactions_picker(choice):
	"""
		Corollary to get_transactions_picker Given a choice from it, it parses it and returns the transaction id and message as a tuple
	:param choice: string choice from the picker created by get_transactions_picker
	:return: tuple (id, message)
	"""

	parts = choice.split(" - ")
	return parts[0], parts[1]


def get_input_filter_picker(validation_class, selector_index):
	"""

	:param validation_class: the arcmap tool validation class object
	:param selector_index: the index of the field we're adding the filter list for in the validation class
	:return:
	"""

	session = orm_models.new_session()

	try:
		try:
			l_input_filters = session.query(orm_models.InputFilter).all()
		except:
			if not local_vars.debug:
				raise IOError("Unable to communicate with the PISCES database")
			else:
				raise

		text_filters = []
		for input_filter in l_input_filters:
			if input_filter.full_name == "Unassigned":
				continue

			text_filters.append("{0:s} - {1:s} - {2:s}".format(str(input_filter.pkey), input_filter.code, input_filter.full_name))

		validation_class.params[selector_index].filter.list = text_filters
	finally:
		session.close()


def parse_input_filter_picker(choice):
	"""
		Corollary to get_input_filter_picker. Given a choice from it, it parses it and returns the input filter id, filter code, and name as a tuple
	:param choice: string choice from the picker created by get_input_filter_picker
	:return: tuple (id, filter code, name)
	"""

	parts = choice.split(" - ")
	return parts[0], parts[1], parts[2]


def zones_feature_to_array(zones_layer):
	"""
		WARNING: This function should be deprecated in favor of funcs.hucs_to_list
	:param zones_layer:
	:return:
	"""

	l_cursor = arcpy.SearchCursor(zones_layer)

	zones_array = []

	for feature in l_cursor:  # should only iterate over the selected features
		zones_array.append(feature.HUC_12)  # TODO: Fix HUC_12 Hardcode

	return zones_array


def query_datasets_by_zone(zones, db_conn, species=None):
	"""
		In process of deprecation: replaced by the Look Up Records tool, which no longer calls this function.
		Given a set of HUC_12s and, optionally, a species to limit them to, queries the observations table
		to determine what the data sources are.
	:param zones:
	:param db_conn:
	:param species:
	:return:
	"""

	db_cursor = db_conn.cursor()

	if not (type(zones) is tuple or type(zones) is list):
		zones = [zones] # make it into a list so that the same code works

	species_ext = ""	
	if species is not None:
		species_ext = " and t1.Species_ID = '%s'" % species

	query = "select distinct t1.set_id, t2.source_data, t2.input_filter, t1.presence_type from observations as t1, observation_sets as t2 where t1.zone_id = ? and t1.set_id = t2.set_id%s" % species_ext
	arcpy.AddMessage("Running query - %s" % query)
	observation_sets = {}
	hucs = {}
	tablerows_by_source = []

	#TODO: Fix this block - it's probably broken
	for zone in zones:
		l_results = db_cursor.execute(query, zone)
		for result in l_results:
			if not (result.set_id in observation_sets):
				observation_sets[result.set_id] = input_filters.common.observation_set()
				observation_sets[result.set_id].zones = []  # initialize an empty array of zones
				observation_sets[result.set_id].dataset_path = result.source_data  # set the attributes
				observation_sets[result.set_id].filter_code = result.input_filter

			tablerows_by_source.append(html_add_tablerow([result.set_id, result.input_filter, result.source_data, zone, result.presence_type]))  # store a table row to print to the final file

			arcpy.AddMessage("%s - %s - %s - %s - %s" % (result.set_id, result.input_filter, result.source_data, zone, result.presence_type))  # and print it directly to the arcpy console

	l_out_filename = os.path.join(local_vars.internal_workspace, "log", "query_datasets_by_zone_out.htm")

	if os.path.exists(l_out_filename):
		os.remove(l_out_filename)  # get rid of the old file

	zone_out = open(l_out_filename, 'w')  # and open a new one

	if species:
		zone_out.write('<html><head><title>' + species + ' Source information</title>'
				   '<style>body{font-family:Arial,Helvetica, sans-serif;color:#666;}</style></head>'
				   '<body><h1>' + species + ' Source information</h1>')
	else:
		zone_out.write('<html><head><title>HUC12 Source information</title>'
				   '<style>body{font-family:Arial,Helvetica, sans-serif;color:#666;}</style></head>'
				   '<body><h1>HUC12 Source information</h1>')

	zone_out.write('<table cellspacing="10">'
				   '<tr><td>Observation Set ID</td><td>Input Filter Code</td><td>Dataset Path</td>'
				   '<td>Zone ID</td><td>Presence Type</td>')  # make a rudimentary non-standards-compliant html page

	for row in tablerows_by_source:
		zone_out.write(row)

	zone_out.write("</table></body></html>")

	arcpy.AddWarning("Full output is located at %s" % l_out_filename)

	#TODO: Make display better and highlight/note HUCs with multiple sources

	db_cursor.close()


def split_collection_names(picker_output):
	"""

	:param picker_output:
	:return:
	"""

	collections = picker_output.split(";")
	for i in range(len(collections)):
		collections[i] = collections[i].replace("'", "")  # seems to come out with ' characters around things, which breaks matching

	return collections


def make_obs_type_picker(validation_class, selector_index):

	session = orm_models.new_session()
	try:
		l_types = []
		obs_types = session.query(orm_models.PresenceType).order_by(orm_models.PresenceType.type).all()
		for o_type in obs_types:
			l_types.append("{0:s} - {1:s}".format(str(o_type.type), o_type.description))
	finally:
		session.close()

	validation_class.params[selector_index].filter.list = l_types


def obs_type_selection_box_to_list(obs_type_as_string):
	"""
		Given the output of the observation type picker box, returns the observation IDs
	:param obs_type_as_string:
	:return:
	"""

	observation_types = obs_type_as_string.split(";")

	vals = []
	for i, item in enumerate(observation_types):
		vals.append(parse_obs_type_from_list(item))

	return vals

def parse_obs_type_from_list(l_search_string):
	'''takes an observation code from an ArcGIS 10 Script tool dropdown in the form of "Code - Description" and parses out the code and returns it'''

	type_re = re.search("^'?(\d+)", l_search_string)
	try:
		return int(type_re.group(1))
	except:
		return None  # if it didn't work, we probably don't have an obs type


def make_config_backup():
	"""
		Backups up the configuration file. Used when successfully loaded before editing it
	:return:
	"""

	config_backup = os.path.join(local_vars.code_folder, "config.py.pisces_backup")
	config_file = os.path.join(local_vars.code_folder, "config.py")

	if os.path.exists(config_backup):  # if it already exists, delete it
		os.remove(config_backup)

	shutil.copyfile(config_file, config_backup)  # back it up



def html_add_tablerow(items):
	"""
		PROBABLY DEPRECATED along with the old Look Up Records tool. TODO: We should check for usages
	:param items:
	:return:
	"""
	l_row = "<tr>\n"
	for item in items:
		l_row = "%s<td>%s</td>\n" % (l_row,item) # add a table cell for the item
	l_row = "%s\n</tr>" % l_row # end the row

	return l_row


def set_default_IF_for_addition(username, validation_class, selector_index):
	"""
		Sets the default input filter for the Add or Modify Data tool based upon the user's username (looks up the input filter associated with it, and leaves it blank otherwise)
	:param username: the PISCES username to use to find the input filter
	:param validation_class: script tool validation class object
	:param selector_index: the index order of the field with the input filter selector
	:return:
	"""

	try:
		input_filter = determine_default_IF_for_addition(username)
		validation_class.params[selector_index].value = "{0:s} - {1:s} - {2:s}".format(str(input_filter.pkey), input_filter.code, input_filter.full_name)
	except ValueError:
		validation_class.params[selector_index].value = ""



def determine_default_IF_for_addition(username):
	"""
		Treating the username as an input filter code, it retrieves the best IF, raising ValueError if an Input Filter is not found. This should be caught and set the box to no value on the handling end.
	:param username: the PISCES username of the current install
	:return:
	"""

	session = orm_models.new_session()

	try:
		input_filter = session.query(orm_models.InputFilter).filter_by(code=username).one()
	except:
		raise ValueError("Input filter for {0:s} not found".format(username))
	finally:
		session.close()

	return input_filter