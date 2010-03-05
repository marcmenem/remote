#!/usr/bin/python -i

import urllib
import urllib2
import struct
import sys, re

import decode
import response

import threading

import ConfigParser

config = ConfigParser.RawConfigParser()
filename = 'remotecontrol.cfg'

def writeConfig(id):
    config.add_section('connexion')
    config.set( itunes.serviceName, 'sessionid', id)
    # Writing our configuration file to 'example.cfg'
    with open(filename, 'wb') as configfile:
        config.write(configfile)

def readConfig():
    config.read(filename)
    return config.get('connexion', 'sessionid', 0) 



class daemonThread( threading.Thread ):
    def __init__(self):
        super(daemonThread, self).__init__()
        self.setDaemon(False)

class eventman(daemonThread):
    def run ( self ):
        if not 'nextupdate' in dir(self.remote): self.remote.showStatus()
        st = self.remote.showStatus( self.remote.nextupdate )
        print "Update"
        self.run()

class playlistman(daemonThread):
    def run ( self ):
        if not 'nextplaylistupdate' in dir(self.remote): self.remote.update()
        st = self.remote.update( self.remote.nextplaylistupdate )
        print "Update playlist"
        self.run()        



        
def _encode( values ):
    st = '&'.join([ str(k) + '=' + str(values[k]) for k in values ])
    return st.replace(' ', "%20")


class results:
    def __init__(self):
        pass
        
    def show(self):
        print "Albums  --+", self.albums.totnb
        for n in self.albums.list:
            print "\t", n.name
        print "Artists --+", self.artists.totnb
        for n in self.artists.list:
            print "\t", n
        print "Songs   --+", self.tracks.totnb
        for n in self.tracks.list:
            print "\t", n.name


