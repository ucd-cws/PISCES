import os
import arcpy
SOS_folder =os.getcwd()
print SOS_folder
all_files =os.listdir(SOS_folder)
print all_files
for current_file in all_files:  # currently working with all files, not just mxds - let's process each one in turn
	if current_file.endswith(".mxd"):  # if the current file is a map document
		mxd_path = os.path.join(SOS_folder, current_file)  # gives us the full path to the file instead of the path relative to the current folder
		mxd = arcpy.mapping.MapDocument(mxd_path) #then open the mxd
		Ai_Folder =SOS_folder
		Ai_Name =os.path.splitext(current_file)[0] + ".ai"
		Ai_Path =os.path.join(Ai_Folder, Ai_Name)
		arcpy.mapping.ExportToAI(mxd, Ai_Path)
		print mxd