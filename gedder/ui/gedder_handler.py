'''
Gedder.py UI for running gedcom transform programs

Uses global variables:
    _LOGFILE="transform.log"
    LOG = logging.getLogger(__name__)
    run_args = Namespace(# Global options
                 output_gedcom=None, display_changes=False, dryrun=False, nolog=False, encoding='utf-8',
                 # places options
                 reverse=False, add_commas=False, ignore_lowercase=False, display_nonchanges=False,
                 ignore_digits=False, minlen=0, auto_order=False, auto_combine=False, 
                 match='', parishfile="seurakunnat.txt", villagefile="kylat.txt")

Created on 6.3.2017

@author: Juha Mäkeläinen

'''

import os 
import gi
from re import match
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango, Gdk
import logging
import gedcom_transform

_LOGFILE="transform.log"
input_gedcom = None

# Show menu in application window, not on the top of Ubuntu desktop
os.environ['UBUNTU_MENUPROXY']='0'

LOG = logging.getLogger('gedder')
# run_args = Namespace(# Global options
#                      output_gedcom=None, display_changes=False, dryrun=False, nolog=False, encoding='utf-8',
#                      # places options
#                      reverse=False, add_commas=False, ignore_lowercase=False, display_nonchanges=False,
#                      ignore_digits=False, minlen=0, auto_order=False, auto_combine=False, 
#                      match='', parishfile="seurakunnat.txt", villagefile="kylat.txt")

#global get_transform, run_args

class Handler:

    def __init__(self, run_args, get_transform):
#         global transformer
#         global input_gedcom
#         global run_args
        self.get_transform_func = get_transform
        self.transformer = None
        self.input_gedcom = None
        self.run_args = run_args
        self.loglevel = 20  # INFO

        self.builder = Gtk.Builder()
        self.builder.add_from_file("ui/Gedder.glade")
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("applicationwindow")
        self.aboutdialog = self.builder.get_object("displaystate")
        
        self.st = self.builder.get_object('statusbar1')
        self.st_id = self.st.get_context_id("gedder")
        # Set default files for parishfile_chooser and villagefilechooser
        fn = run_args.parishfile
        if fn:
            bu = self.builder.get_object('parishfile_chooser')
            bu.set_filename(fn)
        fn = run_args.villagefile
        if fn:
            bu = self.builder.get_object('villagefile_chooser')
            bu.set_filename(fn)
        self.message_id = None
        self.window.show()

    def onDeleteWindow(self, *args):
        Gtk.main_quit(*args)
        
    def on_opNotebook_switch_page (self, notebook, page, page_num, data=None):
        ''' Valittu välilehti määrää toiminnon 
        '''
        opers = (None, "names", "places", "marriages", "hiskisources", "kasteet", "lahdeviitteet")
        self.op_selected = None
        
        self.tab = notebook.get_nth_page(page_num)
        self.label = notebook.get_tab_label(self.tab).get_label()
        if page_num < len(opers):
            self.op_selected = opers[page_num]
    
        self.builder.get_object("checkbutton2").set_sensitive(self.op_selected == 'places')

        # Define transformer program and the argumets used
        if self.op_selected:
            self.transformer, vers, doc = self.get_transform_func(self.op_selected)
            if self.transformer: 
                self.message_id = self.st.push(self.st_id, doc + " " + vers)
                self.activate_run_button()
            else:
                self.st.push(self.st_id, "Transform not found; use -l to list the available transforms")
        elif self.message_id:
            self.message_id = self.st.pop(self.message_id)
        
    def on_runButton_clicked(self, button):
        ''' Open log file and run the selected transformation '''
        self.st.push(self.st_id, "{} käynnistyi".format(button.get_label()))
        
        print("Lokitiedot: {!r}".format(_LOGFILE))
        self.init_log()
        disp_cmd = self.op_selected
        gedcom_transform.process_gedcom(self.run_args, self.transformer, task_name=disp_cmd)

        self.st.push(self.st_id, "{} tehty".format(button.get_label()))
