from __future__ import absolute_import, division, print_function

from sqlalchemy import distinct

from . import support

from .. import local_vars
from .. import orm_models as orm


def get_hucs_for_species_as_list(species_code, presence_types, collections=local_vars.hq_collections):
	"""
		Given a species code and a presence type, returns a list of huc12 IDs.

		Example usage is for determining whether a new rainbow trout observation is observed or translocated - pull
		the historical range from here
	:param species_code: a PISCES species code (eg: SOM09)
	:param presence_type: list of presence type codes, or the string definitions from local_vars (separated by commas)
	:param collections: list of collection ids, or the string degintions from local_vars (separated by commas)
	:return: list of HUC 12 ids for that species, presence type, and collection.
	"""

	presence = support._parse_presence_types_and_collections_to_list(presence_types)
	collections = support._parse_presence_types_and_collections_to_list(collections)

	session = support.connect_orm()

	try:
		huc_list = session.query(distinct(orm.Observation.zone_id))\
			.filter(orm.Observation.species_id == species_code)\
			.filter(orm.Observation.presence_type_id.in_(presence))\
			.filter(orm.Observation.collections.any(orm.Collection.pkey.in_(collections)))

		return [record[0] for record in huc_list]
	finally:
		session.close()


def get_hucs_for_group_as_list(group_name, presence_types, collections=local_vars.hq_collections, debug=False):
	"""
		Given a group name and a presence type, returns a list of huc12 IDs. This returns a group range, not a
		set of ranges for each species in the group. If you want ranges for individual species in a group, use
		get_hucs_for_species_in_group_as_list.

	:param group_name: a PISCES species group name (eg: Flow_Sensitive)
	:param presence_type: list of presence type codes, or the string definitions from local_vars (separated by commas)
	:param collections: list of collection ids, or the string designations from local_vars (separated by commas)
	:param debug: default False. When True, instead of returning actual results, returns the sql generated for the query
	:return: list of HUC 12 ids for that group, presence type, and collection.
	"""

	presence = support._parse_presence_types_and_collections_to_list(presence_types)
	collections = support._parse_presence_types_and_collections_to_list(collections)

	session = support.connect_orm(hotload=True)
	support._check_group_name(group_name, session)  # confirm it's a valid group name

	try:
		huc_list = session.query(distinct(orm.Observation.zone_id))\
			.join("species", "groups")\
			.filter(orm.Species.groups.any(orm.SpeciesGroup.name == group_name))\
			.filter(orm.Observation.presence_type_id.in_(presence))\
			.filter(orm.Observation.collections.any(orm.Collection.pkey.in_(collections)))

		if debug:
			return str(huc_list)  # returns sql query

		return [record[0] for record in huc_list]
	finally:
		session.close()


def get_hucs_for_species_in_group_as_list(group_name, presence_types, collections=local_vars.hq_collections, debug=False):
	"""
		Given a group name and a presence type, returns a list of huc12 IDs. This returns lists of HUC12s for each
		species ID in the group name as a dictionary. The dictionary is keyed by species ID and for each key has
		a list of HUC12 IDs.

		If you want a group range and not individual ranges, use get_hucs_for_group_as_list

	:param group_name: a PISCES species group name (eg: Flow_Sensitive)
	:param presence_type: list of presence type codes, or the string definitions from local_vars (separated by commas)
	:param collections: list of collection ids, or the string designations from local_vars (separated by commas)
	:param debug: default False. When True, instead of returning actual results, returns the sql generated for the query
	:return: dictionary keyed by species ID (FID) with each key having a list of HUC12s indicating presence.
	"""

	presence = support._parse_presence_types_and_collections_to_list(presence_types)
	collections = support._parse_presence_types_and_collections_to_list(collections)

	session = support.connect_orm(hotload=True)
	support._check_group_name(group_name, session)  # confirm it's a valid group name

	try:
		huc_list = session.query(distinct(orm.Observation.zone_id), orm.Observation.species_id) \
			.join("species", "groups") \
			.filter(orm.Species.groups.any(orm.SpeciesGroup.name == group_name)) \
			.filter(orm.Observation.presence_type_id.in_(presence)) \
			.filter(orm.Observation.collections.any(orm.Collection.pkey.in_(collections))) \

		if debug:
			return str(huc_list)  # returns sql query

		records = {}
		for record in huc_list:  # make it into a dictionary keyed by species id with a list of HUC12s
			if record.species_id not in records:
				records[record.species_id] = []
			records[record.species_id].append(record[0])
		return records
	finally:
		session.close()


def get_taxonomic_tree():
	"""
		Returns a dictionary tree of taxonomic levels starting with families. Only includes taxa in the TaxonomicLevel
		ORM objects, so no species groups attached - as of this writing, only native fish.

		Top level keys are familys. The values are always dictionaries with two objects ("name" and "children"),
		so any given level's .keys() will be the scientific name at that level (eg, top level Salmonidae).
		The "name" key includes a common name representation for the taxonomic level, if available, and "children"
		includes access to lower taxonomic levels as a dictionary with the same key/value structure as the top level
		If you then go a level in, such as tree["Salmonidae"], that level
		has .keys() of genus names and .values() are dicts that themselves have species level names as keys (for consistency,
		and to support a future subspecies tree without changes).
	:return:
	"""
	session = support.connect_orm(hotload=True)

	tree = {}
	try:
		taxonomic_levels = session.query(orm.TaxonomicLevel).filter(orm.TaxonomicLevel.level == "Family")
		for family in taxonomic_levels:
			tree[family.scientific_name] = {"name": family.common_name, "children": {}}
			for genus in family.children:
				tree[family.scientific_name]["children"][genus.scientific_name] = {"name": genus.common_name, "children": {}}
				for species in genus.children:
					tree[family.scientific_name]["children"][genus.scientific_name]["children"][species.scientific_name] = {"name": species.common_name, "children": {}}

	finally:
		session.close()

	return tree


def get_distinct_taxonomic_names_in_group_as_list(level, group_name=None):
	"""
		Given a species group, outputs a list of every distinct name at a given taxonomic level (family, genus, or species)
	:param level:
	:param group_name: optional
	:return:
	"""
	level = level.lower()
	if not level in ("family", "genus", "species"):
		raise ValueError("Aggregation level can only be one of: family, genus, species")

	session = support.connect_orm(hotload=True)

	try:
		aggregation_list = session.query(distinct(getattr(orm.Species, level)))
		if group_name:
			support._check_group_name(group_name, session)  # will raise ValueError if the name is invalid
			aggregation_list = aggregation_list.filter(orm.Species.groups.any(orm.SpeciesGroup.name == group_name))

		return [record[0] for record in aggregation_list]
	finally:
		session.close()


def get_fids_in_group_as_list(group_name=None):
	"""
		Gets the species codes for all species in a single group. Can then be used to get huc12s for all species
		in the group (or use get_hucs_for_species_in_group_as_list if you don't need the species IDs for other
		reasons)
	:param group_name:
	:return:
	"""
	session = support.connect_orm(hotload=True)
	try:
		species_list = session.query(orm.Species)
		if group_name:
			support._check_group_name(group_name, session)  # will raise ValueError if the name is invalid
			species_list = species_list.filter(orm.Species.groups.any(orm.SpeciesGroup.name == group_name))

		return [record.fid for record in species_list]
	finally:
		session.close()