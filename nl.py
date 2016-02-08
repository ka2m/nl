#!/usr/bin/python
#
# Script to create a proper Nexus redirect URL.
# Written 4 fun.
#
# Parameters are passed via environment variables:
# Obligatory parameters:
#   NEXUS:  nexus address and port: http://some-nexus:8081/nexus
#   REPO:   repo to look in
#   GID:    group id of artifact
#   AID:    artifact id
# Optional parameters:
#   RELEASE: if non-empty, optimal choice won't be checking snapshot builds
#   VERSION: if none passsed, will return latest
#            if passed X.Y.Z-SNAPSHOT, will return latest for the snapshot
#            can be exact
#   CL:      classifiers, if none passed, will return all the found
#   EXT:     extensions, if none passed, will return all the found
##  BATCH:   no output except the result or fatal errors
# Example:
#   REPOS=releases GID=org.company.project AID=main ./nexus-link.py

import nexuslink.nexuslink as nl


print nl.run()
