from __future__ import absolute_import, division, print_function

import os
import shutil
import string
import traceback
import logging

import six
import pyodbc

import arcpy

if six.PY2:
	import _winreg as winreg
else:
	import winreg

from . import ARCPY_AVAILABLE
from . import log  # safe to import now because we made it not import local vars
new_log = logging.getLogger("PISCES.local_vars")  # for the future

# WORKSPACE VARIABLES
debug = True

internal_workspace = None
maindb = None
spatialdb = None
ormdb = None
newdb = None
workspace = None
	# TODO: this var may need to be adjusted since so many arc scripts just use it intrinsically for input.
calcs_mdb = None
temp = None
observationsdb = None
layer_cache = None
geo_aux = None
HUCS = None

mxd_source = None
mxd_ddp_source = None

test_folder = None
code_folder = None

#OPTIONS
auto_project = None

# data variables and input filters
all_fish = {}
input_rows = {}
datasets = []
observation_certainties = {}
input_filter_methods = {}  # dictionary containing all IF Methods. Indexed by Filter_Code, each dictionary value is an array of if_method objects that can be looked up by code
alt_codes_by_filter = {}  # each dictionary entry (input filter is the key) holds another dictionary where the alt_code returns the species id
field_maps = {}  # indexed by set id number, but not necessarily contiguous. Each entry is an array of the items required for a set

seven_zip = None
data_license = None

huc_field = "HUC_12"
zone_casting = "zone_id"  # what name do we cast HUC_12s to?

# Flags set in the arguments that tell it to skip mapping or importing respectively
importonly = 0
maponly = 0
usecache = 0  # skip generating new map layers, use the cache where possible
continue_mapping = False  # should we continue where we left off?

data_setup_run = False  # flag to let us know if this has run already so we don't run it twice

set_workspace_run = False

# three objects that help us determine the field delimiters for the HUC12 dataset - set by determine_delimiters()
zones_geospatial = None
delim_open = None
delim_close = None


layer_cache_blank = "blank_feature"

# tables
zones_aux = "zones_aux"
zones_table = "huc12fullstate"
observations_table = "observations"
invalid_observations_table = "invalid_observations"
observation_sets_table = "observation_sets"
species_table = "species"
fish_species_table = "species"
species_aux_table = "species_aux"
maps_table = "defs_query_sets"
bind_vals_table = "query_bind"
presence_types_table = "defs_observation_types"
if_methods_table = "defs_if_methods"
observers_table = "observers"
certainty_types_table = "defs_certainty_types"
collections_table = "defs_collections"
observation_collections_table = "observation_collections"
input_filters_table = "defs_input_filters"
species_groups_table = "defs_species_groups"
species_group_members_table = "species_groups"
survey_methods_table = "defs_survey_methods"
map_layers_table = "map_queries"
transactions_table = "transactions"
map_iterators_table = "query_bind"
alt_codes_table = "alt_codes"
taxonomy_table = "taxonomic_levels"

# used for exports
all_tables = [zones_aux, zones_table, observations_table, invalid_observations_table, observation_sets_table,
				species_table, species_aux_table, maps_table, bind_vals_table, presence_types_table, if_methods_table,
				observers_table, certainty_types_table, collections_table, observation_collections_table, input_filters_table,
				species_groups_table, species_group_members_table, survey_methods_table, map_layers_table, transactions_table,
				alt_codes_table, taxonomy_table]

db_true = 1  # switching from access to SQLite means that "Yes/No" no longer exists - instead, 1/0
db_false = 0
db_last_insert = "last_insert_rowid()"  # in Access it was @@IDENTITY - SQLite uses last_insert_rowid()

reg_key = r"Software\CWS\PISCES\location"

tracker_url = "https://bitbucket.org/nickrsan/pisces/issues"

current_obs_types = "1,3,6,7,9"
notrans_obs_types = "1,3,9"  # a collection that includes only non-translocated populations. We can switch current to it with a command line flag
historic_obs_types = "2,5,10"
hq_collections = "5,15,16"

