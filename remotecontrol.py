#!/usr/bin/python -i

import urllib
import urllib2
import struct
import sys, re

import decode
import response

def _encode( values ):
	return '&'.join([ str(k) + '=' + str(values[k]) for k in values ])

class remote:
	def __init__(self):
		self.guid="0x0000000000000001"
		self.service = 'http://192.168.1.8:3689'
		self.sessionid = None
		
		self.musicid = 44197  # FIXME magic "music" playlist

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
		resp = self._operation( command, {} )
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

		resp = self._operation( command, values )
		return resp

	def pairing(self):
		url = '%s/login?pairing-guid=%s' % (self.service, self.guid)

		data = urllib2.urlopen( url ).read()
		self._decode2( data )
		
		resp = response.response(data)		
		self.sessionid = resp.resp['mlog']['mlid']
	
		print "Got session id", self.sessionid
		self.databases()
		self.playlists()
		
		return resp
	
	"""


      // fetch playlists to find the overall magic "Music" playlist
      Response playlists = RequestHelper.requestParsed(String.format(
               "%s/databases/%d/containers?session-id=%s&
               
               meta=dmap.itemname,dmap.itemcount,dmap.itemid,dmap.persistentid,daap.baseplaylist,com.apple.itunes.special-playlist,com.apple.itunes.smart-playlist,com.apple.itunes.saved-genius,dmap.parentcontainerid,dmap.editcommandssupported", this
                        .getRequestBase(), this.databaseId, this.sessionId), false);

      for (Response resp : playlists.getNested("aply").getNested("mlcl").findArray("mlit")) {
         String name = resp.getString("minm");
         if (name.equals("Music")) {
            this.musicId = resp.getNumberLong("miid");
            break;
         }
      }
      Log.d(TAG, String.format("found music-id=%s", this.musicId));


       
       """



	def _decode2(self, d):
		a = []
		for i in range(len(d)):
			a.append(d[i])
		return decode.decode( a, len(d), 0)

	
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
		return self._ctloperation('getspeakers', {})	
		
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
		
	def setproperty(self, prop, val):
		print "setproperty >>> "
		values = {prop: val }
		return self._ctloperation('playstatusupdate', values)	
		
	def getproperty(self, prop ):
		print "getproperty >>> "
		values = {prop: val }
		return self._ctloperation('property', prop)	
		
		
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
		


	def search( self, search, start, end):
		
		querytype = "('com.apple.itunes.mediakind:1','com.apple.itunes.mediakind:4','com.apple.itunes.mediakind:8')"
		query = "(" + querytype + "+('dmap.itemname:*%s*','daap.songartist:*%s*','daap.songalbum:*%s*'))" % (search, search, search)
		
		values = { 
			"meta": 'dmap.itemname,dmap.itemid,daap.songartist,daap.songalbum',
			"type": 'music',
			"include-sort-headers": '1',
			"query": query,
			"sort": "name",
			"index": ("%d-%d" % (start,end)),
			'session-id': self.sessionid
		}
		
		command = "%s/databases/%d/containers/%d/items" % (self.service, self.databaseid, self.musicid)	
		resp = self._operation( command, values )
		return resp

	def tracks( self, albumid):	
		values = { 
			"meta": 'dmap.itemname,dmap.itemid,daap.songartist,daap.songalbum,daap.songalbum,daap.songtime,daap.songtracknumber',
			"type": 'music',
			"include-sort-headers": '1',
			"query": ('daap.songalnbumid:%s' % albumid),
			"sort": "album",
			'session-id': self.sessionid
		}
		
		command = "%s/databases/%d/containers/%d/items" % (self.service, self.databaseid, self.musicid)
		resp = self._operation( command, values )
		return resp

	def albums( self, start, end):
		values = { 
			"meta": 'dmap.itemname,dmap.itemid,dmap.persistentid,daap.songartist',
			"type": 'music',
			"group-type": "albums",
			"include-sort-headers": '1',
			"sort": "artist",
			"index": ("%d-%d" % (start,end)),
			'session-id': self.sessionid
		}
		
		command = "%s/databases/%d/containers/%d/items" % (self.service, self.databaseid, self.musicid)
		resp = self._operation( command, values )
		return resp




if __name__ == "__main__":
	conn = remote()











