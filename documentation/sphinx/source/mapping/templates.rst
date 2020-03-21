.. _base-mxd:

Base Templates
==============

Base Map Templates
------------------
Map templates are the base documents used for map sets. Map templates allow the user to define a map layout once and then apply it to all future map outputs. To work properly, each base :term:`mxd` needs to have an empty feature layer with no data. This empty layer must have its data source as *PISCES/data/layer_cache.gdb/blank_feature*. This is a place holder for feature layers that sits at the level in the document where the new features are placed. When PISCES generates a new map that uses the template MXD, it will begin placing layers into the hierarchy at the location of this placeholder layer

All map sets base templates are saved in *PISCES/mxds/base*.

Data Driven Pages (DDP) Templates
---------------------------------
To create a map set template to be used for a :term:`data driven pages` output - the configuration must be done in the map document. Data driven pages are a series of layout pages from a single map document. A feature layer, or index layer, divides the map into sections based on each index feature in the layer and generates one page per index feature. To create a data driven pages map template, data driven pages must be enabled and the index layer and field must be defined in the setup menu in the ArcMap Data Driven Pages tool bar.



See ArcGIS help documentation for further help about setting up data driven pages:
  
http://resources.arcgis.com/en/help/main/10.2/index.html#/Creating_Data_Driven_Pages/00s90000003n000000/

.. _map-variables:

Mapping Template Replacement Variables
--------------------------------------

Mapping template variables are placed in template map documents and are replaced during map generation by PISCES. They can be placed in any text field in ArcMap and will be found and replaced. Standard ArcGIS mapping dynamic text can also be used. The variables can be used as many times as necessary and multiple variables may be used in a given text field. They are case sensitive and should be written exactly as seen below in the variable column (including the curly braces).


+---------------------+-------------------------------------------------------------------------------------------------------+
| Variable            | Replacement                                                                                           |
+=====================+=======================================================================================================+
| {Title}             | The map title as defined in the map definition in the database.                                       |
+---------------------+-------------------------------------------------------------------------------------------------------+
| {Scientific Name}   | When a map is mapped per species, the scientific name of that species.                                |
+---------------------+-------------------------------------------------------------------------------------------------------+
| {Species}           | When a map is mapped per species, the common name of that species.                                    |
+---------------------+-------------------------------------------------------------------------------------------------------+
| {Bind}              | When a map is mapped for many values (such as per species), the value the map is run for.             |
+---------------------+-------------------------------------------------------------------------------------------------------+
| {Date}              | The date the map was generated. Can also be accomplished with dynamic text.                           |
+---------------------+-------------------------------------------------------------------------------------------------------+
| {Version}           | The PISCES version that generated the map.                                                            |
+---------------------+-------------------------------------------------------------------------------------------------------+
| {Sources}           | List of all of the original sources for the distribution data.                                        |
+---------------------+-------------------------------------------------------------------------------------------------------+
| {hq_collections}    | The IDs of the data collections that have been quality contolled. Also available in map queries.      |
+---------------------+-------------------------------------------------------------------------------------------------------+
