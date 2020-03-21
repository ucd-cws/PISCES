from __future__ import print_function

import local_vars

__author__ = 'nrsantos'

import unittest
import sys

import arcpy

from PISCES import local_vars
from PISCES import script_tool_funcs
from PISCES import log
from PISCES import mapping
from PISCES import funcs

num_hucs_total = int(arcpy.GetCount_management(local_vars.HUCS).getOutput(0))
local_vars.debug = False  # run it like end users will

def assertNumHUCsEqual(self, feature_class, number_hucs):
	"""
	handles the work of loading a HUC12 layer and figuring out how many HUC12s it has
	:param layer: the feature class to check
	:param number_hucs: the number of hucs we're asserting it has
	:return:
	"""

	count = int(arcpy.GetCount_management(feature_class).getOutput(0))
	self.assertEqual(count, number_hucs)


def assertHUCsIn(self, hucs, layer):
	"""
	Given a list of HUC_12 IDs, this function asserts that each HUC_12 ID is in the provided layer
	:param hucs: list: list of HUC_12 IDs
	:param layer: an ArcGIS feature class or feature layer with a HUC_12 field
	:return: None - asserts
	"""

	hucs_in_layer = funcs.hucs_to_list(layer)
	for huc in hucs:
		self.assertIn(huc, hucs_in_layer)


class ReplaceVariablesTest(unittest.TestCase):
	def setup(self):
		script_tool_funcs.get_location()
		log.initialize(arc_script=True)
		local_vars.initialize()

	def test_dict_lookup(self):
		"""
			Terence, I'm not sure why this test exists...? What are we testing for here?
		:return:
		"""
		self.setup()
		self.assertIn("CMC01", local_vars.all_fish)
		print("success")
		self.setup()
		self.assertIn("CMC01", local_vars.all_fish)
		print("success")
		self.setup()
		self.assertIn("CMC01", local_vars.all_fish)
		print("success")
		self.setup()
		self.assertIn("CMC01", local_vars.all_fish)
		print("success")
		self.setup()
		self.assertIn("CMC01", local_vars.all_fish)
		# see note near main block below for why we do this many times in a row


		# All this code was because I thought that the test need to be run across multiple executions
		# turns out it stemmed from being run many times in the same execution
		#run_secondary_dict_lookup()
		#run_secondary_dict_lookup()

		#for i in range(1, 4):
		#	try:
		#		subprocess.check_call(["python", os.path.abspath(__file__)])
		#		print("Run %s times" % i)
		#	except:
		#		print("FAILED")
		#		raise ValueError("Fish id is not in dictionary")


def run_secondary_dict_lookup():
	script_tool_funcs.get_location()
	log.initialize(arc_script=True)
	local_vars.initialize()

	if "alabaster" in local_vars.all_fish:
		print("EXCEPTION - lookup succeeded - 'alabaster' should not exist")
		sys.exit(1)

	if "CMC01" not in local_vars.all_fish:
		sys.exit(1)

	if len(local_vars.all_fish.keys()) == 0:
		sys.exit(1)

	try:
		mapping.begin("all", return_maps=True)  # run the maps and get the objects
	except:
		sys.exit(1)


