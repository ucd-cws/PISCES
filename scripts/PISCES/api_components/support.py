import six

from sqlalchemy import distinct
import sqlalchemy

from .. import local_vars
from .. import funcs
from .. import orm_models as orm

from ..funcs import isiterable

def _parse_presence_types_and_collections_to_list(item):

	# if iterable, return the iterable
	if isiterable(item):
		return item

	# if integer, return it as a list
	if type(item) is int:
		return [int]

	# if string, split based on comma to return as list
	if type(item) in (six.binary_type, six.text_type):
		return [int(single_item) for single_item in item.split(",")]  # split based on comma and cast to int before putting in list

def connect_orm(hotload=False):
	"""
		A convenience function that connects to the database and creates a session.
	:param hotload: A workaround for a bug (or a behavior I don't understand) where backreferences
					can't be traversed unless some object comes through the pipe first. So, when
					hotload is True, we load an object (doesn't matter what it is) so that future
					queries that traverse relationships work. Modifying lazyloading behavior
					or sqlalchemy versions didn't work.
	:return:
	"""

	orm.connect(local_vars.ormdb)
	session = orm.Session()

	if hotload:
		session.query(orm.Observation).filter(orm.Observation.pkey==5)

	return session


def _check_group_name(group_name, session):
	"""
		Given a group name, checks to make sure it exists
	:param group_name:
	:param session:
	:return:
	"""
	try:
		session.query(orm.SpeciesGroup).filter(orm.SpeciesGroup.name == group_name).one()
	except sqlalchemy.orm.exc.NoResultFound:
		group_names = session.query(distinct(orm.SpeciesGroup.name))
		raise ValueError("Group name \"{}\" does not exist. The following groups exist: {}".format(group_name, ", ".join([r[0] for r in group_names])))

	return True  # for testing purposes


def text_or_list_to_species_objects(text_or_list, session=None):
	"""
		Given a delimited set of species codes or groups, or a list of species codes or groups,
		returns the actual species objects (via the ORM) corresponding to those species
	:param text_or_list: comma or semicolon delimited text of species codes and groups (mixed is OK), or a list of the same.
	:return: orm_models.Species objects for each species
	"""

	taxa_codes = funcs.text_to_species_list(text_or_list)

	session_opened = False
	if not session:
		session = connect_orm()
		session_opened = True

	try:
		taxa_objects = session.query(orm.Species).filter(orm.Species.fid.in_(taxa_codes))
		return taxa_objects
	finally:
		if session_opened:
			session.close()
