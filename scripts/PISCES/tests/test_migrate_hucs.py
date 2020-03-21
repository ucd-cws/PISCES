__author__ = 'nickrsan'

import unittest

from PISCES.migrate_hucs import huc_change, huc_change_order, find_new_huc12s
from PISCES import migrate_hucs
from PISCES import log
from PISCES import funcs
from PISCES import local_vars
from PISCES.tests import test_data


class HUCChangeSortTest(unittest.TestCase):

	def localsetup(self):
		self.db_cursor, self.db_conn = funcs.db_connect(local_vars.maindb, "testing: test_migrate_hucs.py")

	def test_find_new_huc12s(self):
		self.localsetup()

		all_new = migrate_hucs.load_hucs(self.db_cursor, local_vars.zones_table)
		all_old = migrate_hucs.load_hucs(self.db_cursor, migrate_hucs.old_layer_name)
		new_hucs, extirpated_hucs = find_new_huc12s(self.db_cursor, migrate_hucs.old_layer_name, local_vars.zones_table)

		log.write("New HUCs Len: %s" % len(all_new), 1)
		log.write("Old HUCs Len: %s" % len(all_old), 1)
		log.write("Brand New HUCs Len: %s" % len(new_hucs), 1)
		log.write("Extirpated HUCs Len: %s" % len(extirpated_hucs), 1)

		self.assertIn('180701060101', all_old)
		self.assertIn('180701060101', all_new)
		self.assertNotIn('180701060101', extirpated_hucs)
		self.assertNotIn('180701060101', new_hucs)

	def test_unit_test_runner(self):
		"""
		Won't fail unless execution itself fails
		:return:
		"""
		migrate_hucs.run_data_unit_tests([test_data, ])

	def test_verify(self):
		self.localsetup()
		log.write("Loading migrations and finding affected database records", 1)
		migrate_hucs.load_migrations(migrate_hucs.migs_file, migrate_hucs.primary_key, migrate_hucs.secondary_key, migrate_hucs.migration_items)  # load the data from the migrations file

		log.write("Finding affected records and loading data", 1)
		changes, source_hucs_only = migrate_hucs.find_affected(migrate_hucs.migration_items, migrate_hucs.changes, 0, migrate_hucs.other_tables_field, migrate_hucs.additional_tables, self.db_conn)

		new_hucs, extirpated_hucs = find_new_huc12s(self.db_cursor, migrate_hucs.old_layer_name, local_vars.zones_table)
		migrate_hucs.verify(source_hucs_only, migrate_hucs.master_tables, migrate_hucs.additional_tables, extirpated_hucs, self.db_cursor)

	def test_sort_changes(self):
		"""
			Was going to be a test for PISCES.migrate_hucs.huc_change_order, but ended up not needing that code. Leaving
			here in case it's ressurected
		"""


		return True



		a, b, c, d, e, f = huc_change()
		a.source = "180101"
		a.destination = "180102"
		b.source = "180102"
		b.destination = "180103"
		c.source = "180103"
		c.destination = "180104"
		d.source = "180104"
		d.destination = "180107"
		e.source = "180105"
		e.destination = "180104"
		f.source = "180105"
		f.destination = "180106"

		mylist = [f, a, e, b, d, c]

		mylist_sort = sorted(mylist, cmp=huc_change_order)
		asserted_list = [d, e, c, b, a, f]

		self.assertEqual(mylist_sort, asserted_list)



if __name__ == '__main__':
	unittest.main()