# ArcGIS folder
try:
	arc_path = arcpy.GetInstallInfo()['InstallDir']  # won't work with the environment variable, and nothing in the registry seems to contain the base Arc folder.
	projections_path = os.path.join(arc_path, "Coordinate Systems")
	proj_teale_albers = arcpy.SpatialReference(3310)
	proj_utm = os.path.join(projections_path, "Projected Coordinate Systems", "UTM", "NAD 1983", "NAD 1983 UTM Zone 10N.prj")
	projections = {'UTM': proj_utm, 'Teale_Albers': proj_teale_albers}
	default_proj = proj_teale_albers
except TypeError:
	if ARCPY_AVAILABLE:
		raise
	else:
		arc_path = None
		projections_path = None
		proj_teale_albers = None
		proj_utm = None
		projections = {}
		default_proj = None
		log.warning("Couldn't set paths to arcpy coordinate systems. This will be expected if running in a non-arcpy Python environment.")

# MAPPING
map_fish = {}  # stores fish common names indexed by FID, but only for the fish we will process
all_maps = []  # stores our map objects (class fish_map)
common_layers = []  # stores references to layers that are generic so that if we use the same query in multiple places, we keep one layer with that information and only process it once

layer_files = None
export_pdf = None
export_png = None
export_mxd = None
export_ddp = None
export_web_layer_kml = None
export_web_layer_shp = None
export_web_layer_lyr = None
output_common_name = None
map_output_folder = None
mxd_output_folder = None
web_layer_output_folder = None
mapping_unique_feature_layer_id = None
web_layer_csv_writer = None
web_layer_csv_file = None
config_metadata = True
force_cache_search = True  # for items that try the layer cache first, look in the cache instead of at the data table


from .code_library_data_files import data_file


def determine_delimiters():
	global zones_geospatial, delim_open, delim_close

	zones_geospatial = data_file(os.path.join(spatialdb, zones_table))
	zones_geospatial.set_delimiters()
	delim_open = zones_geospatial.delim_open
	delim_close = zones_geospatial.delim_close


def set_workspace_vars(l_workspace=None):
	global internal_workspace, maindb, ormdb, newdb, spatialdb, workspace, calcs_mdb, temp, observationsdb, layer_cache, geo_aux
	global HUCS, mxd_source, mxd_ddp_source, test_folder
	global auto_project
	global all_fish, input_rows, datasets
	global seven_zip
	global data_license
	global set_workspace_run
	global code_folder

	if l_workspace is None and not set_workspace_run:  # if no l_workspace is provided, then do this to set the workspace

		try:
			try:
				registry = winreg.ConnectRegistry("", winreg.HKEY_LOCAL_MACHINE)  # open the registry
				base_folder = winreg.QueryValue(registry, reg_key)  # get the PISCES location
				winreg.CloseKey(registry)
			except:
				log.error("Unable to get base folder")
				raise

			internal_workspace = base_folder
			set_workspace_run = True
		except:
			log.error("Unable to set workspace - you are likely loading PISCES from another module. You must manually run set_workspace_vars if you wish to do this")
			raise
		
	elif l_workspace:  # set it to what we've provided - this is most likely to occur when called from the test setup function to reset all paths
		internal_workspace = l_workspace

	maindb = os.path.join(internal_workspace, "data", "pisces.sqlite")
	log.debug("maindb: {}".format(maindb))
	spatialdb = os.path.join(internal_workspace, "data", "PISCES_map_data.gdb")
	ormdb = os.path.join(internal_workspace, "data", "pisces.sqlite")
	newdb = os.path.join(internal_workspace, "inputs", "new_data.mdb")
	workspace = os.path.join(internal_workspace, "proc", "calculations.gdb")
	arcpy.env.workspace = workspace  # set the workspace for arcpy so other things obey this
	calcs_mdb = os.path.join(internal_workspace, "proc", "calculations.mdb")
	temp = os.path.join(internal_workspace, "proc", "temp")
	observationsdb = os.path.join(internal_workspace, "data", "observations.gdb")
	layer_cache = os.path.join(internal_workspace, "data", "layer_cache.gdb")  # TODO: Make argument
	geo_aux = os.path.join(internal_workspace, "data", "geo_aux.mdb")  # TODO: Make argument
	HUCS = os.path.join(spatialdb, zones_table)
	
	mxd_source = os.path.join(internal_workspace, "mxds", "base", "blank.mxd")
	mxd_ddp_source = os.path.join(internal_workspace, "mxds", "base", "blank_ddp.mxd")  # a default to use for USFS layers - probably not particularly useful to have since we're specifiying that doc anyway
	
	test_folder = os.path.join(internal_workspace, "test")  # folder where data goes if we are in test mode

	code_folder = os.path.join(internal_workspace, "scripts", "PISCES")

	#OPTIONS
	auto_project = 1  # sets whether we should attempt to reproject datasets that aren't in Teale Albers. If this is 1, then we will. TODO: Make parameter
	
	# data variables
	all_fish = {}
	input_rows = {}  # stores all of the input data by filename for access at the appropriate time - avoids extra SQL connections/releases and can be accessed later
	datasets = []
	
	seven_zip = os.path.join(internal_workspace, "utils", "7za.exe")
	data_license = os.path.join(internal_workspace, "license.htm")

	determine_delimiters()

