__author__ = 'dsx'

import subprocess
import sys

return_code = subprocess.call(["hg", "pull"])
if return_code == 255:
	print "Failed to pull changes from remote server. Update failed - see above - contact Nick Santos (nrsantos@ucdavis.edu) for assistance."
	sys.exit(1)

return_code = subprocess.call(["hg", "update", "--rev", "dfw", "--check"])

if return_code == 255:
	print "Update failed - see above - contact Nick Santos (nrsantos@ucdavis.edu) for assistance."
else:
	print "UPDATED"