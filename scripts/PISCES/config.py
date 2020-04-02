from __future__ import absolute_import, division, print_function

import os

from . import local_vars

### General

local_vars.debug = True
local_vars.maindb = os.path.join(local_vars.internal_workspace, "data", "pisces.sqlite")
use_intermediate_products = False  # for import filters that act on this flag, it allows skipping intermediate products that are already generated in order to move to the final steps. Primarily a debug flag that acts differently for each filter

username = "CWS"

## MAPPING ##

# configures the default layers and the order they get used (from first to last)
local_vars.layer_files = ["gen_1.lyr", "gen_2.lyr", "gen_3.lyr", "gen_4.lyr", "gen_5.lyr"]
extent_scale_factor = 1.1  # controls how much space is around the edge of the ranges to buffer the ranges

# set each of the following to True in order to export the corresponding file type, False to disable that type of export.
local_vars.export_pdf = False
local_vars.export_png = True
local_vars.export_mxd = True
local_vars.export_ddp = False
# ddp = Data driven pages

# EXPORT FORMATS - setting any of these three to True will greatly increase processing time for map output.
local_vars.export_web_layer_kml = False
local_vars.export_web_layer_shp = False
local_vars.export_web_layer_lyr = False
# EXPORT LOCATIONS
local_vars.map_output_folder = os.path.join(local_vars.internal_workspace, "maps", "output")
local_vars.mxd_output_folder = os.path.join(local_vars.internal_workspace, "mxds", "output")
local_vars.web_layer_output_folder = os.path.join(local_vars.internal_workspace, "maps", "web_output", "layers")

# EXPORT OPTIONS
local_vars.output_common_name = True
# only valid when a name formula isn't specified for a map in the database, so it won't work for all maps
local_vars.config_metadata = False
# speed issue - turning off metadata can make map exports MUCH faster.
