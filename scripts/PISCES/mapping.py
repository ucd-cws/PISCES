from __future__ import print_function

__author__ = 'nrsantos'

import shutil
import os
import time
import string
import traceback
import sys
import subprocess  # for when we zip up shapefiles into one
import csv
import re
import copy

import arcpy
import pyodbc

import local_vars
import funcs
import log
import callbacks
import orm_models
import config
import metadata

mapping_session = orm_models.new_session()  # creating this here isn't good practice. Should be factored out to behave like db_cursor and be passed in


class fish_map:  # an individual map for a given fish. Each fish can have multiple maps, depending on the queries
	def __init__(self, map_title=None, short_name=None, query_set=None, query_set_name=None, base_mxd=None, base_ddp_mxd=None, callback=None, callback_args=None, name_formula=None):
		self.map_layers = []  # array of map_layer class objects
		self.map_title = map_title
		self.short_name = short_name

		self.query_set = query_set  # the set in the database that defines this map
		self.query_set_name = query_set_name
		self.base_mxd = base_mxd
		self.base_ddp_mxd = base_ddp_mxd

		self.callback = callback
		self.callback_args = callback_args

		self.exported_png = None  # will be set if a png is exported so we can find the path afterward
		self.mxd_path = None  # the exported mxd file path

		self.name_formula = name_formula

		self.has_bind = False

	def setup(self, queries, title=None, short_name=None, query_set=None, set_name=None, mxd=None, ddp_mxd=None, callback=None, callback_args=None, fish=None, name_formula=None):
		"""
			Used to load the major class items later - __init__ contains some of the critical items, but most of it is set here. When provided custom_query object, sets up a map with the
			appropriate map_layer objects and custom queries
		:param queries: a list (or other iterable) of custom_query objects
		:param title: The title for the map. Accepts :ref:`parameter placeholders<map-variables>`.
		:param short_name:
		:param query_set:
		:param set_name:
		:param mxd:
		:param ddp_mxd:
		:param callback:
		:param callback_args:
		:param fish:
		:param name_formula:
		:return:
		"""

		self.map_title = title
		self.query_set = query_set
		self.query_set_name = set_name
		self.short_name = short_name
		self.base_mxd = mxd
		self.base_ddp_mxd = ddp_mxd
		self.callback_args = structure_args(callback_args)
		self.callback = callback

		self.name_formula = name_formula

		for query in queries:  # make a layer in this map for each query
			self.map_layers.append(map_layer(query, fish, self))

		if not (self.map_title is None):  # if we actually have a title
			self._process_map_title()  # do this after the layers are added because it will search through the layers for a fish - done this way so that it can be called another time. Calling it with the fish directly from above seems resource inefficient since it requires more code below


	def _load_self(self, db_cursor):


		#TODO: This function looks incomplete - record is left hanging
		l_map_query = "select id, map_title, set_name, short_name, base_mxd, ddp_mxd, iterator, callback, callback_args, name_formula from %s where " % local_vars.maps_table

		if self.query_set:
			l_map_query += " ID=%d" % self.query_set
		elif self.short_name:
			l_map_query += " Short_Name='%s'" % self.short_name
		else:
			raise local_vars.MappingError("Must have either a map ID or a short name in order to load a map object")

		record = db_cursor.execute(l_map_query).fetchone()

	def has_observations_records(self):
		"""
			returns True if at least one of the layers has its observations records
		:return:
		"""
		for layer in self.map_layers:
			if layer.has_observations:
				return True

		return False

	def _process_map_title(self):  # map title should also support {mxd}, which then looks at the mxd, gets the title from there, and runs it through here as well, in case the mxd has a {FISH} block
		"""
			Obsolete. The replace_variables code does this and more
		:return:
		"""
		return  # TODO: Remove this return and fix the below code

		# self.map_title = self.map_title.lower() #convert to lowercase so our check is easier
		if "{Species}" in self.map_title or "{Bind}" in self.map_title:  # if we have this operator
			for layer in self.map_layers:  # iterate over the layers until we find a fish
				if not layer.custom_query.bind_var is None:  # if we find one
					if layer.custom_query.bind_var in map_fish:
						self.map_title = self.map_title.replace("{species}", map_fish[layer.custom_query.bind_var])  # replace the {fish} portion of the map with this fish's common name
					self.map_title = self.map_title.replace("{bind}", layer.custom_query.bind_var)  # alternatively, if we just have another bind var and want to replace it
					break
			else:  # if we completed the loop without hitting the break, signaling that we found something
				raise local_vars.MappingError("{species} operator used in map title, but no queries in the map's body are associated with more than one fish. If you wish to put a fish's name in the title, consider hardcoding it")

		self.map_title = string.capwords(self.map_title)  # Put it into title case now
		self.map_title = self.map_title.replace(" Huc", " HUC")
		self.map_title = self.map_title.replace(" Huc12", " HUC12")  # can these lines just be achieved with .upper() ??? Probably not since the rest of the string would be capitalized too - however, this line shouldn't be necessary since it would be covered by the previous

	def populate(self, db_cursor):

		for layer in self.map_layers:  # for every layer that's a part of this map
			if layer.check_layer_cache(db_cursor):  # checks whether we're supposed to continue, and if so, checks if this layer already exists - if it does, skips it
				log.write("Already generated layer", True)
				continue

			if len(layer.zones) == 0:  # if it's still an empty array - which it's possible it's not since layers might be shared
				layer.populate(db_cursor)

	def make_layers(self, zone_layer, db_cursor, cache_layer_flag=True, unique_layer_name=False):
		# cache_layer is a flag that specifies whether or not we want the system to cache the layer - in the case of script tools that return the layers automatically, we don't want to, and they don't have the associated information to be cached
		# unique_layer_name is a flag that specifies whether or not it should give each layer a unique name by copying out the input layer before using it.

		if unique_layer_name is True:  # if we're supposed to keep unique layers in memory, then store the input (this is slow, since we just made it into a feature layer...)
			arcpy.env.overwriteOutput = True
			temp_feature_name = os.path.join(local_vars.workspace, zone_layer)  # get the new location name
			arcpy.CopyFeatures_management(zone_layer, temp_feature_name)  # save it there - we'll retrieve it from here under a new id each time

		initial_zones = zone_layer
		for layer in self.map_layers:
			if layer.check_layer_cache(db_cursor):  # checks whether we're supposed to continue, and if so, checks if this layer already exists - if it does, skips it
				log.write("Already generated layer", True)
				continue

			zone_layer = refresh_zones()
			if unique_layer_name is True:
				local_vars.mapping_unique_feature_layer_id += 1  # increment it so that it will be different
				zone_layer = "layer_%s" % local_vars.mapping_unique_feature_layer_id
				arcpy.MakeFeatureLayer_management(temp_feature_name, zone_layer)  # make ourselves a new feature layer into the id
			else:
				zone_layer = initial_zones  # on every iteration of the loop, start fresh. It's likely better to just not share the name below so that we don't have to do this

			if layer.cache_file is None:  # again, if this isn't a shared layer

				if len(layer.zones) == 0:  # if it's an empty array still
					log.write("No Zones to map - skipping", 1)
					continue  # make no layer - skip to the next layer. Otherwise, all zones will be selected. We'll handle the removal of empty layers later and skipping empty maps

				layer.make(zone_layer, db_cursor)

				if cache_layer_flag is True:
					#using layer.layer_name below because that's what the data will be stored in, not necessarily, in zone_layer
					layer.cache_file = cache_layer(layer.layer_name, layer.custom_query.bind_var, layer.custom_query.id, layer, db_cursor)

			if layer.cache_file is None:  # if we still don't have this defined
				raise local_vars.MappingError("No layer was created - skipping")

	def set_text_variables(self, mxd):
		#set text elements

		for elm in arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT"):
			elm.text = self.replace_variables(elm.text)

	def replace_variables(self, item, fill_spaces=False):
		"""
			The goal of abstracting this out was that it was supposed to be used for query replacement too, but for now
			that would require too much additional re-engineering.
		:param item: string to run replacement operations on
		:return: string with replacement variables replaced
		"""

		# TODO: See above

		bind_var = None
		for layer in self.map_layers:  # iterate over the layers until we find a fish
			if not layer.custom_query.bind_var is None:  # if we find one
				if layer.custom_query.bind_var in local_vars.all_fish:
					bind_var = layer.custom_query.bind_var
					break

		#log.warning("Replacing Start {}".format(item))
		l_time = time.strftime('%Y-%m-%d', time.localtime())

		item = self._replace_single(item, "{Title}", self.map_title)
		if bind_var:
			item = self._replace_single(item, "{Scientific Name}", local_vars.all_fish[bind_var].sci_name)
			item = self._replace_single(item, "{Common Name}", local_vars.all_fish[bind_var].species)
			item = self._replace_single(item, "{Species}", local_vars.all_fish[bind_var].species)
			item = self._replace_single(item, "{FID}", bind_var)
			item = self._replace_single(item, "{Bind}", bind_var)
		item = self._replace_single(item, "{Date}", l_time)
		item = self._replace_single(item, "{Version}", local_vars.version)
		item = self._replace_single(item, "{Sources}", self.get_data_sources_string())
		item = self._replace_single(item, "{hq_collections}", local_vars.hq_collections)

		if fill_spaces:
			item = item.replace(" ", "_")

		#log.warning("Replacing End {}".format(item))
		return item

	def get_data_sources_string(self):
		"""
			If the map document has records (configured via a metadata plugin, return a string of the data sources
		:return: str: Data sources for the map
		"""
		if not local_vars.config_metadata or not self.has_observations_records():
			return ""

		data_sources = {}
		for layer in self.map_layers:
			for observation in layer.observations:
				try:
					if observation.set and observation.set.name:
						data_sources[observation.set.name] = 1
				except:
					log.warning("Unable to add sources for observations - traceback: %s" % traceback.format_exc(3))

		output_str = ""
		for data_source in data_sources.keys():
			output_str += "{0:s};".format(str(data_source))

		return output_str[:-1]  # chop off the final semicolon

	def _replace_single(self, text_string, marker, value):
		"""

		:param text_string: The text string to search for a replacement variable (marker)
		:param marker: The text replacement string (ie, {Scientific Name})
		:param value: the value to replace it with if found
		:return:
		"""

		if text_string and marker in text_string:
			if value is not None and value != "":
				return text_string.replace(marker, value)
			else:
				return text_string.replace(marker, " ")  # replace it with empty text in the case that we have no value
		else:
			return text_string

	def generate(self, ddp=False):  # generates the map once it is set up
		log.write("\nGenerating Map for set %s - Map title %s" % (self.query_set_name, self.map_title), 1)

		mxd = self.choose_mxd(ddp)

		if self.has_contents() is False:  # if this map has no contents
			log.write("Map has no contents", 1)
			return  # then don't bother continuing - we don't care about it

		# sort layers by rank
		if len(self.map_layers) > 1:  # if we have multiple layers, make sure they are sorted
			self.map_layers = sorted(self.map_layers, key=lambda map_layer: map_layer.custom_query.rank, reverse=True)  # we want it reversed because it's a stack so we want to place #4 below #3, etc

		# get the data frame
		dataFrame = arcpy.mapping.ListDataFrames(mxd)[0]  # TODO: WARNING - this won't handle MXDs with multiple data frames - we can fix this by having it check all data frames for the first one with the reference layer in it. That way we could support inset maps, etc

		#find the reference layer
		r_layer = self.find_reference_layer(mxd)  # searches to find the blank layer. We'll use it first, then add more

		generic_layer_num = 0

		extent_object = None  # set it to a blank for now

		#add the layers to the map
		for layer in self.map_layers:

			if layer.cache_file is None:  # if this layer has no data, skip it
				log.write("No data - skipping layer (id: {0:s})".format(str(layer.custom_query.id)), 1)
				continue

			if layer.custom_query.layer_file is None or layer.custom_query.layer_file == "default":  # if we don't have a custom layer file specified
				if generic_layer_num < len(local_vars.layer_files):  # then iterate through the generic ones we have for as long as we have them
					layer.custom_query.layer_file = os.path.join(local_vars.internal_workspace, "mxds", "base", local_vars.layer_files[generic_layer_num])
					generic_layer_num += 1
				else:  # if we don't have any more default layers, but we need one, skip the layer and log that
					log.write("No layer file specified and no default layers to use for layer in map %s - skipping" % (self.map_title), 1)
					continue
			try:
				l_layer = arcpy.mapping.Layer(layer.custom_query.layer_file)  # make the layer into an accessible file
			except:
				raise local_vars.MappingError("couldn't load layer file!")

			l_layer.name = layer.custom_query.layer_name

			# set the data source
			file_only = os.path.split(layer.cache_file)
			file_only = file_only[-1]
			try:
				l_layer.replaceDataSource(local_vars.layer_cache, "FILEGDB_WORKSPACE", file_only)
			except:
				raise local_vars.MappingError("Unable to set data source on map layer")

			# track the extents so that we can set it easily later without re-iterating over these
			if extent_object is None:
				extent_object = l_layer.getExtent() # start with the extent of the first layer
			else:
				self.track_extent(extent_object, l_layer)

			#insert the data
			arcpy.mapping.InsertLayer(dataFrame, r_layer, l_layer, "AFTER")

			layer.composed_layer = l_layer  # we might want to use it later for an export - it will be cleared

		arcpy.mapping.RemoveLayer(dataFrame, r_layer)  # we don't actually want that in there - it's just a marker

		# Set map document name
		if self.name_formula:  # if we have a name formula, use this, otherwise, we'll leave it like before where it just uses the most recent layer
			file_only = self.replace_variables(self.name_formula, fill_spaces=True)

		try:
			self.set_text_variables(mxd)
		except:  # nonfatal for the map
			if local_vars.debug:
				raise
			log.error("Unable to set text strings in map! You'll need to do that manually - see mapping.py line 267")

		#set extent
		dataFrame.extent = extent_object
		dataFrame.scale *= config.extent_scale_factor  # adds a nice bit of space around the edges

		if not self.has_name_formulas() and local_vars.output_common_name is True:  # if we want to output common names, and the layers don't have name formulas already
			log.write("Swapping common name for FID. Original name = %s" % file_only)
			file_only = replace_fid_with_common(file_only)

		self.export_maps(mxd, file_only, ddp, extent_object, dataFrame)  # extent_object and dataFrame are passed in so we can grab the extent and check it with DDP
		if (local_vars.export_web_layer_kml is True or local_vars.export_web_layer_shp is True or local_vars.export_web_layer_lyr is True) and ddp is False:
			self.export_web_layers()

		self.clear_composed_layers()

	def has_name_formulas(self):
		"""
			We want to know if any of the layers have
		:return:
		"""
		for layer in self.map_layers:
			if layer.custom_query.name_formula:
				return True
		return False

	def clear_composed_layers(self):  # deletes the in-memory composed layers
		for layer in self.map_layers:
			layer.composed_layer = None

	def has_contents(self):

		for layer in self.map_layers:
			if layer.cache_file is not None:
				return True  # one of the layers has a file to pop onto the map! Great - the map has data

		return False  # if iterating over every layer didn't cause us to return, then this map has...nooo data - return false

	def decrement_ref_counts(self):
		for index in range(len(self.map_layers)):  # using this method in order to not copy out the data
			self.map_layers[index].ref_count -= 1

	def export_maps(self, mxd, file_only, ddp, extent_object, data_frame):

		if ddp is True:
			log.write("Exporting Data Driven Pages...This may take some time...", 1)

		# construct filename base
		base_name = ""
		if self.short_name and not self.name_formula:  # if we have a short name, prepend it to the output
			base_name = base_name + self.short_name + "_"
		if ddp is True:
			base_name += "ddp_"
		base_name = base_name + file_only

		# Export the files
		self.mxd_path = os.path.join(local_vars.mxd_output_folder, "%s.mxd" % base_name)

		# Write an MXD so we can mess with this independently
		if local_vars.export_mxd is True:
			log.write("Writing mxd %s" % self.mxd_path, 1)
			try:
				mxd.saveACopy(self.mxd_path)
			except:
				log.error("Unable to save MXD for %s - ArcGIS threw an error" % self.mxd_path)

		if ddp is False: # no ddp export with PNGs at the moment...If this becomes important (hint, it will), then we can do this with a loop
			if local_vars.export_pdf is True:
				# Write out the PDF
				pdf_out = os.path.join(local_vars.map_output_folder, "%s.pdf" % base_name)
				log.write("Saving pdf %s" % pdf_out,1)
				try:
					arcpy.mapping.ExportToPDF(mxd, pdf_out)
				except:
					log.error("Unable to save PDF for %s - ArcGIS threw an error" % pdf_out)
					exc_type, exc_value, exc_traceback = sys.exc_info()
					log.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))

			# Write a PNG - allows for quick
			if local_vars.export_png is True:
				png_out = os.path.join(local_vars.map_output_folder, "%s.png" % base_name)
				log.write("Saving png %s" % png_out, 1)
				try:
					arcpy.mapping.ExportToPNG(mxd, png_out, resolution=300)
					self.exported_png = png_out
				except:
					log.error("Unable to save PNG for %s - ArcGIS threw an error" % png_out)
					exc_type, exc_value, exc_traceback = sys.exc_info()
					log.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))

		else:  # if it's ddp!
			log.write("Saving data driven pdfs and pngs", 1)
			l_out_dir = os.path.join(local_vars.map_output_folder, base_name)
			if not os.path.exists(l_out_dir):
				os.mkdir(l_out_dir)

			for pageNum in range(1, mxd.dataDrivenPages.pageCount + 1):  # shamelessly taken from esri
				mxd.dataDrivenPages.currentPageID = pageNum
				print("%s..." % pageNum)
				if self.layers_visible(extent_object,data_frame) is False:
					log.write("Skipping data driven page %s - no data is visible" % pageNum)
					continue

				if local_vars.export_pdf is True:
					try:
						arcpy.mapping.ExportToPDF(mxd, os.path.join(l_out_dir, base_name + "_" + str(pageNum) + ".pdf"))
					except:
						log.error("Unable to export PDF for %s" % base_name + "_" + str(pageNum) + ".pdf")
						exc_type, exc_value, exc_traceback = sys.exc_info()
						log.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))

				if local_vars.export_png is True:
					try:
						arcpy.mapping.ExportToPNG(mxd, os.path.join(l_out_dir,base_name + "_" + str(pageNum) + ".png"), resolution=150)
					except:
						log.error("Unable to export PNG for %s" % base_name + "_" + str(pageNum) + ".png")
						exc_type, exc_value, exc_traceback = sys.exc_info()
						log.error(repr(traceback.format_exception(exc_type, exc_value, exc_traceback)))

		#TODO - Export a dataframe pdf that's large enough to use in a lot of instances

		print("\n",)  # writing newline in case the last line printed didn't have one

		del mxd  # clean up a bit. We might still have some layers floating around. Arc is a bit ambiguous to that...
		if arcpy.Exists("z_layer"):  # Prevents an obscure bug where a hidden "z_layer" ends up in map documents - clean it up after each map is produced to make sure it's gone
			arcpy.Delete_management("z_layer")

	def export_web_layers(self):

		log.write("Exporting and compressing web layers", True)

		composite = 'NO_COMPOSITE'

		output_folder = local_vars.web_layer_output_folder

		csv_data = {}
		csv_loc = os.path.join(output_folder, "manifest.csv")

		if not os.path.exists(output_folder):  # does our output folder exist?
			os.makedirs(output_folder)  # make all dirs required up to and including the output

		arcpy.env.overwriteOutput = True

		for layer in self.map_layers:

			if layer.cache_file is None:
				continue

			output_name = os.path.split(layer.cache_file)[1]  # just get the filename
			output_path = os.path.join(output_folder, output_name)

			if local_vars.export_web_layer_kml is True:

				kml_out = "%s.kmz" % output_path

				try:
					arcpy.LayerToKML_conversion(layer.composed_layer, kml_out, "1", composite)
					csv_data['kmz_%s' % layer.custom_query.id] = "%s.kmz" % output_name
				except:
					if local_vars.debug:
						raise
					raise local_vars.MappingError("Unable to create KML %s" % kml_out)

			if local_vars.export_web_layer_lyr is True:

				lyr_package_out = "{0:s}.lyr".format(str(output_path))

				try:
					layer.composed_layer.saveACopy(lyr_package_out, "10.1")
					csv_data['lyr_%s' % layer.custom_query.id] = "{0:s}.lyr".format(str(output_name))
				except:
					if local_vars.debug:
						raise
					raise local_vars.MappingError("Unable to create layer package %s" % lyr_package_out)

		l_bind = self.map_layers[0].custom_query.bind_var

		if l_bind is not None:  # if we have a bind variable
			f_name = "%s_%s.zip" % (self.short_name, l_bind)
			all_zip = os.path.join(output_folder, f_name)

			csv_data['fid'] = l_bind  # set the value for the csv writer

			try:
				if arcpy.Exists(all_zip):
					arcpy.Delete_management(all_zip)

				zipped = subprocess.call([local_vars.seven_zip, "a", all_zip, local_vars.data_license], stdout=open(os.devnull, 'w'))  # add the license to the full zip
			except:
				raise local_vars.MappingError("Unable to zip up export layers for %s" % all_zip)

			csv_data['all_zip'] = f_name

			if local_vars.export_png:
				try:
					zipped = subprocess.call([local_vars.seven_zip, "a", all_zip, self.exported_png], stdout=open(os.devnull, 'w'))  # add the license to the full zip
					send_png_file = "%s_%s.png" % (self.short_name, l_bind)
					send_png = os.path.join(output_folder, send_png_file)

					shutil.copy2(self.exported_png, send_png)

					csv_data['png_map'] = os.path.split(self.exported_png)[1]
				except:
					raise local_vars.MappingError("Couldn't add png file to export for %s" % l_bind)

		if local_vars.export_web_layer_shp is True:
			for layer in self.map_layers:

				if layer.cache_file is None:
					continue

				output_name = os.path.split(layer.cache_file)[1]  # just get the filename
				shp_name = os.path.join(output_folder, output_name)  # doesn't include .shp!! Let's us glob search in the next step

				try:
					arcpy.FeatureClassToShapefile_conversion(os.path.join(local_vars.layer_cache,output_name),output_folder)

					z_only = "%s.zip" % output_name
					zip_name = os.path.join(output_folder, z_only)
					if arcpy.Exists(zip_name):
						arcpy.Delete_management(zip_name)

					zipped = subprocess.call([local_vars.seven_zip,"a",zip_name,"%s*" % shp_name,"-x!*.zip","-x!*.kml"],stdout=open(os.devnull, 'w')) # add the shape-related data to the zip, exclude filenames with .zip in them already
					zipped = subprocess.call([local_vars.seven_zip,"a",zip_name,local_vars.data_license],stdout=open(os.devnull, 'w'))

					csv_data["shp_%s" % layer.custom_query.id] = z_only

					# calls 7za.exe in the utils folder with the command to add files to {shpname}.zip and then adds all files associated with the shape with an OS glob of {shpname}*
				except:
					raise local_vars.MappingError("Unable to export .shp for %s or zip data" % shp_name)

				if not (l_bind is None):
					# if we have a bind variable # defined above this loop
					zipped_all = subprocess.call([local_vars.seven_zip, "a", all_zip, os.path.join(output_folder, "*%s*" % l_bind), "-x!*.zip"], stdout=open(os.devnull, 'w')) # similar to the above call, except adds all the shapes with this bind variable to one zip - exclude all zips in the folder with a matching name

				if zipped == 0 and zipped_all == 0:  # if they both returned exit code 0 then we can delete the shape!
					arcpy.Delete_management(os.path.join(output_folder, "%s.shp" % output_name))
				else:
					log.error("Unable to zip shapefile %s.shp" % output_name)

		# write the records to the csv
		if local_vars.web_layer_csv_file is None:
			local_vars.web_layer_csv_file = open(csv_loc, 'wb')
		try:
			write_csv_row(writer=local_vars.web_layer_csv_writer, file=local_vars.web_layer_csv_file, data=csv_data)
		except ValueError:  # ValueError would happen if we don't have the correct headers for web export
			log.warning("Couldn't insert record into manifest for web output layers - the layers exported properly though. Non-critical unless you plan to use the manifest to aid upload to another server")

	def layers_visible(self, check_extent, data_frame):  # this actually doesn't guarantee that it's visible - in the case of a feature with two points at the far corners of a bounding box (or features with that distribution. you can be at a spot inside the theoretical bounding box without data. Los Angeles NF could frequently be in this situation.

		# First, the simple check. Does the layer's endpoints fall in the extent
		if funcs.is_between(check_extent.XMin, data_frame.extent.XMin, data_frame.extent.XMax) or funcs.is_between(check_extent.XMax, data_frame.extent.XMin, data_frame.extent.XMax) or (funcs.is_between(data_frame.extent.XMin,check_extent.XMin,check_extent.XMax) and funcs.is_between(data_frame.extent.XMax,check_extent.XMin,check_extent.XMax)):
			# if either of the X values of the check extent object are between the x values of the data frame OR if the data frame is encapsulated in the feature extent
			# and then... check the same for the y values
			if funcs.is_between(check_extent.YMin, data_frame.extent.YMin, data_frame.extent.YMax) or funcs.is_between(check_extent.YMax, data_frame.extent.YMin, data_frame.extent.YMax) or (funcs.is_between(data_frame.extent.YMin,check_extent.YMin,check_extent.YMax) and funcs.is_between(data_frame.extent.YMax,check_extent.YMin,check_extent.YMax)):
				return True

		# Still not done - now we need to see if, possibly, the layer's endpoints are wrapped around the extents. Essentially, is the extent inside the layer.

		return False  # if we get here, then the layers aren't visible in the data frame

	def track_extent(self, extent_object, layer):

		l_properties = layer.getExtent()

		# each of these essentially says that if this layer is further out to one direction than the current setting, change the setting
		if l_properties.XMin < extent_object.XMin:
			extent_object.XMin = l_properties.XMin
		if l_properties.YMin < extent_object.YMin:
			extent_object.YMin = l_properties.YMin
		if l_properties.XMax > extent_object.XMax:
			extent_object.XMax = l_properties.XMax
		if l_properties.YMax > extent_object.YMax:
			extent_object.YMax = l_properties.YMax

		log.write(
			"Extent Changed.\nXMin: {}, XMax: {}\nYMin: {}, YMax: {}".format(*[getattr(extent_object, a) for a in ("XMin", "XMax", "YMin", "YMax")]),
			True
		)

		return

	def find_reference_layer(self, mxd):
		for lyr in arcpy.mapping.ListLayers(mxd): #@UndefinedVariable
			if lyr.isFeatureLayer:
				if lyr.datasetName == "blank_feature":
					return lyr
		else:  # if we still don't have an object, then we gotta skip this one! This would mean a programmatic error
			raise local_vars.MappingError("Couldn't find placeholder/reference layer in template map document - this layer is necessary so that PISCES can insert new layers. Please make sure you have a layer in your map document pointing to blank_feature in the PISCES layer cache (which doesn't, itself, need to exist once you are done setting the reference layer). You can copy the layer out of one of the other templates into your template if you like.")

	def choose_mxd(self, ddp):
		if ddp is False: # if it's a normal map this time
			if self.base_mxd == "default" or self.base_mxd == None: # set the mxd - if a custom mxd wasn't specified, use the default
				self.base_mxd = local_vars.mxd_source
			else:
				self.base_mxd = os.path.join(local_vars.internal_workspace,"mxds","base",self.base_mxd)
			return arcpy.mapping.MapDocument(self.base_mxd)  # open the mxd  @UndefinedVariable
		else:  # otherwise, use the DDP map
			if self.base_ddp_mxd == "ddp_default" or self.base_ddp_mxd is None:  # is the map name already something else? If not, use the default
				self.base_ddp_mxd = local_vars.mxd_ddp_source
			else:
				self.base_ddp_mxd = os.path.join(local_vars.internal_workspace, "mxds", "base", self.base_ddp_mxd)
			return arcpy.mapping.MapDocument(self.base_ddp_mxd)

	def get_custom_queries(self, db_conn):

		log.write("Getting custom queries for map set %s" % self.query_set_name)

		db_cursor = db_conn.cursor()

		l_sql_query = "select mq.custom_query, mq.query_rank, mq.id, mq.layer_file, mq.callback_function, mq.callback_args, mq.layer_name, mq.metadata_plugin, mq.metadata_args, mq.name_formula from map_queries as mq where mq.query_set = ?"

		db_cursor.execute(l_sql_query, self.query_set)
		l_queries = db_cursor.fetchall()

		if not len(l_queries) > 0:
			raise local_vars.MappingError("No queries for query set %s" % self.query_set)

		query_objects = []
		for item in l_queries:
			t_query = custom_query(item.custom_query, item.query_rank, item.id, item.layer_file, item.callback_function, item.callback_args, item.layer_name, item.metadata_plugin, item.metadata_args, item.name_formula)
			query_objects.append(t_query)

		db_cursor.close()
		return query_objects


