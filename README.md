#MonFS

## Introduction

MonFS is a Fuse filesystem which allows one to store a Nagios (or 
compatible) configuration in MongoDB and mount that database as as a read 
only filesystem containing a set of configuration files for your 
monitoring application to use.

The goal is to have the MongoDB tools (and the ecosystem around that) 
available to query, alter and store your configuration.  Once a change is 
done in one of the documents stored in MongoDB it is immediately visible 
in the filesystem.

## Design

Each configuration object such as a host or service is a separate file.  This 
will indeed cause many open/read/close operations when your monitoring 
program read the configuration files but I don't see that as a problem.  
This might change in the future but for the time being it works.

Besides a directory for each object type, there's also a Templates directory 
for each ojbect type.  These directories contain objects which have the 
"register 0" configuration. (Currently there's only a Templates directory 
available for hosts, services and contacts)

Each document in MongoDB has a '_monfs' attribute, which contains MonFS 
related "metadata" indicating the type of the object and whether it's enabled 
or not.  When the value of enabled is "False" the filename for that object 
will end on 123456789.cfg.disabled

    u'_monfs': {u'type': u'hostgroup', u'enabled': True}

## Usage

### Installation

You need to have Python and the Python-Fuse bindings available.
Mounting the filesystem from fstab is adding a line similar to this:

    /opt/monfs/monfs.py#   /mnt/monfs   fuse    allow_other,host=sandbox,db=server,collection=objects 0   1
    
The host, db and collection parameters are related to the MongoDB connection.

### Migration

You can load your current Nagios compatible configuration into MongoDB 
using the migrate2monfs.py tool.

    ./migrate2monfs.py --dir /etc/nagios/objects --host mongodbhost --db dbname --collection collectionname

Mount your filesystem and have a look to your configuration.


# Support

If you need any support please submit a message to the monfs forum at 
https://groups.google.com/d/forum/monfs

If you have found a bug submit a ticket to:
https://github.com/smetj/monfs/issues.


Have fun!
