from __future__ import absolute_import, division, print_function

__author__ = 'dsx'

import pkg_resources
pkg_resources.require("sqlalchemy>=0.9.4")

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import orm, Column, Integer, String, Boolean, Float, ForeignKey, Table, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, backref, scoped_session

from . import local_vars

engine = None
Session = None
Base = declarative_base()


def connect(db=local_vars.ormdb):
	"""
		Don't use me directly! Use api.connect_orm instead - it'll better handle some of the startup.
	:param db:
	:return:
	"""
	global engine, Session

	engine = sqlalchemy.create_engine("sqlite+pysqlite:///%s" % db)
	Session = orm.sessionmaker(bind=engine)


def disconnect_engine_and_session():
	global engine, Session

	Session.close()


def new_session(db=local_vars.ormdb, autocommit=True):
	global Session

	if not Session:  # if we're not yet connected
		connect(db)

	return Session(autocommit=autocommit)  # TODO: In the long run, this shouldn't be on autocommit, but until we can switch everything out from PyODBC, it'll need to be
			# scoped_session gives us some thread safety


species_groups = Table(local_vars.species_group_members_table, Base.metadata,
    Column('fid', Integer, ForeignKey('{0:s}.fid'.format(local_vars.species_table))),
    Column('group_id', Integer, ForeignKey('{0:s}.id'.format(local_vars.species_groups_table)))
)


class Species(Base):
	__tablename__ = local_vars.species_table

	pkey = Column("objectid", Integer, primary_key=True)
	fid = Column("fid", String)
	family = Column("family", String)
	genus = Column("genus", String)
	species = Column("species", String)
	subspecies = Column("subspecies", String)
	scientific_name = Column("scientific_name", String)
	taxonomic_unit = Column("taxonomic_unit", String)
	common_name = Column("common_name", String)
	notes = Column("notes", String)
	native = Column("native", Boolean)  # TODO: This should be fully deprecated soon in order to rely only on groups
	image_location = Column("image_location", String)
	temporary = Column("temporary", Boolean)  # Flags records that are only for catching data that needs taxa to be determined.
	# non_native = Column("non_native", Boolean)  # Fully deprecated and rely on groups instead
	# qc = Column("qc", Boolean)  # Fully deprecated and rely on collections instead

	#groups = relationship to SpeciesGroup class
	#observations = relationship to Observation class

	def __repr__(self):
		return self.common_name

	@hybrid_property
	def full_taxonomic_name_species(self):
		"""
			Concatenates all taxonomic information that PISCES includes so that we
			can use it for getting distinct values that aggregate subspecies to species level
		:return:
		"""

		return self.family + " " + self.genus + " " + self.species

	@hybrid_property
	def full_taxonomic_name_genus(self):
		"""
			same as full_taxonomic_name_species, but only goes down to unique genus level
		:return:
		"""
		return self.family + " " + self.genus


class SpeciesGroup(Base):
	"""
		Example usage:
			natives_group = session.Query(orm.SpeciesGroup).filter_by(name="Native_Fish").one()
			for fish in natives_group.taxa:
				## do something
				pass

		# in reverse
			hardhead = session.Query(orm.Species).filter_by(fid="CMC01").one()
			for group in hardhead.groups:
				## do something
				print(group.name)
	"""
	__tablename__ = local_vars.species_groups_table

	pkey = Column("id", Integer, primary_key=True)
	name = Column("group_name", String)
	short_name = Column("short_name", String)
	description = Column("description", String)

	taxa = relationship("Species",
                    secondary=species_groups,
                    backref="groups")

	def __repr__(self):
		return self.name


