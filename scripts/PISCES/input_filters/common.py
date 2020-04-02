from __future__ import absolute_import, division, print_function

import os
import logging

import six
import arcpy

from .. import local_vars
from ..local_vars import input_rows, DataProcessingError, input_filter_list, all_fish, get_species_from_alt_code, \
	maindb, db_last_insert, copy_data, observationsdb, remove_data, newdb, field_maps

from ..funcs import db_connect, db_close

log = logging.getLogger("PISCES.input_filters")

class EmptyRow(object):
	def __init__(self):
		pass

	def fields_to_notes_string(self, fields):  # fields comes in as a tuple of field names

		l_string = ""

		for item in fields:
			if self.__dict__.has_key(item):  # if it actually exists - otherwise we'll get a key error
				l_string = "%s%s: %s; \n" % (l_string, item, self.__dict__[item])

		return l_string

	# this class is just a base to attach unknown attributes to in the multifeature_to_HUCs function


class EmptyField(object):
	def __init__(self):
		self.value = None
		self.fielddata = None


def convert_DDM_to_DD(compiled_re_pattern, value):
	"""
		Some of the values in this dataset are of the form 34(degree symbol) 35.550' - which appear to be Degrees Decimal Minutes (DDM)
		since it mixes Degrees Minutes Seconds with Decimal Degrees. This function converts those to Decimal Degrees

		The compiled re pattern should be something like re.compile('(?P<degrees>\d+).\s+(?P<minutes>\d+)\.(?P<dec_seconds>\d+)').
		Provided as a parameter here so that it can be compiled once and passed in for converting many times
	:param value:
	:return:
	"""
	match = compiled_re_pattern.search(six.text_type(value))
	if match:  # the re (match) object should have three groups, corresponding to degrees, minutes, and decimal seconds
		degrees_matched = match.group("degrees")
		minutes_matched = match.group("minutes")
		decimal_seconds = match.group("dec_seconds")

		minutes = float("{}.{}".format(minutes_matched, decimal_seconds))
		decimal_minutes = minutes/60
		decimal_degrees = float(degrees_matched) + decimal_minutes
		return decimal_degrees
	else:
		return value  # if it doesn't match, it should already be DD, return it


def tablecoords_to_file(dataset_path, field_map, projection_index):
	# args: dataset to work on, the field that contains the x coord, the field containing the y coord, and the projection file to use

	print("Converting Coordinates to Feature Class")

	if projection_index == None:
		raise local_vars.DataProcessingError("No projection specified for dataset %s" % dataset_path)

	l_rows = table_to_array(dataset_path, True)

	index = 0
	l_max = len(l_rows)
	while index < l_max:  # we're going to check to make sure that we have x,y for each
		try:
			if l_rows[index].__dict__[field_map["Longitude"].input_field].value == None or l_rows[index].__dict__[field_map["Latitude"].input_field].value == None:  # if we don't have a value for both
				del l_rows[index]
				l_max = len(l_rows)  # update the iteration count
			else:
				index = index + 1  # only increment when we aren't deleting and items since everything following will move forward by one when we do
		except:
			raise local_vars.DataProcessingError("Unable to retrieve coordinates from %s - check your field map" % dataset_path)

	spatial_reference = arcpy.SpatialReference(int(projection_index))
	return reproject_coords(l_rows, field_map["Longitude"].input_field, field_map["Latitude"].input_field, spatial_reference)


