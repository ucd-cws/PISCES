'''provides an entry point for these functions from an ArcGIS 10 Toolbox'''

import traceback

import arcpy

from PISCES import local_vars
from PISCES import log
from PISCES import funcs
from PISCES import script_tool_funcs
from PISCES import api

local_vars.start(arc_script=1)

huc_layer_index = 0
species_picker_index = 1
species_list_index = 2
#join_results_index = 3
observation_types_index = 3
collections_picker_index = 4
collections_storage_index = 5
output_table_index = 6

layer = arcpy.GetParameterAsText(huc_layer_index)
config_species_and_groups_list = arcpy.GetParameterAsText(species_list_index)
#config_join_results = arcpy.GetParameter(join_results_index)
config_observation_types = arcpy.GetParameterAsText(observation_types_index)
config_collections = arcpy.GetParameterAsText(collections_storage_index)


def look_up_records(l_layer, l_config_species_and_groups_list, l_config_observation_types, l_config_collections):
	log.write("Looking Up Records", True)
	# preprocess inputs
	if l_config_species_and_groups_list and l_config_species_and_groups_list != '':
		log.write("Parsing Species Requested", True)
		species_list = funcs.text_to_species_list(l_config_species_and_groups_list)  # parse out the species codes
	else:
		species_list = None
	zones = script_tool_funcs.zones_feature_to_array(l_layer)  # get the selected HUCs

	if l_config_observation_types and l_config_observation_types != '':
		log.write("Parsing Observation Types", True)
		observation_types = script_tool_funcs.obs_type_selection_box_to_list(l_config_observation_types)
	else:
		observation_types = None

	if l_config_collections and l_config_collections != '':
		log.write("Parsing Collections", True)
		collections = script_tool_funcs.split_collection_names(l_config_collections)
	else:
		collections = None

	# get results
	log.write("Obtaining Records", True)
	records = api.get_observation_records_for_hucs(zones, species_list, observation_types, collections)
	log.write("Writing Table", True)
	l_table = script_tool_funcs.write_table_from_observation_records(records, return_gdb_table=True)

	return l_table

#if script_tool_funcs.is_in_arcgis():  # sort of like if __name__ == "__main__" for ArcGIS tools
if __name__ == "__main__":
	try:
		table = look_up_records(layer, config_species_and_groups_list, config_observation_types, config_collections)

		# add them to ArcMap
		log.write("Loading Table Into ArcMap", True)
		arcpy.SetParameter(output_table_index, table)
	except:
		log.error(traceback.format_exc())

#orm_models.disconnect_engine_and_session()
