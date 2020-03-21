import unittest

from PISCES import api_tools

class APIToolsTest(unittest.TestCase):
	def test_name_lookup_cache(self):
		api_tools.join_assemblage_as_field(
			r"C:\Users\dsx\Code\eflow-species\data\report_update\scratch.gdb\new_flow_sensitive_aggregation_species_v15_2019_02_13",
			"Flow_Sensitive_V2", field_name="assemblage_species_test_1_3_9", key_field="huc_12_string",
			taxonomic_aggregation_level="Species", presence_types=(1, 3, 9))