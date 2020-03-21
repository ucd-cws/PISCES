import os
import re
import string
import logging

import arcpy

from .. import local_vars
from ..local_vars import input_filter_methods, get_species_from_alt_code, alt_codes_by_filter
from .. import api
from .. import funcs

from common import tablecoords_to_file, table_to_array, multifeature_to_HUCs, determine_certainty, copy_row

log = logging.getLogger("PISCES.input_filters")

database_mapping = {'Species_ID': "species_id", 'Observation Type': 'presence_type', 'Date': "observation_date",
					'Latitude': "latitude", 'Longitude': "longitude", 'Presence_Type': "presence_type",
					'Observer': "observer", 'Survey Method': "survey_method", 'Certainty': "certainty",
					"Zone_ID": "zone_id"}  # ok, now this is ridiculous...field maps inside of field maps. Am I in the twilight zone? This variable - using this makes some code relatively ugly, but it's necessary to make things human readable - maybe this original mapping needs to live in the database in some way...


class InputFilter(object):  # parent class to all actual input filters that describe

	def __init__(self, full_obs_set):
		# full_obs_set is the object that this input filter is a part of. It's so we can access the data in that class
		# we should probably think about whether or not there is a better way to achieve that goal.
		self.all_init(full_obs_set)

	def all_init(self, full_obs_set):  # called by __init__ of input filters in order to have a constant set of things that gets called before anything happens
		self.parent = full_obs_set
		# this way self.parent gets us the object that this filter is contained in (NOT the parent class)

		self.name_match_string = None
		self.name_match_group = None

		self.if_methods = None
		self.default_observer = None

		self.set_up_field_maps()

		self.get_defaults()

	def set_up_field_maps(self):

		## TODO: If this ever gets refactored, remove the list and just use the dict - we can access it as a list if we need to
		self.fmap_index = {}  # set it up - we want to have a lookup for "latitude", etc that returns the entry, from which we can grab the column or other data
		self.field_map = []

		## TODO: Apparently this function blows. It requires that you copy a template mapping with ID 0 from newdata (so if you add new mapping possibilities, make sure to do it there!) instead of being flexible to each one being different. So poopy.
		if self.parent.new_data.ID in local_vars.field_maps:
			for l_map in local_vars.field_maps[
				0]:  # copy the defaults out - we can't just assign the larger array over because we're going to swap out items and we don't want that to happen to all of them
				self.field_map.append(l_map)

			for index in range(len(local_vars.field_maps[
									   self.parent.new_data.ID])):  # overwrite the defaults with the more specific copy, if available - iterate over the loops and copy out the specific one in place of the default when their names match
				for d_index in range(len(self.field_map)):
					if local_vars.field_maps[self.parent.new_data.ID][index].field_name == self.field_map[d_index].field_name:
						self.field_map[d_index] = local_vars.field_maps[self.parent.new_data.ID][index]

			self.index_field_maps()  # throw the data in

	def get_defaults(self):
		# this is incredibly inefficient to do this for every input filter, but a more robust method that caches it doesn't yet make sense. If we start to get more variables, maybe a cache is wise

		db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "Getting defaults for input filter")

		code = self.parent.filter_code

		sql = "select default_observer from defs_input_filters where code = ?"
		rows = db_cursor.execute(sql, code)

		for row in rows:  # there should only be one - if there is more, then this takes the last one
			self.default_observer = row.default_observer

		funcs.db_close(db_cursor, db_conn)

	def determine_species(self, match_string):
		log.info("parsing dataset name for species determination in dataset %s" % self.parent.dataset_name)

		if not self.name_match_string is None:
			l_match = re.search(self.name_match_string, match_string)  # pull out the data we need from the filename

			l_alt_code_species = l_match.group(
				self.name_match_group)  # pops the match from the previous search into there. Now we need to check if it's a species code or if its an alt_code
		# name match group is previously defined in case we want to match multiple spots
		else:
			l_alt_code_species = match_string

		if local_vars.all_fish.has_key(
				l_alt_code_species):  # Validate: if it has the key for the id, then we have a fish
			self.parent.species_fid = l_alt_code_species  # we can expand this as we expect more data in the filename
			log.info("Fish species identified for feature class %s. Species %s" % (self.parent.dataset_name, l_alt_code_species))
		else:
			l_species = get_species_from_alt_code(l_alt_code_species, self.parent.filter_code)
			if l_species is False:  # if the function couldn't find it, raise the error which will stop processing this set since it's the last attempt we can make
				raise local_vars.DataProcessingError(
					"Unable to determine species for %s (using alt_code %s) - it's probably going to be easiest for you to just define it yourself in the New_Data.mdb record (replace 'filter' in the record with something valid as explained on the input form)" % (
					self.parent.dataset_name, l_alt_code_species), self.parent.dataset_key)
			else:  # if it found one, set it and return
				self.parent.species_fid = l_species

	def process_observations(self):
		return

	def make_results(self, zones, species, obs_type, pri_cert, sec_cert=None, if_method=None):

		l_result = local_vars.result_set()  # make the result to store the data in

		l_observations = []  # make the observations array
		for zone in zones:
			l_obs = local_vars.observation()  # make the observation for this index
			l_obs.zone_id = zone
			l_obs.species_id = species
			l_obs.presence_type = obs_type
			l_obs.certainty = determine_certainty((pri_cert, sec_cert))  # primary, secondary
			l_observations.append(l_obs)
		l_result.observations = l_observations
		l_result.if_method = if_method
		# l_result.temporary_dataset = out_feat

		return l_result

	def index_field_maps(self):
		for l_map in self.field_map:
			self.fmap_index[l_map.field_name] = l_map

	def filter_results(self):
		'''meant to provide a placeholder for functions that remove rows after processing and before inserting'''
		pass