class map_layer:
	def __init__(self, query=None, bind_v=None, parent=None, text_query=None):
		self.zones = []  # the HUCs returned from the database for this layer
		self.observations = []  # will hold the observation ORM objects returned if the query uses metadata methods! Cool!
		self.aux_attrs = []  # used in case each zone has a particular set of attributes to be used in post processing. The callback needs to know already the order it comes in though
		self.cache_file = None  # the location of the cache file
		self.symbology_lyr = None
		self.layer_name = None  # the name of the layer in memory
		self.short_name = None  # populated by the short name column in the DB TODO: Not currently used. Needs to be first populated, and then used more for layer generation

		self.name_formula = None

		self.composed_layer = None  # stores the location of the layer created from this data and the layer file - we'll use it if we output layers to kml or shp

		if not text_query:  # text_query assumes another loading pattern, not database oriented
			self.parent_map = parent
			self.ref_count = 0  # a count of the number of references to this layer - if it goes back to zero, we'll nuke it after exporting.
			# CUSTOM QUERY
			self.custom_query = copy.copy(query)  # do it this way so we make a COPY of the query
		else:
			self.custom_query = custom_query(text_query, 1, None, None, None, None, "pisces_query")

		self.custom_query.bind_var = bind_v
		if "?" in self.custom_query.query_string:  # if this query string requires a bind variable
			if not bind_v is None:  # Make sure we have one
				self.custom_query.bind_var = bind_v
			else:  # but we don't have one! EXCEPTION
				raise local_vars.MappingError("Query string with bind variable called with no fish to bind - query string: %s, fish %s" % (query.query_string, bind_v))
		else:  # if it doesn't require a bind variable - essentially,  it's a generic query
			self = check_common_layers(self)  # passes itself in and probably gets itself back out. It's possible it will get out a layer that already exists in another map so that we save some work. It's possible the cost of checking this isn't worth it, but in most cases the array of common layers is unlikely to be large

	def _load(self, query_id, db_conn):

		"""

		:param query_id:
		:param db_conn:
		:return: :raise local_vars.MappingError:
		"""
		db_cursor = db_conn.cursor()

		l_sql_query = "select mq.Custom_Query, mq.Query_Rank, mq.ID, mq.Layer_File, mq.Callback_Function, mq.Callback_Args, mq.Layer_Name, mq.metadata_plugin, mq.metadata_args, mq.name_formula from Map_Queries as mq where ID=?"

		db_cursor.execute(l_sql_query, query_id)
		item = db_cursor.fetchone()

		if not item:
			raise local_vars.MappingError("No queries for query_id %s" % query_id)

		rquery = custom_query(item.Custom_Query, item.Query_Rank, item.ID, item.Layer_File, item.Callback_Function, item.Callback_Args, item.Layer_Name, item.metadata_plugin, item.metadata_args, item.name_formula)
		db_cursor.close()
		return rquery

	def has_observations(self):
		if len(self.observations) > 0:
			return True
		else:
			return False

	def populate(self, db_cursor):
		global mapping_session
		session = mapping_session

		try:
			self.custom_query.process_vars()
			log.write("Processing Custom Query: %s with bind variable %s" % (self.custom_query.query_string, self.custom_query.bind_var), 1)
			if self.custom_query.bind_var is None:  # if we don't have a bind var, don't provide one!
				l_results = db_cursor.execute(self.custom_query.query_string)  # execute its query
			else:
				self.custom_query.process_bind()  # for queries where the bind variable is needed multiple times, this replaces {bind} with the variable
				l_results = db_cursor.execute(self.custom_query.query_string, self.custom_query.bind_var)  # execute its query


			log.write("Getting observation records", 1)
			try:
				for result in l_results:
					self.zones.append(result.zone_id)
					if self.custom_query.metadata_plugin and local_vars.config_metadata:
						self.observations.append(session.query(orm_models.Observation).filter_by(pkey=result.objectid).first())  # note, this is backwards and slow - we should consider another way - this results in execution of a query for every observation record hit (as high as 50k!!)
					self.aux_attrs.append(result)  # full array, including Zone_ID is appended for access later. If the callback wants to access other information without a new query, this can handle that
				self.zones = list(set(self.zones))  # dedupe our zones list for faster selections
			except AttributeError:

				if local_vars.debug:
					raise
				raise local_vars.MappingError("Invalid query for map - queries must retrieve HUC_12 ids AS zone_id or else they will be invalid. See the full documentation for more details. (example query: 'select HUC_12 as zone_id from HUC12FullState'")
		except pyodbc.Error as e:
			log.error("Error in layer population. Exception string: %s\nPyodbc reported %s." % (str(e), traceback.format_exc()))
			raise

	def make(self, zone_layer=None, db_cursor=None):
		"""
			Does the actual work of generating the spatial layer from the query. We should have already executed the query to retrieve the zones, but not retrieved the zones as a layer.
			This function batches a selection query to retrieve HUC12s from the zones layer, then export it out after optionally calling a callback.
			With the current query layer functionality in ArcMap, we could theoretically do a join (select from HUC12FullState, Observations where Observations.Zone_ID = HUC12FullState.HUC_12 and ...) instead of multiple selections, which would be much faster, but wouldn't give us preexported layers. Some drawbacks and needs testing
		:param zone_layer:
		:param db_cursor:
		:return:
		"""
		if len(self.zones) == 0:
			return None

		# if we don't have a zone_layer, then make one from the default
		if not zone_layer:
			zone_layer = "z_layer"
			arcpy.MakeFeatureLayer_management(local_vars.HUCS, zone_layer)

		try:  # NOTE: The following code was written before PISCES used Spatialite, so this was necessary to select HUCs back. In a future version, we could probably change this to create a query layer directly instead, but in its current form, it's so fast that it may not be worth it.
			log.write("Selecting Zones")
			selection_type = "NEW_SELECTION"  # start a new selection, then add to
			try:
				arcpy.SelectLayerByAttribute_management(zone_layer, "CLEAR_SELECTION")  # we need to do this because if we don't then two layers in a row with the same number of records will result in the second (or third, etc) being skipped because the following line will return the selected number
				if not (int(len(self.zones)) == int(arcpy.GetCount_management(zone_layer).getOutput(0))): # if they are not the same - ie, we are asking to select everything - then skip the selection - this shortcut won't work if we change to allowing portions of a HUC string to select the HUCs
					log.write("Selecting %s zones" % len(self.zones), 1)
					zone_expression = "%s%s%s IN (" % (local_vars.delim_open, local_vars.huc_field, local_vars.delim_close)  # the where clause - we want to initialize it to blank
					num_hucs = len(self.zones)
					for index in range(num_hucs):  # we have to do this in a loop because building one query to make Arc do it for us produces an error
						zone_expression += "'%s'," % self.zones[index]  # brackets are required by Arc for Personal Geodatabases (that's us!)
						if (index != 0 or num_hucs == 1) and (index % 500 == 0 or index == len(self.zones) - 1):  # Chunking: every 30th HUC, we run the selection, OR when we've reached the last one. we're trying to chunk the expression. Arc won't take a big long one, but selecting 1 by 1 is slow
							# first segment of the above statement says that we don't want this to only select 1 huc in the first selection because 0%500 == 0, so we don't run this when index is zero unless we only have one huc
							zone_expression = zone_expression[:-1] + ")"
							#zone_expression = zone_expression[:-4]  # chop off the trailing " OR "
							if local_vars.debug:
								log.debug("Debug: Selection Expression [%s]" % zone_expression)
							arcpy.SelectLayerByAttribute_management(zone_layer, selection_type, zone_expression)
							selection_type = "ADD_TO_SELECTION"  # set it so that selections accumulate
							zone_expression = "%s%s%s IN (" % (local_vars.delim_open, local_vars.huc_field, local_vars.delim_close)  # the where clause - we want to initialize it to blank
			except:
				log.error(traceback.format_exc())
				raise local_vars.MappingError("Unable to select features for new layer - check the sql query associated with query id %s" % self.custom_query.id)

			try:  # CALLBACKS - allow custom processing to occur after the layer has been pulled
				if self.custom_query.callback is not None and self.custom_query.callback != '':  # if we have a callback
					l_callback = getattr(callbacks, self.custom_query.callback)  # get the callback function's object
					zone_layer = l_callback(zone_layer, db_cursor, self.custom_query.callback_args, self)  # call it with the layer as the parameter. It's possible that it may copy it out and return a new zone_layer
			except:
				if local_vars.debug:
					raise
				else:
					raise local_vars.MappingError("Failed in callback for layer with query id %s" % self.custom_query.id)

			try:  # METADATA
				if local_vars.config_metadata and self.custom_query.metadata_plugin is not None and self.custom_query.metadata_plugin != '':  # if we need to run metadata
					metadata_plugin = getattr(metadata, self.custom_query.metadata_plugin)  # get the metadata module
					metadata_function = getattr(metadata_plugin, "attach")  # get the code that runs the metadata

					if self.custom_query.metadata_args:
						kwargs = metadata.format_args(self.custom_query.metadata_args)
					else:
						kwargs = {}

					zone_layer = metadata_function(self, zone_layer, **kwargs)
			except NameError:
				if local_vars.debug:
					raise
				else:
					raise local_vars.MappingError("Unable to find metadata plugin named %s - check that it is installed and present" % self.custom_query.metadata_plugin)
			except:
				if local_vars.debug:
					raise
				else:
					raise local_vars.MappingError("Unable to attach metadata to layer with query id %s" % self.custom_query.id)

			self.layer_name = zone_layer  # store it for later - we'll cache based on this name

		except local_vars.MappingError:
			if local_vars.debug:
				raise
			raise
		except:
			if local_vars.debug: raise
			raise local_vars.MappingError("Unable to make and save the new layer")

		return zone_layer

	def check_layer_cache(self, db_cursor, force_check=False):
		"""
			Given a cursor, checks to see if there's already a layer stored in the cache for this map_layer. If one is found, it sets self.cache_file to the value and returns True. Otherwise, returns False
		:param db_cursor: a cursor to access the database
		:param force_check: boolean: By default, this method only checks when the --continue flag is set on the command line, or when local_vars.continue_mapping is true. If force_check is True, this method checks for a cached layer regardless
		:return boolean: returns True when a layer is found and False when not
		"""

		if local_vars.continue_mapping or force_check:
			if self.cache_file:
				return True

			cached_layer = cache_layer(None, self.custom_query.bind_var, self.custom_query.id, self, db_cursor, force_search=local_vars.force_cache_search)
			if cached_layer:
				log.write("Found cached layer", True)
				self.cache_file = cached_layer
				return True
		return False

