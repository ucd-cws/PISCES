Presence Types
=================================

.. _obs-types:


Observation Types
---------------------------------
**Defined in**: :ref:`defs_Observation_Types<defs-observation-types>`


PISCES has 10 different observation types. Observation types document the source (empirical record, expert knowledge, modeled, etc.) and 
classification (native, historic, translocated, etc.) for each record. Storing data with the observation presence types provides extra 
information about the quality and meaning of the data. Different observation types are output from PISCES as separate map layers by 
default, though new maps sets can be configured to collapse groups if you wish. 

1. **Observed** - backed up by data, this is verifiable.
2. **Historical Range Expert Opinion** - from expert opinion 
3. **Extant Range Expert Opinion** - expert opinion says it is here
4. **Extant Range Modeled** -  modeled current distribution
5. **Extirpated** - expert opinion for extinct/extirpated species
6. **Translocated Expert Opinion** - expert opinion for introduction/translocation 
7. **Translocated Observed** - data for introduction/translocation 
8. **Historical Range Modeled** - historical modeled distribution
9. **Reintroduced** - documented reintroduction into area previously extirpated
10. **Historical Range Observed** - backed up by data including an observation date


.. Note::
	Historical records for California fish were any records prior to ~1970. Records were classified using the best available 
	expert knowledge for each species (Moyle 2002).
	


Observation Presence Groups:
----------------------------
		
.. list-table::
   :widths: 5 5 20
   :header-rows: 1

   * - Group
     - Presence_Types
     - Description
   * - Current
     - 1, 3, 6, 7, 9
     - Observations and expert opinion for current species distribution
   * - Historical
     - 2, 5, 10
     - Observations and expert opinion for historical species distribution
   * - Current - no trans
     - 1, 3, 9
     - Current distribution with no translocations
   * - Modeled
     - 4, 8
     - Modeled distributions