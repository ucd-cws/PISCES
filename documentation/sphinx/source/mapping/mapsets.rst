.. _mapsets:

Configuring Maps
====================================

--------------------------------------------------
Map Sets
--------------------------------------------------
Map generation in PISCES is automated by using preconfigured map sets. Map sets are a composed of one or more PISCES-generated layers to be added to a :doc:`template map document<templates>` that can itself be expanded to generate multiple maps for one or more species. Map sets are highly customizable and allow the user to quickly create standardized map outputs.

Map sets have three main parts to their definition:

#. :ref:`Map set core (title, map-wide specifications, enabled/disabled, etc)<defs-query-sets>`
#. :ref:`Map layers (definitions for the database query, layer name, symbology, etc for each layer)<map-queries>`
#. :ref:`Scope of the map output (selected species or species group)<query-bind>`

To find out more about how mapping works in PISCES, see :ref:`How mapping works in PISCES<how-mapping-works>`.
To learn more about creating a new map, see :ref:`Setting up a new map for export<new-map>`.

.. _defs-query-sets: 

Map Set Core Definition 
^^^^^^^^^^^^^^^^^^^^^^^^^^

**Defined in:** :ref:`defs_Query_Sets<defs-query-sets>`

For every map, define a single "map core" record in the **defs_query_sets** table. These "map cores" are templates that are used to generate all of the maps in a map set. To create a new map set, simply add a new record at the bottom of the table.
  
.. list-table::
	:widths: 10 30
	:header-rows: 1
	
	* - Field Name
	  - Description
	* - ID
	  - Autonumber	 
	* - Set_Name
	  - A name for the map  
	* - Map_Title
	  - A title for the map - used with the {Title} :ref:`replacement variable<map-variables>` 
	* - Short_Name
	  - A short name that will be used in other places in PISCES to reference this map. This should be short enough to read in another database field.
	* - Set_Description
	  - A description for the map set to describe what it displays or how it differs from others 
	* - Base_MXD
	  - A :ref:`base template mxd<base-mxd>` (see maps in the mxds/base folder for examples)
	* - DDP_MXD
	  - A optional :ref:`template<base-mxd>` to be used for :term:`data driven pages` output 
	* - Iterator
	  - A table name and field to use as unique values for :ref:`layer query bind variables<query-bind>` in the format table_name:field_name. For maps queries that take bind variables and where you have specified 'all', PISCES retrieves all the unique values in the specified field and creates a new map for each one and passes that value in as the bind variable. For maps that specify all, without an iterator, the iterator defaults to Species:FID 	  
	* - Active
	  - A flag to control whether or not a map should be generated. Only checked (True) maps will be output.	  
	* - Callback
	  - [Unimplemented]	  
	* - Callback_Args
	  - [Unimplemented]	  
 	  
	  
.. _map-queries:
	
Layers in a Map Set
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Table: Map_Queries**

Each layer for a map set has to be defined in **Map_Queries**. The software has no limit on the number of layers to be added to a map, but you should limit the number of layers by time and view ability. A map must have at least one layer.


.. list-table::
   :widths: 10 30
   :header-rows: 1

   * - Field Name
     - Description
   * - ID
     - AutoNumber
   * - Custom_Query
     - Query can return any number of items, though one of them must be read as Zone_ID. Each Zone_ID gets stored in an array for access by the callback
   * - Layer_Name
     - Name for each feature layer
   * - Query_Set
     - ID of map set that query is part of. See :ref:`defs_Query_Sets<defs-query-sets>` for table of possible map sets.
   * - Query_Rank
     - Stacking Order: Layer 1 is on top, 2 is below it, etc
   * - Description
     - Any notes about query or layer
   * - Iterator
     - 
   * - Layer_File
     - Optional: A custom file to use for symbology, etc. Set to a custom file if there are more than four layers in a map or you don't want the defaults.
   * - :ref:`Callback_Function<map-callbacks>`
     - Optional: Take the selection from custom_query as the parameter to a custom function and return a layer file. This can be used for custom post-processing of zones.
   * - :ref:`Callback_Args<map-callbacks>`
     - Optional: Arguments for the callback. Each argument should be separated by two colons ( :: )
   * - Short_Name
     -    
   * - Metadata_plugin
     - Sets if the generate metadata plugin is configured for the layer.
   * - Metadata_args
     - Arguments for the metadata plugin.
   * - Name_Formula
	 - Sets the layer name format for layers using :ref:`map replacement variables<map-variables>`

	 
.. _query-bind:

Map Set Output Scope (Query_Bind)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


**Table: Query_Bind**

PISCES generates a map for every distinct value in the **defs_Query_sets** iterator column (table:column), passing the values in to each layer's query as the "bind parameter" in the table **Query_Bind**. The bind parameter can be a :term:`species code`, :term:`species groups` or "all".  The bind parameter pulls all the species FIDs requested, and the mapping code will retrieve those records for a map set, expand any groups out to their species code and merge the resulting values.