set_workspace_vars()
# import other PISCES items after running set_workspace_vars

from PISCES import __version__
version = __version__


### We're duplicating the database connection code here to avoid a circular import - in the future it'd be good to get it out of here entirely. But baby steps
def db_connect(db_name, note=None, access=False):

	log_string = "Making database connection to %s" % db_name

	if note is not None:
		log_string += " - note added: %s" % note

	log.write(log_string)

	if not access:
		conn = pyodbc.connect('DRIVER=SQLite3 ODBC Driver;Database=%s' % db_name)
	else:
		conn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb)};DBQ='+db_name)

	return conn.cursor(), conn


def db_close(cursor, conn):
	log.write("Closing database connection")
	cursor.close()
	conn.close()

def start(arc_script=False):
	set_workspace_vars()  # call it immediately
	check_workspace()
	log.initialize("PISCES starting", arc_script=arc_script)
	log.write("Starting PISCES", True)
	mapping_setup()  # import config, overwriting variables - janky, I know
	data_setup()


# Error Classes

class GenError(Exception):

	def __init__(self, value):
		self.value = value
		log.error(value)

	def __str__(self):
		return repr(self.value)

class IFError(Exception):  # an IFError relates to the input filter and determining it. We want to catch it separately

	def __init__(self, value):
		self.value = value
		log.error(str(value))

	def __str__(self):
		return repr(self.value)

class OutOfBoundsCoordinateError(Exception):
	def __init__(self, value):
		self.value = value
		log.error(str(value))

	def __str__(self):
		return repr(self.value)

class DataProcessingError(Exception):

	def __init__(self, value=None, set_index=None):
		
		if not set_index is None:  # if the dataset is provided when the error is raised, remove the dataset from processing
			datasets[set_index] = None  # using = None instead of del so that it doesn't get reindexed. We'll need to check for a value when we loop now.
		
		log.error(str(value))
		
		self.value = value  # set the error string

	def __str__(self):
		return "\nCritical Error:" + repr(self.value)


class DataStorageError(Exception):  # used after all the data is processed to detect custom errors

	def __init__(self, value=None):
	
		self.value = value  # set the error string
		log.error(value)

	def __str__(self):
		return "\nCritical Error:" + repr(self.value)


class MappingError(Exception):  # used after all the data is processed to detect custom errors

	def __init__(self, value=None):
	
		self.value = value  # set the error string
		
		log.error("%s - stack trace follows: %s" % (value, traceback.print_exc()))
		
	def __str__(self):
		return "\nMapping Error:" + repr(self.value)
	
# Main program classes


class fish:  # this class will be used for internal program representation of the fish data table for quick local lookups
	def __init__(self):
		self.species = None
		self.fid = None
		self.alt_codes = []
		
		self.sci_name = None
		#a dictionary of this class will be maintained based on the fid for lookup

class input_data: # used for temporary storage of the db rows

	# TODO: change i1,i2, etc in __init__ below to be more semantic
	def __init__(self, i1=None, i2=None, i3=None, i4=None, i5=None, i6=None, i7=None, i8=None, i9=None, i10=None, i11=None):  # be ready for all of it to be passed in via constructor
		self.ID = i1
		self.Species_ID = i2
		self.Input_Filter = i3
		self.Presence_Type = i4
		self.IF_Method = i5
		self.Observer_ID = i6
		self.Survey_Method = i7
		self.Notes = i8
		self.Source_Data_Notes = i9
		self.Input_Filter_Args = i10
		self.Projection_Key = i11