class TaxonomicLevel(Base):
	__tablename__ = local_vars.taxonomy_table

	pkey = Column("id", Integer, primary_key=True)
	level = Column("level", String)
	scientific_name = Column("scientific_name", String)
	common_name = Column("common_name", String)
	check_flag = Column("check_flag", Boolean)

	parent_level_id = Column("parent_level_id", Integer, ForeignKey("{}.id".format(local_vars.taxonomy_table)))
	parent_level = relationship("TaxonomicLevel",  backref="children", remote_side=[pkey])  # specify for the above, self-referencing relationship, what

	def confirm_tree(self, parent_scientific_name, db_session):
		"""
			Occasionally, at the species level, we have name collisions. By providing the parent_scientific_name,
			can confirm we got the correct taxonomic object. We can't do this through queries because traversing the
			relationship mid-query fails. Returns the *correct* taxonomy object
		:param parent_scientific_name:
		:param db_session:  Need to provide the session because if it the test fails, it'll try to give back the correct object
		:return:
		"""

		if self.parent_level.scientific_name == parent_scientific_name:
			return self
		else:
			if self.level.lower() == "species":
				parent_level = "Genus"
			elif self.level.lower() == "genus":
				parent_level = "Family"
			else:
				raise ValueError("Couldn't find correct taxonomic item and can't resolve by searching")

			potential_parents = db_session.query(TaxonomicLevel).filter(sqlalchemy.and_(TaxonomicLevel.level == parent_level, TaxonomicLevel.scientific_name == parent_scientific_name))
			for parent in potential_parents:
				for child in parent.children:
					if child.scientific_name == self.scientific_name:
						return child
			else:
				raise ValueError("This is not the correct taxonomy object, but also couldn't find correct one. Check parameters. Current scientific name is: {} - Looking for parent level of {} with scientific name of {}".format(self.scientific_name, parent_level, parent_scientific_name))

class Observer(Base):
	__tablename__ = local_vars.observers_table

	pkey = Column("objectid", Integer, primary_key=True)
	name = Column("name", String)
	notes = Column("notes", String)


class InputFilter(Base):
	__tablename__ = local_vars.input_filters_table

	pkey = Column("objectid", Integer, primary_key=True)

	code = Column("code", String)
	code_class = Column("class", String)
	full_name = Column("full_name", String)
	notes = Column("notes", String)

	default_observer_id = Column("default_observer", Integer, ForeignKey("{0:s}.objectid".format(local_vars.observers_table)))
	default_observer = relationship(Observer, primaryjoin=(default_observer_id == Observer.pkey))


class AlternateSpeciesName(Base):
	"""
		This table is used for importing data to map species IDs for other datasets to the PISCES ID
	"""
	__tablename__ = local_vars.alt_codes_table

	pkey = Column("objectid", Integer, primary_key=True)

	fid = Column("fid", String, ForeignKey("{0:s}.fid".format(local_vars.species_table)))
	species = relationship(Species, primaryjoin=(fid == Species.fid), backref="alternate_species_names")

	input_filter_code = Column("input_filter", String, ForeignKey("{0:s}.code".format(local_vars.input_filters_table)))
	input_filter = relationship(InputFilter, primaryjoin=(input_filter_code == InputFilter.code), backref="alternate_species_names")

	alternate_species_name = Column("alt_code", String)

	UniqueConstraint('input_filter', 'fid')


class CertaintyType(Base):
	__tablename__ = local_vars.certainty_types_table

	pkey = Column("certainty_type", Integer, primary_key=True)
	certainty_level = Column("certainty_level", Integer)
	description = Column("description", String)


class ObservationSet(Base):
	__tablename__ = local_vars.observation_sets_table

	pkey = Column("set_id", Integer, primary_key=True)
	species_id = Column("species", String, ForeignKey("species.fid"))
	species = relationship(Species, primaryjoin=(species_id == Species.fid), backref="observation_sets")

	source_data = Column(String)
	name = Column(String)

	input_filter_code = Column("input_filter", String, ForeignKey("{0:s}.code".format(local_vars.input_filters_table)))
	input_filter = relationship(InputFilter, primaryjoin=(input_filter_code == InputFilter.code), backref="observation_sets")


