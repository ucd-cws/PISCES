from __future__ import print_function

__author__ = 'dsx'

import os
import sys

from Tkinter import Tk
from tkFileDialog import askdirectory
import pyodbc

import arcpy

try:
	from PISCES.funcs import db_connect
except ImportError:

	def db_connect(db_name, note=None, access=False):

		if not access:
			conn = pyodbc.connect('DRIVER=SQLite3 ODBC Driver;Database=%s' % db_name)
		else:
			conn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb)};DBQ='+db_name)

		return conn.cursor(), conn


def delete_queries(delete_items, database, access_db=True, softerror=False):
	"""
		We have a number of queries that are for internal use, but DFW won't want to see - delete them on build
	:param delete_items: file path of the file with the names of the queries to delete (one per line)
	:param database: full path to the database the queries are in
	:return:
	"""

	db_cursor, db_conn = db_connect(database, access=access_db)

	with open(delete_items, 'r') as to_delete:
		for item in to_delete:
			print("Dropping Table {0:s}".format(item))
			try:
				db_cursor.execute("DROP TABLE %s" % item)
			except pyodbc.ProgrammingError:
				print("Unable to drop table {0:s}".format(item))
			except pyodbc.Error:
				if not softerror:
					raise
				else:
					print("Unable to remove a table (%s) - it likely doesn't exist - moving on!" % item)

	db_conn.commit()
	db_cursor.close()
	db_conn.close()


if __name__ == "__main__":
	directory = arcpy.GetParameterAsText(0)
	care_errors = arcpy.GetParameter(1)  # do we care about errors?
	
	if not directory:
		print("Please select the PISCES folder location!")
		#  the following code is from http://stackoverflow.com/questions/3579568/choosing-a-file-in-python-simple-gui - thanks!
		Tk().withdraw()  # we don't want a full GUI, so keep the root window from appearing
		directory = askdirectory()  # show an "Open" dialog box and return the path to the selected file

	if not directory:  # maybe they hit cancel
		print("No directory, exiting")
		sys.exit()

	# start by deleting unneccessary queries from the databases
	config_delete_items = os.path.join(directory, "dependencies", "builddata", "removequeries.txt")
	access_database = os.path.join(directory, "data", "pisces.mdb")
	sqlite_database = os.path.join(directory, "data", "pisces.sqlite")

	delete_queries(config_delete_items, access_database, access_db=True, softerror=care_errors)
	delete_queries(config_delete_items, sqlite_database, access_db=False, softerror=care_errors)

	# then build the pyramids on the hillshade layer - we don't include it because it's unnecessary bulk (~250MB) and can be remade
	# but we need to build the pyramids or else we get performance issues using the map documents.
	hillshade = os.path.join(directory, "data", "Hillshade", "swiss_ca_flattened.tif")
	arcpy.BuildPyramids_management(hillshade)

# something = raw_input("Hit any key to select the PISCES database to clean/build.")

