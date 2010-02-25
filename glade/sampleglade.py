#!/usr/bin/python
# vim: set fileencoding=utf-8

import pygtk
pygtk.require( "2.0" )
import gtk

class Sample:
    def gtk_main_quit( self, window ):
        gtk.main_quit()

    def cb_delete_event( self, window, event ):
        # Run dialog
        response = self.quit_dialog.run()
        self.quit_dialog.hide()

        return response != 1

    def cb_show_about( self, button ):
        # Run dialog
        self.about_dialog.run()
        self.about_dialog.hide()

    def __init__( self ):
        builder = gtk.Builder()
        builder.add_from_file( "sample.glade" )
        
        self.window       = builder.get_object( "window1" )
        self.about_dialog = builder.get_object( "aboutdialog1" )
        self.quit_dialog  = builder.get_object( "dialog1" )

        builder.connect_signals( self )

if __name__ == "__main__":
    win = Sample()
    win.window.show_all()
    gtk.main()

