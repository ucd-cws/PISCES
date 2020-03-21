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


class Get_Species_List_from_HUCs(script_tool_funcs.Filter_Tool_Template):

	def getParameterInfo(self):
		"""Define parameter definitions"""
		params = self.filter_params()
		return params