class observation:  # contains data related to a particular observation data file
	def __init__(self):
		self.observer = None
		self.species_id = None
		self.zone_id = None  # Zone == HUC - trying to make this program a little more generic
		self.observation_date = None
		self.presence_type = None
		self.latitude = None  # TODO: should this be the polygon centroid for polygons? Same for next
		self.longitude = None
		self.notes = None  # info from the input filter, etc that gets tacked on to the records
		self.other_data = None  # place to store additional data from an import that we think is valuable to keep in a human readable form
		self.certainty = None
		self.survey_method = None
		self.collections = []  # added 12/13/2011 - input filters can add collection_ids to this list and any collections present will be inserted for the observation
		self.objectid = None  # added 12/13/2011 - lets us set this here and call another method on the db to insert collections
		self.set_id = None  # added 10/10/2013 - does not reference parent object on imports. Just an integer, and not set by importing code
		self.if_method = None  # same as previous
		self.date_added = None  # similar to previous. Not set by Input Filter, but used when selecting observations back out

		self.table_used = "observations"  # used when selecting from other tables that are like observations

		self.not_db_items = ('not_db_items', 'table_used', 'collections', 'do_not_add', 'observer', 'table_specific_not_db_items')  # items that don't correspond to the obs table - observer is because it's a property of if_method, really
		self.do_not_add = ('objectid',)  # items to not include in an insert
		self.table_specific_not_db_items = {'invalid_observations': ['date_added', ], 'observations': []}  # similar to not_db, but for specific tables. a kluge. TODO: Make this a better solution

	def load(self, record_id, from_table=None, db_cursor=None):
		"""
			Given an observation id, loads the relevant observation from the database into this object
			use from_table to override the table to use (ie, to make an Invalid_Observations object. If db_cursor
			is provided, it will be used for the database. Otherwise, a new connection will be made.
		"""
		log.write("Objectid: %s" % record_id, 1)
		if from_table:
			self.table_used = from_table

		close_cursor = False
		db_conn = None
		if not db_cursor:  # open a new cursor if we don't have one yet, note in var that we opened it so we can close it
			db_cursor, db_conn = db_connect(maindb, "loading observations")
			close_cursor = True

		select_str = """
						SELECT objectid,
					   set_id,
					   species_id,
					   zone_id,
					   notes,
					   longitude,
					   latitude,
					   presence_type,
					   if_method,
					   certainty,
					   other_data,
					   survey_method,
					   observation_date"""
		if self.table_used.lower() == "observations":  # hack to make it work slightly differently for the two separate tables
			select_str += ", date_added"
		select_str += " FROM %s where objectid = ?" % self.table_used

		results = db_cursor.execute(select_str, record_id)  # pass record_id as bind value
		record = results.fetchone()
		if not record:
			return

		fields = [t[0] for t in db_cursor.description]
		for field in fields:
			setattr(self, str(field).lower(), record.__getattribute__(field))  # using field for both keys because we wrote them as "as" statements in the querhy

		# ok, now get the collections and append them to the list on the object
		select_collections = "SELECT collection_id from observation_collections where observation_id = ?"
		collections_res = db_cursor.execute(select_collections, record_id)
		for collection in collections_res:
			self.collections.append(collection.Collection_ID)

		if close_cursor:
			db_close(db_cursor, db_conn)

	def insert(self, db_cursor):
		"""
			If we have data, then insert it into the database as a new record, returning the record id and setting it as an attribute. Use builtin funcs for this, passing a dictionary

		:param db_cursor:
		"""

		# The following is a funky way of copying the object dictionary while excluding a few items (the items that don't
		# correspond to DB fields) - creates a new dict, looks at every key on the object, and exclude the fields defined
		# in the exclusion variables not_db_items and do_not_add

		insert_dict = {}
		for key in self.__dict__:
			if key not in self.not_db_items and key not in self.do_not_add and key not in self.table_specific_not_db_items[self.table_used]:
				insert_dict[key] = getattr(self, key)

		query = compose_query_from_dict(self.table_used, insert_dict)
		db_cursor.execute(query)

		# get the objectid
		l_query = "select %s as id_value" % db_last_insert
		l_identity = db_cursor.execute(l_query).fetchone()
		self.objectid = l_identity.id_value

		self.insert_collections(db_cursor)  # now insert the collections for this record

	def insert_collections(self, db_cursor):
		"""

		:param db_cursor:
		:return:
		"""

		if self.table_used.lower() != "observations":
			log.write("skipping collections addition because table is %s" % self.table_used)
			return

		for collection_id in self.collections:
			query = "insert into observation_collections (observation_id, collection_id) values (%s,%s)" % (self.objectid, collection_id)

			try:
				db_cursor.execute(query)
			except pyodbc.IntegrityError as err:
				# likely means that this record already exists if we're violating an integrity constraint
				log.write("skipping insert for record %s and collection_id %s because it failed a constraint"
						  " (IntegrityError) - probably a duplicate" % (self.objectid, collection_id))


