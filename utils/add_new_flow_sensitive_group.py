import csv

from PISCES import orm_models as orm
from PISCES import api

session = api.support.connect_orm(hotload=True)

new_flow_sensitive_group = session.query(orm.SpeciesGroup).filter(orm.SpeciesGroup.name=="Flow_Sensitive_V2").first()

with open(r"C:\Users\dsx\Downloads\flow_sensitive_species_notes_Peter.csv") as data:
	records = csv.DictReader(data)

	for record in records:
		species = session.query(orm.Species).filter(orm.Species.fid==record["fid"]).first()
		if species:
			if record["flow_sensitive"] == "x":
				print("{} - {}".format(record["fid"], record["common_name"]))
				species.groups.append(new_flow_sensitive_group)
		else:
			print("############# {} - {} SPECIES MISSING!!! ###############".format(record["fid"], record["common_name"]))

session.commit()
session.close()