class custom_query:
	def __init__(self, query=None, query_rank=None, query_id=None, template_layer_file=None, callback=None, callback_arguments=None, layer_name=None, metadata_plugin=None, metadata_args=None, name_formula=None):
		self.query_string = query
		self.rank = query_rank
		self.id = query_id

		self.bind_var = None  # if we have a fish to use as a bind variable (multi-fish queries will have one), it's stored here
		self.specified_bind = None  # when a bind var is specified as a group, this holds the group name so that you can access that value as well as the instance value determined from that group. Essentially, it stores the value you actually provided for the bind variable, and not PISCES' interpreted or expanded value for that.

		self.layer_name = layer_name
		self.layer_file = template_layer_file  # this is stored here because it's associated with the queries in the db before making the layers
		self.callback = callback  # optional callback to be processed after results of this query get returned
		self.callback_args = structure_args(callback_arguments)

		self.metadata_plugin = metadata_plugin
		self.metadata_args = metadata_args
		self.name_formula = name_formula

		# custom queries allow us to generate maps with custom layers that will always be processed for a given fish
		# the default maps are stores as custom queries so that only one logic set is needed to make all of the maps
		# default maps are stored with FID ALL in order to be processed for all fish with data that are specified by this function

	def process_bind(self):  # in instances where we need multiple bind variables, the {bind} entity lets us add them in.
		if "{bind}" in self.query_string:
			self.query_string = self.query_string.replace("{bind}", str(self.bind_var))

		if self.callback_args is not None:
			for i in range(len(self.callback_args)):  # TODO: this is a stupid hack and should be replaced
				self.callback_args[i] = self.callback_args[i].replace("{bind}", str(self.bind_var))
				self.callback_args[i] = self.callback_args[i].replace("{hq_collections}", local_vars.hq_collections)

	def process_vars(self):
		if "{zones_table}" in self.query_string:
			self.query_string = self.query_string.replace("{zones_table}", local_vars.zones_table)
		if "{hq_collections}" in self.query_string:
			self.query_string = self.query_string.replace("{hq_collections}", local_vars.hq_collections)

		self._replace_arbitrary_variables()

	def _replace_arbitrary_variables(self):
		"""
			Finds anything in a query wrapped in {} and then looks up that item in local_vars, replacing it
		:return: None
		"""
		print("Looking for other variables in query")
		matches = re.findall("{([\w_]+?)}", self.query_string)
		for match in matches:
			print("Found {}".format(match))
			replacement_value = getattr(local_vars, match)
			self.query_string = self.query_string.replace("{{{}}}".format(match), replacement_value)  # {{ is a literal brace, so we need three of each to have the literal and the format string




