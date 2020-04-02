##
##    System - PISCES
##    File - tables.py - handles table related transformations of the data for output
##
from __future__ import absolute_import, division, print_function

import sys
import os
import csv
import re

import arcpy
import markdown
import smartypants

from . import funcs
from . import local_vars
from . import log

#filter_data = arcpy.GetParameterAsText(0)
#output_folder = arcpy.GetParameterAsText(1)

local_vars.start()


html_flag = True


# Set up the args!
table_query = arcpy.GetParameterAsText(0)
table_name = arcpy.GetParameterAsText(1)
output_folder = arcpy.GetParameterAsText(2)
output_filename = arcpy.GetParameterAsText(3)
filter_data = arcpy.GetParameterAsText(4)  # we're not yet set up to handle this as a param, really, except for a test - the values won't be set!

if not os.path.exists(output_folder):
	output_folder = os.path.join(os.getcwd(), output_folder)  # try joining the current path to the folder

if output_folder == os.getcwd() or not(os.path.exists(output_folder)):  # if it's only the current directory, or it doesn't exist
	output_folder = os.path.join(os.getcwd(), "maps", "web_output", "tables")  # then drop it into web_output
	log.write("Setting output folder to %s" % output_folder)

if output_filename == "" or output_filename is None:
	raise BaseException("No filename given for output")

if filter_data:
	filter_data_flag = True
else:
	filter_data_flag = False

def get_input_accessor(input):
	'''Determines whether the input is shape/features or csv data and returns a 2 item array with a code ( fl | csv) as value 1 and either a feature layer or a filehandle as the value 2, depending'''

	log.write("Determining data type of limit file and opening", 1)
	# ############# TEMPORARY LINE ####################
	input = os.path.join(os.getcwd(), "selected.csv")  #TODO: REMOVE!

	description = arcpy.Describe(input)

	if description.dataType == "Shapefile" or description.dataType == "FeatureClass":
		l_data = arcpy.MakeFeatureLayer_management(input)
		return ['fl', l_data]
	elif description.dataType == "FeatureLayer":
		return ['fl',input]
	elif ".csv" in input or '.CSV' in input or '.Csv' in input:
		# this is NOT a robust check for csv type, which is why it's last - if it's something else described by arcpy, then we trust that more.
		# theoretically, we could just do a simple regex to ensure that ".csv" is at the end, but that's not too much better...

		input_filehandle = open(input, 'r')  # open it read-only

		return ['csv', input_filehandle]


def get_output_location():
	pass


def get_filter_values_from_input(input, filter_col="HUC_12"):
	'''takes an input filehandle or feature layer from get_input_accessor and returns an array with the filter values'''

	log.write("Getting filter values", 1)
	filter_items = []

	if input[0] == 'csv':
		input_reader = csv.DictReader(input[1])
		for row in input_reader:
			try:
				filter_items.append(row[filter_col])
			except KeyError:
				log.error("column %s is not a column in the input data" % filter_col)
				raise
	elif input[0] == 'fl':
		# it's a feature layer

		if operation == "clip":
			#TODO
			# spatial join?
			# change input[1] to the result
			# set column to HUCs
			# then it can be processed by the following code
			pass


		l_cursor = arcpy.SearchCursor(input[1])
		for row in l_cursor:
			try:
				filter_items.append(row.getValue(filter_col)) # add the values in
			except:
				log.error("unable to get data from feature layer - make sure that it has a column with the name you are specifying - exiting")
				raise
		del l_cursor
		del row

	else:
		log.error("file format not understood - exiting")
		sys.exit()

	db_col = "Zone_ID"
	return filter_items, db_col # return the data


