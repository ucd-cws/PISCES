__author__ = 'dsx'

import os
import imp

try:
	import local_vars
except ImportError:
	from PISCES import local_vars, arcpy_metadata
try:
	import log
except ImportError:
	from PISCES import log

import metadata_basic as basic

__all__ = []

try:
	import arcpy_metadata
except ImportError:
	from PISCES import arcpy_metadata

arcpy_metadata.metadata_temp_folder = local_vars.temp


def discover_plugins():  # could probably have done this by just leaving things be with the items in the folder...
	"""
		Searches this folder for modules and loads them - each one being a separate metadata plugin. They become available as dotted modules in this package
		For example, plugin basic.py is in this folder. After running this module, basic.py is available at PISCES.plugins.metadata.basic
	:return:
	"""

	global __all__
	__all__ = []

	plugin_folder = os.path.split(os.path.abspath(__file__))[0]

	for filename in os.listdir(plugin_folder):
		if filename != "__init__.py" and filename.endswith(".py"):
			mod_name = os.path.splitext(filename)[0]
			__all__.append(mod_name)

			with open(os.path.join(plugin_folder, filename), 'r') as mod_file:
				globals()[mod_name] = imp.load_module(mod_name, mod_file, filename, ('', 'r', imp.PY_SOURCE))  # loads the module after using the find command to search for it in the current folder, and expands out the tuple

			log.write("Found metadata plugin: %s" % globals()[mod_name].__name__, True)


## TODO: We should have some sort of run_plugin method here that handles when a plugin isn't available


def format_args(args_string):
	"""
		Takes an args string in the form key1=value1::key2=value2::key3=value3 and turns it into a dict {key1: value1, key2: value2, key3: value3}
	:param args_string: string of arguments in the form key1=value1::key2=value2::key3=value3
	:return: dict: arguments as key value pairs
	"""

	args = {}
	all_args = args_string.split("::")
	for item in all_args:
		key, value = item.split("=", 1)
		args[key] = value

	return args