def begin(fish_subset, return_maps=False):

	log.write("\nBeginning Mapping", 1)

	mapping_cursor, mapping_conn = funcs.db_connect(local_vars.maindb)  # open the db for the remainder of this function

	log.write("Retrieving mapping data from database...", 1)

	# handle fish specified or get fish ids if "all"
	global map_fish  # use the global fish structure
	map_fish = get_fish_to_map(fish_subset, mapping_cursor)  # takes the argument and returns a dictionary with codes set as the index - receives the cursor in case fish subset is all, in which case it retrieves all fish that have an observation
	del fish_subset

	global all_maps
	all_maps = initialize_maps(mapping_conn)

	zone_layer = refresh_zones()  # if this layer doesn't exist, it makes it. Some of these functions modify the layer
	if local_vars.usecache == 0:  # if we're not supposed to use the cache only
		for i in range(len(all_maps)):
			try:

				all_maps[i].populate(mapping_cursor)
				all_maps[i].make_layers(zone_layer, mapping_cursor)

				#if we've made it to the end of the processing here, we can commit any changes we've made to the layer cache, etc
				try:
					mapping_conn.commit()
				except pyodbc.Error:
					log.error("Failed to commit changes to database - not critical at this moment, but you should be aware that layer cache changes were not saved")
					# TODO: Fix this - sqlite3 doesn't seem to like the concurrent connection thing of using pyodbc and sqlalchemy at the same time.

			except local_vars.MappingError as e:
				#if local_vars.debug == 1: raise
				log.error("Encountered error in mapping id #%d - reported \"%s\". Skipping" % (all_maps[i].query_set,e))
				all_maps[i] = None  # zero out the map
				continue
	else:  # we're supposed to use the cache
		for l_map in all_maps:
			for layer in l_map.map_layers:  # then for every layer in every map
					layer.cache_file = cache_layer(None, layer.custom_query.bind_var, layer.custom_query.id, layer, mapping_cursor, force_search=local_vars.force_cache_search)  # get the quick cache file name for mapping

	log.write("Generating maps", 1)
	for index in range(len(all_maps)):  # Doing this as a second loop so that we have some certainty in this - if we reach this point, layer generation and caching is complete
		if all_maps[index] is not None:  # if it wasn't deleted due to error
			try:
				all_maps[index].generate()

				if all_maps[index].base_ddp_mxd is not None and local_vars.export_ddp is True:  # if we also need to do one with Data Driven Pages...
					all_maps[index].generate(ddp=True)
			except:
				if local_vars.debug:
					raise
				log.error("Encountered error in generating map (id #%d). Skipping" % all_maps[index].query_set)
				all_maps[index] = None  # zero out the map
				continue

			all_maps[index].decrement_ref_counts()
			if not return_maps:
				all_maps[index] = None # see if we can't fix the memory leak in arcgis - we don't need this anymore - maybe deleting it will help, but we don't wan to delete the actual array element (or else we end up out of range later)
			clean_common_layers()

	funcs.db_close(mapping_cursor, mapping_conn)
	wrapup()

	log.write("Mapping Complete", 1)

	return all_maps  # return the map objects in case the caller wants any info

