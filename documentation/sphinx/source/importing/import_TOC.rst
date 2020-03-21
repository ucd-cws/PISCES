Importing Data
==================================


.. _import-types:

PISCES recognizes and handles the following forms of spatial and tabular data:

#. **Point**, **line** or **polygon** data where
	#. all features in the file represent the occurrence of a single species (though possibly of varying :ref:`occurrence_types<obs-types>`)
	#. each feature has a field indicating a taxon
	#. each feature has multiple fields where the field name indicates the taxon and the value of that field for each feature indicates a form of presence  
#. **Tables** with a field for x coordinates and a field for y coordinates and
	#. each row has a field indicating a taxon
	#. each feature has multiple fields where the field name indicates the taxon and the value of that field for each feature indicates a form of presence  

PISCES code does not automatically recognize that a dataset is one of these data types - you will need to specify which one it is when you configure it. A dataset that does not match these formats can still be imported, but will possibly need additional code to be functional.

Adding additional datasets to PISCES is separated into two main steps, **configuration** and **import**.


.. toctree::
   :maxdepth: 1
   
   import_config
   alt_codes
   input_filters  
   extending_input_filters
   import_run
 
