from __future__ import absolute_import, division, print_function

__author__ = 'nrsantos'

## INSTRUCTIONS:
## Commit your PISCES working directory to the repository so you can roll back any bad changes
## Run a full output from PISCES and set it aside somewhere. We'll need it later
## Set this code up. Make sure to update the variables in USER VARIABLES below with your new set of migration information
## Run this code. It will do *almost* all translations for you, but for tables with  one-to-one joins to the HUC12 layer (probably just one), it may not complete the translation because it can't determine which record should become the record for a new HUC ID when two HUCs merge. In this case, it will print out an error and ask you to intervene.
## Make any manual interventions indicated
## Pay attention to the outputs and results of the log messages in the PISCES main log.
## Commit changes again
## Run another full output from PISCES.
## Place the outputs in the same location and run the comparison script in tests/nonunittest_compare_range_sets.py


import os
import sys
import csv
import unittest

import arcpy
import pyodbc

from . import local_vars
from . import log
from . import funcs
from . input_filters import common

from .tests import test_data


### USER VARIABLES: Update these each run
migs_file = os.path.join(os.getcwd(), "utils", "huc12_updates_2013.csv")  # file containing all of the migrations
new_layer = os.path.join(os.getcwd(), "utils", "HUC_12s_CWS_Mod.gdb", "HUC12_AllCABasins_and_HUC8_CWSMod")  # location of the new HUC_12 layer
primary_key = "source"  # the key to hucs to use in the migrations file
secondary_key = "destination"  # the destination huc key in the migrations file
old_layer_name = "oldHUC12FullState"  # what do we rename the old layer?
log_dir = os.path.join(os.getcwd(), "log", "huc_migration_2013", )
changes_output_file = os.path.join(log_dir, "huc12_changes.csv")  # where to write the changes made out to - just a log file
new_hucs_output_file = os.path.join(log_dir, "huc12_changes_new_hucs.csv")  # where to put the list of all NEW HUCs
removed_hucs_output_file = os.path.join(log_dir, "huc12_changes_removed_hucs.csv")  # where to put the list of all the HUCs that no longer exist
changed_species_output_file = os.path.join(log_dir, "huc12_changed_species.csv")  # where to output the list of species that were changed to
if not os.path.exists(log_dir):
	os.mkdir(os.path.join(os.getcwd(), "log", "huc_migration_2013"))

local_vars.start()
log.initialize("Migrating HUCs", log_file=os.path.join(log_dir, "huc_migration_log.html"))

migration_items = {}
changes = []

ID_drop_fields = ["ID", "OBJECTID", ]

collection_id = None  # the collection to add the affected records to so that we can track which records were changed by this code - set by the creation of a collection in the code below
other_tables_field = 'huc_update_2013_created'  # the field to mark in zones_aux if it was added

log_table = "HUC_Migration_Log"
clear_tables = ['Connectivity', 'Layer_Cache']  # tables generated from the data that need to be cleared
additional_tables = {'Zones_Aux': 'Zone'}  # Table, HUC field pairs. Observations/Invalid_Observations are handled by the class
additional_pkeys = {'Zones_Aux': 'ID'}
master_tables = {'Observations': 'Zone_ID', 'Invalid_Observations': 'Zone_ID'}
cardinality = {'Zones_Aux': 'One'}  # dictionary defining whether there can be many records given how we're working with the table. Options are "One" and "Many"
fake_zones_aux_ids = {}  # we'll need to temporarily assign some records to this pool
fake_ids_index = 1
test_modules = [test_data,]


### Basic approach of this code
# select the records in observations that are affected by the change. Determine if they belong to any datasets
#	if one to one - update the observations and zonesaux items to use new layer (other tables?)
#	if one old, two new, update primary, add new records for secondary to all tables with same exact data as primary. Add zones_aux flag indicating this is how it was added
	# then, need to create records for it in datasets (like QC dataset)
#	if two old, one new, it acts the same as one to one. old huc as primary effectively means it is one to one, but we need to check zones_aux. Maybe as a manual flag
# add all affected records (existing and new) to a new dataset that consists of records affected by HUC changes
#	if no primary, but secondary, just create it in appropriate place
#	move old layer to a different name
#	replace old layer with new layer
#	Manually check some other tables.
# theoretically, if we don't have any destination huc, then we should delete records, maybe, but we won't do that.


