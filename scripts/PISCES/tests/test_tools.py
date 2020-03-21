import unittest
import tempfile

import numpy

from PISCES import tbx_make_clusters
from PISCES import tbx_make_matrix
from PISCES import local_vars

class TestTools(unittest.TestCase):

	def test_clustering(self):
		tbx_make_clusters.make_species_clusters(r"C:\Users\dsx\Code\eflow-species\data\report_update\working_scratch.gdb\june_2018_current_notrans_neighbors_7to10",\
												presence_values="1,3,9",
												min_species=0,
												num_groups=(4, 5, 6, 7),
												huc_regions=r"C:\Users\dsx\Code\eflow-species\data\report_update\regions.gdb\regions_without_desert",
												region_group_field="huc_region_group",
												spatial_constraint="CONTIGUITY_EDGES_CORNERS")

class TestTbxMakeMatrix(unittest.TestCase):
	def test_matrix_aggregation(self):
		taxa_folder = tempfile.mkdtemp(prefix="pisces_test")
		matrix_taxa = tbx_make_matrix.make_matrix("Native_Fish", taxa_folder, true_value=1, false_value=0, aggregation=None)
		species_folder = tempfile.mkdtemp(prefix="pisces_test")
		matrix_species = tbx_make_matrix.make_matrix("Native_Fish", species_folder, true_value=1, false_value=0, aggregation="species")
		genus_folder = tempfile.mkdtemp(prefix="pisces_test")
		matrix_genus = tbx_make_matrix.make_matrix("Native_Fish", genus_folder, true_value=1, false_value=0, aggregation="genus")
		family_folder = tempfile.mkdtemp(prefix="pisces_test")
		matrix_family = tbx_make_matrix.make_matrix("Native_Fish", family_folder, true_value=1, false_value=0, aggregation="family")

		self.assertLess(matrix_family["data_frame"].size, matrix_genus["data_frame"].size)
		self.assertLess(matrix_genus["data_frame"].size, matrix_species["data_frame"].size)
		self.assertLess(matrix_species["data_frame"].size, matrix_taxa["data_frame"].size)

		self.assertLess(numpy.count_nonzero(matrix_family["data_frame"].values), numpy.count_nonzero(matrix_genus["data_frame"].values))
		self.assertLess(numpy.count_nonzero(matrix_genus["data_frame"].values), numpy.count_nonzero(matrix_species["data_frame"].values))
		self.assertLess(numpy.count_nonzero(matrix_species["data_frame"].values), numpy.count_nonzero(matrix_taxa["data_frame"].values))

		# now test some roach records at different levels - they're geographically distinct, but should merge as we go from
		# taxon to species to genus
		taxon_present_huc = "180500020801"
		taxon_absent_huc = "180400130701"  # will be present when we move to species level, but should be absent for CLS05
		genus_present_huc = "180101090103"
		all_absent_huc = "180400121002"
		# first confirm the matrix is present and absent for one of the species correctly
		self.assertEqual(1, matrix_taxa["data_frame"][tbx_make_matrix._make_safe_field_name("CLS05", taxa_info=local_vars.all_fish, name_attribute="species")][taxon_present_huc])
		self.assertEqual(0, matrix_taxa["data_frame"][tbx_make_matrix._make_safe_field_name("CLS05", taxa_info=local_vars.all_fish, name_attribute="species")][taxon_absent_huc])
		self.assertEqual(0, matrix_taxa["data_frame"][tbx_make_matrix._make_safe_field_name("CLS05", taxa_info=local_vars.all_fish, name_attribute="species")][all_absent_huc])

		# then confirm that it's present in both at the species level, while still being absent where no roach are
		self.assertEqual(1, matrix_species["data_frame"][tbx_make_matrix._make_safe_field_name("symmetricus", taxa_info=local_vars.all_fish)][taxon_present_huc])
		self.assertEqual(1, matrix_species["data_frame"][tbx_make_matrix._make_safe_field_name("symmetricus", taxa_info=local_vars.all_fish)][taxon_absent_huc])
		self.assertEqual(0, matrix_species["data_frame"][tbx_make_matrix._make_safe_field_name("symmetricus", taxa_info=local_vars.all_fish)][genus_present_huc])
		self.assertEqual(0, matrix_species["data_frame"][tbx_make_matrix._make_safe_field_name("symmetricus", taxa_info=local_vars.all_fish)][all_absent_huc])

		# now try it at the genus level
		self.assertEqual(1, matrix_genus["data_frame"][tbx_make_matrix._make_safe_field_name("Hesperoleucus", taxa_info=local_vars.all_fish)][taxon_present_huc])
		self.assertEqual(1, matrix_genus["data_frame"][tbx_make_matrix._make_safe_field_name("Hesperoleucus", taxa_info=local_vars.all_fish)][taxon_absent_huc])
		self.assertEqual(1, matrix_genus["data_frame"][tbx_make_matrix._make_safe_field_name("Hesperoleucus", taxa_info=local_vars.all_fish)][genus_present_huc])
		self.assertEqual(0, matrix_genus["data_frame"][tbx_make_matrix._make_safe_field_name("Hesperoleucus", taxa_info=local_vars.all_fish)][all_absent_huc])

	if __name__ == "__main__":
		unittest.main()