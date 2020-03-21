from __future__ import print_function

from _winreg import *
import os
import shutil
import sys
from distutils.sysconfig import get_python_lib
import urllib
import zipfile
import subprocess
import platform
import datetime


# TODO: Check if running as admin and relaunch if not
# TODO: Refactor later to add error checking to the batch files


try:
	import arcpy
except ImportError:
	print("Cannot install without ArcGIS 10.2 or above. Please install ArcGIS before installing PISCES. If you just want the database, you do not need to run this install script.")
	raw_input("Press any key to exit...")
	sys.exit()

try:
	stage = sys.argv[1]
	if stage == "" or stage is None:
		stage = 1
except IndexError:
	stage = 1



current_file = os.path.abspath(__file__)
current_directory = os.path.split(current_file)[0]  # get the location of the install script
log_file = os.path.join(current_directory, "pisces_install.log")
log_handle = open(log_file, 'a')
dependencies_folder = os.path.join(current_directory, "dependencies")
install_success = []  # we'll throw True/False in here
extension_changer = r"dependencies\change_python_to_version.bat"
path_mods = r"dependencies\mod_path.bat"
base_python = os.path.split(sys.executable)[0]
arcgis_version = arcpy.GetInstallInfo()['Version'][:4]  # get only the first four characters - we don't care about minor updates
require_32bit = True
architecture = platform.architecture()[0]  # just get 32/64
minimum_code_lib_version = "1.5"  # minimum version of the CWS code library to not install a new version on top
sevenzip = os.path.join(current_directory, "utils", "7za.exe")
mingw = os.path.join(current_directory, "dependencies", "MinGW-4.8.1-4.7z")
setuptools_install = os.path.join(dependencies_folder, "setuptools-6.1", "setup.py")
batch_file_one = os.path.join(dependencies_folder, "run_installs.bat")
batch_file_two = os.path.join(dependencies_folder, "run_installs_part2.bat")
code_lib_installer = os.path.join(dependencies_folder, "CWS_Toolbox-1.5", "install_code_library.py")

pyodbc_installer = {"10.0": "pyodbc-3.0.7.win32-py2.6_arcgis10.0.exe",
					"10.1": "pyodbc-3.0.7.win32-py2.7_arcgis10.1and10.2.exe",
					"10.2": "pyodbc-3.0.7.win32-py2.7_arcgis10.1and10.2.exe",  # 10.2 uses Python2.7 as well
					}  # dictionary keyed on versions of arcgis

PIL_installer = {"10.0": "PIL-1.1.7.win32-py2.6_arcgis10.0.exe",
				"10.1": "PIL-1.1.7.win32-py2.7_arcgis10.1and10.2.exe",
				"10.2": "PIL-1.1.7.win32-py2.7_arcgis10.1and10.2.exe",  # 10.2 uses Python2.7 as well
				}

tortoise_hg_installer = {"x86": "tortoisehg-3.1.2-x86.msi",
						"x64": "tortoisehg-3.1.2-x64.msi"
						}


