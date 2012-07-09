#!/usr/bin/python

import fuse
from time import time

import stat
import os
import errno
import sys
   
from pymongo import Connection
from re import match
from bson.objectid import ObjectId


fuse.fuse_python_api = (0, 2)


class MonFS(fuse.Fuse):
    """
    A Fuse plugin which allows one to store a Nagios configuration into MongoDB and 
    expose it as a regular filesystem.
    
    As a base for this script I have shamelessly ripped of:
        http://sourceforge.net/apps/mediawiki/fuse/index.php?title=FUSE_Python_tutorial
    
    Currently NagiosFS exposes each object as a file because that works for me.
    If there's any interest in alternative ways, let me know.    
    
    Example fstab entry:
    
        /opt/monfs/monfs.py#   /mnt/monfs   fuse    allow_other,host=sandbox,db=monfs,collection=objects 0   1
    
    Parameters:
    
        * host: The name of the MongoDB server.
        * db: The name of the database.
        * collection: The name of the collection containing the configuration.
    """

    def __init__(self, host='localhost', db='monfs', collection='objects', *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)
        self.host=host
        self.db=db
        self.collection=collection
        self.dir_structure = [  '.', '..', 
                                'host', 'hostTemplates', 'hostGroup', 'hostDependency', 'hostEscalation',
                                'service', 'serviceTemplates', 'serviceGroup', 'serviceDependency', 'serviceEscalation',
                                'contact', 'contactTemplates', 'contactGroup',
                                'timePeriod', 'command',
                                'hostExtInfo', 'serviceExtInfo' ]

    def setupConnection(self):
        '''Create a connection object to the MongoDB.'''
        
        try:
            self.mongo = Connection(self.host)[self.db][self.collection]
        except Exception as err:
            print sys.stderr.write('Could not connect to MongoDB. Reason: %s'%err)
            sys.exit(1)

    def getattr(self, path):
        """
        - st_mode (protection bits)
        - st_ino (inode number)
        - st_dev (device)
        - st_nlink (number of hard links)
        - st_uid (user ID of owner)
        - st_gid (group ID of owner)
        - st_size (size of file, in bytes)
        - st_atime (time of most recent access)
        - st_mtime (time of most recent content modification)
        - st_ctime (platform dependent; time of most recent metadata change on Unix,
                    or the time of creation on Windows).
        """
        
        print '*** getattr', path
        st = fuse.Stat()
        if path.lstrip('/') in self.dir_structure or path in ['/','.','..']:
            st.st_mode = stat.S_IFDIR | 0755  
            st.st_nlink = 2
            st.st_atime = int(time())  
            st.st_mtime = st.st_atime  
            st.st_ctime = st.st_atime
            return st
        elif path.split('/')[1] in self.dir_structure:
            size = self.__queryDocument(path)
            if size == None:
                return -errno.ENOENT
            else:
                st.st_mode = stat.S_IFREG | 0755  
                st.st_nlink = 1
                st.st_atime = int(time())  
                st.st_mtime = st.st_atime  
                st.st_ctime = st.st_atime
                st.st_size = len(size)
                return st
        else:
            return -errno.ENOENT
          
    def readdir(self, path, offset):
        print '*** getdir', path
        path = self.__splitPath(path)
        if path[0] == '/':
            for dir in self.dir_structure:
                yield fuse.Direntry(str(dir))
        else:
            for file in self.generateMongoDir(path[1]):
                yield fuse.Direntry(str(file))

    def generateMongoDir(self, type):
        '''Generates the content of a directory by type.
        
        Each directory is "yielded" so it becomes iterable.
        '''
        
        if "Templates" in type :
            query = {"_monfs.type":match('(.*?)Templates',type).group(1), "register":"0"}
        else:
            query = {"_monfs.type":type.lower(), "register":{"$ne":"0"}}
        for object in self.mongo.find(query):
            if object['_monfs']['enabled'] == True:
                yield ('%s.cfg'%(object['_id']))
            else:
                yield ('%s.cfg.disabled'%(object['_id']))
        for object in ['.', '..']:
            yield object

    def read ( self, path, length, offset ):
        print '*** read', path, length, offset
        document = self.__queryDocument(path)
        slen = len(document)
        if offset < slen:
            if offset + length > slen:
                size = slen - offset
            buf = document[offset:offset+size]
        else:
            buf = ''
        return buf

    def __splitPath(self, path):

        if path == '/':
            return ('/','')
        else:
            parts = path.split('/')
            
            if len(parts) == 2:            
                return (parts[0], parts[1].split('.')[0])
            else:
                return (parts[0], None)

    def __queryDocument(self, path):
        '''Queries MongoDB for a document and transforms it to a Nagios compatible format.
        '''
        try:
            document = self.mongo.find_one({ "_id":ObjectId(path.split('/')[2].split('.')[0])})
            return self.__transformDocument(document)
        except:
            return None
    
    def __transformDocument(self, doc):
        '''Pretty print the dictonary
        '''
        object = []
        object.append("define %s{"%(doc['_monfs']['type']))
        
        for key in sorted(doc.keys()):
            if not key in [ '_monfs', '_id' ]:
                object.append("    {0:50} {1}".format(key, doc[key]))
        object.append('}\n')
        return str('\n'.join(object))

    def mythread ( self ):
        print '*** mythread'
        return -errno.ENOSYS

    def chmod ( self, path, mode ):
        print '*** chmod', path, oct(mode)
        return -errno.ENOSYS

    def chown ( self, path, uid, gid ):
        print '*** chown', path, uid, gid
        return -errno.ENOSYS

    def fsync ( self, path, isFsyncFile ):
        print '*** fsync', path, isFsyncFile
        return -errno.ENOSYS

    def link ( self, targetPath, linkPath ):
        print '*** link', targetPath, linkPath
        return -errno.ENOSYS

    def mkdir ( self, path, mode ):
        print '*** mkdir', path, oct(mode)
        return -errno.ENOSYS

    def mknod ( self, path, mode, dev ):
        print '*** mknod', path, oct(mode), dev
        return -errno.ENOSYS

    def open ( self, path, flags ):
        print '*** open', path, flags
        return 0

    def readlink ( self, path ):
        print '*** readlink', path
        return -errno.ENOSYS

    def release ( self, path, flags ):
        print '*** release', path, flags
        return 0
  
    def rename ( self, oldPath, newPath ):
        print '*** rename', oldPath, newPath
        return -errno.ENOSYS

    def rmdir ( self, path ):
        print '*** rmdir', path
        return -errno.ENOSYS

    def statfs ( self ):
        print '*** statfs'
        return -errno.ENOSYS

    def symlink ( self, targetPath, linkPath ):
        print '*** symlink', targetPath, linkPath
        return -errno.ENOSYS

    def truncate ( self, path, size ):
        print '*** truncate', path, size
        return -errno.ENOSYS

    def unlink ( self, path ):
        print '*** unlink', path
        return -errno.ENOSYS

    def utime ( self, path, times ):
        print '*** utime', path, times
        return -errno.ENOSYS

    def write ( self, path, buf, offset ):
        print '*** write', path, buf, offset
        return -errno.ENOSYS

def extractInfo(list):
    '''If someone can figure out how to parse "extra options" through the Fuse argument parser be my 
    guest.  Patches are welcome. 
    '''
    extra_options={}
    options=[]
    index=list.index('-o')+1
    values = list[index].split(',')
    
    for value in values:
        matcher = match('(host|db|collection)=(.*)',value)
        if matcher:
            extra_options[matcher.group(1)]=matcher.group(2)
        else:
            options.append(value)

    list[index]=','.join(options)
    return (list, extra_options)    

if __name__ == "__main__":
    try:
        (options, x_options) = extractInfo(sys.argv)
        fs = MonFS(host=x_options.get('host','sandbox'),db=x_options.get('db','monfs'),collection=x_options.get('collection','objects'))
        fs.flags = 0
        fs.multithreaded = 0
        fs.parse(errex=1)
        fs.setupConnection()
        fs.main()
    except Exception:
        pass
