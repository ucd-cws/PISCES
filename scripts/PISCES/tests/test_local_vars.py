__author__ = 'nickrsan'

import unittest


from PISCES import local_vars
from PISCES import funcs


class ObservationClassTest(unittest.TestCase):

	def test_observation_loading(self):
		my_observation = local_vars.observation()
		my_observation.load(369829)

		# note that these assertions may not be valid if the data changes. If this test starts failing, we'll need to find a stable data source
		self.assertEqual(my_observation.species_id, "SOM04")
		self.assertEqual(my_observation.notes, "copying huc with new obs to hist and expert")
		self.assertEqual(my_observation.zone_id, "180102100103")

		db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "Unit Testing")
		observation2 = local_vars.observation()
		observation2.load(369829, db_cursor=db_cursor)
		self.assertEqual(observation2.species_id, "SOM04")
		self.assertEqual(observation2.notes, "copying huc with new obs to hist and expert")
		self.assertEqual(observation2.zone_id, "180102100103")

		obs3 = local_vars.observation()
		obs3.load(349864, from_table="Invalid_Observations")
		self.assertEqual(obs3.species_id, "SOM09")
		self.assertEqual(obs3.notes, "Moyle 2002")
		self.assertEqual(obs3.zone_id, "181002041308")

		funcs.db_close(db_cursor, db_conn)

class DataLoadTest(unittest.TestCase):
	def test_data_loading(self):
		local_vars.start()
		self.assertGreater(len(local_vars.all_fish.keys()), 0)

if __name__ == '__main__':
	unittest.main()
