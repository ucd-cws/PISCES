.. _defs:

Defs Tables
=============

Definition (Defs) tables set the schema for specific values for columns in another table in the database. In relational databases, the defs tables establish the values and properties of the data tables that actually store the data. Many defs tables can be appended with more values, please see the :ref:`Database Tutorial<tutorials>` for instructions. 

.. _defs-survey-methods:

defs_survey_methods
--------------------
Different types of survey methods (such as electric fishing, snorkel, gil nets) for sampling or collecting fish. These values are used for setting the survey method field when importing new datasets or adding observations. Please add more values to the table if applicable. 

.. _defs-collections:

defs_collections
--------------------

:ref:`Collections<collections>` are a way to group any set of observation records for retrieval by the PISCES export tools. Collections are defined by the user to distinguish database level differences in the type and quality of the data. It is a quick way to subset records for map outputs and database queries that belong to the same data group.

New collections must have a unique name and a unique abbreviation as well as a short description explaining the properties of the members of the collection.

:ref:`For more information, see the Collections section<collections>`


.. _defs-observation-types:

defs_observation_types
------------------------

Definition table for setting :ref:`observations types<obs-types>`. Observations types are classification based on the source and type of the data. Observation types add extra information about the quality and meaning of the data. Supported observation types include actual records as well as expert opinion for occurrence and inference from modeling. PISCES currently supports 10 different observation types. New observation types may be added as needed but other components would need to be updated in order to be included in outputs.

:ref:`For more information, see Observation Presence Types<obs-types>`


.. _defs-input-filters:

defs_input_filters
--------------------
Lists :ref:`input filters<input-filters>` that are configured for specific data sets. All data that is imported into the database must be configured through an input filter. Input filters are interpreters for datasets that configure the data to be compatible with PISCES. Data comes in many forms and formats, input filters are custom configurations to standardize common types of occurrence data to HUC12s. Input filters are classes of python code that handle a type of data. They are hierarchical by default due to python and extensible due to how PISCES is built. They are all based on a core set of code and have extensions that make them more useful to a particular type of source data or types of source data.

.. _defs-if-methods:

defs_if_methods
----------------
Custom methods that build on the :ref:`input filters<input-filters>`. These can be set to customize existing :ref:`defs_input_filters<defs-input-filters>` to match data that is of a similar format of a pre-existing input filter. 


.. _defs-certainty-types:

defs_certainty_types
---------------------
Sets the values for the certainty level of records in the observation table. Initially implemented to document different levels of data quality (Highly Certain, Moderately Certain or Uncertain), this feature is not used consistently throughout the database. The method of classifying data into these categories was replaced by using :ref:`observation types<obs-types>` and :ref:`quality controlled collections<qc-data>`.


.. _def-species-groups:

defs_species_groups
-------------------
	
This definition table is where new :ref:`species groups<species-group>` are set. Groups are list of species that can be used for creating and classifying assemblages. Groupings are a useful way to organize species into many different categories. Species can belong to many different groups. Each new species group mush have unique name as well as an abbreviation and description set in defs_species_groups.

:ref:`For more information, see the Species Groups section<species-group>`

.. _defs-query-sets:

defs_query_sets
----------------

:ref:`Please see the Configuring Maps section for more information<mapsets>`