class IFMethod(Base):
	__tablename__ = local_vars.if_methods_table

	pkey = Column("objectid", Integer, primary_key=True)
	short_name = Column("short_name", String)
	description = Column("description", String)
	input_filter = Column("input_filter", String)
	default_observation_type = Column("default_observation_type", Integer)

	default_certainty = Column("default_certainty", Integer)

	parameters = Column("trigger", String)


class SurveyMethod(Base):
	__tablename__ = local_vars.survey_methods_table

	pkey = Column("id", Integer, primary_key=True)
	short_name = Column("short-name", String)
	description = Column("description", String)


class PresenceType(Base):
	__tablename__ = local_vars.presence_types_table

	pkey = Column("objectid", Integer, primary_key=True)

	type = Column("type", Integer)
	description = Column("description", String)
	default_certainty = Column("default_certainty", Integer)
	short_description = Column("short_desc", String)

	#observations = reference to Observation class

	def __repr__(self):
		return str(self.type)

class Zone(Base):
	__tablename__ = local_vars.zones_table

	pkey = Column("OBJECTID", Integer, primary_key=True)
	HUC_12 = Column(String)
	HUC_8 = Column(String)
	HU_12_DS = Column(String)
	HU_12_NAME = Column(String)
	HU_12_MOD = Column(String)
	states = Column("STATES", String)
	shape_area = Column("Shape_Area", Float)

	#observations = reference to Observation class

	def __repr__(self):
		return str(self.HUC_12)


class ZonesAux(Base):
	__tablename__ =local_vars.zones_aux

	pkey = Column("id", Integer, primary_key=True)

	zone = Column("zone", String)
	usforest_id1 = Column("usforest_id1", Integer)
	usforest_id2 = Column("usforest_id2", Integer)

	rim_dam = Column(Boolean)
	beta_div_nat_hist = Column(Float)
	beta_div_nat_cur = Column(Float)
	beta_div_nn_hist = Column(Float)
	beta_div_nn_cur = Column(Float)

	sierranevadamodoc = Column(Boolean)
	zoogeo2012_region = Column(String)
	zoogeo2012_subregion = Column(String)
	huc_update_2013_created = Column(Boolean)
	barrier_dams = Column(Boolean)
	in_state = Column(Boolean)

	freshwater_region = Column(String)


class Transaction(Base):
	__tablename__ = local_vars.transactions_table

	pkey = Column("id", Integer, primary_key=True)
	fid = Column(String, ForeignKey("{0:s}.fid".format(local_vars.species_table)))
	species = relationship(Species, primaryjoin=(fid == Species.fid), backref="transactions_from")
	species_input = Column("species_in", String)

	fid_to = Column(String)#, ForeignKey("{0:s}.fid".format(local_vars.species_table)))
	#species_to = relationship(Species, primaryjoin=(fid_to == Species.fid), backref="transactions_to")
	species_resulting = Column("species_to", String)
	operation = Column(String)

	input_filter_code = Column("input_filter", String, ForeignKey("{0:s}.code".format(local_vars.input_filters_table)))
	input_filter = relationship(InputFilter, primaryjoin=(input_filter_code == InputFilter.code), backref="transactions")

	message = Column(String)
	subset = Column(String)
	result = Column(String)
	datetime_conducted = Column(DateTime)


class Invalid_Observation(Base):
	"""
		Just a small part of the table that we actually need
	"""
	__tablename__ = local_vars.invalid_observations_table

	pkey = Column("id", Integer, primary_key=True)

	transaction_id = Column(Integer, ForeignKey("{0:s}.id".format(local_vars.transactions_table)))
	transaction = relationship(Transaction, primaryjoin=(transaction_id == Transaction.pkey), backref="invalid_observations")