def filter_rows(filter_values=None, db_column=None, sql="select * from observations", filter="", ignore_cols=[]):
	'''connects to db, iterates over each row, and if it matches a value in filter values, it saves that row to an array'''

	log.write("Retrieving data and filtering rows", 1)

	db_cursor, db_conn = funcs.db_connect(local_vars.maindb)

	## compose the sql query
	if sql is None or sql == "":
		sql = "select * from observations"  # we define it again in case ArcGIS passes in a blank value

	if not (filter == "" or filter is None):
		import re
		if re.search('where', filter.lower()):  # if it already has a where clause
			# we'll assume the query passed in is valid as is - if not, the db will give an error, which is fine
			# this means that it's a where clause with one or more complete conditions and not ending with "and"
			sql = "%s and %s" % (sql, filter)

	## execute the sql
	rows = db_cursor.execute(sql)

	saved_rows = []

	# the following is a HACK - not sure how to get the length of a pyodbc row - the documentation doesn't say

	num_cols = None

	## put together lists of results to store from the database cursor
	for row in rows:  # for every row
		if num_cols is None:  # only trigger the first time through - better done outside of loop, but whatever...
			i = 0
			# the following block is just looking to figure out how many columns we have
			while i < 5000:  # set a huge upper limit that will trigger before the program freezes if something goes wrong, but won't trigger too early
				try:
					test = row[i]
				except IndexError:  # we've gone out of bounds
					break
				i += 1

			num_cols = i  # so the column limit is the i value minus one, but passing a value of 1+ to range() will generate what we want

		if (filter_values is not None) and (row.__getattribute__(db_column) not in filter_values):  # if we have filter values, and it's not in the filter values, then don't keep it
			continue
		else:
			new_row = []  # make a new row
			for i in range(num_cols):  # and for every column in it
				if row.cursor_description[i][0] in ignore_cols:  # is this column one of the ones we're looking to ignore?
					continue  # if so, skip it - this is more efficiently done in sql, but for large tables we may want to specify this way
				if html_flag:
					try:
						if (type(row[i]) is str or type(row[i]) is unicode) and ('\n' in row[i] or len(row[i]) > 255):
							# try to detect if we want to html-ify it.
							# do we have a text field that is either a multiline or long field?
							new_row.append(html_convert(row[i]))
						else:
							if row[i] is None:
								new_row.append("")
							else:
								new_row.append(row[i])  # fallback to just adding it
					except:
						new_row.append(row[i])  # if something goes wrong, just add the text to the row
				else:
					if row[i] is None:
						new_row.append("")
					else:
						new_row.append(row[i])  # add that column to the new row
			saved_rows.append(new_row)  # then add the new row to the saved rows

	new_row = []  # do it one more time - we're going to prepend a header
	for column in row.cursor_description:  # for every column returned
		if column[0] in ignore_cols:  # if it's a column we don't want
			continue  # skip it
		new_row.append(column[0])  # add just the name as a new_row item

	saved_rows.insert(0, new_row)

	return saved_rows


def html_convert(data):

	if data is None:
		return ""

	converted_txt = data.replace(" - ", " -- ")
	converted_txt = smartypants.educateQuotes(converted_txt)
	converted_txt = smartypants.educateEllipses(converted_txt)
	converted_txt = smartypants.educateDashesOldSchool(converted_txt)
	# normalise line endings and insert blank line between paragraphs for Markdown
	converted_txt = re.sub("\r\n", "\n", converted_txt)
	converted_txt = re.sub("\n\n+", "\n", converted_txt)
	converted_txt = re.sub("\n", "\n\n", converted_txt)
	converted_txt = unicode( converted_txt, "utf8" )

	html = markdown.markdown(converted_txt)	

	return html


def write_table(rows, output=os.path.join(os.getcwd(), "temp.csv")):
	log.write("writing rows out", 1)

	data_writer = csv.writer(open(output, 'wb'), quoting=csv.QUOTE_ALL)
	for row in rows:  # for every row
		try:
			row = remove_newlines(row)
			data_writer.writerow(row)  # try to write the row
		except:
			log.error(
				"failed to write row - can't output row - probably a bad character")  # and write it to the log so that it can be looked at later


def remove_newlines(l_list):

	# remove windows, linux, and mac newlines and return the string
	for inc in range(len(l_list)):
		l_list[inc] = re.sub('\r\n'," /nwln/ ", str(l_list[inc])) # \r\n goes first since otherwise anything that has it will get hit twice
		l_list[inc] = re.sub('\n',' /nwln/ ', str(l_list[inc]))
		l_list[inc] = re.sub('\r',' /nwln/ ', str(l_list[inc]))

	return l_list

if not os.path.exists(output_folder): # does our output folder exist?
	os.makedirs(output_folder) # make all dirs required up to and including the output

if filter_data_flag is True:    
	data_accessor = get_input_accessor(filter_data)
	filter_vals,db_col = get_filter_values_from_input(data_accessor)
else:
	filter_vals = None
	db_col = None

if table_query == "query":
	output_rows = filter_rows(sql=table_name,ignore_cols = ["Shape"], filter_values = filter_vals,db_column = db_col)
else:
	output_rows = filter_rows(sql="select * from %s" % table_name,ignore_cols = ["Shape"], filter_values = filter_vals,db_column = db_col)
write_table(output_rows,os.path.join(output_folder,output_filename))
