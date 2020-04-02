"""
	This script migrates in some code library code on spatial data files to remove it as a separate dependency
"""
import os
import tempfile
import sys
import re
import traceback

import arcpy

import log

try:
	coordinate_systems = os.path.join(arcpy.GetInstallInfo()['InstallDir'], "Coordinate Systems")
	projected_coordinate_systems = os.path.join(coordinate_systems, "Projected Coordinate Systems")
	teale_albers = os.path.join(projected_coordinate_systems, "State Systems",
								"NAD 1983 California (Teale) Albers (Meters).prj")
except:
	log.warning(
		"unable to GetInstallInfo for ArcGIS. If you are not using an arcpy project, this is not a big deal and can be ignored")

temp_folder = None
temp_gdb = None
raster_count = 0

delims_open = {'mdb': "[", "sqlite": "\"", 'gdb': "\"", 'shp': "\"",
			   'in_memory': ""}  # a dictionary of field delimiters for use in sql statements. We don't always know that the huc layer will be stored
delims_close = {'mdb': "]", "sqlite": "\"", 'gdb': "\"", 'shp': "\"",
				'in_memory': ""}  # in one type of field or another. These two are just extension based lookups


class geospatial_object:

	def setup_object(self):
		'''like __init__ but won't be overridden by subclasses'''

		if 'setup_run' in self.__dict__:  # check if we have this key in a safe way
			if self.setup_run is True:  # have we already run this function
				return  # don't run it again

		self.setup_run = True
		self.gdb = None
		self.temp_folder = None
		self.temp_gdb = None

	def check_temp(self):
		self.setup_object()

		if not self.temp_folder or not self.temp_gdb:
			try:
				self.temp_folder = tempfile.mkdtemp()
				temp_gdb = os.path.join(self.temp_folder, "join_temp.gdb")
				if arcpy.Exists(temp_gdb):
					self.temp_gdb = temp_gdb
				else:  # doesn't exist
					if 'log' in sys.modules:
						log.write("Creating %s" % temp_gdb, True)
					arcpy.CreateFileGDB_management(self.temp_folder, "join_temp.gdb")
					self.temp_gdb = temp_gdb
			except:
				return False
		return True

	def get_temp_folder(self):
		self.setup_object()

		if self.check_temp():
			return self.temp_folder
		else:
			raise IOError("Couldn't create temp folder")

	def get_temp_gdb(self):
		self.setup_object()

		if self.check_temp():
			return self.temp_gdb
		else:
			raise IOError("Couldn't create temp gdb or folder")


class data_file(geospatial_object):
	def __init__(self, filename=None):
		self.data_location = filename
		self.delim_open = None
		self.delim_close = None

	def set_delimiters(self):

		log.debug("Setting delimiters")

		try:
			fc_info = arcpy.ParseTableName(self.data_location)
			database, owner, featureclass = fc_info.split(",")
		except:
			log.error("Failed to assess data format")
			return False

		log.debug("Type from ParseTableName = %s" % featureclass)

		if re.match(" mdb", featureclass) is not None or re.search("\.mdb", featureclass) is not None:
			self.delim_open = delims_open['mdb']
			self.delim_close = delims_close['mdb']
		elif re.match(" gdb", featureclass) is not None or re.search("\.gdb", featureclass) is not None:
			self.delim_open = delims_open['gdb']
			self.delim_close = delims_close['gdb']
		elif re.match(" shp", featureclass) is not None or re.search("\.shp", featureclass) is not None:
			self.delim_open = delims_open['shp']
			self.delim_close = delims_close['shp']
		elif re.match(" sqlite", featureclass) is not None or re.search("\.db", featureclass) is not None or re.search(
				"\.sqlite", featureclass) is not None:
			self.delim_open = delims_open['sqlite']
			self.delim_close = delims_close['sqlite']
		elif re.match(" in_memory", featureclass) is not None or re.search("in_memory",
																		   featureclass) is not None:  # dbmses use no delimeters. This is just a guess at how to detect if an fc is in one since I don't have access yet.
			self.delim_open = delims_open['in_memory']
			self.delim_close = delims_close['in_memory']
		elif re.match(" sde",
					  featureclass) is not None:  # dbmses use no delimeters. This is just a guess at how to detect if an fc is in one since I don't have access yet.
			self.delim_open = ""
			self.delim_close = ""
		else:
			log.warning(
				"No field delimiters for this type of data. We can select features in gdbs, mdbs, shps, in_memory, and possibly sde files (untested)",
				True)
			return False

		return True