class MakeLayerTest(unittest.TestCase):

	# TODO: Need to do some basic testing of the supporting functions (assertHUCsIn, get_num_records, etc)
	def setup(self, query="select distinct HUC_12 as Zone_ID from HUC12FullState", bind=None, ):

		local_vars.config_metadata = False
		self.zones_layer_name = "z_layer"

		self.db_cursor, self.db_conn = funcs.db_connect(local_vars.maindb)

		# create the query
		self.map_layer = mapping.map_layer(query=None, bind_v=bind, parent=None, text_query=query)

		self.map_layer.populate(self.db_cursor)

	def get_num_records(self, huc_12s):
		"""
			Since there can be multiple HUC_12 polygons per HUC_12 ID, for some comparisons, we need to get the actual number of records.
			This function gets the number of records in the HUC12 table for the corresponding list of HUCs
		:param huc_12s: list: the huc_12 IDs to determine the number of records for
		:return: int: count of the number of records
		"""

		hucs_str = str(list(set(huc_12s))).strip("[]").replace("u", "")  # modification of a nice little trick from http://www.decalage.info/en/python/print_list
		query = "select count(*) as count from %s where %s in (%s)" % (local_vars.zones_table, local_vars.huc_field, hucs_str)

		record = self.db_cursor.execute(query).fetchone()
		return int(record.count)

	def close_item(self):
		if 'db_cursor' in self.__dict__:
			self.db_cursor.close()
			del self.db_cursor
		if 'db_conn' in self.__dict__:
			self.db_conn.close()
			del self.db_conn

		if 'zones_layer_name' in self.__dict__ and arcpy.Exists(self.zones_layer_name):
			arcpy.Delete_management(self.zones_layer_name)
			del self.zones_layer_name

	def huc_limit(self, limit=500):
		try:
			self.setup(query="select distinct zone_id from %s limit %s" % (local_vars.observations_table, limit))
			self.num_records = self.get_num_records(self.map_layer.zones)
			returned_features = self.map_layer.make(db_cursor=self.db_cursor)

			assertHUCsIn(self, self.map_layer.zones, returned_features)
			assertNumHUCsEqual(self, returned_features, self.num_records)
		finally:
			self.close_item()

	def test_make_with_provided_zones(self, zones_layer=local_vars.HUCS):

		try:
			self.setup(query="select distinct zone_id from %s where zone_id LIKE '1806000507__'" % local_vars.observations_table)

			arcpy.MakeFeatureLayer_management(zones_layer, self.zones_layer_name)
			self.num_records = self.get_num_records(self.map_layer.zones)

			returned_features = self.map_layer.make(zone_layer=self.zones_layer_name, db_cursor=self.db_cursor)

			assertHUCsIn(self, self.map_layer.zones, returned_features)
			assertNumHUCsEqual(self, returned_features, self.num_records)
		finally:
			self.close_item()

	def test_makes_own_zones(self):

		try:
			self.setup(query="select distinct zone_id from %s where zone_id LIKE '1806000507__'" % local_vars.observations_table)
			self.num_records = self.get_num_records(self.map_layer.zones)

			returned_features = self.map_layer.make(db_cursor=self.db_cursor)

			assertHUCsIn(self, self.map_layer.zones, returned_features)
			assertNumHUCsEqual(self, returned_features, self.num_records)

		finally:
			self.close_item()

	def test_no_zones(self):
		try:
			self.setup(query="select distinct zone_id from %s where zone_id LIKE 'ZZZ_________'" % local_vars.observations_table)  # should select no zones
			self.assertEqual(len(self.map_layer.zones), 0)  # assert that we got no zones so that if something changes, the test breaks

			returned_features = self.map_layer.make(db_cursor=self.db_cursor)

			self.assertEqual(returned_features, None)  # returned_features should be None in the case of zero HUCs - larger mapping relies on a different mechanism, but API layers require this

		finally:
			self.close_item()

	def test_single_zone(self):
		try:
			self.setup(query="select distinct zone_id from %s where zone_id='180201160310'" % local_vars.observations_table)  # select just one zone
			self.assertEqual(len(self.map_layer.zones), 1)  # assert that we have just a single zone so that if something changes, the test breaks

			returned_features = self.map_layer.make(db_cursor=self.db_cursor)
			assertHUCsIn(self, ['180201160310', ], returned_features)
			assertNumHUCsEqual(self, returned_features, self.get_num_records(['180201160310']))

		finally:
			self.close_item()

	def test_many_hucs(self):
		"""
			This test is designed to help us make sure that many different huc numbers all come back correctly from small to large so that we validate any changes to the chunking strategy
		:return:
		"""
		self.huc_limit(25)
		self.huc_limit(80)
		self.huc_limit(228)
		self.huc_limit(385)
		self.huc_limit(500)
		self.huc_limit(503)  # check that we can nail both 500 and just a few more (on the batching line, right now
		self.huc_limit(1002)
		self.huc_limit(1744)
		self.huc_limit(2000)
		self.huc_limit(2006)
		self.huc_limit(3539)
		self.huc_limit(4018)

		db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
		all_zones = db_cursor.execute("select count(*) as count from %s" % local_vars.zones_table).fetchone().count
		db_cursor.close()
		db_conn.close()

		self.huc_limit(all_zones)  # get the count of all zones and try that
		self.huc_limit(all_zones - 3)  # and try just slightly less


if __name__ == "__main__":
	# If this script is invoked directly, then it means we're running the secondary tests
	# One issue that cropped up only appeared when something was run multiple times in a row.
	# To replicate better, we'll invoke this as a subprocess from a master in order to check

	run_secondary_dict_lookup()
	sys.exit(0)

	#results = unittest.TestResult()
	#loader = unittest.defaultTestLoader
	#test_suite = loader.loadTestsFromName('PISCES.tests.test_mapping.ReplaceVariablesTest.run_secondary_dict_lookup')
	#test_suite.run(results)
	#sys.exit(0)