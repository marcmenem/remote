#!/usr/bin/python -i

import urllib
import urllib2
import struct
import sys, re

import decode
import response

import threading



class eventman(threading.Thread):
    
    def run ( self ):
        st = self.remote.showStatus( self.remote.nextupdate )
        print "Update"
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
    def __init__(self):
        self.guid="0x0000000000000001"
        self.service = 'http://192.168.1.8:3689'
        self.sessionid = None
        

    def _ctloperation( self, command, values, verbose = True):
        command = '%s/ctrl-int/1/%s' % (self.service, command)
        return self._operation( command, values, verbose)
        
        
    def _operation( self, command, values, verbose=True):
        if self.sessionid is None:
            self.pairing()
    
        values['session-id'] = self.sessionid
        
        url = command
        url += "?" + _encode(values)
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
       
        
    """
    http.request.uri == "/databases/41/containers/28402/items?
    session-id=1131893462&
    meta=dmap.itemname,dmap.itemid,daap.songartist,daap.songalbum,
    dmap.containeritemid,com.apple.itunes.has-video&
    type=music&
    sort=name&
    include-sort-headers=1&
    query=(('com.apple.itunes.mediakind:2','com.apple.itunes.mediakind:6',
    'com.apple.itunes.mediakind:36','com.apple.itunes.mediakind:32',
    'com.apple.itunes.mediakind:64','com.apple.itunes.mediakind:2097154',
    'com.apple.itunes.mediakind:2097158')+'dmap.itemname:*Vam*')&
    index=0-7"
    
    """
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
        
        resp = self._operation( command, values, True )
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
            
    def serverinfo(self, prop ):
        print "server-info >>> "
        values = {prop: val }
        command = '%s/server-info' % (self.service)
        return self._operation(command, prop)    
        
    def serverinfo(self):
        print "server-info >>> "
        url = '%s/update' % (self.service)
        return self._operation(url, {})
        
    def shuffle(self):
        return self.setproperty( 'dacp.shufflestate', '1')
        
    def repeat(self):
        return self.setproperty( 'dacp.repeatstate', '2')
        
    def updatecallback(self):
        event = eventman()
        event.remote = self
        event.start()
        print "Launched thread"



if __name__ == "__main__":
    conn = remote()