def table_to_array(dataset_path, transfer_object=False):  # takes a path to an arcgis table (or any shape with a table) and returns an array of objects with the fields as attributes and the data filled in.

	'''somewhere along the path of creating the set of functions that this function supports, we went the roundabout way. It is likely possible that simply creating a point
		at the x,y specified in the column and assigning the .shape attribute the the point would work. Even if that didn't work, it's still very possible that a more direct conversion
		of the table to a shape would work. For now, this code functions well and is pretty robust so I'm not willing to remove this code, but note that a potentially
		serious speedup may be possible through a less roundabout method (we arrived here as requirements changed while coding)'''

	l_fields = arcpy.ListFields(dataset_path)
	for index in range(len(l_fields)):
		if (l_fields[
				index].type == "OID"):  # for whatever reason, Arc Has issues here... make sure we don't run into issues with the OBJECTID column - don't copy it
			del l_fields[index]
			break

	l_cursor = arcpy.SearchCursor(dataset_path)

	l_rows = []

	if transfer_object == True:
		''' stepping through this: This if statement really only relates to the nested for loop, but is out here to save some speed
			In the case that transfer_object is true, then we copy the whole field object over to fielddata and then the value into .value
			- this way we can access the field structure every time that field is used while the value remains discrete
			In the else case, it just stores the value for something where we aren't looking to recreate the table - just access it
		'''
		for row in l_cursor:  # for each row in the result
			l_row = EmptyRow()
			for field in l_fields:  # and for every field in that row
				l_row.__dict__[field.name] = EmptyField()
				l_row.__dict__[field.name].fielddata = field
				l_row.__dict__[field.name].value = row.getValue(field.name)
			l_rows.append(l_row)
	else:
		for row in l_cursor:  # for each row in the result
			l_row = EmptyRow()
			for field in l_fields:  # and for every field in that row
				l_row.__dict__[field.name] = row.getValue(
					field.name)  # create an attribute in the __dict__ for this instance of empty_row and set its value to the value in the table
			l_rows.append(l_row)

	return l_rows


def arcgis_table_to_list(dataset):
	"""
		Might duplicate and shorten table_to_array
	:param dataset:
	:return:
	"""

	l_fields = arcpy.ListFields(dataset)

	# DEBUG CODE
	field_names = []
	for field in l_fields:
		field_names.append(field.name)

	log.debug("Fields listed. Fields=%s" % field_names)
	l_cursor = arcpy.SearchCursor(dataset)
	records = []
	log.debug("Cursor opened")
	i = 1
	for row in l_cursor:  # for each row in the result
		if (i % 100) == 0:
			log.debug("row %s" % i)
		i += 1

		l_row = EmptyRow()
		for field in l_fields:  # and for every field in that row
			l_row.__dict__[field.name] = row.getValue(
				field.name)  # create an attribute in the __dict__ for this instance of empty_row and set its value to the value in the table
		records.append(l_row)

	return records


def multifeature_to_HUCs(feature=None, relationship="HAVE_THEIR_CENTER_IN"):
	'''base function that when provided with a feature class with multiple features
	 in it and a column containing the species designation will return a multipart feature for each species

	usage: multifeature_to_HUCS(feature_class_location)
		returns: an array of objects, sorted by species with a .zone attribute and attributes for every field in the data table.'''

	log.info("Getting Zones for multiple features")

	if feature is None:
		log.error("multifeature_to_HUCs error: No feature provided - skipping")
		return []

	arcpy.env.workspace = local_vars.workspace  # make sure the workspace is set

	try:
		feature_layer = "input_feature_layer"
		arcpy.MakeFeatureLayer_management(feature, feature_layer)
	except:
		if local_vars.debug:
			raise
		raise local_vars.DataProcessingError("Unable to make feature layer for %s" % feature)

	try:
		zones_layer = "zones_feature_layer"
		arcpy.MakeFeatureLayer_management(local_vars.HUCS, zones_layer)
	except:
		if local_vars.debug:
			raise
		raise local_vars.DataProcessingError("Unable to make feature layer for zones")

	join_shape = arcpy.CreateScratchName(prefix="temp_sjoin", workspace=local_vars.workspace)

	arcpy.SpatialJoin_analysis(zones_layer, feature_layer, join_shape, "JOIN_ONE_TO_MANY", "KEEP_COMMON",
							   match_option=relationship)
	# the above statement intersects the input features, transfers all of their attributes, discards zones without that aren't joined, and creates multiple copies of any zone where multiple input features (observations) occur
	# options for relationship defined by spatial join docs are INTERSECT,CONTAINS,WITHIN,CLOSEST - this defaults to INTERSECT but is taken as a function arg

	log.info("Spatial Join completed, getting features back")
	zones = arcgis_table_to_list(join_shape)

	log.info("Zones retrieved, cleaning up")

	arcpy.Delete_management(feature_layer)
	arcpy.Delete_management(zones_layer)
	arcpy.Delete_management(join_shape)

	log.info("Completed Getting Zones - returning\n")
	return zones


