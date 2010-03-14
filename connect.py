#!/usr/bin/python -i
#Copyright (C) 2010 Marc Menem

#This file is part of Remote. Remote is free software: you can
#redistribute it and/or modify it under the terms of the GNU General
#Public License as published by the Free Software Foundation, either
#version 3 of the License, or (at your option) any later version.

#Remote is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with Remote. If not, see <http://www.gnu.org/licenses/>.

"""
Ugly class

"""


import select, socket, sys, threading

__macosx__ = sys.platform == 'darwin'

regtype  = '_touch-able._tcp'
timeout  = 5
itunesClients = {}



data = []


if __macosx__:
    import pybonjour
    
    def txtRec( tr ):
        tr = pybonjour.TXTRecord.parse(tr)
        d = {}
        for k in tr: 
            d[ k[0] ] = k[1]
        return d
    
    def query_record_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                              rrtype, rrclass, rdata, ttl):
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            for it in itunesClients.values():
                if it.query_sdRef == sdRef:
                    it.queried( rdata )
                    it.show()
                    return
            
    
    def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                         hosttarget, port, txtRecord):
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            it = itunesClients[fullname.split(".")[0]]
            it.resolved( hosttarget, fullname, port, txtRecord )
    
            it.query_sdRef = pybonjour.DNSServiceQueryRecord( interfaceIndex = interfaceIndex,
                                fullname = hosttarget, rrtype = pybonjour.kDNSServiceType_A,
                                callBack = query_record_callback)
            
    
    def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                        regtype, replyDomain):
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return
    
        if flags & pybonjour.kDNSServiceFlagsAdd:
            it = itunes( interfaceIndex, serviceName, replyDomain )
            itunesClients[ serviceName ] = it
    
            it.resolve_sdRef = pybonjour.DNSServiceResolve( 0, interfaceIndex, serviceName,
                                regtype, replyDomain, resolve_callback)
    
            
        else:
            print 'Service removed', interfaceIndex, serviceName, replyDomain
            it = itunesClients[ serviceName ]
            it.closeConnexions()
            del itunesClients[serviceName]
    
        
    loop = True

    def populateITunes():
        browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype, callBack = browse_callback)
        loop = True
        
        try:
            try:
                while loop:
    
                    timeout = None
                    socks = [browse_sdRef]
                    processing = []
                    for client in itunesClients.values():
                        extra = client.sockets()
                        if extra:
                            processing.append( client )
                            socks.extend(extra)
                            timeout = 5
                    
                    ready, w, e = select.select(socks, [], [], timeout)
                    
                    if len(ready) == 0:
                        # Remove timed out clients
                        for client in processing:
                            client.closeConnexions()
                            del itunesClients[client.serviceName]
                    
                    for sock in ready:
                        pybonjour.DNSServiceProcessResult(sock)
        
            except KeyboardInterrupt:
                pass
        finally:
            browse_sdRef.close()
            for client in itunesClients.values(): client.closeConnexions()    
    
    
    
    class browse(threading.Thread):
        def __init__(self):
            super(browse, self).__init__()
            self.setDaemon(True)
    
        def run(self):
            populateITunes()



else:
    import dbus, gobject, avahi
    from dbus import DBusException
    from dbus.mainloop.glib import DBusGMainLoop


    def txtRec( tr ):
        out = {}
        
        for dp in tr:
            if hasattr( dp, 'signature' ):
                d = "".join( [chr( i.real ) for i in dp] )
                d = d.split("=")
                out[d[0]] = d[1]
                
            else:
                print ">>>>>", dp
            
        return out

    
    def service_resolved(*args):
        print 'service resolved'
        print 'name:', args[2]
        print 'address:', args[7]
        print 'port:', args[8]
        print 'hostname:', args[5]
        
        txtRecord = args[9]
        
        it = itunesClients[args[2].decode() ]
        fn = args[2].decode()  + "." + regtype + "." + "local."
        it.resolved( args[5].decode() , fn, args[8].real , txtRecord )
        it.ip = args[7].decode() 
        it.show()
      
    def print_error(*args):
        print 'error_handler'
        print args[0]
        
        
    def myhandler(interface, protocol, name, stype, domain, flags):
        print "+++ Found service '%s' type '%s' domain '%s' " % (name, stype, domain)
        it = itunes( interface.real, name.decode() , domain.decode()  )
        itunesClients[ name.decode()  ] = it
         
        server.ResolveService(interface, protocol, name , stype, 
                domain, avahi.PROTO_UNSPEC, dbus.UInt32(0), 
                reply_handler=service_resolved, error_handler=print_error)

    
    
    def myhandler_rem(interface, protocol, name, stype, domain, flags):
        print "--- Removed service '%s' type '%s' domain '%s' \n" % (name, stype, domain)
        it = itunesClients[ name.decode() ]
        del itunesClients[name.decode() ]


    loop = DBusGMainLoop()
    
    bus = dbus.SystemBus(mainloop=loop)
    
    server = dbus.Interface( bus.get_object(avahi.DBUS_NAME, '/'),
            'org.freedesktop.Avahi.Server')
    
    sbrowser = dbus.Interface(bus.get_object(avahi.DBUS_NAME,
            server.ServiceBrowserNew(avahi.IF_UNSPEC,
                avahi.PROTO_UNSPEC, regtype, 'local', dbus.UInt32(0))),
            avahi.DBUS_INTERFACE_SERVICE_BROWSER)
    
    sbrowser.connect_to_signal("ItemNew", myhandler)
    sbrowser.connect_to_signal("ItemRemove", myhandler_rem)





class itunes:
    def __init__(self, interfaceIndex, serviceName, replyDomain):
                                
        self.interfaceIndex = interfaceIndex
        self.serviceName = serviceName
        self.replyDomain = replyDomain
        self.isresolved = False
        self.isqueried = False
    
        print 'Service added; resolving', interfaceIndex, serviceName, replyDomain
        
        
        
    def sockets(self):
        if not self.isresolved: return [self.resolve_sdRef]
        if not self.isqueried: return [self.query_sdRef]
    
    def resolved(self, hosttarget, fullname, port, txtRecord):
        self.isresolved = True
        self.fullname = fullname
        self.hosttarget = hosttarget
        self.port = port
        self.txtRecord = txtRec( txtRecord )
        
        if self.txtRecord.has_key('CtlN'):  self.dbName = self.txtRecord['CtlN']
        if self.txtRecord.has_key('DbId'):  self.dbId = self.txtRecord['DbId']
        
        if __macosx__:
            self.resolve_sdRef.close()
            self.resolve_sdRef = None
        
    def queried(self, rdata):
        self.isqueried = True
        self.ip = socket.inet_ntoa(rdata)

        if __macosx__:
            self.query_sdRef.close()
            self.query_sdRef = None

    def show(self):
        print 'Resolved service:'
        print '  fullname   =', self.fullname
        print '  hosttarget =', self.hosttarget
        print '  port       =', self.port  
        print '  IP         =', self.ip  
        
        for k in self.txtRecord.keys(): print k, '=', self.txtRecord[ k ]


    def closeConnexions(self):
        if __macosx__:
            if self.resolve_sdRef: self.resolve_sdRef.close()
            if self.query_sdRef: self.query_sdRef.close()
        


if __name__ == "__main__":

    if __macosx__:
        browse().start()
    else:
        loop2 = gobject.MainLoop()
        loop2.run()        
        
