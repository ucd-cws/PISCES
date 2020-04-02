from __future__ import absolute_import, division, print_function

import os
import sys
import re
import sqlite3

import arcpy

from PISCES import local_vars
from PISCES import args
from PISCES import log
from PISCES import funcs
from PISCES import script_tool_funcs

'''This script is meant to be run only as an ArcGIS script tool - messages will be passed out using arcpy'''
'''This is the primary toolbox function from before they were prefixed with tbx_ - it handles modifications of records directly from within ArcGIS'''


print("This script should only be run as an ArcGIS script tool. If you can see this message, you should exit or you better know what you are doing")

local_vars.start(arc_script=1)

# general
layer = arcpy.GetParameterAsText(0)
species = arcpy.GetParameterAsText(1)
operation = arcpy.GetParameterAsText(2) # add, remove, transfer
new_species = arcpy.GetParameterAsText(3)
data_type = arcpy.GetParameterAsText(4)
reason_message = arcpy.GetParameterAsText(5)
other_notes = arcpy.GetParameterAsText(6)
username = arcpy.GetParameterAsText(7)

if username is None or username == "":
	username = "np"

submitted_edits_gdb = os.path.join(local_vars.internal_workspace,"data","submitted_edits.gdb")

# do a sanity check
if arcpy.GetCount_management(layer).getOutput(0) == arcpy.GetCount_management(local_vars.HUCS).getOutput(0): # if we have all of the HUCs selected
    arcpy.AddError("Whoa - are you trying to destroy a whole species here? You selected the whole state! Since it was probably an error, we're going to just exit the program right now. If you intended to run that operation, do us a favor and select all of the polygons, then deselect just one so we know you are in your right mind. Then try again.")
    sys.exit()

if species == None and new_species == None:
    log.error("No species to work on, exiting")
    sys.exit()

# TODO: Code exists for the following block in script_tool_funcs.py as parse_input_species_from_list()
species_re = re.search("^(\w{3}\d{2})",species) 
species = species_re.group(0)
if len(new_species) > 0:
    species_re = re.search("^(\w{3}\d{2})",new_species)
    new_species = species_re.group(0)

log.write("Setup complete - writing out edits for %s" % species)

def copy_layer(layer, username):
	output_name = arcpy.CreateUniqueName("edit", submitted_edits_gdb)
	
	log.write("Saving spatial data", 1)
	try:
		arcpy.CopyFeatures_management(layer, output_name)
	except:
		log.error("Unable to copy the edits to storage - failed to process your edits! Try again please!")
		raise
	
	return output_name

def write_log(filename):
	log_db = sqlite3.connect(os.path.join(local_vars.internal_workspace,"data","submitted_edits.sqlite3"))
	log_db.isolation_level = None  # put the connection into autocommit more
	log_cursor = log_db.cursor()
	log.write("Saving metadata", 1)
	try:
		log_cursor.execute('''insert into edits (user,edit_time,filename,data_type,species,operation,new_species,reason,other_notes) values (?,datetime('now'),?,?,?,?,?,?,?)''',(username,filename,data_type,species,operation,new_species,reason_message,other_notes))
	except:
		log.error("Your edits were written out, but could not be logged, so Nick won't know what to do with them. Please try again!")
		raise
	log_cursor.close()
	log_db.close()

file = copy_layer(layer, username)
write_log(file)

log.write("Success! You can close this box now")
