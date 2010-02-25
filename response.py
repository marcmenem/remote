#!/usr/bin/python -i

import urllib
import urllib2
import struct
import sys, re

import decode
import remotecontrol


BRANCHES = ["cmst", "mlog", "agal", "mlcl", "mshl", "mlit", "abro", "abar", 
				"apso", "caci", "avdb", "cmgt", "aply", "adbs", "casp", "mdcl"]
STRINGS = ["minm", "cann", "cana", "cang", "canl", "asaa", "asal", "asar"]



class response:
	def __init__(self, data):
		self.resp = self.parse( data, len(data) )

	def _readString(self, data, length):
		st = data[0:length]
		data = data[length:]
		return st, data
		
		
	def _readInt(self, data):
		st = data[0:4]
		data = data[4:]
		return struct.unpack('>I',st)[0], data
		
		
	def _readInteger(self, data, length):
		st = data[0:length]
		data = data[length:]
		if length == 4:
			return struct.unpack('>I',st)[0], data
		if length == 2:
			return struct.unpack('>B',st)[0], data
		if length == 1:
			return ord(st), data
		
		
		
	def parse(self, data, handle):
		resp = {}
		progress = 0
		
		while( handle > 0):
			key, data = self._readString(data, 4)
			length, data = self._readInt(data)
			
			#print key, length
			
			handle -= 8 + length
			progress += 8 + length
			
			if resp.has_key(key):
				nicekey = "%s[%06d]" % (key, progress)
			else:
				nicekey = key
				
			if key in BRANCHES:
				branch = self.parse( data, length ) #listener, listenFor, length )
				data = data[length:]
				resp[nicekey] = branch
	
			elif key in STRINGS:
				resp[nicekey], data = self._readString( data, length )
			elif (length == 1 or length == 2 or length == 4 or length == 0):
				resp[nicekey], data = self._readInteger( data, length )
			else:
				resp[nicekey], data = self._readString( data, length )

		return resp



if __name__ == "__main__":
	conn = remotecontrol.remote()

	status = conn.status()
	obj = response( status )