#         rev = self.builder.get_object("revertButton")
#         rev.set_sensitive(True)
        ''' Show report '''
        self.on_showButton_clicked(button)
        
    def on_revertButton_clicked(self, button):
        self.st.push(self.st_id, "Painettu: " + button.get_label())
        rev = self.builder.get_object("revertButton")
        rev.set_sensitive(False)

    def on_showButton_clicked(self, button):
        ''' Näytetään luettu lokitiedosto uudessa ikkunassa '''
        self.builder2 = Gtk.Builder()
        self.builder2.add_from_file("ui/displaystate.glade")
        self.builder2.connect_signals(self)
        msg = self.builder2.get_object("msg")
        self.disp_window = self.builder2.get_object("displaystate")
        self.disp_window.set_transient_for(self.window)
        self.disp_window.show()
        self.textbuffer = msg.get_buffer()
        w_tag = self.textbuffer.create_tag( "warning", weight=Pango.Weight.BOLD, 
                                            foreground_rgba=Gdk.RGBA(0, 0, 0.5, 1))
        e_tag = self.textbuffer.create_tag( "error", weight=Pango.Weight.BOLD, 
                                            foreground_rgba=Gdk.RGBA(0.5, 0, 0, 1))
        d_tag = self.textbuffer.create_tag( "debug", #style=Pango.Style.ITALIC, 
                                            foreground_rgba=Gdk.RGBA(0, 0, 0.5, 1))
        msg.modify_font(Pango.FontDescription("Monospace 9"))
        
        # Read logfile and show it's content formatted in self.textview
        try:
            f = open(_LOGFILE, 'r')
            for line in f:
                position = self.textbuffer.get_end_iter()
                if line.startswith("INFO:"):
                    self.textbuffer.insert(position, line[5:])
                elif line.startswith("WARNING:"):
                    self.textbuffer.insert_with_tags(position,line[8:], w_tag)
                elif line.startswith("ERROR:"):
                    self.textbuffer.insert_with_tags(position,line[6:], e_tag)
                else:
                    self.textbuffer.insert_with_tags(position, line.replace('DEBUG:', '', 1), d_tag)
            f.close()
        except FileNotFoundError:
            position = self.textbuffer.get_end_iter()
            self.textbuffer.insert_with_tags(position,"Ei tuloksia näytettävänä", e_tag)
        except Exception as e:
            position = self.textbuffer.get_end_iter()
            self.textbuffer.insert_with_tags(position,"Virhe {!r}".format(str(e), e_tag))

    def on_displaystate_close(self, *args):
        ''' Suljetaan lokitiedosto-ikkuna '''
        self.disp_window.destroy()

    def on_combo_encoding_changed(self, combo):
        global run_args
        value = combo.get_active_text()
        self.run_args.__setattr__('encoding', value)
        self.st.push(self.st_id, "Valittu merkistö " + value)
    
    def on_combo_logging_changed(self, combo):
        value = combo.get_active_id()
        self.loglevel = int(value)
#         LOG.setLevel(int(value))
        self.st.push(self.st_id, "Lokitaso " + logging.getLevelName(value))

    def on_checkbutton_toggled(self, checkButton):
        self.st.push(self.st_id, "Painettu: " + checkButton.get_label())
        rev = self.builder.get_object("revertButton")
        rev.set_sensitive(False)

    def inputFilechooser_set(self, button):
        ''' The user has selected a file '''
        def _get_fileInfo(filename):
            combo = self.builder.get_object("combo_encoding")
            enc = combo.get_active_text()

            try:
                f = open(filename, 'r', encoding=enc)
                msg = []
                for i in range(100):
                    ln = f.readline()
                    if ln.startswith('1 SOUR'):
                        msg.append('Source ')
                    if ln.startswith('2 VERS'):
                        msg.append(ln[2:])
                    if ln.startswith('1 GEDC'):
                        msg.append('Gedcom ')
                    if ln.startswith('1 NAME'):
                        msg.append(ln[2:])
                    if ln.startswith('1 CHAR'):
                        msg.append(ln[2:])
                    if match('0.*SUBM', ln):
                        msg.append('Submitter ')
                    if match('0.*INDI', ln):
                        break
                return ''.join(msg)
            except UnicodeDecodeError as e:
                return "Väärä merkistö, kokeile toisella"
            except Exception as e:
                return type(e).__name__ + str(e)
                
        global input_gedcom
        name = button.get_filename()
        if name:
            input_gedcom = name
            setattr(self.run_args, 'input_gedcom', input_gedcom)
            self.message_id = self.st.push(self.st_id, "Syöte " + input_gedcom)
            info = self.builder.get_object("fileInfo")
            msg = _get_fileInfo(input_gedcom)
            info.set_text(msg)

            self.activate_run_button()
            
 
    def on_file_open_activate(self, menuitem, data=None):
        ''' Same as inputFilechooser_file_set_cb - not actually needed '''
        global input_gedcom
        self.dialog = Gtk.FileChooserDialog("Open...",
            self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
            )
        self.response = self.dialog.run()
        if self.response == Gtk.ResponseType.OK:
            input_gedcom = self.dialog.get_filename()
            setattr(self.run_args, 'input_gedcom', input_gedcom)
            self.message_id = self.st.push(self.st_id, "Syöte " + input_gedcom)
            self.activate_run_button()
            self.dialog.destroy()
        else:
            self.st.push(self.st_id, "Outo palaute {}".format(self.response))

    def activate_run_button(self):
        ''' If file and operation are choosen '''
        global input_gedcom
        runb = self.builder.get_object("runButton")
        if input_gedcom and self.transformer: 
            runb.set_sensitive(True)
        else: 
            runb.set_sensitive(False)

    def init_log(self):
        ''' Define log file and save one previous log '''
        try:
            if os.path.isfile(_LOGFILE):
                os.rename(_LOGFILE, _LOGFILE + '~')
        except:
            pass
        logging.basicConfig(filename=_LOGFILE,level=self.loglevel, format='%(levelname)s:%(message)s')