class Species_Aux(Base):
	__tablename__ = local_vars.species_aux_table

	pkey = Column("id", Integer, primary_key=True)
	#qc = Column("qc", Integer) # Fully deprecated and rely on collections instead

	fid = Column("fid", String, ForeignKey("{0:s}.fid".format(local_vars.species_table)))
	species = relationship(Species, primaryjoin=(fid == Species.fid), backref="aux")

	status = Column("status", String)
	r5_summary = Column("r5_summary", String)
	description = Column("description", String)
	taxonomic_relationships = Column("taxonomic_relationships", String)
	life_history = Column("life_history", String)
	habitat_requirements = Column("habitat_requirements", String)
	distribution = Column("distribution", String)
	distribution_score = Column("distribution_score", Integer)
	abundance_trends = Column("abundance_trends", String)
	threats = Column("threats", String)
	threat_caption = Column("threat_caption", String)
	climate_effects = Column("climate_effects", String)
	status_determination = Column("status_determination", String)
	metrics_caption = Column("metrics_caption", String)
	management_recommendations = Column("management_recommendations", String)
	major_dams_rating = Column("major_dams_rating", String)
	major_dams_explanation = Column("major_dams_explanation", String)
	agriculture_rating = Column("agriculture_rating", String)
	agriculture_explanation = Column("agriculture_explanation", String)
	grazing_rating = Column("grazing_rating", String)
	grazing_explanation = Column("grazing_explanation", String)
	rural_rating = Column("rural_rating", String)
	rural_explanation = Column("rural_explanation", String)
	urbanization_rating = Column("urbanization_rating", String)
	urbanization_explanation = Column("urbanization_explanation", String)
	instreammining_rating = Column("instreammining_rating", String)
	instreammining_explanation = Column("instreammining_explanation", String)
	mining_rating = Column("mining_rating", String)
	mining_explanation = Column("mining_explanation", String)
	estuarinealteration_rating = Column("estuarinealteration_rating", String)
	estuarinealteration_explanation = Column("estuarinealteration_explanation", String)
	transportation_rating = Column("transportation_rating", String)
	transportation_explanation = Column("transportation_explanation", String)
	logging_rating = Column("logging_rating", String)
	logging_explanation = Column("logging_explanation", String)
	fire_rating = Column("fire_rating", String)
	fire_explanation = Column("fire_explanation", String)
	recreation_rating = Column("recreation_rating", String)
	recreation_explanation = Column("recreation_explanation", String)
	harvest_rating = Column("harvest_rating", String)
	harvest_explanation = Column("harvest_explanation", String)
	hatcheries_rating = Column("hatcheries_rating", String)
	hatcheries_explanation = Column("hatcheries_explanation", String)
	alienspecies_rating = Column("alienspecies_rating", String)
	alienspecies_explanation = Column("alienspecies_explanation", String)
	areaoccupied_score = Column("areaoccupied_score", Integer)
	areaoccupied_justification = Column("areaoccupied_justification", String)
	popsize_score = Column("popsize_score", Integer)
	popsize_justification = Column("popsize_justification", String)
	interventiondependence_score = Column("interventiondependence_score", Integer)
	interventiondependence_justification = Column("interventiondependence_justification", String)
	tolerance_score = Column("tolerance_score", Integer)
	tolerance_justification = Column("tolerance_justification", String)
	geneticrisk_score = Column("geneticrisk_score", Integer)
	geneticrisk_justification = Column("geneticrisk_justification", String)
	climatechange_score = Column("climatechange_score", Integer)
	climatechange_justification = Column("climatechange_justification", String)
	threats_score = Column("threats_score", Integer)
	threats_justification = Column("threats_justification", String)
	average = Column("average", Float)
	certainty = Column("certainty", Integer)
	certainty_justification = Column("certainty_justification", String)
	lifestyle = Column("lifestyle", String)
	katzmoyle_status = Column("katzmoyle_status", String)
	ca_status = Column("ca_status", String)
	fed_listing = Column("fed_listing", String)
	ca_listing = Column("ca_listing", String)
	fs_sensitive_status = Column("fs_sensitive_status", Integer)


