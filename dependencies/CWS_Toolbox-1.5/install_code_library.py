from _winreg import *
import os
import sys
import subprocess
from distutils.sysconfig import get_python_lib
import platform

require_32bit = True
current_file = os.path.abspath(__file__)
current_directory = os.path.split(current_file)[0]  # get the location of the install script
architecture = platform.architecture()[0]  # just get 32/64

## Detect if it's being run by the 64 bit Python instead of the 32bit where we'll need it. Relaunch if it is
if require_32bit and architecture != "32bit":
	print "Relaunching 32bit version"
	new_path = sys.executable.replace("x64", "")
	base_python = os.path.split(new_path)[0]
	subprocess.call([new_path, current_file])  # re call the script, but with the 32 bit interpreter
	raw_input("launched version under 32 bit python. Closing original version. Hit any key to exit.")
	sys.exit()


curdir = os.getcwd()

print "Registering location in system registry at HKEY_CURRENT_USER\Software\CWS\code_library\location"
print "Registering location as %s" % current_directory
try:
	registry = ConnectRegistry("", HKEY_CURRENT_USER)
	Software = OpenKey(registry, "Software")
	CWS = CreateKey(Software, "CWS")
	code_library = CreateKey(CWS, "code_library")
	SetValue(code_library, "location", REG_SZ, current_directory)
	FlushKey(code_library)
	print "registered!\n"
except:
	print "FAILED to register"

# create the egg and link it to this location
subprocess.check_call([sys.executable, os.path.join(current_directory, "setup.py"), "develop"])
"""
try:
	locations = ("common", "cws_toolbox")
	print "Writing location to Python path"
	pth_dir = get_python_lib()
	pth_file = os.path.join(pth_dir, "code_library.pth")
	open_file = open(pth_file, 'w')
	for folder in locations:
		print "Writing %s" % os.path.join(current_directory, folder)
		open_file.write(os.path.join(current_directory, folder) + "\n")
	open_file.close()
	print "Location written\n"
except:
	print "Couldn't write .pth file to Python install - possibly a permissions issue. Some tools may fail, but the main PISCES software should work"
"""