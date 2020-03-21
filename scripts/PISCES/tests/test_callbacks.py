__author__ = 'nrsantos'

import unittest

import arcpy

from PISCES import funcs
from PISCES import log
from PISCES import local_vars
from PISCES import mapping
from PISCES import callbacks

class ComposeQueryTest(unittest.TestCase):

	def setup(self):
		pass


class ExportRasterTest(unittest.TestCase):

	def setup(self):
		log.initialize("Running tests")
		local_vars.data_setup()
		self.db_cursor, self.db_conn = funcs.db_connect(local_vars.maindb, "Testing")

	def test_basic_export(self):

		self.setup()

		self.query = mapping.custom_query(query="select distinct Observations.Zone_ID from Observations, Observation_Collections where Species_ID = ? And Presence_Type = 3 and Observations.OBJECTID = Observation_Collections.Observation_ID and Observation_Collections.Collection_ID = 5",
										  callback="export_raster",
										  callback_arguments="3::270::%s::%s" % (local_vars.HUCS, local_vars.workspace)
			)
		self.map_layer = mapping.map_layer(query=self.query, bind_v="CMC01")

		self.map_layer.populate(self.db_cursor)
		arcpy.MakeFeatureLayer_management(local_vars.HUCS, "zones_layer")
		self.map_layer.make("zones_layer", db_cursor=self.db_cursor)

		self.assertTrue(arcpy.Exists(self.map_layer.layer_name))

