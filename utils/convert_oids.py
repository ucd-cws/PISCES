__author__ = 'dsx'

""" This script is meant to convert the OGC_FID field to match the objectid field in a table
"""

from PISCES import funcs
from PISCES import local_vars

db_cursor, db_conn = funcs.db_connect(local_vars.maindb)

config_table = "cvas"
config_new_id_col = "OGC_FID"
config_old_id_col = "id"
config_fuzz = False  # temporary measure that allows us to rewrite invalid IDs out of range for one pass. Then we come back through and give them the IDs we want
config_fuzz_range = range(1, 200)  # THIS MUST BE SET WHEN config_fuzz IS TRUE

if config_fuzz:
	print "Fuzzing mixed IDs"
	config_starting_number = int(db_cursor.execute("select max(%s) as maxval from %s" % (config_old_id_col, config_table)).fetchone().maxval) + 1
	fuzz_query = "update %s set %s=? where %s=?" % (config_table, config_new_id_col, config_new_id_col)
	for i in config_fuzz_range:
		if (i % 100) == 0:
			print i
		db_cursor.execute(fuzz_query, config_starting_number, i)
		config_starting_number += 1

config_starting_number = db_cursor.execute("select max(%s) as maxval from %s where %s != %s" % (config_old_id_col, config_table, config_new_id_col, config_old_id_col)).fetchone().maxval
print "Starting with record #" + str(config_starting_number)

i = config_starting_number

update_query = "update %s set %s=? where %s=?" % (config_table, config_new_id_col, config_old_id_col)

while i > 0:
	db_cursor.execute(update_query, i, i)

	if (i % 100) == 0:
		print i
		db_conn.commit()
	i -= 1  # decrement

db_cursor.execute("COMMIT TRANSACTION")
funcs.db_close(db_cursor, db_conn)