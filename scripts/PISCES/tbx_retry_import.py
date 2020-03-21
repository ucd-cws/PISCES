import input_filters.common

__author__ = 'dsx'

import arcpy

from PISCES import local_vars
from PISCES import funcs
from PISCES import log
from PISCES import script_tool_funcs


if script_tool_funcs.is_in_arcgis():  # allows us to unit test the code by making it not run unless we're in ArcGIS

	local_vars.start(arc_script=1)

	config_dataset_name = arcpy.GetParameterAsText(0)

	log.write("BEGINNING IMPORT PHASE", True)
	input_filters.common.import_new_data(config_dataset_name)