class remote:
    def __init__(self, ip, port):
        self.guid="0x0000000000000001"
        self.service = 'http://' + ip + ':' + port
        self.sessionid = None
        

    def _ctloperation( self, command, values, verbose = True):
        command = '%s/ctrl-int/1/%s' % (self.service, command)
        return self._operation( command, values, verbose)
        
        
    def _operation( self, command, values, verbose=True, sessionid = True):
        if sessionid:
            if self.sessionid is None:
                self.pairing()
            values['session-id'] = self.sessionid
        
        url = command
        if len(values): url += "?" + _encode(values)
        if verbose: print url
        
        headers = { 'Viewer-Only-Client': '1'  }
        request = urllib2.Request( url, None, headers )
        resp = urllib2.urlopen(request)
        out = resp.read()
        
        if verbose: self._decode2( out )
        resp = response.response( out )
        
        return resp.resp
    
    
    def databases(self):
        command = '%s/databases' % (self.service)
        resp = self._operation( command, {}, False )
        self.databaseid = resp["avdb"]["mlcl"]["mlit"]["miid"]
        return resp        
            
    def playlists(self):
        command = '%s/databases/%d/containers' % (self.service, self.databaseid)
        meta = [
            'dmap.itemname', 
            'dmap.itemcount', 
            'dmap.itemid', 
            'dmap.persistentid', 
            'daap.baseplaylist', 
            'com.apple.itunes.special-playlist', 
            'com.apple.itunes.smart-playlist', 
            'com.apple.itunes.saved-genius', 
            'dmap.parentcontainerid', 
            'dmap.editcommandssupported', 
            'com.apple.itunes.jukebox-current', 
            'daap.songcontentdescription'
            ]        
        values = { 'meta': ','.join(meta) }

        resp = self._operation( command, values, False )
        resp = resp['aply']
        self.playlists_cache = resp
        return resp


    def pairing(self):
        url = '%s/login?pairing-guid=%s' % (self.service, self.guid)

        data = urllib2.urlopen( url ).read()
        
        resp = response.response(data)        
        self.sessionid = resp.resp['mlog']['mlid']
    
        print "Got session id", self.sessionid
        self.databases()
        pl = self.playlists()
        self.musicid = pl.library.id
        self.getspeakers()
        
        return resp
    
    
    
    def _query_groups(self, q):
        command = '%s/databases/%d/groups' % (self.service, self.databaseid)
        mediakind = [1,4,8,2097152,2097156]
        qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
        query="((" + qt + ")+'daap.songalbum:*" + q + "*'+'daap.songalbum!:')"
        
        meta = [
            'dmap.itemname',
            'dmap.itemid', 
            'dmap.persistentid', 
            'daap.songartist', 
            ]        

        values = { 
            "meta": ','.join(meta),
            "type": 'music',
            'group-type': 'albums',
            "sort": "album",
            "include-sort-headers": '1',
            "index": ("%d-%d" % (0,7)),
            "query": query
            }

        resp = self._operation( command, values, False )
        return resp['agal']

    
    def _query_artists(self, q):
        command = '%s/databases/%d/browse/artists' % (self.service, self.databaseid)
        mediakind = [1,4,8,2097152,2097156]
        qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
        query="(" + qt + ")+'daap.songartist:*" + q + "*'+'daap.songartist!:'"
        
        values = { 
            "include-sort-headers": '1',
            "index": ("%d-%d" % (0,7)),
            "filter": query
        }

        resp = self._operation( command, values, False )
        return resp['abro']
       

    def _query_songs(self, q):
        command = '%s/databases/%d/containers/%d/items' % (self.service, 
                                                    self.databaseid, self.musicid)
        #mediakind = [2,6,36,32,64,2097154,2097158]   # films & podcasts
        mediakind = [1,4,8,2097152,2097156]
        
        qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
        query="((" + qt + ")+'dmap.itemname:*" + q + "*')"

        meta = [
            'dmap.itemname',
            'dmap.itemid', 
            'dmap.songartist',
            'dmap.songalbum', 
            'daap.containeritemid',
            'com.apple.itunes.has-video'
            ]        

        values = { 
            "meta": ','.join(meta),
            "type": 'music',
            "sort": "name",
            "include-sort-headers": '1',
            "index": ("%d-%d" % (0,7)),
            "query": query
            }
        
        resp = self._operation( command, values, False )
        return resp['apso']

    
    def query(self, text):
        res = results()
        res.albums = self._query_groups(text)
        res.artists = self._query_artists(text)
        res.tracks = self._query_songs(text)
        
        res.show()
        return res


    def _decode2(self, d):
        a = []
        for i in range(len(d)):
            a.append(d[i])
        r = decode.decode( a, len(d), 0)
        print "--+ :)"
        return r
        
    
    def skip(self):
        return self._ctloperation('nextitem', {})    
        
    def prev(self):
        return self._ctloperation('previtem', {})    
        
    def play(self):
        return self._ctloperation('playpause', {})    
        
    def pause(self):
        return self._ctloperation('pause', {})    
        
    def getspeakers(self):
        spk = self._ctloperation('getspeakers', {}, False)    
        self.speakers = spk['casp']
        return self.speakers
        
    def setspeakers(self, spkid):
        values = {'speaker-id': ",".join([ str(self.speakers[idx].id) for idx in spkid]) }
        self._ctloperation('setspeakers', values)    
        return self.getspeakers()
        
        
        
    def showStatus(self, revisionnumber='1', verbose=False):
        values = {'revision-number': revisionnumber }
        status = self._ctloperation('playstatusupdate', values, verbose)    
        status = status['cmst']
        status.show()
        self.nextupdate = status.revisionnumber
        return status
        
    def clearPlaylist( self ):
        return self._ctloperation('cue', {'command': 'clear'})
        
    def playArtist( self, artist, index=0):
        values = {
            'command': 'play', 
            'query': "'daap.songartist:" + artist + "'",
            'index': index,
            'sort': 'album',
            }
        return self._ctloperation('cue', values)
        
    def playAlbumId(albumid, index=0):
        values = {
            'command': 'play', 
            'query': "'daap.songalbumid:" + albumid + "'",
            'index': index,
            'sort': 'album',
            }
        return self._ctloperation('cue', values)
        
        
        
        
    def seek( self, time ):
        return self.setproperty('dacp.playingtime', time)
        
    def setproperty(self, prop, val):
        values = {prop: val }
        return self._ctloperation('setproperty', values)    
        
    def getproperty(self, prop ):
        values = {'properties': prop }
        return self._ctloperation('getproperty', values)    
        
        
    def getvolume(self ):
        return self.getproperty('dmcp.volume')    
        
    def setvolume(self, value ):
        return self.setproperty('dmcp.volume', value)    
        
    # Blocks until playlist is updated
    def update(self, rev=None):
        print "server-info >>> "
        url = '%s/update' % (self.service)
        if rev: 
            values = {'revision-number':rev}
        else:
            values = {}
        up = self._operation(url, values)
        self.nextplaylistupdate = up['mupd']['musr']
        return up
        
    def serverinfo(self):
        print "server-info >>> "
        url = '%s/server-info' % (self.service)
        return self._operation(url, {}, sessionid=False)
        
    def shuffle(self, state):
        return self.setproperty( 'dacp.shufflestate', state)
        
    def repeat(self, state):
        return self.setproperty( 'dacp.repeatstate', state)
        
    def updatecallback(self):
        print "Launching UI thread"
        event = eventman()
        event.remote = self
        event.start()

        print "Launching playlist thread"
        pl = playlistman()
        pl.remote = self
        pl.start()



"GET /ctrl-int/1/nowplayingartwork?mw=320&mh=320&session-id=284830210"

"""
/ctrl-int/1/cue?command=play&
    query=(('com.apple.itunes.mediakind:1','com.apple.itunes.mediakind:4',
    'com.apple.itunes.mediakind:8','com.apple.itunes.mediakind:2097152',
    'com.apple.itunes.mediakind:2097156')+'dmap.itemname:*Dido*')&
    index=1&sort=name&session-id=284830210

/databases/41/items/10391/extra_data/artwork?session-id=1131893462&mw=55&mh=55

"""


if __name__ == "__main__":
    conn = remote('192.168.1.8', '3689')











