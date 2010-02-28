#!/usr/bin/python -i
# vim: set fileencoding=utf-8

import pygtk
pygtk.require( "2.0" )
import gtk

import remotecontrol
import gobject

def timerepr(t1):
	min = t1 / ( 60000 )
	sec = (t1 - 60000*min)/1000
	return "%0d:%02d" % (min, sec)

class Remote:
    def gtk_main_quit( self, window ):
        gtk.main_quit()

    def searchchanged(self, window):
        value = 'Nina' #FIXME
        self.reset_search()
        artists = self.remote.searchartist(value)
        self.add_results("Artists", artists)
        albums = self.remote.searchalbum(value)
        self.add_results("Albums", albums)
        tracks = self.remote.searchtracks(value)
        self.add_results("Tracks", tracks)
        
    def reset_search(self):
        print "Reset search"   
        
    def add_results(self, category, results):
        #FIXME
        print category, results
        
        
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
        self.update_status()
        
    def play(self, window):
        self.remote.play()
        self.update_status()
        
    def previtem(self, window):
        self.remote.prev()
        self.update_status()

    def cb_delete_event( self, window, event ):
        # Run dialog
        response = self.quit_dialog.run()
        self.quit_dialog.hide()

        return response != 1

    def cb_show_about( self, button ):
        # Run dialog
        self.about_dialog.run()
        self.about_dialog.hide()

    def update_status(self):
        status = self.remote.showStatus()
        if status.ok():
            self.track.set_label(status.track)
            self.artist.set_label(status.artist)
            #self.album.set_label(status.album)
            #self.genre.set_label(status.genre)
            
            self.playstatus = status.playstatus
            if status.playstatus > 2:
            	self.totaltime = status.totaltime
            	self.timepos = status.time
                self.position.set_upper(self.totaltime)
                self.update_time( self )
        	
        
    def update_time(self, obj):
        if self.timepos < 0:
        	self.update_status()
        else:        
            self.time.set_label(timerepr( self.totaltime - self.timepos ))
            self.timeremain.set_label(timerepr( self.totaltime ))
                
            self.position.set_value(self.totaltime - self.timepos)
                
            if self.playstatus == 4:
                self.timepos -= 250
                self.timer = gobject.timeout_add( 250, self.update_time, self)
        

    def update_speakers(self):
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
        
        builder.connect_signals( self )

        self.remote = remotecontrol.remote()
        self.update_speakers()
        self.update_status()
        self.update_playlists()
        
        
        
if __name__ == "__main__":
    win = Remote()
    win.window.show_all()
    gtk.main()

