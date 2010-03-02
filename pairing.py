#!/usr/bin/python -i

import socket
import struct 


def send(clientsocket): 
    rcv = clientsocket.recv(1000)
    print rcv
    """
    GET /pair?pairingcode=75D809650423A40091193AA4944D1FBD&servicename=985461928A772733 HTTP/1.1
    Host: 192.168.1.8:1024
    User-Agent: iTunes/9.0.3 (Macintosh; Intel Mac OS X 10.6.2) AppleWebKit/531.21.8
    Accept-Encoding: gzip
    Connection: close
    """

    
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
    
    http_headers = """HTTP/1.0 200 OK
Date: Fri, 31 Dec 1999 23:59:59 GMT
Content-Type: text/html
Content-Length: %s

""" % len(encoded)

    print http_headers
    clientsocket.send( http_headers )
    clientsocket.send(encoded) 
    return 


import select
import sys
import pybonjour

"""
<?xml version="1.0" standalone='no'?>
<!--*-nxml-*--> 
<!DOCTYPE service-group SYSTEM "avahi-service.dtd"> 
<service-group>  
	<name>0000000000000000000000000000000000000001</name>  
	<service>  
		<type>_touch-remote._tcp</type>  
		<port>1024</port>  
		<txt-record>DvNm=Android remote</txt-record>  
		<txt-record>RemV=10000</txt-record>  
		<txt-record>DvTy=iPod</txt-record>  
		<txt-record>RemN=Remote</txt-record>  
		<txt-record>txtvers=1</txt-record>  
		<txt-record>Pair=0000000000000001</txt-record>  
	</service> 
</service-group> 
"""


name    = '0000000000000001'
regtype = '_touch-remote._tcp'
port    = 1024

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

sdRef = pybonjour.DNSServiceRegister(name = name,
                                     regtype = regtype,
                                     port = port, txtRecord = txtrecord,
                                     callBack = register_callback)


if __name__ == "__main__":
    poll_interval = 0.5
    
    try:
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.bind((socket.gethostname(), port))
        serversocket.listen(5)
        
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
    
