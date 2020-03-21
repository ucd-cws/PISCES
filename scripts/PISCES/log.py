from __future__ import print_function

import logging
import datetime
import os

import arcpy

global mylog
global datalog
global errorlog
global arc_script_flag

base_folder = os.path.split(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])[0]

def write(log_string, auto_print=0):  # default write function - will be overridden by initialize(), but auto-calls it if the user forgets
	initialize("auto-init")
	write(log_string, auto_print)

def info(log_string):  # start making an API compatible with Python's built-in logging
	write(log_string, auto_print=1)

def error(log_string):
	write(log_string, 1)  # autowrite it to the main log and the screen too
	errorlog.write("%s - %s\n" % (get_datestring(), log_string))

def warning(log_string):
	error(log_string)  # for normal use, it behaves just the same. In a script tool, it doesn't

def initialize(log_string=None, arc_script=0, log_file=None):
	global mylog
	global datalog
	global errorlog
	global arc_script_flag
	global write  # we're going to override them in order to save log-time processing power - small hit to maintainability
	global error  # we're going to override the error function too
	global warning  # and warning

	arc_script_flag = arc_script  # on init, an arc script will pass this in as "1", which other logging functions will use to determine whether to write an add_message

	logging.basicConfig(filename=os.path.join(base_folder, "log", "python_logging_output.txt"), level=logging.DEBUG)

	if log_file:  # allow override of log file location
		mylog = open(log_file, 'a')
	else:
		mylog = open(os.path.join(base_folder, "log", 'fsfish_processing_log.htm'), 'a')  # main log file - open the log file in append mode
	datalog = open(os.path.join(base_folder, "log", 'fsfish_changes.log.txt'), 'a')  # data log - logs major changes to data between version
	errorlog = open(os.path.join(base_folder, "log", 'fsfish_error.log.txt'), 'a')
	l_date_string = get_datestring()

	if log_string is not None:
		log_string = " - %s" % log_string
	else:
		log_string = " "

	mylog.write("\n<h2>New Run Began at %s%s</h2>\n" % (l_date_string, log_string))
	errorlog.write("\nNew Run Began at %s%s\n" % (l_date_string, log_string))

	if arc_script == 0:
		def write(log_string, auto_print=0):

			mylog.write("<p>%s - %s</p>\n" % (get_datestring(), log_string))

			if auto_print == 1 or auto_print is True:  # autoprint lets us just make the call to log.write and have it also appear on screen
				try:
					print("%s" % log_string)
				except:
					mylog.write("<p>Unable to write last message to screen</p>")
	else:
		def write(log_string, auto_print=0):

			mylog.write("<p>%s - %s</p>\n" % (get_datestring(), log_string))

			if auto_print == 1 or auto_print is True:  # autoprint lets us just make the call to log.write and have it also appear on screen
				arcpy.AddMessage("%s" % log_string)  # we could theoretically utilize some caller detection to figure out if this is an error (or just have a param) so that we could use AddError instead

		# we need to overwrite error too, so that we can do arcpy.AddError on failure
		def error(log_string):
			l_date_string = get_datestring()
			mylog.write("<p>%s - %s</p>\n" % (l_date_string, log_string))
			arcpy.AddError(log_string)
			errorlog.write("%s - %s\n" % (l_date_string, log_string))


		def warning(log_string):
			l_date_string = get_datestring()
			mylog.write("<p>%s - %s</p>\n" % (l_date_string, log_string))
			arcpy.AddWarning(log_string)
			errorlog.write("%s - %s\n" % (l_date_string, log_string))

def get_datestring():
	l_date = datetime.datetime.now()
	return "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year, l_date.month, l_date.day, l_date.hour, l_date.minute, l_date.second)

def data_write(log_string):
	datalog.write("%s - %s\n" % (get_datestring(), log_string))


def debug(log_string, screen=False):  # this formerly only acted if debug was on - skipping for now
	write(log_string, screen)


def bug(items):
	if type(items) is tuple:
		for item in items:
			print("[%s]" % item)
	else:
		print("[%s]" % items)