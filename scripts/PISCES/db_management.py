"""
	Database loading and dumping for use in version control. With these scripts, we can better track what changes happen
	in the database in version control - binary DB representations get dumped to text and can then actually be compared
	via version control - GitHub would reject our DB file as being too big, but BitBucket should be OK with it. I might
	try committing it to a test repo first and see how it does with pushing that file though.

	General usage is that AFTER changes are made, dehydrate_db should be called to dump the database to a file - this
	file will be monitored in version control and changes can then be committed. Then, on other machines, unless they have
	made their own changes to the DB, they should run hydrate_db to get the latest copy of the database.

	At some point, we can make an update_db.py script or utility that retrieves the latest "release" database and runs
	it through hydrate.

"""
from __future__ import absolute_import, division, print_function

import os
import platform
import subprocess
import shutil

from . import local_vars
from . import log

DUMP_EXTENSION = "sqldump"
DUMP_FOLDER = os.path.join(local_vars.internal_workspace, "data", "dumps")

def _get_time(file_path):
	if platform.system() == 'Windows':
		return os.path.getmtime(file_path)
	else:
		stat = os.stat(file_path)  # Mac
		try:
			return stat.st_birthtime
		except AttributeError:
			# We're probably on Linux. No easy way to get creation dates here, so we'll take the last modified date
			# and subtract the file length, which should be sufficient
			return stat.st_mtime

def _get_latest_export(folder):
	list_of_files = os.listdir(os.path.join(folder))  # get all the files in the folder first
	only_sql = [filename for filename in list_of_files if filename.endswith(DUMP_EXTENSION)]  # doing this instead of glob because I think globbing had some performance issues on windows/networks

	# this step does two things - first, it adds back in the full folder path, and it filters out anything that's not SQL
	final_candidates = [os.path.join(folder, filename) for filename in only_sql]

	# return the single dump with the latest time, returning None if we have no dumps for any reason
	if len(final_candidates) is 0:
		return None

	return max(final_candidates, key=_get_time)


def hydrate_db(db=local_vars.maindb,
			   sqlite=os.path.join(local_vars.internal_workspace, "utils", "sqlite-tools-win32-x86-3240000", "sqlite3.exe"),
			   db_export_folder=DUMP_FOLDER):
	"""
		Retrieves the latest file (by creation time) from db_export_folder with the extension sqldump and loads it into
		a sqlite database, replacing pisces.sqlite.
	:param db:
	:param sqlite:
	:param db_export_folder:
	:return:
	"""

	data_dump = _get_latest_export(db_export_folder)

	if os.path.exists(db):
		db_time = _get_time(db)
		backup_folder = os.path.join(DUMP_FOLDER, "backups")
		if not os.path.exists(backup_folder):
			os.makedirs(backup_folder)

		log.info("Removing existing DB, but making a backup into dumps folder")
		shutil.copyfile(db, os.path.join(backup_folder, "{}_{}".format(os.path.split(db)[1], db_time)))
		os.remove(db)

	hydrate = os.path.join(DUMP_FOLDER, "hydrate.sql")
	with open(hydrate, 'w') as hydrate_file:
		hydrate_file.write("PRAGMA journal_mode = OFF;\nPRAGMA synchronous = OFF; \n.read {}".format(data_dump.replace("\\", "/")))

	log.info("Loading DB export from {} into {}".format(data_dump, db))
	subprocess.check_call([sqlite, db, ".read {}".format(hydrate.replace("\\", "/"))])


def dehydrate_db(db=local_vars.maindb,
				 sqlite=os.path.join(local_vars.internal_workspace, "utils", "sqlite-tools-win32-x86-3240000", "sqlite3.exe"),
				 db_export_folder=DUMP_FOLDER):
	"""
		Exports single tables into dump folder so they can be better versioned as they change. The hydrate_db function
		doesn't yet match this well.
	:param db:
	:param sqlite:
	:param db_export_folder:
	:return:
	"""

	for table in local_vars.all_tables:
		db_export_file = os.path.join(db_export_folder, "pisces_{}.{}".format(table, DUMP_EXTENSION))
		if os.path.exists(db_export_file):
			log.info("Removing existing DB export file")
			os.remove(db_export_file)

		dehydrate = os.path.join(DUMP_FOLDER, "dehydrate_{}.sql".format(table))
		with open(dehydrate, 'w') as dehydrate_file:
			dehydrate_file.write(".output {}\n".format(db_export_file.replace("\\", "/")))
			dehydrate_file.write(".schema {}\n".format(table))
			dehydrate_file.write("select * from {}\n".format(table))

		log.info("Exporting to {}".format(db_export_file))
		subprocess.check_call([sqlite, db, ".read {}".format(dehydrate.replace("\\", "/"))])
		log.info("Exported {}".format(table))