def wrapup():
	if local_vars.web_layer_csv_file:
		local_vars.web_layer_csv_file.close()


def initialize_maps(db_conn, set_ids=()):

	log.write("Initializing map structures")

	db_cursor = db_conn.cursor()
	l_maps = []  # local map array

	l_query_sets = get_enabled_query_sets(db_cursor, set_ids)  # returns a database results object to process below

	for result in l_query_sets:

		query_fish = get_multi_fish_query(result.id, db_conn, result.iterator)  # return the bind values to run this query set for

		if (query_fish is not None) and len(query_fish) > 0:  # if this is supposed to be done for multiple fish - the second check might be unnecessary
			# select fish from fish table, check against our fish list that was passed in, and set up objects
			for fish in query_fish:
				try:
					l_map = fish_map()  # init a new map
					l_map.query_set = result.id  # set the set ID immediately for query retrieval
					try:
						l_queries = l_map.get_custom_queries(db_conn)  # returns all of the queries to be used in this kind of map
					except local_vars.MappingError as error:
						log.error("%s - skipping map" % error)
						continue  # skips this map - it won't make it to be appended to the list
					except:
						if local_vars.debug:
							raise
						else:
							log.error("Problem retrieving custom queries - skipping map set %s" % result.short_name)
						continue

					l_map.setup(l_queries, result.map_title, result.short_name, result.id, result.set_name, result.base_mxd, result.ddp_mxd, result.callback, result.callback_args, fish, name_formula=result.name_formula)
					l_map.has_bind = True
				except local_vars.MappingError as e:  # if we have any problems during setup, then we need to skip this map
					log.error("Skipping Query Set %s with bind variable %s - encountered problem during setup - error reported was %s" % (result.id, fish, e))
					continue

				l_maps.append(l_map)
		else:
			try:
				l_map = fish_map()
				l_map.query_set = result.id
				try:
					l_queries = l_map.get_custom_queries(db_conn)  # returns all of the queries to be used in this kind of map
				except local_vars.MappingError as error:
					log.error("%s - skipping map" % error)
					continue  # skips this map - it won't make it to be appended to the list
				except:
					log.error("Problem retrieving custom queries - skipping map set %s" % result.short_name)
					continue

				l_map.setup(l_queries, result.map_title, result.short_name, result.id, result.set_name, result.base_mxd, result.ddp_mxd, result.callback, result.callback_args, name_formula=result.name_formula)
				# set up a single object
			except local_vars.MappingError as e:  # if we have any problems during setup, then we need to skip this map
				log.write("Skipping Query Set %s - encountered problem during setup - error reported was %s" % (result.id, e), 1)
				continue

			l_maps.append(l_map)

	db_cursor.close()

	return l_maps