class result_set:
	def __init__(self, p_observations=None, p_if_method=None):
		if p_observations is None:
			p_observations = []

		self.observations = p_observations  # contains observation objects
		self.if_method = p_if_method


def print_workspace_vars():
	log.debug("\n\nUsing workspace:")
	log.info("\tMain Database: {}".format(maindb))
	print("\tInternal Workspace: %s" % internal_workspace)
	print("\tWorkspace: %s" % workspace)
	print("\tNew Data Database: %s" % newdb)
	print("\tObservations Database: %s" % observationsdb)
	print("\tLayer Cache: %s" % layer_cache)
	print("\tAuxiliary Geographic Data: %s\n" % geo_aux)
	print("\tUsing Observation Types in: %s\n" % current_obs_types)
	print("\tUsing Historic Observation Types in: %s\n" % historic_obs_types)
	print("\tUsing Collections in (when using high quality collections): %s\n" % hq_collections)

def log_version_information():
	log.info("PISCES code version {}. Date last record added to database: {}.".format(version, most_recent_record()))

def data_setup():
	"""
		Main function calling various others to set up internal variables that speed up PISCES
	"""

	global all_fish

	log_version_information()
	log.write("Loading Configuration Data", 1)
	all_fish = get_species_data()
	check_observations_db()  # checks to make sure we have an observations db to import to
	get_input_filter_list()  # populate the IF list
	retrieve_input_filter_methods()  # populate the listing of methods for each IF
	pull_alt_codes()
	get_observation_certainties()  # populates the dictionary of default certainties for observations
	pull_field_maps()

	global data_setup_run
	data_setup_run = True


def initialize():
	"""
		Just an alias for data_setup
	:return:
	"""

	data_setup()


def projection_code_to_file(projection_code):  # probably doesn't need to be a function (since it's just looking things up in a dict), but in the interest of a standard interface, this works
	return projections[projection_code]


def get_version():
	"""
		Just a compatibility function
	:return:
	"""
	return version


def get_observation_certainties():
	global observation_certainties

	db_cursor, db_conn = db_connect(maindb)

	l_sql = "select type, default_certainty from defs_observation_types order by type"
	l_results = db_cursor.execute(l_sql)

	for result in l_results:
		observation_certainties[result.type] = result.default_certainty

	db_close(db_cursor, db_conn)


def check_observations_db():
	try:
		if not arcpy.Exists(observationsdb):
			obs_db = os.path.split(observationsdb)
			arcpy.CreateFileGDB_management(obs_db[0], obs_db[1])
	except:
		log.write(auto_print=1, log_string="Unable to check on existence of observations geodatabase or create new database")
		raise


def get_input_filter_list():
	log.write("Getting input filter information from the database")

	l_sql = 'select code, class as l_class from defs_input_filters;'
	l_cursor, l_conn = db_connect(maindb)

	l_data = l_cursor.execute(l_sql)

	for l_filter in l_data:
		input_filter_list[l_filter.code] = l_filter.l_class

	db_close(l_cursor, l_conn)

	return