def feature_to_HUCs(feature=None, intersect_centroid="INTERSECT"):
	"""intersect_centroid is just whether we want to overlap by intersect or centroid methods"""

	# TODO: Check the projection of the data. If local_vars.auto_project == 1, then reproject it using local_vars.proj_teale_albers, otherwise, throw an EXCEPTION

	### Sample Usage
	# HUCs = []
	# HUCs,feature = input_filters.feature_to_HUCs(feature=os.path.join(local_vars.newdb,"MOY","hhpolychp"),"INTERSECT")

	####
	#### Check data validity
	####
	if feature is None:
		log.info("feature_to_HUCS error: No feature provided - skipping")
		return []

	####
	#### Set up variables
	####
	HUC12_IDs = []  # define an empty array of the IDs
	arcpy.env.workspace = local_vars.workspace  # make sure the workspace is set

	feature_name_parts = os.path.split(feature)
	feature_name = feature_name_parts[1]  # get the part of the feature's path that's just the name

	selection_name = "HUC_Select_" + feature_name + "_" + intersect_centroid
	# this name might be a bit long, but should identify info in a good way

	####
	#### Make sure we aren't overwriting existing data
	####
	try:
		local_vars.remove_data(selection_name, local_vars.workspace)
	except:
		log.info("Unable to delete existing intersection data - cannot proceed")
		raise

	####
	#### Select the features!
	####
	try:
		feature_layer = "feature_layer"  # _" + feature_name + "_" + intersect_centroid
		HUCs_layer = "all_HUCs"

		log.info("Making feature layers from feature classes for intersect - using %s" % feature)
		arcpy.MakeFeatureLayer_management(feature, feature_layer)
		arcpy.MakeFeatureLayer_management(local_vars.HUCS, HUCs_layer)

		log.info("Intersecting feature layer %s with HUCs via %s method" % (feature, intersect_centroid))
		arcpy.SelectLayerByLocation_management(HUCs_layer, intersect_centroid, feature_layer,
											   selection_type="NEW_SELECTION")
	except:
		log.info("Unable to intersect layer %s with HUCs via %s method" % (feature, intersect_centroid))
		raise

	####
	#### Write the selected features to a new feature class
	####
	arcpy.CopyFeatures_management(HUCs_layer, selection_name)

	####
	#### Get the HUCs to store in the database
	####
	rows = arcpy.SearchCursor(selection_name)
	for row in rows:
		HUC12_IDs.append(row.getValue("HUC_12"))

	###
	### Delete the data layers so we can make new ones
	###
	arcpy.Delete_management(feature_layer)
	arcpy.Delete_management(selection_name)
	arcpy.Delete_management(
		HUCs_layer)  # deleting this and recreating it is probably inefficient if we do a lot of it. We could create it outside of the loop and pass it in, but the code is cleaner if we keep it all grouped as it is now

	####
	#### Return the data
	####
	return HUC12_IDs  # selection_name is returned too so that the data can be dissolved and stored if necessary


def reproject_coords(rows, xaxis, yaxis, spatial_reference_object):
	"""
		This could likely be refactored to use MakeXYEventLayer
	:param rows:
	:param xaxis:
	:param yaxis:
	:param spatial_reference_object:
	:return:
	"""
	print("Projecting coordinates")

	arcpy.env.workspace = local_vars.workspace  # confirm that the arcpy workspace is currently correct!
	point_fc_short = "project_point"
	point_fc = os.path.join(arcpy.env.workspace, point_fc_short)  # @UndefinedVariable

	if not arcpy.Exists(point_fc):
		arcpy.CreateFeatureclass_management(arcpy.env.workspace, point_fc_short, "Point", '', "DISABLED", "DISABLED", spatial_reference_object)
	else:
		log.info("temporary feature class already exists - deleting")
		arcpy.Delete_management(point_fc)  # delete it and recreate it - to ensure it's clear
		arcpy.CreateFeatureclass_management(arcpy.env.workspace, point_fc_short, "Point", '', "DISABLED", "DISABLED", spatial_reference_object)

	for item in rows[0].__dict__.keys():  # for every field that we have here
		arcpy.AddField_management(point_fc, rows[0].__dict__[item].fielddata.name,
								  rows[0].__dict__[item].fielddata.type)  # add it to the shape

	# add the points
	cur = arcpy.InsertCursor(point_fc)

	for index in range(len(rows)):
		#log.debug("{}, {}".format(rows[index].__dict__[xaxis].value, rows[index].__dict__[yaxis].value), True)

		new_feature = cur.newRow()  # make a new row
		l_point = arcpy.Point(rows[index].__dict__[xaxis].value, rows[index].__dict__[yaxis].value)  # make the point
		new_feature.shape = l_point  # set the new row's geometry to the point
		for item in rows[index].__dict__.keys():  # set the values of its fields
			new_feature.setValue(item, rows[index].__dict__[item].value)
		cur.insertRow(new_feature)  # complete the insert

	del cur

	# project that file
	result = arcpy.CreateScratchName("project_point_proj", workspace=arcpy.env.workspace)  # @UndefinedVariable
	try:
		arcpy.Project_management(point_fc, result, local_vars.default_proj)  # TODO: This should be a function that can be called by others. Theoretically other shapes should be projected!
	except:
		if local_vars.debug:
			raise
		log.info("Unable to project the new points made from x/y data")
		arcpy.Delete_management(point_fc)  # clean up
		raise local_vars.DataProcessingError

	arcpy.Delete_management(point_fc)  # we're done with it now - just need the result

	return result


