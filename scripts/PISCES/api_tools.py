"""
	API tools is sort of like `funcs` except it can use API functions - API depends on funcs, so we'd get
	circular imports if we used funcs instead of this. It's also *NOT* in the API package because it uses
	arcpy - trying to keep the API to only using the ORM so that an ORM/API only version of the package
	could be still be used in the absence of arcpy installs, etc.
"""
from __future__ import absolute_import, division, print_function

import six

import arcpy
import sqlalchemy

from . import local_vars
from .api import presence
from .api import support
from . import orm_models as orm

aggregation_levels = ("family", "genus", "species")

name_lookup_cache = {"Family": {}, "Genus": {}, "Species": {}}  # holds name lookups - each level there is for a separate lookup tree


def get_common_name_from_species_string(scientific_name, level, speedup=True):
	"""
		Given a Family_genus_species_subspecies string (such as produced by species aggregation queries in the API),
		gets the common name associated with the specified taxonomic level. Not meant for looking up common names by
		genus, species, and subspecies (use the Species model in the ORM directly for that). This function gives *aggregated*
		common names at the species, genus, and family levels, where we have them

	:param scientific_name: The name of the species, starting at family level down to the level specified in the paramer setting
	:param level: family, genus, or species - what level to provide the common name at
	:param speedup: Indicates that we should cache names - allows for testing of cache vs. noncache

	:return:
	"""
	global name_lookup_cache

	session = support.connect_orm(hotload=True)

	try:
		level_lookup = {
			"family": 0,
			"genus": 1,
			"species": 2,
		}

		name_parts = scientific_name.split(" ")  # split it by spaces
		while len(name_parts) < 3:
			name_parts.append("")  # we shouldn't use these empty ones, but it makes the expression below work in all cases, no matter how long of an initial string we got, so long as the string always starts with the family

		#			family			genus	    species could have spaces in it - rejoin everything remaining with spaces
		levels = [name_parts[0], name_parts[1], " ".join(name_parts[2:len(name_parts)])]

		if speedup:  # we'll look through the cached dictionary to see if we already looked this species up. If so, return it
			base_dict = name_lookup_cache[level.capitalize()]
			for speed_level in levels:
				if speed_level in base_dict:
					if type(base_dict[speed_level]) is dict:  # then look up the next level
						base_dict = base_dict[speed_level]
					else:  # we're at the end, found our species already - if the key exists already, then we'll have populated it - could lead to a bug if this function crashes the first time after creating key but before populating it
						return base_dict[speed_level]
				else:
					base_dict[speed_level] = {}
					base_dict = base_dict[speed_level]


		species_scientific_name = levels[level_lookup[level.lower()]]  # there has to be a simpler way to get the scientific name for the
																		# species level than I'm doing right now
		if level.lower() == "family":
			parent_sci_name = None
		else:
			parent_sci_name = levels[level_lookup[level.lower()]-1]  # get the parent level scientific name

		name = get_taxonomy(scientific_name=species_scientific_name, level=level, parent_scientific_name=parent_sci_name, session=session).common_name
		if speedup:
			base = name_lookup_cache[level.capitalize()]
			for speed_level in levels:
				if len(base[speed_level].keys()) == 0:  # if we hit a dict with no keys, then we're at the bottom of the tree
					base[speed_level] = name  # replace it with the name instead
				else:
					base = base[speed_level]

		return name
	finally:
		session.close()


def get_taxonomy(scientific_name, level, session, parent_scientific_name=None,):
	"""
		Given a scientific name for the current level and a level itself, plus a parent level to deconflict, this code
		returns the taxonomy object associated with it for traversal. IMPORTANT: If you are trying to get the information
		for a family, parent_level is ignored, and checks for conflicts won't happen because we don't store levels above
		families.
	:param scientific_name:
	:param level:
	:param session: You must provide an open session to the PISCES orm so that this can return species objects to you
	:param parent_scientific_name:
	:return:
	"""

	taxon = session.query(orm.TaxonomicLevel).filter(sqlalchemy.and_(
														orm.TaxonomicLevel.scientific_name == scientific_name,
														orm.TaxonomicLevel.level == level.capitalize())
													 ).first()
	if level.lower() != "family":  # make sure we got the correct species with this scientific name
									# have to do this because can't query multiple records that reference each other in SQLAlchemy (maybe there's a way that I just don't know?)
		return taxon.confirm_tree(parent_scientific_name=parent_scientific_name, db_session=session)
	else:
		return taxon


def join_assemblage_as_field(huc_dataset,
							 species_or_group,
							 field_name=None,
							 key_field=local_vars.huc_field,
							 taxonomic_aggregation_level="common_name",
						 	 presence_types=local_vars.current_obs_types,
						 	 collections=local_vars.hq_collections):
	"""
		Given a HUC layer and species group, joins a field (field_name) that has the comma separated assemblage for that
		group, optionally at the given aggregation level

		The current orm method used here can be pretty slow, so caution against heavy use of this function
	:param huc_dataset: a feature class to add the field to
	:param species_or_group: a list of species codes or groups
	:param field_name: the name of the assemblage field to create. If not provided, one will be generated, starting with "assemblage" and including the aggregation level and presence types -
						it will not include the species or group because that could be complex - so in contexts where that will be important, provide your own field name
	:param key_field: The name of the HUC_12 ID field. Defaults to local_vars.huc_field ("HUC_12" as of this writing). Can override for use with other datasets here
	:param taxonomic_aggregation_level: default fid: Possible values: None, fid, common_name, scientific_name, species, genus, or family - None will give results by individual taxa, using common name as output. species groups subspecies to species, genus groups subspecies up to genus level, and family groups subspecies up to family level
	:param presence_types:
	:param collections:
	:return:
	"""

	presence_data = presence.get_species_list_by_hucs(species_or_group=species_or_group,
										 taxonomic_aggregation_level=taxonomic_aggregation_level,
										 presence_types=presence_types,
										 collections=collections)

	if taxonomic_aggregation_level.lower() in aggregation_levels:  # if we're aggregated, transform it back to a common name
		for key in presence_data:  # this is SLOOOOOOW - adds a ton of time when it has to be run for assemblages on every species
			presence_data[key] = [get_common_name_from_species_string(scientific_name=sci_name, level=taxonomic_aggregation_level)
								  for sci_name in presence_data[key]]

	if not field_name:
		if type(presence_types) in (six.text_type, six.binary_type):  # if it's a string, it'll be comma separated - replace the commas with underscores
			presence_name = presence_types.replace(",", "_")
		elif hasattr(presence_types, "__iter__"):  # really just want an iterable. If so, join the elements with underscores
			presence_name = "_".join([str(pt) for pt in presence_types])  # TODO: Iterables can't actually be passed through to the API right now, but at least it's ready here
		else:
			raise ValueError("Can't use presence types - must be comma separated string of values or an iterable")

		field_name = "assemblage_{}_{}".format(taxonomic_aggregation_level, presence_name)

	arcpy.AddField_management(huc_dataset, field_name, field_type="TEXT", field_length=65535)
	try:
		with arcpy.da.UpdateCursor(huc_dataset, [key_field, field_name]) as records:
			for record in records:
				value = ", ".join(sorted(presence_data[record[0]]))
				record[1] = value  # turn the assemblage into a string
				records.updateRow(record)
	except:
		arcpy.DeleteField_management(huc_dataset, field_name)  # if something goes wrong, delete the field so we can safely proceed
		raise


