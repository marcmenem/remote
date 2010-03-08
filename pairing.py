#!/usr/bin/python -i

import socket
import struct 
import re
import select
import sys
import pybonjour
import datetime


__macos__ = sys.platform == 'darwin'

name    = '0000000000000001'
passcode = '1234'

regtype = '_touch-remote._tcp'
poll_interval = None
    
import pairing_code

def serverConnexion(clientsocket): 
    rcv = clientsocket.recv(1024)
    """
    GET /pair?pairingcode=75D809650423A40091193AA4944D1FBD&servicename=985461928A772733 HTTP/1.1
    Host: 192.168.1.8:1024
    User-Agent: iTunes/9.0.3 (Macintosh; Intel Mac OS X 10.6.2) AppleWebKit/531.21.8
    Accept-Encoding: gzip
    Connection: close
    """

    ua = re.compile("User-Agent: (.*)")
    co = re.compile("GET.*?=([A-F0-9]*)&.*?=([A-F0-9]*)")
    
    for l in rcv.split('\n'):
        m = ua.match(l)
        n = co.match(l)
        if m:
            useragent = m.group(1)
            print "Request from", useragent
        if n:
            pairingcode = n.group(1)
            servicename = n.group(2)
            print "Pairing code", pairingcode, "service name", servicename
    
    expected = pairing_code.itunes_pairingcode(passcode, name)
    print "Expected", pairing_code.to_hex(expected)
    
    # any incoming requests are just pairing code related 
    # return our guid regardless of input 
    values = { 
        'cmpg': '\x00\x00\x00\x00\x00\x00\x00\x01',
        'cmnm': 'devicename', 
        'cmty': 'ipod', } 
    encoded = '' 

    for key, value in values.iteritems(): 
        encoded += '%s%s%s' % (key, struct.pack('>i', len(value)), value) 
    header = 'cmpa%s' % (struct.pack('>i', len(encoded))) 
    encoded = '%s%s' % (header, encoded) 
    
    "Fri, 31 Dec 1999 23:59:59 GMT"
    dt = datetime.datetime.today().strftime('%a, %d %b %Y %H:%M:%S %Z')
    
    http_headers = """HTTP/1.0 200 OK
Date: %s
Content-Type: text/html
Content-Length: %s

""" % (dt ,len(encoded))

    print http_headers, values
    clientsocket.send( http_headers )
    clientsocket.send(encoded) 
    clientsocket.close()
    return 




def register_callback(sdRef, flags, errorCode, name, regtype, domain):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        print 'Registered service:'
        print '  name    =', name
        print '  regtype =', regtype
        print '  domain  =', domain


data = {
    "DvNm" : "Marc Remote",
    "RemV" : "10000",
    "DvTy" : "computer",
    "RemN" : "Remote",
    "Pair" : name ,
    "txtvers" : "1"
   }


def startserver(port):
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((socket.gethostname(), port))
    serversocket.listen(5)
    return serversocket
    
def bonjoursocket(port):
    sdRef = pybonjour.DNSServiceRegister(name = name,
                                 regtype = regtype,
                                 port = port, txtRecord = pybonjour.TXTRecord(data),
                                 callBack = register_callback)
    return sdRef


if __name__ == "__main__":
    

    try:
        port    = 10024
        connected = False
        maxtries = 12
        tried = 0
        
        while not connected and tried < maxtries:
            print "Creating server on port", port
            tried += 1
            try:
                serversocket = startserver(port) 
                readfrom = [serversocket]
                connected = True
            except socket.error, e:
                if e.errno == 48:
                    port += 1
                    print "Address already in use, trying port", port 
                else:
                    print "Unknown error"
                    raise
        
        if __macos__:
            print "Using pybonjour"
            sdRef = bonjoursocket( port )
            readfrom.append(sdRef)
        else:
            print "Using avahi"
            import avahi
            from ZeroconfService import ZeroconfService
            service = ZeroconfService(name=name, port=port, stype=regtype, text=avahi.dict_to_txt_array(data))
            service.publish()
        
            
    
        while True:
            ready_to_read, w, in_error = select.select(readfrom, [], [], poll_interval)
            
            if len(ready_to_read) > 0:
                print "Finally something to do"
                
                if __macos__ and (sdRef in ready_to_read):
                    pybonjour.DNSServiceProcessResult(sdRef)
                elif serversocket in ready_to_read:
                    (clientsocket, address) = serversocket.accept()
                    serverConnexion(clientsocket)
        
                else:
                    print ready_to_read
    finally:
        if __macos__:
            sdRef.close()
        else:
            service.unpublish()
        serversocket.close() 
    
