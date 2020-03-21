__author__ = 'dsx'

from six.moves import reload_module

import arcpy

from PISCES import config_class  # keep this syntax because it's what's used in the tool validators, so this will let us update it
from PISCES import local_vars

local_vars.start(arc_script=True)

config_username = arcpy.GetParameterAsText(0)
config_export_mxd = arcpy.GetParameter(1)
config_export_png = arcpy.GetParameter(2)
config_export_pdf = arcpy.GetParameter(3)
config_export_shp = arcpy.GetParameter(4)
config_export_kml = arcpy.GetParameter(5)
config_export_ddp = arcpy.GetParameter(6)
config_output_common_name = arcpy.GetParameter(7)
config_export_metadata = arcpy.GetParameter(8)
config_debug = arcpy.GetParameter(9)
config_maindb = arcpy.GetParameterAsText(10)
config_map_output_folder = arcpy.GetParameterAsText(11)
config_mxd_output_folder = arcpy.GetParameterAsText(12)
config_web_layer_output_folder = arcpy.GetParameterAsText(13)
config_export_lyr = arcpy.GetParameter(14)

# get the config
config = config_class.PISCES_Config()

config.username = config_username
config.export_mxd = config_export_mxd
config.export_png = config_export_png
config.export_pdf = config_export_pdf
config.export_shp = config_export_shp
config.export_kml = config_export_kml
config.export_lyr = config_export_lyr
config.export_ddp = config_export_ddp
config.output_common_name = config_output_common_name
config.export_metadata = config_export_metadata
config.debug = config_debug
config.maindb = config_maindb
config.map_output_folder = config_map_output_folder
config.mxd_output_folder = config_mxd_output_folder
config.web_layer_output_folder = config_web_layer_output_folder
config.save()

reload_module(config_class.config)  # make sure it refreshes if it's being run in ArcMap

del config