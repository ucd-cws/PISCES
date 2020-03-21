.. _import-config:

Configuring Data for Import
=================

Configuring data for import can be done using the :ref:`Import Data Tool<tool-import-data>` in the :ref:`PISCES toolbox<tools>` as well as manually in **New_Data.mdb**. The Import Data Tool is a limited functionality tool that covers most import use cases

Please see the :ref:`Importing Data Tutorial<tutorials>` for more information. Some related reference information is below.

.. _new-data-table:

Add to New_Data.mdb
-------------------

Configuring data for import into PISCES happens in **PISCES\\inputs\\New_Data.mdb**. Add the feature or table from the data storage folder to New_Data.mdb. This is a temporary workspace that is only used for configure new data sets prior to importing the records to the main PISCES database. Full configuration for each data set needs to happen in the New_Data.mdb database or the import will not be successful. PISCES code does not automatically recognize what :ref:`type of data<import-types>` is in a dataset or what the fields in the dataset represent. 


Add source to NewData Table
###########################

Each unique feature or table for importing records needs to be appended to the **NewData** table. The **NewData** table sets the operations to use when PISCES runs the data import functions, so it is very important to configure correctly. 


.. csv-table:: 
	:header: Field Name, Description
	:widths: 10, 25
	
	ID, Autonumber
	Feature_Class_Name, The name of the feature or table in New_Data.mdb
	Species_ID,  The PISCES :term:`species code` (or :ref:`Alt_codes<alt-codes>`) if it is a single species or filter if the data contains records for multiple species.
	Input_Filter, The :ref:`input filter<input-filters>` that will be used to process the data set
	Presence_type, The default :ref:`observation presence type<obs-types>`
	IF_Method, Configuration options for the :ref:`input filter<input-filters>`
	Observer_ID, The default observer for the dataset (see the :ref:`Observers table<table-observers>`)
	Survey_Methods, The :ref:`survey method<defs-survey-methods>` used to collect the data
	Notes, Any notes about the data set
	Imported, The PISCES dataset ID of the imported dataset, to link imported data to its import configuration. Enter 0 when setting up a dataset for automatic import so PISCES knows it needs to be imported (fills in automatically once records are added).
	Input_Filter_Args, [Unimplemented]
	Projection, projection of the data source - enter the EPSG/WKID of the data - this only applies when coordinates are given in a table and PISCES needs to create the spatial component to determine the corresponding HUC12s.
	
	

FieldMapping
############

Each field in the feature or table to be imported into the database must be referenced or mapped to a field type that the :ref:`input filter<input-filters>` can process. PISCES :ref:`input filters<input-filters>` match the inputs from the **FieldMapping** table to interpret the data in a standardized format. The PISCES import functions recognizes fields for Species, Latitude, Longitude, Zone_ID (:term:`HUC12`), Date, :ref:`Certainty<defs-certainty-types>`, :ref:`Observer<table-observers>` , :ref:`Observation Type<obs-types>` , :ref:`Survey Method<defs-survey-methods>`, and Notes/Items. Each unique field mapping should be added separately to the table, but make sure that all of the fields reference the NewData ID number. 

.. csv-table:: 
	:header: Field Name, Description
	:widths: 10, 25
	
	ID, Autonumber
	NewData_ID, The ID for the feature class in the :ref:`NewData table<new-data-table>`
	Field_Name, The field in the database that the item will be placed into
	Input_Field, The name of the field in the input data that will be standardized
	Handler_Function, Optional function to pass the data through before it gets mapped to the field in Field_Name
	Required, If field is required and there is not data then the importer skips the observation

.. note::Multiple fields can be referenced to the **NotesItems** field type. Each field name should be separated by a semicolon.










