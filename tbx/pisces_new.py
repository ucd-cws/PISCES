import arcpy

from code_library.common import toolbox
from PISCES import script_tool_funcs


class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "PISCES New Tools"
		self.alias = ""

		# List of tool classes associated with this toolbox
		self.tools = [Get_Species_List_from_HUCs]


class Filter_Tool_Template(object):

	def __init__(self):
		"""Define the tool (tool name is the name of the class)."""
		self.label = "Get Species List from HUCs"
		self.description = ""
		self.canRunInBackground = False
		self.blank = ""
		self.params_index = {}

	def filter_params(self):
		"""Define parameter definitions"""
		hucs_layer = arcpy.Parameter(name="hucs_layer",
									 displayName="Selected HUC12s",
									 direction="input",
									 parameterType="required",
									 enabled=True,
									 multiValue=False,
									 datatype="GPFeatureLayer")

		limit_to = arcpy.Parameter(name="limit_to",
									 displayName="Limit to these taxa or groups",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=False,
									 datatype="GPString")

		limit_to_holder = arcpy.Parameter(name="limit_to_holder",
									displayName="Limit holder",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=True,
									 datatype="GPString")

		datasets = arcpy.Parameter(name="datasets",
									 displayName="Limit to these datasets within PISCES",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=False,
									 datatype="GPString")

		datasets_holder = arcpy.Parameter(name="datasets_holder",
									displayName="Dataset limit holder",
									 direction="input",
									 parameterType="optional",
									 enabled=True,
									 multiValue=True,
									 datatype="GPString")
		datasets_holder.value = "Best available knowledge 8/2013;Non native QC 12/12/13"
		datasets_holder.category = "Advanced Options"

		params = [hucs_layer, limit_to, limit_to_holder, datasets, datasets_holder]
		toolbox.index_params(self, params)

		script_tool_funcs.make_species_group_picker(self, limit_to, limit_to_holder, objects_passed=True)
		return params

	def isLicensed(self):
		"""Set whether tool is licensed to execute."""
		return True

	def updateParameters(self, parameters):
		"""Modify the values and properties of parameters before internal
		validation is performed.  This method is called whenever a parameter
		has been changed."""

		script_tool_funcs.add_selection(self, parameters[1], parameters[2], objects_passed=True)

	def updateMessages(self, parameters):
		"""Modify the messages created by internal validation for each tool
		parameter.  This method is called after internal validation."""
		return

	def execute(self, parameters, messages):
		"""The source code of the tool."""
		return


class Get_Species_List_from_HUCs(Filter_Tool_Template):

	def getParameterInfo(self):
		"""Define parameter definitions"""
		params = self.filter_params()
		return params


