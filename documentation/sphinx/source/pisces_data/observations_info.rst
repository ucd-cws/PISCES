Observations
============

**Key Concepts:**
	* Records are stored in a table called :ref:`observations<observations>`
	* Records have different :ref:`observation presence types<obs-types>`
	* :ref:`Collections<collections>` are sets of records that have similar data quality
	* All information is flagged with a :term:`observation set` corresponding to the data source
	* Records that are removed from the database are stored in :ref:`Invalid Observations Table<table-invalid-observations>`

.. _observations:

	
Table: Observations
-------------------
.. _obs-table:

.. list-table::
   :widths: 8 25
   :header-rows: 1

   * - Field Name
     - Description
   * - OBJECTID
     - Primary Key
   * - SET_ID
     - The :term:`observation set` that is associated with the record from the :term:`input filter`
   * - Species_ID
     - PISCES :term:`Species code` for the record
   * - Zone_ID
     - Mapping Unit (:term:`HUC12`) ID
   * - Presence_Type
     - The :ref:`observation types<obs-types>` of the record
   * - IF_Method
     - The :term:`input filter` code path that processed this observation from source data
   * - Certainty
     - Certainty value of a record (*depreciated*)
   * - Longitude
     - Longitude if observation came from point data
   * - Latitude
     - Latitude if observation came from point data
   * - Survey_Method
     - Type of surveying method used to capture and identify species. 
   * - Notes
     - Additional information about the record added by operator
   * - Observation_Date
     - Date of the observation as noted in the source data 
   * - Date_Added
     - Date and time record was added to the database
   * - Other_Data
     - Semicolon separated fields captured by :term:`input filter`

.. _collections:


Collections
-----------
**Defined in**: :ref:`defs_Collections<defs-collections>`

Collections are a way to group any set of observation records for retrieval by the PISCES export tools (for example records that have undergone review). Collections are defined by the user to distinguish database level differences in the type and quality of the data. It is a quick way to subset records for map outputs and database queries that belong to the same data group.

The main use for data collections is for distinguishing quality controlled data. :ref:`Quality controlled data<qc-data>` collections are sets of records that have been vetted and reviewed by experts and considered authoritative. Many map sets and queries are set up to run using only quality controlled data. Data records that don't belong to the collection are not included in the output until the records are reviewed by experts and then added to the collection. Collections can be used to segment off data for more than just quality control purposes. When PISCES' copy of the HUC12s was updated, a collection of records affected by the change was created so that it would be possible to track those changes.

Records for species can be added to collections using the :ref:`Add Species Data to Collection<tool-add2collection>` tool. The tool appends the new records for the species to the collection.


Workflow with Collections
-------------------------
Collections are commonly used as part of the editing workflow, and are the structure underlying PISCES :ref:`quality controlled data<qc-data>`. Collections usually come in as the final part of the :ref:`editing workflow<range_edits>`. First, the PISCES operator will :ref:`import a new dataset<import_TOC>`, which contains untrusted data - aka data that hasn't been vetted to be valid, or which doesn't translate cleanly to HUC12s. Then, the operator can :ref:`generate a range map<generate_maps>` showing all data available for a given taxon (map set Unlimited Range Maps). Using the resulting map document and the :ref:`tool to modify data<addmodify>`, low quality and incorrect data can be removed from a range, and new data added to fill in, based on available experts. Once that process is complete, the operator runs the :ref:`Add Species Data to Collection<tool-add2collection>` tool, adding the data to one of the :ref:`quality controlled data collections<qc-data>` to mark any remaining records for the taxon as being of high quality. Once the records are added to the appropriate collections, the data will show up on the maps for high quality data (Main Range Maps)


.. _transaction-logs:


Transaction Logs
----------------

The database logs all transactions so that changes can be traced. Often, changes can be easily reverted. 
The database logs all changes from the :ref:`Add or Modify Data tool<tool-addmodify-data>` in 
the :ref:`Transactions Table<table-transactions>`.


All records that are removed are stored in a table called :ref:`Invalid Observations<table-invalid-observations>`. 
The table documents the rational why records were removed from database. 
Transactions can be reverted using the :ref:`Undo Transaction Tool<tool-undo-transaction>`.


