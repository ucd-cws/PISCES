import sys
import os
import subprocess  # for when we zip up the upload

import paramiko

import local_vars
import log


def upload_dir(ssh_client, sftp_client, directory, remote_dir):
	'''zips up a folder, uploads it using the sftp_client, then unzips it using the ssh_client.
		It's a bit of a hack to get around the annoyance of a recursive directory upload with paramiko
	'''
	# ## Definitions
	temp_dir = local_vars.temp
	temp_file = "pisces_upload.zip"
	temp_path = os.path.join(temp_dir, temp_file)
	folder_name = os.path.split(directory)[1]  # get the dir-name - it'll be in the zip
	remote_path = "~/pisces_upload/temp/{0:s}".format(folder_name)

	unzip_command = "unzip ~/{0:s} -d ~/pisces_upload/temp/".format(temp_file)

	### Zip it up

	log.write("Zipping Data for upload...", 1)

	if os.path.exists(temp_path):
		os.remove(temp_path)

	zipped = subprocess.call([local_vars.seven_zip, "a", temp_path, directory], stdout=open(os.devnull, 'w'))

	### Send it over
	log.write("Uploading Data", 1)
	results = ssh_client.exec_command("rm -f ~/%s" % temp_file)  # in case it exists
	file_atts = sftp_client.put(temp_path, temp_file)

	### Unzip it
	log.write("Unzipping on remote server", 1)
	results = ssh_client.exec_command("rm -fr %s" % remote_dir)  # remove the existing "new" folder
	# it's possible this would fail if the directory is being locked - need to check STDERR for it...
	results = ssh_client.exec_command(unzip_command)

	### Move it to the proper location
	results = ssh_client.exec_command("mv %s %s" % (remote_path, remote_dir))  # in case it exists

	### Delete the temp file
	results = ssh_client.exec_command("rm -f ~/%s" % temp_file)


try:
	from _winreg import *

	registry = ConnectRegistry("", HKEY_LOCAL_MACHINE)  # open the registry
	base_folder = QueryValue(registry, "Software\CWS\PISCES\location")  # get the PISCES location
	CloseKey(registry)
except:
	log.error("Unable to get base folder")
	sys.exit()

local_vars.start(arc_script=1)
local_vars.set_workspace_vars(base_folder)  # set up the workspace to the location
log.initialize("Uploading files to server")

# define location of private key
ppk = os.path.join(local_vars.internal_workspace, "data", "keys", "id_rsa.ppk")

# connect to server
host = "pisces.ucdavis.edu"
remote_dir = "~/pisces_upload/new"
log.write("Connecting to %s" % host, 1)

try:
	ssh_client = paramiko.SSHClient()
	ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	ssh_client.connect(hostname=host, port=22, username="dsx", pkey=paramiko.RSAKey.from_private_key_file(filename=ppk, password='eV9twCSJfKFeN5pNejHH'))
	sftp = ssh_client.open_sftp()
	#sftp_transport.auth_publickey("dsx",)
except:
	log.error("Unable to connect!")
	raise

# make the final connection and keep it in sftp

upload_dir(ssh_client, sftp, os.path.join(local_vars.internal_workspace, "maps", "web_output"), remote_dir)

sftp.close()
ssh_client.close()