def log(log_string):
	print(log_string)
	log_handle.write("%s %s\n" % (datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p"), log_string))

def set_environ():
	os.environ["PATH"] += ";%s;%s\Scripts;%s\Lib;%s\bin;C:\MinGW;C:\MinGW\bin" % (base_python, base_python, base_python, base_python)


def check_bit_depth():

	if require_32bit and architecture != "32bit":
		log("Relaunching 32bit version")
		new_path = sys.executable.replace("x64", "")
		base_python = os.path.split(new_path)[0]
		subprocess.call([new_path, current_file])  # re call the script, but with the 32 bit interpreter
		change_version = raw_input("If you ran this installer as an administrator, we can change the python file extension to use the correct version for PISCES (32 bit version) for you. If you did not run the installer as an administrator, after installation, run the following command on the command line (in the PISCES directory) \"%s %s\". Would you like to make that change (y/n)" % (extension_changer, base_python))
		if change_version.lower() == "y" or change_version.lower() == "yes":
			subprocess.call([os.path.join(current_directory, extension_changer), base_python])
		raw_input("launched version under 32 bit python. Closing original version. Hit any key to exit.")
		sys.exit()


def change_python_to_version(version=base_python):
	try:
		subprocess.call([os.path.join(current_directory, extension_changer), version])
	except:
		log("Couldn't change python to 32 bit version")
		return False

	return True


def add_python_to_syspath(change_script=path_mods, python_version=base_python):

	# check if it's
	syspath = os.environ['PATH'].lower()
	if base_python in syspath:
		return

	# TODO: Needs to check if it's already on the system path so that it doesn't just keep adding to it and making it longer if they rerun install
	# TODO: Output isn't checked to make sure installation worked
	try:
		log("Adding python to system path")
		subprocess.call([os.path.join(current_directory, change_script), python_version], shell=True)
	except:
		log("Couldn't add python to the system path")
		return False
	return True


def fix_distutils(python_folder):
	"""
		Fixes distutils a la http://stackoverflow.com/questions/6034390/compiling-with-cython-and-mingw-produces-gcc-error-unrecognized-command-line-o/6035864#6035864
	"""
	distutils_file_old = os.path.join(python_folder, "Lib", "distutils", "cygwinccompiler_old.py")
	distutils_file = os.path.join(python_folder, "Lib", "distutils", "cygwinccompiler.py")

	# move distutils file to old location
	shutil.move(distutils_file, distutils_file_old)

	with open(distutils_file_old) as dist_file_old:
		with open(distutils_file, 'wb') as dist_file:
			for line in dist_file_old:
				dist_file.write(line.replace(" -mno-cygwin", ""))

	## phase 2 - add file configuring distutils
	distconfig_file = os.path.join(python_folder, "Lib", "distutils", "distutils.cfg")
	if os.path.exists(distconfig_file):
		log("WARNING: distutils already has a configuration file - can't write out changes (this could also happen if you're just reinstalling, in which case you can ignore this message). Parts of install may fail. If you don't understand this message, contact the PISCES developers")
		return False

	with open(distconfig_file, 'wb') as dist_config:
		dist_config.write("[build]\n\ncompiler=mingw32")

	return True


def install_mingw32(mingw_compressed=mingw, szip=sevenzip):

	log("Installing MingW32 compiler")
	subprocess.call([szip, "x", mingw_compressed, "-oC:\\"])


def install_setuptools(directory=current_directory):

	log("installing setuptools")

	#TODO: check the output to make sure they install
	subprocess.call([os.path.join(base_python, "python.exe"), os.path.join(directory, "dependencies", "setuptools-6.1", "setup.py"), "install"], shell=True)

	return True


def install_pip():

	log("Installing Pip")
	#TODO: check the output to make sure they install
	subprocess.call([os.path.join(base_python, "Scripts", "easy_install.exe"), "pip"], shell=True)
	return True


def set_dsn(curdir):
	try:
	
		registry = ConnectRegistry("", HKEY_CURRENT_USER)
		Software = OpenKey(registry, "Software")
		
		try:
			ODBC = OpenKey(Software, "ODBC")
		except WindowsError:
			ODBC = CreateKey(Software, "ODBC")
		
		try:
			ODBC_INI = OpenKey(ODBC, "ODBC.INI")
		except WindowsError:
			ODBC_INI = CreateKey(ODBC, "ODBC.INI")
			
		try:
			ODBC_Data_Sources = OpenKey(ODBC_INI, "ODBC Data Sources")
		except WindowsError:
			ODBC_Data_Sources = CreateKey(ODBC_INI, "ODBC Data Sources")

		log("Writing DSN")
		#load template dsn

		# TODO - we'll likely wnat to uncomment this - I was running into a permissions issue, and wanted to get some more tests done first
		#PISCES_Data_Source = SetValueEx(ODBC_Data_Sources, "PISCES", 0, REG_SZ, "SQLite3 ODBC Driver")
		#FlushKey(PISCES_Data_Source)

		PISCES = CreateKey(ODBC_INI, "PISCES")

		db_path = os.path.join("C:\PISCES", "data", "pisces.sqlite")
		log("Database path: %s" % db_path)
		
		with open(os.path.join(curdir, "dependencies", "pisces_template.reg_temp")) as dsn_file:
			for line in dsn_file:
				items = line.split("=")
				if items[0] != "Database":
					SetValueEx(PISCES, items[0], 0, REG_SZ, items[1])
				else:
					SetValueEx(PISCES, items[0], 0, REG_SZ, db_path)
		
		FlushKey(PISCES)

		# TODO: This code should be modified to move any existing links if it already exists. As of now, it just fails in text, but succeeds in the call
		log("Creating Alias C:\PISCES for current installation")
		if curdir != "C:\PISCES":  # if we're already in that folder, no need to create an alias
			subprocess.call([os.path.join(curdir, "dependencies", "junction.exe"), r"C:\PISCES", curdir], shell=True)

	except:
		log("Couldn't create DSN - accessing tables from within Microsoft Access will be broken")
		return False
	return True


def add_to_windows_registry(curdir):
	log("Registering location in system registry at HKEY_CURRENT_USER\Software\CWS\PISCES\location")
	log("Registering location as %s" % curdir)
	try:
		registry = ConnectRegistry("", HKEY_LOCAL_MACHINE)
		Software = OpenKey(registry, "SOFTWARE")
		#wow6432node = OpenKey(Software, "Wow6432Node")
		CWS = CreateKey(Software, "CWS")
		PISCES = CreateKey(CWS, "PISCES")
		SetValue(PISCES, "location", REG_SZ, curdir)
		FlushKey(PISCES)
		log("registered!\n")
	except:
		log("FAILED to register. PISCES is NOT installed")
		return False
	return True


def add_to_pythonpath(curdir):
	try:
		log("Writing location to Python path")
		pth_dir = get_python_lib()
		pth_file = os.path.join(pth_dir, "pisces.pth")
		open_file = open(pth_file, 'w')
		open_file.write(os.path.join(curdir, "scripts"))
		open_file.close()
		log("Location written\n")
	except:
		log("Couldn't write .pth file to Python install - PISCES is NOT installed")
		return False

	return True


def install_cws_code_library(py, installer, to_folder):  # TODO: This should be more sophisticated - IE, it should detect the code_library, if installed, and determine if it should upgrade it. We should migrate code_library to full python installation, so we can use the built in handling for it

	try:
		import code_library
		if hasattr(code_library, "__version__") and (code_library.__version__ > minimum_code_lib_version or code_library.__version__ == minimum_code_lib_version):
			log("Skipping code library - already installed")
			return True
	except ImportError:
		pass  # will install next

	try:
		subprocess.call([os.path.join(py, "python.exe"), installer])
		sys.path.append(os.path.join(dependencies_folder, "CWS_Toolbox-1.5", "common"))  # Hot patch these in there - we'll need them later
		sys.path.append(os.path.join(dependencies_folder, "CWS_Toolbox-1.5", "code_library"))
	except:
		log("Couldn't install code library!")
		return False

	return True

	log("Installing Code Library - if you have a copy installed, it will be switched to this version. Please make sure to remove and re-add any toolboxes as they will be WRONG now")  # TODO: Remove old version if exists!
	try:
		log("Downloading")
		code_lib, file_info = urllib.urlretrieve("http://bitbucket.org/nickrsan/sierra-code-library/get/release.zip")
		# Assume it went ok. # TODO: Don't assume! Just having trouble figuring out what part of file_info tells us if it was successful

		log("Extracting")
		code_lib_zip = zipfile.ZipFile(code_lib)
		code_lib_zip.extractall(to_folder)
		del code_lib_zip

		log("Installing")
		install_file = find("install.py", to_folder)  # find the install file - since we don't know what the folder name is - should be fast since it's not deep
		subprocess.call([sys.executable, install_file])

	except:
		log("Couldn't install code library. Please do so manually using the copy in the dependencies folder. Also, check that Python is on your system path")
		return False

	return True


def install_pyodbc(cur_dir, executable_name):

	log("Installing pyodbc - check for any background installer windows")
	try:
		import pyodbc
	except ImportError:
		try:
			subprocess.call(os.path.join(cur_dir, "dependencies", executable_name))
		except:
			return False

	return True


def install_PIL(cur_dir, executable_name):
	"""
		Not a dependency of PISCES, but a dependency of the code library. Set it up here for now
	:param cur_dir:
	:param executable_name:
	:return:
	"""

	log("Installing PIL - check for any background installer windows")
	try:
		import PIL
	except ImportError:
		try:
			subprocess.call(os.path.join(cur_dir, "dependencies", executable_name))
		except:
			return False

	return True

	# TODO: This function repeats the previous one. We should probably genericize it.

def install_generic_dependency(cur_dir, executable_name, name):
	"""
		Initializes generic dependency installation (like executables and msis that aren't python packages)
	:param cur_dir: the install directory
	:param executable_name: the name of the executable in the dependencies folder
	"""
	
	log("Installing {}".format(name))
	try:
		subprocess.call(os.path.join(cur_dir, "dependencies", executable_name))
	except:
		return False
		
	return True

def initialize_pisces(executable, curdir):
	"""
		Tried to do it in place, but importing only "funcs" using imp triggered a number of other import errors. Nice to avoid
	:param executable:
	:param curdir:
	:return:
	"""
	pisces_main = os.path.join(curdir, "scripts", "PISCES", "main.py")

	try:
		subprocess.call([executable, pisces_main, "clearcaches"])
	except:
		log("Couldn't initialize PISCES - please create a geodatabase called 'layer_cache.gdb' in the data folder")
		os.chdir(curdir)
		return False

	os.chdir(curdir)
	return True


def find(name, path):
	"""
		Utility function from http://stackoverflow.com/questions/1724693/find-a-file-in-python
	:param name:
	:param path:
	:return:
	"""
	for root, dirs, files in os.walk(path):
		if name in files:
			return os.path.join(root, name)

def next_stage(stage):

	nextstage = stage + 1
	log("launched stage {0:s} of installation".format(str(nextstage)))
	subprocess.call([os.path.join(base_python, "python.exe"), current_file, str(nextstage)], shell=True)  # call the script again, but at next stage
	check_success()
	sys.exit()  # we do this because we need to reload the system path, etc now that we've installed some things


def install_tortoisehg(installer, installer_folder):

	# TODO: Should test this installer on a 32 bit machine
	try:
		subprocess.call("hg")
	except WindowsError:  # WindowsError will indicate that it's not available
		log("Installing TortoiseHg")
		if platform.architecture() == "AMD64":  # make sure we install the version appropriate for the machine
			bit_installer = installer["x64"]
		else:
			bit_installer = installer["x86"]
		subprocess.call([os.path.join(installer_folder, bit_installer)])  # run the installer


def check_success():

	if False in install_success:
		raw_input("Install had errors. Please see above. Press Enter to close.")
	else:
		raw_input("Finished. Press Enter to close...")


def install_sqlalchemy(install_location):
	return  # putting this here to indicate that this code isn't running right now - handled in batch file
	try:
		import sqlalchemy
		if sqlalchemy.__version__ < "0.9.8":
			log("ERROR: SQLAlchemy already installed, but at version lower than required (0.9.8). Remove the old version of SQLAlchemy and run the installer again")
			return False
	except:
		# subprocess.call([os.path.join(base_python, "python.exe"), install_location, "install"], shell=True)
		# TODO: Switch back to the above - not sure why I get failures using the local copies this way - install doesn't fail when manually installing same folder from command line
		subprocess.call([os.path.join(base_python, "Scripts", "pip.exe"), "install", "sqlalchemy"], shell=True)

	return True

def install_logbook(install_location):
	return  # putting this here to indicate that this code isn't running right now - handled in batch file
	try:
		import logbook
		if logbook.__version__ < "0.7.0":
			log("ERROR: Logbook module already installed, but at version lower than required (0.7.0). Remove the old version of Logbook and run the installer again")
			return False
	except:
		#subprocess.call([os.path.join(base_python, "python.exe"), install_location, "install"], shell=True)
		# TODO: Switch back to the above - not sure why I get failures using the local copies this way - install doesn't fail when manually installing same folder from command line
		subprocess.call([os.path.join(base_python, "Scripts", "pip.exe"), "install", "logbook"], shell=True)

	return True


def batch_file_phase_one(batch_file, py, sevenz, ming, setuptools):

	subprocess.call([batch_file, py, sevenz, ming, setuptools])
	return True


def batch_file_phase_two(batch_file, py, sqlalchemy, logbook):

	subprocess.call([batch_file, py, sqlalchemy, logbook])
	return True


if __name__ == "__main__":

	log("PISCES Install operation begun at %s" % (datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")))
	log("You must be connected to the Internet for this installation to succeed")

	set_environ()
	check_bit_depth()
#	if stage == 1:
#		install_success.append(add_python_to_syspath(python_version=base_python))
#		install_success.append(install_setuptools(current_directory))
#
#		next_stage(1)

#	#if stage == 2:
#	install_success.append(install_mingw32(mingw, sevenzip))
#	install_success.append(install_pip())
#	#	next_stage(2)

	# TODO: Split batch file so that the system path batch file is separate because we want to do some error checking on it (see if we need to at all)
	install_success.append(batch_file_phase_one(batch_file_one, base_python, sevenzip, mingw, setuptools_install))
	install_success.append(fix_distutils(base_python))
	install_success.append(change_python_to_version(base_python))
	#TODO: These installs use pip. It'd be good to refactor it later to use the local copies, but those don't seem to work when installed from the batch file
	install_success.append(batch_file_phase_two(batch_file_two, base_python, os.path.join(dependencies_folder, 'SQLAlchemy-0.9.8', "setup.py"), os.path.join(dependencies_folder, 'Logbook-0.7.0', "setup.py")))

	install_success.append(add_to_windows_registry(current_directory))
	install_success.append(add_to_pythonpath(current_directory))
#	install_success.append(install_sqlalchemy(os.path.join(dependencies_folder, 'SQLAlchemy-0.9.8', "setup.py")))
#	install_success.append(install_logbook(os.path.join(dependencies_folder, 'Logbook-0.7.0', "setup.py")))
	install_success.append(install_pyodbc(current_directory, pyodbc_installer[arcgis_version]))
	install_success.append(install_generic_dependency(current_directory, "sqliteodbc.exe", "SQLite Database Driver"))
	install_success.append(install_generic_dependency(current_directory, "sqliteodbc_w64.exe", "SQLite 64 bit Database Driver"))
	install_success.append(set_dsn(current_directory))
	install_success.append(install_tortoisehg(tortoise_hg_installer, current_directory))
	install_success.append(install_PIL(current_directory, PIL_installer[arcgis_version]))
	install_success.append(install_cws_code_library(base_python, installer=code_lib_installer, to_folder=os.path.join(current_directory, "dependencies")))  ## This comes after the other installers because it will faile to import otherwise
	install_success.append(initialize_pisces(sys.executable, current_directory))
	# TODO: make it run a selected subset of the unit tests

	check_success()