from setuptools import setup

setup(name="PISCES",
	version="2.0.5",
	description="This setup file is only used for registering PISCES correctly in a new copy of Python. Other setup is" \
                "required",
	long_description="""Placeholder""",
	packages=['PISCES', 'PISCES.api_components', 'PISCES.callbacks', 'PISCES.input_filters', 'PISCES.plugins'],
	requires=["arcpy", "pyodbc", "sqlalchemy"],
	author="nickrsan",
	author_email="nrsantos@ucdavis.edu",
	url='https://bitbucket.org/nickrsan/PISCES',
	include_package_data=False,
)