def load_migrations(migrations_file, pkey=primary_key, skey=secondary_key, migrations=migration_items):
	"""
		Opens migrations_file, loads data into dict passed in as migrations
	"""

	file_pointer = open(migrations_file, 'rb')
	migration_data = csv.DictReader(file_pointer)

	for item in migration_data:
		key = item[pkey]
		if key in migrations:  # if this pkey already is created in the dict, just append the secondary huc
			migrations[key].append(item[skey])
		else:  # otherwise, create the list
			migrations[key] = [item[skey], ]  # and prepopulate the list we make with the HUC12 from the file

	### The following code was to check for a situation that "should never happen" but happened a lot. Reengineered the code
	### to mitigate the problem. Can now skip the check. Leaving, just in case, and for the beastly list comprehension.
	docstring = """
	# check for a condition that should never happen - essentially, a HUC ID being reassigned to a geographically different HUC
	for key in migrations:  # we're going to do this by seeing if a HUC is both a source and a destination in the input data, which would say that it should both be translated to and away from at the same time
		if key in [item for values in migrations.values() for item in values]:  # list comp. basically says "if the key is a destination huc for any of the others"
			log.write("WARNING WARNING WARNING: Some HUCs (%s) are both a source and a destination. If they are not in the"
					  " correct order (change the sources before adding the new destination), you will"
					  " run into problems" % key, 1)
	"""

	file_pointer.close()


def find_affected(migrations, change_items, changed_collection, changed_field, other_tables, db_conn):
	"""
		This might be a bit of a backward way to doing this - we maybe should just do it on load from the file
	"""
	db_cursor = db_conn.cursor()

	all_source_hucs = []
	for key in migrations:
		duplicate = False
		for destination in migrations[key]:
			change = huc_change()
			change.source = key
			all_source_hucs.append(key)
			change.db_conn = db_conn  # setting it here to avoid passing it in everywhere. Inefficient, but fine.
			change.destination = destination
			change.needs_creating = duplicate  # first time through, it's false, but then will be true
			change.changed_collection = changed_collection
			change.changed_flag_field = changed_field

			change.load(db_cursor, other_tables)  # we need to load the change no matter what
			change_items.append(change)

			duplicate = True

	db_cursor.close()

	return change_items, all_source_hucs


