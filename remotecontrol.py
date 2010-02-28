#!/usr/bin/python -i

import urllib
import urllib2
import struct
import sys, re

import decode
import response

def _encode( values ):
    st = '&'.join([ str(k) + '=' + str(values[k]) for k in values ])
    return st.replace(' ', "%20")


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
		self._decode2( data )
		
		resp = response.response(data)		
		self.sessionid = resp.resp['mlog']['mlid']
	
		print "Got session id", self.sessionid
		self.databases()
		pl = self.playlists()
		self.musicid = pl.library.id
		
		return resp
	
	"""

       
       /databases/41/groups?session-id=1131893462&
       meta=dmap.itemname,dmap.itemid,dmap.persistentid,daap.songartist&
       type=music&
       group-type=albums&
       sort=album&
       include-sort-headers=1&
       index=0-7&
       query=(('com.apple.itunes.mediakind:1',
        'com.apple.itunes.mediakind:4',
        'com.apple.itunes.mediakind:8',
        'com.apple.itunes.mediakind:2097152',
        'com.apple.itunes.mediakind:2097156')+
        'daap.songalbum:*V*'+'daap.songalbum!:')
       
       
       """

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

	    resp = self._operation( command, values, True )
        
	    return resp

	"""

    http.request.uri == "/databases/41/browse/artists?
    session-id=1131893462&
    include-sort-headers=1&
    filter=('com.apple.itunes.mediakind:1','com.apple.itunes.mediakind:4',
    'com.apple.itunes.mediakind:8','com.apple.itunes.mediakind:2097152',
    'com.apple.itunes.mediakind:2097156')+
    'daap.songartist!:'+'daap.songartist:*Va*'&index=0-7"
    
    """
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

	    resp = self._operation( command, values, True )
        
	    return resp
       
        
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
	    mediakind = [2,6,36,32,64,2097154,2097158]
	    qt = ",".join( [ "'com.apple.itunes.mediakind:" + str(mk) + "'" for mk in mediakind])
	    query="((" + qt + ")+'daap.itemname:*" + q + "*')"

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
        
	    return resp

    


	def _decode2(self, d):
		a = []
		for i in range(len(d)):
			a.append(d[i])
		r = decode.decode( a, len(d), 0)
		print "--+ :)"
		return r
		
	
	def skip(self):
		print "skip >>> "
		return self._ctloperation('nextitem', {})	
		
	def prev(self):
		print "prev >>> "
		return self._ctloperation('previtem', {})	
		
	def play(self):
		print "play >>> "
		return self._ctloperation('playpause', {})	
		
	def pause(self):
		print "pause >>> "
		return self._ctloperation('pause', {})	
		
	def getspeakers(self):
		print "speakers >>> "
		spk = self._ctloperation('getspeakers', {}, False)	
		return spk['casp']
		
	def setspeakers(self, spkid):
		print "setspeakers >>> "
		values = {'speaker-id': spkid }
		return self._ctloperation('setspeakers', values)	
		
		
		
	def showStatus(self, verbose=False):
		#print "status >>> "
		values = {'revision-number': '1' }
		status = self._ctloperation('playstatusupdate', values, verbose)	
		status = status['cmst']
		status.show()
		return status
		
	"""
	And we can seek in the track, where dacp.playingtime is the seek destination in milliseconds:

    http://192.168.254.128:3689/ctrl-int/1/setproperty?dacp.playingtime=82784&session-id=1686799903

"""
		
	def setproperty(self, prop, val):
		print "setproperty >>> "
		values = {prop: val }
		return self._ctloperation('setproperty', values)	
		
	def getproperty(self, prop ):
		print "getproperty >>> "
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
		
	def serverinfo(self, prop ):
		print "server-info >>> "
		values = {prop: val }
		command = '%s/update' % (self.service)
		return self._operation(command, prop)	
		
		
	def shuffle(self):
		return self.setproperty( 'dacp.shufflestate', '1')
		
	def repeat(self):
		return self.setproperty( 'dacp.repeatstate', '2')
		
	def volume(self, value):
		return self.setproperty( 'dmcp.volume', value)
		



if __name__ == "__main__":
	conn = remote()











