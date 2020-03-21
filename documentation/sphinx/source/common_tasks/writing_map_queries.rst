Writing Map Queries for PISCES
==============================
To get the most out of PISCES, or to begin extending PISCES for other purposes, an understanding of writing mapping queries is essential. Map queries are used when creating new permanent maps, or when trying to visualize PISCES data using the :ref:`Generate Layer from Query tool<tool-generate-layer>`.

An advanced PISCES user who wants to write Map Queries should have a basic understanding of SQL and be able to write a join clause. SQL is covered well on the Internet, and will not be covered here. This article instead covers the Map Query-specific ways to write SQL

General form
------------
A general PISCES map query takes a form like *select zone_id from Observations*. PISCES will take the results of that query - HUC 12 IDs - and find the corresponding features and use them for mapping. If we wanted PISCES to map HUC 12s in a specific HUC 8 instead, we could use the query *select HUC_12 as zone_id from HUC12FullState where HUC_8 = "18050804"* (for example).

The important part of these queries to note is that, whether or not you're selecting from a table that has a zone_id attribute, the result of your query must include a list of HUC 12s, and the field that contains those values must be cast as the name Zone_ID using the *as* operator. PISCES looks for the field Zone_ID in order to generate layers.

Reusable queries
----------------
In the case of species range maps, PISCES uses a single query for each layer, and this query is reusable across all taxa. We do this with *query parameters*, which are a standard SQL feature that we use for this purpose.

A query parameter uses a placeholder for a variable that will change for each map output (like species) to allow us to reuse a query, and then we can provide the value of the placeholder when the query is executed. The placeholder is just some symbol that is unknown to the database engine, but we commonly use a question mark (?).

To write a query that allows the Map Set to take parameters, just include the ? in the location of the parameter (such as *select distinct zone_id from Observations where Species_ID = ? And (Presence_Type in (1,9))* ). This feature doesn't work for the :ref:`Generate Layer from Query tool<tool-generate-layer>`, but does work for the :ref:`Generate Maps tool<tool-gen-map>`.

Once you have a query parameter, you need to specify what PISCES is supposed to allow to be filled into that parameter (which makes the Generate Maps tool give you those items as options too). When creating a map set with a parameter query, add a value to the Iterator field in the :ref:`Map Set definition table<mapsets>`. This value is of the form *tablename:fieldname* and allows for any value in that table's field to be provided as a parameter. For example, the *Iterator* for the Main Range Maps Map Set is *Species:FID* which indicates that all unique values in the *FID* column in the *Species* table should be allowed as parameters for queries in that map.

A Map Set can only have a single Iterator, but each layer can use the resulting values independently of the other layers.

Finally, the placeholder bind value can only be used once in a single query, or else map generation will fail. If you need to use it more than once, use the *{bind}* placeholder instead of the ? placeholder.

Queries support one additional replacement variable: *{hq_collections}*. This variable will always reference the current software-defined set of quality controlled datasets. That way, when it changes, it only needs to be configured in the software and queries don't need to be rewritten.

Additional Examples
-------------------
You can find numerous examples of Map Queries for inspiration the Map_Queries table in the PISCES database, but here are a few more.

Example: **Select all quality controlled historical records for a species along with necessary fields for metadata generation.**
Query: *select distinct observations.zone_id, Observations.Set_ID, Observations.IF_Method, Observations.OBJECTID from Observations, Observation_Collections where Species_ID = ? And Presence_Type in (2,5) and Observations.OBJECTID = Observation_Collections.Observation_ID and Observation_Collections.Collection_ID in (5, 15)*

Example: **Select all records (including non-quality controlled) with a direct observation (field data)**
Query: *select distinct zone_id from Observations where Species_ID = ? And (Presence_Type in (1,9))*
