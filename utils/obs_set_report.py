import os

from PISCES import local_vars,funcs

groups = { # group name then comma separated list of observation set ids
	"CNDDB":"224",
	"EMAP":"225",
	"FERC":"182,183,184,185,186,187",
	"TU":"239,240,241,242,243",
	"CVSalmonid": "218,219,220,221,222,223",
	"Moyle":"1,2,3,4,6,7,9,12,13,14,15,16,17,18,20,21,22,24,25,26,27,29,30,31,32,33,34,37,38,39,40,41,42,43,44,45,46,47,48,49,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173",
	"USFS":"53,55,56,54,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,5,8,10,11,19,23,28,35,36",
	"BIOS":"81,82",
	"CalFish":"227,228",
	"Expert":"174",
	"Various Supporting":"230,231,232,233,234,235,236,237,238,226,244,245,246,247,248",
}

queries = {
	"Num Datasets with Data":"select count(*) as num from (select distinct Set_ID from Observations where Set_ID in (?))",
	"Num Records":"select count(*) as num from Observations where Set_ID in (?)",
	"Num QC Records":"select count(*) as num from Observations, Observation_Collections where Set_ID in (?) and Observations.OBJECTID = Observation_Collections.Observation_ID and Observation_Collections.Collection_ID in (1,3)",
}

def output_write(value):
	print value,
	global export
	export.write(value)

db_cursor,db_conn = funcs.db_connect(local_vars.maindb)
export = open(os.path.join(os.getcwd(),"data_out.csv"),'w')

output_write("Group,")
ordered_queries = []
for query in queries: # so, we're going through the queries
	ordered_queries.append(query) # and adding them to the list because we want this to be the ONLY order that this dictionary is traversed in
	output_write(query + ",")
output_write("\n") # header row done

for group in groups:
	output_write(group + ",")
	for query in ordered_queries:
		t_query = queries[query].replace('?',groups[group]) # # access doesn't like the "IN" query when we pass in the list as a bind var. So, we're replacing it now by creating a copy then replacing the bind var
		#print "running %s" % t_query
		results = db_cursor.execute(t_query)
		for result in results: # there should only be one, but we don't care about efficiency
			output_write(str(result.num) + ",")
	output_write("\n")
	
export.close()
funcs.db_close(db_cursor,db_conn)