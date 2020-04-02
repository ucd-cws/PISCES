from __future__ import absolute_import, division, print_function

__author__ = 'nrsantos'

import csv
import traceback

from . import log
from . import funcs
from . import local_vars
from . import api

from .code_library_data_files import teale_albers
from . import code_library_geometry as geometry


def percent_overlap(range_old, range_new):
	return geometry.percent_overlap(range_old, range_new, dissolve=True)


def centroid_distance(range_old, range_new):
	return geometry.simple_centroid_distance(range_old, range_new, teale_albers, dissolve=True) / 1000


def historic_vs_current(fid, collections=local_vars.hq_collections):
	"""
		Compares a species' historic range to its current range, defaulting to using only hq_collections

	:param str fid: A PISCES species FID code (eg: "SOM09")
	:param str collections: the collection ids to limit the data to. Defaults to the hq_collections variable which uses the "QC dataset"
	:return: comparison object
	:rtype: geospatial.geometry.Comparison
	"""

	local_vars.data_setup()  # if it hasn't already happened, run it

	if not fid in local_vars.all_fish:
		raise ValueError("Provided fid does not exist. This could be a misspelling or a database connection error. Please check the provided FID and note that it is case sensitive")

	sql_str = "select distinct Observations.Zone_ID " \
				  "from Observations, Observation_Collections " \
				  "where Species_ID = ? And " \
				  "Presence_Type in ({presence_types}) and " \
				  "Observations.OBJECTID = Observation_Collections.Observation_ID and " \
				  "Observation_Collections.Collection_ID in ({collections})"

	log.write("Getting current layer", 1)
	current = api.get_query_as_layer(query=sql_str.format(presence_types=local_vars.current_obs_types, collections=collections), bind=fid)
	log.write("Getting historic layer", 1)
	historic = api.get_query_as_layer(query=sql_str.format(presence_types=local_vars.historic_obs_types, collections=collections), bind=fid)

	log.write("Getting percent overlap", 1)
	pct_over = percent_overlap(historic, current)
	log.write("Getting centroid distance and direction", 1)
	cent_dist = geospatial.geometry.simple_centroid_distance(historic, current, geospatial.teale_albers, dissolve=True, centroid_direction=True)

	comparison = geospatial.geometry.Comparison()
	comparison.percent_overlap = pct_over["percent_overlap"]
	comparison.percent_overlap_final = pct_over["overlap_final_perspective"]
	comparison.percent_overlap_initial = pct_over["overlap_init_perspective"]
	comparison.overlap_intersect_area = pct_over["intersect_area"]
	comparison.overlap_union_area = pct_over["union_area"]
	comparison.centroid_direction = cent_dist["centroid_direction"]
	comparison.centroid_distance = cent_dist["distance"]

	return comparison


def batch_compare_species_ranges(output_file, species=None):
	"""
		Pulls the list of native species (since they have historic ranges) from the database and runs :function::historic_vs_current on each one. Returns a csv file with the results

	:param str output_file: Path to new CSV file where results would be placed
	:param list species: optional. An iterable of species codes to run this for
	"""

	log.write("Batch comparing species", 1)

	if species:
		species_codes = species
	else:
		species_codes = funcs.species_group_as_list(group_name="Native_Fish")

	comparison_obj = geospatial.geometry.Comparison()
	comparison_obj.species = None
	comparison_obj.common_name = None

	out_file = open(output_file, 'wb', buffering=1)  # buffering of 1 means line buffering - should write after every line
	csv_writer = csv.DictWriter(out_file, comparison_obj.__dict__.keys())
	csv_writer.writeheader()

	had_errors = False
	for code in species_codes:
		try:
			dict_obj = historic_vs_current(code).__dict__   # convert it to a dictionary on the fly
			dict_obj["species"] = code
			dict_obj["common_name"] = local_vars.all_fish[code].species
			csv_writer.writerow(dict_obj)
		except:
			had_errors = True
			log.error("Failed to run analysis for species" + code)
			log.error("Error reported was " + traceback.format_exc())

	if had_errors:
		log.write("Errors were reported during processing. Please check the error log and correct any missing species (this function can take a list of species codes as a parameter so you can rerun specific missing codes)", 1)

	out_file.close()