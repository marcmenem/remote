#!/usr/bin/python -i

import socket
import struct 
import re
import select
import sys
import pybonjour
import datetime

def send(clientsocket): 
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
        if n:
            pairingcode = n.group(1)
            servicename = n.group(2)
    
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



name    = '0000000000000001'
regtype = '_touch-remote._tcp'

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
txtrecord = pybonjour.TXTRecord(data)



def register_services(port):
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((socket.gethostname(), port))
    serversocket.listen(5)
    
    sdRef = pybonjour.DNSServiceRegister(name = name,
                                 regtype = regtype,
                                 port = port, txtRecord = txtrecord,
                                 callBack = register_callback)

    return serversocket, sdRef

if __name__ == "__main__":
    poll_interval = 0.5
    
    try:
        port    = 1024
        connected = False
        
        while not connected:
            try:
                serversocket, sdRef = register_services( port )
                connected = True
            except socket.error, e:
                if e.errno == 48:
                    port += 1
                    print "Address already in use, trying port", port 
                else:
                    print "Unknown error"
                    raise
        
        while True:
            ready_to_read, w, in_error = select.select([serversocket, sdRef], [], [], poll_interval)
            
            if len(ready_to_read) > 0:
                if sdRef in ready_to_read:
                    pybonjour.DNSServiceProcessResult(sdRef)
                
                elif serversocket in ready_to_read:
                    (clientsocket, address) = serversocket.accept()
                    send(clientsocket)
        
                else:
                    print ready_to_read
    finally:
        sdRef.close()
        serversocket.close() 
    
