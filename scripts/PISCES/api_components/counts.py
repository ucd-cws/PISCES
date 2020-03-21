
from sqlalchemy import distinct, func

from support import _parse_presence_types_and_collections_to_list, connect_orm

from .. import local_vars
from .. import orm_models as orm

def count_species_in_group_by_huc(group_name, presence_types, collections=local_vars.hq_collections, debug=False):
	"""
		Given a group name and a presence type, returns the count of taxa in each HUC. Basically an alpha
		richness function with some configuration parameters.

	:param group_name: a PISCES species group name (eg: Flow_Sensitive)
	:param presence_type: list of presence type codes, or the string definitions from local_vars (separated by commas)
	:param collections: list of collection ids, or the string degintions from local_vars (separated by commas)
	:return: list of HUC 12 ids for that species, presence type, and collection.
	"""

	presence = _parse_presence_types_and_collections_to_list(presence_types)
	collections = _parse_presence_types_and_collections_to_list(collections)

	session = connect_orm()

	try:
		huc_list = session.query(orm.Observation.zone_id, func.count(distinct(orm.Observation.species_id)))\
			.join("species", "groups")\
			.filter(orm.SpeciesGroup.name == group_name)\
			.filter(orm.Observation.presence_type_id.in_(presence))\
			.filter(orm.Observation.collections.any(orm.Collection.pkey.in_(collections)))\
			.group_by(orm.Observation.zone_id)

		if debug:
			return str(huc_list)  # return the sql instead

		return huc_list
	finally:
		session.close()

