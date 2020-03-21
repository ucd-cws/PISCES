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


transaction_to_reverse = arcpy.GetParameterAsText(0)


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