def retrieve_input_filter_methods():
	db_cursor, db_conn = db_connect(maindb, "Retrieving IF_Methods")

	l_sql = """
		SELECT defs_if_methods.objectid,
			   defs_if_methods.short_name,
			   defs_if_methods.description,
			   defs_if_methods.default_observation_type,
			   defs_if_methods.default_certainty,
			   defs_input_filters.code,
			   defs_if_methods.trigger
		FROM defs_if_methods
		INNER JOIN defs_input_filters ON ((defs_if_methods.input_filter) = defs_input_filters.objectid)
	 """

	db_results = db_cursor.execute(l_sql)  # get all of the IF_Methods for this input filter type

	for result in db_results:  # map them to a if_method object and append it to the methods for this IF
		l_method = InputFilterMethod()
		l_method.method_id = result.objectid
		l_method.short_name = result.short_name
		l_method.description = result.description
		l_method.default_observation_type = result.default_observation_type
		l_method.default_certainty = result.default_certainty
		l_method.trigger = result.trigger

		if not result.code in input_filter_methods:
			input_filter_methods[result.code] = []

		input_filter_methods[result.code].append(l_method)

	db_close(db_cursor, db_conn)


def pull_alt_codes():
	global alt_codes_by_filter  # we're using the shared variable

	l_cursor, l_conn = db_connect(maindb, "Pulling Alt Codes")

	l_sql = "select input_filter, fid, alt_code from alt_codes order by input_filter asc"

	l_results = l_cursor.execute(l_sql)
	for row in l_results:
		l_alt_code = string.upper(row.alt_code)  # make sure we're always comparing apples to apples
		if not row.input_filter in alt_codes_by_filter:  # if this is the first one for this filter
			alt_codes_by_filter[row.input_filter] = {}  # make the dictionary
		alt_codes_by_filter[row.input_filter][l_alt_code] = row.fid  # set the key of the Alt_Code to the FID

	db_close(l_cursor, l_conn)


def check_workspace():
	"""
		Checks to make sure we have the temporary working locations. Creates them if we don't. Errors get raised if not.
	:return:
	"""
	if not os.path.exists(workspace):
		clean_location(workspace, "FGDB")
	if not os.path.exists(calcs_mdb):
		clean_location(calcs_mdb, "PGDB")
	if not os.path.exists(temp):
		clean_location(temp, "Folder")


def pull_field_maps():
	global field_maps

	db_cursor, db_conn = db_connect(newdb, "Getting field maps", access=True)

	l_sql = "select f1.newdata_id, f1.field_name, f1.input_field, f1.handler_function, f1.required from fieldmapping as f1 LEFT OUTER JOIN newdata as f2 ON f1.newdata_id = f2.id where (f2.imported = 0 or f1.newdata_id = 0) order by f1.newdata_id asc"  # "where Imported = 0" might not work well...but it should - that's the criteria on the importing data as wellselect f1.NewData_ID, f1.Field_Name, f1.Input_Field, f1.Handler_Function, f1.Required from FieldMapping as f1 OUTER JOIN NewData as f2 ON f1.NewData_ID = f2.ID where f2.Imported = 0 order by f1.NewData_ID asc" # "where Imported = 0" might not work well...but it should - that's the criteria on the importing data as wellselect f1.NewData_ID, f1.Field_Name, f1.Input_Field, f1.Handler_Function, f1.Required from FieldMapping as f1 OUTER JOIN NewData as f2 ON f1.NewData_ID = f2.ID where f2.Imported = 0 order by f1.NewData_ID asc" # "where Imported = 0" might not work well...but it should - that's the criteria on the importing data as well
	rows = db_cursor.execute(l_sql)

	for row in rows:
		if row.newdata_id not in field_maps:  # if we don't already have the array in place
			field_maps[row.newdata_id] = []  # make it into an empty array

		l_map = FieldMap()
		l_map.field_name = row.field_name
		l_map.handler_function = row.handler_function
		l_map.input_field = row.input_field
		l_map.set_id = row.newdata_id
		l_map.required = row.required

		field_maps[row.newdata_id].append(l_map)

	db_close(db_cursor, db_conn)


