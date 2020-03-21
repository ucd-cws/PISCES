from __future__ import print_function

from _winreg import *
import os

def add_to_windows_registry(curdir):
	print("Registering location in system registry at HKEY_CURRENT_USER\Software\CWS\PISCES\location")
	print("Registering location as %s" % curdir)
	try:
		registry = ConnectRegistry("", HKEY_CURRENT_USER)
		Software = OpenKey(registry, "SOFTWARE")
		#wow6432node = OpenKey(Software, "Wow6432Node")
		CWS = CreateKey(Software, "CWS")
		PISCES = CreateKey(CWS, "PISCES")
		SetValue(PISCES, "location", REG_SZ, curdir)
		FlushKey(PISCES)
		print("registered!\n")
	except:
		raise
		print("FAILED to register. PISCES is NOT installed")
		return False
	return True
	
add_to_windows_registry(os.path.split(os.path.abspath(__file__))[0])