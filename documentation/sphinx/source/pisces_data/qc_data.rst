.. _qc-data:

Quality Controlled Data
=======================

Quality controlled (QC) data sets are established :ref:`collections<collections>` of vetted and reviewed species records.
Members of the quality controlled data collection have gone through a quality control process with taxa experts.
Members of quality controlled collections represent the best available knowledge and are considered authoritative.


By default, new records imported to PISCES are not part of quality controlled collections. Data sources vary in quality
and completeness, which can introduce errors in the database. New data should be reviewed by appropriate taxa experts
to verify that the records are classified correctly and valid. Then, records can be added to a quality controlled
collection using the :ref:`Add Species Data to Collection Tool<tool-add2collection>`.

.. NOTE::

	Many map sets and queries are set up to run using only quality controlled data sources. Data records that
	are not yet part of the quality controlled collection are not included in the outputs. For example, the
	map set **Main Range Maps** will only output data that belongs to current quality controlled data collections
	(sets numbered 5 and 15, below). If you don't want to limit the results to quality controlled observations,
	use the **Unlimited Range Maps** which will use all data.


For more information on collections in general and their uses in PISCES, see the main article on :ref:`collections<collections>`.

Established QC Data Collections
-------------------------------

.. csv-table:: 
	:header: ID, Name, Date, # Species, Notes
	:widths: 2, 15, 5, 8, 25
	
	1, Fish Species of Special Concern, 12/15/2011, 65, Best available expert knowledge (Katz-Santos) as delivered to the Forest Service
	5, CA Native Fish QC, 8/31/2013, 133, Best available expert knowledge (Moyle-Quiñones-Bell) for all California native fish. Includes current and historic distributions as well as translocations.
	15, Non-native fish QC, 12/12/2013, 48, Best available knowledge (Moyle-Quiñones-Bell) for non-native fish in California