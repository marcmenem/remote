#!/usr/bin/python -i

import ConfigParser
import sys, os.path, time

import connect

filename = 'example.cfg'
GUID = "0000000000000001"
remotename = "Marc Remote tbbt"
defaultPort = 10024

itunesClients = {}

time.sleep(1.5)



__macosx__ = sys.platform == 'darwin'


if __macosx__:
    connect.browse().start()
else:
    #import gobject
    #loop2 = gobject.MainLoop()
    #loop2.run()
    pass
    

class client:
    def __init__(self):
        pass
    
    def fromBonjour(self, bjitunes):
        self.dbId = bjitunes.dbId
        self.dbName = bjitunes.dbName
        
        

class configManager:
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        if os.path.exists(filename):
            self.readConfig()
        else:
            self.config.add_section("Client")
            self.config.set('Client', 'guid', GUID)
            
            for it in connect.itunesClients.values():
                cl = client()
                cl.fromBonjour(it)
                self.manage(cl)
    
    
    def manage(self, cl):
        self.config.add_section(cl.dbId)
        self.config.set(cl.dbId, "name", cl.dbName )
    
    def readConfig(self):
        try:
            self.config.read(filename)
            GUID = self.config.get("Client", "guid")
            
        except ConfigParser.NoSectionError, e:
            print e
        
    def saveConfig(self):
        with open(filename, 'wb') as configfile:
            self.config.write(configfile)
        
    def connect(self, dbId, sessionid):
        try:
            self.config.set(dbId, "sessionid", sessionid)
        except:
            print "EEEE", "unable to add config"
        
    def unconnect(self, dbId):
        try:
            self.config.remove_option(dbId, "sessionid")
        except:
            print "EEEE", "unable to remove config"
        
    
    def sessionid( self, dbId ):
        try:
            str = self.get(dbId, "sessionid")
        except:
            return None
        return str
        
        
    #config.remove_option(section1, option)

if __name__ == "__main__":
    requiredDB = 'Biblioth\xc3\xa8que de \xc2\xab\xc2\xa0Marc Menem\xc2\xa0\xc2\xbb'

    confMan = configManager()
    confMan.saveConfig()

    sys.exit(0)



"""

# getfloat() raises an exception if the value is not a float
# getint() and getboolean() also do this for their respective types
float = config.getfloat('Section1', 'float')
int = config.getint('Section1', 'int')
print float + int

# Notice that the next output does not interpolate '%(bar)s' or '%(baz)s'.
# This is because we are using a RawConfigParser().
if config.getboolean('Section1', 'bool'):
    print config.get('Section1', 'foo')
""


config = ConfigParser.ConfigParser()
config.read('example.cfg')

# Set the third, optional argument of get to 1 if you wish to use raw mode.
print config.get('Section1', 'foo', 0) # -> "Python is fun!"
print config.get('Section1', 'foo', 1) # -> "%(bar)s is %(baz)s!"

# The optional fourth argument is a dict with members that will take
# precedence in interpolation.
print config.get('Section1', 'foo', 0, {'bar': 'Documentation',
                                        'baz': 'evil'})

# New instance with 'bar' and 'baz' defaulting to 'Life' and 'hard' each
config = ConfigParser.SafeConfigParser({'bar': 'Life', 'baz': 'hard'})
config.read('example.cfg')

print config.get('Section1', 'foo') # -> "Python is fun!"
config.remove_option('Section1', 'bar')
config.remove_option('Section1', 'baz')
print config.get('Section1', 'foo') # -> "Life is hard!"


def opt_move(config, section1, section2, option):
    try:
        config.set(section2, option, config.get(section1, option, 1))
    except ConfigParser.NoSectionError:
        # Create non-existent section
        config.add_section(section2)
        opt_move(config, section1, section2, option)
    else:
        

"""

