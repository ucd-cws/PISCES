# Workflow for issuing PISCES updates
This document is to describe the general steps that need to be done to issue a PISCES update

## General
 * Write release notes
 * Commit code, merge into release branch, make a tag for the release version and move the release tag to that commit
 * Update non-critical dependencies (TortoiseHg, SQLiteStudio, etc) that won't cause breakages if untested in installation package
 * Make sure config.py doesn't have any machine-specific settings - need to move to something with local config and global like other projects

## Data
 * Clean the layer cache and run an export for all native fish so that it's prepopulated
 * Run a web export and upload to PISCES site - alert Dave that we have updated data, potentially including new fish species, etc.
 
## Software
 * Bump the version number
 * Build the documentation (this might be done in the next step)
 * Double check the username set as default in the installation package
 * Build a new installation package
 * Upload the new installation package to the web
 
## Online
 * Use Beyond Compare to copy the documentation up to pisces.ucdavis.edu
 * Update the layers in the PISCES online viewer from the exported layer cache copy
 * Export a diversity layer and update the layer in the online viewer
 
## Notifications
 * Probably worth alerting key CWS staff and DFW staff about new versions that are stable
 