class Gen_Poly_IF(InputFilter):
	def __init__(self, full_obs_set):
		self.all_init(full_obs_set)  # sets all the defaults for us

	def determine_species(self):
		print self.name_match_string
		InputFilter.determine_species(self, self.parent.dataset_name)

	def process_observations(self):
		# TODO: Comment this function
		# TODO: much of this function can probably be abstracted once we get more IF methods
		# Run the analysis

		print "Processing dataset %s" % self.parent.dataset_path

		for method in input_filter_methods[self.parent.filter_code]:

			if self.parent.new_data.IF_Method is not None:  # if we were told to only use a particular IF Method
				if not self.parent.new_data.IF_Method == method.short_name:  # and we aren't using it!
					continue  # then skip this round

			results = multifeature_to_HUCs(self.parent.dataset_path, method.trigger)
			HUCS = []
			for row in results:
				HUCS.append(row.HUC_12)  # bundle the HUCs - this lets us become compatible with the code below for now

			obs_type = self.parent.new_data.Presence_Type
			if obs_type == None:
				obs_type = method.default_observation_type

			l_result = self.make_results(HUCS, self.parent.species_fid, obs_type, method.default_certainty,
										 local_vars.observation_certainties[method.default_observation_type], method)
			# zones, observation_type, certainty 1, fallback certainty, if method id

			self.parent.results.append(l_result)

		# TODO: Write line to the data log indicating changes