def find_HUC_by_latlong(lat,
						long):  # THIS FUNCTION IS PROBABLY DEPRECATED. CHECK tablecoords_to_file -> multifeature_to_HUC workflow

	# TODO: modify this - it should take a tuple of lat longs and an optional projection file . It will then create the points, project them to teal albers if need be and intersect them. It then returns the HUCs intersected. This way, we save on operations creating feature classes, spatial joining, etc.

	"""provided a lat/long pair (in Teale Albers meters!), it returns the HUC"""

	'''arcpy.env.workspace = local_vars.workspace #confirm that the arcpy workspace is currently correct!

	# TODO: this function should perform a sanity check. If the numbers are less than 1000, we were probably handed degrees

	log.info("finding HUC at %s, %s" % (latitude,longitude),1)
	temp_fc = os.path.join(arcpy.env.workspace, "temp_point") #@UndefinedVariable

	if not arcpy.Exists(temp_fc):
		arcpy.CreateFeatureclass_management(arcpy.env.workspace,"temp_point","Point",'',"DISABLED","DISABLED",local_vars.proj_teale_albers) #@UndefinedVariable
	else:
		log.info("temporary feature class already exists - deleting",1)
		arcpy.Delete_management(temp_fc)


	l_point = arcpy.Point(latitude,longitude,0,0,1) #lat, long,z,m,id

	# Open an insert cursor for the new feature class
	cur = arcpy.InsertCursor(temp_fc)

	new_feature = cur.newRow()
	new_feature.shape = l_point
	cur.insertRow(new_feature)

	temp_result = os.path.join(arcpy.env.workspace,"temp_result") #@UndefinedVariable

	arcpy.SpatialJoin_analysis(temp_fc,local_vars.HUCS,temp_result)

	# Create a search cursor
	rows = arcpy.SearchCursor(temp_result)
	for row in rows:
		HUC12_ID = row.getValue("HUC_12")

	log.info("HUC_12 ID found - %s\n" % HUC12_ID)

	try:
		print("deleting temporary feature classes...")
		arcpy.Delete_management(temp_fc)
		arcpy.Delete_management(temp_result)
	except:
		log.info("Unable to remove temporary feature classes")

	return HUC12_ID '''


def determine_certainty(certainties):
	for certainty in certainties:  # step through them in order - return the first valid one
		if not certainty == None:
			return certainty
	else:
		raise local_vars.DataProcessingError(
			"Unable to determine observation's certainty. Check to make sure that either the observation type or the IF_Method has a certainty assigned in the database (or ensure both do)")


def copy_row(new_row, old_row, fields, skip_fields):
	for field in fields:
		if field.editable and field.name not in skip_fields:
			new_row.setValue(field.name, old_row.getValue(field.name))

	return new_row