observation_collections = Table(local_vars.observation_collections_table, Base.metadata,
    Column('observation_id', Integer, ForeignKey('{0:s}.objectid'.format(local_vars.observations_table))),
    Column('collection_id', Integer, ForeignKey('{0:s}.id'.format(local_vars.collections_table)))
)


class Collection(Base):
	"""
		Example of use for getting observations

		hq_collection = session.query(orm.Collection).filter_by(pkey=5).one()  # retrieves the collection in question
		for observation in hq_collection.observations:

	"""
	__tablename__ = local_vars.collections_table

	pkey = Column("id", Integer, primary_key=True)
	name = Column("collection_name", String)
	short_name = Column("short_name", String)
	description = Column("description", String)
	#observations = reference to Observation


class MapSet(Base):
	__tablename__ = local_vars.maps_table

	pkey = Column("id", Integer, primary_key=True)

	name = Column("set_name", String)
	title = Column("map_title", String)
	short_name = Column("short_name", String)
	description = Column("description", String)
	base_mxd = Column("base_mxd", String)
	ddp_mxd = Column("ddp_mxd", String)
	iterator = Column("iterator", String)
	is_active = Column("active", Integer)
	callback = Column("callback", String)
	callback_args = Column("callback_args", String)


class MapLayers(Base):
	__tablename__ = local_vars.map_layers_table

	pkey = Column("id", Integer, primary_key=True)

	query = Column("custom_query", String)
	name = Column("layer_name", String)
	short_name = Column("short_name", String)
	rank = Column("query_rank", Integer)
	description = Column("description", String)
	iterator = Column("iterator", String)
	layer_file = Column("layer_file", String)
	callback_function = Column("callback_function", String)
	callback_args = Column("callback_args", String)

	map_set_id = Column("query_set", Integer, ForeignKey("{0:s}.id".format(local_vars.maps_table)))
	map_set = relationship(MapSet, primaryjoin=(map_set_id == MapSet.pkey), backref="layers")


class Observation(Base):
	__tablename__ = local_vars.observations_table

	pkey = Column("objectid", Integer, primary_key=True)

	set_id = Column(Integer, ForeignKey("{0:s}.set_id".format(local_vars.observation_sets_table)))
	set = relationship(ObservationSet, primaryjoin=(set_id == ObservationSet.pkey), backref="observations")

	species_id = Column("species_id", String, ForeignKey("{0:s}.fid".format(local_vars.species_table)))
	species = relationship(Species, primaryjoin=(species_id == Species.fid), backref="observations")

	zone_id = Column("zone_id", String, ForeignKey("{0:s}.HUC_12".format(local_vars.zones_table)))
	zone = relationship(Zone, primaryjoin=(zone_id == Zone.HUC_12), backref="observations")

	presence_type_id = Column("presence_type", Integer, ForeignKey("{0:s}.objectid".format(local_vars.presence_types_table)))
	presence_type = relationship(PresenceType, primaryjoin=(presence_type_id == PresenceType.pkey), backref="observations")

	if_method_id = Column("if_method", Integer, ForeignKey("{0:s}.objectid".format(local_vars.if_methods_table)))
	if_method = relationship(IFMethod, primaryjoin=(if_method_id == IFMethod.pkey), backref="observations")

	survey_method_id = Column("survey_method", Integer, ForeignKey("{0:s}.id".format(local_vars.survey_methods_table)))
	survey_method = relationship(SurveyMethod, primaryjoin=(survey_method_id == SurveyMethod.pkey), backref="observations")

	notes = Column("notes", String)
	longitude = Column("longitude", String)
	latitude = Column("latitude", String)
	observation_date = Column("observation_date", String)
	date_added = Column("date_added", String)
	other_data = Column("other_data", String)



	collections = relationship("Collection",
                    secondary=observation_collections,
                    backref="observations")