class Gen_Table_IF(InputFilter):
	"""
		Generic Filter for tables that have a species column and a column for x/y - we can base future classes on this
		subclasses can extend the functionality of this class by defining a new method process_observations,
		and then calling parent class's version of .process_observations() after all the prep work is done. This would be a good way
		to do things like splitting data columns and any other *very* item specific processing (generic processing would ideally)
		be incorporated into this class.

		Even better than overriding process_observations is to leave that in place, and instead override the handler functions on this class (handle_zone_id, handle_date, etc).
		This allows the primary workflow of the class to remain, but provides a way to change the behavior for specific fields as necessary. You can define multiple new handler functions for the same attribute in a subclass and allow the PISCES operator to specify which should be used at import time (in the field map) in order to provide customization options for a specific type of dataset.

		This class, or one of its subclasses, should be used for most imports as it is the most flexible and tested.
	"""

	def __init__(self, full_obs_set):
		self.all_init(full_obs_set)  # sets all the defaults for us - defined in the main input_filter class
		self.handle_args()
		self.survey_method = self.parent.new_data.Survey_Method
		self.intersect_method = "INTERSECT"

	def handle_args(self):
		"""
			Loads arguments provided in the newdata configuration and makes them available to the current instance
		:return:
		"""
		self.args = self.parent.new_data.Input_Filter_Args

	# args_array = string.split(self.args,";")

	def determine_species(self):
		"""
			Overrides the default method for determining the species of an input filter (with respect to the whole dataset). Datasets have a species code and records have separate species code. This one determines the code for the whole dataset, using MUL99 when it deals with multiple species
		:return:
		"""
		# must set self.parent.species_id
		if self.parent.new_data.Species_ID is None or self.parent.new_data.Species_ID == "filter":
			self.parent.species_fid = "MUL99"
		else:
			InputFilter.determine_species(self, self.parent.new_data.Species_ID)
			# call the parent class' generic version - in some cases, more handling can be done here, but in most cases,
			# the parent class will handle the full range of possibilities

	def determine_species_for_record(self, species):
		"""
			Receives the value for the species field for each record and attempts to look it up using the main species codes for PISCES or using the alt codes for the current input filter using this class.

			This is a key method to override in a subclass handling data of a differing form or format.
		:param species:
		:return:
		"""
		if species is None:
			return False

		species = string.upper(str(species))
		if species in local_vars.all_fish:
			return local_vars.all_fish[species]
		else:
			l_species = get_species_from_alt_code(species, self.parent.filter_code)
			if l_species is not False:
				return l_species

		return False  # if we've gotten to here, then we don't know what species it is. False will skip the record

	def get_zones(self):
		"""
			Provided a table with coordinates or a feature class, returns a list with the spatially joined attributes of the input dataset on HUC12s, allowing for a translation of input record data to HUC12 locations

			This function is a key function to override for data of differing form or formats.
		:return: list: full, spatially joined record information for all HUCs the dataset passed in had data for
		"""
		try:
			describer = arcpy.Describe(self.parent.dataset_path)
		except:
			raise local_vars.DataProcessingError("Unable to determine object type")

		if describer.dataType == "Table":
			try:
				l_features = tablecoords_to_file(self.parent.dataset_path, self.fmap_index, self.parent.new_data.Projection_Key)  # dataset, field name for x axis, field name for y axis, and the projection they are all in
			except local_vars.DataProcessingError as lerror:
				print lerror
				raise  # skip this dataset!
		else:
			l_features = self.parent.dataset_path
		HUCs = multifeature_to_HUCs(l_features, relationship=self.intersect_method)

		if describer.dataType == "Table":  # we only want to delete the feature class if the initial file was a table because that means we created it here - otherwise we want to save it still
			arcpy.Delete_management(
				l_features)  # we're through with it - delete it because the same name will be used should tablecoords_to_file be called again

		del describer  # a bit of memory management

		return HUCs

	def preprocess(self):
		"""
			Designed to be overridden and called by process_observations. Allows for setup work without having to override process_observations
		:return:
		"""
		pass

	def process_observations(self):
		"""
			Does the bulk of the work for determining records. Calls get_zones to get the information out of the input table or feature class, but then does the translation to PISCES values.

			Each item for tanslation is handled by a specific method, which can be overridden with a new code class. A code class can also have multiple methods for the same field and the field to use can be chosen by the person configuring the import in the field mapping area. Species and NotesItems are not handled by handlers directly, but Species is handled by the *determine species for record* method and can be overriden there

			It is not recommended to override this method in a subclass. Instead, override the various handle_parameter methods
		:return:
		"""

		self.preprocess()

		log.info("Processing %s" % self.parent.dataset_name)

		method = input_filter_methods[self.parent.filter_code][0]  # currently uncertain of a way to make this handle multiple if_methods. It might be unnecessary though, so we'll cross that bridge when we get there
		self.parent.obs_type = method.default_observation_type

		### Figure out what it is so we can process it either as a table or as a multispecies feature class
		try:
			HUCs = self.get_zones()
		except:
			if local_vars.debug:
				raise
			else:
				raise local_vars.DataProcessingError("Unable to import dataset %s" % self.parent.dataset_path)
			# return  # skip the dataset on exception (default get_zones handles it)

		l_result = local_vars.result_set()  # make the result set
		l_observations = []  # the observations array that will be plugged into the result set

		log.info("%s records in this dataset" % len(HUCs))

		for row in HUCs:

			observation = local_vars.observation()  # make the observation

			if self.parent.species_fid is not None and self.parent.species_fid != "MUL99" and self.parent.species_fid != "filter":
				observation.species_id = self.parent.species_fid  # then we defined a specific species. Use it!
			elif "Species" in self.fmap_index:  # it legitimately might not - it's possible this table is entirely for one species
				observation.species_id = self.determine_species_for_record(
					row.__dict__[self.fmap_index["Species"].input_field])  # get the species for this record
				if observation.species_id is False:  # if it's for a species that we either aren't tracking or couldn't be determined, then
					log.debug("No species id for this record - Record discarded for observation")
					continue  # skip this record. A continue here prevents this whole loop iteration's data from being appended.
			else:  # we don't have a field, and we don't have a species id for the dataset
				log.debug("No species id for dataset and no species field defined - can't insert records - skipping!")
				continue  # skip it!

			### set the big, important values that we have a field map for
			global database_mapping

			continue_flag = 0

			notes_fields = ""
			if "NotesItems" in self.fmap_index:
				notes_fields = str(self.fmap_index["NotesItems"].input_field).split(';')
				# figure out which fields are part of the notes
			observation.other_data = row.fields_to_notes_string(notes_fields)
			# process it first so we can chuck it from the field map

			if not "Zone_ID" in self.fmap_index:  # if the Zone_ID isn't supposed to be retrieved from the field map, then we should get it from the spatial data using our defaults
				observation.zone_id = self.handle_zone_id(row=row, item=None, method=None, observation=None)

			for item in self.field_map:
				if item.field_name == "NotesItems" or item.field_name == "Species" or item is self.fmap_index[
					"NotesItems"] or item is self.fmap_index["Species"]:
					# we already processed this - skip it - theoretically species could be integrated, but it'd be a pain for end users
					continue

				l_function = self.get_handler(item)
				if l_function is True:  # if we have a function, pass the column value through it first. If we have a function, but not a column, the function should return a default
					try:
						l_value = item.handler_function_object(item, observation, row, method)  # pass it a bunch of extra information by default so that it should be able to do anything it needs
					except local_vars.DataProcessingError as lerror:  # if we get an error raised, set the flag so that we can skip this record - we can't reliably work with this record anymore
						print lerror
						continue_flag = 1
				elif l_function is False and item.input_field and not (
					row.__dict__[item.input_field] is None):  # we don't have a function, but we do have a field
					l_value = row.__dict__[item.input_field]
				else:  # we have neither function nor field
					l_value = None

				if continue_flag == 1:
					continue  # something went wrong - continue before we append

				observation.__dict__[database_mapping[item.field_name]] = l_value  # observations field

			l_observations.append(observation)

		l_result.observations = l_observations  # add all of this to the results object
		l_result.if_method = method

		# l_result = self.make_results(HUCs,method.default_observation_type,method.default_certainty,method.default_observation_type,method.method_id)
		# zones, observation_type, certainty 1, fallback certainty, if method id

		self.parent.results.append(l_result)

	def get_handler(self, l_map):
		"""
			Given a field map object, attaches the actual handler function to it for use during translation
		:param l_map:
		:return:
		"""
		if not l_map.handler_function is None:
			try:
				l_map.handler_function_object = getattr(self,
														l_map.handler_function)  # this is PROBABLY wrong - the functions will likely be stored differently as part of an object...
				return True  # yes, an object
			except AttributeError:  # there is SUPPOSED to be a function, but we can't find it! ERROR
				raise local_vars.DataProcessingError(
					"Unable to create handler function for field map for set %s and field %s" % (
					l_map.set_id, l_map.field_name))
		else:
			return False  # no object

	####
	##   Default Handlers!
	####

	def handle_zone_id(self, item, observation, row, method):
		"""
			Default way to determine zone value for the current record. Since, by default, the Gen_Table_IF class spatially joins records, it just returns the value of the HUC12 field. Can be overridden by subclasses to behave differently though

			Override in a subclass for different behavior

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as the zone/HUC12 for the current record
		"""
		return row.__dict__[local_vars.huc_field]

	def handle_certainty(self, item, observation, row, method):
		"""
			Certainty should be considered deprecated as it is not supported by the more modern PISCES tool
			meant to be overridden by subclasses - as it is, it just returns the default. This way, though, subclasses can override these small parts without having to override
			the entire process_observations() behemoth.
		"""

		return method.default_certainty

	def handle_species(self, item, observation, row, method):
		"""
			Deprecated - use determine_species for record if you want to override
			TODO: this function should not actually get used - it's a relic - consider removal!

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as species for the current record
		"""

		if item.input_field in row.__dict__:
			return row.__dict__[item.input_field]
		else:  # we should NEVER be here - if we've gotten this far without a valid species field...
			raise local_vars.DataProcessingError("Could not find a species for record - skipping")

	def handle_latitude(self, item, observation, row, method):

		"""
			Basic function that returns the value of the latitude field

			Override in a subclass for different behavior

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as latitude for the current record
		"""

		if item.input_field in row.__dict__:
			return row.__dict__[item.input_field]
		elif item.required is True:  # we should NEVER be here - if we've gotten this far without a valid latitude field... - this could be popping up unexpectedly for you if you didn't define a latitude field - in this case, it uses the default field map which includes one
			raise local_vars.DataProcessingError("Could not find a latitude for record - skipping")
		else:
			return None

	def handle_longitude(self, item, observation, row, method):
		"""
			Basic function that returns the value of the longitude field

			Override in a subclass for different behavior

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as longitude for the current record
		"""
		if item.input_field in row.__dict__:
			return row.__dict__[item.input_field]
		elif item.required is True:  # we should NEVER be here - if we've gotten this far without a valid longitude field... - this could be popping up unexpectedly for you if you didn't define a longitude field - in this case, it uses the default field map which includes one
			raise local_vars.DataProcessingError("Could not find a longitude for record - skipping")
		else:
			return None

	def handle_date(self, item, observation, row, method):
		"""
			This default method just returns the value of the field configured for dates, but you may wish to override it to convert dates to a consistent format

			Override in a subclass for different behavior

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as date for the current record
		"""
		if item.input_field in row.__dict__:  # if we have a field, return its value for the row
			return row.__dict__[item.input_field]
		elif item.required is True:  # if we don't, and it's required, raise the error - it will be caught and the record skipped
			raise local_vars.DataProcessingError("Could not find a date for record - skipping")
		else:  # if there isn't a field, and it's not required, we don't care
			return None

	def handle_observer(self, item, observation, row, method):
		"""
			Decision tree. If there's an observer field, it returns that. Otherwise, if the parent dataset has an observer configured, it returns that. Finally, if we still don't have an observer, it returns the input filter's default observer

			Override in a subclass for different behavior

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as observer for the current record
		"""
		if item.input_field in row.__dict__:  # if we have a field, return its value for the row
			return row.__dict__[item.input_field]
		else:
			if self.parent.observer is not None:  # for this default function, return the parent dataset's info if it exists
				return self.parent.observer
			elif self.default_observer is not None:
				return self.default_observer
			elif item.required is True:  # if it doesn't exist and it's required, raise the error - it will be caught and the record skipped
				raise local_vars.DataProcessingError("Could not find an observer for record - skipping")
			else:  # if there isn't a field and we'd don't have a default, but it's not required, we don't care about it - just return None
				return None

	def handle_obs_type(self, item, observation, row, method):
		"""
			By default a short decision tree, returning the value in the configured presence type field, or if that doesn't exist, then the default presence type for the input filter

			Override in a subclass for different behavior

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as observation (presence) type for the current record
		"""
		if item.input_field in row.__dict__:  # if we have a field, return its value for the row
			return row.__dict__[item.input_field]
		else:
			if method.default_observation_type is not None:  # for this default function, return the parent dataset's info if it exists
				return method.default_observation_type
			elif item.required is True:  # if it doesn't exist and it's required, raise the error - it will be caught and the record skipped
				raise local_vars.DataProcessingError("Could not find an observation type for record - skipping")
			else:  # if there isn't a field and we'd don't have a default, but it's not required, we don't care about it - just return None
				return None

	def handle_survey_method(self, item, observation, row, method):
		"""
			By default a short decision tree, returning the value in the configured survey method field, or if that doesn't exist, then the default survey method for the dataset

			Override in a subclass for different behavior

			:param item: The current parameter being processed - determined by the field map. Item is an instance of the field_map class
			:param observation: an instance of the local_vars.observation class being populated by this handler. Think of this as the current state of the output rpow
			:param row: The input data row (from the spatially joined HUC12 layer) containing HUC12 attributes and the input data
			:param method: The IF_Method instance (for accessing other properties of the input filter, such as default values
			:returns: value to be used as the survey method for the current record
		"""
		if item.input_field in row.__dict__:  # if we have a field, return its value for the row
			return row.__dict__[item.input_field]
		else:
			if self.parent.survey_method is not None:  # for this default function, return the parent dataset's info if it exists
				return self.parent.survey_method
			elif item.required is True:  # if it doesn't exist and it's required, raise the error - it will be caught and the record skipped
				raise local_vars.DataProcessingError("Could not find a survey method for record - skipping")
			else:  # if there isn't a field and we'd don't have a default, but it's not required, we don't care about it - just return None
				return None


