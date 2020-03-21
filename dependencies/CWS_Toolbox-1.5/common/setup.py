from setuptools import setup

setup(name="code_library",
	version="1.5.2",
	description="The UCD CWS Code Library and ArcGIS toolbox",
	packages=['code_library',
	'code_library.common',
	'code_library.common.geospatial',
	'code_library.common.image',
	],
	author="Nick Santos, with contributions from other staff",
	author_email="nrsantos@ucdavis.edu",
	url = 'http://bitbucket.org/nickrsan/sierra-code-library',

)