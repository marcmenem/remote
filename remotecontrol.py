#!/usr/bin/python -i

#Copyright (C) 2010 Marc Menem

#This file is part of Remote. Remote is free software: you can
#redistribute it and/or modify it under the terms of the GNU General
#Public License as published by the Free Software Foundation, either
#version 3 of the License, or (at your option) any later version.

#Remote is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Remote. If not, see <http://www.gnu.org/licenses/>.

"""
Some info about the protocol on these pages:

http://dacp.jsharkey.org/
http://daap.sourceforge.net/docs/index.html

"""

import urllib
import urllib2
import struct
import sys, re

import decode
import response

import time
import threading

import ConfigParser

import connect

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
        if not hasattr(self.remote,'nextupdate'): 
            self.remote.showStatus()
            self.remote.artwork = self.remote.nowplayingartwork()
        st = self.remote.showStatus( self.remote.nextupdate )
        print "Update"
        self.remote.artwork = self.remote.nowplayingartwork()
        
        self.run()

class playlistman(daemonThread):
    def run ( self ):
        if not hasattr(self.remote,'nextplaylistupdate'): self.remote.update()
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
        self.service = 'http://' + ip + ':' + str(port)
        self.sessionid = None
        print "Connecting to", self.service
        

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
        
        try:
            resp = urllib2.urlopen(request)
            headers = resp.headers.dict
            
            out = resp.read()
            if headers['content-type'] != 'image/png':
                
                if verbose: self._decode2( out )
                resp = response.response( out )
                
                return resp.resp
            else:
                return out
        except:
            print "CAUGHT ERROR"
            return None
    
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
    
    def logout(self):
        url = '%s/logout' % (self.service)
        lo = self._operation( url, {})
        self.sessionid = None
        return lo
    
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
        url = '%s/update' % (self.service)
        if rev: 
            values = {'revision-number':rev}
        else:
            values = {}
        up = self._operation(url, values, verbose=False)
        self.nextplaylistupdate = up['mupd']['musr']
        return up
        
        
    """
            def do_GET_server_info(self):
            msrv = do('dmap.serverinforesponse',
                      [ do('dmap.status', 200),
                        do('dmap.protocolversion', '2.0'),
                        do('daap.protocolversion', '3.0'),
                        do('dmap.timeoutinterval', 1800),
                        do('dmap.itemname', server_name),
                        do('dmap.loginrequired', 0),
                        do('dmap.authenticationmethod', 0),
                        do('dmap.supportsextensions', 0),
                        do('dmap.supportsindex', 0),
                        do('dmap.supportsbrowse', 0),
                        do('dmap.supportsquery', 0),
                        do('dmap.supportspersistentids', 0),
                        do('dmap.databasescount', 1),                
                        #do('dmap.supportsautologout', 0),
                        #do('dmap.supportsupdate', 0),
                        #do('dmap.supportsresolve', 0),
                       ])
    """
    def serverinfo(self):
        url = '%s/server-info' % (self.service)
        return self._operation(url, {}, sessionid=False, verbose=False)
        
    """
    This request serves to return the list of content codes in use by the server. This allows the 
    server to be updated to contain new fields and older clients can still connect without trouble. 
    In fact, this also allowed us to decode the entirety of the protocol very easily.
    """
    def contentcodes(self):
        print "content-codes >>> "
        url = '%s/content-codes' % (self.service)
        return self._operation(url, {})
        
    " ??? "
    def resolve(self):
        print "resole >>> "
        url = '%s/resolve' % (self.service)
        return self._operation(url, {})
        
                
        
        
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

    def nowplayingartwork(self, savetofile=True):
        data = self._ctloperation('nowplayingartwork', {'mw': '320', 'mh': '320'}, verbose=True)
        if savetofile and (len(data) > 0):
            filename = 'nowplaying.png'
            nowplaying_png = open(filename, 'w')
            nowplaying_png.write(data)
            nowplaying_png.close()
            print "Saved to file", filename
        return data


        
    def playSong(self, song, index=0):
        mediakind = [1,4,8,2097152,2097156]
        
        qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
        query="((" + qt + ")+'dmap.itemname:*" + song + "*')"

        values = { 
            'command': 'play', 
            "sort": "name",
            "include-sort-headers": '1',
            'index': index,
            "query": query
            }
    
        return self._ctloperation('cue', values)
        
        

"""
/ctrl-int/1/cue?command=play&
    query=(('com.apple.itunes.mediakind:1','com.apple.itunes.mediakind:4',
    'com.apple.itunes.mediakind:8','com.apple.itunes.mediakind:2097152',
    'com.apple.itunes.mediakind:2097156')+'dmap.itemname:*Dido*')&
    index=1&sort=name&session-id=284830210

/databases/41/items/10391/extra_data/artwork?session-id=1131893462&mw=55&mh=55

"""


if __name__ == "__main__":
    requiredDB = 'Biblioth\xc3\xa8que de \xc2\xab\xc2\xa0Marc Menem\xc2\xa0\xc2\xbb'

    connect.browse().start()
    conn = None
    while not conn:
        if len(connect.itunesClients) > 0:
            for it in connect.itunesClients.values():
                conn2 = remote(it.ip, it.port)
                si = conn2.serverinfo()
                dbn = si['msrv']['minm']
                if dbn == requiredDB:
                    conn = conn2
                else:
                    print "Skipping", dbn
        else:
            time.sleep(0.5)

    import atexit

    @atexit.register
    def goodbye():
        print "Logging out"
        conn.logout()








