import arcpy, sys, os
import string



def remove_dataset(set_id, invalidate=1):

	if invalidate == 1:  # if we just want to invalidate the whole set, not nuke it into oblivion
		import tbx_modify_records
		tbx_modify_records.invalidate_records("Set_ID = %s" % set_id)
	else: # we want it gone
		query1 = "delete from observation_sets where set_id = ?"
		query2 = "delete from observations where set_id = ?"