class Filtered_Table_IF(Gen_Table_IF):
	"""
		A subclass of Gen_Table_IF designed to automatically mark new non-historical records that coincide with existing QC data as QCed (to reinforce that data),
		then leaving other data not-QCed, but available in observations.
	"""

	# TODO: This no longer inserts into the correct collection - maybe it needs to take the collection as a parameter?

	def process_observations(self):
		"""
			Overrides parent class, but calls parent class version first, then calls the filter_records method
		"""
		Gen_Table_IF.process_observations(self)  # so first, call process observations
		self.filter_records()  # then call the filter records to cull the records

	def filter_records(self):  # can remove or assign to collections

		log.info("filtering records")

		filter_cursor, filter_conn = funcs.db_connect(local_vars.maindb)
		get_qced = "select objectid from observations,observation_collections where observations.species_id = ? and observations.presence_type not in (2,4,5,8,10) and observations.zone_id = ? and observations.objectid = observation_collections.observation_id and observation_collections.collection_id in %s" % local_vars.hq_collections
		# the above query essentially states gets any non-historic/non-modeled records for this species
		# in this huc that are also part of the qc set. If we have at least one,
		# then we will add this record to the qc set automatically - otherwise we won't

		for result_set in self.parent.results:
			for observation in result_set.observations:
				results = filter_cursor.execute(get_qced, observation.species_fid, observation.zone)
				for result in results:
					# if we enter this loop, we have a record
					observation.collections.append()
					break  # only do it once

		funcs.db_close(filter_cursor, filter_conn)


