#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  migrate2monfs.py
#  
#  Copyright 2012 Jelle Smet development@smetj.net
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  
import os
import fnmatch
import re
import sys
from pymongo import Connection
import argparse

class Migrate2MonFS():
    '''Reads recursively the content of a directory and grabs Nagios compatible configuration
    out of the files to upload them into MongoDB with the goal of using MonFS.
    
    Parameters:
    
        * directory: The directory containing the .cfg files. [./]
        * host: The name of the MongoDB host. [localhost]
        * db: The name of the MongoDB database to load the configuration in. [nagios]
        * collection: The name of the MongoDB collection to load the configuration in. [objects]
    '''
    def __init__(self, directory='./', host='localhost', db='monfs', collection='objects'):
        self.conn = Connection(host)
        self.db = db
        self.collection = collection
        self.readDir(directory)

    def readDir(self, dir):
        '''Process all *.cfg files from directory.
        '''                
        for root, dirnames, filenames in os.walk(dir):
            for filename in fnmatch.filter(filenames, '*.cfg'):
                print "Processing %s/%s"%(root, filename)
                self.dumpConfig(os.path.join(root, filename))

    def dumpConfig(self, name):
        '''Opens file and grabs the complete object, determines the object type.
        '''
        
        file = open(name,'r')
        content = ''.join(file.readlines())
        file.close()
        regex = re.compile('^define\ (.*?)\{(.*?)\}$', re.MULTILINE|re.DOTALL)
        for result in regex.findall(content):
            self.writeMongo(self.packageData(result[0], result[1]))

    def packageData(self, type, data):
        '''Creates a dictionary from the config object and writes it into MongoDB.
        '''
        
        object={'_monfs':{'type':type, 'enabled': True}}
        for line in data.split('\n'):
            if line != '':
                keyvalue = re.match('\s*(.*?)\s+(.*)',line).groups()
                object[keyvalue[0]]=keyvalue[1]
        return object
        
    def writeMongo(self, data):
        '''Actually write data to MongoDB.
        '''
        self.conn[self.db][self.collection].insert(data)       

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument( "--dir", help="The directory to import from. [./]", default='./' )
    parser.add_argument( "--host", default='localhost', help="The MongoDB host. [localhost]" )
    parser.add_argument( "--db", default='monfs', help="The name of the MongoDB database to use. [monfs]" )
    parser.add_argument( "--collection", default='objects', help="The name of the MongoDB collection to use. [objects]" )
    args = parser.parse_args()
    try:
        instance = Migrate2MonFS(directory=args.dir, host=args.host, db=args.db, collection=args.collection)
    except Exception as err:
        print ('Import of config files failed.  Reason: %s'%(err))
    else:
        print ('Import succeeded.')