class observation_set:  # basic data structure that holds the data we'll be adding to the database

	def __init__(self, l_dataset_path=None, l_dataset_name=None):  # take it optionally, but allow it to be set later
		self.results = []  # contains result_set objects
		self.species_fid = None
		self.observer = None
		self.obs_date = None
		self.obs_type = None
		self.survey_method = None
		self.dataset_path = l_dataset_path
		self.dataset_name = l_dataset_name
		self.dataset_key = None  # where am I?? Lets it know where it can find itself in the datasets so that it can delete itself
		self.filter_code = None  #the extracted filter defining code from the filename
		self.input_filter = None  #the actual, initialized input filter
		self.set_id = None  # in the database, that is
		self.new_data = None  # the new data object for this item will be moved here

		log.debug("New observation set constructed - not yet added to the database")

	def setup(self, dataset_key):

		log.debug("Setting up observation set %s" % self.dataset_name)

		self.new_data = input_rows[self.dataset_name]
		del input_rows[self.dataset_name]

		# Set the values to what was brought in with self.new_data
		self.filter_code = self.new_data.Input_Filter
		self.species_fid = self.new_data.Species_ID
		self.observer = self.new_data.Observer_ID
		self.dataset_key = dataset_key
		self.survey_method = self.new_data.Survey_Method

		# Check input filter - make sure it's valid. If it isn't skip the file
		try:
			self.make_input_filter()
			self.check_species()
		except DataProcessingError as error_msg:
			log.error(error_msg)  # it already should have already removed itself from the list, so long as it was raised with the index value
			return  # and stop setting this one up

		# TODO: Validate ALL other params. Some can be blank, but if they ARE defined, they need to be valid.

		self.new_db_obs_set()

	def make_input_filter(self):

		#first, check if we have one
		if self.filter_code is None:
			raise DataProcessingError("No input filter set!", self.dataset_key)  # if we don't have an input filter, we can stop processing right here

		#then make sure it's a valid input filter - could be combined with above, but let's keep it separate for readability
		if not self.filter_code in input_filter_list:
			raise DataProcessingError("Input filter is invalid. Check the database to make sure it exists - you provided %s" % self.filter_code,self.dataset_key) # if the specified filter doesn't exist, we can stop processing right here

		#then, check if we have code for it??
		try:
			l_class = globals()[input_filter_list[self.filter_code]] #get the actual class object into l_class
			self.input_filter = l_class(self)  # then make a new input filter - the IF_List maps the code to the class - we call it with self as an argument so that it knows where its observation set is
		except:
			raise DataProcessingError("Unable to create input filter object for filter code %s - class should be %s - check to make sure there is a class for the filter code" % (self.filter_code, input_filter_list[self.filter_code]), self.dataset_key)

	def check_species(self):

		if self.species_fid == "filter":
			#TODO: This should test if the function exists. For tables, we'll need to have determine_species pass back MUL99 (Multiple species - it matches the other format for validation, but is clearly out of the ordinary)
			self.input_filter.determine_species()
		elif all_fish.has_key(self.species_fid):
			pass #we're good! It's already set correctly
		else: #if we've still got nothing, it's either an alt_code or gibberish - if it's not an alt_code, then the following function will throw a DataProcessingError
			self.species_fid = get_species_from_alt_code(self.species_fid, self.filter_code)

		if self.species_fid == "filter" or self.species_fid == None or self.species_fid is False: # the previous attempts failed...
			raise DataProcessingError("Unable to determine the species ID for dataset %s" % self.dataset_name,self.dataset_key)

	def process_data(self):
		self.input_filter.process_observations()  # dumps results as observations into self.results[]
		# TODO: The following line is a temporary fix - it shouldn't be there and should also do actual processing to determine what should be in place of the "1" - the input filter should retrieve that

		#self.add_observations()

		#self.import_to_db()

		# self.cleanup()

	def new_db_obs_set(self):

		log.debug("Creating new observation set for data")

		l_cursor, l_connection = db_connect(maindb)

		try:
			l_query = "insert into observation_sets (species,input_filter,observer,notes,dataset_notes) values (?,?,?,?,?)"
			l_cursor.execute(l_query,self.species_fid,self.filter_code,self.observer,self.new_data.Notes,self.new_data.Source_Data_Notes)
			l_connection.commit()
		except:
			raise DataProcessingError("Unable to add a record to table Observation_Sets for %s. Skipping data - this dataset will be automatically retried next time you run the program")

		l_query = "select %s as id_value" % db_last_insert

		l_identity = l_cursor.execute(l_query)

		for item in l_identity:
			self.set_id = item.id_value
		log.data_write("Observation Set %s created for %s" % (self.set_id, self.dataset_name))

		db_close(l_cursor, l_connection)

	def insert_data(self, db_cursor):  # eventually, once all the processing is done, this will add it all to the db
		# TODO: Test this function on an import. Refactoring didn't catch some renames here
		# TODO: Refactor this to use the observation.insert() method

		l_sql = "insert into observations (set_id,species_id,zone_id,presence_type,if_method,certainty,longitude,latitude,notes,other_data,observation_date,survey_method) values (?,?,?,?,?,?,?,?,?,?,?,?)"
		for result in self.results:
			for obs in result.observations:
				db_cursor.execute(l_sql, self.set_id, obs.species_id, obs.zone_id, obs.presence_type, result.if_method.method_id, obs.certainty, obs.longitude,obs.latitude,obs.notes,obs.other_data, obs.observation_date,obs.survey_method)

				# this will slow things down a bit, but probably marginally in human time...
				id_result = db_cursor.execute("select %s as t_id" % db_last_insert)
				for id_row in id_result:
					obs.db_id = id_row.t_id

	def insert_collections(self, db_cursor):
		l_sql = "insert into observation_collections (observation_id, collection_id) values (?,?)"
		for result in self.results:
			for obs in result.observations:
				for c_id in obs.collections:  # basically, if there are any collections, insert them
					db_cursor.execute(l_sql, obs.db_id, c_id)

	def record_data(self, db_cursor, db_conn):
		log.info("Inserting new records for %s" % self.dataset_name)
		log.data_write("Inserting new records for %s" % self.dataset_name)
		self.insert_data(db_cursor)  # insert the processed observations into the database

		self.insert_collections(db_cursor)  # the objectid is already set on all new observations

		log.info("Copying data source %s to observations database" % self.dataset_name)
		self.save_data(db_cursor)  # copies the source datafiles to the observations storage database and updates the source locations of the data

	def save_data(self, db_cursor):  # once we've added the observations, this copies the dataset to the observations database and updates the path in the object and the database

		#copy features

		new_name = copy_data(self.dataset_path, observationsdb) #the location defaults to the observations database
			# it returns a new name in case it has to be renamed to be copied

		#delete old features from new db

		remove_data(self.dataset_name, newdb)
		if not new_name is None: # if the copy function modified the dataset name
			self.dataset_name = new_name

		#update the database and the object with the new dataset location

		self.dataset_path = os.path.join(observationsdb, self.dataset_name)
		l_sql = "update Observation_Sets set Source_Data = ? where Set_ID = ?"
		db_cursor.execute(l_sql, self.dataset_path, self.set_id)

		#mark the input row as imported - we want that info saved in case something went wrong, so don't delete it
		self.cleanup_mark_input_row_imported()

		#TODO: Fix import and update code

	def cleanup_mark_input_row_imported(self):
		l_cursor,l_conn = db_connect(newdb, access=True)
		sql_query = "update NewData set Imported = ? where ID = ?"
		l_cursor.execute(sql_query,self.set_id,self.new_data.ID) #TODO change input_rows[...] to the objects path part
			# setting imported = set_id so that we can reimport directly from this record and the stored data in the future

		l_conn.commit()
		db_close(l_cursor, l_conn)