class CNDDB_IF(Gen_Table_IF):
	"""
		Subclasses Gen_Table_IF to override presence type handling to map CNDDB presence types to PISCES
	"""

	def handle_obs_type(self, item, observation, row, method):
		if row.OCCTYPE == "Introduced Back into Native Hab./Range" or row.OCCTYPE == "Natural/Native occurrence":
			if row.PRESENCE == "Possibly Extirpated" or row.PRESENCE == "Extirpated":
				return 3  # historical distribution
			else:  # other option for CNDDB is "Presumed Extant"
				return 1  # extant
		if row.OCCTYPE == "Refugium; Artificial Habitat/Occurrence" or row.OCCTYPE == "Transplant Outside of Native Hab./Range":
			if row.PRESENCE == "Possibly Extirpated" or row.PRESENCE == "Extirpated":
				raise local_vars.DataProcessingError(
					"Untrackable CNDDB observation - skipping - occurrence type suggests extirpated nonnative species")  # If it's nonnative and extirpated, we don't quite care here - we don't track that - raise DataProcessingError in order to have it culled ("None resulted in it being inserted anyway, with no presence_type, which is fine for most queries, but bad for ones that don't track that)
			else:  # other option for CNDDB is "Presumed Extant"
				return 6  # translocated
		else:
			raise local_vars.DataProcessingError(
				"Invalid CNDDB record - no occurrence type (OCCTYPE) specified that we understand - we understand 'Introduced Back into Native Hab./Range', 'Natural/Native occurrence', 'Refugium; Artificial Habitat/Occurrence', and 'Transplant Outside of Native Hab./Range' - this row has '%s'" % row.OCCTYPE)


