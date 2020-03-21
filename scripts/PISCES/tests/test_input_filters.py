# -*- coding: utf-8 -*-
__author__ = 'nickrsan'

import unittest
import re

from PISCES.input_filters import common

class TestInputFilterCommon(unittest.TestCase):
	def test_DDM_to_DD_conversion(self):
		pattern = re.compile('(?P<degrees>\d+).\s+(?P<minutes>\d+)\.(?P<dec_seconds>\d+)')

		self.assertEqual(common.convert_DDM_to_DD(pattern, u"34° 43.512'"), 34.7252)
		self.assertEqual(common.convert_DDM_to_DD(pattern, u"34° 43.764'"), 34.7294)
		self.assertEqual(common.convert_DDM_to_DD(pattern, u"34° 42.570'"), 34.7095)
		self.assertAlmostEqual(common.convert_DDM_to_DD(pattern, u"34° 42.979'"), 34.716316666)

