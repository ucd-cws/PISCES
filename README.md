# README #

PISCES is software and data describing the best-known ranges for California's 133 native fish and numerous non-native fish. The data are compiled from multiple sources and are expert verified. It is accessible directly via the PISCES software, downloadable as geographic data layers or images , or queryable from the PISCES database.

PISCES was developed with initial funding from the USDA Forest Service Region 5 and additional funding from California Department of Fish and Wildlife: Biogeographic Data Branch, in collaboration with numerous experts in fish biology and distribution in California.

### How do I get set up? ###
See [full documentation](http://pisces.ucdavis.edu/doc)

# Manual setup
If you need to perform a manual setup, you'll need the following:

## Install dependencies
PISCES requires:
* pyodbc
* SQLAlchemy >= 1.10
* sierra_code_library (provided in repository)
* six

## Set up registry


## Set up ArcGIS Python
Make a file named `PISCES.pth` in the ArcGIS Python installation under `C:\Python27\ArcGISXX.X\lib\site-packages`
and put the full path to the root folder of PISCES there

## Rehydrate the database
