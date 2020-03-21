.. _data-tables:

Data Tables
===========

.. _table-zones-aux:

Zones_Aux
---------

The Zones_Aux table stores additional data about the properties of each :term:`HUC12`. Additional columns can be added to the table as needed. The :ref:`Add HUC12 Attributes Tool<tool-addhuc12>` can be used to add new attributes or update existing fields if it is boolean. 

.. csv-table::
		:header: Field, Purpose
		:widths: 14, 75
		
		zone, :term:`HUC12` identification number
		usforest_id1, ID number of the primary national forest that intersects the :term:`HUC12`
		usforest_id2, ID of the secondary national forest that may additionally intersect the :term:`HUC12`
		rim_dam, :term:`HUC12` contains a rim dam  (large dams at the base of most river systems)
		beta_div_nat_his, beta diversity for historical native species - values automatically populated when All Diversity or Beta Diversity mapset is run.
		beta_div_nat_cur, beta diversity for current native species - values automatically populated when All Diversity or Beta Diversity mapset is run.
		beta_div_nn_hist, beta diversity for historical nonnative species - values automatically populated when All Diversity or Beta Diversity mapset is run.
		beta_div_nn_cur, beta diversity for current nonnative species - values automatically populated when All Diversity or Beta Diversity mapset is run. 
		sierranevadamodoc, :term:`HUC12` is in the Sierra Nevada or Modoc Ecoregions
		zoogeo2012_region, Zoogeographic Region of California (see Moyle 2002 pg. 4 for details)
		zoogeo2012_subregion, Zoogeographic subregion characterized by distinct fish fauna (see Moyle 2002 pg. 4 for details)
		huc_update_2013_created, :term:`HUC12s` created during 2013 conversion
		barrier_dams, :term:`HUC12` contains a major barrier dam to fish passage
		in_huc, :term:`HUC12s` that are totally or partially in California
		freshwater_region, Region for freshwater conservation Zonation analysis
		

.. _table-altcodes:

Alt_Codes 
---------
Alt_Codes are unique values for species names or abbreviations from external data sets 
that are cross referenced to PISCES internal :term:`species code`. The Alt_Codes table is the cross-walk between the Alt_Codes (from the input datasets) and the PISCES species codes. Alt_Codes for new datasets should be set prior to importing using the :ref:`Add Unique Field Values as Alt Codes Tool<tool-altcodes>`. Alt_Codes must be associated with only one species, unknown or unresolved taxa can be imported to temporary species :term:`bins`. Each Alt_Code set is associated with a corresponding :ref:`Input Filter<input-filters>`.


.. _table-transactions:

Transactions
------------
Table stores a record of all operations for the :ref:`Add or Modify Data Tool<tool-addmodify-data>`. 
This transaction history can be used to figure out the correct operation to 
revert (using the :ref:`Undo Transaction Tool<tool-undo-transaction>`) 
or to check if a operation ran successfully. 


.. _table-invalid-observations:

Invalid_Observations
--------------------

Table stores all invalid records that have been removed from the database. Records are moved here when selected to be **removed** with the :ref:`Add or Modify Data Tool<tool-addmodify-data>`. Each :ref:`transaction<table-transactions>` is recorded with an unique transaction_id.  Records can be restored to the main :ref:`Observations Table<observations>` using the :ref:`Undo Transaction Tool<tool-undo-transaction>`.
 
.. _table-layer-cache:

Layer_Cache Table
------------------

Table contains a list of all the features currently in the :term:`layer cache`. Used primarily from the 
:ref:`command line<inter-cmd>` to speed up processing when all data is generated but symbology needs to be updated or changed for all layers in maps (See main.py map --usecache for more information).


.. _table-query-bind:

Query_bind Table
-----------------
Table holds query_bind variables for species or species groups for different map sets. A query_bind is basically a placeholder for a species code. This allows maps to be run in batch for all members of group (see :ref:`Species_groups<species-group>` for more information). 


.. _table-connectivity:

Connectivity Table
-------------------
The connectivity table lists the closest upstream and downstream zones for each :term:`HUC12`. The connectivity data values are generated and updated with the connectivity map set as well as the beta diversity tools. The table can be used to query the SQL database for all of the HUC12s upstream or downstream of a location