def generate_fast_filename(name_base="xt", return_full=True, scratch=True):
	'''uses the in_memory workspace and calls generate_gdb_filename with that as the gdb'''

	return generate_gdb_filename(name_base, return_full, "in_memory", scratch)


def generate_gdb_filename(name_base="xt", return_full=True, gdb=None, scratch=False):
	'''returns the filename and the gdb separately for use in some tools'''
	if gdb is None:
		temp_gdb = get_temp_gdb()
	else:
		temp_gdb = gdb

	try:
		if scratch:
			filename = arcpy.CreateScratchName(name_base, workspace=temp_gdb)
		else:
			filename = arcpy.CreateUniqueName(name_base, temp_gdb)
	except:
		log.error("Couldn't create GDB filename - %s" % traceback.format_exc())
		raise

	if return_full:
		return filename
	else:
		return os.path.split(filename)[1], temp_gdb


def make_temp(override=False):
	"""
		override enables us to say just "give me a new temp gdb and don't try to manage it"
	"""

	global temp_gdb
	global temp_folder
	global raster_count

	if not override:
		if temp_gdb and raster_count < 100:
			raster_count += 1
			return temp_folder, temp_gdb
		else:
			raster_count = 0

	try:
		temp_folder = tempfile.mkdtemp()
		temp_gdb = os.path.join(temp_folder, "temp.gdb")
		if not arcpy.Exists(temp_gdb):
			if 'log' in sys.modules:
				log.write("Creating %s" % temp_gdb, True)
			arcpy.CreateFileGDB_management(temp_folder, "temp.gdb")
			return temp_folder, temp_gdb
	except:
		return False, False


def get_temp_folder():
	temp_folder, temp_gdb = make_temp()
	if temp_folder:
		return temp_folder
	else:
		raise IOError("Couldn't create temp gdb or folder")


def get_temp_gdb():
	temp_folder, temp_gdb = make_temp()
	if temp_gdb:
		return temp_gdb
	else:
		raise IOError("Couldn't create temp gdb or folder")


def check_spatial_filename(filename=None, create_filename=True, check_exists=True, allow_fast=False):
	'''usage: filename = check_spatial_filename(filename = None, create_filename = True, check_exists = True). Checks that we have a filename, optionally creates one, makes paths absolute,
		and ensures that they don't exist yet when passed in. Caller may disable the check_exists (for speed) using check_exists = False
	'''

	if not filename and create_filename is True:
		# if they didn't provide a filename and we're supposed to make one, then make one
		if allow_fast:
			return generate_fast_filename(return_full=True)
		else:
			return generate_gdb_filename(return_full=True)
	elif not filename:
		log.warning("No filename to check provided, but create_filename is False")
		return False

	if os.path.isabs(filename):
		rel_path = filename
		filename = os.path.abspath(filename)
		log.warning("Transforming relative path %s to absolute path %s" % (rel_path, filename))

	if check_exists and arcpy.Exists(filename):
		log.warning("Filename cannot already exist - found in check_spatial_filename")
		return False

	return filename


def get_spatial_reference(dataset=None):
	if not dataset:
		raise ValueError("No dataset provided to get spatial reference")

	desc = arcpy.Describe(dataset)

	sr = desc.spatialReference
	del desc

	return sr


def fast_dissolve(features, raise_error=True, base_name="dissolved"):
	out_name = generate_gdb_filename(base_name)
	try:
		arcpy.Dissolve_management(features, out_name)
	except:
		if raise_error is False:
			log.warning("Couldn't dissolve. Returning non-dissolved layer")
			return features
		else:
			raise
	return out_name


def write_column_by_key(layer, layer_field, layer_key, results_dict):
	"""
		Writes a column to a layer (doesn't create the field) using a key in the layer to match against a results dictionary-

	:param str layer: The layer to modify
	:param str layer_field: The field in the layer that should be changed
	:param str layer_key: The key field in the layer that will be used for lookups in the results
	:param dict results_dict: The dictionary that the key field will be used to look up results in
	"""

	# for every row
	arc_curs = arcpy.UpdateCursor(layer)
	for row in arc_curs:
		cur_key = row.getValue(layer_key)

		if not cur_key in results_dict:  # skip it if it's not there
			continue

		row.setValue(layer_field, results_dict[cur_key])
		arc_curs.updateRow(row)