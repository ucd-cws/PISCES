"""
	This code handles most of the analysis that was done for Santos et al, 2014 - it determines percent overlap of PISCES ranges with Moyle and Randall 1998 ranges,
	along with other metrics. Likely won't work with modern PISCES, but who knows
	-Nick, 12/21/2018
"""


import csv
import os
import traceback

import arcpy

cur_cwd = os.getcwd()
from PISCES import local_vars, funcs
from PISCES import mapping

from code_library.common import geospatial

local_vars.set_workspace_vars(funcs.get_path())
print local_vars.maindb
db_cursor,db_conn = funcs.db_connect(local_vars.maindb)

#obs_sets = [1,2,3,4,6,7,9,12,13,14,15,16,17,18,20,21,22,24,25,26,27,29,30,31,32,33,34,37,38,39,40,41,42,43,44,45,46,47,48,49,84,85,86,87,88,89,90,91,92,93,94,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,166,167,168,169,170,171,172,173,227,228]


obs_sets = [88,107,124,91,112,100,128,102,129,115,122,20,171,135,98,136,85,133,142,]

set_species = {}
myresults = []
ranges_init = {}
ranges_final = {}

class data_query:
	def __init__(self,t_query = None):
		self.query = t_query
		self.takes = None
		self.result = None
		self.param_count = 1

# just the valid area		
a = data_query("SELECT Sum(Shape_Area) AS select_me FROM (SELECT DISTINCT HUC_12, Shape_Area FROM HUC12FullState, Observations WHERE Observations.Set_ID=? and Observations.Presence_Type in (1,3,6,7,9) and HUC12FullState.HUC_12=Observations.Zone_ID)")
a.takes = "set_id"
a.result = "mr_huc_area"

# now, just the invalid area
b = data_query("SELECT Sum(Shape_Area) AS select_me FROM (SELECT DISTINCT HUC_12, Shape_Area FROM HUC12FullState, Invalid_Observations WHERE Invalid_Observations.Set_ID=? and Invalid_Observations.Presence_Type in (1,3,6,7,9) and HUC12FullState.HUC_12=Invalid_Observations.Zone_ID and Invalid_Observations.Zone_ID not in (Select Zone_ID from Observations where Observations.Set_ID = ? and Observations.Presence_Type in (1,3,6,7,9)))")
b.takes = "set_id"
b.result = "invalid_mr_area"
b.param_count = 2
c = data_query("select count(*) as select_me FROM (SELECT DISTINCT Zone_ID FROM Observations WHERE Set_ID=? and Presence_Type in (1,3,6,7,9));")
c.takes = "set_id"
c.result = "mr_huc_count"
d = data_query("SELECT count(*) as select_me FROM Observations WHERE Set_ID=? and Presence_Type in (1,3,6,7,9);")
d.takes = "set_id"
d.result = "mr_record_count"
e = data_query("SELECT Sum(Shape_Area) AS select_me  FROM (SELECT DISTINCT HUC_12, Shape_Area FROM HUC12FullState, Observations WHERE HUC12FullState.HUC_12=Observations.Zone_ID And Observations.Species_ID=? And Observations.Presence_Type In (1,3,6,7,9))")
e.takes = "species"
e.result = "pisces_area"
f = data_query("select count(*) as select_me FROM (SELECT DISTINCT Zone_ID FROM Observations WHERE Species_ID=? And Presence_Type In (1,3,6,7,9));")
f.takes = "species"
f.result = "pisces_huc_count"
g = data_query("SELECT sum(Shape_Area) AS Summed_Area FROM (SELECT DISTINCT HUC_12, Shape_Area FROM HUC12FullState, Invalid_Observations WHERE Invalid_Observations.Species_ID = ? and Invalid_Observations.Presence_Type in (1,3,6,7,9) and HUC12FullState.HUC_12=Invalid_Observations.Zone_ID and HUC12FullState.HUC_12 not in (Select * from q_inv_spec_area_7_2))")
g.takes = "species"
g.result = "invalid_pisces_area"
g.param_count = 2

queries = [] #[a,b,c,d,e,f,]

species_query = "select Species, Source_Data from Observation_Sets where Set_ID = ?"

def sum(values): # this would be better handled by numpy, but this is a simple case
	total = 0
	for val in values:
		total += val # assumes no negative values
	return total