def get_multi_fish_query(query_set, db_conn, bind_column=None):

	log.write("Determining Taxa to Output", 1)

	db_cursor = db_conn.cursor()

	l_query = "select Bind_Value from Query_Bind where Query_Set_ID = ?"
	db_cursor.execute(l_query, query_set)

	# Check values against fish we were told to process

	query_bind = db_cursor.fetchone()
	if query_bind is None:  # if we don't have a row, then this query stands alone
		return None

	all_groups = []
	g_curs = db_conn.cursor()
	group_retrieve = "select group_name from defs_Species_Groups"
	results = g_curs.execute(group_retrieve)
	for item in results:
		all_groups.append(item.group_name)
	g_curs.close()

	if query_bind.bind_value == "all":  # if this query is supposed to be run for all values
		if bind_column is None or bind_column.lower() == "species:fid":
			return map_fish.keys()  # set the fish we want to process
		else:
			return get_bind_values(bind_column, db_cursor)  # retrieve the bind values based upon the column
	else:
		query_bind_ids = db_cursor.fetchall()
		query_bind_ids.append(query_bind)  # we need to add it to the end since it wasn't "all" and fetchall() only returns unfetched rows

		query_bind = []

		for item in query_bind_ids:  # this time, it's supposed to be a loop, but we didn't want that if on every iteration
			'''The following check has been removed since we aren't only mapping fish...'''
			#	if map_fish.has_key(item.Bind_Value):
			if (item.bind_value in all_groups) and (bind_column.lower() == "species_groups:fid" or bind_column.lower() == "species_groups" or bind_column.lower() == "fid"):  # we have a group name and we want to use it as a group name
				t_curs = db_conn.cursor()
				group_retrieve = "select distinct observations.species_id, species.common_name from observations, species where observations.species_id = species.fid and observations.species_id in (select fid from species_groups where group_id = (select id from defs_species_groups where group_name = '%s'))" % item.bind_value
				g_results = t_curs.execute(group_retrieve)
				for l_item in g_results:
					query_bind.append(l_item.species_id)
				t_curs.close()
			else:
				query_bind.append(item.bind_value)

	db_cursor.close()
	return query_bind


