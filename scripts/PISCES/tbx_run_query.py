'''provides an entry point for these functions from an ArcGIS 10 Toolbox'''

import arcpy

from PISCES import local_vars
from PISCES import funcs
from PISCES import log

from PISCES import script_tool_funcs
from PISCES import mapping

local_vars.start(arc_script=1)

base_map = arcpy.GetParameterAsText(0)  # the map definition that we want to use as the basis w/queries
queries = arcpy.GetParameterAsText(1)  # semicolon separated - per ArcGIS. the stack of queries from a map - might be a duplicate, depending on the UI - if we want users to add/remove queries in the tool, then not a dupe.
bind_values = arcpy.GetParameter(2)  # semicolon separated - per ArcGIS.  the bind values as - need to be split
config_output_param_index = 3  # it's the value to start with when we begin returning layers
config_output_max = 7  # it will only return layers so long as the index is less than this
 
queries = script_tool_funcs.semicolon_split_to_array(queries)
bind_values = script_tool_funcs.semicolon_split_to_array(bind_values)


def set_up_map(queries):
    l_queries = []
    for query in queries:
        l_query = mapping.custom_query(custom_query=unicode(query))
        l_queries.append(l_query)

    l_map = mapping.fish_map()
    l_map.setup(l_queries)

    return l_map


def generate_layers(l_map):
    
    db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "Running a query in ArcMap")
    
    l_map.populate(db_cursor)
    l_map.make_layers(arcpy.MakeFeatureLayer_management(local_vars.HUCS), db_cursor, cache_layer=False,unique_layer_name=True)


log.write("Setting up", 1)
main_map = set_up_map(queries)

log.write("Generating Layers", 1)
mapping.generate_layers(main_map)

cur_layer = config_output_param_index
for layer in main_map.map_layers:
    if not cur_layer < config_output_max:  # if we're above the number of parameters we're supposed to be
        log.error("Not all layers returned - reached maximum number of returnable layers")
        break
    log.write("Setting ouput", 1)
    arcpy.SetParameterAsText(cur_layer, layer.layer_name)
    cur_layer = cur_layer + 1
    

log.write(queries)
log.write(bind_values)

# 1) Can select entire map and have the queries filled in...

# 2) Dropdown fills in select box (like the NADconverter) with queries
# 3) if custom, read custom box
# 4) comma separated bind variables for *each* query
# 5-12) 8 return options - returns empty layer (or nothing?) if nothing.