def get_species_data():
	log.write("Retrieving species data from main database", 1)

	db_cursor, db_conn = db_connect(maindb)

	l_sql = 'select fid, common_name, scientific_name from species'
	l_data = db_cursor.execute(l_sql)

	all_fish = {}
	for l_item in l_data:  # for every fish that's returned from the database
		all_fish[l_item.fid] = fish()  # create a new fish object in the all_fish dictionary, keyed on the fid
		all_fish[l_item.fid].fid = l_item.fid  # and add the parameter data
		all_fish[l_item.fid].species = l_item.common_name
		all_fish[l_item.fid].sci_name = l_item.scientific_name

	if len(all_fish.keys()) == 0:
		log.error("PISCES failed to load fish information from the database and will not function correctly. PISCES may not be installed correctly.")

	db_close(db_cursor, db_conn)

	return all_fish


def compose_query_from_dict(table, value_pairs):
	query_fields = "("
	query_values = "("

	query = "INSERT INTO %s " % table

	for key in value_pairs:
		query_fields += key + ", "
		if value_pairs[key] is None:
			query_values += "NULL, "
		elif type(value_pairs[key]) is int or type(value_pairs[key]) is float:
			query_values += "%s, " % value_pairs[key]
		else:
			escape_me = str(value_pairs[key])
			escape_me = escape_me.replace("'", "''")  # replace single quotes in strings with a double single because we're going to wrap in singles.
			query_values += "'%s', " % escape_me

	query_fields = query_fields[:-2]
	query_values = query_values[:-2]  # chop off the final comma and space

	query_fields += ")"
	query_values += ")"

	query += query_fields + " VALUES " + query_values
	return query


def clean_location(path, path_type="FGDB"):
	"""
		Cleans and recreates a particular type of workspace. Types include file geodatabases, personal geodatabases, and folders
	:param path: the full path to the item to clean
	:param path_type: one of the following: (FGDB, PGDB, Folder) for File Geodatabase, Personal Geodatabase, and folders, respectively
	:return:
	"""

	if path_type not in ("FGDB", "PGDB", "Folder"):
		raise ValueError("path_type must be one of (FGDB, PGDB, Folder)")

	if path_type == "Folder":
		if os.path.exists(path):  # delete the folder if it exists
			shutil.rmtree(path)

		os.mkdir(path)  # then recreate it
	else:
		if arcpy.Exists(path):  # if we have a GDB, delete it
			arcpy.Delete_management(path)

		path_parts = os.path.split(path)  # Now recreate it based on type
		if path_type == "FGDB":
			arcpy.CreateFileGDB_management(path_parts[0], path_parts[1])  # then recreate it - fastest way to compact a temp GDB
		elif path_type == "PGDB":
			arcpy.CreatePersonalGDB_management(path_parts[0], path_parts[1])


def copy_data(feature_class, new_location):  # get a full path and a place to copy it to, defaulting to the observations database
	"""
		A wrapper for copying data to gdbs that checks for existence and creates unique names if need be
	:param feature_class:
	:param new_location:
	:return:
	"""

	l_file_split = os.path.split(feature_class)
	out_name = l_file_split[1]

	out_name = arcpy.CreateUniqueName(out_name, new_location)  # if the name already exists in the output location, start renaming it with an iterator until we reach one that doesn't

	arcpy.Copy_management(feature_class, os.path.join(new_location, out_name))
	log.write("Saving %s to %s" % (feature_class, new_location))

	return out_name


def remove_data(item_name, l_workspace=arcpy.env.workspace):  # checks if a feature exists, then deletes it
	t_wkspc_save = arcpy.env.workspace  # @UndefinedVariable

	arcpy.env.workspace = l_workspace  # get the workspace of the function calling this so we remove the correct item
	# this should actually be carried across functions...should use the same workspace as before.

	if arcpy.Exists(item_name):  # if it exists
		try:
			arcpy.Delete_management(item_name)  # delete it
		except:
			log.error("Failed to remove the input dataset from the input database. Please remove it manually")

	arcpy.env.workspace = t_wkspc_save


class InputFilterMethod(object):
	def __init__(self):
		self.method_id = None  # corresponds with OBJECTID
		self.short_name = None
		self.description = None
		self.default_observation_type = None
		self.default_certainty = None
		self.trigger = None  # the thing to use when we're iterating


