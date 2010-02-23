from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer 
import struct 

class PairingHandler(BaseHTTPRequestHandler): 
	def do_GET(self): 
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

		self.send_response(200) 
		self.end_headers() 
		self.wfile.write(encoded) 
		return 

try: 
	port = 1024 
	server = HTTPServer(('', port), PairingHandler) 

	print 'started server on port %s' % (port) 
	server.serve_forever()

except KeyboardInterrupt: 
	server.socket.close() 
