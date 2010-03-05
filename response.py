#!/usr/bin/python -i

import urllib
import urllib2
import struct
import sys, re

import decode
import remotecontrol

LISTENERS = {}
BRANCHES = ["cmst", "mlog", "agal", "mlcl", "mshl", "mlit", "abro", "abar", 
                "apso", "caci", "avdb", "cmgt", "aply", "adbs", "casp", "mdcl", 'mupd', 
                "msrv", "msml", 'cacr', 'mccr', 'arsv']
STRINGS = ["minm", "cann", "cana", "cang", "canl", "asaa", "asal", "asar"]


class speakerset:
    def __init__(self):
        pass


class albumlist:
    def __init__(self):
        self.list = []

class artistlist:
    def __init__(self):
        self.list = []
        
class songlist:
    def __init__(self):
        self.list = []
        
class album:
    def __init__(self):
        pass

class song:
    def __init__(self):
        pass

class sort:
    def __init__(self):
        pass

class status:
    def __init__(self):
        self.unknown = []

    def ok(self):
        return hasattr(self,'artist') and hasattr(self,'album') and hasattr(self,'track') and hasattr(self,'genre')
    
    def show(self):
        if( self.ok() ):
            print "Album:\t", self.album
            print "Artist:\t", self.artist
            print "Track:\t", self.track
            print "Genre:\t", self.genre
            print "Playing:\t", self.playstatus
            if self.playstatus >2:
                print "Time:\t", self.time
                print "Total:\t", self.totaltime
            print "Revision:\t", self.revisionnumber
            
class playlist:
    def __init__(self):
        self.lists = []
        self.unknown = []
    
    def addplaylist(self, pl):
        if pl.library:
            self.library = pl
        self.lists.append( pl )

    def show(self):
        for l in self.lists:
            print l.name, l.nbtracks

class playlistelem:
    def __init__(self):
        self.library = False
        self.unknown = []


class parser:
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
        
        #print ">>>>", st, len(st), len(data)
        if length == 8:
            return struct.unpack('>Q',st)[0], data
        if length == 4:
            return struct.unpack('>I',st)[0], data
        if length == 2:
            return struct.unpack('>H',st)[0], data
        if length == 1:
            return ord(st), data
        
    def _getkey(self, data):
        #try:
        key, data = self._readString(data, 4)
        length, data = self._readInt(data)
        return key, length, data
        
    def _decode2(self, d):
        a = []
        for i in range(len(d)):
            a.append(d[i])
        return decode.decode( a, len(d), 0)
        
    def _processunk( self, key, length, data, obj, verbose=True ):
        if key in STRINGS:
            tmp, data = self._readString( data, length )
        elif (length == 1 or length == 2 or length == 4 or length == 0):
            tmp, data = self._readInteger( data, length )
        else:
            tmp, data = self._readString( data, length )

        if (verbose): print "Unknown key", key, tmp
        if obj: obj.unknown.append(tmp)
        
        return data
    
    def _sortdatalistener( self, data, length, obj):
        obj.letters = []
        while length > 8:
            key, l2, data = self._getkey( data )
            length -= 8 + l2
            sr = sort()
            obj.letters.append(sr)
                        
            while l2 > 8:
                key, l3, data = self._getkey( data )
                l2 -= 8 + l3
                            
                if key == 'mshc':
                    letter, data = self._readString( data, l3 )  
                    sr.sortletter = letter[1]
                elif key == 'mshi':
                    sr.unknown1mshi, data = self._readInteger( data, l3 )  
                elif key == 'mshn':
                    sr.nbelemsthisletter, data = self._readInteger( data, l3 )  
                else:
                    print 'ERROR', key
                    
        return data                           
    
    

"""
 aply  --+
        mstt   4      200
        muty   1      0
        mtco   4      35
        mrco   4      35
        mlcl  --+
                mlit  --+
                        miid   4      28402
                        mper   8      10976505473824925494
                        minm   35     Bibli
                        abpl   1      1
                        mpco   4      0
                        meds   4      0
                        mimc   4      12843
                mlit  --+
                        miid   4      44156
                        mper   8      10976505473824925504
                        minm   7      Musique #(Musique)
                        aeSP   1      1
                        mpco   4      0
                        aePS   1      6
                        meds   4      0
                        mimc   4      12682
"""
class playlistlistener(parser):
    def __init__(self):
        self._playlistparser = playlistparser()
        
    def parse(self, data, handle):
        st = playlist()
                
        while handle > 8:
            key, length, data = self._getkey( data )
            handle -= 8 + length
            
            if key == 'mstt':
                tmp, data = self._readInteger( data, length ) # ok status ?
            elif key == 'mtco':
                st.nbplaylists1, data = self._readInteger( data, length )  
            elif key == 'mrco':
                st.nbplaylists1, data = self._readInteger( data, length )  
            elif key == 'mlcl':
                while length > 8:
                    key, l2, data = self._getkey( data )
                    length -= 8 + l2
                    if (key == 'mlit'):
                        elem, data = self._playlistparser.parse( data, l2 )  
                        st.addplaylist(elem)
                    else:
                        print 'ERROR parsing playlists'
            else:
                data = self._processunk( key, length, data, st, False )
                
        return st        



