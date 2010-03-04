#!/usr/bin/python -i

import select
import socket
import sys
import pybonjour


regtype  = '_touch-able._tcp'
timeout  = 5
itunesClients = {}


class itunes:
    def __init__(self, interfaceIndex, serviceName, replyDomain):
                                
        self.interfaceIndex = interfaceIndex
        self.serviceName = serviceName
        self.replyDomain = replyDomain
        self.isresolved = False
        self.isqueried = False
    
        print 'Service added; resolving', interfaceIndex, serviceName, replyDomain
        
        self.resolve_sdRef = pybonjour.DNSServiceResolve(
                                0,
                                interfaceIndex,
                                serviceName,
                                regtype,
                                replyDomain,
                                resolve_callback)
    
        
    def sockets(self):
        if not self.isresolved: return [self.resolve_sdRef]
        if not self.isqueried: return [self.query_sdRef]
    
    def resolved(self, hosttarget, fullname, port):
        self.isresolved = True
        self.query_sdRef = pybonjour.DNSServiceQueryRecord(
                                        interfaceIndex = self.interfaceIndex,
                                        fullname = hosttarget,
                                        rrtype = pybonjour.kDNSServiceType_A,
                                        callBack = query_record_callback)
        self.fullname = fullname
        self.hosttarget = hosttarget
        self.port = port
        self.resolve_sdRef.close()
        self.resolve_sdRef = None
        
    def queried(self, rdata):
        self.isqueried = True
        self.ip = socket.inet_ntoa(rdata)
        self.query_sdRef.close()
        self.query_sdRef = None

    def show(self):
        print 'Resolved service:'
        print '  fullname   =', self.fullname
        print '  hosttarget =', self.hosttarget
        print '  port       =', self.port  
        print '  IP         =', self.ip  

    def closeConnexions(self):
        if self.resolve_sdRef: self.resolve_sdRef.close()
        if self.query_sdRef: self.query_sdRef.close()
        


def query_record_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                          rrtype, rrclass, rdata, ttl):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        #it = itunesClients[fullname.split(".")[0]]
        it = itunesClients.values()[0]
        print "FIXME"
        it.queried( rdata )
        it.show()
        

def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        it = itunesClients[fullname.split(".")[0]]
        it.resolved( hosttarget, fullname, port )


def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                    regtype, replyDomain):
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    if flags & pybonjour.kDNSServiceFlagsAdd:
        it = itunes( interfaceIndex, serviceName, replyDomain )
        itunesClients[ serviceName ] = it
        resolve_sdRef = it.resolve_sdRef
    else:
        print 'Service removed', interfaceIndex, serviceName, replyDomain
        it= itunesClients[ serviceName ]
        it.closeConnexions()
        del itunesClients[serviceName]

    
def populateITunes():
    browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype, callBack = browse_callback)
    
    try:
        try:
            while True:

                timeout = None
                socks = [browse_sdRef]
                for client in itunesClients.values():
                    extra = client.sockets()
                    if extra:
                        socks.extend(extra)
                        timeout = 5
                
                ready, w, e = select.select(socks, [], [], timeout)
                
                if len(ready) == 0:
                    print "Resolve timed out"
                    #need to remove timed out clients
                
                for sock in ready:
                    pybonjour.DNSServiceProcessResult(sock)
    
        except KeyboardInterrupt:
            pass
    finally:
        browse_sdRef.close()
        for client in itunesClients.values(): client.closeConnexions()    
    

if __name__ == "__main__":
    populateITunes()
    
    
    