class huc_change():
	# TODO: Still needs tests

	def __init__(self):
		self.source = None
		self.destination = None
		self.observations = []  # a list of observations objects, loaded with the affected observations. Then, we can create new ones.
		self.invalid_observations = []  # same as above but for the invalid observations table
		self.zones_aux = []
		self.needs_creating = False  # flags whether this change requires duplicating another
		self.db_conn = None  # store the db connection here so we don't have to pass it in every time. Not particularly efficient. Don't care.
		self.changed_collection = None
		self.changed_flag_field = None  # the field to record the field that indicates if this record was affected by the HUC12 change
		self.affected_ids = {}  # empty dict keyed by table where we store the ids of the affected observations

	def load(self, db_cursor, other_tables):
		"""
			Loads the records for the affected observations and invalid_observations
		"""
		self.load_item("Observations", self.observations, db_cursor)
		self.load_item("Invalid_Observations", self.invalid_observations, db_cursor)
		for obs_item in self.invalid_observations:  # manually set the value of the fields specific to invalid observations. This is only for records we duplicate and add and won't affect the existing records
			obs_item.reason_invalid = "See %s" % obs_item.objectid
			obs_item.invalid_notes = "See %s" % obs_item.objectid
			obs_item.zone_id = self.destination
			if self.changed_collection:
				obs_item.collections.append(self.changed_collection)

		for obs_item in self.observations:  # override the zone_id for when/if we insert this record
			obs_item.zone_id = self.destination
			if self.changed_collection:
				obs_item.collections.append(self.changed_collection)

		secondary_cursor = self.db_conn.cursor()
		global fake_ids_index  # TODO: Make this more portable
		for table in other_tables:
			select_query = "select ID from %s where %s = ?" % (table, other_tables[table])  # find the affected records TODO: This assumes all "other_tables" have primary key of "ID"
			self.affected_ids[table] = []
			results = db_cursor.execute(select_query, self.source)
			for record in results:
				self.affected_ids[table].append(record.ID)

				# this is a hack. Fudge the foreign keys on the table since we're going to set them later anyway. Need them to not interfere with each other
				update_query = "update %s set %s=? where %s=?" % (table, other_tables[table], additional_pkeys[table])  # TODO: Additional pkeys is global
				secondary_cursor.execute(update_query, str(fake_ids_index), record.ID)
				fake_ids_index += 1

		secondary_cursor.close()

	def update(self, other_tables):
		"""
			A single point to run the updates from
		"""
		if self.source is None:  # if this is just a new HUC with no changes
			return  # we'll skip it for now because it'll be created later

		if not self.needs_creating:  # not duplicating. It's "the original"
			self.update_in_place(other_tables)
		else:
			self.duplicate(other_tables)

	def update_in_place(self, other_tables):
		db_cursor = self.db_conn.cursor()
		obs_query = "Update Observations set Zone_ID = ? where Zone_ID = ? and OBJECTID = ?"
		invalid_query = "Update Invalid_Observations set Zone_ID = ? where Zone_ID = ? and OBJECTID = ?"

		for obs in self.observations:
			db_cursor.execute(obs_query, self.destination, self.source, obs.objectid)
		for obs in self.invalid_observations:
			db_cursor.execute(invalid_query, self.destination, self.source, obs.objectid)

		# for new records, this happens automatically. For in place updates, we need to add it here
		for obs_item in self.observations:
			log.write("inserting collections (%s) for %s" % (obs_item.collections, obs_item.objectid))
			obs_item.insert_collections(db_cursor)

		for table in other_tables:  # run it for all of the other tables now
			for record_id in self.affected_ids[table]:
				query = "update %s set %s = ?, %s = yes where %s = ?" % (table, other_tables[table], self.changed_flag_field, additional_pkeys[table])
				try:
					#log.write("Query update %s, %s, %s" % (query, self.destination, record_id), 1)
					db_cursor.execute(query, self.destination, record_id)
				except pyodbc.IntegrityError:
					global fake_ids_index
					if cardinality[table] == "One":
						new_fake = "%s_%s" % (self.destination, fake_ids_index)  # fake_ids_index is last for sortability - want to make it line up next to its twin and see what to put
						fake_ids_index += 1
						log.write("CARDINALITY VIOLATION: Human intervention needed. Table: %s, record ID: %s. Duplicate Zone inserted. Please manually determine which record to use between the one with the current correct ID of %s and a temporary record with the incorrect ID of %s" % (table, record_id, self.destination, new_fake), 1)
						q2 = "update zones_aux set %s='%s' where %s =%s" % (other_tables[table], new_fake, additional_pkeys[table], record_id)
						db_cursor.execute(q2)

		db_cursor.close()

	def duplicate(self, other_tables):

		self.insert_observations()  # also includes invalids and collections
		self.duplicate_other_tables(other_tables=other_tables)

	def insert_observations(self):
		db_cursor = self.db_conn.cursor()

		for observation in self.observations:
			observation.insert(db_cursor)  # collections are inserted by the observation class
		for invalid in self.invalid_observations:
			invalid.insert(db_cursor)  # collections are inserted by the observation class

		db_cursor.close()

	def load_item(self, table, storage_list, db_cursor):
		query = "select OBJECTID from %s where Zone_ID = ?" % table
		records = db_cursor.execute(query, self.source).fetchall()

		for record in records:
			observation = local_vars.observation()
			observation.load(record.OBJECTID, from_table=table, db_cursor=db_cursor)
			storage_list.append(observation)

	def duplicate_other_tables(self, other_tables):

		db_cursor = self.db_conn.cursor()

		for table in other_tables:  # table name = key, field = value

			insert_cursor = self.db_conn.cursor()
			for trec in self.affected_ids[table]:
				sql_query = "select * from %s where ID='%s'" % (table, trec)  # selects the records with this HUC

				# get the contents of the records currently into a list of dicts. Drop the ID fields
				records = funcs.query_to_list_of_dicts(sql_query, db_cursor, ID_drop_fields)

				# to insert new records
				for record in records:  # this is inefficient, we could do this differently
					record[other_tables[table]] = self.destination  # change the HUC
					record[self.changed_flag_field] = "yes"  # add the flag that this field was changed
					query = local_vars.compose_query_from_dict(table, record)
					insert_cursor.execute(query)

			insert_cursor.close()


def huc_change_order(item1, item2):
	"""
		Custom sort function for ensuring that items where the sources and destinations collide end up in the correct order.
		That order is that all of the items with a huc in their source need to be processed before items with that
		same huc as their destination.source

		Unused now. All changes run based on objectid now and so this is defunct
	"""

	if item1.source == item2.destination:
		return -1  # item1 needs to go first
	elif item2.source == item1.destination:
		return 1  # item2 needs to go first
	else:  # same source, no matter, or different but nonconsequential
		return 0


