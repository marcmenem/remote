#!/usr/bin/python -i
# vim: set fileencoding=utf-8

import pygtk
pygtk.require( "2.0" )
import gtk
import gtk.gdk
import gobject

import remotecontrol
import threading 
import config

class searcher(threading.Thread):
    def __init__(self, win):
        super(searcher, self).__init__()
        self.win = win
        #self.working = False
        
    def run(self):
        #while self.working:
        #    time.sleep(0.1)

        print "Searching", self.value
        #self.working = True
        res = self.win.remote.query(self.value)
        #self.working = False
        gobject.idle_add(self.win.reset_search, res)


class listener(threading.Thread):
    def __init__(self, win):
        super(listener, self).__init__()
        self.win = win
        self.do = True
        self.setDaemon(1) # avoid lock on exit
        
    def run(self):
        while self.do:
            print "Waiting server events"
            st = self.win.remote.showStatus( self.win.remote.nextupdate )
            gobject.idle_add(self.win.update_status, st)


def timerepr(t1):
	min = t1 / ( 60000 )
	sec = (t1 - 60000*min)/1000
	return "%0d:%02d" % (min, sec)

class Remote:
    def gtk_main_quit( self, window ):
        gtk.main_quit()
        
    def searchchanged(self, window):
        s = searcher(self)
        s.value = self.entry.get_text()
        s.start()

        
    def reset_search(self, res):
        print "Reset search"   
        try:
            while self.searchresults.remove(self.searchresults.get_iter_first()):
                pass
        except:
            pass
            
        albums = self.searchresults.append(None)
        if albums:
            self.searchresults.set_value( albums, 0, 'Albums' )
            self.searchresults.set_value( albums, 1, str(res.albums.totnb) )
            for pl in res.albums.list:
                row = self.searchresults.append(albums)
                self.searchresults.set_value( row, 0, pl.name )
    
    
        artists = self.searchresults.append(None)
        if artists:
            self.searchresults.set_value( artists, 0, 'Artist' )
            self.searchresults.set_value( artists, 1, str(res.artists.totnb) )
            for pl in res.artists.list:
                row = self.searchresults.append(artists)
                self.searchresults.set_value( row, 0, pl )

        tracks = self.searchresults.append(None)
        if tracks:
            self.searchresults.set_value( tracks, 0, 'Songs' )
            self.searchresults.set_value( tracks, 1, str(res.tracks.totnb) )
            for pl in res.tracks.list:
                row = self.searchresults.append(tracks)
                self.searchresults.set_value( row, 0, pl.name )
        
        
    def volumerelease(self, window):
        volume = 50  #FIXME
        print "FIXME"
        self.remote.setvolume(volume)
        self.update_volume()
    
    def update_volume(self):
        volume = self.remote.getvolume()
        #FIXME
        
    def trackseek(self, window):
        print "trackseek", window
        

    def nextitem(self, window):
        self.remote.skip()
        
    def play(self, window):
        self.remote.play()
        
    def previtem(self, window):
        self.remote.prev()

    def cb_delete_event( self, window, event ):
        # Run dialog
        response = self.quit_dialog.run()
        self.quit_dialog.hide()
        
        if response != 1:
            self.ui_updater.do = False
            return True

        return False 

    def cb_show_about( self, button ):
        # Run dialog
        self.about_dialog.run()
        self.about_dialog.hide()

    def update_status(self, status = None):
        if not status: status = self.remote.showStatus()
        if status.ok():
            self.track.set_label(status.track)
            self.artist.set_label(status.artist)
            #self.album.set_label(status.album)
            #self.genre.set_label(status.genre)
            
            self.playstatus = status.playstatus
            if status.playstatus > 2:
                if hasattr(self.remote,'artwork') and self.remote.artwork:
                    print "Updating artwork"
                    pb = gtk.gdk.PixbufLoader()
                    pb.write(self.remote.artwork)
                    pb.close()
                    self.image.set_from_pixbuf(pb.get_pixbuf())
                    
                else:
                    print "Missing artwork"
                
            	self.totaltime = status.totaltime
            	self.timepos = status.time
                self.position.set_upper(self.totaltime)
                self.update_time( self )
            else:
                self.time.set_label(timerepr( 0 ))
                self.timeremain.set_label(timerepr( 0 ))
             
        else:
            self.track.set_label("")
            self.artist.set_label("")
            #self.album.set_label("")
            #self.genre.set_label("")
        
            self.time.set_label(timerepr( 0 ))
            self.timeremain.set_label(timerepr( 0 ))
             
        
    def update_time(self, obj):
        self.waiting = False
        
        if self.timepos < 0:
        	self.update_status()
        else:
            self.time.set_label(timerepr( self.totaltime - self.timepos ))
            self.timeremain.set_label(timerepr( self.totaltime ))
                
            self.position.set_value(self.totaltime - self.timepos)
            
            if self.playstatus == 4 and not self.waiting:
                self.timepos -= 250
                self.timer = gobject.timeout_add( 250, self.update_time, self)
                self.waiting = True 
            else:
                print "Not scheduling timer"

    def update_speakers(self):
        print "Speakers"
        speakers = self.remote.getspeakers()
        try:
            while self.speakerslist.remove(self.speakerslist.get_iter_first()):
                pass
        except:
            pass
            
        for spk in speakers:
        	row = self.speakerslist.append()
        	self.speakerslist.set_value(row, 0, spk.name)
        
        
    def update_playlists(self):
        try:
            while self.playlists.remove(self.playlists.get_iter_first()):
                pass
        except:
            pass
            
        for pl in self.remote.playlists_cache.lists:
            row = self.playlists.append()
            self.playlists.set_value( row, 0, pl.name )
            self.playlists.set_value( row, 1, pl.nbtracks )

    def __init__( self ):
        builder = gtk.Builder()
        builder.add_from_file( "glade/remote.glade" )
        self.builder = builder
        
        self.window       = builder.get_object( "window2" )
        self.about_dialog = builder.get_object( "aboutdialog1" )
        self.quit_dialog  = builder.get_object( "dialog1" )
        
        self.track = builder.get_object("Track")
        self.artist = builder.get_object("Artist")
        self.time = builder.get_object("time")
        self.timeremain = builder.get_object("timeremain")

        self.searchresults = builder.get_object("treestore1")
        self.speakers = builder.get_object("combobox1")
        self.position = builder.get_object("adjustment1")
        
        self.playlists = builder.get_object("liststore1")
        self.speakerslist = builder.get_object("liststore2")
        self.entry = builder.get_object("entry1")
        
        self.image = builder.get_object("image1")
                
        builder.connect_signals( self )
        
        config.connect.postHook = self.connectRC


    def connectRC(self):
        print "Connecting remote"
        self.remote = remotecontrol.connectRC(update = False)
        self.update_speakers()
        self.update_status()
        self.update_playlists()
        
        # thread helpers
        self.ui_updater = listener(self)
        self.ui_updater.start()
        
        # self.searcher = searcher(self)
        
if __name__ == "__main__":

    win = Remote()
    win.window.show_all()
    gobject.threads_init()

    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()


