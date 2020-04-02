from __future__ import absolute_import, division, print_function

__author__ = 'nickrsan'

import unittest

from PISCES import funcs
from PISCES import local_vars
from PISCES import log


class DataTest(unittest.TestCase):

	def test_observation_record_counts(self):
		query_items = funcs.run_query("select count(*) as colval from (select distinct %s from %s)" % (local_vars.huc_field, local_vars.zones_table))
		query_items2 = funcs.run_query("select count(*) as colval from %s" % local_vars.zones_aux)

		not_same_query_items = funcs.run_query("select count(*) as colval from %s" % (local_vars.zones_table))

		item = query_items[2].fetchone()
		item2 = query_items2[2].fetchone()
		item_not_same = not_same_query_items[2].fetchone()

		self.assertEqual(item.colval, item2.colval)  # the number of HUCs should be the same in the two tables. Zones_Aux should have the same number as the main hucs table.
		self.assertNotEqual(item.colval, item_not_same.colval)  # these should be different because the HUC table has many polygons per HUC sometimes

		query_items[0].close()
		query_items[1].close()
		query_items2[0].close()
		query_items2[1].close()
		not_same_query_items[0].close()
		not_same_query_items[1].close()

	def test_find_missing_records(self):
		hucs_result_set = funcs.run_query("select distinct %s as Zone from %s" % (local_vars.huc_field, local_vars.zones_table))
		zones_aux_result_set = funcs.run_query("select distinct Zone from Zones_Aux")

		hucs = []
		zones_aux = []
		for record in hucs_result_set[2]:
			hucs.append(record.Zone)

		for record in zones_aux_result_set[2]:
			zones_aux.append(record.Zone)

		only_in_hucs = list(set(hucs) - set(zones_aux))
		only_in_zones = list(set(zones_aux) - set(hucs))

		print("HUCs only in HUC 12 Table: %s" % only_in_hucs)
		print("HUCs only in Zone_Aux: %s" % only_in_zones)

		self.assertEqual(0, len(only_in_hucs))
		# we don't assert that there is nothing only in zones because we may have manual cleanup to do

if __name__ == '__main__':
	unittest.main()