def get_enabled_query_sets(db_cursor, set_ids):
	l_map_query = "select id, map_title, set_name, short_name, base_mxd, ddp_mxd, iterator, callback, callback_args, name_formula from %s where active=1" % local_vars.maps_table
	if type(set_ids).__name__ == "list" and len(set_ids) > 0:
		for item in set_ids:
			l_map_query += " OR ID = %d" % item

	l_results = db_cursor.execute(l_map_query)

	return l_results


def get_bind_values(bind_column, db_cursor):
	"""

	:param bind_column:
	:param db_cursor:
	:return: :raise local_vars.MappingError:
	"""
	table_col = bind_column.split(":")
	try:
		table = table_col[0]
		col = table_col[1]
	except:
		raise local_vars.MappingError("Unable to select bind values")

	l_string = "select distinct %s from %s" % (col, table)
	results = db_cursor.execute(l_string)

	values = []
	for item in results:
		if item[0] is None or item[0] == "":
			continue
		#log.write("Found bind value %s" % item[0])
		values.append(item[0])

	return values


def get_fish_to_map(fish_subset, db_cursor):  # takes the argument to mapping and determines what fish we are mapping - returns an array of fish ids

	log.write("Determining fish to map")
	map_fish = {}

	if fish_subset == "all":
		map_fish = get_mappable_fish(db_cursor)
	elif type(fish_subset).__name__ == "string" and len(fish_subset) > 0:  # if they provided a valid string of just one fish
		if fish_subset in local_vars.all_fish:  # if it's actually a fish code
			l_fish = fish_subset  # save the value
			fish_subset = []  # make it a list so we can use the following code no matter what
			fish_subset[0] = l_fish
		else:  # it might be a group name
			map_fish = get_mappable_fish(db_cursor, native_only=False, group=fish_subset)
			if len(map_fish.keys()) == 0:  # basically, we're out of options here
				log.error("invalid species key specified to map - ignoring")

	if type(fish_subset).__name__ == "list" and len(fish_subset) > 0:  # if a list of fish was provided and it's not empty
		for fid in fish_subset:
			if fid in local_vars.all_fish:  # if it's just a fish
				l_query = "select common_name from species where fid = ?"
				l_result = db_cursor.execute(l_query, fid)
				map_fish[fid] = l_result[0].common_name  # make the dictionary of fish indexed by FID
			else:  # it might be a group name
				t_map_fish = get_mappable_fish(db_cursor, native_only=False, group=fid)
				map_fish.update(t_map_fish)  # add the new dict to the current one
				if len(t_map_fish.keys()) == 0:
					log.error("invalid species key specified to map - ignoring")

	if len(map_fish) == 0:  # if we still have no fish
		raise local_vars.MappingError("Unable to determine the fish to map! Valid options are \"all\", a group name, an array subset of species ids or a string containing a species id")

	return map_fish


def get_mappable_fish(db_cursor, native_only=False, group=None):  # returns all the fish we have observations for
	#  should also check to only select fish that have new observations. when importing data we should set a flag. That way we know which fish are "up to date" and won't reprocess maps that are unaffected
	"""

	:param db_cursor:
	:param native_only:
	:param group:
	:return:
	"""
	l_items = {}
	l_query = "select distinct observations.species_id, species.common_name from observations, species where observations.species_id = species.fid"
	if native_only is True:
		l_query = "%s and Species.Native = True" % l_query
	if group is not None:
		l_query = "%s and Observations.Species_Id in (select FID from Species_Groups where Group_ID = (select ID from defs_Species_Groups where Group_Name = %s))" % (l_query, group)

	l_results = db_cursor.execute(l_query)
	for fish in l_results:
		l_items[fish.species_id] = fish.common_name

	return l_items