class FieldMap(object):
	def __init__(self):
		self.set_id = None  # needs this since before being assigned to the input data, this will sit in a list/dict
		self.field_name = None
		self.matched_field = None  # this might not be needed - this is in case the actual field varies from the name specified in field name - this would be the database table.column we actually want to use
		self.input_field = None
		self.handler_function = None  # this is just the name we pull from the db
		self.handler_function_object = None  # this is the retrieved object to run


input_filter_list = {}  # this will be filled in on program init


def get_species_from_alt_code(l_alt_code_species, filter_code):

	l_alt_code_species = string.upper(l_alt_code_species)  # standardize everything coming in - they alt codes are indexed in caps

	if filter_code in alt_codes_by_filter and l_alt_code_species in alt_codes_by_filter[filter_code]:  # if the input filter has alt codes and this alt code is defined
		return alt_codes_by_filter[filter_code][l_alt_code_species]
	else:
		return False



def mapping_process_config():

	if not os.path.exists(web_layer_output_folder):
		raise ValueError("Output folder for web layers (KML, Shp, and Lyr) doesn't exist. Please run the Configuration Options tool.")
	if not os.path.exists(map_output_folder):
		raise ValueError("Output folder for static maps (images and PDFs) doesn't exist. Please run the Configuration Options tool.")
	if not os.path.exists(mxd_output_folder):
		raise ValueError("Output folder for Map Documents (MXDs) doesn't exist. Please run the Configuration Options tool.")

	if not debug:
		return

	if export_pdf is False:
		log.write("PDF Export disabled via export_pdf config variable - PDFs will not be generated", 1)
	if export_png is False:
		log.write("PNG Export disabled via export_png config variable - PNGs will not be generated", 1)
	if export_mxd is False:
		log.write("MXD Export disabled via export_mxd config variable - MXDs will not be saved", 1)


def mapping_setup():
	# set up variables that will be overridden - populate them by default in case config doesn't load. DON'T CHANGE THEM HERE - change them in config.py instead
	global layer_files, export_pdf, export_png, export_ddp, export_web_layer_kml, export_web_layer_shp, export_web_layer_lyr, output_common_name, map_output_folder, \
			mxd_output_folder, web_layer_output_folder, mapping_unique_feature_layer_id, web_layer_csv_writer, web_layer_csv_file, map_fish, all_maps, common_layers

	layer_files = ["gen_1.lyr", "gen_2.lyr", "gen_3.lyr", "gen_4.lyr", "gen_5.lyr"]
	export_pdf = True
	export_png = False
	export_mxd = True
	export_ddp = False
	export_web_layer_kml = False
	export_web_layer_shp = False
	output_common_name = True
	map_output_folder = os.path.join(internal_workspace, "maps", "output")
	mxd_output_folder = os.path.join(internal_workspace, "mxds", "output")
	web_layer_output_folder = os.path.join(internal_workspace, "maps", "web_output", "layers")

	mapping_unique_feature_layer_id = 0  # this id is used when a script is storing multiple layers for one final output from memory. incremented when used

	web_layer_csv_writer = None
	web_layer_csv_file = None

	import config
	reload(config)  # without forcing a refresh of the config here, moving the database won't work correctly in ArcMap
	mapping_process_config()

	global map_fish, all_maps, common_layers
	map_fish = {}  # stores fish common names indexed by FID, but only for the fish we will process
	all_maps = []  # stores our map objects (class fish_map)
	common_layers = []  # stores references to layers that are generic so that if we use the same query in multiple places, we keep one layer with that information and only process it once

def most_recent_record(db_cursor=None):
	"""
		A supplement to the code version for the database - when was the last observation record added? Won't show
	:return:
	"""

	close_connection = False
	if not db_cursor:
		close_connection = True
		db_cursor, db_conn = db_connect(maindb)

	try:
		results = db_cursor.execute("select max(date_added) as max_val from observations")  # pass record_id as bind value
		record = results.fetchone()
		return record.max_val

	finally:
		if close_connection:
			db_cursor.close()
			db_conn.close()


