import callbacks.common

__author__ = 'Nick'

import unittest

import pyodbc

from PISCES import callbacks
from PISCES import funcs
from PISCES import local_vars
from PISCES import log


class QueryTest(unittest.TestCase):

	def query_setup(self):

		test_query = callbacks.common.query()
		test_query.set_defaults(qc=True)
		test_query.base = "SELECT avg(Average)"
		test_query.tables.append("Species_Aux")
		test_query.where_clauses.append("Species_Aux.FID = Species.FID")
		return test_query

	def run_test(self, query, bind='180200010404'):  # just a huc_id to use for a bind var

		db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
		composed_query = query.compose()

		log.write(composed_query,)
		# if we don't get a cursor object back, then it's a bad query that's generated
		if bind:
			self.assertEqual(type(db_cursor.execute(composed_query, bind)), pyodbc.Cursor)
		else:
			self.assertEqual(type(db_cursor.execute(composed_query)), pyodbc.Cursor)

		funcs.db_close(db_cursor, db_conn)

	def test_basic_query(self):

		test_query = self.query_setup()
		self.run_test(test_query)

	def test_qc_query(self):

		test_query = self.query_setup()
		test_query.make_into_qc()
		self.run_test(test_query)





if __name__ == '__main__':
	unittest.main()
