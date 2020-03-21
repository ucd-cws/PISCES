__author__ = 'nrsantos'

"""
	Compares two layer caches and checks that they have all the same files and spits out a report with the centroid
	distance and percent overlap of each layer
"""


import os
import csv
import arcpy

from PISCES import log
from PISCES import comparison
from PISCES import funcs
from PISCES import local_vars

resume = True  # should we resume from a previous run?
resume_item = "SOM09"
compare_limited_list = True
compare_only_species = ["f_AAM01_1", "f_AAM01_16", "f_AAM01_2", "f_AAT01_1", "f_AAT01_16", "f_AAT01_2", "f_CAI01_16",
						"f_CAI01_17", "f_CCA02_1", "f_CCA02_16", "f_CCA02_17", "f_CCA02_2", "f_CCA04_1", "f_CCA04_16",
						"f_CCA04_2", "f_CCB01_2", "f_CCF01_17", "f_CCG01_1", "f_CCG01_16", "f_CCG01_2", "f_CCO01_1",
						"f_CCO01_16", "f_CCO01_17", "f_CCO01_2", "f_CCO03_1", "f_CCO03_16", "f_CCO04_1", "f_CCO04_16",
						"f_CCR01_1", "f_CCR01_16", "f_CCR01_2", "f_CCS02_17", "f_CFP01_1", "f_CFP01_16", "f_CGE01_16",
						"f_CGO01_16", "f_CGO01_17", "f_CLA01_1", "f_CLA01_16", "f_CLA01_2", "f_CLE03_1", "f_CLE03_16",
						"f_CLS01_1", "f_CLS01_16", "f_CLS05_16", "f_CLS07_16", "f_COM01_1", "f_COM01_16", "f_CPG01_1",
						"f_CPG01_16", "f_CPG01_17", "f_CPG01_2", "f_CRO01_1", "f_CRO01_16", "f_CRO01_2", "f_CRO03_1",
						"f_CRO03_16", "f_CSC01_16", "f_CXT01_1", "f_CXT01_16", "f_EHT01_16", "f_EHT01_2", "f_GEN01_1",
						"f_GEN01_16", "f_GEN01_2", "f_GGA01_1", "f_GGA01_16", "f_GGA01_2", "f_GGA02_1", "f_GGA02_16",
						"f_GGA02_2", "f_GGA03_16", "f_GGA03_48", "f_MMC02_1", "f_MMC02_16", "f_OST01_1", "f_OST01_16",
						"f_OTP01_1", "f_OTP01_16", "f_PET01_1", "f_PET01_16", "f_PET01_2", "f_PLA01_1", "f_PLA01_16",
						"f_PLR01_1", "f_PLR01_16", "f_PPS01_1", "f_PPS01_16", "f_PPS01_2", "f_SOC01_1", "f_SOC01_16",
						"f_SOC01_2", "f_SOG01_16", "f_SOK01_1", "f_SOK01_16", "f_SOK01_2", "f_SOK02_1", "f_SOK02_16",
						"f_SOK02_2", "f_SOK03_1", "f_SOK03_16", "f_SOM01_1", "f_SOM01_16", "f_SOM01_2", "f_SOM02_1",
						"f_SOM02_16", "f_SOM03_1", "f_SOM03_16", "f_SOM03_2", "f_SOM04_1", "f_SOM04_16", "f_SOM05_1",
						"f_SOM05_16", "f_SOM05_2", "f_SOM07_1", "f_SOM07_16", "f_SOM07_2", "f_SOM07_48", "f_SOM08_1",
						"f_SOM08_16", "f_SOM08_2", "f_SOM09_1", "f_SOM09_16", "f_SOM09_18", "f_SOM09_2", "f_SOT01_1",
						"f_SOT01_16", "f_SOT02_1", "f_SOT02_16", "f_SOT03_1", "f_SOT03_16", "f_SOT04_1", "f_SOT04_16"]

local_vars.data_setup()
log_folder = os.path.join(os.getcwd(), "log", "huc_migration_2013")
log.initialize("Comparing Ranges - Old v New", log_file=os.path.join(log_folder, "huc_migration_log.html"))

cache_old = os.path.join(os.getcwd(), "data", "layer_cache_old.gdb")
cache_new = os.path.join(os.getcwd(), "data", "layer_cache.gdb")
report_location = os.path.join(log_folder, "comparison_report_limited_secondary.csv")

arcpy.env.workspace = cache_old
cache_old_layers = arcpy.ListFeatureClasses()
arcpy.env.workspace = cache_new
cache_new_layers = arcpy.ListFeatureClasses()
#cache_old_layers.remove("blank_feature")
#cache_new_layers.remove("blank_feature")

only_in_new = list(set(cache_new_layers) - set(cache_old_layers))
only_in_old = list(set(cache_old_layers) - set(cache_new_layers))

log.write("The following items are only in the new layer cache: ", 1)
for item in only_in_new:
	log.write(item, 1)

log.write("The following items are only in the old layer cache: ", 1)
for item in only_in_old:
	log.write(item, 1)

log.write("End of unique items listing", 1)

# open now, we'll write out as we go
if resume:
	output_file = open(report_location, 'ab')
else:
	output_file = open(report_location, 'wb')

writer = csv.DictWriter(output_file, fieldnames=('Name', 'Species', 'percent_overlap', 'intersect_area', 'union_area', 'overlap_init_perspective', 'overlap_final_perspective', 'centroid_distance', ))
if not resume:
	writer.writeheader()

results = []
# get the items common to both
cache_intersect = [val for val in cache_old_layers if val in cache_new_layers]
log.write("%s layers in both caches" % len(cache_intersect))

encountered_resume_item = False
for item in cache_intersect:

	if resume and resume_item in item:
		encountered_resume_item = True

	if resume and not encountered_resume_item:  # resume from previous run
		continue

	if compare_limited_list and item not in compare_only_species:
		log.write("Not in list, skipping", 1)
		continue

	common_name = local_vars.all_fish[funcs.match_species_from_string(item)].species  # matches the species name from the layer, gets the common_name from all fish

	log.write("Running comparison of %s (%s)" % (item, common_name), 1)
	old_path = os.path.join(cache_old, item)
	new_path = os.path.join(cache_new, item)

	result_item = {'Name': item, 'Species': common_name}
	log.write("Percent Overlap", 1)
	percent_overlap_items = comparison.percent_overlap(old_path, new_path)
	result_item = dict(result_item.items() + percent_overlap_items.items())  # merge the dicts
	log.write("Centroid Distance", 1)
	result_item['centroid_distance'] = comparison.centroid_distance(old_path, new_path)

	writer.writerow(result_item)
	output_file.flush()  # flush it so that in case of crash, we get a bunch of it.
	results.append(result_item)

output_file.close()