def import_new_data(dataset_name=None):

	new_data_fetch(dataset_name=dataset_name)  # checks for new data, validates that it exists, and puts the info in the right spots
	setup_new_data(local_vars.datasets)

	for l_set in local_vars.datasets:  # now that the datasets are loaded process them!
		if l_set is not None and (dataset_name is None or l_set.dataset_name == dataset_name):  # check that it's a valid dataset, and that we want to process it (either we're processing all, or this one)
			l_set.process_data()  # will call the input filter for each dataset to handle the importing, then call cleanups

	db_cursor, db_conn = db_connect(local_vars.maindb, "Inserting results!")  # open the db!

	log.info("\nInserting new records!")

	for l_set in local_vars.datasets:
		if l_set is not None and (dataset_name is None or l_set.dataset_name == dataset_name):
		# TODO: Handle DataStorageErrors when thrown - we'll need to roll back a lot of things
		#  depending upon where they were thrown (call dataset.cleanup(), then zero it out)
			l_set.record_data(db_cursor, db_conn)

	db_conn.commit()  # commit here, not in record_data - if we run into an error partway through one, but another succeeds, we want it all to fail.
	db_close(db_cursor, db_conn)  # close that sucker

	try:
		log.info("Compacting Database")
		arcpy.Compact_management(local_vars.newdb)  # database tends to grow quite a bit after an import run. Compact it to shrink when done
	except arcpy.ExecuteError:  # no worries if it doesn't work
		pass


