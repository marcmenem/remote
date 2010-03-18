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


__version__ = "0.1"

print """Remote version %s, Copyright (C) 2010 Marc Menem
Remote comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it under certain conditions.
""" % __version__



import urllib, urllib2
from urllib2 import HTTPError


import struct, sys, re, time, threading
import StringIO, gzip
                
import decode
import response
import config



confMan = config.configManager()



class daemonThread( threading.Thread ):
    def __init__(self):
        super(daemonThread, self).__init__()
        self.setDaemon(True)

class eventman(daemonThread):
    def run ( self ):
        if not hasattr(self.remote,'nextupdate'): 
            st = self.remote.showStatus()
        st = self.remote.showStatus( self.remote.nextupdate )
        if not st:
            time.sleep(1)
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
            print "\t", n.name, n.id
        print "Artists --+", self.artists.totnb
        for n in self.artists.list:
            print "\t", n
        print "Songs   --+", self.tracks.totnb
        for n in self.tracks.list:
            print "\t", n.name, n.id


class remote:
    def __init__(self, ip, port, dbId ):
        self.guid="0x" + config.GUID
        self.service = 'http://' + ip + ':' + str(port)
        self.dbId = dbId
        print "Connecting to", self.service
        self.sessionid = confMan.sessionid(self.dbId)
        

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
        
        headers = { 
            'Viewer-Only-Client': '1', 
            'Connection':'keep-alive', 
            'Accept-Encoding': 'gzip'} 
        
        #    'Accept-Encoding': 'identity', 
        #    'User-agent':'Python-urllib/2.6' } 
        #    'Connection':'close' } 
        
        request = urllib2.Request( url, None, headers )
        
        try:
            resp = urllib2.urlopen(request)
            headers = resp.headers.dict
        
            if 'content-encoding' in headers and headers['content-encoding'] == 'gzip':
                compressedstream = StringIO.StringIO(resp.read())
                gzipper = gzip.GzipFile(fileobj=compressedstream)
                out = gzipper.read()                 
            else:
                out = resp.read()
            if headers['content-type'] != 'image/png':
                
                if verbose: self._decode2( out )
                resp = response.response( out )
                
                return resp.resp
            else:
                return out
        except HTTPError, e:
            print "HTTPError while running query"
            print request.get_full_url()
            print request.headers
            print e
        except:
            print "Unexpected error:", sys.exc_info()[0]
            return None
    
    def databases(self):
        command = '%s/databases' % (self.service)
        resp = self._operation( command, {}, False )
        self.databaseid = resp["avdb"]["mlcl"]["mlit"]["miid"]
        return resp        
            
    def pairing(self):
        url = '%s/login?pairing-guid=%s' % (self.service, self.guid)

        data = urllib2.urlopen( url ).read()
        
        resp = response.response(data)        
        self.sessionid = resp.resp['mlog']['mlid']
    
        confMan.connect( self.dbId, self.sessionid )
    
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
        #confMan.unconnect( self.dbId )
        return lo
    
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

    
    def _query_groups(self, q=None, startid=0, nbitem=8, verbose=False):
        command = '%s/databases/%d/groups' % (self.service, self.databaseid)
        
        meta = [
            'dmap.itemname',
            'dmap.itemid', 
            'dmap.persistentid', 
            'daap.songartist'
            ]        

        values = { 
            "meta": ','.join(meta),
            "type": 'music',
            'group-type': 'albums',
            "sort": "album",
            "include-sort-headers": '1',
            "index": ("%d-%d" % (startid, nbitem - startid - 1)),
            }
            
        if q:
            mediakind = [1,4,8,2097152,2097156]
            qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
            query="((" + qt + ")+'daap.songalbum:*" + q + "*'+'daap.songalbum!:')"
            values['query'] = query
        
        resp = self._operation( command, values, verbose=verbose )
        return resp['agal']

    
    def _query_artists(self, q=None, startid=0, nbitem=8):
        command = '%s/databases/%d/browse/artists' % (self.service, self.databaseid)
        
        values = { 
            "include-sort-headers": '1',
            "index": ("%d-%d" % (startid,nbitem - startid - 1))
        }

        if q:
            mediakind = [1,4,8,2097152,2097156]
            qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
            query="(" + qt + ")+'daap.songartist:*" + q + "*'+'daap.songartist!:'"
            values['filter'] = query        

        resp = self._operation( command, values, False )
        return resp['abro']
       
        
    """
http.request.uri == 
"/databases/43/containers/28764/items?session-id=1248913784
&meta=dmap.itemname,dmap.itemid,daap.songartist,daap.songalbum,
dmap.containeritemid,com.apple.itunes.has-video,daap.songuserrating,
daap.songtime&type=music&sort=album&query='daap.songalbumid:16163238975009571254'"
       
http.request.uri == "/databases/43/containers/28764/items?session-id=1093637321&
meta=dmap.itemname,dmap.itemid,daap.songartist,daap.songalbum,dmap.containeritemid,
com.apple.itunes.has-video,daap.songuserrating,daap.songtime&type=music&sort=album&
query='daap.songalbumid:14279550205875584078'"
       
    """
    
    def _query_songs(self, q=None, startid=0, nbitem=8, containerid=None, verbose=False, albumid=None):
        if not containerid: containerid = self.musicid
        command = '%s/databases/%d/containers/%d/items' % (self.service, self.databaseid, containerid)
        
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
            "include-sort-headers": '1',
            "index": ("%d-%d" % (startid, nbitem - startid - 1)),
            }

        if q:
            #mediakind = [2,6,36,32,64,2097154,2097158]   # films & podcasts
            mediakind = [1,4,8,2097152,2097156]
            
            qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
            query="((" + qt + ")+'dmap.itemname:*" + q + "*')"
            values['query'] = query
            values["sort"] = "name"
        elif albumid:
            query="'daap.songalbumid:" + albumid + "'"
            values['query'] = query
            values["sort"] = "album"
            
        resp = self._operation( command, values, verbose=verbose )
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
        if status:
            status = status['cmst']
            status.show()
            self.nextupdate = status.revisionnumber
            self.status = status
            if status.playstatus > 2:
                self.artwork = self.nowplayingartwork()
            else:
                self.artwork = None
        return status
    
        
    def clearPlaylist( self ):
        return self._ctloperation('cue', {'command': 'clear'})
        
    def playArtist( self, artist, index=0, clear = True):
        if clear: self.clearPlaylist()
        values = {
            'command': 'play', 
            'query': "'daap.songartist:" + artist + "'",
            'index': index,
            'sort': 'album',
            }
        return self._ctloperation('cue', values)
        
    
    
    def playAlbum(self, album, index=0, clear = True):
        if clear: self.clearPlaylist()
        mediakind = [1,4,8,2097152,2097156]
        
        qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
        query="((" + qt + ")+'daap.songalbum:*" + album + "*'" + ''+ ")"

        
        values = {
            'command': 'play', 
            'query': query,
            'index': index,
            'sort': 'album'
            }
        return self._ctloperation('cue', values)
        
        
    def playAlbumId(self, albumid, index=0, clear = True):
        if clear: self.clearPlaylist()
        mediakind = [1,4,8,2097152,2097156]
        
        qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
        query="((" + qt + ")+'daap.songalbumid:" + albumid + "'" + ''+ ")"

        
        values = {
            'command': 'play', 
            'query': query,
            'index': index,
            'sort': 'album'
            }
        return self._ctloperation('cue', values)
        
        
    def playSong(self, song, index=0, clear = True):
        if clear: self.clearPlaylist()
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
        
        
        
    def seek( self, time ):
        return self.setproperty('dacp.playingtime', time)
        
    def setproperty(self, prop, val):
        values = {prop: val }
        return self._ctloperation('setproperty', values)    
        
    def getproperty(self, prop ):
        values = {'properties': prop }
        return self._ctloperation('getproperty', values)    
        
        
    def getvolume(self ):
        return self.getproperty('dmcp.volume')['cmgt']['cmvo']
        
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
             msrv  --+
                mstt (dmap.status)             4      200
                mpro (dmap.protocolversion)    4      131078
                apro (daap.protocolversion)    4      196616
                aeSV (com.apple.itunes.music-sharing-version) 4      196609
                aeFP (com.apple.itunes.req-fplay) 1      1
                ated (daap.supportsextradata)  2      3
                msed                           1      1
                msml  --+
                    msma                           8      134512876069632
                    msma                           8      35679737357056
                ceWM                           0       #()
                ceVO                           1      0
                minm (dmap.itemname)           35     Biblio*****
                mslr (dmap.loginrequired)      1      1
                mstm (dmap.timeoutinterval)    4      1800
                msal (dmap.supportsautologout) 1      1
                msas (dmap.authenticationschemes) 1      3
                msup (dmap.supportsupdate)     1      1
                mspi (dmap.supportspersistentids) 1      1
                msex (dmap.supportsextensions) 1      1
                msbr (dmap.supportsbrowse)     1      1
                msqy (dmap.supportsquery)      1      1
                msix (dmap.supportsindex)      1      1
                msrs (dmap.supportsresolve)    1      1
                msdc (dmap.databasescount)     4      1
                mstc (dmap.utctime)            4      1268580413
                msto (dmap.utcoffset)          4      3600
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

    def getsongartwork(self, itemid, savetofile=True):
        url = '%s/databases/%s/items/%s/extra_data/artwork' % (self.service, self.databaseid, itemid)
        values = {'mw': '55', 'mh': '55'}
        data = self._operation(url, values, verbose=True)
        if savetofile and (len(data) > 0):
            filename = 'extra.png'
            extra_png = open(filename, 'w')
            extra_png.write(data)
            extra_png.close()
            print "Saved to file", filename
        return data

    def getalbumartwork(self, itemid, savetofile=True):
        url = '%s/databases/%s/groups/%s/extra_data/artwork' % (self.service, self.databaseid, itemid)
        values = {'mw': '55', 'mh': '55', 'group-type': 'albums'}
        data = self._operation(url, values, verbose=True)
        if savetofile and (len(data) > 0):
            filename = 'extra.png'
            extra_png = open(filename, 'w')
            extra_png.write(data)
            extra_png.close()
            print "Saved to file", filename
        return data


        