class HUC12_IF(Gen_Table_IF):
	"""
		An input filter for datasets that have a HUC12 (Zone_ID) field that directly corresponds to our own HUC_12 layer
	"""

	def get_zones(self):
		return table_to_array(self.parent.dataset_path)  # override it to just return the table

	def handle_zone_id(self, item, observation, row, method):
		return row.__dict__[item.input_field]  # essentially, return the zone_id value for the row


class TNC_HUC12_IF(HUC12_IF):
	"""
		Nature conservancy specific overrides/field mapping
	"""

	def handle_obs_type(self, item, observation, row, method):
		if row.__dict__[item.input_field] == "Current observations (post 1980)":
			return 3
		elif row.__dict__[item.input_field] == "Extirpated":
			return 10
		elif row.__dict__[item.input_field] == "Historical observation (pre 1980)":
			return 2
		elif row.__dict__[item.input_field] == "Modeled habitat/ generalized observation":
			return 4
		else:
			raise local_vars.DataProcessingError(
				"Found datatype not in value mapping. Skipping - occurence type was [%s]" % row.__dict__[
					item.input_field])


class Moyle_IF(Gen_Table_IF):
	def __init__(self, full_obs_set):
		self.all_init(full_obs_set)

		self.name_match_string = '^(.+?)poly.*$'  # we want the part at the front before the poly
		self.name_match_group = 1

	# def process_observations(self):

	# the following would be the plan if this remained as a Gen_Poly_IF
	# 0) Save the original dataset path
	# 1) select by attributes the features with a particular certainty
	# 2) set a certainty value to feed into determine_certainty
	# 3) set the dataset path to the selected features
	# 4) call the selected features into the parent process_observations
	# 5) do it again for any other certainty levels
	# 6) reset the dataset path

	#    Gen_Table_IF.process_observations(self)

	def handle_certainty(self, item, observation, row, method):
		certainty_map = {1: 2, 2: 2, 3: 3, 4: 2, 5: 3}

		if row.CONFIDENCE in certainty_map:
			return certainty_map[row.CONFIDENCE]  # return our value for the certainty level that the layer provides
		else:
			return 3

	def determine_species(self):
		InputFilter.determine_species(self, self.parent.dataset_name)

	def determine_species_for_record(self, junk):  # override - it's the same for every observation in a Moyle_IF set
		return self.parent.species_fid


