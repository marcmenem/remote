#!/usr/bin/python

import select
import socket
import sys
import pybonjour


regtype  = '_touch-able._tcp'
timeout  = 5

class itunes:
    def __init__(self, interfaceIndex, serviceName, replyDomain):
                                
        self.interfaceIndex = interfaceIndex
        self.serviceName = serviceName
        self.replyDomain = replyDomain
        
        print 'Service added; resolving', interfaceIndex, serviceName, replyDomain
        
        resolve_sdRef = pybonjour.DNSServiceResolve(
                                0,
                                interfaceIndex,
                                serviceName,
                                regtype,
                                replyDomain,
                                resolve_callback)
    
        self.resolve_sdRef = resolve_sdRef
    
    def resolved(self, hosttarget, fullname):
        query_sdRef = pybonjour.DNSServiceQueryRecord(
                                        interfaceIndex = self.interfaceIndex,
                                        fullname = hosttarget,
                                        rrtype = pybonjour.kDNSServiceType_A,
                                        callBack = query_record_callback)
        self.query_sdRef = query_sdRef
        self.fullname = fullname
        
        
    def queried(self, rdata):
        self.ip = socket.inet_ntoa(rdata)
        

    def show(self):
        print 'Resolved service:'
        print '  fullname   =', self.fullname
        print '  hosttarget =', self.hosttarget
        print '  port       =', self.port  
        print '  IP         =', self.ip  



itunesClients = {}

resolvers = []
queriers  = []



def query_record_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                          rrtype, rrclass, rdata, ttl):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        it = itunesClients[interfaceIndex]
        it.queried( rdata )
        it.show()
        

def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    it = itunesClients[interfaceIndex]
    it.resolved( hosttarget, fullname )
    queriers.append(it.query_sdRef)


def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                    regtype, replyDomain):
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    if not (flags & pybonjour.kDNSServiceFlagsAdd):
        print 'Service removed', interfaceIndex, serviceName, replyDomain
        return

    it = itunes(  interfaceIndex, serviceName, replyDomain)
    itunesClients[ interfaceIndex ] = it
    resolve_sdRef = it.resolve_sdRef
    resolvers.append(resolve_sdRef)



if __name__ == "__main__":
    browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype,
                                              callBack = browse_callback)
    
    
    try:
        try:
            while True:
                socks = [browse_sdRef]
                socks.extend(queriers)
                socks.extend(resolvers)

                if len(socks) > 1: 
                    timeout = 5
                else:
                    timeout = None
                ready, w, e = select.select(socks, [], [], timeout)
                
                if len(ready) == 0:
                    print "Resolve timed out"
                
                for sock in ready:
                    pybonjour.DNSServiceProcessResult(sock)
                    if sock in resolvers:
                        resolvers.remove( sock )
                    if sock in queriers:
                        queriers.remove( sock )
                
    
        except KeyboardInterrupt:
            pass
    finally:
        browse_sdRef.close()
