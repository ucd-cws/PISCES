.. _extending-input-filters:

Extending PISCES Import Functionality
=====================================
PISCES native import functionality can be heavily extended via the :ref:`input_filter<input-filters>` class.

If you need custom behaviors to import an existing dataset into PISCES, you may need to add another Python *class* to the file input_filters.py. For best results your new class should be a subclass of one of the existing input filter classes in order - otherwise, it may not function correctly.

You can find the reference for the existing input filters in the :ref:`API code reference section<input-filters-code>` as a starting point for subclassing an input filter and customizing its behavior. The core choice to make when choosing one is whether or not it's a single species or multi-species dataset. If it is a multi-sepecies dataset, you will most likely need to use Gen_Table_IF or something subclassed from it in order to handle the table interpretation.

When creating a new input filter, we create the code class as a subclass of the other code, then override critical parts of the existing code in order to add new functionality. Each input filter has different points to override, with Gen_Table_IF being the most flexible and easiest to customize.
s




	






