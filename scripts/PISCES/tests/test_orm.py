__author__ = 'nrsantos'

import unittest

import sqlalchemy

from PISCES import orm_models as orm
from PISCES import api
from PISCES import api_tools


class ComposeQueryTest(unittest.TestCase):

	def test_connection(self):
		orm.connect(r"C:\Users\dsx\Code\PISCES\data\pisces.sqlite")
		session = orm.Session()
		query_data = session.query(orm.Zone)
		for record in query_data:
			# check to make sure we're connected by pulling data out. The ORM doesn't actually attempt to connect until we need to use data
			self.assertTrue(record.HUC_12.startswith("1") or record.HUC_12.startswith("M"))


class TaxonomicLevelTest(unittest.TestCase):
	def setUp(self):
		self.session = api.support.connect_orm(hotload=True)
		pacificus = self.session.query(orm.TaxonomicLevel).filter(sqlalchemy.and_(orm.TaxonomicLevel.scientific_name == "pacificus", orm.TaxonomicLevel.level == "Species"))
		self.hypomesus = pacificus[0]
		self.thaleichthys = pacificus[1]

	def test_confirmation(self):
		"""
			Test that we get the correct species back when we try to confirm species
		:return:
		"""

		hyp_back = self.hypomesus.confirm_tree(parent_scientific_name="Hypomesus", db_session=self.session)
		self.assertEqual(hyp_back.parent_level.scientific_name, "Hypomesus")
		self.assertIs(self.hypomesus, hyp_back)
		thal_back = self.hypomesus.confirm_tree(parent_scientific_name="Thaleichthys", db_session=self.session)
		self.assertEqual(thal_back.parent_level.scientific_name, "Thaleichthys")
		self.assertIsNot(self.hypomesus, thal_back)

		# make sure it also throws an error if we provide a genus that isn't a parent of this species
		with self.assertRaises(ValueError):
			self.hypomesus.confirm_tree(parent_scientific_name="non_existent_genus", db_session=self.session)

	def test_get_taxonomy(self):
		"""
			Confirm that the function that handles getting the taxon in a safe manner does it correctly. Makes sure that
			when we request two species with the same name via `get_taxonomy`, it returns the correct one in each case
		:return:
		"""
		hypomesus = api_tools.get_taxonomy(scientific_name="pacificus", level="Species", session=self.session, parent_scientific_name="Hypomesus")
		thaleichthys = api_tools.get_taxonomy(scientific_name="pacificus", level="Species", session=self.session, parent_scientific_name="Thaleichthys")

		self.assertEqual(hypomesus.parent_level.scientific_name, self.hypomesus.parent_level.scientific_name)
		self.assertEqual(thaleichthys.parent_level.scientific_name, self.thaleichthys.parent_level.scientific_name)

	def test_get_common_name(self):
		# test a highly aggregated species
		self.assertEqual("Chinook salmon", api_tools.get_common_name_from_species_string(scientific_name="Salmonidae Oncorhynchus tshawytscha",
																 						 level="Species"))
		# test a species with no aggregation
		self.assertEqual("Mountain whitefish", api_tools.get_common_name_from_species_string(scientific_name="Salmonidae Prosopium williamsoni",
																 						 level="Species"))
		# test a species with confusion (a name collision at species level)
		self.assertEqual("Delta smelt", api_tools.get_common_name_from_species_string(scientific_name="Osmeridae Hypomesus pacificus",
																 						 level="Species"))
		# test a species with spaces in its species string
		self.assertEqual("Roach (symmetricus x venustus)", api_tools.get_common_name_from_species_string(scientific_name="Cyprinidae Hesperoleucus symmetricus x venustus",
																						level="Species"))
		# test a family
		self.assertEqual("Salmonids", api_tools.get_common_name_from_species_string(scientific_name="Salmonidae Oncorhynchus tshawytscha",
																						level="Family"))
		self.assertEqual("Salmonids", api_tools.get_common_name_from_species_string(scientific_name="Salmonidae",
																						level="Family"))
		# test a genus
		self.assertEqual("Salmonids", api_tools.get_common_name_from_species_string(scientific_name="Salmonidae Oncorhynchus tshawytscha",
																						level="Genus"))
		self.assertEqual("Salmonids", api_tools.get_common_name_from_species_string(scientific_name="Salmonidae Oncorhynchus",
																						level="Genus"))
