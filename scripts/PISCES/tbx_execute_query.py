__author__ = 'nrsantos'

import arcpy
from PISCES import api
from PISCES import local_vars

local_vars.start(arc_script=True)

query = arcpy.GetParameterAsText(0)
callback = arcpy.GetParameterAsText(1)
callback_args = arcpy.GetParameterAsText(2)

layer = api.get_query_as_layer(query, callback=callback, callback_args=callback_args)

arcpy.SetParameter(3, layer)

