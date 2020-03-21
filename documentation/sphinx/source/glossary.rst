Glossary
=========


.. glossary::
	:sorted:

	HUC12
	HUC12s
		United States Geological Survey Hydrologic Unit Code 12 - subwatersheds. See http://water.usgs.gov/GIS/huc.html for more information. 
	HUC8
		United States Geological Survey Hydrologic Unit Code 8 - subbasins. See http://water.usgs.gov/GIS/huc.html for more information. 
	PISCES
		a Programmable Geographic Information System for Cataloging and Encoding Species observations; the twelfth sign of the zodiac.
	MXD
	MXDS
		an ArcGIS Map Document.
	COLLECTION
		A subset of the database records that have similar properties (such as data that has been quality controlled). See :ref:`Collections<collections>` for more info.
	INPUT FILTER
		Combination of translation values for taxa IDs (:term:`Alt Codes`) and the code class that handles the import. 
	ALT CODES
		Names or abbreviations for species that are cross-walked and referenced to PISCES's species codes. Codes are associated with :term:`input filter` for different datasets due to non-standard species names or codes. 
	Data Driven Pages
		An index layer is used to produce multiple output pages using a single layout. Each page shows the data at a different extent. The extents are defined by the features in the index layers.
	LAYER CACHE
		Output geodatabase for layer files generated during mapping (*PISCES/data/layer_cache.gdb*).
	TOOLBOX
		Collection of customized ArcGIS scripts and tools for PISCES (*PISCES/tbx/pisces/tbx*).
	SPECIES CODE
		Unique identification code for each species in database. Derived from first letter of family, first letter of genus and first letter of scientific name plus two digits (ie: ZZZ01)	
	OBSERVATION SET
		Groups all data from a single data source. See Observation_Sets in PISCES.mdb.
	BINS
		Temporary storage for species of unknown taxonomy.
	SPECIES GROUPS
		a collection of :term:`species code` for list of species that share a common characteristic