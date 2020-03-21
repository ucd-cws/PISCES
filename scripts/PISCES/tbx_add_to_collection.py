'''a quick and dirty way to add all observations to a collection. We should do this a better way, but we don't currently have the time.'''

import sys, os
import arcpy

from PISCES import funcs
from PISCES import local_vars
from PISCES import log

local_vars.start(arc_script=1)

log.initialize("Adding records to collection", arc_script=1)

# we only want data for these species to enter the "collections"
#filter_species = ["PLA01","PET01","PES01","CSB03","CGC01","CGO01","CLE01","CLE02","CLE03","CLS04","CLS05","CRO04","CRO05","CCF01","SOT01","SOT02","SOT03","SOT07","SOT08","SOM03","SOM04","SOM10","SOM11","SOM12","SOM13","SOM14","CAI01","PET02","PLH01","PLR01","PLL01","AAM01","AAT01","CST01","CSB05","CCO02","CCK01","CCP03","CLS01","CLS08","CMC01","CRO07","CCP01","CCS01","SPW01","SOK03","SOC01","CCK02","CCK03","CCG01","EHT01"]

filter_species_full = arcpy.GetParameterAsText(0)
collection = arcpy.GetParameterAsText(1)

filter_species = funcs.parse_input_species_from_list(filter_species_full)

db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
db_insert = db_conn.cursor()

get_collection_id = "select id from defs_collections where collection_name = ?"
c_rows = db_cursor.execute(get_collection_id, collection)
collection_id = c_rows.fetchone().id

log.write("Pulling records", 1)
select_sql = "select objectid, species_id from observations where species_id = ?"
db_cursor.execute(select_sql, filter_species)

insert_sql = "insert into observation_collections (observation_id,collection_id) values (?,?)"

log.write("Filtering and inserting collections", 1)

for row in db_cursor:
	try:
		db_insert.execute(insert_sql, row.objectid, collection_id)
	except:
		#TODO: make this check the actual exception to see if that's what occurred, and note if it isn't
		log.write("A record was not inserted - probably already exists")
		
db_cursor.close()
db_insert.close()
db_conn.commit()
