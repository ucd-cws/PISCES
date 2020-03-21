.. _how-mapping-works:

How PISCES Mapping Works
========================
PISCES mapping is a flexible automation system for generating large numbers of maps in the same style, but with different underlying data. While the most common map outputs from PISCES are species range maps, these maps are not hard coded into PISCES - they are instead created through map configurations called :ref:`Map Sets<mapsets>`. The one used to generate species range maps is called "Main Range Maps," but you are free to modify or add new map sets as necessary.

These map sets are not limited to generating species range maps. They can combine and mash up any data in the PISCES database, including species status information, connections between range information, or HUC 12 characteristics, in order to generate maps with different thematic content. The only limit is that these maps should be depicted by HUC 12s, since they are the core PISCES data storage unit (however, even this limitation does not apply to advanced PISCES mapping).

PISCES map sets serve as core configurations that are meant to be duplicated - when a map is configured for one species, it is able to be run for all species simultaneously, allowing us to configure a single "Main Range Maps" configuration to generate all of primary outputs for species. When PISCES mapping is run, you can then specify which taxa to generate the map for and PISCES will set up a map and populate it for each one.

The most critical part of PISCES mapping to understand are that each map set has a template ArcGIS map document that's used as the base map. Into this map document, PISCES injects the layers that are generated for the map. Each map has one or more layers, which are produced by executing a custom SQL query against the PISCES database. These SQL queries must always produce a set of HUC12 IDs in order to be valid. So long as they do PISCES will then populate a new feature class with the resulting HUC12s, symbolize the layer, and inject the result into the template map document, doing this whole process for as many species as it is supposed to run the map for (expect for maps that only produce a single result, like richness maps.)

For further processing, PISCES map layers can be passed to arbitrary code called "callbacks" for further processing. At this phase, you can add attributes from the PISCES database or calculations, restructure the data, run geoprocessing operations, etc. PISCES ships with a number of useful default callbacks available for calculating diversity measures and doing some basic reforming of the output. See :ref:`map callbacks<map-callbacks>` for more on these.

Lastly, PISCES can export all of these resulting maps into most major formats ArcGIS can export in order to automate sharing the resulting data into other systems.

Maps are a very large subject in PISCES - this article is just an overview. For more information, See the topics below

Related Topics
--------------

.. toctree::
   :maxdepth: 2

   mapsets
   templates
   map_callbacks
   generate_maps
   ../common_tasks/writing_map_queries

Tutorials
---------

 * :download:`Creating Map Sets<../tutorials/Creating Maps.pdf>`