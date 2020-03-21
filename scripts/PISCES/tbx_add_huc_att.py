import sys
import os

import arcpy

from PISCES import funcs
from PISCES import local_vars
from PISCES import log
from PISCES import script_tool_funcs

local_vars.start(arc_script=True)

# get the args
hucs_layer = arcpy.GetParameterAsText(0)
field_name = arcpy.GetParameterAsText(1)
input_field_name = arcpy.GetParameterAsText(2) # the name of the field in the input data that contains the value to look at - only used in non-boolean cases

# get the hucs as a list
list_of_hucs = funcs.hucs_to_list(hucs_layer)

if not list_of_hucs:
	log.error("No HUCs - exiting")
	sys.exit()

if not field_name:
	log.error("No field to add - exiting")
	sys.exit()

# check if the field already exists - using arcpy to check, but we'll alter the table with a query because Arc doesn't have a boolean datatype
cur_table = os.path.join(local_vars.maindb, local_vars.zones_aux)

log.write("Adding field if necessary", True)
desc = arcpy.Describe(cur_table)

db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
for field in desc.fields:  # desc contains zones_aux, not the passed in layer
	# probably better done with a lambda
	if field_name == field.name:
		new_col = False
		break
else:
	# then we need to add it
	# TODO: This tool won't work until we fix this alter table query to be compatible with SQLite
	query = "ALTER TABLE zones_aux ADD COLUMN %s INTEGER" % field_name
	results = db_cursor.execute(query)
	new_col = True

del desc

log.write("Updating data", True)

if new_col: # right now we can only process boolean in new columns. We'll need to fix this in the future.
	# set it all to False
	query = "update %s set %s=%s" % (local_vars.zones_aux, field_name, local_vars.db_false)
	results = db_cursor.execute(query)

	# now set specific ones to true
	query = "update %s set %s=%s where Zone=?" % (local_vars.zones_aux, field_name, local_vars.db_true)
	for huc in list_of_hucs:
		results = db_cursor.execute(query, huc)
else:
	t_curs = arcpy.SearchCursor(hucs_layer)

	query = "update %s set %s=? where zone=?" % (local_vars.zones_aux, field_name)
	for huc in t_curs:
		results = db_cursor.execute(query, huc.getValue(input_field_name), huc.getValue(local_vars.huc_field))

db_conn.commit()  # commit the change
funcs.db_close(db_cursor, db_conn)
log.write("Complete", True)
