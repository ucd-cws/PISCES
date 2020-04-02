from __future__ import absolute_import, division, print_function

import sys
import os

import arcpy

from . import local_vars
from . import log
from . import funcs

args = ['-test','-testdir','-workspace','-importonly','-maponly','-usecache','-stats']
flags = {}

from . import config
from . import mapping

def process_args(args):
	"""
		Sets configuration variables based on command line arguments

	@param args:
	@return: False
	"""

	if args["--export_png"] is True:
		local_vars.export_png = True
	elif args["--export_png"] is False:
		log.write("Will not export PNGs",1)
		local_vars.export_png = False

def check_args():
	del sys.argv[0] #strip off the program name from the front
	
	global flags
	
	#iterate over the args
	for item in args: #TODO: this is completely innefficient. We already check the args in handle_arg. We essentially check it twice. Fix this sometime when have the chance
		for index, arg in enumerate(sys.argv):
			if item == arg:
				try:
					handle_arg(sys.argv[index],sys.argv[index+1],flags)
					del sys.argv[index+1], sys.argv[index] #remove the arguments - don't need to search for them again!
				except:
					print_usage()
					
	if flags.has_key("test"):
		funcs.setup_test_mode() #we want this to happen after all of the other args are processed

	# finally, if there remain args after this, then they didn't use the command line right
	# so we should print a usage note
	
	try: # this is probably a super funky way to do this...just seeing if it exists first before we try to access it directly
		sys.argv[0]
	except IndexError: # if it doesn't exist, append None so that the next if statement still isn't triggered
		sys.argv.append(None)
		
	if sys.argv[0] is not None: # if we got here and we still have command line params, then something is wrong
		print_usage()
		
def print_usage():
	"""
		Likely a fully deprecated function - usage is automatically printed by docopt when not used correctly.
	:return:
	"""
	print("Command line usage:\n\tstart.py")
	print("\t\t[-stats 1 - print stats and exit]")
	print("\t\t[-maponly 1 - only generate maps - skip import]")
	print("\t\t[-importonly 1 - only import data - skip mapping]")
	print("\t\t[-usecache 1 - when mapping, don't generate new layers - use cached layers instead]")
	print("\t\t[-test 1 - sets test mode - makes a copy of data files so we aren't using the real versions]")
	print("\t\t[-testdir \"{a folder}\" - sets the location to store the test files. Defaults to a subdir of this program, but setting this can be much faster if working on a network drive.]")
	print("\t\t[-workspace \"{.mdb location}\"] - used for scratch work]")
	print("\n\nAdditional configuration variables are available in /scripts/PISCES/config.py")
	sys.exit()
	
			
def handle_arg(arg,value,flags):
	if(arg == "-workspace"):
		local_vars.workspace = value
		arcpy.env.workspace = value
		log.write("Workspace set to %s\n" % value,1)
	elif(arg == "-testdir"):
		if value == "temp":
			import tempfile
			local_vars.test_folder = os.path.join(tempfile.gettempdir(),"fsfish")
		else:
			local_vars.test_folder = value
		log.write("Test folder set to %s\n" % local_vars.test_folder,1)
	elif(arg == "-maponly"):
		local_vars.maponly = 1
		local_vars.importonly = 0
		log.write("Map Only flag set - skipping import\n",1)
	elif(arg == "-importonly"):
		local_vars.importonly = 1
		local_vars.maponly = 0
		log.write("Import Only flag set - skipping mapping\n",1)
	elif(arg == "-usecache"):
		local_vars.usecache = 1
		log.write("Using Layer Cache - This will NOT generate new layers for queries, and any maps that contain queries without existing layers WILL FAIL.\n",1)
	elif arg == "-stats":
		flags['stats'] = True
		log.write("Stats only - skipping processing\n",1)
	elif(arg == "-test"):
		flags['test'] = 1 # we just set the flag because we want this to happen last