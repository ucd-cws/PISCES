"""
	A simple utility that runs the PISCES statistics functions and returns the results as a table into ArcMap
"""

__author__ = 'dsx'

import os
from datetime import datetime
import csv

import arcpy

from PISCES import local_vars
from PISCES import script_tool_funcs
from PISCES import funcs
from PISCES import log


def get_stats_table(output_gdb):
	"""
		Runs funcs.data_stats and output a table into the geodatabase provided as a parameter
	:param output_gdb: The geodatabase to put the stats table into
	:return:
	"""
	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)

	name_col = "Parameter"
	value_col = "Value"
	values = funcs.data_stats(db_cursor, print_to_screen=True, name_col=name_col, value_col=value_col)

	csv_name = os.path.join(local_vars.temp, "pisces_stats_%s.csv" % datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))

	with open(csv_name, 'wb') as csv_file:
		writer = csv.DictWriter(csv_file, [name_col, value_col])
		writer.writeheader()
		writer.writerows(values)

	gdb_name = os.path.split(os.path.splitext(csv_name)[0])[1]
	arcpy.TableToTable_conversion(csv_name, output_gdb, gdb_name)
	full_dataset = os.path.join(output_gdb, gdb_name)

	funcs.db_close(db_cursor, db_conn)

	return full_dataset

if script_tool_funcs.is_in_arcgis():

	local_vars.start(arc_script=1)

	output_gdb = arcpy.GetParameterAsText(0)
	try:
		output_table = get_stats_table(output_gdb=output_gdb)
		arcpy.SetParameter(1, output_table)
	except:
		log.error("Can't send output table to table of contents. Are you running this in ArcMap? If not, your results are above.")