class R5_Table_IF(Gen_Table_IF):
	def __init__(self, full_obs_set):
		self.define_presence_values()

		# call the parent class' version - we just want to make sure that the codes get defined
		Gen_Table_IF.__init__(self, full_obs_set)

	def define_presence_values(self):
		self.l_codes = {31: [1, 1], 32: [3, 2], 41: [1, 1], 42: [3, 2]}  # codes that tell us if they are present or not

	# each key is the codes for presence that the forest service has and the following list is Observation Type, Certainty

	def process_observations(self):
		'''Rewrites the r5 tables so that species is a column with a record for each presence'''

		log.info("Preprocessing %s" % self.parent.dataset_name)

		# copy the feature class to the calculations db. We'll read it from there so we can update the original
		out_name = os.path.join(local_vars.workspace, self.parent.dataset_name)

		import config
		if not config.use_intermediate_products or not arcpy.Exists(out_name):
			# if we specified to use intermediate products and the middle file exists, then skip this section to save time

			arcpy.Copy_management(self.parent.dataset_path, out_name)
			# add the fields we'll use
			arcpy.AddField_management(out_name, "Species", "TEXT")
			arcpy.AddField_management(out_name, "Mod_Flag", "LONG")

			# figure out which species are actually fields in this dataset
			species_fields = []
			l_fields = arcpy.ListFields(out_name)
			for field in l_fields:  # we're going to loop over the fields and check if it's in the alt_codes. This way, we know which fields are used for species - we could theoretically just loop over the alt codes, but that assumes that all datasets for a particular filter have that column, and we might get an exception.
				if field.name.upper() in alt_codes_by_filter[self.parent.filter_code]:
					log.debug("species code field found: %s" % field.name)
					species_fields.append(field.name)

			# make the cursors
			try:
				l_dataset = arcpy.SearchCursor(self.parent.dataset_path)
				l_insert = arcpy.InsertCursor(out_name)
			except:
				raise local_vars.DataProcessingError("Unable to load cursors for dataset to preprocess")

			for row in l_dataset:  # iterate over each row
				for column in species_fields:  # and scan through each of the species columns

					# log.info("Row: %s, Column: [%s]" % (row,column))
					try:
						if not (row.isNull(column) or row.getValue(column) == 0):  # if that column has a value)
							log.debug("Filling species field with %s" % column)
							new_row = l_insert.newRow()
							new_row = copy_row(new_row, row, l_fields, skip_fields=["Species", "Mod_Flag"])  # copies the values from the current row into the new row
							new_row.setValue("Species", column)  # set the species column to the alt_code - if this doesn't work, it might be because it's not an update cursor?
							new_row.setValue("Mod_Flag", 1)  # set the mod_flag
							l_insert.insertRow(
								new_row)  # then copy the row over - this can happen multiple times for a given initial record so that we get all species
					except:
						log.error("Skipping record - exception raised copying data over")
						if local_vars.debug:
							raise
						continue

			# close the tables
			del row
			del l_dataset
			del l_insert

		# TODO: Needs to be set up with a SPECIES field? or adds it directly? Check the other r5 datasets...
		# call the parent class' version now that we've done our preprocessing

		self.parent.dataset_path = out_name  # set the parent dataset path to this path in order to make the processing down the line work - it won't get deleted correctly from the input database when we do this because it'll use the intermediate source, but the initial source won't get modified.
		Gen_Table_IF.process_observations(self)

	# we need to override these two handlers and inject a check before them since the certainty and observation type are determined in each record.
	def handle_obs_type(self, item, observation, row, method):

		if not (row.Species is None or row.Species == 0):  # if the row has a species and
			if row.__dict__[row.Species] in self.l_codes.keys():  # if the value of that species' column is in the codes provided
				return self.l_codes[row.__dict__[row.Species]][1]
				# in this case, it's looking up the value of the column with the same name as the species field and returning the value in it, then translates that based on self.l_codes to a PISCES value-
			else:  # call the parent class
				return Gen_Table_IF.handle_obs_type(self, item, observation, row, method)

	def handle_certainty(self, item, observation, row, method):

		if not (row.Species is None or row.Species == 0):  # if the row has a species and
			if row.__dict__[
				row.Species] in self.l_codes.keys():  # if the value of that species' column is in the codes provided
				return self.l_codes[row.__dict__[row.Species]][1]
			else:  # call the parent class
				return Gen_Table_IF.handle_certainty(self, item, observation, row, method)


class TU_Inverts_IF(R5_Table_IF):
	"""
		Totally different datasets, but similar structure to the R5 tables. Columns are alt codes, rows are locations, species values coded for in the values
	"""

	def define_presence_values(self):
		self.l_codes = {1: [3,
							1]}  # codes that tell us if they are present or not - in the case of this filter, there's only one valid present value - everything else codes for absent.

	# each key is the codes for presence that the dataset has and the following list is the corresponding [Observation Type, Certainty]