def get_dissolved_ranges(initial,species,final,db_cursor):
	# if we didn't pass in a layer name, then just make one right here
	if final is None and species is not None and db_cursor is not None:
		try:
			print "Selecting Zones...",
			selection_type = "NEW_SELECTION" # start a new selection, then add to
			
			# get zones, then select them
			zones_query = "select distinct Zone_ID from Observations where Species_ID = ? and Presence_Type in (1,3,6,7,9)"
			zones_curs = db_cursor.execute(zones_query,species)
			
			zones = []
			for row in zones_curs:
				zones.append(row.Zone_ID)
			
			try:
				arcpy.SelectLayerByAttribute_management(zone_layer,"CLEAR_SELECTION") # we need to do this because if we don't then two layers in a row with the same number of records will result in the second (or third, etc) being skipped because the following line will return the selected number
				if not (int(len(zones)) == int(arcpy.GetCount_management(zone_layer).getOutput(0))): # if they are the same - ie, we are asking to select everything - then skip the selection - this shortcut won't work if we change to allowing portions of a HUC string to select the HUCs
					print "Selecting %s zones" % len(zones),
					zone_expression = "" # the where clause - we want to initialize it to blank
					for index in range(len(zones)): # we have to do this in a loop because building one query to make Arc do it for us produces an error
						zone_expression = zone_expression + "[HUC_12] = '%s' OR " % zones[index] # brackets are required by Arc for Personal Geodatabases (that's us!)
						if (index % 12 == 0 or index == len(zones)-1): # Chunking: every 12th HUC, we run the selection, OR when we've reached the last one. we're trying to chunk the expression. Arc won't take a big long one, but selecting 1 by 1 is slow
							zone_expression = zone_expression[:-4] # chop off the trailing " OR "
							arcpy.SelectLayerByAttribute_management(zone_layer,selection_type,zone_expression)
							selection_type = "ADD_TO_SELECTION" # set it so that selections accumulate
							zone_expression = "" # clear the expression for the next round
			except:
				raise
		except:
			raise

		final = arcpy.CreateUniqueName("layer_copied_%s" % species,local_vars.workspace)
		print "Saving layer"
		arcpy.CopyFeatures_management(zone_layer,final)
	
	try:
		print "Dissolving...",
		dissolved_init = arcpy.CreateUniqueName("layer_dissolve_init_%s" % species,local_vars.workspace)
		arcpy.Dissolve_management(initial,dissolved_init)
		ranges_init[species] = dissolved_init

		dissolved_final = arcpy.CreateUniqueName("layer_dissolve_final_%s" % species,local_vars.workspace)
		arcpy.Dissolve_management(final,dissolved_final)
		ranges_final[species] = dissolved_final
	except:
		print "couldn't dissolve either initial or final"
		raise
	
	return dissolved_init,dissolved_final

def centroid_distance(initial,species,final=None,db_cursor=None):
	if species not in ranges_init or species not in ranges_final:
		dissolved_init,dissolved_final = get_dissolved_ranges(initial,species,final,db_cursor)
	else:
		dissolved_init = ranges_init[species]
		dissplolved_final = ranges_final[species]
		
	print "Centroid Distancing"
	
	try:
		distance_km = geospatial.geometry.simple_centroid_distance(dissolved_init,dissolved_final,geospatial.teale_albers) / 1000
	except:
		print "failed to calculate centroid distance"
		raise
		
	return distance_km
	

