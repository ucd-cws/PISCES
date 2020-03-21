import os

import arcpy
from sqlalchemy.exc import IntegrityError

from PISCES import script_tool_funcs
from PISCES import local_vars
from PISCES import log
from PISCES import orm_models

local_vars.start(arc_script=1)

arcpy.env.overwriteOutput = True  # we want to overwrite outputs because we'll be writing to temp.mdb

feature_layer = arcpy.GetParameterAsText(0)
column = arcpy.GetParameterAsText(1)
input_filter = arcpy.GetParameterAsText(2)
fid_column = arcpy.GetParameterAsText(3)
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

arcpy.AddWarning("Alt_Codes added for input filter %s - be sure to go check and add any necessary and missing FIDs for the codes" % input_filter)