class playlistparser(parser):
    def __init__(self):
        pass
        
    def parse(self, data, handle):
        st = playlistelem()
        
        while handle > 8:
            key, length, data = self._getkey( data )
            handle -= 8 + length
            
            if key == 'miid':
                st.id, data = self._readInteger( data, length ) 
            elif key == 'mper':
                st.permanentid, data = self._readInteger( data, length )  
            elif key == 'minm':
                st.name, data = self._readString( data, length )  
                #print ">>>", st.name
            elif key == 'mimc':
                st.nbtracks, data = self._readInteger( data, length )  
            elif key == 'ascn':
                st.geniusartiststyle, data = self._readString( data, length )  
            elif key == 'abpl':
                tmp, data = self._readInteger( data, length )  
                st.library = True
            elif key == 'aeSP':
                tmp, data = self._readInteger( data, length )  
                st.auto = True

            else:
                data = self._processunk( key, length, data, st, False )
            
        return st, data


"""
casp  --+
    mstt   4      200
    mdcl  --+
        minm   10     Ordinateur #(Ordinateur)
        msma   8      0
    mdcl  --+
        caia   1      1
        minm   8      4713424192092923251 #(AirTunes)
        msma   8      154081533644
"""
class speakerslistener(parser):
    def __init__(self):
        pass
        
    def parse(self, data, handle):
        st = []
        
        while handle > 8:
            key, length, data = self._getkey( data )
            handle -= 8 + length
            
            if key == 'mdcl':
                spk = speakerset()
                st.append(spk)
                spk.playing = False
                while length > 8:
                    key, l2, data = self._getkey( data )
                    length -= 8 + l2
                    if key == 'minm':
                        spk.name, data = self._readString( data, l2 )  
                    elif key == 'msma':
                        spk.id, data = self._readInteger( data, l2 )  
                    elif key == 'caia':
                        on, data = self._readInteger( data, l2 )  
                        spk.playing = True
                    else:
                        print 'ERROR parsing speakers'
            elif key == 'mstt':
                tmp, data = self._readInteger( data, length )  
            
            else:
                data = self._processunk( key, length, data, None, False )
            
        return st                



class albumslistener(parser):
    def __init__(self):
        pass
        
    def parse(self, data, handle):
        st = albumlist()
        
        while handle > 8:
            key, length, data = self._getkey( data )
            handle -= 8 + length
            
            if key == 'mtco':
                st.totnb, data = self._readInteger( data, length )  
            elif key == 'mrco':
                st.nb, data = self._readInteger( data, length )  
            elif key == 'mlcl':
                
                while length > 8:
                    key, l2, data = self._getkey( data )
                    length -= 8 + l2
                    al = album()
                    st.list.append(al)

                    while l2 > 8:
                        key, l3, data = self._getkey( data )
                        l2 -= 8 + l3
                    
                        if key == 'minm':
                            al.name, data = self._readString( data, l3 )  
                        elif key == 'miid':
                            al.id, data = self._readInteger( data, l3 )  
                        elif key == 'mper':
                            al.permid, data = self._readInteger( data, l3 )  
                        elif key == 'mimc':
                            al.nbtracks, data = self._readInteger( data, l3 )  
                        elif key == 'asaa':
                            al.artist, data = self._readString( data, l3 )  
                        else:
                            print 'ERROR', key
                
                        
            elif key == 'mshl':
                data = self._sortdatalistener(data, length, st)
            
            elif key == 'mstt':
                tmp, data = self._readInteger( data, length )  
            
            else:
                data = self._processunk( key, length, data, None, False )
            
        return st                

        