.. _table-model-results:

Model Results
-------------
Results for preliminary predictive range modeling using PISCES. Predictive modeling can incorporate both current and future conditions to assign probability surfaces and thereby focus management decisions in areas where data are unavailable or uncertain. PISCES outputs combined with discriminant analysis (a classification technique used to maximize differences between groups and assign categories based on a given set of multivariates) can produce predictive fine-scale distribution maps. The following discriminant analyses illustrate the potential for predictive mapping and provide a framework for future conservation efforts.
17 environmental and 5 anthropogenic variables were used to model 4 fish species for the Central Valley and west slope of the Sierra Nevada. The species selected for this pilot covered a range of environmental tolerances and life history strategies. Environmental variables were modeled in conjunction with the historical expert opinion dataset from PISCES, and environmental plus anthropogenic variables were modeled with the current expert opinion dataset. Models were then validated with observed data to see how accurately they predicted occupancy in HUCs with observed data.

Please see http://pisces.ucdavis.edu/modeling for more information. 

.. _table-users:

Users
-----
Table contains the configured user profile IDs and user names. The user names are primarily used to limit the display of custom auxiliary maps sets (configured in the :ref:`Map_Users table<table-map-users>`). For more information on user accounts in PISCES see the :ref:`User Accounts Tutorial<tutorials>`.

.. _table-map-users:

Map_Users
---------
Stores which :ref:`Map Sets<mapsets>` are accessible to the different :ref:`users<table-users>` in the :ref:`Generate Map<tool-generate-map>` selection box. To learn how to give a user access to a map, see the :ref:`User Accounts Tutorial<tutorials>`.

.. _table-assemblage-groups:

Assemblage_Groups
-----------------
Additional species subgroups for freshwater conservation zonation analysis. Fish species are split into groups of anadromous species, species with a total range less than 25 HUC12s (highly endemic) or wide ranging species (not anadromous and not narrow_25). Benthic macroinvertebrates were broken into taxonomic groups of Arthropod, Mollusk or Crustacean. Amphibians were split according to dominant life-history requirements; lentic, lotic or both (lotic_lentic).


.. _table-cvas:
  
CVAs
----------
HUC12s identified as Conservation Value Areas (CVAs) from the California Freshwater Conservation Blueprint Project (*in prep*). Conservation Value Areas are the 10% of HUC12s within a freshwater region identified by Zonation as of high importance for at least one :ref:`Assemblage Group<table-assemblage-groups>`. Table includes the common name (cva_name) for the CVA as well as the freshwater region and the selected taxonomic group.

.. _table-status-scores:

Status Scores
-------------

moyle_1976
###########
Vulnerability status scores for native fish circa 1976. Scores are on a four point scale. For more information, see Inland Fish of California - 1st edition (Moyle 1976).

status_1989
############
Vulnerability status of native fish circa 1989. Scores are also on a four point scale. For more information, see Fish Species of Special Concern - 1st edition (Moyle et al. 1989).

status_1995
############
Status scores of fish in 1995. For more info, see Fish Species of Special Concern - 2nd edition (Moyle et al. 1995).

Status_2013 
#####################################

Threat and status scores for all native and introduced fish species in California. See `Moyle, Katz and Quinones (2010) <https://watershed.ucdavis.edu/pdf/Moyle%20CA%20fish%20status-WP.pdf>`_ for more information. Scores for each catagory are given on a 1 - 6 point scale. Cumulative metrics for baseline vulnerability (Vb), climate change vulnerability (Vc), and overall vulnerability (Vo) are ranked on a 1 - 4 point scale with low scores representing more vulnerable species. A score of zero represents extinct or extirpated species.

Status_2013_by_zoogoo
#######################

Same methods as Status_2013 but scores are separated by zoogeographic subprovince (see Moyle 2002 pg. 4 for boundary details) if applicable. 


.. _table-observers:

Observers
----------
Stores the list of organizations or individuals that contribute data. Each record that is imported should be associated with one of these observers. This is a required field for importing data or adding observation. The observers table is an element required for datasets that was designed to catalog the individuals and organizations who gathered the data.