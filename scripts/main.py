"""
PISCES

Usage:
  main.py clearcaches
  main.py cleartemp [--softerror]
  main.py stats
  main.py [[map|export] [--usecache] [--continue] [--notrans] [--export_png=<boolean>]]
  main.py import
  main.py [help] [--help] [-h] [--usage]
"""
from __future__ import print_function

import os
import sys

try:
	from docopt import docopt  # by default, use the installed version
except ImportError:  # but if it's not installed, use a local copy
	from PISCES.pisces_docopt import docopt

from PISCES import local_vars
from PISCES import args
from PISCES import funcs
from PISCES import mapping
from PISCES import input_filters

#if __name__ == '__main__':
arguments = docopt(__doc__, version="1.x")
#set up the workspace
local_vars.start()

if (arguments["--help"] or arguments["help"] or arguments["-h"] or arguments["--usage"]) \
	or (not (not (arguments["stats"] is False) or not (arguments["clearcaches"] is False)
		or not (arguments["import"] is False) or not (arguments["cleartemp"] is False) or not
		(arguments["map"] is False) or not (arguments["export"] is False))):
	# TODO: WTF is this? Why? Isn't there a better way to do this with docopt?
	print(__doc__)
	sys.exit()

args.process_args(arguments)

if arguments["stats"]:
	t_cursor, t_conn = funcs.db_connect(local_vars.maindb, "getting stats")
	funcs.data_stats(t_cursor)
	funcs.db_close(t_cursor, t_conn)
	sys.exit()

if arguments["clearcaches"]:
	funcs.clean_workspace()
	funcs.refresh_layer_cache()
	sys.exit()

if arguments["cleartemp"]:
	if arguments["--softerror"]:
		softerror = True
	else:
		softerror = False
	funcs.clean_workspace(softerror=softerror)
	sys.exit()

if arguments["--notrans"]:
	local_vars.current_obs_types = local_vars.notrans_obs_types

local_vars.print_workspace_vars()
local_vars.data_setup()  # populates variables with data from the database
#funcs.clean_workspace() #make sure that old data files are cleared out


# run stats for a normal run here so that they sit for a while while everything else gets set up
t_cursor, t_conn = funcs.db_connect(local_vars.maindb, "getting stats")
funcs.data_stats(t_cursor)
funcs.db_close(t_cursor, t_conn)


### Process Any New Data ###

if arguments["import"]:
	print("BEGINNING NEW DATA PROCESSING")

	input_filters.common.import_new_data(dataset_name=None)

if arguments["map"] or arguments["export"]:
	if arguments["--usecache"]:
		local_vars.usecache = 1
	if arguments["--continue"]:
		local_vars.continue_mapping = True

	try:
		mapping.begin("all")
	except local_vars.MappingError as error:
		print("Uncaught error encountered while mapping - program provided: %s" % error)

print("\nComplete")