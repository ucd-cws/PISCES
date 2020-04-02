from __future__ import absolute_import, division, print_function

__author__ = 'dsx'

import unittest
import os
import timeit
from operator import itemgetter

from PISCES import api
from PISCES import orm_models
from PISCES import local_vars

from PISCES.tbx_query_sources import look_up_records


class GetObservationRecordsForHUCsTest(unittest.TestCase):

	def test_basic(self):
		records = api.get_observation_records_for_hucs(["180201040504", "180201040502"], ["CMC01"])
		for record in records:
			self.assertIsInstance(record, orm_models.Observation)

	def test_performance(self):
		"""
			The performance of ArcMap seems to degrade after running the Look Up Records tool a handful of times
		:return:
		"""

		for i in range(0, 50):
			time_val = timeit.timeit(self._performance_individual_call, number=1)
			print(time_val)
			self.assertLess(time_val, 10)

	def _performance_individual_call(self):
		layer = os.path.join(local_vars.internal_workspace, "scripts", "PISCES", "tests", "Test_Layer.gdb", "GetObservationRecordsForHUCs_test_performance")

		table = look_up_records(layer, '', '', '')
		self.assertIsNotNone(table)
		self.assertGreater(len(table), 0)  # assert that its path has characters

	def test_counts_species_in_group_by_huc(self):
		counts = api.counts.count_species_in_group_by_huc("Flow_Sensitive", (1,3,9))
		self.assertLess(counts.count(), 3200)  # was 3097 at last check

		max_num_species_in_huc = max(counts, key=itemgetter(1))[1]  # get the max value in any huc
		self.assertLess(max_num_species_in_huc, 30)  # was 27 at last check

class GetDistinctTaxonomicNamesInGroupAsListTest(unittest.TestCase):

	def test_invalid(self):
		"""
			Tests providing an invalid aggregation level and speceis group
		:return:
		"""

		self.assertRaises(ValueError, api.listing.get_distinct_taxonomic_names_in_group_as_list, level="order", group_name="Native_Fish")
		family_in_invalid_group = api.listing.get_distinct_taxonomic_names_in_group_as_list(level="family", group_name="blorblat")
		self.assertEqual(len(family_in_invalid_group), 0)

	def test_group_filter(self):
		"""
			Make sure the group filter actually works by comparing the number of returned values with and without it
		:return:
		"""

		all_families = api.listing.get_distinct_taxonomic_names_in_group_as_list(level="family")
		native_fish = api.listing.get_distinct_taxonomic_names_in_group_as_list(level="family", group_name="Native_Fish")

		self.assertLess(len(native_fish), len(all_families))

	def test_family_in_native_fish(self):
		pass

class CheckGroupNameTest(unittest.TestCase):

	def setUp(self):
		self.session = api.support.connect_orm(hotload=False)

	def test_invalid_name(self):
		self.assertRaises(ValueError, api.support._check_group_name, "nonexistentGroup", self.session)

	def test_valid_name(self):
		self.assertTrue(api.support._check_group_name("Native_Fish", self.session))


class GetHUCsForGroupAsListTest(unittest.TestCase):
	def test_filtering_by_group(self):
		native_list = api.listing.get_hucs_for_group_as_list("Native_Fish", "1,3,6,7,9")
		print("\nNative List: {}".format(len(native_list)))
		anadromous_list = api.listing.get_hucs_for_group_as_list("Anadromous", "1,3,6,7,9")
		print("Anadromous List: {}".format(len(anadromous_list)))
		self.assertLess(len(anadromous_list), len(native_list))


class GetPresenceByTaxaTest(unittest.TestCase):
	def test_aggregation(self):
		subspecies_level = api.presence.get_presence_by_taxa("Flow_Sensitive",)
		species_level = api.presence.get_presence_by_taxa("Flow_Sensitive",
															 taxonomic_aggregation_level="species",)
		genus_level = api.presence.get_presence_by_taxa("Flow_Sensitive",
															 taxonomic_aggregation_level="genus",)
		family_level = api.presence.get_presence_by_taxa("Flow_Sensitive",
															 taxonomic_aggregation_level="family",)

		subspecies_count = len(subspecies_level)
		species_count = len(species_level)
		genus_count = len(genus_level)
		family_count = len(family_level)

		print("Counts. subspecies: {}, species: {}, genus: {}, family: {}".format(subspecies_count, species_count, genus_count, family_count))

		self.assertLess(family_count, genus_count)
		self.assertLess(genus_count, species_count)
		self.assertLess(species_count, subspecies_count)

		self.records = subspecies_level
		self._check_for_cls05(subspecies_level)

	def _check_for_cls05(self, records):
		for record in records:
			if record.taxon == "CLS05" and record.zone_id == "180400130701":
				raise ValueError("CLS05 shows up in zone it's not in (180400130701)")

		for record in records:
			if record.taxon == "CLS05" and record.zone_id == "180500020801":
				break
		else:
			raise ValueError("CLS05 doesn't show up in zone it's supposed to be in (180500020801)")

	def test_general_presence(self):
		cls05 = api.presence.get_presence_by_taxa("CLS05")
		self._check_for_cls05(cls05)


class GetPresenceByHUCSetTest(unittest.TestCase):
	def test_cluster(self):
		"""
			Simulating sending a cluster of HUCs into the DB and getting back the list of species
		:return:
		"""

		# these came from the 12/21/2018 run of clustering - it's for Great Basin cluster 4
		cluster_hucs = [u'160501020504', u'160501020503', u'160501010102', u'160503010101', u'160503020102', u'160503020101', u'160503020103', u'160503020104', u'160503020105', u'160502010103', u'160501020203', u'160501020102', u'160501020101', u'160502010301', u'160501010301', u'160502010302', u'160501010303', u'160501010401', u'160501010402', u'160501010403', u'160501020204', u'160501020201', u'160501020206', u'160503010302', u'160503010206', u'160503010208', u'160503010303', u'160501010202', u'160501010500', u'160501010101', u'160501020202', u'160503010103', u'160503010102', u'160503010105', u'160503010108', u'160503010109', u'160503010104', u'160503010204', u'160503010110', u'160503010107', u'160503020107', u'160503020106', u'160503010301', u'160503020108', u'160503010106', u'160503020201', u'160503020203', u'160503020202', u'160502010102', u'160502010101', u'160502010104', u'160502010105', u'160503020205', u'160502010106', u'160502010107', u'160502010108', u'160501020205', u'160501020104', u'160501020107', u'160501020106', u'160501020103', u'160501020105', u'160503010205', u'160503010304', u'160503020304', u'160503020302', u'160503020204', u'160503020207', u'160503020206', u'160503020401', u'160502010202', u'160502010201', u'160502010203', u'160501010302', u'160502010304', u'160502010303', u'160501020501', u'160503010201']

		actual_species = [u'Paiute cutthroat trout', u'Lahontan speckled dace', u'Lahontan mountain sucker', u'Lahontan stream tui chub', u'Tahoe sucker', u'Paiute sculpin', u'Lahontan redside', u'Lahontan cutthroat trout', u'Mountain whitefish']
		actual_species_set = set(actual_species)

		assemblage = api.presence.get_presence_by_huc_set("Flow_Sensitive_V2", cluster_hucs, "common_name", "1,3,9")

		missing_species = list(actual_species_set - set(assemblage))
		self.assertEqual(0, len(missing_species))

		extra_species = list(set(assemblage) - actual_species_set)
		self.assertEqual(0, len(extra_species))

		print(assemblage)




