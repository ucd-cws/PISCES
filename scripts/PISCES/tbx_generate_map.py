import funcs
import local_vars

__author__ = 'Nick'

import os

import arcpy

from PISCES import local_vars
from PISCES import funcs
from PISCES import script_tool_funcs
from PISCES import log
from PISCES import mapping

local_vars.start(arc_script=1)

map_name = arcpy.GetParameterAsText(0)
# 1 is a description holder and 2 is the selection for the groups
config_species_and_groups_list = arcpy.GetParameterAsText(3)
config_auto_open = arcpy.GetParameter(4)

config_output_ddp = arcpy.GetParameter(5)
config_output_png = arcpy.GetParameter(6)
config_output_pdf = arcpy.GetParameter(7)
config_output_kml = arcpy.GetParameter(8)
config_output_shp = arcpy.GetParameter(9)
config_export_metadata = arcpy.GetParameter(10)
config_output_lyr = arcpy.GetParameter(12)
config_iterator = arcpy.GetParameter(11)

arcmap_layers, running_in_arcmap = script_tool_funcs.deactivate_map("CURRENT")

try:
	if map_name != "Last Map Configuration":  # If we haven't specified to keep everything the way it is.
		# takes the string and separates it out into individual items,
		#  extracting the species from their "code - common name" form
		# if it's not using the standard species and groups picker, then don't do this behavior because it's not expecting a species.
		if config_iterator.lower() in ("species_groups:fid", "species:fid"):
			config_species_list = funcs.parse_multi_species_group_list(config_species_and_groups_list)
		else:  # not expecting a species - just make a list from the input
			config_species_list = config_species_and_groups_list.split(";")

		# connect to the DB
		db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "exporting maps from script tool")

		# disable all maps
		disable_maps_query = "update %s set active=%s" % (local_vars.maps_table, local_vars.db_false)
		db_cursor.execute(disable_maps_query)

		# enable the relevant one
		enable_correct_map_query = "update %s set active=%s where set_name='%s'" % (local_vars.maps_table, local_vars.db_true, map_name)
		db_cursor.execute(enable_correct_map_query)
		db_conn.commit()  # commit the changes

		# get the map id
		map_id_query = "select id from %s where set_name='%s'" % (local_vars.maps_table, map_name)
		map_id = db_cursor.execute(map_id_query).fetchone().id

		log.write("Map ID: %s" % map_id, True)
		if not map_id:
			log.error("Couldn't find Map ID for selected map")
			raise ValueError("Couldn't find Map ID for selected map")

		# delete all existing bind for the map
		remove_bind_query = "delete from %s where query_set_id = %s" % (local_vars.bind_vals_table, map_id)
		db_cursor.execute(remove_bind_query)

		if config_iterator is not None and config_iterator != "" and len(config_species_list) > 0:  # if we have an iterator and we have items from it
			# insert the new species records
			insert_bind_query = "insert into %s (query_set_id, bind_value) values (%s, ?)" % (local_vars.bind_vals_table, map_id)
			for species in config_species_list:
				db_cursor.execute(insert_bind_query, species)

		# commit the changes again
		db_conn.commit()
		funcs.db_close(db_cursor, db_conn)

	# set some mapping variables
	local_vars.export_mxd = True

	local_vars.export_pdf = config_output_pdf
	local_vars.export_png = config_output_png
	local_vars.export_ddp = config_output_ddp
	local_vars.export_web_layer_kml = config_output_kml  # setting either of these two to True will greatly increase processing time
	local_vars.export_web_layer_shp = config_output_shp
	local_vars.config_metadata = config_export_metadata
	local_vars.export_web_layer_lyr = config_output_lyr

	# execute the map
	map_objects = mapping.begin("all", return_maps=True)  # run the maps and get the objects

	if config_auto_open:  # if we should auto-open it
		if map_objects and len(map_objects) == 1:  # if we have just one map, try to auto-open
			l_map = map_objects[0]  # the resulting map

			if l_map.mxd_path is not None and os.path.exists(l_map.mxd_path):
				log.write("Opening MXD", 1)
				os.startfile(l_map.mxd_path)  # subprocess.call([os.path.join(install_dir, "Bin", "ArcMap.exe"), ]) # call arcmap with the mxd
			else:
				log.warning("A map document was not created, likely because there wasn't data for your requested mapset and species.")
		elif not map_objects or (map_objects and len(map_objects) == 0):  # no maps!
			log.error("Failed to output map - See error message above")
		else:  # otherwise, it's too many maps - don't want to open 20 maps, etc
			log.warning("Too many maps to open - please open them manually out of the mxds/output directory of your PISCES"
						"install folder")
except:
	raise
finally:  # regardless of what happens, turn their map layers back on
	script_tool_funcs.reactivate_map("CURRENT", arcmap_layers, running_in_arcmap)