def clear_cache_tables(tables, db_cursor):
	"""
		Empties tables used as a cache in PISCES
	"""

	for table in tables:
		if table.lower() == "layer_cache":
			continue  # it's already cleared in "referesh_layer_cache" below
		query = "delete * from %s" % table
		db_cursor.execute(query)

	funcs.refresh_layer_cache()
	funcs.clean_workspace()


def alter_tables(db_cursor, tables, field):

	for table in tables:
		query = "ALTER TABLE %s ADD COLUMN %s yesno" % (table, field)
		db_cursor.execute(query)
		default_query = "Update %s set %s=no" % (table, field)  # set it as the default - access doesn't let us set defaults in SQL
		db_cursor.execute(default_query)


def load_hucs(db_cursor, table):
	query = "select distinct HUC_12 from %s" % table
	results = db_cursor.execute(query)

	all_hucs = []
	for record in results:
		all_hucs.append(record.HUC_12)

	return all_hucs


def copy_new_layer(new_layer_path, old_layer, rename_old_to):

	arcpy.CopyFeatures_management(old_layer, rename_old_to)  # copy the old one to the new location

	arcpy.env.overwriteOutput = True
	arcpy.CopyFeatures_management(new_layer_path, old_layer)  # overwrite the old one with the new one
	arcpy.env.overwriteOutput = False


def find_new_huc12s(db_cursor, old_table, new_table):

	all_new_hucs = load_hucs(db_cursor, new_table)
	old_hucs = load_hucs(db_cursor, old_table)

	log.write("%s old HUCs, %s new HUCs" % (len(old_hucs), len(all_new_hucs)), 1)

	new_hucs = list(set(all_new_hucs) - set(old_hucs))
	removed_hucs = list(set(old_hucs) - set(all_new_hucs))

	return new_hucs, all_new_hucs, removed_hucs


def create_new_huc12_records(tables, huc_12s, db_cursor):
	"""
		Inserts all of the HUC12s identified as being new
	"""

	for table in tables:
		query = "insert into %s (%s) values (?)" % (table, tables[table])
		for huc in huc_12s:
			try:
				db_cursor.execute(query, huc)  # TODO: Sort of. This doesnt' flag the records in zones_aux as being created this way
			except pyodbc.IntegrityError:
				pass  # skip because if we already have it, we are ok.


def verify(source_hucs, obs_master_tables, other_tables, removed_hucs, new_hucs, db_cursor):

	all_tables = dict(obs_master_tables.items() + other_tables.items())
	for table in all_tables:
		query = "select count(*) as record_count from %s where %s=?" % (table, all_tables[table])

		problem_hucs = 0
		for item in removed_hucs:  # these huc12s should now be gone
			number_matching = db_cursor.execute(query, item).fetchone().record_count
			if number_matching != 0:
				problem_hucs += 1
				log.write("ERROR: HUC_12 ID %s should not exist anymore in %s, but does (count=%s)" % (item, table, number_matching), 1)

		log.write("Total incorrectly converted HUCs in %s: %s" % (table, problem_hucs), 1)


def write_species_changes(dataset_id, db_cursor, species_outfile):
	local_vars.get_species_data()  # set up the all_fish object
	affected_species = funcs.get_species_in_dataset(dataset_id, db_cursor)
	species_out = open(species_outfile, 'wb')
	csv_writer = csv.DictWriter(species_out, ("code", "common_name"))
	csv_writer.writeheader()
	for species in affected_species:
		csv_writer.writerow({"code": species, "common_name": local_vars.all_fish[species].species, })
	species_out.close()


