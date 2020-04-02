import os
import re
import string
import logging
import arcpy

from .. import funcs
from .. import local_vars

from ..funcs import isiterable
from ..code_library_data_files import write_column_by_key, generate_gdb_filename

log = logging.getLogger("PISCES.callbacks")

def write_results_by_key(layer, results, layer_field, results_field, layer_key="HUC_12", results_key="HUC_12", ):
	# make a lookup structure for the data
	results_dict = {}
	for row in results:
		results_dict[row.__getattribute__(results_key)] = row.__getattribute__(results_field)

	write_column_by_key(layer, layer_field, layer_key, results_dict)


def split_postprocess_cbargs(cb_args, layer, parent_layer):
	# structure the queries out of the arguments
	t_count = 0
	l_queries = []
	while t_count < len(cb_args):
		t_query = empty_object()
		t_query.query = cb_args[t_count]
		t_query.column = cb_args[t_count + 1]
		t_query.col_type = cb_args[t_count + 2]

		if isinstance(t_query.query, function_arg):  # if it's a class instance, then it's a function_arg
			t_query.run_function = True
		else:
			t_query.run_function = False

		try:
			if string.upper(t_query.col_type) == "TEXT":
				# we want to set the length on text fields
				arcpy.AddField_management(layer, t_query.column, t_query.col_type, "", "", 10000)  # add the column
			else:
				arcpy.AddField_management(layer, t_query.column, t_query.col_type)
		except:
			raise local_vars.MappingError(
				"Unable to run callback postprocess_zones - error adding field %s" % t_query.column)

		# replace entities in the query
		t_query.query = replace_variables(t_query.query, parent_layer=parent_layer)

		l_queries.append(t_query)

		t_count += 3  # skip the next 2 records

	return l_queries


def coerce_value_from_arc_type(val, col_type):
	if val is None:  # if it's None, then we don't care what type it is, just set it to None so arcpy can make it NULL
		row_val = None
	elif string.upper(col_type) == "TEXT":  # coerce types
		if isiterable(val):
			row_val = stringify(val)  # stringify is a nicer way of going about it for iterables
		else:
			row_val = str(val)
	elif string.upper(col_type) == "LONG":
		row_val = int(val)
	elif string.upper(col_type) == "FLOAT" or string.upper(col_type) == "DOUBLE":
		row_val = float(val)
	else:
		row_val = val

	return row_val


def add_field(zones_layer, db_cursor, cb_args, parent_layer):
	"""
		Very similar to postprocess_zones except it executes a query once, and joins a result to the output layer
		Meant to be used for summary queries that summarize by HUC12

	:param zones_layer:
	:param db_cursor:
	:param cb_args:
	:param parent_layer:
	:return:
	"""

	log.info("Adding field with callback query")
	# TODO: Warning, this code will leave this dataset in memory - a fixed number of these can be called in any given session
	new_name = generate_gdb_filename("callback_add_field", return_full=True)
	try:
		arcpy.CopyFeatures_management(zones_layer, new_name)
	except RuntimeError:
		log.error("Error copying zones_layer {} to new_name {}".format(zones_layer, new_name))
		raise

	l_queries = split_postprocess_cbargs(cb_args, new_name, parent_layer)  # this also adds the fields to the layers

	for l_query in l_queries:  # for every input query_object, runs the query, and passes results to function to be written out
		results = db_cursor.execute(l_query.query)
		write_results_by_key(new_name, results, l_query.column, "col_value", results_key=local_vars.zone_casting)

	return new_name


