nl
=====

nexus-link - format redirect URLs for your artifacts basing on GAV

# HowTo

Parameters are passed via environment variables:

Obligatory parameters:

*  NEXUS:  nexus address and port: http://some-nexus:8081/nexus
*  REPO:   repo to look in
*  GID:    group id of artifact
*  AID:    artifact id

Optional parameters:

* VERSION: if none passsed, will return latest
           if passed X.Y.Z-SNAPSHOT, will return latest for the snapshot
           can be exact
*  CL:      classifiers, if none passed, will return all the found
*  EXT:     extensions, if none passed, will return all the found

Example:

REPOS=snapshots GID=org.company.project AID=main EXT=war ./nexus-link.py

# TODO

* Search in release
* Verbose mode
* Refactoring

# Credits

Vlad Slepukhin, 2016