class songslistener(parser):
    def __init__(self):
        pass
        
    def parse(self, data, handle):
        st = songlist()
        
        while handle > 8:
            key, length, data = self._getkey( data )
            handle -= 8 + length
            
            if key == 'mtco':
                st.totnb, data = self._readInteger( data, length )  
            elif key == 'mrco':
                st.nb, data = self._readInteger( data, length )  
            elif key == 'mlcl':
                
                while length > 8:
                    key, l2, data = self._getkey( data )
                    length -= 8 + l2
                    al = song()
                    st.list.append(al)

                    while l2 > 8:
                        key, l3, data = self._getkey( data )
                        l2 -= 8 + l3
                    
                        if key == 'minm':
                            al.name, data = self._readString( data, l3 )  
                        elif key == 'miid':
                            al.id, data = self._readInteger( data, l3 )  
                        elif key == 'mikd':
                            al.unkown_mikd, data = self._readInteger( data, l3 )  
                        elif key == 'mimc':
                            al.nbtracks, data = self._readInteger( data, l3 )  
                        elif key == 'aeHV':   # has video ?
                            al.unknown_aeHV, data = self._readString( data, l3 ) 
                        else:
                            print 'ERROR', key
                
                        
            elif key == 'mshl':
                data = self._sortdatalistener(data, length, st)
            
            elif key == 'mstt':
                tmp, data = self._readInteger( data, length )  
            
            else:
                data = self._processunk( key, length, data, None, False )
            
        return st                



class artistslistener(parser):
    def __init__(self):
        pass
        
    def parse(self, data, handle):
        st = artistlist()
        
        while handle > 8:
            key, length, data = self._getkey( data )
            handle -= 8 + length
            
            if key == 'mtco':
                st.totnb, data = self._readInteger( data, length )  
            elif key == 'mrco':
                st.nb, data = self._readInteger( data, length )  
            elif key == 'abar':
                while length > 8:
                    key, l2, data = self._getkey( data )
                    length -= 8 + l2
                    
                    if key == 'mlit':
                        name, data = self._readString( data, l2 )  
                        st.list.append(name)
                    else:
                        print 'ERROR', key
                    
            elif key == 'mshl':
                data = self._sortdatalistener(data, length, st)
            elif key == 'mstt':
                tmp, data = self._readInteger( data, length )  
            
            else:
                data = self._processunk( key, length, data, None, False )
            
        return st                

     

  

class playstatuslistener(parser):
    def __init__(self):
        pass
        
    def parse(self, data, handle):
        st = status()
        
        while handle > 8:
            key, length, data = self._getkey( data )
            handle -= 8 + length
            
            if key == 'cann':
                st.track, data = self._readString( data, length )
            elif key == 'cana':
                st.artist, data = self._readString( data, length )
            elif key == 'canl':
                st.album, data = self._readString( data, length )
            elif key == 'cant':
                st.time, data = self._readInteger( data, length )
            elif key == 'cast':
                st.totaltime, data = self._readInteger( data, length )
            elif key == 'cang':
                st.genre, data = self._readString( data, length )
            elif key == 'cmsr':
                st.revisionnumber, data = self._readInteger( data, length )
            elif key == 'caps':
                st.playstatus, data = self._readInteger( data, length ) # 4=playing, 3=paused
            elif key == 'cash':
                st.shuffle, data = self._readInteger( data, length ) #shuffle status: 0=off, 1=on 
            elif key == 'carp':
                st.repeat, data = self._readInteger( data, length ) # repeat status: 0=none, 1=single, 2=all 
            elif key == 'asai':
                st.albumid, data = self._readInteger( data, length )  
            elif key == 'mstt':
                tmp, data = self._readInteger( data, length )  
            
            else:
                data = self._processunk( key, length, data, st, False )
            
        return st                


LISTENERS['casp'] = speakerslistener()
LISTENERS['cmst'] = playstatuslistener()
LISTENERS['aply'] = playlistlistener()
LISTENERS['agal'] = albumslistener()
LISTENERS['abro'] = artistslistener()
LISTENERS['apso'] = songslistener()


class response(parser):
    def __init__(self, data):
        self.resp = self.parse( data, len(data) )


    def parse(self, data, handle):
        resp = {}
        progress = 0
        
        while( handle > 0):
            key, length, data = self._getkey( data )
            #print key, length, data
            
            handle -= 8 + length
            progress += 8 + length
            
            if resp.has_key(key):
                nicekey = "%s[%06d]" % (key, progress)
            else:
                nicekey = key
                
            if key in LISTENERS:
                listener = LISTENERS[key]
                resp[nicekey] = listener.parse( data, length )
                data = data[length:]
                
            elif key in BRANCHES:
            
                if key == 'abar': BRANCHES.remove('mlit') ## wtf ?'
                branch = self.parse( data, length ) #listener, listenFor, length )
                if key == 'abar': BRANCHES.append('mlit') ## wtf ?'
                
                data = data[length:]
                resp[nicekey] = branch
    
            elif key in STRINGS:
                resp[nicekey], data = self._readString( data, length )
            elif (length == 1 or length == 4 or length == 2):
                resp[nicekey], data = self._readInteger( data, length )
            elif (length == 0):
                resp[nicekey] = None
            else:
                resp[nicekey], data = self._readString( data, length )

        return resp



if __name__ == "__main__":
    conn = remotecontrol.remote()

    status = conn.status()
    obj = response( status )