def postprocess_zones(zones_layer, db_cursor, cb_args, parent_layer):
	'''
		Takes each record in the zones_layer and runs queries related to them.
		Queries should specify the place to include the zone with sql bind variables "?" and the variable operators specified by object location relative to parent_layer (eg: {custom_query.bind_var}) are optional
		Flexible:{object path from parent layer being worked on} - example {custom_query.bind_var} would return parent_layer.custom_query.bind_var and dump it into the query at that location
		Argument Format: query,column_name,column_data_type,query,column_name,column_data_type,query...etc
		Notes: the value to be placed in the column for a given query should be selected "AS col_value" - that's what the following code will be looking to retrieve
	'''

	arcpy.env.overwriteOutput = True

	log.info("Postprocessing zones - this may take some time!")
	# log.debug("%s queries for layer" % len(cb_args) / 2)

	l_name = arcpy.CreateUniqueName('postprocessing_temp', local_vars.workspace)
	l_temp_file = os.path.join(local_vars.workspace, l_name)
	arcpy.CopyFeatures_management(zones_layer, l_temp_file)  #copy any selected zones out

	l_queries = split_postprocess_cbargs(cb_args, l_temp_file, parent_layer)

	rows = arcpy.UpdateCursor(l_temp_file)

	# for each row
	for row in rows:

		#check that it's a HUC
		if row.getValue(local_vars.huc_field) is None:
			print "skipping row..."
			continue

		# then run the queries
		for query in l_queries:
			if query.run_function:
				# if we're supposed to run a function instead of just executing the queries
				val = query.query.function_obj(zones_layer, db_cursor,
											   [query.query, row.getValue(local_vars.huc_field), cb_args], parent_layer)
			else:
				zone = row.getValue(local_vars.huc_field)
				db_cursor.execute(str(query.query), zone)
				try:
					l_result = db_cursor.fetchone()  # just get me the first row. There only should be one anyway...
					val = l_result.col_value
				except AttributeError:
					log.error("Failed to execute postprocess zones for zone %s" % (zone))
					continue

			row_val = coerce_value_from_arc_type(val, query.col_type)
			row.setValue(query.column, row_val)

		rows.updateRow(row)  # save it!

	del row
	del rows  # cleanup
	arcpy.env.overwriteOutput = False

	arcpy.Delete_management(zones_layer)  # kill the previous version
	arcpy.MakeFeatureLayer_management(l_temp_file, zones_layer)  # and read in the new one

	# return it
	return zones_layer


def stringify(in_list, delimiter=", "):
	"""
	Turns a list into a string without the "u" or brackets
	@param in_list: list to process
	@param delimiter: string denoting what to use to separate items
	@return: string
	"""
	l_string = ""

	for item in in_list:
		l_string += "%s%s" % (str(item), delimiter)

	return l_string


def replace_variables(replacement_string, parent_layer):
	while True:  # find any object requests in the query - this is bad way to do this, but it "should" break on the first non_match

		if type(
				replacement_string) != "str":  # if we pass in an object instead of a string, don't search it - it's their own damn fault for being complicated. They can search themselves
			break

		m_object = re.search("({.+?})", replacement_string)  # {.+?}

		if m_object is None:  # if we don't have any replacement variables, break
			break
		match_item = m_object.group(0)

		# get the path to the object
		if "." in match_item:  # if it has multiple parts, split it into a tuple
			object_parts = match_item.split(".")
		else:  # otherwise, make our own one item tuple
			object_parts = (match_item,)  # make it a single item tuple

		replace_object = parent_layer  # start with the layer object
		for part in object_parts:  # then for each portion of the object path
			try:
				replace_object = replace_object.__dict__[
					part]  # get that part and set it as the object to replace - effectively, move "down" the object
			except:  # I see this being very possibly called - specifying a bad path would cause this (IndexError?)
				raise local_vars.MappingError(
					"Unable to run callback postprocess_zones - couldn't get custom entity specified in {%s}" % match_item)

		replacement_string.replace("{%s}" % match_item, replace_object)

	return replacement_string


def _compose_simple_query(sql_base, sql_tables, where_clauses):
	sql_tables_str = ""
	for table in sql_tables:
		sql_tables_str += " %s," % table
	sql_tables_str = sql_tables_str[:-1]  # chop off the last ,

	sql_where_str = " WHERE"
	for where in where_clauses:
		sql_where_str += " %s and" % where
	sql_where_str = sql_where_str[:-3]  # chop off the last "and"

	return sql_base + sql_tables_str + sql_where_str


def start_query_parts(args):
	species_lim = get_arg(args, 0, "Native_Fish")
	species_limit = funcs.text_to_species_list(species_lim)  # pass it into the species/group parser
	observations_limit = get_arg(args, 1,
								 local_vars.hq_collections)  # tuple of one and three represents the defaultobservation sets we're interested in
	obs_cur = get_arg(args, 2, local_vars.current_obs_types)
	obs_hist = get_arg(args, 3, local_vars.historic_obs_types)

	sql_tables = ["observations"]
	where_clauses = []

	if species_limit:
		sql_tables.append("Species_Groups")
		sql_tables.append("defs_Species_Groups")
		where_clauses.append("defs_Species_Groups.Group_Name = \"{}\"".format(species_lim))
		where_clauses.append("Species_Groups.Group_ID = defs_Species_Groups.ID")
		where_clauses.append("Species_Groups.fid = Observations.Species_ID")

	# spp_string = ""
	# for item in species_limit:
	#	spp_string += "'%s'," % item
	# spp_string = spp_string[:-1]
	# where_clauses.append("Species_ID in (%s)" % spp_string)

	if observations_limit and observations_limit != "None":  # string version because it'll be specified in the DB
		sql_tables.append("observation_collections")
		where_clauses += ["observations.objectid = observation_collections.observation_id",
						  "observation_collections.collection_id IN (%s)" % (
							  str(observations_limit))]  # chop the list brackets off the list
	else:
		log.info("No observation collections (records) selected for limiting - if you intended to limit to a group or list of species, check your callback arguments")

	return sql_tables, where_clauses


