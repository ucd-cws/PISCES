.. _users:

.. this document is superceded by Andy's clarify documentation

User Accounts in PISCES
=======================
PISCES has a simple concept of user accounts, primarily used to reduce clutter when using the software. As of version
2.0, a user account controls:

1. Which :ref:`Map Sets<mapsets>` are visible when using the :ref:`Generate Map<tool-generate-map>` tool
2. Which input filter is the default when using the :ref:`Add or Modify Data Tool<tool-addmodify-data>`

.. _users-change:

Setting/Changing your username
------------------------------
Changing your username can be done during the installation process when the options screen is shown, or by using the
:ref:`Change Configuration Options<tool-config>` tool.

.. _users-new:

Creating a new user
-------------------
PISCES users are stored in the :ref:`users<table-users>` table in the database, and are simply a record with the username
for the user. No other information is required. To add a new user, open up the database editor and open up the "users"
table and add a record. Put in the username and make sure to commit your changes.

.. TODO Make database editor a reference to a page on it.


.. _users-maps:

Giving a user access to a mapset
--------------------------------
As of version 2.0, this process is not streamlined. To give a user access to a Map Sets<mapsets>, you will need to know
the integer ID of that Map Set (findable by opening the table "defs_Query_Sets" in the database editor and looking at the
ID column for the Map Set of interest). You will also need to know the user's integer ID - findable by doing the same
process in the "users" table. Once you have both of these, open up the map_users table and add a record, filling in map_id
with the integer ID of the Map Set and user_id with the integer ID of the user. Click commit to save your changes, and
the map will now show up for that user when running the :ref:`Generate Map<tool-generate-map>` tool.
