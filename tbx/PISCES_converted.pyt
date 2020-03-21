# -*- coding: utf-8 -*-

import contextlib
import os
import sys
import traceback

import arcpy

from PISCES import local_vars
from PISCES import script_tool_funcs
from PISCES import config_class
from PISCES import funcs
from PISCES import log
from PISCES import mapping

# You can ignore/delete this code; these are basic utility functions to
# streamline porting

@contextlib.contextmanager
def script_run_as(filename, args=None):
    oldpath = sys.path[:]
    oldargv = sys.argv[:]
    newdir = os.path.dirname(filename)
    sys.path = oldpath + [newdir]
    sys.argv = [filename] + [arg.valueAsText for arg in (args or [])]
    oldcwd = os.getcwdu()
    os.chdir(newdir)

    try:
        # Actually run
        yield filename
    finally:
        # Restore old settings
        sys.path = oldpath
        sys.argv = oldargv
        os.chdir(oldcwd)

def set_parameter_as_text(params, index, val):
    if (hasattr(params[index].value, 'value')):
        params[index].value.value = val
    else:
        params[index].value = val

# Export of toolbox C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx

class Toolbox(object):
    def __init__(self):
        self.label = u'PISCES'
        self.alias = ''
        self.tools = [GenerateMap2, addhucattributes2, AddData2, addunique2, generatematrix2, LookUpRecords, Tool78282bf0, SummaryStats, UndoTransaction, ChangeConfig, ImportDataset, RetryImport, AddToCollection]

# Tool implementation code

class GenerateMap2(object):    
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
    
        self.params = parameters
        self.map_field = 0
        self.map_desc_field = 1
        self.lookup_field = 2
        self.storage_field = 3
        self.config_metadata = 10
        self.field_storage = 11
        self.export_shp = 9
        self.export_kml = 8
        self.export_pdf = 7
        self.export_png = 6
        self.export_ddp = 5
        self.export_lyr = 12
        self.blank = ""
        #self.takes_species_args = {}  # make an empty dict - we'll use the maps selection as keys and boolean values so we can turn on and off the boxes
    
        # This all MUST be defined up here because it won't exist when needed otherwise - arc apparently nukes this object between selecting parameters...
        self.map_dict = {}
        maps, map_strings = script_tool_funcs.load_map_sets()
        self.maps = maps
        self.map_dict[''] = "" # define the empty case
        for l_map in maps:
          if l_map.Set_Description is None:
            l_map.Set_Description = "No Description"
          self.map_dict[l_map.Set_Name] = l_map # lets us look up maps later
    
          
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        # reload the modules so that preferences get loaded if they were modified
        reload(config_class.config)
    
        config = config_class.PISCES_Config()
    
        self.params[self.map_desc_field].enabled = False
        self.params[self.map_desc_field].value = ""
        self.params[self.storage_field].value = ""
        self.selected_species = ""
        self.map_dict = {}
        self.old_iterator = "Species_Groups:FID"
    
        self.params[self.export_ddp].value = config.export_ddp
        self.params[self.config_metadata].value = config.export_metadata
        self.params[self.export_shp].value = config.export_shp
        self.params[self.export_kml].value = config.export_kml
        self.params[self.export_pdf].value = config.export_pdf
        self.params[self.export_png].value = config.export_png
        self.params[self.export_lyr].value = config.export_lyr
    
        self.params[6].category = "Export Options"
        self.params[7].category = "Export Options"
        self.params[8].category = "Export Options"
        self.params[9].category = "Export Options"
        self.params[self.export_lyr].category = "Export Options"
    
        self.params[self.field_storage].enabled = False
        self.params[self.field_storage].category = "System"
        
        self.cur_species = {'1':None,'3':None} # dict representing a species field and what the currently selected species is
    
        maps, map_strings = script_tool_funcs.load_map_sets(config.username)
        self.params[self.map_field].filter.list = map_strings
    
        script_tool_funcs.make_species_group_picker(self,self.lookup_field,self.storage_field)
            
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
    
        script_tool_funcs.autocomplete_full_field(self,self.map_field) # complete the map name
    
        # checks the species field for commands
        script_tool_funcs.validate_species(self.params[self.lookup_field]) # runs operations like "load"
    
        #script_tool_funcs.autocomplete_full_field(self,self.lookup_field)
        script_tool_funcs.add_selection(self,self.lookup_field,self.storage_field)
    
        # add map description field
        if self.params[self.map_field].value in self.map_dict.keys() and self.map_dict[self.params[self.map_field].value].Set_Description != self.params[self.map_desc_field].value:  # if the currently selected map isn't already displayed:
            if self.params[self.map_field].value in self.map_dict:
              l_map = self.map_dict[self.params[self.map_field].value]
              self.params[self.map_desc_field].value = "%s - %s" % (l_map.Map_Title,l_map.Set_Description)
          
              if l_map.Iterator:
                self.params[self.lookup_field].enabled = True
                self.params[self.storage_field].enabled = True
    
                # when our iterator changes, switch the picker options and clear the picked options
                script_tool_funcs.switch_iterator_field(l_map.Iterator, self.params[11].value, self, self.lookup_field, self.storage_field)
              else:
                self.params[self.lookup_field].enabled = False
                self.params[self.storage_field].enabled = False
    
              self.params[11].value = l_map.Iterator
    
            else:
              self.params[self.map_desc_field].value = "No Map Description"
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Generate Map'
        self.description = u'Outputs a PISCES map with a few basic available options'
        self.canRunInBackground = False
        self.category = "Output"
		
    def getParameterInfo(self):
        # Map
        param_1 = arcpy.Parameter()
        param_1.name = u'Map'
        param_1.displayName = u'Map'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'
        param_1.filter.list = [u'Last Map Configuration', u'All Diversity', u'Beta Diversity', u'Connectivity', u'Data Gaps', u'Downstream Diversity', u'Genus Range Map', u'HUC8 Richness', u'Highlight Dataset Changes', u'Inset - Range Maps', u'Main Range Maps', u'Main Range Maps 2018', u'Meadows_Richness', u'Modify_Records', u'Native Richness', u'Network Distance', u'NonNative Richness', u'QA Dist', u'Raster', u'Richness Difference', u'SOS II Salmonid Diversity Map', u'SOS Range Maps', u'Sensitive Native Taxa', u'Sensitivity_Metrics', u'Species Richness', u'Status_scores_average', u'Status_zoogeo', u'Streamlines Representation', u'Unlimited Range Maps', u'Watershed Contributing Area', u'ZooGeo Richness']

        # Map_Description
        param_2 = arcpy.Parameter()
        param_2.name = u'Map_Description'
        param_2.displayName = u'Map Description'
        param_2.parameterType = 'Optional'
        param_2.direction = 'Input'
        param_2.datatype = u'String'

        # Generate_map_for_each_of_these_items
        param_3 = arcpy.Parameter()
        param_3.name = u'Generate_map_for_each_of_these_items'
        param_3.displayName = u'Generate map for each of these items'
        param_3.parameterType = 'Optional'
        param_3.direction = 'Input'
        param_3.datatype = u'String'
        param_3.filter.list = [u' ', u'all', u'-----', u'Amphibians', u'Anadromous', u'Arthropods', u'Crustacean', u'Dams_Indicators', u'FSSC_2012', u'Fish', u'Flow_Sensitive', u'Herps', u'Herps_Lentic', u'Herps_Lotic', u'Herps_Lotic_Lentic', u'Invertebrate', u'Meadows_Indicators', u'Mollusks', u'Narrow_25', u'Native_Fish', u'Non_Native_Fish', u'Paper_Species', u'Reptiles', u'Resident_Natives', u'SOS_Species_2016', u'USFS_2017', u'USFS_R5', u'Wide_Ranging', u'-----', u'PXL01 - African Clawed Frog', u'CRO06 - Amargosa Canyon speckled dace', u'CCN02 - Amargosa River pupfish', u'AME01 - Ameletidae family', u'RLC01 - American Bullfrog', u'CAS01 - American Shad', u'AMP01 - Amphizoidae family', u'ANI01 - Anisogammaridae family', u'APA01 - Apataniidae family', u'CTA01 - Aquatic gartersnake', u'STA01 - Arctic grayling', u'RCB01 - Argentine pearlfish', u'GCI01 - Arrow goby', u'BAC02 - Arroyo Toad', u'CGO01 - Arroyo chub', u'ASE01 - Asellidae family', u'AST01 - Astacidae family', u'ATH01 - Athericidae family', u'ATY01 - Atyidae family', u'HPH01 - Baja California Treefrog', u'SSA01 - Barred Pipefish', u'CCK01 - Bigeye marbled sculpin', u'CIC01 - Bigmouth buffalo', u'PPM01 - Bigscale logperch', u'IAM01 - Black bullhead', u'CPN01 - Black crappie', u'BAE01 - Black toad', u'COM02 - Blackfish (bin)', u'BLE01 - Blephariceridae family', u'IIF01 - Blue catfish', u'CGC01 - Blue chub', u'FLG01 - Bluefin killifish', u'CLM02 - Bluegill', u'CGE01 - Bonytail', u'BRA01 - Brachycentridae family', u'SSF01 - Brook Trout', u'GCI02 - Brook stickleback', u'SST01 - Brown Trout', u'IAN02 - Brown bullhead', u'SSC01 - Bull trout', u'CAL01 - Calamoceratidae family', u'SOT04 - California Coast fall Chinook salmon', u'BAB02 - California Toad', u'DDE01 - California giant salamander', u'SOM14 - California golden trout', u'PPC01 - California halibut', u'CFP01 - California killifish', u'STT01 - California newt', u'RRD01 - California red-legged frog', u'CLS01 - California roach', u'AAC01 - California tiger salamander', u'COM03 - California tilapia (hybrid)', u'HPC01 - California tree frog', u'CAP01 - Capniidae family', u'RRC01 - Cascades frog', u'SOM05 - Central California coast winter steelhead', u'SOK01 - Central Coast coho salmon', u'SOT08 - Central Valley fall Chinook salmon', u'SOT07 - Central Valley late fall Chinook salmon', u'SOT06 - Central Valley spring Chinook salmon', u'SOM06 - Central Valley steelhead', u'SOT05 - Central Valley winter Chinook salmon', u'GTT01 - Chameleon goby', u'IIP01 - Channel catfish', u'CTM01 - Checkered gartersnake', u'SOT09 - Chinook Salmon (bin)', u'CHI01 - Chirocephalidae family', u'CHL01 - Chloroperlidae family', u'SOK03 - Chum salmon', u'CLE02 - Clear Lake hitch', u'CCA03 - Clear Lake prickly sculpin', u'CLS04 - Clear Lake roach', u'CPC01 - Clear Lake splittail', u'EHT03 - Clear Lake tule perch', u'SOC01 - Coastal cutthroat trout', u'SSC02 - Coastal dolly varden', u'DDT01 - Coastal giant salamander', u'SOM09 - Coastal rainbow trout', u'AAT02 - Coastal tailed frog', u'GGA01 - Coastal threespine stickleback', u'CCA04 - Coastrange sculpin', u'SOK04 - Coho (bin)', u'SOC05 - Colorado River cutthroat trout', u'CPL01 - Colorado pikeminnow', u'CLG03 - Common Kingsnake', u'CCC01 - Common carp', u'CTS01 - Common gartersnake', u'COR01 - Cordulegastridae family', u'COR02 - Corduliidae family', u'COR03 - Corydalidae family', u'CCS04 - Cottonball Marsh pupfish', u"SSC04 - Couch's spadefoot toad", u'CST03 - Cow Head tui chub', u'CRA01 - Crangonyctidae family', u'SOC04 - Cutthroat trout (bin)', u'PPE01 - Del Norte Salamander', u'OHP01 - Delta smelt', u'CCM02 - Desert pupfish', u'DEU01 - Deuterophlebiidae family', u'PPG01 - Diamond turbot', u'DIX01 - Dixidae family', u'SSC03 - Dolly varden', u"PPD01 - Dunn's salamander", u'SOM12 - Eagle Lake rainbow trout', u'CSB05 - Eagle Lake tui chub', u'ELM01 - Elmidae family', u'CHS01 - Empty data bin - California roach', u'EPH01 - Ephemerellidae family', u'OTP01 - Eulachon', u'EUL01 - Eulichadidae family', u'CPP01 - Fathead minnow', u'CCL02 - Flannelmouth sucker', u'IPO01 - Flathead Catfish', u'RRB01 - Foothill yellow-legged frog', u'CTG01 - Giant gartersnake', u'GLO01 - Glossosomatidae family', u'GOE01 - Goeridae family', u'CNC01 - Golden shiner', u'CCA05 - Goldfish', u'PET02 - Goose Lake lamprey', u'SOM11 - Goose Lake redband trout', u'CCO02 - Goose Lake sucker', u'CST01 - Goose Lake tui chub', u'CCI01 - Grass carp', u'SSI01 - Great Basin spadefoot', u'BAC03 - Great Plains toad', u'CLC01 - Green sunfish', u'PXH01 - Green swordtail', u'CLP01 - Gualala roach', u'PPR01 - Guppy', u'CMC01 - Hardhead', u'HEL01 - Helicopsychidae family', u'HEP01 - Heptageniidae family', u'CSB02 - High Rock Springs tui chub', u'CLE04 - Hitch (bin)', u'CCO04 - Humboldt sucker', u'HYD01 - Hydrobiidae family', u'MMB01 - Inland silverside', u'GGA02 - Inland threespine stickleback', u'PBC01 - Inyo Mountains salamander', u'ISO01 - Isonychiidae family', u'CLS09 - Kaweah roach', u'SOM13 - Kern River rainbow trout', u'PLH01 - Kern brook lamprey', u'SOM04 - Klamath Mountains Province summer steelhead', u'SOM03 - Klamath Mountains Province winter steelhead', u'PES01 - Klamath River lamprey', u'CCP04 - Klamath lake sculpin', u'CCS01 - Klamath largescale sucker', u'CCR01 - Klamath smallscale sucker', u'CRO03 - Klamath speckled dace', u'CSB01 - Klamath tui chub', u'SOC03 - Lahontan cutthroat trout', u'CSB03 - Lahontan lake tui chub', u'CCP01 - Lahontan mountain sucker', u'CRE01 - Lahontan redside', u'CRO02 - Lahontan speckled dace', u'CSB04 - Lahontan stream tui chub', u'SSN01 - Lake trout', u'CMS01 - Largemouth Bass', u'LEP01 - Lepidostomatidae family', u'LEU01 - Leuctridae family', u'LIM01 - Limnephilidae family', u'SOM15 - Little Kern golden trout', u'CRO05 - Long Valley speckled dace', u'AAM03 - Long-toed Salamander', u'OST01 - Longfin smelt', u'GGM01 - Longjaw mudsucker', u'GCS01 - Longtail goby', u'CCL01 - Lost River sucker', u'CCK02 - Lower Klamath marbled sculpin', u'LUT01 - Lutrochidae family', u'LYM01 - Lymnaeidae family', u'MAC01 - Macromiidae family', u'CCK04 - Marbled Sculpin (bin)', u'MAR01 - Margaritiferidae family', u'SOM10 - McCloud River redband trout', u'MMB02 - Mississippi silversides', u'CCM01 - Modoc sucker', u'CSM01 - Mojave tui chub', u'CLE03 - Monterey hitch', u'CCO03 - Monterey sucker', u'SPW01 - Mountain whitefish', u'CLS06 - Navarro roach', u'NEM01 - Nemouridae family', u'AEC01 - Northern Alligator Lizard', u'PEF01 - Northern California brook lamprey', u'SOM02 - Northern California coast summer steelhead', u'SOM01 - Northern California coast winter steelhead', u'CLS03 - Northern coastal roach', u'AAM01 - Northern green sturgeon', u'RRP01 - Northern leopard frog', u'RRA01 - Northern red-legged frog', u'CLS08 - Northern roach', u'CTO01 - Northwestern gartersnake', u'AAG01 - Northwestern salamander', u'ODO01 - Odontoceridae family', u'RRP02 - Oregon spotted frog', u'CCR02 - Owens pupfish', u'CRO04 - Owens speckled dace', u'CCF01 - Owens sucker', u'CSB06 - Owens tui chub', u'PLP01 - Pacific brook lamprey', u'HPR01 - Pacific chorus frog', u'CCH01 - Pacific herring', u'PET01 - Pacific lamprey', u'SOC02 - Paiute cutthroat trout', u'CCB02 - Paiute sculpin', u'PEL01 - Peltoperlidae family', u'PER01 - Perlidae family', u'PER02 - Perlodidae family', u'PET03 - Petaluridae family', u'PHI01 - Philopotamidae family', u'PHR01 - Phryganeidae family', u'SOG01 - Pink salmon', u'CST02 - Pit River tui chub', u'CCP02 - Pit sculpin', u'PLL01 - Pit-Klamath brook lamprey', u'PLE01 - Pleuroceridae family', u'PPG02 - Porthole livebearer', u'CCA02 - Prickly sculpin', u'PSY01 - Psychomyiidae family', u'PTE01 - Pteronarcyidae family', u'PTI01 - Ptilodactylidae family', u'CLG01 - Pumpkinseed', u'SOM17 - Rainbow Trout (Summer Steelhead)', u'SOM18 - Rainbow Trout (Winter Steelhead)', u'FLP01 - Rainwater killifish ', u'CXT01 - Razorback sucker', u'CLS02 - Red Hills roach', u'CCL03 - Red shiner', u'STR01 - Red-bellied newt', u'BAP01 - Red-spotted toad', u'SOM16 - Redband trout (bin)', u'CTZ01 - Redbelly tilapia', u'CLM03 - Redear sunfish', u'CMC02 - Redeye bass', u'CCP03 - Reticulate sculpin', u'RHY01 - Rhyacophilidae family', u'CCG01 - Riffle sculpin', u'PLA01 - River lamprey', u'CCA01 - Rough sculpin', u'STG01 - Rough-skinned newt', u'EHT02 - Russian River tule perch', u'COM01 - Sacramento blackfish', u'CLE01 - Sacramento hitch', u'CAI01 - Sacramento perch', u'CPG01 - Sacramento pikeminnow', u'CRO01 - Sacramento speckled dace', u'CPM01 - Sacramento splittail', u'CCO01 - Sacramento sucker', u'EHT01 - Sacramento tule perch', u'PPL01 - Sailfin molly', u'CCS03 - Salt Creek pupfish', u'CTS02 - San Francisco Gartersnake', u'CRO07 - Santa Ana speckled dace', u'CCS02 - Santa Ana sucker', u'PAN01 - Santa Cruz Black Salamander', u'AAM04 - Santa Cruz long-toed Salamander', u'CCN01 - Saratoga Springs pupfish', u'SCI01 - Scirtidae family', u'CCX01 - Sculpin spp (bin)', u'SER01 - Sericostomatidae family', u'CCA06 - Sharpnose sculpin', u'PAI01 - Shasta Black Salamander', u'GGA04 - Shay Creek stickleback', u'GTB01 - Shimofuri goby', u'ECA01 - Shiner perch', u'SCP01 - Shortfin corvina', u'PPM02 - Shortfin molly', u'CCB01 - Shortnose sucker', u'CCN04 - Shoshone pupfish', u'RRM01 - Sierra Madre yellow-legged frog', u'RRS01 - Sierra Nevada yellow-legged frog', u'CTC01 - Sierra gartersnake', u'STS01 - Sierra newt', u'HPS01 - Sierran Treefrog', u'PPS02 - Siskiyou Mountains Salamander', u'CCT02 - Slender sculpin', u'CMD01 - Smallmouth Bass', u'SON01 - Sockeye (Kokanee) Salmon', u'SOM07 - South Central California coast steelhead', u'CTS03 - South Coast Gartersnake', u'AEC02 - Southern Alligator Lizard', u'SOM08 - Southern California steelhead', u'SOK02 - Southern Oregon Northern California coast coho salmon', u'SOT03 - Southern Oregon Northern California coast fall Chinook salmon', u'CLS05 - Southern coastal roach', u'AAM02 - Southern green sturgeon', u'RRV01 - Southern torrent salamander', u'PAF01 - Speckled Black Salamander', u'CRO08 - Speckled Dace (bin)', u'SPH01 - Sphaeriidae family', u'CMP01 - Spotted bass', u'CLA01 - Staghorn sculpin', u'PPS01 - Starry flounder', u'SOM19 - Stocked Rainbow Trout (bin)', u'MMS01 - Striped bass', u'MMC02 - Striped mullet', u'OHP02 - Surf smelt', u'TAE01 - Taeniopterygidae family', u'CCT01 - Tahoe sucker', u'TAN01 - Tanyderidae family', u'CCN03 - Tecopa pupfish', u'CTT01 - Tench', u'CSC01 - Thicktail chub', u'CDP01 - Threadfin shad', u'GGA05 - Threespine stickleback (bin)', u'GEN01 - Tidewater goby', u'CLS07 - Tomales roach', u'AAA01 - Topsmelt', u'CSB07 - Tui chub bin', u'EHT04 - Tule perch (bin)', u'CTH01 - Twp-striped gartersnake', u'UEN01 - Uenoidae family', u'GGA03 - Unarmored threespine stickleback', u'UNI01 - Unionidae family', u'CCK03 - Upper Klamath marbled sculpin', u'SOT01 - Upper Klamath-Trinity fall Chinook salmon', u'SOT02 - Upper Klamath-Trinity spring Chinook salmon', u'OHN01 - Wakasagi', u'PAV01 - Wandering Salamander', u'CLG02 - Warmouth', u'EAM01 - Western Pond Turtle', u'PLR01 - Western brook lamprey', u'PGA01 - Western mosquitofish', u'EEM01 - Western pond turtle', u'SSH01 - Western spadefoot toad', u'CTE01 - Western terrestrial gartersnake', u'BAB01 - Western toad', u'MMC01 - White bass', u'IAC01 - White catfish', u'CPA01 - White crappie', u'AAT01 - White sturgeon', u"BAW01 - Woodhouse's toad", u'IAN01 - Yellow bullhead', u'PPF01 - Yellow perch', u'GAF01 - Yellowfin goby', u'BAC01 - Yosemite Toad', u'ZZZ01 - temp']

        # Generate_map_for_each_of_these_items_Holder
        param_4 = arcpy.Parameter()
        param_4.name = u'Generate_map_for_each_of_these_items_Holder'
        param_4.displayName = u'Generate map for each of these items Holder'
        param_4.parameterType = 'Optional'
        param_4.direction = 'Input'
        param_4.datatype = u'String'
        param_4.multiValue = True

        # Open_MXD_when_complete
        param_5 = arcpy.Parameter()
        param_5.name = u'Open_MXD_when_complete'
        param_5.displayName = u'Open MXD when complete'
        param_5.parameterType = 'Optional'
        param_5.direction = 'Input'
        param_5.datatype = u'Boolean'
        param_5.value = u'false'

        # Export_Data_Driven_Pages
        param_6 = arcpy.Parameter()
        param_6.name = u'Export_Data_Driven_Pages'
        param_6.displayName = u'Export Data Driven Pages'
        param_6.parameterType = 'Optional'
        param_6.direction = 'Input'
        param_6.datatype = u'Boolean'
        param_6.value = u'false'

        # Export_PNG
        param_7 = arcpy.Parameter()
        param_7.name = u'Export_PNG'
        param_7.displayName = u'Export PNG'
        param_7.parameterType = 'Optional'
        param_7.direction = 'Input'
        param_7.datatype = u'Boolean'
        param_7.value = u'true'

        # Export_PDF
        param_8 = arcpy.Parameter()
        param_8.name = u'Export_PDF'
        param_8.displayName = u'Export PDF'
        param_8.parameterType = 'Optional'
        param_8.direction = 'Input'
        param_8.datatype = u'Boolean'
        param_8.value = u'false'

        # Export_KML_of_each_layer
        param_9 = arcpy.Parameter()
        param_9.name = u'Export_KML_of_each_layer'
        param_9.displayName = u'Export KML of each layer'
        param_9.parameterType = 'Optional'
        param_9.direction = 'Input'
        param_9.datatype = u'Boolean'
        param_9.value = u'false'

        # Export_SHP_of_each_layer
        param_10 = arcpy.Parameter()
        param_10.name = u'Export_SHP_of_each_layer'
        param_10.displayName = u'Export SHP of each layer'
        param_10.parameterType = 'Optional'
        param_10.direction = 'Input'
        param_10.datatype = u'Boolean'
        param_10.value = u'false'

        # Generate_Metadata__when_configured_
        param_11 = arcpy.Parameter()
        param_11.name = u'Generate_Metadata__when_configured_'
        param_11.displayName = u'Generate Metadata (when configured)'
        param_11.parameterType = 'Optional'
        param_11.direction = 'Input'
        param_11.datatype = u'Boolean'
        param_11.value = u'false'

        # Iterator
        param_12 = arcpy.Parameter()
        param_12.name = u'Iterator'
        param_12.displayName = u'Iterator'
        param_12.parameterType = 'Optional'
        param_12.direction = 'Input'
        param_12.datatype = u'String'
        param_12.value = u'[None]'

        # Export_Layer_Package_of_each_layer
        param_13 = arcpy.Parameter()
        param_13.name = u'Export_Layer_Package_of_each_layer'
        param_13.displayName = u'Export Layer Package of each layer'
        param_13.parameterType = 'Optional'
        param_13.direction = 'Input'
        param_13.datatype = u'Boolean'
        param_13.value = u'false'

        return [param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9, param_10, param_11, param_12, param_13]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_generate_map.py'):

            local_vars.start(arc_script=1)
            
            map_name = parameters[0].valueAsText
            # 1 is a description holder and 2 is the selection for the groups
            config_species_and_groups_list = parameters[3].valueAsText
            config_auto_open = parameters[4]
            
            config_output_ddp = parameters[5]
            config_output_png = parameters[6]
            config_output_pdf = parameters[7]
            config_output_kml = parameters[8]
            config_output_shp = parameters[9]
            config_export_metadata = parameters[10]
            config_output_lyr = parameters[12]
            config_iterator = parameters[11].valueAsText
            
            arcmap_layers, running_in_arcmap = script_tool_funcs.deactivate_map("CURRENT")
            
            try:
                if map_name != "Last Map Configuration":  # If we haven't specified to keep everything the way it is.
                    # takes the string and separates it out into individual items,
                    #  extracting the species from their "code - common name" form
                    # if it's not using the standard species and groups picker, then don't do this behavior because it's not expecting a species.
                    if config_iterator.lower() in ("species_groups:fid", "species:fid"):
                        config_species_list = funcs.parse_multi_species_group_list(config_species_and_groups_list)
                    else:  # not expecting a species - just make a list from the input
                        config_species_list = config_species_and_groups_list.split(";")
            
                    # connect to the DB
                    db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "exporting maps from script tool")
            
                    # disable all maps
                    disable_maps_query = "update %s set active=%s" % (local_vars.maps_table, local_vars.db_false)
                    db_cursor.execute(disable_maps_query)
            
                    # enable the relevant one
                    enable_correct_map_query = "update %s set active=%s where set_name='%s'" % (local_vars.maps_table, local_vars.db_true, map_name)
                    db_cursor.execute(enable_correct_map_query)
                    db_conn.commit()  # commit the changes
            
                    # get the map id
                    map_id_query = "select id from %s where set_name='%s'" % (local_vars.maps_table, map_name)
                    map_id = db_cursor.execute(map_id_query).fetchone().id
            
                    log.write("Map ID: %s" % map_id, True)
                    if not map_id:
                        log.error("Couldn't find Map ID for selected map")
                        raise ValueError("Couldn't find Map ID for selected map")
            
                    # delete all existing bind for the map
                    remove_bind_query = "delete from %s where query_set_id = %s" % (local_vars.bind_vals_table, map_id)
                    db_cursor.execute(remove_bind_query)
            
                    if config_iterator is not None and config_iterator != "" and len(config_species_list) > 0:  # if we have an iterator and we have items from it
                        # insert the new species records
                        insert_bind_query = "insert into %s (query_set_id, bind_value) values (%s, ?)" % (local_vars.bind_vals_table, map_id)
                        for species in config_species_list:
                            db_cursor.execute(insert_bind_query, species)
            
                    # commit the changes again
                    db_conn.commit()
                    funcs.db_close(db_cursor, db_conn)
            
                # set some mapping variables
                mapping.export_mxd = True
            
                mapping.export_pdf = config_output_pdf
                mapping.export_png = config_output_png
                mapping.export_ddp = config_output_ddp
                mapping.export_web_layer_kml = config_output_kml  # setting either of these two to True will greatly increase processing time
                mapping.export_web_layer_shp = config_output_shp
                mapping.config_metadata = config_export_metadata
                mapping.export_web_layer_lyr = config_output_lyr
            
                # execute the map
                map_objects = mapping.begin("all", return_maps=True)  # run the maps and get the objects
            
                if config_auto_open:  # if we should auto-open it
                    if map_objects and len(map_objects) == 1:  # if we have just one map, try to auto-open
                        l_map = map_objects[0]  # the resulting map
            
                        if l_map.mxd_path is not None and os.path.exists(l_map.mxd_path):
                            log.write("Opening MXD", 1)
                            os.startfile(l_map.mxd_path)  # subprocess.call([os.path.join(install_dir, "Bin", "ArcMap.exe"), ]) # call arcmap with the mxd
                        else:
                            log.warning("A map document was not created, likely because there wasn't data for your requested mapset and species.")
                    elif not map_objects or (map_objects and len(map_objects) == 0):  # no maps!
                        log.error("Failed to output map - See error message above")
                    else:  # otherwise, it's too many maps - don't want to open 20 maps, etc
                        log.warning("Too many maps to open - please open them manually out of the mxds/output directory of your PISCES"
                                    "install folder")
            except:
                raise
            finally:  # regardless of what happens, turn their map layers back on
                script_tool_funcs.reactivate_map("CURRENT", arcmap_layers, running_in_arcmap)
            
            