class empty_object:
	""" @todo: this should be replaced in usage with object()"""

	def __init__(self):
		pass


class function_arg:
	''' a small class that allows us to pass around function names with an argument (or set of arguments) in a way that lets us test for it'''

	def __init__(self, function, argument):
		self.function = function
		self.argument = argument  # should be a tuple

		if callable(function):
			self.function_obj = function
		else:  # try to find it in the current namespace, but this likely won't work - we should be passing in objects, not strings
			try:
				self.function_obj = globals()[self.function]
			except:
				log.error("function used in function_arg in callback does not exist")
				raise


class query():
	"""
		An ORM would do many of the things that this class does, but we don't have one, so this will have to work
	"""

	def __init__(self):
		self.tables = []
		self.base = None
		self.where_clauses = []
		self.fish_only = True
		self.observation_types = None
		self.suffix = None

	def __str__(self):
		return self.compose()

	def __unicode__(self):
		return self.compose()

	def _compose_simple_query(self):
		sql_tables_str = " from"
		for table in self.tables:
			sql_tables_str += " %s," % table
		sql_tables_str = sql_tables_str[:-1]  # chop off the last ,

		sql_where_str = " where"
		for where in self.where_clauses:
			sql_where_str += " %s and" % where
		sql_where_str = sql_where_str[:-3]  # chop off the last "and"

		if self.suffix:
			str_suffix = self.suffix
		else:
			str_suffix = ""

		return self.base + sql_tables_str + sql_where_str + str_suffix

	def compose(self):
		"""

		"""
		if not self.base:
			raise ValueError("You must define query.base as the 'select' (or other) portion of the sql query")
		if not self.observation_types:
			log.info("Warning: No observation_types set. Will output all types together")

		if not "distinct" in self.base:
			log.info(
				"Warning: 'distinct' is not present in your database query. This doesn't mean it's incorrect, but most"
				"summary queries should use distinct to ensure non-duplication of species")

		if self.observation_types:
			self.where_clauses.append("Observations.Presence_Type in (%s)" % self.observation_types)

		self.where_clauses = list(set(self.where_clauses))  # dedupe it!
		self.tables = list(set(self.tables))  # dedupe it too - required

		return self._compose_simple_query()

	def set_defaults(self, zonal_callback=True, qc=False):
		"""
			Handles the proper method chaining for most queries
		"""
		self.add_base()
		self.set_current()

		if zonal_callback:
			self.add_zonal_callback()

		if qc is True:
			self.make_into_qc()

	def add_base(self):
		"""

		"""

		self.tables.append(local_vars.observations_table)

		if self.fish_only:
			self.tables.append(local_vars.fish_species_table)
			self.tables.append(local_vars.species_group_members_table)
			self.species_table = local_vars.fish_species_table
			self.where_clauses.append("%s.fid=%s.fid" % (local_vars.fish_species_table, local_vars.species_group_members_table))
			self.where_clauses.append("%s.group_id=1" % local_vars.species_group_members_table)
		else:
			self.tables.append(local_vars.species_table)
			self.species_table = local_vars.species_table

		self.where_clauses.append("%s.species_id = %s.fid" % (local_vars.observations_table, local_vars.species_table))

	def add_zonal_callback(self):
		self.where_clauses.append("observations.zone_id = ?")

	def make_count_query(self):
		self.base = "SELECT count(*) AS col_value FROM ("
		self.suffix = ")"

	def make_into_qc(self):
		"""

		"""
		self.tables.append("Observation_Collections")
		self.collections = local_vars.hq_collections
		self.where_clauses.append("observation_collections.collection_id in (%s)" % local_vars.hq_collections)
		self.where_clauses.append(
			"%s.objectid = observation_collections.observation_id" % local_vars.observations_table)

	def set_current(self):
		self.observation_types = local_vars.current_obs_types

	def set_historic(self):
		self.observation_types = local_vars.historic_obs_types


def get_arg(args, index, default, fieldmap=None, split_commas=False):
	# TODO: Document this function and add to autodoc
	try:
		if args[index]:
			if fieldmap and args[index] in fieldmap:  # if we want to transform this to something else
				return fieldmap[args[index]]
			if split_commas:
				return string.split(args[index], ",")
			else:
				return args[index]  # otherwise, return what was passed in
		else:  # no value, return default
			if fieldmap and default in fieldmap:  # if we want to transform this to something else
				return fieldmap[default]
			return default
	except:  # error, return the default. Error should be in getting args[index] - doesn't exist
		if fieldmap and default in fieldmap:  # if we want to transform this to something else
			return fieldmap[default]
		return default