"""
/ctrl-int/1/cue?command=play&
    query=(('com.apple.itunes.mediakind:1','com.apple.itunes.mediakind:4',
    'com.apple.itunes.mediakind:8','com.apple.itunes.mediakind:2097152',
    'com.apple.itunes.mediakind:2097156')+'dmap.itemname:*Dido*')&
    index=1&sort=name&session-id=284830210

/databases/41/items/10391/extra_data/artwork?session-id=1131893462&mw=55&mh=55

"""

def connectRC(update = True):
    requiredDB = 'Biblioth\xc3\xa8que de \xc2\xab\xc2\xa0Marc Menem\xc2\xa0\xc2\xbb'


    print "Connecting"
    
    conn = None
    t = 1000
    while not conn and t>0:
        sys.stdout.flush()

        nbCl = len(config.connect.itunesClients)
        if nbCl > 0:
            print "Got %i clients" % nbCl, 
    
            for it in config.connect.itunesClients.values():
                if hasattr(it,'ip') and hasattr(it,'port') and hasattr(it,'dbId') :

                    conn2 = remote(it.ip, it.port, it.dbId)
                    si = conn2.serverinfo()
                    dbn = si['msrv']['minm']
                    if dbn == requiredDB:
                        conn = conn2
                        conn.showStatus()
                        if update: conn.updatecallback()
                    else:
                        print "Skipping", dbn
                
                else:
                    print "... Waiting, client not resolved yet", it
                    pass
                    
            print 

        else:
            time.sleep(0.5)
        
        t -= 1
    
    if t == 0:
        print "Failed"



    
    import atexit

    @atexit.register
    def goodbye():
        print "Logging out"
        conn.logout()
        confMan.saveConfig()

    return conn


if __name__ == "__main__":
    
    __macosx__ = sys.platform == 'darwin'
    
    if not __macosx__:
        import gobject
        loop = gobject.MainLoop()
        

        def quitMain():
            print "Quiting GLib main loop"
            loop.quit()
        
        config.connect.postHook = quitMain
        loop.run()
        
    
    conn = connectRC()


