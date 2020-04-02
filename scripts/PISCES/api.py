from __future__ import absolute_import, division, print_function

__author__ = 'nrsantos'

import random
import string

from sqlalchemy import distinct

import arcpy

from . import api_components
from .api_components.listing import get_hucs_for_species_as_list  # backwards compatibility
from .api_components import listing  # make it available as api.listing for now
from .api_components import counts
from .api_components import support
from .api_components import presence

from . import local_vars
from . import funcs
from . import orm_models as orm
from . import mapping
from . import log


class NoDataError(Exception):
	def __init__(self, message, **kwargs):
		log.error("No data returned. {}".format(message))
		super(NoDataError, self).__init__(**kwargs)


def get_query_as_layer(query, bind=None, fc=False, callback=None, callback_args=None, metadata=False):
	"""
		Takes a SQL query that obtains HUC_12 IDs in the PISCES database and returns a feature class or feature layer generated from that query. Contains the full PISCES metadata available.


	:param query: str: The query to run against the PISCES database that will generate a set of HUC IDs. It must conform to PISCES query standards (namely, that the HUC_12 field must come out as Zone_ID to bne seen). This may change in a future version. You should read the rest of the documentation before using this function.
	:param bind: A bind value to pass along with the query. If you need more than one, use {bind}
	:param fc: boolean. Indicates whether to return a feature class or a feature layer. Feature layer is the default (fc is False). When fc is True, a feature class is written out and the path is returned instead of a feature layer.
	:param callback:
	:param callback_args:
	:return: Fully qualified path to generated feature class on disk
	"""

	# open a db_cursor
	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)

	# configure whether we should output metadata TODO: add support for this flag in the tools
	local_vars.config_metadata = metadata

	# create the query
	map_layer = mapping.map_layer(query=None, bind_v=bind, parent=None, text_query=query)

	# make the feature layer
	zone_layer = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))  # get a random layer name
	try:
		arcpy.MakeFeatureLayer_management(local_vars.HUCS, zone_layer)

		map_layer.populate(db_cursor)
		layer = map_layer.make(zone_layer=zone_layer)
		if layer is None:
			raise NoDataError("Query did not return any HUCs to map. The query may be incorrect, or no records may match the query.")

		output_layer = mapping.cache_layer(layer, bind, 0, map_layer, db_cursor)  # returns the full path
	finally:
		arcpy.Delete_management(zone_layer)  # cleanup so we can run this again

	return output_layer




def get_common_names_in_hucs(huc_list):

	"""
	Given a list of HUC12 IDs, returns a list of species common names present (for all presence types) in those HUC12s
	:param huc_list: list: A list of HUC 12 ids to search
	:return: list: Common names of species in the huc12s provided
	"""
	
	session = api_components.support.connect_orm()

	try:
		distinct_list = session.query(distinct(orm.Observation.species_id)).filter(orm.Observation.zone_id.in_(huc_list)).all()
		species = []
		for record in distinct_list:
			species.append(str(session.query(orm.Species.common_name).filter(orm.Species.fid == record[0]).one()[0]))

		species.sort()
	finally:
		session.close()

	return species




def get_observation_records_for_hucs(huc_list_or_layer, species_list=None, presence_types_list=None, collection_list=None):
	"""
		:param huc_list_or_layer:
		:param species_list: a Python list of PISCES species codes
		:param presence_types_list: a Python list of presence type codes (from definitions table) to limit the results to
		:param collection_list: a Python list of collection names to limit the results to
		Given a set of hucs as a list or a feature class or feature layer, and one or more species or groups, returns the observation records meeting those criteria
	:return: list of orm.Observation objects
	"""

	session = api_components.support.connect_orm()

	try:
		# first, determine if we have a list of hucs, or if it's an arcpy layer
		if hasattr(huc_list_or_layer, "__iter__"):  # then we have a list of hucs, go with it
			huc_list = huc_list_or_layer
		else:
			huc_list = funcs.hucs_to_list(huc_list_or_layer)

		observation_list = session.query(orm.Observation).filter(orm.Observation.zone_id.in_(huc_list))

		if species_list:
			observation_list = observation_list.filter(orm.Observation.species_id.in_(species_list))

		if presence_types_list:
			observation_list = observation_list.filter(orm.Observation.presence_type_id.in_(presence_types_list))

		if collection_list:
			# get the collections first in this case since the relationship is different
			#collections = session.query(orm.Collection).filter(orm.Collection.pkey.in_(collection_list))
			observation_list = observation_list.filter(orm.Observation.collections.any(orm.Collection.name.in_(collection_list)))
	finally:
		session.close()

	return observation_list