class CDFW_Heritage_Trout_IF(Gen_Table_IF):

	def preprocess(self):
		"""
			No single field has all of the latitude and longitude information - There are four fields: a downstream latitude
			and longitude and an upstream latitude and longitude. The downstream fields are most populated, so we'll use
			them as the primary values. In the instances where they aren't populated, we'll use the upstream value. In
			some instances only one of the upstream fields is populated, but this only seems to occur when the downstream
			is fully populated, and in no instances is one of the downstream fields populated, but not the other (which
			would result in mixing coordinates from downstream and upstream if we use the code below).

			This code handles this by making new fields for latitude and longitude and trying to use the downstream
			coordinate fields when possible, and using the upstream fields in the instances that the downstream fields
			aren't populated.
		:return:
		"""

		coordinate_check = re.compile('(?P<degrees>\d+).\s+(?P<minutes>\d+)\.(?P<dec_seconds>\d+)')  # matches something like 34(degree symbol) 35.550' - we'll use it later, but let's compile it once here

		desc = arcpy.Describe(self.parent.dataset_path)
		latitude_field = "PISCES_Latitude"
		longitude_field = "PISCES_Longitude"
		if latitude_field not in desc.fields:
			arcpy.AddField_management(self.parent.dataset_path, latitude_field, "Double")
		if longitude_field not in desc.fields:
			arcpy.AddField_management(self.parent.dataset_path, longitude_field, "Double")

		latitude_fields = {"real": "Downstream_latitude__NAD83_", "backup": "Upstream_latitude__NAD83_"}
		longitude_fields = {"real": "Downstream_longitude__NAD83_", "backup": "Upstream_longitude__NAD83_"}
		records = arcpy.UpdateCursor(self.parent.dataset_path)
		for record in records:
			latitude = record.getValue(latitude_fields["real"])
			if (latitude is None or latitude == "") and latitude_fields["backup"] in desc.fields:  # if we don't have a latitude value and we have a backup field
				latitude = record.getValue(latitude_fields["backup"])
			longitude = record.getValue(longitude_fields["real"])
			if (longitude is None or longitude == "") and longitude_fields["backup"] in desc.fields:  # if we don't have a longitude value and we have a backup field
				longitude = record.getValue(longitude_fields["backup"])

			if latitude is None or longitude is None:  # have to check for this here, even though sanity check covers this case because the methods we're using to convert DDM coordinates will fail if it gets None
				continue

			# check fields for DDM coordinates and convert to decimal degrees
			latitude = common.convert_DDM_to_DD(coordinate_check, latitude)
			longitude = common.convert_DDM_to_DD(coordinate_check, longitude)

			try:  # some of the longitude coordinates are clearly latitude, and sometimes we still end up with None values - this filters both
				self.sanity_check(latitude, lower=30, upper=45)
				self.sanity_check(longitude, lower=112, upper=125)
			except local_vars.OutOfBoundsCoordinateError:
				continue

			record.setValue(latitude_field, float(latitude))
			record.setValue(longitude_field, float(longitude))
			records.updateRow(record)

	def sanity_check(self, coordinate, lower=110, upper=130):
		"""
			Many of the longitude values have what are clearly latitude values. This function checks for those values
			and raises local_vars.OutOfBoundsCoordinateError if they're found
		:param coordinate:
		:param lower:
		:param upper:
		:return:
		"""

	def handle_obs_type(self, item, observation, row, method):
		"""
			Overriding this because for the CDFW data, we want to assign it to be 1 for observed, but if it's outside
			of the species' historical range as currently established by high quality data, then we'll mark it as a 7
			for translocated observed. This method gets the list of HUCs representing the historic range, and if the
			current record's HUC isn't in that list, returns 7.
		:param item:
		:param observation:
		:param row:
		:param method:
		:return:
		"""

		if "historical_ranges" not in globals():  # we're going to store a dict in the globals that contains keys for each species - that way we only hit the DB once per species
			globals()["historical_ranges"] = {}

		if observation.species_id not in globals()["historical_ranges"]:  # hit the DB once and store the results in the global dictionary for it - future calls to this handler will use the cached value
			globals()["historical_ranges"][observation.species_id] = api.get_hucs_for_species_as_list(species_code=observation.species_id, presence_types=[2, 10])

		historical_range_for_species = globals()["historical_ranges"][observation.species_id]  # get the historical hucs for this species from the global dict

		if observation.zone_id in historical_range_for_species:
			return 1  # if this huc corresponds with the known historic range, then call it an observation
		else:
			return 7  # otherwise, call it a translocated observation

