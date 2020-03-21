
.. _alt-codes:

Taxa Identifiers
===================

Most datasets have their own way of indicating what species a particular record documents. Some use scientific names, others common names, and others use various shorthands developed by those in the field.

All taxa in PISCES have a unique :term:`species code` for identification in the database. The species code used in PISCES is derived from first letter of the family, genus and scientific name plus two digits (ie ZZZ01) for each taxa.  The species code is unique for each taxa in the database and all new data that is added to the database must be cross-referenced to the PISCES species code.

To import other datasets, PISCES needs to understand what species is specified by each of the taxa identifiers. This is handled via a lookup table called :ref:`Alt_Codes<table-altcodes>`.


Automatically adding identifiers
--------------------------------
The :ref:`PISCES toolbox<tool-altcodes>` contains a tool called :ref:`Add Unique Field Values as Alt Codes<tool-altcodes>` that can prepopulate the :ref:`Alt_Codes<table-altcodes>` and :ref:`Input_Filter<input-filters>` for a specific dataset, so long as that dataset has a column with the unique values. If the dataset already contains a column with the PISCES species FID codes, the tool will associate them with corresponding identifiers. Otherwise, the associations need to be manually established in the :ref:`Alt_Codes<table-altcodes>` table. Codes for data :term:`bins` can be used for unknown or unresolved taxonomy.
