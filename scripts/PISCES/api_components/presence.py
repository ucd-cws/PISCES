import collections as collections_package

from sqlalchemy import distinct

from .. import local_vars
from .. import funcs
from .. import orm_models as orm
from .. import log

from . import support

aggregation_level_lookup = {
# used so that we can use hybrid columns to get actual full taxonomic distinct name since species names may not be distinct across genera, and genera may not be distinct across families
	"fid": "fid",
	"common_name": "common_name",
	"scientific_name": "scientific_name",
	"species": "full_taxonomic_name_species",
	"genus": "full_taxonomic_name_genus",
	"family": "family",
}


def get_presence_by_huc_set(species_or_group,
							zone_list,
						 taxonomic_aggregation_level="fid",
						 presence_types=local_vars.current_obs_types,
						 collections=local_vars.hq_collections):
	"""
		Given a species list or species group, returns presence/absence information,
		optionally aggregated up the taxonomic tree. This function does *not* return
		presence for each zone, but instead returns a single list of species that are
		present in the zone IDs provided in zone_list. For HUC_12 presence for a single species, use
		listing.get_hucs_for_species_as_list.

		The current orm method used here can be pretty slow, so caution against heavy use of this function.
	:param species_or_group: a list of species codes or groups
	:param huc12_list: A list of Zone IDs to use to look up presence
	:param taxonomic_aggregation_level: default fid: Possible values: None, fid, common_name, scientific_name, species, genus, or family - None will give results by individual taxa, using common name as output. species groups subspecies to species, genus groups subspecies up to genus level, and family groups subspecies up to family level
	:param presence_types:
	:param collections:
	:return: list of namedtuples (zone_id, taxon) with presence specified
	"""

	session = support.connect_orm(hotload=True)

	try:
		species_level, pisces_collections, presence, taxa = validate_parameters(session, collections, presence_types,
																	species_or_group, taxonomic_aggregation_level)

		objects = session.query(species_level)\
					.join(orm.Observation)\
					.join(orm.observation_collections)\
					.join(orm.Collection)\
					.filter(orm.Observation.zone_id.in_(zone_list))\
					.filter(orm.Species.fid.in_(taxa))\
					.filter(orm.Observation.presence_type_id.in_(presence))\
					.filter(orm.Observation.collections.any(orm.Collection.pkey.in_(pisces_collections)))\
					.group_by(species_level)

		return [record[0] for record in objects]  # make it a list instead of a sqlalchemy object
	finally:
		session.close()


def get_presence_by_taxa(species_or_group,
						 taxonomic_aggregation_level="fid",
						 presence_types=local_vars.current_obs_types,
						 collections=local_vars.hq_collections):
	"""
		Given a species list or species group, returns presence/absence information,
		optionally aggregated up the taxonomic tree. For HUC_12 presence for a single species, use
		listing.get_hucs_for_species_as_list.

		Returns a list of namedtuples with records for each zone and taxon - zones and taxons will each have multiple values.

		The current orm method used here can be pretty slow, so caution against heavy use of this function.
	:param species_or_group: a list of species codes or groups
	:param taxonomic_aggregation_level: default fid: Possible values: None, fid, common_name, scientific_name, species, genus, or family - None will give results by individual taxa, using common name as output. species groups subspecies to species, genus groups subspecies up to genus level, and family groups subspecies up to family level
	:param presence_types:
	:param collections:
	:return: list of namedtuples (zone_id, taxon) with presence specified
	"""

	session = support.connect_orm(hotload=True)

	try:
		species_level, pisces_collections, presence, taxa = validate_parameters(session, collections, presence_types,
																	species_or_group, taxonomic_aggregation_level)

		zone_taxon = collections_package.namedtuple('zone_taxon', ["zone_id", "taxon"])

		objects = session.query(orm.Observation.zone_id, species_level)\
					.join(orm.observation_collections)\
					.join(orm.Collection)\
					.join(orm.Species)\
					.filter(orm.Species.fid.in_(taxa))\
					.filter(orm.Observation.presence_type_id.in_(presence))\
					.filter(orm.Observation.collections.any(orm.Collection.pkey.in_(pisces_collections)))\
					.group_by(orm.Observation.zone_id, species_level)
		#log.debug(str(objects), screen=True)
		return [zone_taxon(record[0], record[1]) for record in objects]
	finally:
		session.close()


def validate_parameters(session, collections, presence_types, species_or_group, taxonomic_aggregation_level):
	"""
		Given a set of API input parameters such as collections and taxonomic aggregation levels, validates
		and cleans them
	:param collections:
	:param presence_types:
	:param session:
	:param species_or_group:
	:param taxonomic_aggregation_level:
	:return:
	"""

	presence = support._parse_presence_types_and_collections_to_list(presence_types)

	if collections:
		pisces_collections = support._parse_presence_types_and_collections_to_list(collections)
	else:
		pisces_collections = session.query(distinct(orm.Collection.pkey)).all()  # We could just drop the collections join below instead, and it'd be faster, but it actually seems like it'd make another code pathway to test

	taxa = funcs.text_to_species_list(species_or_group)

	if taxonomic_aggregation_level is None:
		taxonomic_aggregation_level = "common_name"  # use it as a default if it's set to None
	level = taxonomic_aggregation_level.lower()

	if level not in ("fid", "common_name", "scientific_name", "species", "genus", "family"):
		raise ValueError("Aggregation level can only be one of: family, genus, species for aggregation. common_name, scientific_name, and fid are allowed for subspecies clustering")

	species_level = getattr(orm.Species, aggregation_level_lookup[level])

	return species_level, pisces_collections, presence, taxa


def get_species_list_by_hucs(species_or_group,
						 taxonomic_aggregation_level="fid",
						 presence_types=local_vars.current_obs_types,
						 collections=local_vars.hq_collections):
	"""
		Given a species list or species group, returns a dictionary with HUCs as keys and a species list as the value.
		The values in the species list are controlled by the taxonomic aggregation level. Behind the scenes, calls
		get_presence_by_taxa. For HUC_12 presence for a single species, use
		listing.get_hucs_for_species_as_list.

		The current orm method used here can be pretty slow, so caution against heavy use of this function
	:param species_or_group: a list of species codes or groups
	:param taxonomic_aggregation_level: default fid: Possible values: None, fid, common_name, scientific_name, species, genus, or family - None will give results by individual taxa, using common name as output. species groups subspecies to species, genus groups subspecies up to genus level, and family groups subspecies up to family level
	:param presence_types:
	:param collections:
	:return:
	"""

	records = {}

	presence_data = get_presence_by_taxa(species_or_group=species_or_group,
										 taxonomic_aggregation_level=taxonomic_aggregation_level,
										 presence_types=presence_types,
										 collections=collections)

	for row in presence_data:
		if row.zone_id not in records:
			records[row.zone_id] = []
		records[row.zone_id].append(row.taxon)

	return records