def replace_fid_with_common(replace_string):
	''''a complicated way to make output occur with common name instead of FID - replaces the FID in the string rather than starting with common name earlier. Avoids problems with GDBs'''

	try:
		l_fid_match = re.search("(\w{3}\d{2})", replace_string)
		if l_fid_match and l_fid_match.groups > 1:  # if we have groups
			l_fid = l_fid_match.group(0)
		else:
			log.write("No species to replace with")  # be pretty silent though
			return replace_string
	except:
		if local_vars.debug:
			raise
		return replace_string

	try:
		if l_fid in local_vars.all_fish.keys():  # if we matched an actual species
			replace_string = str(replace_string).replace(l_fid, local_vars.all_fish[l_fid].species)
		replace_string = str(replace_string).replace(" ", "_")  # replace spaces that are now in the name with underscores
	except:
		if local_vars.debug:
			raise
		else:
			return replace_string

	return replace_string  # whatever it is, return it


def check_common_layers(layer):

	for index in range(len(local_vars.common_layers)):  # iterate over all of the common layers
		if layer.custom_query.query_string is local_vars.common_layers[index].custom_query.query_string and \
		layer.custom_query.bind_var == local_vars.common_layers[index].custom_query.bind_var:  #if it's the same query, with the same bind var, and with the same callback - we're using "is" for the query string because that's going to come in once for each query set, but it will exclude query sets that have the same query elsewhere, but maybe with different callbacks since they won't reside in the same query space in memory
		# defunct piece of code now: saving, just in case...	and layer.custom_query.callback == check_layer.custom_query.callback
			local_vars.common_layers[index].ref_count = local_vars.common_layers[index].ref_count + 1
			return local_vars.common_layers[index]  # if we do, give this map that layer

	layer.ref_count = 1  # set a ref_count so that we can nuke shared layers when it hits zero. The software currently crashes after running too long, so we want to manage this
	local_vars.common_layers.append(layer)  # if we haven't returned yet, then this layer is a potential common layer that we haven't processed. Add it so that future layers check here
	return layer


def clean_common_layers():
	l_max = len(local_vars.common_layers)
	index = 0
	while index < l_max:
			if local_vars.common_layers[index].ref_count == 0:
				del local_vars.common_layers[index]  # only deletes this reference, but we'll probably delete the others too
				l_max = len(local_vars.common_layers)  # set it to the new length
				continue  # don't increment - the next layer will now be this index
			index = index + 1


def refresh_zones():

	"""
		Creates a feature layer from the HUC 12s in the database

	:return: str: Name of the feature layer created for mapping :raise local_vars.MappingError:
	"""
	zone_layer = "z_layer"
	try:  # try to make it
		if arcpy.Exists(zone_layer):
			arcpy.Delete_management(zone_layer)
		arcpy.MakeFeatureLayer_management(local_vars.HUCS, zone_layer)  # bring the HUCs in as a layer
	except:  # if we get an exception, we don't care because it will come out as an error later
		raise local_vars.MappingError("Couldn't load zones!")

	return zone_layer


def structure_args(args):  # takes the arguments and makes them into a tuple
	if not type(args).__name__ == "list" and args is not None:
		if "::" in args:  # if it has multiple args
			all_args = string.split(args,"::")
			return all_args  # return the split
		else:
			return args  # return the input
	else: # in the event that these have already been processed
		return args


def write_csv_row(writer=None, fields=('fid','all_zip','kmz_1','kmz_2','kmz_16','kmz_17','kmz_18','kmz_48','lyr_1','lyr_2','lyr_16','lyr_17','lyr_18','lyr_48','shp_1','shp_2','shp_16','shp_17','shp_18','shp_48','png_map'), file = None, data = None):  # TODO: Make this dynamic. It shouldn't be hardcoded what fields get created. That makes it useful only in a handful of cases. We could iterate through the maps and find all the names.

	log.write("writing row to manifest")

	# we already have a writer
	if data is None:
		raise ValueError("data cannot be None")

	if writer is None:  # we don't have a writer - create it

		if file is None:
			raise ValueError("filename cannot be None")

		local_vars.web_layer_csv_writer = csv.DictWriter(file, fields)
		writer = local_vars.web_layer_csv_writer

		writer.writeheader()  # write the row out

	# so just write the data
	writer.writerow(data)


def cache_layer(arc_layer, bind_var, query_id, map_layer_object, db_cursor, force_search=False):  # when called with arc_layer = None, returns full_layer_path immediately after it's generated. This way, we can use one spot to generate cache names, and return what would have been done with a full processing

	log.write("Caching layer", 1)
	#check to see if this is already cached. If it is, remove the old file, save the new file and update the location

	bind_var, full_layer_path, out_layer_name = funcs.generate_layer_name(bind_var, query_id, map_layer_object)

	if arc_layer is None:  # if we don't actually want it to cache it - we just want the name
		if not force_search:  # force_search is for when we have accidentally killed the database (versioning) in between the previous generation and continuing
			log.write("Trying to use cached layer", True)
			query = "select layer_file from layer_cache where query_id = ? and bind_var = ?"
			rows = db_cursor.execute(query, query_id, bind_var)  # add a record for it to the database

			t_row = rows.fetchone()
			if t_row:  # if we actually have a row for this query
				out_layer_name = t_row.layer_file  # use the Layer_File column
			else:
				log.write("No cached layer", True)
				return None	 # otherwise return None

		full_layer_path = os.path.join(local_vars.layer_cache, out_layer_name)  # set the full path to the layer on disk

		if arcpy.Exists(full_layer_path):  # we're looking for the name, but if it doesn't exist, then we don't want it because other things rely on that info
			return full_layer_path
		else:  # return None if we don't have it
			log.write("No cached layer", True)
			return None

	#l_sql = "select Layer_Cache.ID from Layer_Cache where Layer_Cache.Query_ID = ? and Layer_Cache.Bind_Var = ?"
	#l_results = db_cursor.execute(l_sql,) # look to see if we have an existing layer for this query/bind var

	#for result in l_results:
	#	if not result.ID == None: # if there already is a stored result for this query/bind var
	try:
		if arcpy.Exists(full_layer_path):  # if it also exists in the cache area
			arcpy.Delete_management(full_layer_path)  # remove the old feature
		l_sql = "delete from layer_cache where query_id = ? and bind_var = ?"
		db_cursor.execute(l_sql, query_id, bind_var)  # and delete the row
	except:
		raise local_vars.MappingError("Error removing the previous dataset for this query. Skipping this map. Data may have been deleted from the layer cache for query id %s with bind variable %s" % (query_id,bind_var))

	# regardless, we need to save the new data and update the database
	try:
		# TODO: The below needs to detect types and use copy for rasters and copyfeatures for vector. Copy is too unstable to use for vector, I think.
		arcpy.CopyFeatures_management(arc_layer, full_layer_path)  # save the new layer - using Copy because we may get rasters if a callback changes the type
	except:
		raise local_vars.MappingError("Unable to save the selection to the layer cache - unable to proceed with this map. Exception follows: {}".format(traceback.format_exc()))

	try:
		l_sql = "insert into layer_cache (query_id,bind_var,layer_file,last_updated) values (?,?,?,datetime('now'))"
		db_cursor.execute(l_sql, query_id, bind_var, out_layer_name)  # add a record for it to the database
	except:
		raise local_vars.MappingError("Unable to update the Layer_Cache table in the database with the new file information")

	if not arc_layer == "z_layer":  # TODO: This needs to be more robust. hardcoding the name here is bad. Much better to have some other method of determining what to keep and what to remove (this goes back to the problem of keeping the layer in memory in the first place...it's a bit of a kluge
		try:
			arcpy.Delete_management(arc_layer)  # do some cleanup - keeping all of this in memory is probably unwise - we'll read it back in when we need it
		except:
			print("Warning: Unable to delete layer %s from memory. The layer is not being skipped, but memory usage could rapidly increase if you see many of these messages" % arc_layer)

	return full_layer_path