def percent_overlap(initial,species,final=None,db_cursor = None):
	"""
	This code has been significantly refined in the code library copy and now returns a dict. Does not generate the ranges though
	:param initial:
	:param species:
	:param final:
	:param db_cursor:
	:return:
	"""

	if not arcpy.Exists(initial):
		print "Dataset doesn't exist"
		return (0,0,0)
	
	dissolved_init,dissolved_final = get_dissolved_ranges(initial,species,final,db_cursor)
	
	try:
		print "Getting area of Initial...",
		total_init_area = geospatial.geometry.get_area(dissolved_init)
				
		print "Getting area of Final...",
		total_final_area = geospatial.geometry.get_area(dissolved_final)
	except:
		print "Couldn't get the areas"
		raise
		
	try:
		print "Intersecting...",
		intersect = arcpy.CreateUniqueName("layer_intersect_%s" % species,local_vars.workspace)
		arcpy.Intersect_analysis([initial,final],intersect)
		
		int_curs = arcpy.SearchCursor(intersect)
		int_areas = []
		for row in int_curs:
			int_areas.append(row.Shape_Area)
		intersect_area = sum(int_areas)
	except:
		print "Couldn't Intersect"
		raise
	
	try:
		print "Unioning...",
		if len(int_areas) > 0: # short circuit - if it's 0, we can return 0 as the value
			union = arcpy.CreateUniqueName("layer_union_%s" % species,local_vars.workspace)
			arcpy.Union_analysis([initial,final],union)
		else:
			# (percent_overlap,int_area,union_area)
			return (0,0,None)
		
		union_curs = arcpy.SearchCursor(union)
		union_areas = []
		for row in union_curs:
			union_areas.append(row.Shape_Area)
		union_area = sum(union_areas)
	except:
		print "couldn't union"
		raise
	
	print "Calculating"
	
	percent_overlap = (float(intersect_area)/float(union_area)) * 100
	overlap_init_perspective = (float(intersect_area)/float(total_init_area)) * 100
	overlap_final_perspective = (float(intersect_area)/float(total_final_area)) * 100
	
	# (percent_overlap,int_area,union_area)
	return (percent_overlap,intersect_area,union_area,overlap_init_perspective,overlap_final_perspective)

	# intersect the two
	# get the area of the intersection
	# if intersection is not 0
	# 	union the two
	#	get area of the union
	# return intersection area over union area



# open the csv file
out_path = os.path.join(cur_cwd,"pisces_stats.csv")
print "Output goes to %s" % out_path
outfile = open(out_path,'wb')
fields = ["species","obs_set","mr_huc_area","invalid_mr_area","mr_huc_count","mr_record_count","pisces_area","pisces_huc_count","invalid_pisces_area","percent_overlap","intersect_area","union_area","overlap_initial_perspective","overlap_final_perspective","centroid_distance_km"]
csv_writer = csv.DictWriter(outfile,fields)

t_row = {} # construct a header row since this is python 2.6
for field in fields:
	t_row[field] = field

# write the header
csv_writer.writerow(t_row)


zone_layer = "z_layer"
arcpy.MakeFeatureLayer_management(local_vars.HUCS,zone_layer)


for cur_set in obs_sets:
	print "obs set = %s" % cur_set
	results = db_cursor.execute(species_query,cur_set)
	row = results.fetchone()
	set_species[cur_set] = row.Species # set the species code for this set
	del results
	
	set_data = row.Source_Data
	set_data = os.path.split(set_data)[1] # strip the beginning off
	set_data = os.path.join(local_vars.observationsdb,set_data)
	
	t_result = {}
	t_result["species"] = set_species[cur_set]
	t_result["obs_set"] = cur_set
	
	q_count = 0
	for query in queries:
		q_count+=1
		print "%s..." % q_count,
		if query.takes == "set_id":
			param = t_result["obs_set"]
		else:
			param = t_result["species"]
		
		if query.param_count == 2:
			results = db_cursor.execute(query.query,param,param)
		else:
			results = db_cursor.execute(query.query,param)
			
		row = results.fetchone()
		t_result[query.result] = row.select_me
	
	t_cursor = db_conn.cursor()
	try:
		pass
		#overlap_items = percent_overlap(set_data,set_species[cur_set],db_cursor = t_cursor)
		#t_result["percent_overlap"] = overlap_items[0]
		#t_result["intersect_area"] = overlap_items[1]
		#t_result["union_area"] = overlap_items[2]
		#t_result["overlap_initial_perspective"] = overlap_items[3]
		#t_result["overlap_final_perspective"] = overlap_items[4]
	except:
		traceback.print_exc()
		print "Couldn't run percent overlap"
	
	try:
		t_result["centroid_distance_km"]=centroid_distance(set_data,set_species[cur_set],db_cursor = t_cursor)
	except:
		traceback.print_exc()
		print "Couldn't run centroid distance"
	
	t_cursor.close()
				
	csv_writer.writerow(t_result)
	myresults.append(t_result)
	print "\n"

outfile.close()