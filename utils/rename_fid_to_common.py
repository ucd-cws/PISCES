import sys, os, re

working_dir = os.getcwd()

try:
	from _winreg import *
	registry = ConnectRegistry("", HKEY_CURRENT_USER)  # open the registry
	base_folder = QueryValue(registry, "Software\CWS\PISCES\location")  # get the PISCES location
	CloseKey(registry)
	sys.path.append(os.path.join(base_folder, "scripts", "PISCES"))
except:
	log.error("Unable to get base folder")
	sys.exit()
    
import local_vars
import funcs
    
local_vars.set_workspace_vars(base_folder) # set up the workspace to the location
db_cursor,db_conn = funcs.db_connect(local_vars.maindb)

files = os.listdir(working_dir)

l_query = "select Common_Name as Name from Species where FID = ?"
for file in files:
	if file == "rename.py": # skip itself
		continue
		
	print "%s" % file
	full_path = os.path.join(working_dir,file)
	
	try:
		l_fid_match = re.search("(\w{3}\d{2})",file)
		l_fid = l_fid_match.group(0)
	except:
		print "skipping...\n"
		continue
		
	l_results = db_cursor.execute(l_query,l_fid)
	for result in l_results: # should only be one
		file = file.replace(l_fid,result.Name)
	
	new_full_path = os.path.join(working_dir,file)
	try:
		os.rename(full_path, new_full_path)
	except:
		print "need to manually rename %s to %s" % (full_path, new_full_path)
		
	print "renamed to %s\n" % file

print "done"
