from __future__ import absolute_import, division, print_function

__author__ = 'nickrsan'

import os
import re

from . import local_vars
from . import config
from . import log

class PISCES_Config:
	"""
		Doesn't store the running config, but allows for containerized reading and writing of the config file. Lightweight - verifies that correct types are used, but not much more.

		This method does a few things backward due to some backward thinking when I started it (don't parse a python file with regex Nick - just load it. Duh). So it's partially re-engineered, but works. Worth maybe paring down at some point.
	"""

	def __init__(self):

		self.replace_string = "{replace}"
		self.patterns = {'username': ('username = "(.+)"', 'username = "{0:s}"'.format(self.replace_string), None, config.username),  # format: match string, replacement string, type for verification if needs enforcing. None means *any*. Final item is the actual attribute to load/current value
				'maindb': ['local_vars.maindb = (r*"*.+?"*)\r', 'local_vars.maindb = r"{0:s}"\r'.format(self.replace_string), None, local_vars.maindb],
				'export_pdf': ('local_vars.export_pdf = (.+?)\s+', 'local_vars.export_pdf = {0:s}\r'.format(self.replace_string), bool,
							   local_vars.export_pdf),
				'export_png': ('local_vars.export_png = (.+?)\s+', 'local_vars.export_png = {0:s}\r'.format(self.replace_string), bool,
							   local_vars.export_png),
				'export_shp': ('local_vars.export_web_layer_shp = (.+?)\s+', 'local_vars.export_web_layer_shp = {0:s}\r'.format(self.replace_string), bool,
							   local_vars.export_web_layer_shp),
				'export_kml': ('local_vars.export_web_layer_kml = (.+?)\s+', 'local_vars.export_web_layer_kml = {0:s}\r'.format(self.replace_string), bool,
							   local_vars.export_web_layer_kml),
				'export_lyr': ('local_vars.export_web_layer_lyr = (.+?)\s+', 'local_vars.export_web_layer_lyr = {0:s}\r'.format(self.replace_string), bool,
							   local_vars.export_web_layer_lyr),
				'export_mxd': ('local_vars.export_mxd = (.+?)\s+', 'local_vars.export_mxd = {0:s}\r'.format(self.replace_string), bool,
							   local_vars.export_mxd),
				'export_ddp': ('local_vars.export_ddp = (.+?)\s+', 'local_vars.export_ddp = {0:s}\r'.format(self.replace_string), bool,
							   local_vars.export_ddp),
				'export_metadata': ('local_vars.config_metadata = (.+?)\s+', 'local_vars.config_metadata = {0:s}\r'.format(self.replace_string), bool,
									local_vars.config_metadata),
				'output_common_name': ('local_vars.output_common_name = (.+?)\s+', 'local_vars.output_common_name = {0:s}\r'.format(self.replace_string), bool,
									   local_vars.output_common_name),
				'debug': ('local_vars.debug = (.+?)\s+', 'local_vars.debug = {0:s}\r\n'.format(self.replace_string), bool, local_vars.debug),
				'map_output_folder': ('local_vars.map_output_folder = (r*"*.+?"*)\r', 'local_vars.map_output_folder = r"{0:s}"\r'.format(self.replace_string), None,
									  local_vars.map_output_folder),
				'mxd_output_folder': ('local_vars.mxd_output_folder = (r*"*.+?"*)\r', 'local_vars.mxd_output_folder = r"{0:s}"\r'.format(self.replace_string), None,
									  local_vars.mxd_output_folder),
				'web_layer_output_folder': ('local_vars.web_layer_output_folder = (r*"*.+?"*)\r', 'local_vars.web_layer_output_folder = r"{0:s}"\r'.format(self.replace_string), None,
											local_vars.web_layer_output_folder),
		}

		log.write("Reading PISCES Configuration", True)
		with open(os.path.join(local_vars.code_folder, "config.py"), 'rb') as config_file:
			self.file = config_file.read()
			for name in self.patterns:  # look through all the patterns on each line (this could get slow as the config grows, fine for now)
				try:
					match = re.search(self.patterns[name][0], self.file).group(1)
					if match:  # if we have a match
						self.__dict__[name] = self.patterns[name][3]  # save the first subgroup as an attribute on this object, named by the dictionary key
				except AttributeError:
					log.error("Couldn't find an item in the configuration file. Check your patterns and your config file. You may need to restore the default")

	def save(self):
		log.write("Writing PISCES Configuration", True)
		for name in self.patterns:  # look through all the patterns on each line (this could get slow as the config grows, fine for now
			log.write("Saving %s" % name, True)
			if type(self.__dict__[name]) is not self.patterns[name][2] and self.patterns[name][2] is not None:  # If the type mismatches the required type. None stands for any
				raise TypeError("Type mismatch for PISCES configuration option {0:s}. You provided an object of type {1:s}. This option requires an item of type {2:s}".format(name, type(self.__dict__[name]), self.patterns[name][2]))
			self.file = re.sub(self.patterns[name][0], self.patterns[name][1].replace(self.replace_string, str(self.__dict__[name])), self.file)  # replace the pattern with the replacement string (look up the value for it in the object's dict

		with open(os.path.join(local_vars.code_folder, "config.py"), 'wb') as config_file:
			config_file.write(self.file)