def new_data_get_current_observation_sets(l_connection): #get_current_data
	l_sql = 'SELECT Source_Data FROM Observation_Sets;'
	l_cursor, l_conn = db_connect(local_vars.maindb)

	l_connection.append(l_cursor)
	l_connection.append(l_conn)

	l_data = l_cursor.execute(l_sql)

	return l_data


def new_data_fetch(dataset_name=None):
	log.info("\nChecking for new data in %s" % local_vars.newdb)

	new_data_pull(dataset_name=dataset_name)  # fetches the rows from the database that correspond to the feature sets we're about to fetch
	new_data_validate()
	new_data_dedupe()  # dedupe also sets up the observation set for each item if it's not a duplicate


def new_data_validate():
	log.debug("Ensuring new data rows have a corresponding dataset")

	arcpy.env.workspace = local_vars.newdb

	for new_data in local_vars.input_rows.keys():  # if a record in the database leads to a feature class that doesn't exist, remove it from the list to process
		if not arcpy.Exists(new_data):
			log.error("Skipping %s - No feature class exists for database row" % new_data)
			del local_vars.input_rows[new_data]
	else:
		log.debug("All database records have a corresponding dataset")

	arcpy.env.workspace = local_vars.workspace  # set the workspace back!


def new_data_dedupe():  # simply checks them against existing observations to warn if we are duplicating
	log.debug("Checking new datasets for duplicates")
	l_connection = []  # this construction is stupid - it should be changed at some point, but not right now.

	l_existing_data = new_data_get_current_observation_sets(l_connection)  # Check for redundant features - l_connection passed in so the db connection can be placed in it

	for item in local_vars.input_rows.keys():  # for each item in the list of features
		for existing_data in l_existing_data:
			if existing_data == item:  # check it against the list of existing data in the db
				log.info("Feature class %s is the same as %s - if you believe them to be different, please rename the new feature class" % (local_vars.input_rows[item], existing_data))
				del local_vars.input_rows[item]               # if if already exists, remove it from the array
				break                                   # and go to the next iteration

		print("New Feature Class: %s\n" % item)

		l_dataset = observation_set(os.path.join(local_vars.newdb, item), item)  #_init__ takes the dataset path as an optional argument
		local_vars.datasets.append(l_dataset)

	db_close(l_connection[0], l_connection[1])
	del l_connection  # clean up - this program could run a while and we want it clean

	#### Returning
	arcpy.env.workspace = local_vars.workspace


def new_data_pull(dataset_name=None):
	log.debug("Checking %s for new data" % local_vars.newdb)
	l_cursor, l_conn = db_connect(local_vars.newdb, access=True)
	l_sql = """SELECT ID,
				   Feature_Class_Name,
				   Species_ID,
				   Input_Filter,
				   Presence_Type,
				   IF_Method,
				   Observer_ID,
				   Survey_Method,
				   Notes,
				   Data_Source_Notes,
				   Input_Filter_Args,
				   Projection
			FROM NewData
			WHERE Imported = 0
			"""

	if dataset_name:
		l_sql += " AND Feature_Class_Name = '%s'" % dataset_name

	l_sql += " ORDER BY Species_ID ASC;"

	l_data = l_cursor.execute(l_sql)
	for row in l_data:
		local_vars.input_rows[row.Feature_Class_Name] = local_vars.input_data(row.ID, row.Species_ID, row.Input_Filter,
															  row.Presence_Type, row.IF_Method,
															  row.Observer_ID, row.Survey_Method, row.Notes, row.Data_Source_Notes,
															  row.Input_Filter_Args, row.Projection)
		log.debug("Found data %s in input database" % row.Feature_Class_Name)

	db_close(l_cursor, l_conn)


def setup_new_data(obs_sets):
	for key in range(len(obs_sets)):  # doing this with the index values so that we can delete it if we need to.
		try:
			obs_sets[key].setup(key)  # passing in key so that errors can be handled in the function
		except local_vars.DataProcessingError as error_msg:
			obs_sets[key] = None  #  if we get an error processing the data while setting it up, remove it from the array to skip it, but then continue - it won't be processed in the future.
							# we use = None instead of del so that the array doesn't get reindexed.
							# TODO: This solution doesn't address the problem of previously committed data.
			log.error(error_msg)