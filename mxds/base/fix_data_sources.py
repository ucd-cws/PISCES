from __future__ import print_function
import os

import arcpy

folder = os.getcwd()
files = os.listdir(folder)

def fix_paths(mxd):
	mxd.replaceWorkspaces(r"C:\Users\dsx.AD3\Code\PISCES\data\PISCES.mdb", "ACCESS_WORKSPACE", r"C:\Users\dsx.AD3\Code\PISCES\data\PISCES_map_data.gdb", "FILEGDB_WORKSPACE")

def fix_lakes_query(mxd):
	for lyr in arcpy.mapping.ListLayers(mxd):  
		if lyr.name == "Lakes":  
			lyr.definitionQuery = "Area > 6000000"  

for f in files:
	if f.endswith(".mxd"):
		print(f)
		mxd = arcpy.mapping.MapDocument(os.path.join(folder, f))
		#fix_paths()
		fix_lakes_query(mxd)
		mxd.save()
		del mxd
		

