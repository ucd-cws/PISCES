.. _metadata:

Metadata 
=========

Species ranges are tracked through presence records for species in each watershed. Each presence record in PISCES includes foreign keys to the :term:`HUC12` mapping unit, :ref:`taxon<species-table>`, original dataset, and a :ref:`presence type<obs-types>` along with any other relevant metadata specific to that record. 


:ref:`Presence classifications<obs-types>` include whether the data is historic or current, native or translocated, and whether the data source is empirical, model-generated or expert knowledge. PISCES uses these attributes to layer and separate data upon output.


Records can be assigned to a :term:`collection`, such as :ref:`quality controlled datasets<qc-data>` which are a set of records that has been manually reviewed by species experts and is considered authoritative. Groups of :ref:`taxa<species-table>`, such as native species, or taxa of interest for specific analyses can be placed together in :term:`species groups`. Users can filter PISCES outputs to only include selected taxa and/or data types using metadata attributes, collections, and/or species groups.


:ref:`Built-in transaction system<transaction-logs>` track all changes to data, such as the import of new data or the modifications of existing data. Data changes made using the :ref:`built-in tools<tool-addmodify-data>` can be retroactively reverted to prior states if desired.

