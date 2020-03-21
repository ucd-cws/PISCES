.. _map-callbacks:

Map Callbacks
=============

Map callbacks take zones selected by a query as the parameter and return a feature layer file by applying a customized query or function. This can be used for custom processing of zones. Map callbacks can be customized for individual layers of a map set in the :ref:`Map_Queries <map-queries>` table. The map callback uses the :ref:`SQL query<sql_tutorial>` in Custom_query to set the zones that are selected and stored in an array for the callback. The query can return any item but one must be read as Zone_ID. Zones typically are the mapping unit (:term:`HUC12s`) but don't necessarily have to be. Unknown items in the custom query such as the :term:`species code` can be referenced using the SQL bind replacement variable "?".


**Key Points:**
 * Map callbacks take the zones selected by the custom_query and apply the function described by the callback and arguments
 * Arguments should be separated by two colons ( :: )
 * Some callback can take multiple arguments
 * Values in callback argument queries should be selected "AS col_value"


------------------------------------------------------------------ 

.. list-table::
	:widths: 5 15 20
	:header-rows: 1
	
	* - Callback
	  - Arguments
	  - Description
	* - **add_field**
	  - SQL_query::Fieldname_created::Fieldtype_created
	  - Executes a SQL query once, and joins result to the output layer. Meant to be used for summary queries that summarize by HUC12s.
	* - **connectivity**
	  - Fieldtype::Fieldname_1
	  - Calculates the sum of an attribute upstream from a location, can take multiple attributes.
	* - **network_distance**
	  - Zone_1
	  - Calculates the network distance between two zones or one zone and all other zones.
	* - **diversity**
	  - Grouping::Dams?::Diversity_Type::QC_data
  	  - Calculates beta diversity (Jaccard distance) 
	* - **postprocess_zones**
	  - SQL_query::Fieldname_created::Fieldtype_created
	  - Takes each record in the zones_layer and runs the query. Zone should be replaced with the SQL bind variable "?". Value to be returned should be selected "As col_value". Multiple arguments can be passed to callback but need to be in the format of Fieldname::Fieldtype
	* - **mega_diversity_info**
	  - 
	  - Many richness functions in a single layer
	* - **representation**
	  - 
	  - Ranges are represented as stream lines instead of HUCs
	* - **richness_difference**
	  - Species_group::Observation_Collections
	  - Calculates current richness, historical richness, losses and additions for each zone. Can be limited to specific species groups and observation collection
	* - **get_downstream_diversities**
	  - 
	  - Calculates the downstream assemblage information for each zone
	* - **sensitivity_stats**
	  - 
	  - Calculates sensitivity statistics for each zone
	* - **export_raster**
	  - Value::Template_raster::Export_Folder::Raster_type
 	  - Exports ranges as rasters for use in Zonation
