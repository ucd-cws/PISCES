# Dependency Order
This lists the expected order of loading in PISCES submodules/packages in order to avoid circular imports.
Not all orderings are listed, but the following should be used as a rule to guide the rest.

1. log
2. local_vars
3. funcs
4. api
5. callbacks
6. mapping
7. everything else

Generally, anything that loads PISCES modules should load them in that order, but that is less important
than ensuring that changes don't cause any module to import anything further down the list from itself,

Log does not need to be first since it doesn't rely on anything else. It is in the process of being made
obsolete anyway.