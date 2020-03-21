"""
	An ArcGIS Toolbox tool to import a dataset when the input filter is already set up.

	The methods in this tool may be a bit roundabout because they'll be attempting to use quite a bit of existing code that
	assumes explicit paths, etc. So records and data will need to be written to those locations in order to be used.
"""
import funcs
import input_filters.common
import local_vars

__author__ = 'dsx'

import os
import traceback

import arcpy

from PISCES import local_vars
from PISCES import funcs
from PISCES import script_tool_funcs
from PISCES import log


def set_up_import(dataset, input_filter, species, field_mapping_record_set):
	"""
		Given the necessary information, sets up the data for an import (but doesn't run the import - copies the dataset to newdata.mdb, adds the record, inserts the field map, etc. Meant to be run as an ArcGIS script tool
	:param dataset: an arcgis feature class or feature layer to attempt to import
	:param input_filter: The input filter to use to process this dataset, as constructed by script_tool_funcs.get_input_filter_picker()
	:param species: optional. If the dataset is a single species, this one is it. In the format of the ArcGIS tool pickers (species code - common name) so it can be parsed.
	:param field_mapping_record_set: An ArcGIS RecordSet object - can also be just a table with four fields (PISCES_Field (string), Input_Field (string), Handler_Function (string), Required (boolean)). Records indicate a field mapping from Input_Field->PISCES_Field
	:return:
	"""

	# copy the feature class to the new data geodatabase
	log.write("Copying data to Database", True)
	full_path = local_vars.copy_data(dataset, local_vars.newdb)
	fc_name = os.path.split(full_path)[1]

	try:
		log.write("Validating inputs", True)
		# parse the filter code
		filter_parts = script_tool_funcs.parse_input_filter_picker(input_filter)
		filter_code = filter_parts[1]

		# determine the species
		if species == "Determined per-record by software":
			species_code = "filter"
		else:
			species_code = funcs.parse_input_species_from_list(species)

		db_cursor, db_conn = funcs.db_connect(local_vars.newdb, "Connecting for tbx_import_dataset", access=True)
		sql_statement = "insert into NewData (Feature_Class_Name, Input_Filter, Species_ID) values (?,?,?)"
		db_cursor.execute(sql_statement, fc_name, filter_code, species_code)
		# don't commit yet because if the insertion of the FieldMapping fails we don't want to keep this

		new_data_id = funcs.get_last_insert_id(db_cursor, access=True)

		log.write("Inserting Records", True)
		allowed_fields = ("Species", "Zone_ID", "Observation Type", "Latitude", "Longitude", "Survey Method", "NotesItems", "Date", "Certainty", "Observer")
		sql_statement = "insert into FieldMapping (NewData_ID, Field_Name, Input_Field, Handler_Function, Required) values (?,?,?,?,?)"
		dataset_fields = arcpy.ListFields(dataset)
		valid_input_fields = [record.name for record in dataset_fields]

		record_cursor = arcpy.SearchCursor(field_mapping_record_set)
		for record in record_cursor:
			#if (record.Input_Field is None or record.Input_Field == "") and (record.PISCES_Field is None or record.PISCES_Field == ""):
			#	continue  # if we don't have an input field or a pisces field, they probably weren't configuring anything. We got some errors for records that didn't exist

			if record.Required not in (None, 0, 1):
				raise ValueError("Values for \"Required\" must be either 0 (not required) or 1 (required). You provided '%s'" % record.Required)

			if record.PISCES_Field not in allowed_fields:
				raise ValueError("Options for PISCES_Field must be one of the following: %s. You provided '%s'" % (allowed_fields, record.PISCES_Field))

			if record.Input_Field not in valid_input_fields:
				raise ValueError("Field names in Input_Field must be fields that exist in the input dataset. You provided '%s'. Valid options are %s" % (record.Input_Field, valid_input_fields))

			db_cursor.execute(sql_statement, new_data_id, record.PISCES_Field, record.Input_Field, record.Handler_Function, record.Required)

		log.write("Finishing Up", True)
		db_conn.commit()
		funcs.db_close(db_cursor, db_conn)

		return fc_name

	except:
		# clean up on failure, then raise the exception up
		log.error("Failure occurred, attempting to clean up - error: %s" % traceback.format_exc())
		try:
			dataset_path = os.path.join(local_vars.newdb, fc_name)
			if arcpy.Exists(dataset_path):
				arcpy.Delete_management(dataset_path)
		except:
			pass
		raise


def run_import(dataset_name):

	input_filters.common.import_new_data(dataset_name)


if script_tool_funcs.is_in_arcgis():  # allows us to unit test the code by making it not run unless we're in ArcGIS

	local_vars.start(arc_script=1)

	config_dataset = arcpy.GetParameterAsText(0)
	config_input_filter = arcpy.GetParameterAsText(1)
	config_species = arcpy.GetParameterAsText(2)
	config_field_mapping_record_set = arcpy.GetParameterAsText(3)

	log.write("BEGINNING SETUP PHASE", True)
	new_data_name = set_up_import(config_dataset, config_input_filter, config_species, config_field_mapping_record_set)

	log.write("BEGINNING IMPORT PHASE", True)
	run_import(new_data_name)