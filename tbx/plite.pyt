__author__ = 'dsx'

from sqlalchemy import distinct
import arcpy

from PISCES import local_vars
from PISCES import orm
from PISCES import api
from PISCES import script_tool_funcs


def connect_orm():

	script_tool_funcs.get_location()
	orm.connect(local_vars.ormdb)
	session = orm.Session()
	return session


class Toolbox(object):
	def __init__(self):
		"""Define the toolbox (the name of the toolbox is the name of the
		.pyt file)."""
		self.label = "PISCES 2lbox"
		self.alias = ""

		# List of tool classes associated with this toolbox
		self.tools = [Get_Species_List_from_HUCs]



class Tool_Template(object):

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

		params = [hucs_layer,]
		return params

	def isLicensed(self):
		"""Set whether tool is licensed to execute."""
		return True

	def updateParameters(self, parameters):
		"""Modify the values and properties of parameters before internal
		validation is performed.  This method is called whenever a parameter
		has been changed."""

		return

	def updateMessages(self, parameters):
		"""Modify the messages created by internal validation for each tool
		parameter.  This method is called after internal validation."""
		return

	def execute(self, parameters, messages):
		"""The source code of the tool."""
		"""The source code of the tool."""

		hucs = parameters[0].valueAsText
		huc_ids = zones_feature_to_array(hucs)
		arcpy.AddMessage("%s HUCs Selected" % len(huc_ids))

		species = api.get_common_names_in_hucs(huc_ids)

		for item in species:
			arcpy.AddMessage(item)
		arcpy.AddMessage("%s taxa" % len(species))

		arcpy.GetMessages()



def zones_feature_to_array(zones_layer):

	l_cursor = arcpy.SearchCursor(zones_layer)

	zones_array = []

	for feature in l_cursor:  # should only iterate over the selected features
		zones_array.append(feature.HUC_12)

	return zones_array


class Get_Species_List_from_HUCs(Tool_Template):

	def getParameterInfo(self):
		"""Define parameter definitions"""
		params = self.filter_params()
		return params


