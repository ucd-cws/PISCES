.. _input-filters:

Input Filters
=============

Input filters are interpreters for datasets that configure the data to be compatible with PISCES. Data comes in many forms and formats, input filters are custom configurations to standardize common types of occurrence data to HUC12s.

Input filters are classes of python code that handle a type of data. They are hierarchical by default due to python and extensible due to how PISCES is built. They are all based on a core set of code and have extensions that make them more useful to a particular type of source data or types of source data.

Input filters have two parts - the definition of defaults (:ref:`information in new_data.mdb<import-config>` and :ref:`species identifiers<alt-codes>`) and a python code class that handles the importing of data. These two parts are independent and a python class can (and does) work for multiple input filters. 

Built-in Input Filter Classes
-----------------------------
PISCES has the following :ref:`Input Filters<defs-input-filters>` primary code classes to be used when configuring new datasets. Code for these input filters is available :ref:`in the API reference<input-filters-code>`

.. csv-table:: 
	:header: Input Filter, Description
	:widths: 10, 25
	
	Gen_Poly_IF, Generic Filter for polygons
	Gen_Table_IF, Generic Filter for tables that have a species column and a column for x/y 
	HUC12_IF, Dataset that have a HUC12 Zone ID field 
	Filtered_Table_IF, Filters table using customized selection
	Molye_IF, Moyle distribution maps importer
	CNDDB_IF, Imports data from the California Natural Diversity Database
	R5_Table_IF, Propriety format of USFS region 5 database


If your dataset doesn't match an existing input filter, you will need to create and configure one. See :ref:`Extending Input Filters<extending-input-filters>` for more information.

