'''a quick and dirty way to add all observations to a collection. We should do this a better way, but we don't currently have the time.'''

import arcpy
import sys, os

try:
	from _winreg import *
	registry = ConnectRegistry("", HKEY_CURRENT_USER)  # open the registry
	base_folder = QueryValue(registry, "Software\CWS\PISCES\location")  # get the PISCES location
	CloseKey(registry)
except:
	print "can't start! can't find pisces in registry"
	try:
		import log
		log.initialize()
		log.error("Unable to get base folder")
	except:
		print "Can't find log module"
	sys.exit()


sys.path.append(os.path.join(base_folder,"scripts","PISCES"))
import funcs, local_vars, log

local_vars.set_workspace_vars(base_folder) # set up the workspace to the location

from script_tool_funcs import *

log.initialize("Adding records to collection")

# we only want data for these species to enter the "collections"
#filter_species = ["PLA01","PET01","PES01","CSB03","CGC01","CGO01","CLE01","CLE02","CLE03","CLS04","CLS05","CRO04","CRO05","CCF01","SOT01","SOT02","SOT03","SOT07","SOT08","SOM03","SOM04","SOM10","SOM11","SOM12","SOM13","SOM14","CAI01","PET02","PLH01","PLR01","PLL01","AAM01","AAT01","CST01","CSB05","CCO02","CCK01","CCP03","CLS01","CLS08","CMC01","CRO07","CCP01","CCS01","SPW01","SOK03","SOC01","CCK02","CCK03","CCG01","EHT01"]

filter_species = ["CCO01"]

db_cursor,db_conn = funcs.db_connect(local_vars.maindb)
db_insert = db_conn.cursor()

log.write("Pulling records",1)
select_sql = "select Observations.OBJECTID, Observations.Species_ID from Observations, Species where Observations.Species_ID = Species.FID and Species.Native = TRUE"
db_cursor.execute(select_sql)

insert_sql = "insert into Observation_Collections (Observation_ID,Collection_ID) values (?,4)"

log.write("Filtering and inserting collections",1)

for row in db_cursor:
	# check if it's a species we want to mark as good
	if row.Species_ID in filter_species:
		try:
			db_insert.execute(insert_sql,row.OBJECTID)
		except:
			pass
		
db_cursor.close()
db_insert.close()
db_conn.commit()
