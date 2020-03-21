__author__ = 'dsx'


# shamelessly taken from the Read The Docs code when trying to autocompile sphinx

class Mock(object):
	def __init__(self, *args, **kwargs):
		pass

	def __call__(self, *args, **kwargs):
		return Mock()

	@classmethod
	def __getattr__(cls, name):
		if name in ('__file__', '__path__'):
			return '/dev/null'
		elif name[0] == name[0].upper():
			mockType = type(name, (), {})
			mockType.__module__ = __name__
			return mockType
		else:
			return Mock()