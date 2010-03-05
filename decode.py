#!/usr/bim/python
# simple message decoder for dacp
# released gplv3 by jeffrey sharkey

import sys, struct, re
import response

from daap_data import *

def format(c):
	if ord(c) >= 128: return "(byte)0x%02x"%ord(c)
	else: return "0x%02x"%ord(c)


def read(queue, size):
	pull = ''.join(queue[0:size])
	del queue[0:size]
	return pull

group = response.BRANCHES

#['casp', 'cmst','mlog','agal','mlcl','mshl','abro','mlit',
#	'abar','apso','caci','avdb','cmgt','aply','adbs','cmpa', 'mdcl', 'mupd', 'mstt', 'msrv']

rebinary = re.compile('[^\x20-\x7e]')

#def ashex(s): return ''.join([ "%02x" % ord(c) for c in s ])
def ashex(s): return ''.join(s)

def asbyte(s): return struct.unpack('>B', s)[0]
def asint(s): return struct.unpack('>I', s)[0]
def as2b(s): return struct.unpack('>H', s)[0]
def aslong(s): return struct.unpack('>Q', s)[0]


def decode(raw, handle, indent):
	while handle >= 8:
		
		# read word data type and length
		ptype = read(raw, 4)
		plen = asint(read(raw, 4))
		handle -= 8 + plen
		
		#print ptype, raw[0:10], plen, handle
		
		# recurse into groups
		if ptype in group:
			if ptype == 'abar': group.remove('mlit') ## wtf ?
			print '\t' * indent, ptype, " --+"
			decode(raw, plen, indent + 1)
			if ptype == 'abar': group.append('mlit')
			continue
		
		# read and parse data
		pdata = read(raw, plen)
		
		nice = '%s' % ashex(pdata)
		#if plen == 1: nice = '%s == %s' % (ashex(pdata), asbyte(pdata))
		#if plen == 4: nice = '%s == %s' % (ashex(pdata), asint(pdata))
		#if plen == 8: nice = '%s == %s' % (ashex(pdata), aslong(pdata))
		
		try:
			if plen == 1: nice = '%s' % (asbyte(pdata))
			if plen == 2: nice = '%s' % (as2b(pdata))
			if plen == 4: nice = '%s' % (asint(pdata))
			if plen == 8: nice = '%s' % (aslong(pdata))
		
			if rebinary.search(pdata) is None:
				nice += ' #(%s)' % (pdata)
		except:
			nice = 'ERROR'
		
		key = ptype
		if key in dmapCodeTypes:
		    key += " (%s)" % dmapCodeTypes[key][0]
		print '\t' * indent, key.ljust(30), str(plen).ljust(6), nice


if __name__ == "__main__":

	raw = []

	#for c in raw_input(): raw.append(c)
	#raw.append('\x0a')

	for c in sys.stdin.read(): raw.append(c)
	
	
	print ','.join([ format(c) for c in raw ])
	
	decode(raw, len(raw), 0)



