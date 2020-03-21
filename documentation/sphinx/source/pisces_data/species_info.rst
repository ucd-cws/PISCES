Species Information
====================

**Key Concepts:**

	* Each species has an unique :term:`species code`
	* Unknown taxonomy for observations can be temporary stored in :term:`bins`
	* Additional information can be joined to each species using the :term:`species code` and is stored in :ref:`Species_Aux<species-aux>`
	* :term:`Species groups` are lists of individual species that belong to a certain category
	* Species can belong to multiple :term:`species groups`

.. note::
	The term *species* in PISCES can refer to other taxonomic resolutions such as families, subspecies, ESUs and DPSs.
	
.. _species-table:

Species Table
---------------
The **Species** table stores primary information about each species. Additional species can be added to the table in needed but each new species must have an unique FID that has not been used previously. The :term:`species code` is typically derived from first letter of family, first letter of genus and first letter of scientific name plus two digits. Unknown or unresolved taxonomy for records can be temporary placed in :term:`bins`. Data in :term:`bins` by default is not included in data collections, queries or exports. 

.. csv-table:: 
	:header: Field Name, Description
	:widths: 10, 25
	
	OBJECTID, Primary Key
	FID, Unique :term:`species code`
	Family, Taxonomic Family
	Genus, Taxonomic Genus
	Species, Taxonomic Species Name
	Subspecies, Taxonomic subspecies name (if applicable)
	Scientific_Name, Genus + Species + Subspecies (if applicable)
	Taxonomic_unit, Resolution of species code 
	Common_Name, Recognized common name for species
	Notes, Any notes about species
	Native, Allows for sorting of native species
	Image_Location, File path to image for use in reports
	Temporary, Flags records that are only for catching data that needs taxa to be determined. 
	
	


.. _species-aux:
	 
Species_Aux
------------
The **Species_Aux** table stores auxiliary information about each species. Species are identified by their :term:`species code` (FID). The information in the table is customizable and can be expanded as needed. The user can additional columns with new information about the life history, conservation status, habitat requirements, etc. for each species. Information in table can be used to generate text for automated reports on each species or joined to the observation records to create custom queries. 

.. note:: 

	Data in **Species_Aux** is currently derived from Moyle, Peter B., Jacob VE Katz, and Rebecca M. Quiñones. "Rapid decline of California’s native inland fishes: a status assessment." Biological Conservation 144.10 (2011): 2414-2423.


.. _species-group:
	
Species Groups
---------------

Species groups are simply lists of species codes the user wants to group together. Groups are lists 
of species that can be used for creating and classifying assemblages. Often, species groups are 
created to group species that all share a common characteristic (such as flow sensitive species 
or anadromous fish). Groupings are a useful way to organize species into many different categories. 
Species can belong to many different groups. Creating a new assemblage group requires a new 
entry in the :ref:`defs_Species_Groups table<def-species-groups>` and then appending the desired species codes to 
the :ref:`Species_Groups table<species-group>`. Species groups are a convenient way to subset records or map output 
for species of interest. Several of the map sets can take a species group as a parameter to generate 
only maps or queries using the species that belong to the selected group. 
















