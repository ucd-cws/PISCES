import os
import unittest

from PISCES import tbx_make_clusters

eflows_folder = r"C:\Users\dsx\Code\eflow-species"


class MakeClustersTest(unittest.TestCase):
	def test_new_flow_sensitive_2018_12_21(self):
		presence_types = "1,3,9"
		spatial_constraint = "CONTIGUITY_EDGES_CORNERS"
		aggregation_level = "species"
		new_name = "new_flow_sensitive_aggregation_{}_v15_2019_02_13".format(aggregation_level)
		output_path = os.path.join(eflows_folder, r"data\report_update\scratch.gdb\{}".format(new_name))
		tbx_make_clusters.make_species_clusters(output_path=output_path,
												group_name="Flow_Sensitive_V2",
												presence_values=presence_types,  # current presence without translocations
												min_species=1,
												# this is a shortcut to remove all the out of state areas - don't cluster empty areas
												num_groups=(3, 4, 5, 6, 7, 8, 9, 10, 11, 12),  # added two because great_basin region is especially wonky - see what happens with only two groups
												huc_regions=os.path.join(eflows_folder, r"data\regions\regions.gdb\regions_noesturary_nodesert_2018_09_17"),
												region_group_field="huc_region_group",
												aggregation=aggregation_level,
												spatial_constraint=spatial_constraint,
												report_folder=os.path.join(eflows_folder, "data", "report_update", new_name))