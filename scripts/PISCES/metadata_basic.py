__author__ = 'dsx'

import os
import datetime

try:
	import orm_models
	import local_vars
	import log
	import arcpy_metadata as md
except ImportError:
	from PISCES import orm_models
	from PISCES import local_vars
	from PISCES import log

# import PISCES.plugins.metadata.__init__ as pisces_metadata  # TODO - this is the wrong way to import this, I think - fix that


def attach(pisces_layer, zone_layer, layer_type=None, title=None, **kwargs):

	log.write("Attaching Basic Metadata", 1)

	metadata = md.MetadataEditor(dataset=zone_layer, temp_folder=local_vars.temp)

	if pisces_layer.custom_query.bind_var:
		species = local_vars.all_fish[pisces_layer.custom_query.bind_var]
	else:
		species = None

	if title:
		metadata.title.set(title)
	elif species:
		metadata.title.set("%s - %s" % (species.species, pisces_layer.custom_query.layer_name))
	else:
		metadata.title.set("Species Range")

	session = orm_models.new_session()
	observation_sets = {}
	for observation in pisces_layer.observations:  # it's a list of sqlalchemy objects, not a sqlalchemy query object
		if not observation.set_id in observation_sets and observation.set_id:  # every once in a blue moon, we get a set_id of None
				observation_sets[observation.set_id] = session.query(orm_models.ObservationSet).get(observation.set_id)  # get the observation set object into the dict

	presence_string = "Species presence data in this dataset provided by the following datasets and interpreted by PISCES:\r\n"
	for obs_set in observation_sets.keys():
		presence_string += "%s (%s),\r\n" % (observation_sets[obs_set].name, os.path.split(observation_sets[obs_set].source_data)[1])
	presence_string += "\r\n. This layer was generated by PISCES on %s" % (datetime.datetime.now().strftime("%m/%d/%Y %I:%M %p"))

	metadata.purpose.set("Species range layer for %s, showing HUC12s with presence types for %s" % (species.species, pisces_layer.custom_query.layer_name))
	metadata.abstract.prepend(presence_string)

	metadata.tags.add([species.species, species.sci_name, pisces_layer.custom_query.bind_var])

	metadata.finish()  # save and cleanup

	return zone_layer  # it did get modified by the metadata editor

	# determine distinct set of data sources involved