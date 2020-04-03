# README #

PISCES is software and data describing the best-known ranges for California's 133 native fish and numerous non-native fish. The data are compiled from multiple sources and are expert verified. It is accessible directly via the PISCES software, downloadable as geographic data layers or images , or queryable from the PISCES database.

PISCES was developed with initial funding from the USDA Forest Service Region 5 and additional funding from California Department of Fish and Wildlife: Biogeographic Data Branch, in collaboration with numerous experts in fish biology and distribution in California.

### How do I get set up? ###
See [full documentation](http://pisces.ucdavis.edu/doc)

# Manual setup
If you need to perform a manual setup, you'll need the following:

## Install dependencies
PISCES runs on Python 2 or Python 3 (though some functionality is currently missing in Python 3. It cannot generate
maps or set metadata on exports in Python 3 yet).

It requires:
* pyodbc
* SQLAlchemy >= 1.10
* six

* arcpy (for many tools, mapping, and import. It will import fine in other Python installs and allow access to the `api`
    portion of the package when you don't have ArcGIS)
    
The dependencies should be installed for you automatically in the next step, but they are listed here in case you prefer
a manual installation.

## Set up the package in Python.

PISCES needs to run out of the folder you extract it to, so after cloning the repository, put it in a location
where it will live while you use it. If you move it, you will need to repeat setup steps. 

Activate whichever Python environment you plan to use for PISCES in a command prompt, then navigate to the folder
you stored the PISCES repository in, then to the `scripts` subfolder and run `python setup.py develop` in the same
command prompt. Activating an appropriate Python environment is a nontrivial operation for new Python users, but is
also beyond the scope of this readme right now (sorry!). Reach out to Nick if you need help with that.

## Set up registry
If you're on Windows AND using PISCES with ArcGIS, you need to set up the registry as well. The way ArcGIS loads PISCES,
it can't find its data files on its own, so we need to tell PISCES where everything is with a registry entry. You need
to add a registry key to `HKEY_CURRENT_USER\Software\CWS\PISCES\location` with the value being the full path
to the PISCES folder. We'll update the scripts to insert this automatically and include them here soon. Again, if you're
not running on Windows, or you aren't using ArcGIS' copy of Python, you don't need to do this step, but you'll be limited
to the API functions as opposed to the full functionality of PISCES.

## Obtain a copy of the database

## Update your user configuration