class addhucattributes2(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Input\addhucattributes2"""
    def __init__(self):
        self.label = u'Add HUC12 Attributes'
        self.canRunInBackground = False
        self.category = "Input"
		
    def getParameterInfo(self):
        # HUCs
        param_1 = arcpy.Parameter()
        param_1.name = u'HUCs'
        param_1.displayName = u'HUCs'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'Feature Layer'

        # Attribute_Name
        param_2 = arcpy.Parameter()
        param_2.name = u'Attribute_Name'
        param_2.displayName = u'Attribute Name'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'

        # Input_Attribute_Name
        param_3 = arcpy.Parameter()
        param_3.name = u'Input_Attribute_Name'
        param_3.displayName = u'Input Attribute Name'
        param_3.parameterType = 'Optional'
        param_3.direction = 'Input'
        param_3.datatype = u'Field'

        return [param_1, param_2, param_3]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_add_huc_att.py'):
            import sys
            import os
            
            import arcpy
            
            from PISCES import funcs
            from PISCES import local_vars
            from PISCES import log
            from PISCES import script_tool_funcs
            
            local_vars.start(arc_script=True)
            
            # get the args
            hucs_layer = parameters[0].valueAsText
            field_name = parameters[1].valueAsText
            input_field_name = parameters[2].valueAsText # the name of the field in the input data that contains the value to look at - only used in non-boolean cases
            
            # get the hucs as a list
            list_of_hucs = funcs.hucs_to_list(hucs_layer)
            
            if not list_of_hucs:
                log.error("No HUCs - exiting")
                sys.exit()
            
            if not field_name:
                log.error("No field to add - exiting")
                sys.exit()
            
            # check if the field already exists - using arcpy to check, but we'll alter the table with a query because Arc doesn't have a boolean datatype
            cur_table = os.path.join(local_vars.maindb, local_vars.zones_aux)
            
            log.write("Adding field if necessary", True)
            desc = arcpy.Describe(cur_table)
            
            db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
            for field in desc.fields:  # desc contains zones_aux, not the passed in layer
                # probably better done with a lambda
                if field_name == field.name:
                    new_col = False
                    break
            else:
                # then we need to add it
                # TODO: This tool won't work until we fix this alter table query to be compatible with SQLite
                query = "ALTER TABLE zones_aux ADD COLUMN %s INTEGER" % field_name
                results = db_cursor.execute(query)
                new_col = True
            
            del desc
            
            log.write("Updating data", True)
            
            if new_col: # right now we can only process boolean in new columns. We'll need to fix this in the future.
                # set it all to False
                query = "update %s set %s=%s" % (local_vars.zones_aux, field_name, local_vars.db_false)
                results = db_cursor.execute(query)
            
                # now set specific ones to true
                query = "update %s set %s=%s where Zone=?" % (local_vars.zones_aux, field_name, local_vars.db_true)
                for huc in list_of_hucs:
                    results = db_cursor.execute(query, huc)
            else:
                t_curs = arcpy.SearchCursor(hucs_layer)
            
                query = "update %s set %s=? where zone=?" % (local_vars.zones_aux, field_name)
                for huc in t_curs:
                    results = db_cursor.execute(query, huc.getValue(input_field_name), huc.getValue(local_vars.huc_field))
            
            db_conn.commit()  # commit the change
            funcs.db_close(db_cursor, db_conn)
            log.write("Complete", True)
            

class AddData2(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Modification\AddData2"""
    import arcpy
    import os, sys
    from PISCES import local_vars
    from PISCES import script_tool_funcs
    from PISCES import config
    
    reload(config)  # make sure it's current if they changed it during this session
    
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
        self.blank = ""
        self.obs_box = 9
            
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        self.cur_species = {'1':None,'3':None} # dict representing a species field and what the currently selected species is
    
        try:
          l_fish = script_tool_funcs.get_fish_filter()
        except:
          l_fish = []
          
        if len(self.params) > 3: # stupid arcgis fix because it won't validate otherwise
            self.params[0].value = "HUC12s"
            self.params[1].filter.list = l_fish
            self.params[1].value = ""
            self.params[2].filter.list = ["Add","Transfer","Remove"]
            self.params[2].value = "Add"
            self.params[3].filter.list = l_fish
            self.params[3].enabled = False
    
        if len(self.params) > 7: # another stupid arcgis fix because it won't validate otherwise
            script_tool_funcs.get_input_filter_picker(self, 6)
            #self.params[6].value = "18 - MQB - Moyle and Quinones"
            self.params[6].category = "Adding Observations Advanced Options"
            self.params[7].filter.list = ["auto"]
            self.params[7].value = "auto"
            self.params[7].category = "Adding Observations Advanced Options"
    
        script_tool_funcs.make_obs_type_picker(self, self.obs_box)
    
        self.check_subset_and_obs_boxes()
    
        script_tool_funcs.set_default_IF_for_addition(config.username, self, 6)
        
        return
        
      def check_subset_and_obs_boxes(self):
        if self.params[2].value == "Transfer" or self.params[2].value == "Remove":
          self.params[5].enabled = True
          self.params[self.obs_box].enabled = False
        elif self.params[2].value == "Add":
          self.params[5].enabled = False
          self.params[self.obs_box].enabled = True
        else:
          self.params[5].enabled == True  # in case something new gets added later, just make it enabled
          self.params[self.obs_box].enabled = True
        
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
    
        if self.params[2].value == "Transfer":
          self.params[3].enabled = True
        else:
          self.params[3].enabled = False
    
        self.check_subset_and_obs_boxes()
    
        # checks the species field for commands
        script_tool_funcs.validate_species(self.params[1])
    
        script_tool_funcs.autocomplete_full_field(self,1)
        if self.params[3].enabled is True:
          script_tool_funcs.autocomplete_full_field(self,3)
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    
    def __init__(self):
        self.label = u'Add or Modify Data'
        self.canRunInBackground = False
        self.category = "Modification"
		
    def getParameterInfo(self):
        # Zones
        param_1 = arcpy.Parameter()
        param_1.name = u'Zones'
        param_1.displayName = u'Zones'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'Feature Layer'
        param_1.value = u'HUC12s'

        # Species
        param_2 = arcpy.Parameter()
        param_2.name = u'Species'
        param_2.displayName = u'Species'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'
        param_2.filter.list = [u'PXL01 - African Clawed Frog', u'CRO06 - Amargosa Canyon speckled dace', u'CCN02 - Amargosa River pupfish', u'AME01 - Ameletidae family', u'RLC01 - American Bullfrog', u'CAS01 - American Shad', u'AMP01 - Amphizoidae family', u'ANI01 - Anisogammaridae family', u'APA01 - Apataniidae family', u'CTA01 - Aquatic gartersnake', u'STA01 - Arctic grayling', u'RCB01 - Argentine pearlfish', u'GCI01 - Arrow goby', u'BAC02 - Arroyo Toad', u'CGO01 - Arroyo chub', u'ASE01 - Asellidae family', u'AST01 - Astacidae family', u'ATH01 - Athericidae family', u'ATY01 - Atyidae family', u'HPH01 - Baja California Treefrog', u'SSA01 - Barred Pipefish', u'CCK01 - Bigeye marbled sculpin', u'CIC01 - Bigmouth buffalo', u'PPM01 - Bigscale logperch', u'IAM01 - Black bullhead', u'CPN01 - Black crappie', u'BAE01 - Black toad', u'COM02 - Blackfish (bin)', u'BLE01 - Blephariceridae family', u'IIF01 - Blue catfish', u'CGC01 - Blue chub', u'FLG01 - Bluefin killifish', u'CLM02 - Bluegill', u'CGE01 - Bonytail', u'BRA01 - Brachycentridae family', u'SSF01 - Brook Trout', u'GCI02 - Brook stickleback', u'SST01 - Brown Trout', u'IAN02 - Brown bullhead', u'SSC01 - Bull trout', u'CAL01 - Calamoceratidae family', u'SOT04 - California Coast fall Chinook salmon', u'BAB02 - California Toad', u'DDE01 - California giant salamander', u'SOM14 - California golden trout', u'PPC01 - California halibut', u'CFP01 - California killifish', u'STT01 - California newt', u'RRD01 - California red-legged frog', u'CLS01 - California roach', u'AAC01 - California tiger salamander', u'COM03 - California tilapia (hybrid)', u'HPC01 - California tree frog', u'CAP01 - Capniidae family', u'RRC01 - Cascades frog', u'SOM05 - Central California coast winter steelhead', u'SOK01 - Central Coast coho salmon', u'SOT08 - Central Valley fall Chinook salmon', u'SOT07 - Central Valley late fall Chinook salmon', u'SOT06 - Central Valley spring Chinook salmon', u'SOM06 - Central Valley steelhead', u'SOT05 - Central Valley winter Chinook salmon', u'GTT01 - Chameleon goby', u'IIP01 - Channel catfish', u'CTM01 - Checkered gartersnake', u'SOT09 - Chinook Salmon (bin)', u'CHI01 - Chirocephalidae family', u'CHL01 - Chloroperlidae family', u'SOK03 - Chum salmon', u'CLE02 - Clear Lake hitch', u'CCA03 - Clear Lake prickly sculpin', u'CLS04 - Clear Lake roach', u'CPC01 - Clear Lake splittail', u'EHT03 - Clear Lake tule perch', u'SOC01 - Coastal cutthroat trout', u'SSC02 - Coastal dolly varden', u'DDT01 - Coastal giant salamander', u'SOM09 - Coastal rainbow trout', u'AAT02 - Coastal tailed frog', u'GGA01 - Coastal threespine stickleback', u'CCA04 - Coastrange sculpin', u'SOK04 - Coho (bin)', u'SOC05 - Colorado River cutthroat trout', u'CPL01 - Colorado pikeminnow', u'CLG03 - Common Kingsnake', u'CCC01 - Common carp', u'CTS01 - Common gartersnake', u'COR01 - Cordulegastridae family', u'COR02 - Corduliidae family', u'COR03 - Corydalidae family', u'CCS04 - Cottonball Marsh pupfish', u"SSC04 - Couch's spadefoot toad", u'CST03 - Cow Head tui chub', u'CRA01 - Crangonyctidae family', u'SOC04 - Cutthroat trout (bin)', u'PPE01 - Del Norte Salamander', u'OHP01 - Delta smelt', u'CCM02 - Desert pupfish', u'DEU01 - Deuterophlebiidae family', u'PPG01 - Diamond turbot', u'DIX01 - Dixidae family', u'SSC03 - Dolly varden', u"PPD01 - Dunn's salamander", u'SOM12 - Eagle Lake rainbow trout', u'CSB05 - Eagle Lake tui chub', u'ELM01 - Elmidae family', u'CHS01 - Empty data bin - California roach', u'EPH01 - Ephemerellidae family', u'OTP01 - Eulachon', u'EUL01 - Eulichadidae family', u'CPP01 - Fathead minnow', u'CCL02 - Flannelmouth sucker', u'IPO01 - Flathead Catfish', u'RRB01 - Foothill yellow-legged frog', u'CTG01 - Giant gartersnake', u'GLO01 - Glossosomatidae family', u'GOE01 - Goeridae family', u'CNC01 - Golden shiner', u'CCA05 - Goldfish', u'PET02 - Goose Lake lamprey', u'SOM11 - Goose Lake redband trout', u'CCO02 - Goose Lake sucker', u'CST01 - Goose Lake tui chub', u'CCI01 - Grass carp', u'SSI01 - Great Basin spadefoot', u'BAC03 - Great Plains toad', u'CLC01 - Green sunfish', u'PXH01 - Green swordtail', u'CLP01 - Gualala roach', u'PPR01 - Guppy', u'CMC01 - Hardhead', u'HEL01 - Helicopsychidae family', u'HEP01 - Heptageniidae family', u'CSB02 - High Rock Springs tui chub', u'CLE04 - Hitch (bin)', u'CCO04 - Humboldt sucker', u'HYD01 - Hydrobiidae family', u'MMB01 - Inland silverside', u'GGA02 - Inland threespine stickleback', u'PBC01 - Inyo Mountains salamander', u'ISO01 - Isonychiidae family', u'CLS09 - Kaweah roach', u'SOM13 - Kern River rainbow trout', u'PLH01 - Kern brook lamprey', u'SOM04 - Klamath Mountains Province summer steelhead', u'SOM03 - Klamath Mountains Province winter steelhead', u'PES01 - Klamath River lamprey', u'CCP04 - Klamath lake sculpin', u'CCS01 - Klamath largescale sucker', u'CCR01 - Klamath smallscale sucker', u'CRO03 - Klamath speckled dace', u'CSB01 - Klamath tui chub', u'SOC03 - Lahontan cutthroat trout', u'CSB03 - Lahontan lake tui chub', u'CCP01 - Lahontan mountain sucker', u'CRE01 - Lahontan redside', u'CRO02 - Lahontan speckled dace', u'CSB04 - Lahontan stream tui chub', u'SSN01 - Lake trout', u'CMS01 - Largemouth Bass', u'LEP01 - Lepidostomatidae family', u'LEU01 - Leuctridae family', u'LIM01 - Limnephilidae family', u'SOM15 - Little Kern golden trout', u'CRO05 - Long Valley speckled dace', u'AAM03 - Long-toed Salamander', u'OST01 - Longfin smelt', u'GGM01 - Longjaw mudsucker', u'GCS01 - Longtail goby', u'CCL01 - Lost River sucker', u'CCK02 - Lower Klamath marbled sculpin', u'LUT01 - Lutrochidae family', u'LYM01 - Lymnaeidae family', u'MAC01 - Macromiidae family', u'CCK04 - Marbled Sculpin (bin)', u'MAR01 - Margaritiferidae family', u'SOM10 - McCloud River redband trout', u'MMB02 - Mississippi silversides', u'CCM01 - Modoc sucker', u'CSM01 - Mojave tui chub', u'CLE03 - Monterey hitch', u'CCO03 - Monterey sucker', u'SPW01 - Mountain whitefish', u'CLS06 - Navarro roach', u'NEM01 - Nemouridae family', u'AEC01 - Northern Alligator Lizard', u'PEF01 - Northern California brook lamprey', u'SOM02 - Northern California coast summer steelhead', u'SOM01 - Northern California coast winter steelhead', u'CLS03 - Northern coastal roach', u'AAM01 - Northern green sturgeon', u'RRP01 - Northern leopard frog', u'RRA01 - Northern red-legged frog', u'CLS08 - Northern roach', u'CTO01 - Northwestern gartersnake', u'AAG01 - Northwestern salamander', u'ODO01 - Odontoceridae family', u'RRP02 - Oregon spotted frog', u'CCR02 - Owens pupfish', u'CRO04 - Owens speckled dace', u'CCF01 - Owens sucker', u'CSB06 - Owens tui chub', u'PLP01 - Pacific brook lamprey', u'HPR01 - Pacific chorus frog', u'CCH01 - Pacific herring', u'PET01 - Pacific lamprey', u'SOC02 - Paiute cutthroat trout', u'CCB02 - Paiute sculpin', u'PEL01 - Peltoperlidae family', u'PER01 - Perlidae family', u'PER02 - Perlodidae family', u'PET03 - Petaluridae family', u'PHI01 - Philopotamidae family', u'PHR01 - Phryganeidae family', u'SOG01 - Pink salmon', u'CST02 - Pit River tui chub', u'CCP02 - Pit sculpin', u'PLL01 - Pit-Klamath brook lamprey', u'PLE01 - Pleuroceridae family', u'PPG02 - Porthole livebearer', u'CCA02 - Prickly sculpin', u'PSY01 - Psychomyiidae family', u'PTE01 - Pteronarcyidae family', u'PTI01 - Ptilodactylidae family', u'CLG01 - Pumpkinseed', u'SOM17 - Rainbow Trout (Summer Steelhead)', u'SOM18 - Rainbow Trout (Winter Steelhead)', u'FLP01 - Rainwater killifish ', u'CXT01 - Razorback sucker', u'CLS02 - Red Hills roach', u'CCL03 - Red shiner', u'STR01 - Red-bellied newt', u'BAP01 - Red-spotted toad', u'SOM16 - Redband trout (bin)', u'CTZ01 - Redbelly tilapia', u'CLM03 - Redear sunfish', u'CMC02 - Redeye bass', u'CCP03 - Reticulate sculpin', u'RHY01 - Rhyacophilidae family', u'CCG01 - Riffle sculpin', u'PLA01 - River lamprey', u'CCA01 - Rough sculpin', u'STG01 - Rough-skinned newt', u'EHT02 - Russian River tule perch', u'COM01 - Sacramento blackfish', u'CLE01 - Sacramento hitch', u'CAI01 - Sacramento perch', u'CPG01 - Sacramento pikeminnow', u'CRO01 - Sacramento speckled dace', u'CPM01 - Sacramento splittail', u'CCO01 - Sacramento sucker', u'EHT01 - Sacramento tule perch', u'PPL01 - Sailfin molly', u'CCS03 - Salt Creek pupfish', u'CTS02 - San Francisco Gartersnake', u'CRO07 - Santa Ana speckled dace', u'CCS02 - Santa Ana sucker', u'PAN01 - Santa Cruz Black Salamander', u'AAM04 - Santa Cruz long-toed Salamander', u'CCN01 - Saratoga Springs pupfish', u'SCI01 - Scirtidae family', u'CCX01 - Sculpin spp (bin)', u'SER01 - Sericostomatidae family', u'CCA06 - Sharpnose sculpin', u'PAI01 - Shasta Black Salamander', u'GGA04 - Shay Creek stickleback', u'GTB01 - Shimofuri goby', u'ECA01 - Shiner perch', u'SCP01 - Shortfin corvina', u'PPM02 - Shortfin molly', u'CCB01 - Shortnose sucker', u'CCN04 - Shoshone pupfish', u'RRM01 - Sierra Madre yellow-legged frog', u'RRS01 - Sierra Nevada yellow-legged frog', u'CTC01 - Sierra gartersnake', u'STS01 - Sierra newt', u'HPS01 - Sierran Treefrog', u'PPS02 - Siskiyou Mountains Salamander', u'CCT02 - Slender sculpin', u'CMD01 - Smallmouth Bass', u'SON01 - Sockeye (Kokanee) Salmon', u'SOM07 - South Central California coast steelhead', u'CTS03 - South Coast Gartersnake', u'AEC02 - Southern Alligator Lizard', u'SOM08 - Southern California steelhead', u'SOK02 - Southern Oregon Northern California coast coho salmon', u'SOT03 - Southern Oregon Northern California coast fall Chinook salmon', u'CLS05 - Southern coastal roach', u'AAM02 - Southern green sturgeon', u'RRV01 - Southern torrent salamander', u'PAF01 - Speckled Black Salamander', u'CRO08 - Speckled Dace (bin)', u'SPH01 - Sphaeriidae family', u'CMP01 - Spotted bass', u'CLA01 - Staghorn sculpin', u'PPS01 - Starry flounder', u'SOM19 - Stocked Rainbow Trout (bin)', u'MMS01 - Striped bass', u'MMC02 - Striped mullet', u'OHP02 - Surf smelt', u'TAE01 - Taeniopterygidae family', u'CCT01 - Tahoe sucker', u'TAN01 - Tanyderidae family', u'CCN03 - Tecopa pupfish', u'CTT01 - Tench', u'CSC01 - Thicktail chub', u'CDP01 - Threadfin shad', u'GGA05 - Threespine stickleback (bin)', u'GEN01 - Tidewater goby', u'CLS07 - Tomales roach', u'AAA01 - Topsmelt', u'CSB07 - Tui chub bin', u'EHT04 - Tule perch (bin)', u'CTH01 - Twp-striped gartersnake', u'UEN01 - Uenoidae family', u'GGA03 - Unarmored threespine stickleback', u'UNI01 - Unionidae family', u'CCK03 - Upper Klamath marbled sculpin', u'SOT01 - Upper Klamath-Trinity fall Chinook salmon', u'SOT02 - Upper Klamath-Trinity spring Chinook salmon', u'OHN01 - Wakasagi', u'PAV01 - Wandering Salamander', u'CLG02 - Warmouth', u'EAM01 - Western Pond Turtle', u'PLR01 - Western brook lamprey', u'PGA01 - Western mosquitofish', u'EEM01 - Western pond turtle', u'SSH01 - Western spadefoot toad', u'CTE01 - Western terrestrial gartersnake', u'BAB01 - Western toad', u'MMC01 - White bass', u'IAC01 - White catfish', u'CPA01 - White crappie', u'AAT01 - White sturgeon', u"BAW01 - Woodhouse's toad", u'IAN01 - Yellow bullhead', u'PPF01 - Yellow perch', u'GAF01 - Yellowfin goby', u'BAC01 - Yosemite Toad', u'ZZZ01 - temp']

        # Operation
        param_3 = arcpy.Parameter()
        param_3.name = u'Operation'
        param_3.displayName = u'Operation'
        param_3.parameterType = 'Required'
        param_3.direction = 'Input'
        param_3.datatype = u'String'
        param_3.value = u'Add'
        param_3.filter.list = [u'Add', u'Transfer', u'Remove']

        # New_Species
        param_4 = arcpy.Parameter()
        param_4.name = u'New_Species'
        param_4.displayName = u'New Species'
        param_4.parameterType = 'Optional'
        param_4.direction = 'Input'
        param_4.datatype = u'String'
        param_4.filter.list = [u'PXL01 - African Clawed Frog', u'CRO06 - Amargosa Canyon speckled dace', u'CCN02 - Amargosa River pupfish', u'AME01 - Ameletidae family', u'RLC01 - American Bullfrog', u'CAS01 - American Shad', u'AMP01 - Amphizoidae family', u'ANI01 - Anisogammaridae family', u'APA01 - Apataniidae family', u'CTA01 - Aquatic gartersnake', u'STA01 - Arctic grayling', u'RCB01 - Argentine pearlfish', u'GCI01 - Arrow goby', u'BAC02 - Arroyo Toad', u'CGO01 - Arroyo chub', u'ASE01 - Asellidae family', u'AST01 - Astacidae family', u'ATH01 - Athericidae family', u'ATY01 - Atyidae family', u'HPH01 - Baja California Treefrog', u'SSA01 - Barred Pipefish', u'CCK01 - Bigeye marbled sculpin', u'CIC01 - Bigmouth buffalo', u'PPM01 - Bigscale logperch', u'IAM01 - Black bullhead', u'CPN01 - Black crappie', u'BAE01 - Black toad', u'COM02 - Blackfish (bin)', u'BLE01 - Blephariceridae family', u'IIF01 - Blue catfish', u'CGC01 - Blue chub', u'FLG01 - Bluefin killifish', u'CLM02 - Bluegill', u'CGE01 - Bonytail', u'BRA01 - Brachycentridae family', u'SSF01 - Brook Trout', u'GCI02 - Brook stickleback', u'SST01 - Brown Trout', u'IAN02 - Brown bullhead', u'SSC01 - Bull trout', u'CAL01 - Calamoceratidae family', u'SOT04 - California Coast fall Chinook salmon', u'BAB02 - California Toad', u'DDE01 - California giant salamander', u'SOM14 - California golden trout', u'PPC01 - California halibut', u'CFP01 - California killifish', u'STT01 - California newt', u'RRD01 - California red-legged frog', u'CLS01 - California roach', u'AAC01 - California tiger salamander', u'COM03 - California tilapia (hybrid)', u'HPC01 - California tree frog', u'CAP01 - Capniidae family', u'RRC01 - Cascades frog', u'SOM05 - Central California coast winter steelhead', u'SOK01 - Central Coast coho salmon', u'SOT08 - Central Valley fall Chinook salmon', u'SOT07 - Central Valley late fall Chinook salmon', u'SOT06 - Central Valley spring Chinook salmon', u'SOM06 - Central Valley steelhead', u'SOT05 - Central Valley winter Chinook salmon', u'GTT01 - Chameleon goby', u'IIP01 - Channel catfish', u'CTM01 - Checkered gartersnake', u'SOT09 - Chinook Salmon (bin)', u'CHI01 - Chirocephalidae family', u'CHL01 - Chloroperlidae family', u'SOK03 - Chum salmon', u'CLE02 - Clear Lake hitch', u'CCA03 - Clear Lake prickly sculpin', u'CLS04 - Clear Lake roach', u'CPC01 - Clear Lake splittail', u'EHT03 - Clear Lake tule perch', u'SOC01 - Coastal cutthroat trout', u'SSC02 - Coastal dolly varden', u'DDT01 - Coastal giant salamander', u'SOM09 - Coastal rainbow trout', u'AAT02 - Coastal tailed frog', u'GGA01 - Coastal threespine stickleback', u'CCA04 - Coastrange sculpin', u'SOK04 - Coho (bin)', u'SOC05 - Colorado River cutthroat trout', u'CPL01 - Colorado pikeminnow', u'CLG03 - Common Kingsnake', u'CCC01 - Common carp', u'CTS01 - Common gartersnake', u'COR01 - Cordulegastridae family', u'COR02 - Corduliidae family', u'COR03 - Corydalidae family', u'CCS04 - Cottonball Marsh pupfish', u"SSC04 - Couch's spadefoot toad", u'CST03 - Cow Head tui chub', u'CRA01 - Crangonyctidae family', u'SOC04 - Cutthroat trout (bin)', u'PPE01 - Del Norte Salamander', u'OHP01 - Delta smelt', u'CCM02 - Desert pupfish', u'DEU01 - Deuterophlebiidae family', u'PPG01 - Diamond turbot', u'DIX01 - Dixidae family', u'SSC03 - Dolly varden', u"PPD01 - Dunn's salamander", u'SOM12 - Eagle Lake rainbow trout', u'CSB05 - Eagle Lake tui chub', u'ELM01 - Elmidae family', u'CHS01 - Empty data bin - California roach', u'EPH01 - Ephemerellidae family', u'OTP01 - Eulachon', u'EUL01 - Eulichadidae family', u'CPP01 - Fathead minnow', u'CCL02 - Flannelmouth sucker', u'IPO01 - Flathead Catfish', u'RRB01 - Foothill yellow-legged frog', u'CTG01 - Giant gartersnake', u'GLO01 - Glossosomatidae family', u'GOE01 - Goeridae family', u'CNC01 - Golden shiner', u'CCA05 - Goldfish', u'PET02 - Goose Lake lamprey', u'SOM11 - Goose Lake redband trout', u'CCO02 - Goose Lake sucker', u'CST01 - Goose Lake tui chub', u'CCI01 - Grass carp', u'SSI01 - Great Basin spadefoot', u'BAC03 - Great Plains toad', u'CLC01 - Green sunfish', u'PXH01 - Green swordtail', u'CLP01 - Gualala roach', u'PPR01 - Guppy', u'CMC01 - Hardhead', u'HEL01 - Helicopsychidae family', u'HEP01 - Heptageniidae family', u'CSB02 - High Rock Springs tui chub', u'CLE04 - Hitch (bin)', u'CCO04 - Humboldt sucker', u'HYD01 - Hydrobiidae family', u'MMB01 - Inland silverside', u'GGA02 - Inland threespine stickleback', u'PBC01 - Inyo Mountains salamander', u'ISO01 - Isonychiidae family', u'CLS09 - Kaweah roach', u'SOM13 - Kern River rainbow trout', u'PLH01 - Kern brook lamprey', u'SOM04 - Klamath Mountains Province summer steelhead', u'SOM03 - Klamath Mountains Province winter steelhead', u'PES01 - Klamath River lamprey', u'CCP04 - Klamath lake sculpin', u'CCS01 - Klamath largescale sucker', u'CCR01 - Klamath smallscale sucker', u'CRO03 - Klamath speckled dace', u'CSB01 - Klamath tui chub', u'SOC03 - Lahontan cutthroat trout', u'CSB03 - Lahontan lake tui chub', u'CCP01 - Lahontan mountain sucker', u'CRE01 - Lahontan redside', u'CRO02 - Lahontan speckled dace', u'CSB04 - Lahontan stream tui chub', u'SSN01 - Lake trout', u'CMS01 - Largemouth Bass', u'LEP01 - Lepidostomatidae family', u'LEU01 - Leuctridae family', u'LIM01 - Limnephilidae family', u'SOM15 - Little Kern golden trout', u'CRO05 - Long Valley speckled dace', u'AAM03 - Long-toed Salamander', u'OST01 - Longfin smelt', u'GGM01 - Longjaw mudsucker', u'GCS01 - Longtail goby', u'CCL01 - Lost River sucker', u'CCK02 - Lower Klamath marbled sculpin', u'LUT01 - Lutrochidae family', u'LYM01 - Lymnaeidae family', u'MAC01 - Macromiidae family', u'CCK04 - Marbled Sculpin (bin)', u'MAR01 - Margaritiferidae family', u'SOM10 - McCloud River redband trout', u'MMB02 - Mississippi silversides', u'CCM01 - Modoc sucker', u'CSM01 - Mojave tui chub', u'CLE03 - Monterey hitch', u'CCO03 - Monterey sucker', u'SPW01 - Mountain whitefish', u'CLS06 - Navarro roach', u'NEM01 - Nemouridae family', u'AEC01 - Northern Alligator Lizard', u'PEF01 - Northern California brook lamprey', u'SOM02 - Northern California coast summer steelhead', u'SOM01 - Northern California coast winter steelhead', u'CLS03 - Northern coastal roach', u'AAM01 - Northern green sturgeon', u'RRP01 - Northern leopard frog', u'RRA01 - Northern red-legged frog', u'CLS08 - Northern roach', u'CTO01 - Northwestern gartersnake', u'AAG01 - Northwestern salamander', u'ODO01 - Odontoceridae family', u'RRP02 - Oregon spotted frog', u'CCR02 - Owens pupfish', u'CRO04 - Owens speckled dace', u'CCF01 - Owens sucker', u'CSB06 - Owens tui chub', u'PLP01 - Pacific brook lamprey', u'HPR01 - Pacific chorus frog', u'CCH01 - Pacific herring', u'PET01 - Pacific lamprey', u'SOC02 - Paiute cutthroat trout', u'CCB02 - Paiute sculpin', u'PEL01 - Peltoperlidae family', u'PER01 - Perlidae family', u'PER02 - Perlodidae family', u'PET03 - Petaluridae family', u'PHI01 - Philopotamidae family', u'PHR01 - Phryganeidae family', u'SOG01 - Pink salmon', u'CST02 - Pit River tui chub', u'CCP02 - Pit sculpin', u'PLL01 - Pit-Klamath brook lamprey', u'PLE01 - Pleuroceridae family', u'PPG02 - Porthole livebearer', u'CCA02 - Prickly sculpin', u'PSY01 - Psychomyiidae family', u'PTE01 - Pteronarcyidae family', u'PTI01 - Ptilodactylidae family', u'CLG01 - Pumpkinseed', u'SOM17 - Rainbow Trout (Summer Steelhead)', u'SOM18 - Rainbow Trout (Winter Steelhead)', u'FLP01 - Rainwater killifish ', u'CXT01 - Razorback sucker', u'CLS02 - Red Hills roach', u'CCL03 - Red shiner', u'STR01 - Red-bellied newt', u'BAP01 - Red-spotted toad', u'SOM16 - Redband trout (bin)', u'CTZ01 - Redbelly tilapia', u'CLM03 - Redear sunfish', u'CMC02 - Redeye bass', u'CCP03 - Reticulate sculpin', u'RHY01 - Rhyacophilidae family', u'CCG01 - Riffle sculpin', u'PLA01 - River lamprey', u'CCA01 - Rough sculpin', u'STG01 - Rough-skinned newt', u'EHT02 - Russian River tule perch', u'COM01 - Sacramento blackfish', u'CLE01 - Sacramento hitch', u'CAI01 - Sacramento perch', u'CPG01 - Sacramento pikeminnow', u'CRO01 - Sacramento speckled dace', u'CPM01 - Sacramento splittail', u'CCO01 - Sacramento sucker', u'EHT01 - Sacramento tule perch', u'PPL01 - Sailfin molly', u'CCS03 - Salt Creek pupfish', u'CTS02 - San Francisco Gartersnake', u'CRO07 - Santa Ana speckled dace', u'CCS02 - Santa Ana sucker', u'PAN01 - Santa Cruz Black Salamander', u'AAM04 - Santa Cruz long-toed Salamander', u'CCN01 - Saratoga Springs pupfish', u'SCI01 - Scirtidae family', u'CCX01 - Sculpin spp (bin)', u'SER01 - Sericostomatidae family', u'CCA06 - Sharpnose sculpin', u'PAI01 - Shasta Black Salamander', u'GGA04 - Shay Creek stickleback', u'GTB01 - Shimofuri goby', u'ECA01 - Shiner perch', u'SCP01 - Shortfin corvina', u'PPM02 - Shortfin molly', u'CCB01 - Shortnose sucker', u'CCN04 - Shoshone pupfish', u'RRM01 - Sierra Madre yellow-legged frog', u'RRS01 - Sierra Nevada yellow-legged frog', u'CTC01 - Sierra gartersnake', u'STS01 - Sierra newt', u'HPS01 - Sierran Treefrog', u'PPS02 - Siskiyou Mountains Salamander', u'CCT02 - Slender sculpin', u'CMD01 - Smallmouth Bass', u'SON01 - Sockeye (Kokanee) Salmon', u'SOM07 - South Central California coast steelhead', u'CTS03 - South Coast Gartersnake', u'AEC02 - Southern Alligator Lizard', u'SOM08 - Southern California steelhead', u'SOK02 - Southern Oregon Northern California coast coho salmon', u'SOT03 - Southern Oregon Northern California coast fall Chinook salmon', u'CLS05 - Southern coastal roach', u'AAM02 - Southern green sturgeon', u'RRV01 - Southern torrent salamander', u'PAF01 - Speckled Black Salamander', u'CRO08 - Speckled Dace (bin)', u'SPH01 - Sphaeriidae family', u'CMP01 - Spotted bass', u'CLA01 - Staghorn sculpin', u'PPS01 - Starry flounder', u'SOM19 - Stocked Rainbow Trout (bin)', u'MMS01 - Striped bass', u'MMC02 - Striped mullet', u'OHP02 - Surf smelt', u'TAE01 - Taeniopterygidae family', u'CCT01 - Tahoe sucker', u'TAN01 - Tanyderidae family', u'CCN03 - Tecopa pupfish', u'CTT01 - Tench', u'CSC01 - Thicktail chub', u'CDP01 - Threadfin shad', u'GGA05 - Threespine stickleback (bin)', u'GEN01 - Tidewater goby', u'CLS07 - Tomales roach', u'AAA01 - Topsmelt', u'CSB07 - Tui chub bin', u'EHT04 - Tule perch (bin)', u'CTH01 - Twp-striped gartersnake', u'UEN01 - Uenoidae family', u'GGA03 - Unarmored threespine stickleback', u'UNI01 - Unionidae family', u'CCK03 - Upper Klamath marbled sculpin', u'SOT01 - Upper Klamath-Trinity fall Chinook salmon', u'SOT02 - Upper Klamath-Trinity spring Chinook salmon', u'OHN01 - Wakasagi', u'PAV01 - Wandering Salamander', u'CLG02 - Warmouth', u'EAM01 - Western Pond Turtle', u'PLR01 - Western brook lamprey', u'PGA01 - Western mosquitofish', u'EEM01 - Western pond turtle', u'SSH01 - Western spadefoot toad', u'CTE01 - Western terrestrial gartersnake', u'BAB01 - Western toad', u'MMC01 - White bass', u'IAC01 - White catfish', u'CPA01 - White crappie', u'AAT01 - White sturgeon', u"BAW01 - Woodhouse's toad", u'IAN01 - Yellow bullhead', u'PPF01 - Yellow perch', u'GAF01 - Yellowfin goby', u'BAC01 - Yosemite Toad', u'ZZZ01 - temp']

        # Message
        param_5 = arcpy.Parameter()
        param_5.name = u'Message'
        param_5.displayName = u'Message'
        param_5.parameterType = 'Optional'
        param_5.direction = 'Input'
        param_5.datatype = u'String'

        # Subset
        param_6 = arcpy.Parameter()
        param_6.name = u'Subset'
        param_6.displayName = u'Subset'
        param_6.parameterType = 'Optional'
        param_6.direction = 'Input'
        param_6.datatype = u'String'
        param_6.value = u'Presence_Type = 3'

        # Default_Input_Filter
        param_7 = arcpy.Parameter()
        param_7.name = u'Default_Input_Filter'
        param_7.displayName = u'Default Input Filter'
        param_7.parameterType = 'Required'
        param_7.direction = 'Input'
        param_7.datatype = u'String'
        param_7.value = u'23 - CWS - Default CWS "Add or Modify Data" Input Filter'
        param_7.filter.list = [u'1 - MOY - Moyle Distribution Maps', u'3 - USFS_Tahoe - Tahoe National Forest Data', u'5 - USFS_AREMP - Klamath National Forest Data', u'6 - USFS_LTBMU - Lake Tahoe Basin Management Unit Data', u'7 - USFS_Sierra - Sierra National Forest Data', u'8 - USFS_R5 - Region 5 Database Importer', u'9 - USFS_Stan - Stanislaus National Forest Data', u'10 - MKS - Moyle and Katz', u'11 - MKS_Low - Moyle and Katz - Low Probability', u'12 - FERC_Data - FERC survey data', u'13 - Lindley_NOAA - Historical Salmonid Distributions', u'14 - CNDDB - California Natural Diversity Database', u'15 - EMAP - California EMAP Data', u'16 - CNDDB_Amph - California Natural Diversity Database Amphibians', u'17 - Gen_Poly - General Polygon Import', u'18 - MQB - Moyle and Quinones', u'19 - TNC_Herps - The Nature Conservancy Database', u'21 - AW_herps - Herps HUC12 Ranges from Amber Wright', u'22 - TU_inverts - Inverts for freshwater conservation from TU', u'23 - CWS - Default CWS "Add or Modify Data" Input Filter', u'24 - CDFW - Default CDFW "Add or Modify Data" Input Filter', u'25 - CDFW_Heritage_Trout - CDFW Heritage Trout Dataset']

        # Default_Observation_Set
        param_8 = arcpy.Parameter()
        param_8.name = u'Default_Observation_Set'
        param_8.displayName = u'Default Observation Set'
        param_8.parameterType = 'Required'
        param_8.direction = 'Input'
        param_8.datatype = u'String'
        param_8.value = u'auto'
        param_8.filter.list = [u'auto']

        # New_Distribution
        param_9 = arcpy.Parameter()
        param_9.name = u'New_Distribution'
        param_9.displayName = u'New Distribution'
        param_9.parameterType = 'Derived'
        param_9.direction = 'Output'
        param_9.datatype = u'Feature Layer'

        # Presence_Type
        param_10 = arcpy.Parameter()
        param_10.name = u'Presence_Type'
        param_10.displayName = u'Presence Type'
        param_10.parameterType = 'Required'
        param_10.direction = 'Input'
        param_10.datatype = u'String'
        param_10.multiValue = True
        param_10.value = u"'3 - Extant Range - Expert opinion says it is here'"
        param_10.filter.list = [u'1 - Observed - backed up by data, this is verifiable', u'2 - Historical Range - Expert opinion source as noted', u'3 - Extant Range - Expert opinion says it is here', u'4 - Extant Range - Modeled to exist here currently', u'5 -  Extirpated -  confirmed by experts', u'6 - Translocated - Expert Opinion', u'7 - Translocated - Observed', u'8 - Historical Range - Modeled', u'9 - Reintroduced', u'10 - Historical Range - Observed']

        # Return_Updated_Expert_Knowledge_Layer
        param_11 = arcpy.Parameter()
        param_11.name = u'Return_Updated_Expert_Knowledge_Layer'
        param_11.displayName = u'Return Updated Expert Knowledge Layer'
        param_11.parameterType = 'Optional'
        param_11.direction = 'Input'
        param_11.datatype = u'Boolean'

        return [param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9, param_10, param_11]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_modify_records.py'):
            import os
            import sys
            import re
            
            import arcpy
            
            import local_vars
            import log
            import funcs
            import mapping
            import api
            import script_tool_funcs
            
            '''This script is meant to be run only as an ArcGIS script tool - messages will be passed out using arcpy'''
            '''This is the primary toolbox function from before they were prefixed with tbx_ - it handles modifications of records directly from within ArcGIS'''
            
            
            print "This script should only be run as an ArcGIS script tool. If you can see this message, you should exit or you better know what you are doing"
            
            local_vars.start(arc_script=1)
            
            mapping.config_metadata = False  # don't generate metadata for maps when they have it enabled
            
            # general
            layer = parameters[0].valueAsText
            species = parameters[1].valueAsText
            operation = parameters[2].valueAsText  # add, remove, transfer
            new_species = parameters[3].valueAsText
            reason_message = parameters[4].valueAsText
            where_string = parameters[5].valueAsText
            
            # for adding new records
            default_input_filter = parameters[6].valueAsText
            default_observation_set = parameters[7].valueAsText
            
            observation_types = parameters[9].valueAsText
            update_range = parameters[10]
            
            # do a sanity check
            if arcpy.GetCount_management(layer).getOutput(0) == arcpy.GetCount_management(local_vars.HUCS).getOutput(0):  # if we have all of the HUCs selected
                messages.AddErrorMessage("Whoa - are you trying to destroy a whole species here? You selected the whole state! (Check to make sure that the HUC12 layer you selected in the tool is the one with the selection for modifications). Since it was probably an error, we're going to just exit the program right now. If you intended to run that operation, do us a favor and select all of the polygons, then deselect just one so we know you are in your right mind. Then try again.")
                sys.exit()
            
            if default_input_filter is None:  # if one wasn't specified
                default_input_filter = "CWS"
            else:
                default_input_filter = script_tool_funcs.parse_input_filter_picker(default_input_filter)[1]  # a tuple is returned. We want the part with the filter code to align with the existing code in this tool
            
            if species is None and new_species is None:
                log.error("No species to work on, exiting")
                sys.exit()
            
            observation_types = script_tool_funcs.obs_type_selection_box_to_list(observation_types)
            
            if len(observation_types) == 0 and operation == "Add":
                messages.AddErrorMessage("No Observation Type set for addition. Please select at least one observation type")
                sys.exit()
            
            
            species_in = species
            species = funcs.parse_input_species_from_list(species)
            
            new_species_in = new_species
            if len(new_species) > 0:
                new_species = funcs.parse_input_species_from_list(new_species)
            
            log.write("Making changes to species %s" % species)
                
            db_cursor, db_conn = funcs.db_connect(local_vars.maindb, "Connecting to database to modify HUC data")
            
            
            def get_zones(layer, zones_array, column):
                
                dataset = arcpy.SearchCursor(layer)
                for row in dataset:
                    zones_array.append(row.getValue(column))  # append the zones id to the array
            
            
            def get_obs_set_id():
            
                select_string = "select Set_ID from Observation_Sets where Input_Filter = ?"  # will select the first one
                results = db_cursor.execute(select_string, default_input_filter)
                
                for row in results:  # return the first one we get
                    return row.set_id
            
            
            def get_defaults():
                if default_observation_set == "auto" or default_observation_set is None:
                    set_id = get_obs_set_id()
            
                select_string = "select ifm.objectid, ifm.default_observation_type, ifm.default_certainty from defs_if_methods as ifm, defs_input_filters as dif where ifm.input_filter = dif.objectid and dif.code = ?"
                results = db_cursor.execute(select_string, str(default_input_filter))
                
                for row in results:
                    return set_id, row.default_certainty, row.default_observation_type, row.objectid
            
            
            def new_records(zones, obs_types):  # to be used for adding entirely new records to the database
            
                set_id, certainty, presence_type, if_method = get_defaults()
                
                import datetime
                l_date = datetime.datetime.now()
                l_date_string = "%s-%02d-%02d %02d:%02d:%02d" % (l_date.year, l_date.month, l_date.day, l_date.hour, l_date.minute, l_date.second)
                    
                insert_string = "insert into observations (set_id,species_id,zone_id,presence_type,if_method,certainty,observation_date, date_added, notes) values (?,?,?,?,?,?,?,?,?)"
            
                for zone in zones:
                    for pres_type in obs_types:
                        db_cursor.execute(insert_string, set_id, species, zone, pres_type, if_method, certainty, l_date_string, l_date_string, reason_message)
            
                        # The following were a temporary hack as a result of database inconsistencies during the migration from access to sqlite
                        #id_value = db_cursor.execute("select last_insert_rowid() as recordid").fetchone().recordid
                        #db_cursor.execute("update observations set geodb_oid=%s, objectid=%s where OGC_FID=%s" % (id_value, id_value, id_value))
            
                # I think the following lines duplicate functionality further down in modify_records where transactions are added.
                #transaction_string = "insert into transactions (fid,species_in,fid_to,species_to,operation,input_filter,message,subset,result) values (?,?,?,?,?,?,?,?,?)"
                #db_cursor.execute(transaction_string, species, species_in, new_species, new_species_in, operation, default_input_filter, reason_message, where_string, "success")
            
            
            def modify_records(zones):
            
                # save the transaction
                transaction_string = "insert into transactions (fid, species_in, fid_to, species_to,operation,input_filter,message,subset,result) values (?,?,?,?,?,?,?,?,?)"
                db_cursor.execute(transaction_string, species, species_in, new_species, new_species_in, operation, default_input_filter, reason_message, where_string, "failed")
            
                # get the ID to attach to the records
                transaction_id = funcs.get_last_insert_id(db_cursor)
            
                for zone in zones:
                    
                    w_clause = "Species_ID = ? and Zone_ID = ?"
                            
                    if where_string:
                        w_clause = "%s and %s" % (w_clause, where_string)
            
                    invalidate_records(w_clause, species, zone, transaction_id)
                    
                    if operation == "Remove":  # if we're not moving it, then delete the records
                        delete_string = "delete from observations where %s" % w_clause
                        db_cursor.execute(delete_string, species, zone)
                    elif operation == "Transfer":  # we have a fish to move to
                        update_string = "update observations set species_id = ? where %s" % w_clause
                        db_cursor.execute(update_string, new_species, species, zone)
                    else:
                        messages.AddErrorMessage("Specified operation: %s - however, the other parameters specified are insufficient to complete that operation" % operation)
                        sys.exit()
            
                    # we made it through, set the result to success
                    db_cursor.execute("update transactions set result='success' where id=?", transaction_id)
            
            
            def invalidate_records(w_clause, species, zone, transaction_id):
                """
                    Copies records over from observations to invalid_observations that match the specified where clause, species code, and huc 12 ID.
                :param w_clause: a where clause for SQL - should include parameter markers for species and zone_ID columns to be passed in
                :param species: A PISCES species code to filter the records to
                :param zone: HUC 12 ID, as used in PISCES - used to filter the species
                :param transaction_id: the transaction ID to associate the records with
                :return:
                """
                # move the records over to Invalid_Observations
            
                if w_clause == "":  # if it's empty:
                    raise local_vars.DataStorageError("Can't invalidate records without a where clause - are you trying to nuke the whole database???")
            
                select_string = "select * from observations where %s" % w_clause
                records = db_cursor.execute(select_string, species, zone)
                l_cursor = db_conn.cursor()
                
                insert_string = "insert into invalid_observations (objectid, set_id, species_id, zone_id, presence_type, if_method, certainty, longitude, latitude, survey_method, notes, observation_date, other_data, invalid_notes, transaction_id) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                
                for record in records:
                    l_cursor.execute(insert_string, record.objectid, record.set_id, record.species_id, record.zone_id, record.presence_type, record.if_method, record.certainty, record.longitude, record.latitude, record.survey_method, record.notes, record.observation_date, record.other_data, reason_message, transaction_id)
                
                # close the subcursor
                l_cursor.close()
            
            
            def modify_range(l_layer, l_species, l_operation, l_new_species, l_reason_message, l_where_string, l_input_filter, l_observation_set, l_observation_types, l_update_range):
                """
                    WARNING: Doesn't work yet because this whole script uses damn globals.
                :param l_layer:
                :param l_species:
                :param l_operation:
                :param l_new_species:
                :param l_reason_message:
                :param l_where_string:
                :param l_input_filter:
                :param l_observation_set:
                :param l_observation_types:
                :param l_update_range:
                :return:
                """
                # open the database connection
                log.write("Getting Zones")
                zones = []
                get_zones(l_layer, zones, "HUC_12")  # fills the zones array with the zones to work with
            
                if operation == "Add":  # if we have a species, but not a current one, then we're adding new records
                    new_records(zones, observation_types)
                else:  # otherwise, we're modifying existing records
                    modify_records(zones)  # handles records whether they are being modified or deleted entirely
            
                db_conn.commit()
                log.write("Completed modifications", 1)
            
                if l_update_range is True:
                    log.write("Generating new layer", 1)
                    new_layer = api.get_query_as_layer("select distinct Zone_ID from Observations where Species_ID = '%s' And Presence_Type = 3" % l_species)
                    if new_layer:
                        params = parameters
                        params[8].symbology = os.path.join(local_vars.internal_workspace, "mxds", "base", "gen_3.lyr")
                        set_parameter_as_text(parameters, 8, new_layer)
            
                    # close the database connection
                    funcs.db_close(db_cursor, db_conn)
            
            
            if script_tool_funcs.is_in_arcgis():
                arcmap_layers, running_in_arcmap = script_tool_funcs.deactivate_map("CURRENT")
            
                try:
                    modify_range(layer, species, operation, new_species, reason_message, where_string, default_input_filter, default_observation_set, observation_types, update_range)
            
                finally:
                    script_tool_funcs.reactivate_map("CURRENT", arcmap_layers, running_in_arcmap)
            

class addunique2(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Input\addunique2"""
    import arcpy
    
    from PISCES import local_vars
    from PISCES import script_tool_funcs
    
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        self.blank = ""
    
        local_vars.start()
    
        script_tool_funcs.get_input_filter_picker(self, 2)
          
    
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
    
        l_dataset = self.params[0].value
        if l_dataset is not None:
          l_fields = arcpy.ListFields(l_dataset)  # we're using this method rather than a builtin connection in the toolbox because we're not just allowing tables to be used.
    
          l_list = [] # create the temporary list
          for field in l_fields:
            l_list.append(field.name) # for whatever reason, it seems that the actual list doesn't support append (nothing showed up when that was tried), so we append to the temp list instead
    
          self.params[1].filter.list = l_list # copy to the column field
          self.params[3].filter.list = l_list # copy to the fid_column field
    
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Add Field Values as Alternate Species Names'
        self.description = u"Takes the selected features and adds the values from a selected column to the database as alt_codes for a specified input filter. It adds the same row's FID if a column is specified (optional)"
        self.canRunInBackground = False
        self.category = "Input"
    def getParameterInfo(self):
        # Table_or_Feature_Class
        param_1 = arcpy.Parameter()
        param_1.name = u'Table_or_Feature_Class'
        param_1.displayName = u'Table or Feature Class'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'Table View'

        # Alt_Code_Column
        param_2 = arcpy.Parameter()
        param_2.name = u'Alt_Code_Column'
        param_2.displayName = u'Alt Code Column'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'
        param_2.filter.list = []

        # Input_Filter
        param_3 = arcpy.Parameter()
        param_3.name = u'Input_Filter'
        param_3.displayName = u'Input Filter'
        param_3.parameterType = 'Required'
        param_3.direction = 'Input'
        param_3.datatype = u'String'
        param_3.filter.list = [u'1 - MOY - Moyle Distribution Maps', u'3 - USFS_Tahoe - Tahoe National Forest Data', u'5 - USFS_AREMP - Klamath National Forest Data', u'6 - USFS_LTBMU - Lake Tahoe Basin Management Unit Data', u'7 - USFS_Sierra - Sierra National Forest Data', u'8 - USFS_R5 - Region 5 Database Importer', u'9 - USFS_Stan - Stanislaus National Forest Data', u'10 - MKS - Moyle and Katz', u'11 - MKS_Low - Moyle and Katz - Low Probability', u'12 - FERC_Data - FERC survey data', u'13 - Lindley_NOAA - Historical Salmonid Distributions', u'14 - CNDDB - California Natural Diversity Database', u'15 - EMAP - California EMAP Data', u'16 - CNDDB_Amph - California Natural Diversity Database Amphibians', u'17 - Gen_Poly - General Polygon Import', u'18 - MQB - Moyle and Quinones', u'19 - TNC_Herps - The Nature Conservancy Database', u'21 - AW_herps - Herps HUC12 Ranges from Amber Wright', u'22 - TU_inverts - Inverts for freshwater conservation from TU', u'23 - CWS - Default CWS "Add or Modify Data" Input Filter', u'24 - CDFW - Default CDFW "Add or Modify Data" Input Filter', u'25 - CDFW_Heritage_Trout - CDFW Heritage Trout Dataset']

        # FID_Column
        param_4 = arcpy.Parameter()
        param_4.name = u'FID_Column'
        param_4.displayName = u'FID Column'
        param_4.parameterType = 'Optional'
        param_4.direction = 'Input'
        param_4.datatype = u'String'

        return [param_1, param_2, param_3, param_4]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_add_alt_codes.py'):
            import os
            
            import arcpy
            from sqlalchemy.exc import IntegrityError
            
            import script_tool_funcs
            import local_vars
            import funcs
            import log
            import orm_models
            
            local_vars.start(arc_script=1)
            
            arcpy.env.overwriteOutput = True  # we want to overwrite outputs because we'll be writing to temp.mdb
            
            feature_layer = parameters[0].valueAsText
            column = parameters[1].valueAsText
            input_filter = parameters[2].valueAsText
            fid_column = parameters[3].valueAsText
            if fid_column == "":
                fid_column = None
            
            
            class alt_code():  # def the class - it'll be used when retrieving the results
                def __init__(self, l_code=None, l_fid=None):
                    self.fid = l_fid
                    self.input_filter = input_filter # auto set it to the global input_filter
                    self.alt_code = l_code
            
            all_codes = {}  # holds the retrieved codes
            
            log.write("Retrieving information from feature", True)
            
            input_filter = script_tool_funcs.parse_input_filter_picker(input_filter)[1]
            
            features = desc = arcpy.Describe(feature_layer).catalogPath
            feature_name = os.path.split(features)[1]
            
            
            fields = [column, ]
            if fid_column is not None and fid_column != "":
                fields.append(fid_column)
            
            l_codes = arcpy.SearchCursor(features, fields=";".join(fields))
            
            for code in l_codes:
                alt = code.getValue(column)
                if alt in all_codes or alt is None or alt == "":  # don't add it again if we already have it - makes it so we only get unique
                    continue
            
                l_alt = alt_code(alt)
                if fid_column is not None and fid_column != "":
                    l_alt.fid = code.getValue(fid_column)
                all_codes[alt] = l_alt
            
            
            log.write("Updating database with information")
            
            session = orm_models.new_session(autocommit=True)
            
            try:
                for alt in all_codes:
                    l_code = all_codes[alt]
                    try:
                        new_name = orm_models.AlternateSpeciesName()
                        new_name.alternate_species_name = l_code.alt_code
                        new_name.species = session.query(orm_models.Species).filter_by(fid=l_code.fid).first()
                        new_name.input_filter = session.query(orm_models.InputFilter).filter_by(code=l_code.input_filter).first()
            
                        session.add(new_name)
                    except IntegrityError:
                        log.warning("Skipping duplicate entry for {} in input filter {}".format(l_code.alt_code, l_code.input_filter))
                        continue  # this is OK to skip - the same alt-code for the same input filter should almost always be fine to pass over with just a warning
            
            finally:
                session.close()
            
            messages.AddWarningMessage("Alt_Codes added for input filter %s - be sure to go check and add any necessary and missing FIDs for the codes" % input_filter)
            

class generatematrix2(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Output\generatematrix2"""
    import arcpy
    
    from PISCES import local_vars
    from PISCES import script_tool_funcs
    
    
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
    
    
        self.species_picker = 0
        self.species_storage = 1
        self.obs_type_picker = 2
    
        self.blank = ""
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        script_tool_funcs.make_species_group_picker(self, self.species_picker, self.species_storage)
        script_tool_funcs.make_obs_type_picker(self, self.obs_type_picker)
    
        self.params[7].category = "Table Settings"
        self.params[8].category = "Table Settings"
    
        self.params[9].category = "Database Query Settings"
        
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
    
        script_tool_funcs.add_selection(self, self.species_picker, self.species_storage)
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Generate Species Matrix'
        self.description = u'Generates a presence/absence matrix for a species, species group, or list of species'
        self.canRunInBackground = False
        self.category = "Output"
		
    def getParameterInfo(self):
        # Species_and_Groups
        param_1 = arcpy.Parameter()
        param_1.name = u'Species_and_Groups'
        param_1.displayName = u'Species and Groups'
        param_1.parameterType = 'Optional'
        param_1.direction = 'Input'
        param_1.datatype = u'String'
        param_1.filter.list = [u' ', u'all', u'-----', u'Amphibians', u'Anadromous', u'Arthropods', u'Crustacean', u'Dams_Indicators', u'FSSC_2012', u'Fish', u'Flow_Sensitive', u'Herps', u'Herps_Lentic', u'Herps_Lotic', u'Herps_Lotic_Lentic', u'Invertebrate', u'Meadows_Indicators', u'Mollusks', u'Narrow_25', u'Native_Fish', u'Non_Native_Fish', u'Paper_Species', u'Reptiles', u'Resident_Natives', u'SOS_Species_2016', u'USFS_2017', u'USFS_R5', u'Wide_Ranging', u'-----', u'PXL01 - African Clawed Frog', u'CRO06 - Amargosa Canyon speckled dace', u'CCN02 - Amargosa River pupfish', u'AME01 - Ameletidae family', u'RLC01 - American Bullfrog', u'CAS01 - American Shad', u'AMP01 - Amphizoidae family', u'ANI01 - Anisogammaridae family', u'APA01 - Apataniidae family', u'CTA01 - Aquatic gartersnake', u'STA01 - Arctic grayling', u'RCB01 - Argentine pearlfish', u'GCI01 - Arrow goby', u'BAC02 - Arroyo Toad', u'CGO01 - Arroyo chub', u'ASE01 - Asellidae family', u'AST01 - Astacidae family', u'ATH01 - Athericidae family', u'ATY01 - Atyidae family', u'HPH01 - Baja California Treefrog', u'SSA01 - Barred Pipefish', u'CCK01 - Bigeye marbled sculpin', u'CIC01 - Bigmouth buffalo', u'PPM01 - Bigscale logperch', u'IAM01 - Black bullhead', u'CPN01 - Black crappie', u'BAE01 - Black toad', u'COM02 - Blackfish (bin)', u'BLE01 - Blephariceridae family', u'IIF01 - Blue catfish', u'CGC01 - Blue chub', u'FLG01 - Bluefin killifish', u'CLM02 - Bluegill', u'CGE01 - Bonytail', u'BRA01 - Brachycentridae family', u'SSF01 - Brook Trout', u'GCI02 - Brook stickleback', u'SST01 - Brown Trout', u'IAN02 - Brown bullhead', u'SSC01 - Bull trout', u'CAL01 - Calamoceratidae family', u'SOT04 - California Coast fall Chinook salmon', u'BAB02 - California Toad', u'DDE01 - California giant salamander', u'SOM14 - California golden trout', u'PPC01 - California halibut', u'CFP01 - California killifish', u'STT01 - California newt', u'RRD01 - California red-legged frog', u'CLS01 - California roach', u'AAC01 - California tiger salamander', u'COM03 - California tilapia (hybrid)', u'HPC01 - California tree frog', u'CAP01 - Capniidae family', u'RRC01 - Cascades frog', u'SOM05 - Central California coast winter steelhead', u'SOK01 - Central Coast coho salmon', u'SOT08 - Central Valley fall Chinook salmon', u'SOT07 - Central Valley late fall Chinook salmon', u'SOT06 - Central Valley spring Chinook salmon', u'SOM06 - Central Valley steelhead', u'SOT05 - Central Valley winter Chinook salmon', u'GTT01 - Chameleon goby', u'IIP01 - Channel catfish', u'CTM01 - Checkered gartersnake', u'SOT09 - Chinook Salmon (bin)', u'CHI01 - Chirocephalidae family', u'CHL01 - Chloroperlidae family', u'SOK03 - Chum salmon', u'CLE02 - Clear Lake hitch', u'CCA03 - Clear Lake prickly sculpin', u'CLS04 - Clear Lake roach', u'CPC01 - Clear Lake splittail', u'EHT03 - Clear Lake tule perch', u'SOC01 - Coastal cutthroat trout', u'SSC02 - Coastal dolly varden', u'DDT01 - Coastal giant salamander', u'SOM09 - Coastal rainbow trout', u'AAT02 - Coastal tailed frog', u'GGA01 - Coastal threespine stickleback', u'CCA04 - Coastrange sculpin', u'SOK04 - Coho (bin)', u'SOC05 - Colorado River cutthroat trout', u'CPL01 - Colorado pikeminnow', u'CLG03 - Common Kingsnake', u'CCC01 - Common carp', u'CTS01 - Common gartersnake', u'COR01 - Cordulegastridae family', u'COR02 - Corduliidae family', u'COR03 - Corydalidae family', u'CCS04 - Cottonball Marsh pupfish', u"SSC04 - Couch's spadefoot toad", u'CST03 - Cow Head tui chub', u'CRA01 - Crangonyctidae family', u'SOC04 - Cutthroat trout (bin)', u'PPE01 - Del Norte Salamander', u'OHP01 - Delta smelt', u'CCM02 - Desert pupfish', u'DEU01 - Deuterophlebiidae family', u'PPG01 - Diamond turbot', u'DIX01 - Dixidae family', u'SSC03 - Dolly varden', u"PPD01 - Dunn's salamander", u'SOM12 - Eagle Lake rainbow trout', u'CSB05 - Eagle Lake tui chub', u'ELM01 - Elmidae family', u'CHS01 - Empty data bin - California roach', u'EPH01 - Ephemerellidae family', u'OTP01 - Eulachon', u'EUL01 - Eulichadidae family', u'CPP01 - Fathead minnow', u'CCL02 - Flannelmouth sucker', u'IPO01 - Flathead Catfish', u'RRB01 - Foothill yellow-legged frog', u'CTG01 - Giant gartersnake', u'GLO01 - Glossosomatidae family', u'GOE01 - Goeridae family', u'CNC01 - Golden shiner', u'CCA05 - Goldfish', u'PET02 - Goose Lake lamprey', u'SOM11 - Goose Lake redband trout', u'CCO02 - Goose Lake sucker', u'CST01 - Goose Lake tui chub', u'CCI01 - Grass carp', u'SSI01 - Great Basin spadefoot', u'BAC03 - Great Plains toad', u'CLC01 - Green sunfish', u'PXH01 - Green swordtail', u'CLP01 - Gualala roach', u'PPR01 - Guppy', u'CMC01 - Hardhead', u'HEL01 - Helicopsychidae family', u'HEP01 - Heptageniidae family', u'CSB02 - High Rock Springs tui chub', u'CLE04 - Hitch (bin)', u'CCO04 - Humboldt sucker', u'HYD01 - Hydrobiidae family', u'MMB01 - Inland silverside', u'GGA02 - Inland threespine stickleback', u'PBC01 - Inyo Mountains salamander', u'ISO01 - Isonychiidae family', u'CLS09 - Kaweah roach', u'SOM13 - Kern River rainbow trout', u'PLH01 - Kern brook lamprey', u'SOM04 - Klamath Mountains Province summer steelhead', u'SOM03 - Klamath Mountains Province winter steelhead', u'PES01 - Klamath River lamprey', u'CCP04 - Klamath lake sculpin', u'CCS01 - Klamath largescale sucker', u'CCR01 - Klamath smallscale sucker', u'CRO03 - Klamath speckled dace', u'CSB01 - Klamath tui chub', u'SOC03 - Lahontan cutthroat trout', u'CSB03 - Lahontan lake tui chub', u'CCP01 - Lahontan mountain sucker', u'CRE01 - Lahontan redside', u'CRO02 - Lahontan speckled dace', u'CSB04 - Lahontan stream tui chub', u'SSN01 - Lake trout', u'CMS01 - Largemouth Bass', u'LEP01 - Lepidostomatidae family', u'LEU01 - Leuctridae family', u'LIM01 - Limnephilidae family', u'SOM15 - Little Kern golden trout', u'CRO05 - Long Valley speckled dace', u'AAM03 - Long-toed Salamander', u'OST01 - Longfin smelt', u'GGM01 - Longjaw mudsucker', u'GCS01 - Longtail goby', u'CCL01 - Lost River sucker', u'CCK02 - Lower Klamath marbled sculpin', u'LUT01 - Lutrochidae family', u'LYM01 - Lymnaeidae family', u'MAC01 - Macromiidae family', u'CCK04 - Marbled Sculpin (bin)', u'MAR01 - Margaritiferidae family', u'SOM10 - McCloud River redband trout', u'MMB02 - Mississippi silversides', u'CCM01 - Modoc sucker', u'CSM01 - Mojave tui chub', u'CLE03 - Monterey hitch', u'CCO03 - Monterey sucker', u'SPW01 - Mountain whitefish', u'CLS06 - Navarro roach', u'NEM01 - Nemouridae family', u'AEC01 - Northern Alligator Lizard', u'PEF01 - Northern California brook lamprey', u'SOM02 - Northern California coast summer steelhead', u'SOM01 - Northern California coast winter steelhead', u'CLS03 - Northern coastal roach', u'AAM01 - Northern green sturgeon', u'RRP01 - Northern leopard frog', u'RRA01 - Northern red-legged frog', u'CLS08 - Northern roach', u'CTO01 - Northwestern gartersnake', u'AAG01 - Northwestern salamander', u'ODO01 - Odontoceridae family', u'RRP02 - Oregon spotted frog', u'CCR02 - Owens pupfish', u'CRO04 - Owens speckled dace', u'CCF01 - Owens sucker', u'CSB06 - Owens tui chub', u'PLP01 - Pacific brook lamprey', u'HPR01 - Pacific chorus frog', u'CCH01 - Pacific herring', u'PET01 - Pacific lamprey', u'SOC02 - Paiute cutthroat trout', u'CCB02 - Paiute sculpin', u'PEL01 - Peltoperlidae family', u'PER01 - Perlidae family', u'PER02 - Perlodidae family', u'PET03 - Petaluridae family', u'PHI01 - Philopotamidae family', u'PHR01 - Phryganeidae family', u'SOG01 - Pink salmon', u'CST02 - Pit River tui chub', u'CCP02 - Pit sculpin', u'PLL01 - Pit-Klamath brook lamprey', u'PLE01 - Pleuroceridae family', u'PPG02 - Porthole livebearer', u'CCA02 - Prickly sculpin', u'PSY01 - Psychomyiidae family', u'PTE01 - Pteronarcyidae family', u'PTI01 - Ptilodactylidae family', u'CLG01 - Pumpkinseed', u'SOM17 - Rainbow Trout (Summer Steelhead)', u'SOM18 - Rainbow Trout (Winter Steelhead)', u'FLP01 - Rainwater killifish ', u'CXT01 - Razorback sucker', u'CLS02 - Red Hills roach', u'CCL03 - Red shiner', u'STR01 - Red-bellied newt', u'BAP01 - Red-spotted toad', u'SOM16 - Redband trout (bin)', u'CTZ01 - Redbelly tilapia', u'CLM03 - Redear sunfish', u'CMC02 - Redeye bass', u'CCP03 - Reticulate sculpin', u'RHY01 - Rhyacophilidae family', u'CCG01 - Riffle sculpin', u'PLA01 - River lamprey', u'CCA01 - Rough sculpin', u'STG01 - Rough-skinned newt', u'EHT02 - Russian River tule perch', u'COM01 - Sacramento blackfish', u'CLE01 - Sacramento hitch', u'CAI01 - Sacramento perch', u'CPG01 - Sacramento pikeminnow', u'CRO01 - Sacramento speckled dace', u'CPM01 - Sacramento splittail', u'CCO01 - Sacramento sucker', u'EHT01 - Sacramento tule perch', u'PPL01 - Sailfin molly', u'CCS03 - Salt Creek pupfish', u'CTS02 - San Francisco Gartersnake', u'CRO07 - Santa Ana speckled dace', u'CCS02 - Santa Ana sucker', u'PAN01 - Santa Cruz Black Salamander', u'AAM04 - Santa Cruz long-toed Salamander', u'CCN01 - Saratoga Springs pupfish', u'SCI01 - Scirtidae family', u'CCX01 - Sculpin spp (bin)', u'SER01 - Sericostomatidae family', u'CCA06 - Sharpnose sculpin', u'PAI01 - Shasta Black Salamander', u'GGA04 - Shay Creek stickleback', u'GTB01 - Shimofuri goby', u'ECA01 - Shiner perch', u'SCP01 - Shortfin corvina', u'PPM02 - Shortfin molly', u'CCB01 - Shortnose sucker', u'CCN04 - Shoshone pupfish', u'RRM01 - Sierra Madre yellow-legged frog', u'RRS01 - Sierra Nevada yellow-legged frog', u'CTC01 - Sierra gartersnake', u'STS01 - Sierra newt', u'HPS01 - Sierran Treefrog', u'PPS02 - Siskiyou Mountains Salamander', u'CCT02 - Slender sculpin', u'CMD01 - Smallmouth Bass', u'SON01 - Sockeye (Kokanee) Salmon', u'SOM07 - South Central California coast steelhead', u'CTS03 - South Coast Gartersnake', u'AEC02 - Southern Alligator Lizard', u'SOM08 - Southern California steelhead', u'SOK02 - Southern Oregon Northern California coast coho salmon', u'SOT03 - Southern Oregon Northern California coast fall Chinook salmon', u'CLS05 - Southern coastal roach', u'AAM02 - Southern green sturgeon', u'RRV01 - Southern torrent salamander', u'PAF01 - Speckled Black Salamander', u'CRO08 - Speckled Dace (bin)', u'SPH01 - Sphaeriidae family', u'CMP01 - Spotted bass', u'CLA01 - Staghorn sculpin', u'PPS01 - Starry flounder', u'SOM19 - Stocked Rainbow Trout (bin)', u'MMS01 - Striped bass', u'MMC02 - Striped mullet', u'OHP02 - Surf smelt', u'TAE01 - Taeniopterygidae family', u'CCT01 - Tahoe sucker', u'TAN01 - Tanyderidae family', u'CCN03 - Tecopa pupfish', u'CTT01 - Tench', u'CSC01 - Thicktail chub', u'CDP01 - Threadfin shad', u'GGA05 - Threespine stickleback (bin)', u'GEN01 - Tidewater goby', u'CLS07 - Tomales roach', u'AAA01 - Topsmelt', u'CSB07 - Tui chub bin', u'EHT04 - Tule perch (bin)', u'CTH01 - Twp-striped gartersnake', u'UEN01 - Uenoidae family', u'GGA03 - Unarmored threespine stickleback', u'UNI01 - Unionidae family', u'CCK03 - Upper Klamath marbled sculpin', u'SOT01 - Upper Klamath-Trinity fall Chinook salmon', u'SOT02 - Upper Klamath-Trinity spring Chinook salmon', u'OHN01 - Wakasagi', u'PAV01 - Wandering Salamander', u'CLG02 - Warmouth', u'EAM01 - Western Pond Turtle', u'PLR01 - Western brook lamprey', u'PGA01 - Western mosquitofish', u'EEM01 - Western pond turtle', u'SSH01 - Western spadefoot toad', u'CTE01 - Western terrestrial gartersnake', u'BAB01 - Western toad', u'MMC01 - White bass', u'IAC01 - White catfish', u'CPA01 - White crappie', u'AAT01 - White sturgeon', u"BAW01 - Woodhouse's toad", u'IAN01 - Yellow bullhead', u'PPF01 - Yellow perch', u'GAF01 - Yellowfin goby', u'BAC01 - Yosemite Toad', u'ZZZ01 - temp']

        # Species_and_Groups_Holder
        param_2 = arcpy.Parameter()
        param_2.name = u'Species_and_Groups_Holder'
        param_2.displayName = u'Species and Groups Holder'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'
        param_2.multiValue = True

        # Presence_Types
        param_3 = arcpy.Parameter()
        param_3.name = u'Presence_Types'
        param_3.displayName = u'Presence Types'
        param_3.parameterType = 'Required'
        param_3.direction = 'Input'
        param_3.datatype = u'String'
        param_3.multiValue = True
        param_3.filter.list = [u'1 - Observed - backed up by data, this is verifiable', u'2 - Historical Range - Expert opinion source as noted', u'3 - Extant Range - Expert opinion says it is here', u'4 - Extant Range - Modeled to exist here currently', u'5 -  Extirpated -  confirmed by experts', u'6 - Translocated - Expert Opinion', u'7 - Translocated - Observed', u'8 - Historical Range - Modeled', u'9 - Reintroduced', u'10 - Historical Range - Observed']

        # Output_Folder
        param_4 = arcpy.Parameter()
        param_4.name = u'Output_Folder'
        param_4.displayName = u'Output Folder'
        param_4.parameterType = 'Required'
        param_4.direction = 'Input'
        param_4.datatype = u'Folder'

        # Present_Value
        param_5 = arcpy.Parameter()
        param_5.name = u'Present_Value'
        param_5.displayName = u'Present Value'
        param_5.parameterType = 'Required'
        param_5.direction = 'Input'
        param_5.datatype = u'String'
        param_5.value = u'1'

        # Not_Present_Value
        param_6 = arcpy.Parameter()
        param_6.name = u'Not_Present_Value'
        param_6.displayName = u'Not Present Value'
        param_6.parameterType = 'Required'
        param_6.direction = 'Input'
        param_6.datatype = u'String'
        param_6.value = u'0'

        # QC_Data_Only
        param_7 = arcpy.Parameter()
        param_7.name = u'QC_Data_Only'
        param_7.displayName = u'QC Data Only'
        param_7.parameterType = 'Optional'
        param_7.direction = 'Input'
        param_7.datatype = u'Boolean'
        param_7.value = u'true'

        # Use_Scientific_Names
        param_8 = arcpy.Parameter()
        param_8.name = u'Use_Scientific_Names'
        param_8.displayName = u'Use Scientific Names'
        param_8.parameterType = 'Optional'
        param_8.direction = 'Input'
        param_8.datatype = u'Boolean'
        param_8.value = u'false'

        # Zone_Table
        param_9 = arcpy.Parameter()
        param_9.name = u'Zone_Table'
        param_9.displayName = u'Zone Table'
        param_9.parameterType = 'Required'
        param_9.direction = 'Input'
        param_9.datatype = u'String'
        param_9.value = u'HUC12FullState'

        # Zone_Field
        param_10 = arcpy.Parameter()
        param_10.name = u'Zone_Field'
        param_10.displayName = u'Zone Field'
        param_10.parameterType = 'Required'
        param_10.direction = 'Input'
        param_10.datatype = u'String'
        param_10.value = u'HUC_12'

        # Database_Query
        param_11 = arcpy.Parameter()
        param_11.name = u'Database_Query'
        param_11.displayName = u'Database Query'
        param_11.parameterType = 'Optional'
        param_11.direction = 'Input'
        param_11.datatype = u'String'

        return [param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9, param_10, param_11]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_make_matrix.py'):
            """
            THIS SCRIPT IS PARTWAY THROUGH A TRANSLATION FROM GLOBAL TO LOCAL VARIABLES. NEEDS TO HAVE config_ VARIABLES REMOVED
            FROM LOCAL FUNCTIONS.
            """
            
            import csv
            import os
            import sys
            
            import six
            
            import arcpy
            initial_dir = os.getcwd()
            
            from PISCES import local_vars
            from PISCES import funcs
            from PISCES import log
            from PISCES import script_tool_funcs
            
            def get_zones(zones_table, zone_field):
            
                rows_index = {}
                all_zones = []
                log.write("Getting zones", 1)
            
                query = "select distinct %s as myvalue from %s" % (zone_field, zones_table)
            
                db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
                try:
                    results = db_cursor.execute(query)
            
                    for row in results:
            
                        rows_index[str(row.myvalue)] = {zone_field: row.myvalue}
            
                        all_zones.append(row.myvalue)
                finally:
                    funcs.db_close(db_cursor, db_conn)
            
                return all_zones, rows_index
            
            
            def get_species(species, qc_flag, zones, rows_index, presence_types, true_value, false_value, override_query):
            
                log.write("getting data for %s" % species, 1)
            
                if override_query:
                    query = override_query
                else:
                    if qc_flag:
                        query = "select distinct zone_id from observations, observation_collections where observations.species_id = ? and observations.presence_type in %s and observation_collections.observation_id = observations.objectid and observation_collections.collection_id in (%s)" % (presence_types, local_vars.hq_collections)
                    else:
                        query = "select distinct zone_id from observations where species_id = ? and presence_type in %s" % presence_types
            
                db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
                try:
                    results = db_cursor.execute(query, species)
            
                    present_hucs = []
            
                    for t_row in results:
                        present_hucs.append(t_row.zone_id)
            
                    for zone in present_hucs:
                        if zone in rows_index:  # it might not because our study area may be smaller than we track
                            rows_index[str(zone)][species] = true_value
            
                    not_in_hucs = list(set(zones) - set(present_hucs))
                    #not_in_hucs = list(set(present_hucs) & set(all_zones)) # get the hucs it's NOT in and explicitly set those rows to False - we could also have just set them all to False beforehand. oops
            
                    for zone in not_in_hucs:
                        if zone in rows_index:
                            rows_index[str(zone)][species] = false_value
                finally:
                    funcs.db_close(db_cursor, db_conn)
            
                return rows_index
            
            def write_csv(filename, headers, rows, sci_name_output, header_row=None):
                    log.write("Writing CSV out to %s" % filename, 1)
                    csvfile = open(filename, 'wb')
            
                    csvwriter = csv.DictWriter(csvfile, headers, quoting=csv.QUOTE_NONNUMERIC)
                    #csvwriter.writeheader() # writeheader is new in 2.7
                    headerrow = {}
                    if not header_row:
                        if sci_name_output:
                            for row in headers:
                                headerrow[row] = local_vars.all_fish[row].sci_name  # make a dict object where the lookup that the dictwriter will use has a value of the header
                        else:
                            for row in headers:
                                headerrow[row] = local_vars.all_fish[row].species  # make a dict object where the lookup that the dictwriter will use has a value of the header
            
                    else:
                        headerrow = header_row
            
                    csvwriter.writerow(headerrow)  # write out the header we just made
            
                    for tkey in rows.keys():
                            csvwriter.writerow(rows[tkey])
            
                    csvfile.close()
                    del csvwriter
            
            
            def make_matrix(species_list, output_folder, presence_types="1,3,6,7,9", true_value=1, false_value=0, qc_flag=True, use_scientific_name=False, override_query=False, zones_table="HUC12FullState", zone_field="HUC_12", out_name=""):
                """
                    Produces a matrix of species presence information where the rows are zone ids (huc 12s) and the columns are species names.
                    Presence is denoted using a true or false value in each cell
                :param species_list: A python list of species codes, or a single species group as a string. It currently does not
                    behave like other tools where a mix of types works. If you do need to mix types, do so as a string with
                    semicolons separating values to emulate the behavior of ArcGIS script tools.
                :param output_folder: The folder that the matrix should be placed in. The name is automatically determined
                :param presence_types: A string separated list of PISCES presence types to look for. Default is "1,3,6,7,9" for current presence.
                :param true_value: What value should be used in the matrix when a species is present in the zone? Defaults to "1"
                :param false_value: What value should be used in the matrix when a species is *not* present in the zone? Defaults to "0?
                :param qc_flag: Indicates whether only QCed data should be used. In the future this may be migrated to a collection ID input
                :param use_scientific_name: When True, column headers will use the species scientific name. When False (default), uses common name
                :param override_query: Advanced option allowing you to pass in your own query that retrieves the relevant records for a species. Should be of the form "select distinct zone_id from observations where species_id = ?"
                :param zones_table: If using an alternative set of zones, provide the table name
                :param zone_field: If using an alternative set of zones, provide the key field that indicates zones.
                :return:
                """
                if type(species_list) != list:
                    species_list = funcs.text_to_species_list(species_list)
                if len(species_list) == 0:
                    raise ValueError("No valid species or groups specified - make sure to use a species FID or a species group identifier")
            
                presence_types = "({})".format(presence_types)
            
                all_zones, rows_index = get_zones(zones_table, zone_field)
            
                headers = [zone_field]
                header_row = {}
                header_row[zone_field] = zone_field
                for taxa in species_list:
                    headers.append(taxa)  # add the common name to the headers instead of the pisces name
                    if use_scientific_name:
                        header_row[taxa] = local_vars.all_fish[taxa].sci_name
                    else:
                        header_row[taxa] = local_vars.all_fish[taxa].species
            
                    rows_index = get_species(taxa, qc_flag, all_zones, rows_index, presence_types, true_value, false_value, override_query=override_query)  # get the data, modify rows_index and return it
            
                out_name = "{}_{}_presence_matrix.csv".format(os.path.join(output_folder, zones_table), out_name)
                write_csv(out_name, headers, rows_index, use_scientific_name, header_row)
            
            
            if __name__ == "__main__":
            
                config_species_picker = parameters[0].valueAsText
                config_species_list = parameters[1].valueAsText
                config_presence_values = parameters[2].valueAsText
                config_outfolder = parameters[3].valueAsText
                config_true = parameters[4].valueAsText
                config_false = parameters[5].valueAsText
                config_qc_flag = parameters[6]
                config_scientific_name = parameters[7]
                config_zones_table = parameters[8].valueAsText
                config_zone_field = parameters[9].valueAsText
                config_query_override = parameters[10].valueAsText
            
                local_vars.start(arc_script=1)
            
                # new presence value code
                presence_values = script_tool_funcs.obs_type_selection_box_to_list(config_presence_values)
                config_presence_values = ",".join([six.text_type(val) for val in presence_values])  # need to cast back to string to use in a join operation
            
                # old presence value code
                """
                if not config_presence_values:
                    config_presence_values = "(1,3,6,7,9)"
                elif config_presence_values == "current":
                    config_presence_values = "(1,3,6,7,9)"
                elif config_presence_values == "historic":
                    config_presence_values = "(2,5,10)"
                    log.write('using historic and non-translocated current presence values (%s)' % config_presence_values, 1)
                elif config_presence_values == "notrans":
                    config_presence_values = "(1,3,9)"
                else:
                    #elif (str(config_presence_values).find(",") > 0 or str(config_presence_values).find(";") > 0) and not str(config_presence_values).find("("):  # if it's a list of numbers that doesn't include parens
                    config_presence_values = "(%s)" % config_presence_values
                """
            
                if not config_zones_table:
                    config_zones_table = "HUC12FullState"
                if not config_zone_field:
                    config_zone_field = "HUC_12"
            
                if not config_outfolder:
                    config_outfolder = initial_dir
            
                if not config_true:
                    config_true = True
            
                if not config_false:
                    config_false = False
            
                if not config_qc_flag:
                    config_qc_flag = True
            
                if not config_scientific_name:
                    config_scientific_name = False
            
                make_matrix(config_species_list, config_outfolder, config_presence_values, config_true, config_false, config_qc_flag, config_scientific_name, config_query_override, config_zones_table, config_zone_field)
            

class LookUpRecords(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Output\LookUpRecords"""
    import arcpy
    
    import os, sys
    
    from PISCES import local_vars
    from PISCES import script_tool_funcs
    
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
        self.lookup_field = 1
        self.storage_field = 2
        self.observation_type_filter = 3
        self.collection_picker = 4
        self.collection_storage = 5
        self.blank = ""
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        l_fish = script_tool_funcs.get_fish_filter()
       
        self.params[0].value = "HUC12s"
    
        script_tool_funcs.make_obs_type_picker(self, self.observation_type_filter)
        script_tool_funcs.make_species_group_picker(self,self.lookup_field,self.storage_field)
        script_tool_funcs.make_collections_picker(self,self.collection_picker, self.collection_storage)
        
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
    
        # checks the species field for commands
        script_tool_funcs.validate_species(self.params[self.lookup_field]) # runs operations like "load"
    
        #script_tool_funcs.autocomplete_full_field(self,self.lookup_field)
        script_tool_funcs.add_selection(self,self.lookup_field,self.storage_field)
    
        script_tool_funcs.add_selection(self,self.collection_picker,self.collection_storage)
        
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Look Up Records'
        self.canRunInBackground = False
        self.category = "Output"
		
    def getParameterInfo(self):
        # Zones_of_Interest
        param_1 = arcpy.Parameter()
        param_1.name = u'Zones_of_Interest'
        param_1.displayName = u'Zones of Interest'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'Feature Layer'
        param_1.value = u'HUC12s'

        # Species_and_Groups_to_Limit_Records_to
        param_2 = arcpy.Parameter()
        param_2.name = u'Species_and_Groups_to_Limit_Records_to'
        param_2.displayName = u'Species and Groups to Limit Records to'
        param_2.parameterType = 'Optional'
        param_2.direction = 'Input'
        param_2.datatype = u'String'
        param_2.filter.list = [u' ', u'all', u'-----', u'Amphibians', u'Anadromous', u'Arthropods', u'Crustacean', u'Dams_Indicators', u'FSSC_2012', u'Fish', u'Flow_Sensitive', u'Herps', u'Herps_Lentic', u'Herps_Lotic', u'Herps_Lotic_Lentic', u'Invertebrate', u'Meadows_Indicators', u'Mollusks', u'Narrow_25', u'Native_Fish', u'Non_Native_Fish', u'Paper_Species', u'Reptiles', u'Resident_Natives', u'SOS_Species_2016', u'USFS_2017', u'USFS_R5', u'Wide_Ranging', u'-----', u'PXL01 - African Clawed Frog', u'CRO06 - Amargosa Canyon speckled dace', u'CCN02 - Amargosa River pupfish', u'AME01 - Ameletidae family', u'RLC01 - American Bullfrog', u'CAS01 - American Shad', u'AMP01 - Amphizoidae family', u'ANI01 - Anisogammaridae family', u'APA01 - Apataniidae family', u'CTA01 - Aquatic gartersnake', u'STA01 - Arctic grayling', u'RCB01 - Argentine pearlfish', u'GCI01 - Arrow goby', u'BAC02 - Arroyo Toad', u'CGO01 - Arroyo chub', u'ASE01 - Asellidae family', u'AST01 - Astacidae family', u'ATH01 - Athericidae family', u'ATY01 - Atyidae family', u'HPH01 - Baja California Treefrog', u'SSA01 - Barred Pipefish', u'CCK01 - Bigeye marbled sculpin', u'CIC01 - Bigmouth buffalo', u'PPM01 - Bigscale logperch', u'IAM01 - Black bullhead', u'CPN01 - Black crappie', u'BAE01 - Black toad', u'COM02 - Blackfish (bin)', u'BLE01 - Blephariceridae family', u'IIF01 - Blue catfish', u'CGC01 - Blue chub', u'FLG01 - Bluefin killifish', u'CLM02 - Bluegill', u'CGE01 - Bonytail', u'BRA01 - Brachycentridae family', u'SSF01 - Brook Trout', u'GCI02 - Brook stickleback', u'SST01 - Brown Trout', u'IAN02 - Brown bullhead', u'SSC01 - Bull trout', u'CAL01 - Calamoceratidae family', u'SOT04 - California Coast fall Chinook salmon', u'BAB02 - California Toad', u'DDE01 - California giant salamander', u'SOM14 - California golden trout', u'PPC01 - California halibut', u'CFP01 - California killifish', u'STT01 - California newt', u'RRD01 - California red-legged frog', u'CLS01 - California roach', u'AAC01 - California tiger salamander', u'COM03 - California tilapia (hybrid)', u'HPC01 - California tree frog', u'CAP01 - Capniidae family', u'RRC01 - Cascades frog', u'SOM05 - Central California coast winter steelhead', u'SOK01 - Central Coast coho salmon', u'SOT08 - Central Valley fall Chinook salmon', u'SOT07 - Central Valley late fall Chinook salmon', u'SOT06 - Central Valley spring Chinook salmon', u'SOM06 - Central Valley steelhead', u'SOT05 - Central Valley winter Chinook salmon', u'GTT01 - Chameleon goby', u'IIP01 - Channel catfish', u'CTM01 - Checkered gartersnake', u'SOT09 - Chinook Salmon (bin)', u'CHI01 - Chirocephalidae family', u'CHL01 - Chloroperlidae family', u'SOK03 - Chum salmon', u'CLE02 - Clear Lake hitch', u'CCA03 - Clear Lake prickly sculpin', u'CLS04 - Clear Lake roach', u'CPC01 - Clear Lake splittail', u'EHT03 - Clear Lake tule perch', u'SOC01 - Coastal cutthroat trout', u'SSC02 - Coastal dolly varden', u'DDT01 - Coastal giant salamander', u'SOM09 - Coastal rainbow trout', u'AAT02 - Coastal tailed frog', u'GGA01 - Coastal threespine stickleback', u'CCA04 - Coastrange sculpin', u'SOK04 - Coho (bin)', u'SOC05 - Colorado River cutthroat trout', u'CPL01 - Colorado pikeminnow', u'CLG03 - Common Kingsnake', u'CCC01 - Common carp', u'CTS01 - Common gartersnake', u'COR01 - Cordulegastridae family', u'COR02 - Corduliidae family', u'COR03 - Corydalidae family', u'CCS04 - Cottonball Marsh pupfish', u"SSC04 - Couch's spadefoot toad", u'CST03 - Cow Head tui chub', u'CRA01 - Crangonyctidae family', u'SOC04 - Cutthroat trout (bin)', u'PPE01 - Del Norte Salamander', u'OHP01 - Delta smelt', u'CCM02 - Desert pupfish', u'DEU01 - Deuterophlebiidae family', u'PPG01 - Diamond turbot', u'DIX01 - Dixidae family', u'SSC03 - Dolly varden', u"PPD01 - Dunn's salamander", u'SOM12 - Eagle Lake rainbow trout', u'CSB05 - Eagle Lake tui chub', u'ELM01 - Elmidae family', u'CHS01 - Empty data bin - California roach', u'EPH01 - Ephemerellidae family', u'OTP01 - Eulachon', u'EUL01 - Eulichadidae family', u'CPP01 - Fathead minnow', u'CCL02 - Flannelmouth sucker', u'IPO01 - Flathead Catfish', u'RRB01 - Foothill yellow-legged frog', u'CTG01 - Giant gartersnake', u'GLO01 - Glossosomatidae family', u'GOE01 - Goeridae family', u'CNC01 - Golden shiner', u'CCA05 - Goldfish', u'PET02 - Goose Lake lamprey', u'SOM11 - Goose Lake redband trout', u'CCO02 - Goose Lake sucker', u'CST01 - Goose Lake tui chub', u'CCI01 - Grass carp', u'SSI01 - Great Basin spadefoot', u'BAC03 - Great Plains toad', u'CLC01 - Green sunfish', u'PXH01 - Green swordtail', u'CLP01 - Gualala roach', u'PPR01 - Guppy', u'CMC01 - Hardhead', u'HEL01 - Helicopsychidae family', u'HEP01 - Heptageniidae family', u'CSB02 - High Rock Springs tui chub', u'CLE04 - Hitch (bin)', u'CCO04 - Humboldt sucker', u'HYD01 - Hydrobiidae family', u'MMB01 - Inland silverside', u'GGA02 - Inland threespine stickleback', u'PBC01 - Inyo Mountains salamander', u'ISO01 - Isonychiidae family', u'CLS09 - Kaweah roach', u'SOM13 - Kern River rainbow trout', u'PLH01 - Kern brook lamprey', u'SOM04 - Klamath Mountains Province summer steelhead', u'SOM03 - Klamath Mountains Province winter steelhead', u'PES01 - Klamath River lamprey', u'CCP04 - Klamath lake sculpin', u'CCS01 - Klamath largescale sucker', u'CCR01 - Klamath smallscale sucker', u'CRO03 - Klamath speckled dace', u'CSB01 - Klamath tui chub', u'SOC03 - Lahontan cutthroat trout', u'CSB03 - Lahontan lake tui chub', u'CCP01 - Lahontan mountain sucker', u'CRE01 - Lahontan redside', u'CRO02 - Lahontan speckled dace', u'CSB04 - Lahontan stream tui chub', u'SSN01 - Lake trout', u'CMS01 - Largemouth Bass', u'LEP01 - Lepidostomatidae family', u'LEU01 - Leuctridae family', u'LIM01 - Limnephilidae family', u'SOM15 - Little Kern golden trout', u'CRO05 - Long Valley speckled dace', u'AAM03 - Long-toed Salamander', u'OST01 - Longfin smelt', u'GGM01 - Longjaw mudsucker', u'GCS01 - Longtail goby', u'CCL01 - Lost River sucker', u'CCK02 - Lower Klamath marbled sculpin', u'LUT01 - Lutrochidae family', u'LYM01 - Lymnaeidae family', u'MAC01 - Macromiidae family', u'CCK04 - Marbled Sculpin (bin)', u'MAR01 - Margaritiferidae family', u'SOM10 - McCloud River redband trout', u'MMB02 - Mississippi silversides', u'CCM01 - Modoc sucker', u'CSM01 - Mojave tui chub', u'CLE03 - Monterey hitch', u'CCO03 - Monterey sucker', u'SPW01 - Mountain whitefish', u'CLS06 - Navarro roach', u'NEM01 - Nemouridae family', u'AEC01 - Northern Alligator Lizard', u'PEF01 - Northern California brook lamprey', u'SOM02 - Northern California coast summer steelhead', u'SOM01 - Northern California coast winter steelhead', u'CLS03 - Northern coastal roach', u'AAM01 - Northern green sturgeon', u'RRP01 - Northern leopard frog', u'RRA01 - Northern red-legged frog', u'CLS08 - Northern roach', u'CTO01 - Northwestern gartersnake', u'AAG01 - Northwestern salamander', u'ODO01 - Odontoceridae family', u'RRP02 - Oregon spotted frog', u'CCR02 - Owens pupfish', u'CRO04 - Owens speckled dace', u'CCF01 - Owens sucker', u'CSB06 - Owens tui chub', u'PLP01 - Pacific brook lamprey', u'HPR01 - Pacific chorus frog', u'CCH01 - Pacific herring', u'PET01 - Pacific lamprey', u'SOC02 - Paiute cutthroat trout', u'CCB02 - Paiute sculpin', u'PEL01 - Peltoperlidae family', u'PER01 - Perlidae family', u'PER02 - Perlodidae family', u'PET03 - Petaluridae family', u'PHI01 - Philopotamidae family', u'PHR01 - Phryganeidae family', u'SOG01 - Pink salmon', u'CST02 - Pit River tui chub', u'CCP02 - Pit sculpin', u'PLL01 - Pit-Klamath brook lamprey', u'PLE01 - Pleuroceridae family', u'PPG02 - Porthole livebearer', u'CCA02 - Prickly sculpin', u'PSY01 - Psychomyiidae family', u'PTE01 - Pteronarcyidae family', u'PTI01 - Ptilodactylidae family', u'CLG01 - Pumpkinseed', u'SOM17 - Rainbow Trout (Summer Steelhead)', u'SOM18 - Rainbow Trout (Winter Steelhead)', u'FLP01 - Rainwater killifish ', u'CXT01 - Razorback sucker', u'CLS02 - Red Hills roach', u'CCL03 - Red shiner', u'STR01 - Red-bellied newt', u'BAP01 - Red-spotted toad', u'SOM16 - Redband trout (bin)', u'CTZ01 - Redbelly tilapia', u'CLM03 - Redear sunfish', u'CMC02 - Redeye bass', u'CCP03 - Reticulate sculpin', u'RHY01 - Rhyacophilidae family', u'CCG01 - Riffle sculpin', u'PLA01 - River lamprey', u'CCA01 - Rough sculpin', u'STG01 - Rough-skinned newt', u'EHT02 - Russian River tule perch', u'COM01 - Sacramento blackfish', u'CLE01 - Sacramento hitch', u'CAI01 - Sacramento perch', u'CPG01 - Sacramento pikeminnow', u'CRO01 - Sacramento speckled dace', u'CPM01 - Sacramento splittail', u'CCO01 - Sacramento sucker', u'EHT01 - Sacramento tule perch', u'PPL01 - Sailfin molly', u'CCS03 - Salt Creek pupfish', u'CTS02 - San Francisco Gartersnake', u'CRO07 - Santa Ana speckled dace', u'CCS02 - Santa Ana sucker', u'PAN01 - Santa Cruz Black Salamander', u'AAM04 - Santa Cruz long-toed Salamander', u'CCN01 - Saratoga Springs pupfish', u'SCI01 - Scirtidae family', u'CCX01 - Sculpin spp (bin)', u'SER01 - Sericostomatidae family', u'CCA06 - Sharpnose sculpin', u'PAI01 - Shasta Black Salamander', u'GGA04 - Shay Creek stickleback', u'GTB01 - Shimofuri goby', u'ECA01 - Shiner perch', u'SCP01 - Shortfin corvina', u'PPM02 - Shortfin molly', u'CCB01 - Shortnose sucker', u'CCN04 - Shoshone pupfish', u'RRM01 - Sierra Madre yellow-legged frog', u'RRS01 - Sierra Nevada yellow-legged frog', u'CTC01 - Sierra gartersnake', u'STS01 - Sierra newt', u'HPS01 - Sierran Treefrog', u'PPS02 - Siskiyou Mountains Salamander', u'CCT02 - Slender sculpin', u'CMD01 - Smallmouth Bass', u'SON01 - Sockeye (Kokanee) Salmon', u'SOM07 - South Central California coast steelhead', u'CTS03 - South Coast Gartersnake', u'AEC02 - Southern Alligator Lizard', u'SOM08 - Southern California steelhead', u'SOK02 - Southern Oregon Northern California coast coho salmon', u'SOT03 - Southern Oregon Northern California coast fall Chinook salmon', u'CLS05 - Southern coastal roach', u'AAM02 - Southern green sturgeon', u'RRV01 - Southern torrent salamander', u'PAF01 - Speckled Black Salamander', u'CRO08 - Speckled Dace (bin)', u'SPH01 - Sphaeriidae family', u'CMP01 - Spotted bass', u'CLA01 - Staghorn sculpin', u'PPS01 - Starry flounder', u'SOM19 - Stocked Rainbow Trout (bin)', u'MMS01 - Striped bass', u'MMC02 - Striped mullet', u'OHP02 - Surf smelt', u'TAE01 - Taeniopterygidae family', u'CCT01 - Tahoe sucker', u'TAN01 - Tanyderidae family', u'CCN03 - Tecopa pupfish', u'CTT01 - Tench', u'CSC01 - Thicktail chub', u'CDP01 - Threadfin shad', u'GGA05 - Threespine stickleback (bin)', u'GEN01 - Tidewater goby', u'CLS07 - Tomales roach', u'AAA01 - Topsmelt', u'CSB07 - Tui chub bin', u'EHT04 - Tule perch (bin)', u'CTH01 - Twp-striped gartersnake', u'UEN01 - Uenoidae family', u'GGA03 - Unarmored threespine stickleback', u'UNI01 - Unionidae family', u'CCK03 - Upper Klamath marbled sculpin', u'SOT01 - Upper Klamath-Trinity fall Chinook salmon', u'SOT02 - Upper Klamath-Trinity spring Chinook salmon', u'OHN01 - Wakasagi', u'PAV01 - Wandering Salamander', u'CLG02 - Warmouth', u'EAM01 - Western Pond Turtle', u'PLR01 - Western brook lamprey', u'PGA01 - Western mosquitofish', u'EEM01 - Western pond turtle', u'SSH01 - Western spadefoot toad', u'CTE01 - Western terrestrial gartersnake', u'BAB01 - Western toad', u'MMC01 - White bass', u'IAC01 - White catfish', u'CPA01 - White crappie', u'AAT01 - White sturgeon', u"BAW01 - Woodhouse's toad", u'IAN01 - Yellow bullhead', u'PPF01 - Yellow perch', u'GAF01 - Yellowfin goby', u'BAC01 - Yosemite Toad', u'ZZZ01 - temp']

        # Species_and_Groups_Holder
        param_3 = arcpy.Parameter()
        param_3.name = u'Species_and_Groups_Holder'
        param_3.displayName = u'Species and Groups Holder'
        param_3.parameterType = 'Optional'
        param_3.direction = 'Input'
        param_3.datatype = u'String'
        param_3.multiValue = True

        # Limit_to_Presence_Types
        param_4 = arcpy.Parameter()
        param_4.name = u'Limit_to_Presence_Types'
        param_4.displayName = u'Limit to Presence Types'
        param_4.parameterType = 'Optional'
        param_4.direction = 'Input'
        param_4.datatype = u'String'
        param_4.multiValue = True
        param_4.filter.list = [u'1 - Observed - backed up by data, this is verifiable', u'2 - Historical Range - Expert opinion source as noted', u'3 - Extant Range - Expert opinion says it is here', u'4 - Extant Range - Modeled to exist here currently', u'5 -  Extirpated -  confirmed by experts', u'6 - Translocated - Expert Opinion', u'7 - Translocated - Observed', u'8 - Historical Range - Modeled', u'9 - Reintroduced', u'10 - Historical Range - Observed']

        # Limit_to_Collections
        param_5 = arcpy.Parameter()
        param_5.name = u'Limit_to_Collections'
        param_5.displayName = u'Limit to Collections'
        param_5.parameterType = 'Optional'
        param_5.direction = 'Input'
        param_5.datatype = u'String'
        param_5.filter.list = [u'Best available knowledge 8/2013', u'Delivered USFS 12/15/2011', u'Fish Species of Special Concern - Final', u'HUC 12 Update - Oct 2013', u'HUC 12 Update - Oct 2013', u'Non native QC 12/12/13', u'Pre QC', u'QC 2013', u'QC Update 2017']

        # Limit_to_Collections_Holder
        param_6 = arcpy.Parameter()
        param_6.name = u'Limit_to_Collections_Holder'
        param_6.displayName = u'Limit to Collections Holder'
        param_6.parameterType = 'Optional'
        param_6.direction = 'Input'
        param_6.datatype = u'String'
        param_6.multiValue = True

        # Output_Table
        param_7 = arcpy.Parameter()
        param_7.name = u'Output_Table'
        param_7.displayName = u'Output Table'
        param_7.parameterType = 'Derived'
        param_7.direction = 'Output'
        param_7.datatype = u'Table'

        return [param_1, param_2, param_3, param_4, param_5, param_6, param_7]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_query_sources.py'):
            '''provides an entry point for these functions from an ArcGIS 10 Toolbox'''
            
            import traceback
            
            import arcpy
            
            from PISCES import local_vars
            from PISCES import log
            from PISCES import funcs
            from PISCES import script_tool_funcs
            from PISCES import api
            
            local_vars.start(arc_script=1)
            
            huc_layer_index = 0
            species_picker_index = 1
            species_list_index = 2
            #join_results_index = 3
            observation_types_index = 3
            collections_picker_index = 4
            collections_storage_index = 5
            output_table_index = 6
            
            layer = parameters[huc_layer_index].valueAsText
            config_species_and_groups_list = parameters[species_list_index].valueAsText
            #config_join_results = parameters[join_results_index]
            config_observation_types = parameters[observation_types_index].valueAsText
            config_collections = parameters[collections_storage_index].valueAsText
            
            
            def look_up_records(l_layer, l_config_species_and_groups_list, l_config_observation_types, l_config_collections):
                log.write("Looking Up Records", True)
                # preprocess inputs
                if l_config_species_and_groups_list and l_config_species_and_groups_list != '':
                    log.write("Parsing Species Requested", True)
                    species_list = funcs.text_to_species_list(l_config_species_and_groups_list)  # parse out the species codes
                else:
                    species_list = None
                zones = script_tool_funcs.zones_feature_to_array(l_layer)  # get the selected HUCs
            
                if l_config_observation_types and l_config_observation_types != '':
                    log.write("Parsing Observation Types", True)
                    observation_types = script_tool_funcs.obs_type_selection_box_to_list(l_config_observation_types)
                else:
                    observation_types = None
            
                if l_config_collections and l_config_collections != '':
                    log.write("Parsing Collections", True)
                    collections = script_tool_funcs.split_collection_names(l_config_collections)
                else:
                    collections = None
            
                # get results
                log.write("Obtaining Records", True)
                records = api.get_observation_records_for_hucs(zones, species_list, observation_types, collections)
                log.write("Writing Table", True)
                l_table = script_tool_funcs.write_table_from_observation_records(records, return_gdb_table=True)
            
                return l_table
            
            #if script_tool_funcs.is_in_arcgis():  # sort of like if __name__ == "__main__" for ArcGIS tools
            
            try:
                table = look_up_records(layer, config_species_and_groups_list, config_observation_types, config_collections)
            
                # add them to ArcMap
                log.write("Loading Table Into ArcMap", True)
                arcpy.SetParameter(output_table_index, table)
            except:
                log.error(traceback.format_exc())
            
            #orm_models.disconnect_engine_and_session()
            

class Tool78282bf0(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Output\execute-query"""
    import arcpy
    class ToolValidator(object):
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Generate Layer from Query'
        self.description = u'Generates a map layer from a text query using the PISCES API.'
        self.canRunInBackground = False
        self.category = "Output"
		
    def getParameterInfo(self):
        # Query
        param_1 = arcpy.Parameter()
        param_1.name = u'Query'
        param_1.displayName = u'Query'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'

        # Callback_Function_Name
        param_2 = arcpy.Parameter()
        param_2.name = u'Callback_Function_Name'
        param_2.displayName = u'Callback Function Name'
        param_2.parameterType = 'Optional'
        param_2.direction = 'Input'
        param_2.datatype = u'String'

        # Callback_Arguments
        param_3 = arcpy.Parameter()
        param_3.name = u'Callback_Arguments'
        param_3.displayName = u'Callback Arguments'
        param_3.parameterType = 'Optional'
        param_3.direction = 'Input'
        param_3.datatype = u'String'

        # Generated_Layer
        param_4 = arcpy.Parameter()
        param_4.name = u'Generated_Layer'
        param_4.displayName = u'Generated Layer'
        param_4.parameterType = 'Derived'
        param_4.direction = 'Output'
        param_4.datatype = u'Feature Class'

        return [param_1, param_2, param_3, param_4]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_execute_query.py'):
            __author__ = 'nrsantos'
            
            import arcpy
            from PISCES import api
            from PISCES import log
            from PISCES import local_vars
            
            local_vars.start(arc_script=True)
            
            query = parameters[0].valueAsText
            callback = parameters[1].valueAsText
            callback_args = parameters[2].valueAsText
            
            layer = api.get_query_as_layer(query, callback=callback, callback_args=callback_args)
            
            arcpy.SetParameter(3, layer)
            
            

class SummaryStats(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Output\SummaryStats"""
    def __init__(self):
        self.label = u'Summary Stats'
        self.description = u'Returns a table with PISCES summary statistics to the table of contents'
        self.canRunInBackground = False
        self.category = "Output"
		
    def getParameterInfo(self):
        # Output_Geodatabase
        param_1 = arcpy.Parameter()
        param_1.name = u'Output_Geodatabase'
        param_1.displayName = u'Output Geodatabase'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'Workspace'

        # Returned_Table
        param_2 = arcpy.Parameter()
        param_2.name = u'Returned_Table'
        param_2.displayName = u'Returned Table'
        param_2.parameterType = 'Derived'
        param_2.direction = 'Output'
        param_2.datatype = u'Table'

        return [param_1, param_2]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_summary_stats.py'):
            """
                A simple utility that runs the PISCES statistics functions and returns the results as a table into ArcMap
            """
            
            __author__ = 'dsx'
            
            import os
            from datetime import datetime
            import csv
            
            import arcpy
            
            from PISCES import local_vars
            from PISCES import script_tool_funcs
            from PISCES import funcs
            from PISCES import log
            
            
            def get_stats_table(output_gdb):
                """
                    Runs funcs.data_stats and output a table into the geodatabase provided as a parameter
                :param output_gdb: The geodatabase to put the stats table into
                :return:
                """
                db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
            
                name_col = "Parameter"
                value_col = "Value"
                values = funcs.data_stats(db_cursor, print_to_screen=True, name_col=name_col, value_col=value_col)
            
                csv_name = os.path.join(local_vars.temp, "pisces_stats_%s.csv" % datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))
            
                with open(csv_name, 'wb') as csv_file:
                    writer = csv.DictWriter(csv_file, [name_col, value_col])
                    writer.writeheader()
                    writer.writerows(values)
            
                gdb_name = os.path.split(os.path.splitext(csv_name)[0])[1]
                arcpy.TableToTable_conversion(csv_name, output_gdb, gdb_name)
                full_dataset = os.path.join(output_gdb, gdb_name)
            
                funcs.db_close(db_cursor, db_conn)
            
                return full_dataset
            
            if script_tool_funcs.is_in_arcgis():
            
                local_vars.start(arc_script=1)
            
                output_gdb = parameters[0].valueAsText
                try:
                    output_table = get_stats_table(output_gdb=output_gdb)
                    arcpy.SetParameter(1, output_table)
                except:
                    log.error("Can't send output table to table of contents. Are you running this in ArcMap? If not, your results are above.")

class UndoTransaction(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Modification\UndoTransaction"""
    import arcpy
    
    from PISCES import local_vars
    from PISCES import script_tool_funcs
    
    class ToolValidator(object):
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
        self.blank = ""
        self.transactions_field = 0
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        script_tool_funcs.get_transactions_picker(self, self.transactions_field)
    
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Undo Transaction (Undo Deletion)'
        self.description = u'Undoes a transaction where records were deleted, restoring the original records, along with metadata'
        self.canRunInBackground = False
        self.category = "Modification"
    def getParameterInfo(self):
        # Transaction
        param_1 = arcpy.Parameter()
        param_1.name = u'Transaction'
        param_1.displayName = u'Transaction'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'
        param_1.filter.list = [u'2032 - (no message logged for transaction)', u'2030 - Remove Temp Species', u'2029 - (no message logged for transaction)', u'2028 - (no message logged for transaction)']

        return [param_1]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_undo_transaction.py'):
            """
                A PISCES ArcGIS Toolbox tool to restore records deleted as part of a transaction.
            """
            __author__ = 'dsx'
            
            import arcpy
            
            from PISCES import local_vars
            from PISCES import log
            from PISCES import script_tool_funcs
            from PISCES import funcs
            from PISCES import orm_models
            
            
            transaction_to_reverse = parameters[0].valueAsText
            
            
            def undo_transaction(transaction_id_string):
                """
                    Given a transaction ID string (as comes from script_tool_funcs.get_transactions_picker), reverses the transaction. If you already have the transaction ID alone, use script_tool_funcs.reverse_transaction and provide the ID and a db_cursor
                :param transaction_id_string:
                :return:
                """
                transaction_id = script_tool_funcs.parse_transactions_picker(transaction_id_string)[0]
            
                session = orm_models.new_session()
                try:
                    if len(session.query(orm_models.Transaction).get(transaction_id).invalid_observations) == 0:  # session.query(orm_models.Invalid_Observation).filter_by(transaction_id != "").count() == 0:
                        log.error("No records for this transaction. It may be a transaction that's older than this tool can accommodate. Transactions made before February 2015 cannot be reversed using this method.")
                        return
                finally:
                    session.close()
            
                log.write("Reversing Transaction", True)
                db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
                script_tool_funcs.reverse_transaction(transaction_id, db_cursor)
                db_conn.commit()
                funcs.db_close(db_cursor, db_conn)
            
                log.write("Transaction Reversed - it will still show in the transactions list to be selected again, but your records have been restored", True)
            
            
            if script_tool_funcs.is_in_arcgis():
                local_vars.start(arc_script=1)
                undo_transaction(transaction_id_string=transaction_to_reverse)

class ChangeConfig(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\ChangeConfig"""
    
    import arcpy
    
    from PISCES import local_vars
    from PISCES import script_tool_funcs
    from PISCES import config_class
    
    reload(config_class.config)
    
    class ToolValidator(object):
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
    
        self.username = 0
        self.export_mxd = 1
        self.export_png = 2
        self.export_pdf = 3
        self.export_shp = 4
        self.export_kml = 5
        self.export_ddp = 6
        self.output_common_name = 7
        self.export_metadata = 8
        self.debug = 9
        self.database_location = 10
        self.map_output_folder = 11
        self.mxd_output_folder = 12
        self.web_layer_output_folder = 13
        self.export_lyr = 14
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        try:
            config = config_class.PISCES_Config()
            self.params[self.username].value = config.username
            self.params[self.export_mxd].value = config.export_mxd
            self.params[self.export_png].value = config.export_png
            self.params[self.export_pdf].value = config.export_pdf
            self.params[self.export_shp].value = config.export_shp
            self.params[self.export_kml].value = config.export_kml
            self.params[self.export_ddp].value = config.export_ddp
            self.params[self.output_common_name].value = config.output_common_name
            self.params[self.export_metadata].value = config.export_metadata
            self.params[self.debug].value = config.debug
            self.params[self.database_location].value = config.maindb
            self.params[self.map_output_folder].value = config.map_output_folder
            self.params[self.mxd_output_folder].value = config.mxd_output_folder
            self.params[self.web_layer_output_folder].value = config.web_layer_output_folder
            self.params[self.export_lyr].value = config.export_lyr
			
            script_tool_funcs.make_config_backup()  # if we got to here, then config loaded correctly, we can safely back it up
        except:
            self.params[self.username].value = "Could not load your PISCES configuration file. This tool is still in partial testing. Please consult the documentation on restoring your configuration from the backup file. Error reported was {0:s}".format(traceback.format_exc())
    
        self.params[self.debug].category = "General Options"
        self.params[self.database_location].category = "General Options"
        self.params[self.export_mxd].category = "Export Formats"
        self.params[self.export_png].category = "Export Formats"
        self.params[self.export_pdf].category = "Export Formats"
        self.params[self.export_shp].category = "Export Formats"
        self.params[self.export_kml].category = "Export Formats"
        self.params[self.export_lyr].category = "Export Formats"
        self.params[self.export_ddp].category = "Export Formats"
        self.params[self.output_common_name].category = "Export Options"
        self.params[self.export_metadata].category = "Export Options"
        self.params[self.map_output_folder].category = "Export Options"
        self.params[self.mxd_output_folder].category = "Export Options"
        self.params[self.web_layer_output_folder].category = "Export Options"
    
    
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Change Configuration Options'
        self.canRunInBackground = False
    def getParameterInfo(self):
        # Username
        param_1 = arcpy.Parameter()
        param_1.name = u'Username'
        param_1.displayName = u'Username'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'
        param_1.value = u'CWS'

        # Export_MXD
        param_2 = arcpy.Parameter()
        param_2.name = u'Export_MXD'
        param_2.displayName = u'Export MXD'
        param_2.parameterType = 'Optional'
        param_2.direction = 'Input'
        param_2.datatype = u'Boolean'
        param_2.value = u'true'

        # Export_PNG
        param_3 = arcpy.Parameter()
        param_3.name = u'Export_PNG'
        param_3.displayName = u'Export PNG'
        param_3.parameterType = 'Optional'
        param_3.direction = 'Input'
        param_3.datatype = u'Boolean'
        param_3.value = u'true'

        # Export_PDF
        param_4 = arcpy.Parameter()
        param_4.name = u'Export_PDF'
        param_4.displayName = u'Export PDF'
        param_4.parameterType = 'Optional'
        param_4.direction = 'Input'
        param_4.datatype = u'Boolean'
        param_4.value = u'false'

        # Export_Shapefile
        param_5 = arcpy.Parameter()
        param_5.name = u'Export_Shapefile'
        param_5.displayName = u'Export Shapefile'
        param_5.parameterType = 'Optional'
        param_5.direction = 'Input'
        param_5.datatype = u'Boolean'
        param_5.value = u'false'

        # Export_KML
        param_6 = arcpy.Parameter()
        param_6.name = u'Export_KML'
        param_6.displayName = u'Export KML'
        param_6.parameterType = 'Optional'
        param_6.direction = 'Input'
        param_6.datatype = u'Boolean'
        param_6.value = u'false'

        # Export_Data_Driven_Pages
        param_7 = arcpy.Parameter()
        param_7.name = u'Export_Data_Driven_Pages'
        param_7.displayName = u'Export Data Driven Pages'
        param_7.parameterType = 'Optional'
        param_7.direction = 'Input'
        param_7.datatype = u'Boolean'
        param_7.value = u'false'

        # Output_Common_Name
        param_8 = arcpy.Parameter()
        param_8.name = u'Output_Common_Name'
        param_8.displayName = u'Output Common Name'
        param_8.parameterType = 'Optional'
        param_8.direction = 'Input'
        param_8.datatype = u'Boolean'
        param_8.value = u'true'

        # Export_Metadata
        param_9 = arcpy.Parameter()
        param_9.name = u'Export_Metadata'
        param_9.displayName = u'Export Metadata'
        param_9.parameterType = 'Optional'
        param_9.direction = 'Input'
        param_9.datatype = u'Boolean'
        param_9.value = u'false'

        # Debug_Mode
        param_10 = arcpy.Parameter()
        param_10.name = u'Debug_Mode'
        param_10.displayName = u'Debug Mode'
        param_10.parameterType = 'Optional'
        param_10.direction = 'Input'
        param_10.datatype = u'Boolean'
        param_10.value = u'true'

        # Database_Location
        param_11 = arcpy.Parameter()
        param_11.name = u'Database_Location'
        param_11.displayName = u'Database Location'
        param_11.parameterType = 'Required'
        param_11.direction = 'Input'
        param_11.datatype = u'File'
        param_11.value = u'C:\\Users\\dsx\\Code\\pisces\\data\\pisces.sqlite'

        # Static_Map__PDF__PNG__Output_Folder
        param_12 = arcpy.Parameter()
        param_12.name = u'Static_Map__PDF__PNG__Output_Folder'
        param_12.displayName = u'Static Map (PDF, PNG) Output Folder'
        param_12.parameterType = 'Required'
        param_12.direction = 'Input'
        param_12.datatype = u'Folder'
        param_12.value = u'C:\\Users\\dsx\\Code\\PISCES\\maps\\output'

        # Map_Document__MXD__Output_Folder
        param_13 = arcpy.Parameter()
        param_13.name = u'Map_Document__MXD__Output_Folder'
        param_13.displayName = u'Map Document (MXD) Output Folder'
        param_13.parameterType = 'Required'
        param_13.direction = 'Input'
        param_13.datatype = u'Folder'
        param_13.value = u'C:\\Users\\dsx\\Code\\PISCES\\mxds\\output'

        # Web_Layers__Shapefile__KML__Output_Folder
        param_14 = arcpy.Parameter()
        param_14.name = u'Web_Layers__Shapefile__KML__Output_Folder'
        param_14.displayName = u'Web Layers (Shapefile, KML) Output Folder'
        param_14.parameterType = 'Required'
        param_14.direction = 'Input'
        param_14.datatype = u'Folder'
        param_14.value = u'C:\\Users\\dsx\\Code\\PISCES\\maps\\web_output\\layers'

        # Export_Layer_Package
        param_15 = arcpy.Parameter()
        param_15.name = u'Export_Layer_Package'
        param_15.displayName = u'Export Layer Package'
        param_15.parameterType = 'Optional'
        param_15.direction = 'Input'
        param_15.datatype = u'Boolean'
        param_15.value = u'false'

        return [param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9, param_10, param_11, param_12, param_13, param_14, param_15]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_change_config.py'):
            __author__ = 'dsx'
            
            import arcpy
            
            from PISCES import config_class  # keep this syntax because it's what's used in the tool validators, so this will let us update it
            from PISCES import local_vars
            from PISCES import log
            
            local_vars.start(arc_script=True)
            
            config_username = parameters[0].valueAsText
            config_export_mxd = parameters[1]
            config_export_png = parameters[2]
            config_export_pdf = parameters[3]
            config_export_shp = parameters[4]
            config_export_kml = parameters[5]
            config_export_ddp = parameters[6]
            config_output_common_name = parameters[7]
            config_export_metadata = parameters[8]
            config_debug = parameters[9]
            config_maindb = parameters[10].valueAsText
            config_map_output_folder = parameters[11].valueAsText
            config_mxd_output_folder = parameters[12].valueAsText
            config_web_layer_output_folder = parameters[13].valueAsText
            config_export_lyr = parameters[14]
            
            # get the config
            config = config_class.PISCES_Config()
            
            config.username = config_username
            config.export_mxd = config_export_mxd
            config.export_png = config_export_png
            config.export_pdf = config_export_pdf
            config.export_shp = config_export_shp
            config.export_kml = config_export_kml
            config.export_lyr = config_export_lyr
            config.export_ddp = config_export_ddp
            config.output_common_name = config_output_common_name
            config.export_metadata = config_export_metadata
            config.debug = config_debug
            config.maindb = config_maindb
            config.map_output_folder = config_map_output_folder
            config.mxd_output_folder = config_mxd_output_folder
            config.web_layer_output_folder = config_web_layer_output_folder
            config.save()
            
            reload(config_class.config)  # make sure it refreshes if it's being run in ArcMap
            
            del config

class ImportDataset(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Input\ImportDataset"""
    import arcpy
    import os
    import sys
    
    from PISCES import local_vars
    from PISCES import script_tool_funcs
    
    class ToolValidator(object):
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
        self.blank = ""
        self.previous_dataset = None
        self.dataset_index = 0
        self.input_filter_index = 1
        self.species_index = 2
        self.field_map_index = 3
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        script_tool_funcs.get_input_filter_picker(self, self.input_filter_index)
        self.params[self.species_index].filter.list = script_tool_funcs.get_fish_filter(prepend=["Determined per-record by software", ])
        self.params[self.species_index].value = self.blank
        self.params[self.input_filter_index].value = self.blank
    
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
    
        #if self.params[self.dataset_index].value != self.previous_dataset:  # effectively "on change"
        #    self.params[self.field_map_index].value.removeAll()
    
        #    self.params[self.field_map_index].value.addTable(self.params[self.dataset_index].value)
        #    self.previous_dataset = self.params[self.dataset_index].value
        
    
        script_tool_funcs.autocomplete_full_field(self, self.species_index)
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Import Dataset'
        self.description = u'Import a dataset where the input filter and species code mappings already exist'
        self.canRunInBackground = False
        self.category = "Input"
		
    def getParameterInfo(self):
        # Dataset
        param_1 = arcpy.Parameter()
        param_1.name = u'Dataset'
        param_1.displayName = u'Dataset'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'Table View'

        # Input_Filter
        param_2 = arcpy.Parameter()
        param_2.name = u'Input_Filter'
        param_2.displayName = u'Input Filter'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'
        param_2.filter.list = [u'1 - MOY - Moyle Distribution Maps', u'3 - USFS_Tahoe - Tahoe National Forest Data', u'5 - USFS_AREMP - Klamath National Forest Data', u'6 - USFS_LTBMU - Lake Tahoe Basin Management Unit Data', u'7 - USFS_Sierra - Sierra National Forest Data', u'8 - USFS_R5 - Region 5 Database Importer', u'9 - USFS_Stan - Stanislaus National Forest Data', u'10 - MKS - Moyle and Katz', u'11 - MKS_Low - Moyle and Katz - Low Probability', u'12 - FERC_Data - FERC survey data', u'13 - Lindley_NOAA - Historical Salmonid Distributions', u'14 - CNDDB - California Natural Diversity Database', u'15 - EMAP - California EMAP Data', u'16 - CNDDB_Amph - California Natural Diversity Database Amphibians', u'17 - Gen_Poly - General Polygon Import', u'18 - MQB - Moyle and Quinones', u'19 - TNC_Herps - The Nature Conservancy Database', u'21 - AW_herps - Herps HUC12 Ranges from Amber Wright', u'22 - TU_inverts - Inverts for freshwater conservation from TU', u'23 - CWS - Default CWS "Add or Modify Data" Input Filter', u'24 - CDFW - Default CDFW "Add or Modify Data" Input Filter', u'25 - CDFW_Heritage_Trout - CDFW Heritage Trout Dataset']

        # Species
        param_3 = arcpy.Parameter()
        param_3.name = u'Species'
        param_3.displayName = u'Species'
        param_3.parameterType = 'Required'
        param_3.direction = 'Input'
        param_3.datatype = u'String'
        param_3.filter.list = [u'Determined per-record by software', u'PXL01 - African Clawed Frog', u'CRO06 - Amargosa Canyon speckled dace', u'CCN02 - Amargosa River pupfish', u'AME01 - Ameletidae family', u'RLC01 - American Bullfrog', u'CAS01 - American Shad', u'AMP01 - Amphizoidae family', u'ANI01 - Anisogammaridae family', u'APA01 - Apataniidae family', u'CTA01 - Aquatic gartersnake', u'STA01 - Arctic grayling', u'RCB01 - Argentine pearlfish', u'GCI01 - Arrow goby', u'BAC02 - Arroyo Toad', u'CGO01 - Arroyo chub', u'ASE01 - Asellidae family', u'AST01 - Astacidae family', u'ATH01 - Athericidae family', u'ATY01 - Atyidae family', u'HPH01 - Baja California Treefrog', u'SSA01 - Barred Pipefish', u'CCK01 - Bigeye marbled sculpin', u'CIC01 - Bigmouth buffalo', u'PPM01 - Bigscale logperch', u'IAM01 - Black bullhead', u'CPN01 - Black crappie', u'BAE01 - Black toad', u'COM02 - Blackfish (bin)', u'BLE01 - Blephariceridae family', u'IIF01 - Blue catfish', u'CGC01 - Blue chub', u'FLG01 - Bluefin killifish', u'CLM02 - Bluegill', u'CGE01 - Bonytail', u'BRA01 - Brachycentridae family', u'SSF01 - Brook Trout', u'GCI02 - Brook stickleback', u'SST01 - Brown Trout', u'IAN02 - Brown bullhead', u'SSC01 - Bull trout', u'CAL01 - Calamoceratidae family', u'SOT04 - California Coast fall Chinook salmon', u'BAB02 - California Toad', u'DDE01 - California giant salamander', u'SOM14 - California golden trout', u'PPC01 - California halibut', u'CFP01 - California killifish', u'STT01 - California newt', u'RRD01 - California red-legged frog', u'CLS01 - California roach', u'AAC01 - California tiger salamander', u'COM03 - California tilapia (hybrid)', u'HPC01 - California tree frog', u'CAP01 - Capniidae family', u'RRC01 - Cascades frog', u'SOM05 - Central California coast winter steelhead', u'SOK01 - Central Coast coho salmon', u'SOT08 - Central Valley fall Chinook salmon', u'SOT07 - Central Valley late fall Chinook salmon', u'SOT06 - Central Valley spring Chinook salmon', u'SOM06 - Central Valley steelhead', u'SOT05 - Central Valley winter Chinook salmon', u'GTT01 - Chameleon goby', u'IIP01 - Channel catfish', u'CTM01 - Checkered gartersnake', u'SOT09 - Chinook Salmon (bin)', u'CHI01 - Chirocephalidae family', u'CHL01 - Chloroperlidae family', u'SOK03 - Chum salmon', u'CLE02 - Clear Lake hitch', u'CCA03 - Clear Lake prickly sculpin', u'CLS04 - Clear Lake roach', u'CPC01 - Clear Lake splittail', u'EHT03 - Clear Lake tule perch', u'SOC01 - Coastal cutthroat trout', u'SSC02 - Coastal dolly varden', u'DDT01 - Coastal giant salamander', u'SOM09 - Coastal rainbow trout', u'AAT02 - Coastal tailed frog', u'GGA01 - Coastal threespine stickleback', u'CCA04 - Coastrange sculpin', u'SOK04 - Coho (bin)', u'SOC05 - Colorado River cutthroat trout', u'CPL01 - Colorado pikeminnow', u'CLG03 - Common Kingsnake', u'CCC01 - Common carp', u'CTS01 - Common gartersnake', u'COR01 - Cordulegastridae family', u'COR02 - Corduliidae family', u'COR03 - Corydalidae family', u'CCS04 - Cottonball Marsh pupfish', u"SSC04 - Couch's spadefoot toad", u'CST03 - Cow Head tui chub', u'CRA01 - Crangonyctidae family', u'SOC04 - Cutthroat trout (bin)', u'PPE01 - Del Norte Salamander', u'OHP01 - Delta smelt', u'CCM02 - Desert pupfish', u'DEU01 - Deuterophlebiidae family', u'PPG01 - Diamond turbot', u'DIX01 - Dixidae family', u'SSC03 - Dolly varden', u"PPD01 - Dunn's salamander", u'SOM12 - Eagle Lake rainbow trout', u'CSB05 - Eagle Lake tui chub', u'ELM01 - Elmidae family', u'CHS01 - Empty data bin - California roach', u'EPH01 - Ephemerellidae family', u'OTP01 - Eulachon', u'EUL01 - Eulichadidae family', u'CPP01 - Fathead minnow', u'CCL02 - Flannelmouth sucker', u'IPO01 - Flathead Catfish', u'RRB01 - Foothill yellow-legged frog', u'CTG01 - Giant gartersnake', u'GLO01 - Glossosomatidae family', u'GOE01 - Goeridae family', u'CNC01 - Golden shiner', u'CCA05 - Goldfish', u'PET02 - Goose Lake lamprey', u'SOM11 - Goose Lake redband trout', u'CCO02 - Goose Lake sucker', u'CST01 - Goose Lake tui chub', u'CCI01 - Grass carp', u'SSI01 - Great Basin spadefoot', u'BAC03 - Great Plains toad', u'CLC01 - Green sunfish', u'PXH01 - Green swordtail', u'CLP01 - Gualala roach', u'PPR01 - Guppy', u'CMC01 - Hardhead', u'HEL01 - Helicopsychidae family', u'HEP01 - Heptageniidae family', u'CSB02 - High Rock Springs tui chub', u'CLE04 - Hitch (bin)', u'CCO04 - Humboldt sucker', u'HYD01 - Hydrobiidae family', u'MMB01 - Inland silverside', u'GGA02 - Inland threespine stickleback', u'PBC01 - Inyo Mountains salamander', u'ISO01 - Isonychiidae family', u'CLS09 - Kaweah roach', u'SOM13 - Kern River rainbow trout', u'PLH01 - Kern brook lamprey', u'SOM04 - Klamath Mountains Province summer steelhead', u'SOM03 - Klamath Mountains Province winter steelhead', u'PES01 - Klamath River lamprey', u'CCP04 - Klamath lake sculpin', u'CCS01 - Klamath largescale sucker', u'CCR01 - Klamath smallscale sucker', u'CRO03 - Klamath speckled dace', u'CSB01 - Klamath tui chub', u'SOC03 - Lahontan cutthroat trout', u'CSB03 - Lahontan lake tui chub', u'CCP01 - Lahontan mountain sucker', u'CRE01 - Lahontan redside', u'CRO02 - Lahontan speckled dace', u'CSB04 - Lahontan stream tui chub', u'SSN01 - Lake trout', u'CMS01 - Largemouth Bass', u'LEP01 - Lepidostomatidae family', u'LEU01 - Leuctridae family', u'LIM01 - Limnephilidae family', u'SOM15 - Little Kern golden trout', u'CRO05 - Long Valley speckled dace', u'AAM03 - Long-toed Salamander', u'OST01 - Longfin smelt', u'GGM01 - Longjaw mudsucker', u'GCS01 - Longtail goby', u'CCL01 - Lost River sucker', u'CCK02 - Lower Klamath marbled sculpin', u'LUT01 - Lutrochidae family', u'LYM01 - Lymnaeidae family', u'MAC01 - Macromiidae family', u'CCK04 - Marbled Sculpin (bin)', u'MAR01 - Margaritiferidae family', u'SOM10 - McCloud River redband trout', u'MMB02 - Mississippi silversides', u'CCM01 - Modoc sucker', u'CSM01 - Mojave tui chub', u'CLE03 - Monterey hitch', u'CCO03 - Monterey sucker', u'SPW01 - Mountain whitefish', u'CLS06 - Navarro roach', u'NEM01 - Nemouridae family', u'AEC01 - Northern Alligator Lizard', u'PEF01 - Northern California brook lamprey', u'SOM02 - Northern California coast summer steelhead', u'SOM01 - Northern California coast winter steelhead', u'CLS03 - Northern coastal roach', u'AAM01 - Northern green sturgeon', u'RRP01 - Northern leopard frog', u'RRA01 - Northern red-legged frog', u'CLS08 - Northern roach', u'CTO01 - Northwestern gartersnake', u'AAG01 - Northwestern salamander', u'ODO01 - Odontoceridae family', u'RRP02 - Oregon spotted frog', u'CCR02 - Owens pupfish', u'CRO04 - Owens speckled dace', u'CCF01 - Owens sucker', u'CSB06 - Owens tui chub', u'PLP01 - Pacific brook lamprey', u'HPR01 - Pacific chorus frog', u'CCH01 - Pacific herring', u'PET01 - Pacific lamprey', u'SOC02 - Paiute cutthroat trout', u'CCB02 - Paiute sculpin', u'PEL01 - Peltoperlidae family', u'PER01 - Perlidae family', u'PER02 - Perlodidae family', u'PET03 - Petaluridae family', u'PHI01 - Philopotamidae family', u'PHR01 - Phryganeidae family', u'SOG01 - Pink salmon', u'CST02 - Pit River tui chub', u'CCP02 - Pit sculpin', u'PLL01 - Pit-Klamath brook lamprey', u'PLE01 - Pleuroceridae family', u'PPG02 - Porthole livebearer', u'CCA02 - Prickly sculpin', u'PSY01 - Psychomyiidae family', u'PTE01 - Pteronarcyidae family', u'PTI01 - Ptilodactylidae family', u'CLG01 - Pumpkinseed', u'SOM17 - Rainbow Trout (Summer Steelhead)', u'SOM18 - Rainbow Trout (Winter Steelhead)', u'FLP01 - Rainwater killifish ', u'CXT01 - Razorback sucker', u'CLS02 - Red Hills roach', u'CCL03 - Red shiner', u'STR01 - Red-bellied newt', u'BAP01 - Red-spotted toad', u'SOM16 - Redband trout (bin)', u'CTZ01 - Redbelly tilapia', u'CLM03 - Redear sunfish', u'CMC02 - Redeye bass', u'CCP03 - Reticulate sculpin', u'RHY01 - Rhyacophilidae family', u'CCG01 - Riffle sculpin', u'PLA01 - River lamprey', u'CCA01 - Rough sculpin', u'STG01 - Rough-skinned newt', u'EHT02 - Russian River tule perch', u'COM01 - Sacramento blackfish', u'CLE01 - Sacramento hitch', u'CAI01 - Sacramento perch', u'CPG01 - Sacramento pikeminnow', u'CRO01 - Sacramento speckled dace', u'CPM01 - Sacramento splittail', u'CCO01 - Sacramento sucker', u'EHT01 - Sacramento tule perch', u'PPL01 - Sailfin molly', u'CCS03 - Salt Creek pupfish', u'CTS02 - San Francisco Gartersnake', u'CRO07 - Santa Ana speckled dace', u'CCS02 - Santa Ana sucker', u'PAN01 - Santa Cruz Black Salamander', u'AAM04 - Santa Cruz long-toed Salamander', u'CCN01 - Saratoga Springs pupfish', u'SCI01 - Scirtidae family', u'CCX01 - Sculpin spp (bin)', u'SER01 - Sericostomatidae family', u'CCA06 - Sharpnose sculpin', u'PAI01 - Shasta Black Salamander', u'GGA04 - Shay Creek stickleback', u'GTB01 - Shimofuri goby', u'ECA01 - Shiner perch', u'SCP01 - Shortfin corvina', u'PPM02 - Shortfin molly', u'CCB01 - Shortnose sucker', u'CCN04 - Shoshone pupfish', u'RRM01 - Sierra Madre yellow-legged frog', u'RRS01 - Sierra Nevada yellow-legged frog', u'CTC01 - Sierra gartersnake', u'STS01 - Sierra newt', u'HPS01 - Sierran Treefrog', u'PPS02 - Siskiyou Mountains Salamander', u'CCT02 - Slender sculpin', u'CMD01 - Smallmouth Bass', u'SON01 - Sockeye (Kokanee) Salmon', u'SOM07 - South Central California coast steelhead', u'CTS03 - South Coast Gartersnake', u'AEC02 - Southern Alligator Lizard', u'SOM08 - Southern California steelhead', u'SOK02 - Southern Oregon Northern California coast coho salmon', u'SOT03 - Southern Oregon Northern California coast fall Chinook salmon', u'CLS05 - Southern coastal roach', u'AAM02 - Southern green sturgeon', u'RRV01 - Southern torrent salamander', u'PAF01 - Speckled Black Salamander', u'CRO08 - Speckled Dace (bin)', u'SPH01 - Sphaeriidae family', u'CMP01 - Spotted bass', u'CLA01 - Staghorn sculpin', u'PPS01 - Starry flounder', u'SOM19 - Stocked Rainbow Trout (bin)', u'MMS01 - Striped bass', u'MMC02 - Striped mullet', u'OHP02 - Surf smelt', u'TAE01 - Taeniopterygidae family', u'CCT01 - Tahoe sucker', u'TAN01 - Tanyderidae family', u'CCN03 - Tecopa pupfish', u'CTT01 - Tench', u'CSC01 - Thicktail chub', u'CDP01 - Threadfin shad', u'GGA05 - Threespine stickleback (bin)', u'GEN01 - Tidewater goby', u'CLS07 - Tomales roach', u'AAA01 - Topsmelt', u'CSB07 - Tui chub bin', u'EHT04 - Tule perch (bin)', u'CTH01 - Twp-striped gartersnake', u'UEN01 - Uenoidae family', u'GGA03 - Unarmored threespine stickleback', u'UNI01 - Unionidae family', u'CCK03 - Upper Klamath marbled sculpin', u'SOT01 - Upper Klamath-Trinity fall Chinook salmon', u'SOT02 - Upper Klamath-Trinity spring Chinook salmon', u'OHN01 - Wakasagi', u'PAV01 - Wandering Salamander', u'CLG02 - Warmouth', u'EAM01 - Western Pond Turtle', u'PLR01 - Western brook lamprey', u'PGA01 - Western mosquitofish', u'EEM01 - Western pond turtle', u'SSH01 - Western spadefoot toad', u'CTE01 - Western terrestrial gartersnake', u'BAB01 - Western toad', u'MMC01 - White bass', u'IAC01 - White catfish', u'CPA01 - White crappie', u'AAT01 - White sturgeon', u"BAW01 - Woodhouse's toad", u'IAN01 - Yellow bullhead', u'PPF01 - Yellow perch', u'GAF01 - Yellowfin goby', u'BAC01 - Yosemite Toad', u'ZZZ01 - temp']

        # Field_Mapping
        param_4 = arcpy.Parameter()
        param_4.name = u'Field_Mapping'
        param_4.displayName = u'Field Mapping'
        param_4.parameterType = 'Required'
        param_4.direction = 'Input'
        param_4.datatype = u'Record Set'
        param_4.value = u'in_memory\\{536992BC-39F8-4C8B-B3D0-288B06C33DEE}'

        return [param_1, param_2, param_3, param_4]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_import_dataset.py'):
            """
                An ArcGIS Toolbox tool to import a dataset when the input filter is already set up.
            
                The methods in this tool may be a bit roundabout because they'll be attempting to use quite a bit of existing code that
                assumes explicit paths, etc. So records and data will need to be written to those locations in order to be used.
            """
            import funcs
            
            __author__ = 'dsx'
            
            import os
            import traceback
            
            import arcpy
            
            from PISCES import local_vars
            from PISCES import funcs
            from PISCES import script_tool_funcs
            from PISCES import log
            
            
            def set_up_import(dataset, input_filter, species, field_mapping_record_set):
                """
                    Given the necessary information, sets up the data for an import (but doesn't run the import - copies the dataset to newdata.mdb, adds the record, inserts the field map, etc. Meant to be run as an ArcGIS script tool
                :param dataset: an arcgis feature class or feature layer to attempt to import
                :param input_filter: The input filter to use to process this dataset, as constructed by script_tool_funcs.get_input_filter_picker()
                :param species: optional. If the dataset is a single species, this one is it. In the format of the ArcGIS tool pickers (species code - common name) so it can be parsed.
                :param field_mapping_record_set: An ArcGIS RecordSet object - can also be just a table with four fields (PISCES_Field (string), Input_Field (string), Handler_Function (string), Required (boolean)). Records indicate a field mapping from Input_Field->PISCES_Field
                :return:
                """
            
                # copy the feature class to the new data geodatabase
                log.write("Copying data to Database", True)
                full_path = funcs.copy_data(dataset, local_vars.newdb)
                fc_name = os.path.split(full_path)[1]
            
                try:
                    log.write("Validating inputs", True)
                    # parse the filter code
                    filter_parts = script_tool_funcs.parse_input_filter_picker(input_filter)
                    filter_code = filter_parts[1]
            
                    # determine the species
                    if species == "Determined per-record by software":
                        species_code = "filter"
                    else:
                        species_code = funcs.parse_input_species_from_list(species)
            
                    db_cursor, db_conn = funcs.db_connect(local_vars.newdb, "Connecting for tbx_import_dataset", access=True)
                    sql_statement = "insert into NewData (Feature_Class_Name, Input_Filter, Species_ID) values (?,?,?)"
                    db_cursor.execute(sql_statement, fc_name, filter_code, species_code)
                    # don't commit yet because if the insertion of the FieldMapping fails we don't want to keep this
            
                    new_data_id = funcs.get_last_insert_id(db_cursor, access=True)
            
                    log.write("Inserting Records", True)
                    allowed_fields = ("Species", "Zone_ID", "Observation Type", "Latitude", "Longitude", "Survey Method", "NotesItems", "Date", "Certainty", "Observer")
                    sql_statement = "insert into FieldMapping (NewData_ID, Field_Name, Input_Field, Handler_Function, Required) values (?,?,?,?,?)"
                    dataset_fields = arcpy.ListFields(dataset)
                    valid_input_fields = [record.name for record in dataset_fields]
            
                    record_cursor = arcpy.SearchCursor(field_mapping_record_set)
                    for record in record_cursor:
                        #if (record.Input_Field is None or record.Input_Field == "") and (record.PISCES_Field is None or record.PISCES_Field == ""):
                        #    continue  # if we don't have an input field or a pisces field, they probably weren't configuring anything. We got some errors for records that didn't exist
            
                        if record.Required not in (None, 0, 1):
                            raise ValueError("Values for \"Required\" must be either 0 (not required) or 1 (required). You provided '%s'" % record.Required)
            
                        if record.PISCES_Field not in allowed_fields:
                            raise ValueError("Options for PISCES_Field must be one of the following: %s. You provided '%s'" % (allowed_fields, record.PISCES_Field))
            
                        if record.Input_Field not in valid_input_fields:
                            raise ValueError("Field names in Input_Field must be fields that exist in the input dataset. You provided '%s'. Valid options are %s" % (record.Input_Field, valid_input_fields))
            
                        db_cursor.execute(sql_statement, new_data_id, record.PISCES_Field, record.Input_Field, record.Handler_Function, record.Required)
            
                    log.write("Finishing Up", True)
                    db_conn.commit()
                    funcs.db_close(db_cursor, db_conn)
            
                    return fc_name
            
                except:
                    # clean up on failure, then raise the exception up
                    log.error("Failure occurred, attempting to clean up - error: %s" % traceback.format_exc())
                    try:
                        dataset_path = os.path.join(local_vars.newdb, fc_name)
                        if arcpy.Exists(dataset_path):
                            arcpy.Delete_management(dataset_path)
                    except:
                        pass
                    raise
            
            
            def run_import(dataset_name):
            
                funcs.import_new_data(dataset_name)
            
            
            if script_tool_funcs.is_in_arcgis():  # allows us to unit test the code by making it not run unless we're in ArcGIS
            
                local_vars.start(arc_script=1)
            
                config_dataset = parameters[0].valueAsText
                config_input_filter = parameters[1].valueAsText
                config_species = parameters[2].valueAsText
                config_field_mapping_record_set = parameters[3].valueAsText
            
                log.write("BEGINNING SETUP PHASE", True)
                new_data_name = set_up_import(config_dataset, config_input_filter, config_species, config_field_mapping_record_set)
            
                log.write("BEGINNING IMPORT PHASE", True)
                run_import(new_data_name)

class RetryImport(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Input\RetryImport"""
    import arcpy
    
    from PISCES import local_vars
    from PISCES import funcs
    
    class ToolValidator(object):
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        self.params = parameters
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
    
        local_vars.start()
    
        db_cursor, db_conn = funcs.db_connect(local_vars.newdb, access=True)
        sql_statement = "select Feature_Class_Name from NewData where Imported=0 order by ID asc;"
        dataset_names = db_cursor.execute(sql_statement)
    
        filter_items = []
        for item in dataset_names:
            filter_items.append(item.Feature_Class_Name)
    
        self.params[0].filter.list = filter_items
    
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Retry Import'
        self.description = u'Retry a failed import. Imports occur in two stages - setting the metadata into the database to stage the import, then the actual import. If the metadata setup occurred successfully in the Import Dataset tool, but the overall import failed, you can select the dataset to try again with here.'
        self.canRunInBackground = False
        self.category = "Input"
		
    def getParameterInfo(self):
        # Dataset_Name
        param_1 = arcpy.Parameter()
        param_1.name = u'Dataset_Name'
        param_1.displayName = u'Dataset Name'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'

        return [param_1]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_retry_import.py'):
            __author__ = 'dsx'
            
            import arcpy
            
            from PISCES import local_vars
            from PISCES import funcs
            from PISCES import log
            from PISCES import script_tool_funcs
            
            
            if script_tool_funcs.is_in_arcgis():  # allows us to unit test the code by making it not run unless we're in ArcGIS
            
                local_vars.start(arc_script=1)
            
                config_dataset_name = parameters[0].valueAsText
            
                log.write("BEGINNING IMPORT PHASE", True)
                funcs.import_new_data(config_dataset_name)

class AddToCollection(object):
    """C:\Users\dsx\Code\PISCES\tbx\PISCES.tbx\Modification\AddToCollection"""
    from PISCES import local_vars
    from PISCES import funcs
    from PISCES import script_tool_funcs
    
    
    class ToolValidator:
      """Class for validating a tool's parameter values and controlling
      the behavior of the tool's dialog."""
    
      def __init__(self, parameters):
        """Setup arcpy and the list of tool parameters."""
        import arcpy
        self.params = parameters
    
      def initializeParameters(self):
        """Refine the properties of a tool's parameters.  This method is
        called when the tool is opened."""
        import os, sys
    
        local_vars.start()
    
        db_cursor,db_conn = funcs.db_connect(local_vars.maindb)
    
        l_fish = script_tool_funcs.get_fish_filter()
    
        get_cols = "select Collection_Name as rval from defs_Collections"
    
        l_cols = []
    
        collections = db_cursor.execute(get_cols)
        for t_col in collections:
          l_cols.append(t_col.rval)
    
        self.params[0].filter.list = l_fish
        self.params[0].value = ""
        self.params[1].filter.list = l_cols
        
        funcs.db_close(db_cursor,db_conn)
    
        
        return
    
      def updateParameters(self):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parmater
        has been changed."""
    
        import PISCES.script_tool_funcs as script_tool_funcs
    
        script_tool_funcs.autocomplete_full_field(self,0)
        script_tool_funcs.autocomplete_full_field(self,1)
    
    
      def updateMessages(self):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return
    
    def __init__(self):
        self.label = u'Add Species Data to Collection'
        self.canRunInBackground = False
        self.category = "Modification"
		
    def getParameterInfo(self):
        # Species
        param_1 = arcpy.Parameter()
        param_1.name = u'Species'
        param_1.displayName = u'Species'
        param_1.parameterType = 'Required'
        param_1.direction = 'Input'
        param_1.datatype = u'String'
        param_1.filter.list = [u'PXL01 - African Clawed Frog', u'CRO06 - Amargosa Canyon speckled dace', u'CCN02 - Amargosa River pupfish', u'AME01 - Ameletidae family', u'RLC01 - American Bullfrog', u'CAS01 - American Shad', u'AMP01 - Amphizoidae family', u'ANI01 - Anisogammaridae family', u'APA01 - Apataniidae family', u'CTA01 - Aquatic gartersnake', u'STA01 - Arctic grayling', u'RCB01 - Argentine pearlfish', u'GCI01 - Arrow goby', u'BAC02 - Arroyo Toad', u'CGO01 - Arroyo chub', u'ASE01 - Asellidae family', u'AST01 - Astacidae family', u'ATH01 - Athericidae family', u'ATY01 - Atyidae family', u'HPH01 - Baja California Treefrog', u'SSA01 - Barred Pipefish', u'CCK01 - Bigeye marbled sculpin', u'CIC01 - Bigmouth buffalo', u'PPM01 - Bigscale logperch', u'IAM01 - Black bullhead', u'CPN01 - Black crappie', u'BAE01 - Black toad', u'COM02 - Blackfish (bin)', u'BLE01 - Blephariceridae family', u'IIF01 - Blue catfish', u'CGC01 - Blue chub', u'FLG01 - Bluefin killifish', u'CLM02 - Bluegill', u'CGE01 - Bonytail', u'BRA01 - Brachycentridae family', u'SSF01 - Brook Trout', u'GCI02 - Brook stickleback', u'SST01 - Brown Trout', u'IAN02 - Brown bullhead', u'SSC01 - Bull trout', u'CAL01 - Calamoceratidae family', u'SOT04 - California Coast fall Chinook salmon', u'BAB02 - California Toad', u'DDE01 - California giant salamander', u'SOM14 - California golden trout', u'PPC01 - California halibut', u'CFP01 - California killifish', u'STT01 - California newt', u'RRD01 - California red-legged frog', u'CLS01 - California roach', u'AAC01 - California tiger salamander', u'COM03 - California tilapia (hybrid)', u'HPC01 - California tree frog', u'CAP01 - Capniidae family', u'RRC01 - Cascades frog', u'SOM05 - Central California coast winter steelhead', u'SOK01 - Central Coast coho salmon', u'SOT08 - Central Valley fall Chinook salmon', u'SOT07 - Central Valley late fall Chinook salmon', u'SOT06 - Central Valley spring Chinook salmon', u'SOM06 - Central Valley steelhead', u'SOT05 - Central Valley winter Chinook salmon', u'GTT01 - Chameleon goby', u'IIP01 - Channel catfish', u'CTM01 - Checkered gartersnake', u'SOT09 - Chinook Salmon (bin)', u'CHI01 - Chirocephalidae family', u'CHL01 - Chloroperlidae family', u'SOK03 - Chum salmon', u'CLE02 - Clear Lake hitch', u'CCA03 - Clear Lake prickly sculpin', u'CLS04 - Clear Lake roach', u'CPC01 - Clear Lake splittail', u'EHT03 - Clear Lake tule perch', u'SOC01 - Coastal cutthroat trout', u'SSC02 - Coastal dolly varden', u'DDT01 - Coastal giant salamander', u'SOM09 - Coastal rainbow trout', u'AAT02 - Coastal tailed frog', u'GGA01 - Coastal threespine stickleback', u'CCA04 - Coastrange sculpin', u'SOK04 - Coho (bin)', u'SOC05 - Colorado River cutthroat trout', u'CPL01 - Colorado pikeminnow', u'CLG03 - Common Kingsnake', u'CCC01 - Common carp', u'CTS01 - Common gartersnake', u'COR01 - Cordulegastridae family', u'COR02 - Corduliidae family', u'COR03 - Corydalidae family', u'CCS04 - Cottonball Marsh pupfish', u"SSC04 - Couch's spadefoot toad", u'CST03 - Cow Head tui chub', u'CRA01 - Crangonyctidae family', u'SOC04 - Cutthroat trout (bin)', u'PPE01 - Del Norte Salamander', u'OHP01 - Delta smelt', u'CCM02 - Desert pupfish', u'DEU01 - Deuterophlebiidae family', u'PPG01 - Diamond turbot', u'DIX01 - Dixidae family', u'SSC03 - Dolly varden', u"PPD01 - Dunn's salamander", u'SOM12 - Eagle Lake rainbow trout', u'CSB05 - Eagle Lake tui chub', u'ELM01 - Elmidae family', u'CHS01 - Empty data bin - California roach', u'EPH01 - Ephemerellidae family', u'OTP01 - Eulachon', u'EUL01 - Eulichadidae family', u'CPP01 - Fathead minnow', u'CCL02 - Flannelmouth sucker', u'IPO01 - Flathead Catfish', u'RRB01 - Foothill yellow-legged frog', u'CTG01 - Giant gartersnake', u'GLO01 - Glossosomatidae family', u'GOE01 - Goeridae family', u'CNC01 - Golden shiner', u'CCA05 - Goldfish', u'PET02 - Goose Lake lamprey', u'SOM11 - Goose Lake redband trout', u'CCO02 - Goose Lake sucker', u'CST01 - Goose Lake tui chub', u'CCI01 - Grass carp', u'SSI01 - Great Basin spadefoot', u'BAC03 - Great Plains toad', u'CLC01 - Green sunfish', u'PXH01 - Green swordtail', u'CLP01 - Gualala roach', u'PPR01 - Guppy', u'CMC01 - Hardhead', u'HEL01 - Helicopsychidae family', u'HEP01 - Heptageniidae family', u'CSB02 - High Rock Springs tui chub', u'CLE04 - Hitch (bin)', u'CCO04 - Humboldt sucker', u'HYD01 - Hydrobiidae family', u'MMB01 - Inland silverside', u'GGA02 - Inland threespine stickleback', u'PBC01 - Inyo Mountains salamander', u'ISO01 - Isonychiidae family', u'CLS09 - Kaweah roach', u'SOM13 - Kern River rainbow trout', u'PLH01 - Kern brook lamprey', u'SOM04 - Klamath Mountains Province summer steelhead', u'SOM03 - Klamath Mountains Province winter steelhead', u'PES01 - Klamath River lamprey', u'CCP04 - Klamath lake sculpin', u'CCS01 - Klamath largescale sucker', u'CCR01 - Klamath smallscale sucker', u'CRO03 - Klamath speckled dace', u'CSB01 - Klamath tui chub', u'SOC03 - Lahontan cutthroat trout', u'CSB03 - Lahontan lake tui chub', u'CCP01 - Lahontan mountain sucker', u'CRE01 - Lahontan redside', u'CRO02 - Lahontan speckled dace', u'CSB04 - Lahontan stream tui chub', u'SSN01 - Lake trout', u'CMS01 - Largemouth Bass', u'LEP01 - Lepidostomatidae family', u'LEU01 - Leuctridae family', u'LIM01 - Limnephilidae family', u'SOM15 - Little Kern golden trout', u'CRO05 - Long Valley speckled dace', u'AAM03 - Long-toed Salamander', u'OST01 - Longfin smelt', u'GGM01 - Longjaw mudsucker', u'GCS01 - Longtail goby', u'CCL01 - Lost River sucker', u'CCK02 - Lower Klamath marbled sculpin', u'LUT01 - Lutrochidae family', u'LYM01 - Lymnaeidae family', u'MAC01 - Macromiidae family', u'CCK04 - Marbled Sculpin (bin)', u'MAR01 - Margaritiferidae family', u'SOM10 - McCloud River redband trout', u'MMB02 - Mississippi silversides', u'CCM01 - Modoc sucker', u'CSM01 - Mojave tui chub', u'CLE03 - Monterey hitch', u'CCO03 - Monterey sucker', u'SPW01 - Mountain whitefish', u'CLS06 - Navarro roach', u'NEM01 - Nemouridae family', u'AEC01 - Northern Alligator Lizard', u'PEF01 - Northern California brook lamprey', u'SOM02 - Northern California coast summer steelhead', u'SOM01 - Northern California coast winter steelhead', u'CLS03 - Northern coastal roach', u'AAM01 - Northern green sturgeon', u'RRP01 - Northern leopard frog', u'RRA01 - Northern red-legged frog', u'CLS08 - Northern roach', u'CTO01 - Northwestern gartersnake', u'AAG01 - Northwestern salamander', u'ODO01 - Odontoceridae family', u'RRP02 - Oregon spotted frog', u'CCR02 - Owens pupfish', u'CRO04 - Owens speckled dace', u'CCF01 - Owens sucker', u'CSB06 - Owens tui chub', u'PLP01 - Pacific brook lamprey', u'HPR01 - Pacific chorus frog', u'CCH01 - Pacific herring', u'PET01 - Pacific lamprey', u'SOC02 - Paiute cutthroat trout', u'CCB02 - Paiute sculpin', u'PEL01 - Peltoperlidae family', u'PER01 - Perlidae family', u'PER02 - Perlodidae family', u'PET03 - Petaluridae family', u'PHI01 - Philopotamidae family', u'PHR01 - Phryganeidae family', u'SOG01 - Pink salmon', u'CST02 - Pit River tui chub', u'CCP02 - Pit sculpin', u'PLL01 - Pit-Klamath brook lamprey', u'PLE01 - Pleuroceridae family', u'PPG02 - Porthole livebearer', u'CCA02 - Prickly sculpin', u'PSY01 - Psychomyiidae family', u'PTE01 - Pteronarcyidae family', u'PTI01 - Ptilodactylidae family', u'CLG01 - Pumpkinseed', u'SOM17 - Rainbow Trout (Summer Steelhead)', u'SOM18 - Rainbow Trout (Winter Steelhead)', u'FLP01 - Rainwater killifish ', u'CXT01 - Razorback sucker', u'CLS02 - Red Hills roach', u'CCL03 - Red shiner', u'STR01 - Red-bellied newt', u'BAP01 - Red-spotted toad', u'SOM16 - Redband trout (bin)', u'CTZ01 - Redbelly tilapia', u'CLM03 - Redear sunfish', u'CMC02 - Redeye bass', u'CCP03 - Reticulate sculpin', u'RHY01 - Rhyacophilidae family', u'CCG01 - Riffle sculpin', u'PLA01 - River lamprey', u'CCA01 - Rough sculpin', u'STG01 - Rough-skinned newt', u'EHT02 - Russian River tule perch', u'COM01 - Sacramento blackfish', u'CLE01 - Sacramento hitch', u'CAI01 - Sacramento perch', u'CPG01 - Sacramento pikeminnow', u'CRO01 - Sacramento speckled dace', u'CPM01 - Sacramento splittail', u'CCO01 - Sacramento sucker', u'EHT01 - Sacramento tule perch', u'PPL01 - Sailfin molly', u'CCS03 - Salt Creek pupfish', u'CTS02 - San Francisco Gartersnake', u'CRO07 - Santa Ana speckled dace', u'CCS02 - Santa Ana sucker', u'PAN01 - Santa Cruz Black Salamander', u'AAM04 - Santa Cruz long-toed Salamander', u'CCN01 - Saratoga Springs pupfish', u'SCI01 - Scirtidae family', u'CCX01 - Sculpin spp (bin)', u'SER01 - Sericostomatidae family', u'CCA06 - Sharpnose sculpin', u'PAI01 - Shasta Black Salamander', u'GGA04 - Shay Creek stickleback', u'GTB01 - Shimofuri goby', u'ECA01 - Shiner perch', u'SCP01 - Shortfin corvina', u'PPM02 - Shortfin molly', u'CCB01 - Shortnose sucker', u'CCN04 - Shoshone pupfish', u'RRM01 - Sierra Madre yellow-legged frog', u'RRS01 - Sierra Nevada yellow-legged frog', u'CTC01 - Sierra gartersnake', u'STS01 - Sierra newt', u'HPS01 - Sierran Treefrog', u'PPS02 - Siskiyou Mountains Salamander', u'CCT02 - Slender sculpin', u'CMD01 - Smallmouth Bass', u'SON01 - Sockeye (Kokanee) Salmon', u'SOM07 - South Central California coast steelhead', u'CTS03 - South Coast Gartersnake', u'AEC02 - Southern Alligator Lizard', u'SOM08 - Southern California steelhead', u'SOK02 - Southern Oregon Northern California coast coho salmon', u'SOT03 - Southern Oregon Northern California coast fall Chinook salmon', u'CLS05 - Southern coastal roach', u'AAM02 - Southern green sturgeon', u'RRV01 - Southern torrent salamander', u'PAF01 - Speckled Black Salamander', u'CRO08 - Speckled Dace (bin)', u'SPH01 - Sphaeriidae family', u'CMP01 - Spotted bass', u'CLA01 - Staghorn sculpin', u'PPS01 - Starry flounder', u'SOM19 - Stocked Rainbow Trout (bin)', u'MMS01 - Striped bass', u'MMC02 - Striped mullet', u'OHP02 - Surf smelt', u'TAE01 - Taeniopterygidae family', u'CCT01 - Tahoe sucker', u'TAN01 - Tanyderidae family', u'CCN03 - Tecopa pupfish', u'CTT01 - Tench', u'CSC01 - Thicktail chub', u'CDP01 - Threadfin shad', u'GGA05 - Threespine stickleback (bin)', u'GEN01 - Tidewater goby', u'CLS07 - Tomales roach', u'AAA01 - Topsmelt', u'CSB07 - Tui chub bin', u'EHT04 - Tule perch (bin)', u'CTH01 - Twp-striped gartersnake', u'UEN01 - Uenoidae family', u'GGA03 - Unarmored threespine stickleback', u'UNI01 - Unionidae family', u'CCK03 - Upper Klamath marbled sculpin', u'SOT01 - Upper Klamath-Trinity fall Chinook salmon', u'SOT02 - Upper Klamath-Trinity spring Chinook salmon', u'OHN01 - Wakasagi', u'PAV01 - Wandering Salamander', u'CLG02 - Warmouth', u'EAM01 - Western Pond Turtle', u'PLR01 - Western brook lamprey', u'PGA01 - Western mosquitofish', u'EEM01 - Western pond turtle', u'SSH01 - Western spadefoot toad', u'CTE01 - Western terrestrial gartersnake', u'BAB01 - Western toad', u'MMC01 - White bass', u'IAC01 - White catfish', u'CPA01 - White crappie', u'AAT01 - White sturgeon', u"BAW01 - Woodhouse's toad", u'IAN01 - Yellow bullhead', u'PPF01 - Yellow perch', u'GAF01 - Yellowfin goby', u'BAC01 - Yosemite Toad', u'ZZZ01 - temp']

        # Collection
        param_2 = arcpy.Parameter()
        param_2.name = u'Collection'
        param_2.displayName = u'Collection'
        param_2.parameterType = 'Required'
        param_2.direction = 'Input'
        param_2.datatype = u'String'
        param_2.filter.list = [u'Fish Species of Special Concern - Final', u'Delivered USFS 12/15/2011', u'Pre QC', u'QC 2013', u'Best available knowledge 8/2013', u'HUC 12 Update - Oct 2013', u'HUC 12 Update - Oct 2013', u'Non native QC 12/12/13', u'QC Update 2017']

        return [param_1, param_2]
    def isLicensed(self):
        return True
    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()
    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()
    def execute(self, parameters, messages):
        with script_run_as(u'C:\\Users\\dsx\\Code\\PISCES\\scripts\\PISCES\\tbx_add_to_collection.py'):
            '''a quick and dirty way to add all observations to a collection. We should do this a better way, but we don't currently have the time.'''
            
            import sys, os
            import arcpy
            
            import funcs
            import local_vars
            import log
            import script_tool_funcs
            
            local_vars.start(arc_script=1)
            
            log.initialize("Adding records to collection", arc_script=1)
                      
            filter_species_full = parameters[0].valueAsText
            collection = parameters[1].valueAsText
            
            filter_species = funcs.parse_input_species_from_list(filter_species_full)
            
            db_cursor, db_conn = funcs.db_connect(local_vars.maindb)
            db_insert = db_conn.cursor()
            
            get_collection_id = "select id from defs_collections where collection_name = ?"
            c_rows = db_cursor.execute(get_collection_id, collection)
            collection_id = c_rows.fetchone().id
            
            log.write("Pulling records", 1)
            select_sql = "select objectid, species_id from observations where species_id = ?"
            db_cursor.execute(select_sql, filter_species)
            
            insert_sql = "insert into observation_collections (observation_id,collection_id) values (?,?)"
            
            log.write("Filtering and inserting collections", 1)
            
            for row in db_cursor:
                try:
                    db_insert.execute(insert_sql, row.objectid, collection_id)
                except:
                    #TODO: make this check the actual exception to see if that's what occurred, and note if it isn't
                    log.write("A record was not inserted - probably already exists")
                    
            db_cursor.close()
            db_insert.close()
            db_conn.commit()
            