def write_changes_file(l_migrations, new_hucs, extirpated, changes_outfile, new_output_file, removed_output_file, dataset_id, species_outfile, db_cursor):

	#### Write out the migrations made ####
	migration_output_items = []
	for item in l_migrations:
		for obs in list(item.observations + item.invalid_observations):
			out_item = {
				'OBJECTID': obs.objectid,
				'from_huc': item.source,
				'Zone_ID': item.destination,
				'Table': obs.table_used,
			}
			migration_output_items.append(out_item)

	csv_file = open(changes_outfile, 'wb')
	csv_writer = csv.DictWriter(csv_file, ('OBJECTID', 'from_huc', 'Zone_ID', 'Table'))
	csv_writer.writeheader()
	csv_writer.writerows(migration_output_items)
	csv_file.close()

	#### Write out new HUCs ####
	new_outfile = open(new_output_file, 'w')
	new_outfile.write("New HUC12")
	for huc in new_hucs:
		new_outfile.write("%s\r\n" % huc)
	new_outfile.close()

	#### Write out extirpated HUCs ####
	old_outfile = open(removed_output_file, 'w')
	old_outfile.write("Removed HUC12\r\n")
	for huc in extirpated:
		old_outfile.write("%s\r\n" % huc)
	old_outfile.close()

	write_species_changes(dataset_id, db_cursor, species_outfile)


def run_data_unit_tests(tests):

	for module in tests:
		results = unittest.TestResult()
		loader = unittest.defaultTestLoader
		test_suite = loader.loadTestsFromModule(module)
		test_suite.run(results)

		if results.wasSuccessful():
			log.write("Unit Tests passed! Please see other log messages for further instructions", 1)
		else:
			log.write("Unit Tests FAILED! Results follow", 1)
			for failure in results.failures:
				log.write(failure[1], 1)

if __name__ == "__main__":
	if not arcpy.Exists(new_layer):
		log.write("New layer does not exist! Please check your settings")
		sys.exit()

	master_cursor, master_db_conn = funcs.db_connect(local_vars.maindb, "Finding HUC12s affected in migration")

	log.write("Loading migrations and finding affected database records", 1)
	load_migrations(migs_file, primary_key, secondary_key, migration_items)  # load the data from the migrations file

	log.write("Altering tables", 1)
	collection_id = funcs.create_collection(name='HUC 12 Update - Oct 2013', short_name='hucupdate2013', description='Records all of the Observations affected by the HUC12 Update', db_cursor=master_cursor)
	log.write("Collection ID for modified records is %s" % collection_id, 1)
	alter_tables(master_cursor, additional_tables, other_tables_field)
	log.write("Finding affected records and loading data", 1)
	changes, source_hucs_only = find_affected(migration_items, changes, collection_id, other_tables_field, additional_tables, master_db_conn)  # split out the data into objects, loading the affected data. Split into "to create" and "to update" objects

	log.write("Updating database", 1)
	for item in changes:
		item.update(additional_tables)

	master_db_conn.commit()  # commit changes - only commit when everything is done. This is an all or nothing transaction. Closing early so can copy over new layer without a schema lock
	funcs.db_close(master_cursor, master_db_conn)

	log.write("Copying over new layer", 1)
	copy_new_layer(new_layer, local_vars.HUCS, os.path.join(local_vars.maindb, "HUCs", old_layer_name))

	master_cursor, master_db_conn = funcs.db_connect(local_vars.maindb, "Finding HUC12s affected in migration")  # reopen cursor for data checks.
	log.write("Determining new HUC12s and 'extirpated' HUC12s", 1)
	new_hucs_added, new_hucs, extirpated_hucs = find_new_huc12s(master_cursor, old_table=old_layer_name, new_table=local_vars.zones_table, )
	create_new_huc12_records(additional_tables, new_hucs, master_cursor)  # passing in new_hucs instead of new_hucs_added because we want it to try to create one for EVERY new huc item, and it'll silently fail if it already exists.

	log.write("The following HUC12s no longer exist: %s" % str(extirpated_hucs), 1)

	log.write("Clearing caches and verifying", 1)
	clear_cache_tables(clear_tables, master_cursor)
	verify(source_hucs_only, master_tables, additional_tables, extirpated_hucs, new_hucs_added, master_cursor)

	log.write("Writing out Observations changes to %s" % changes_output_file, 1)
	write_changes_file(changes, new_hucs_added, extirpated_hucs, changes_output_file, new_hucs_output_file, removed_hucs_output_file, collection_id, species_outfile=changed_species_output_file, db_cursor=master_cursor)

	master_db_conn.commit()  # commit changes - only commit when everything is done. This is an all or nothing transaction. Closing early so can copy over new layer without a schema lock

	log.write("Running Unit Tests", 1)
	run_data_unit_tests(test_modules)  # runs after committing because they create their own cursor

	funcs.db_close(master_cursor, master_db_conn)
	log.write("Translation complete. Please now run a full output from PISCES and compare it to the previous version using the scripted tools", 1)
