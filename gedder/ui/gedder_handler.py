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

# Show menu in application window, not on the top of Ubuntu desktop
os.environ['UBUNTU_MENUPROXY']='0'
LOG = logging.getLogger(__name__)

class Handler:

    def __init__(self, run_args, get_transform):
        ''' Prepare Glade UI '''
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
        fn = run_args['parishfile']
        if fn:
            bu = self.builder.get_object('parishfile_chooser')
            bu.set_filename(fn)
        fn = run_args['villagefile']
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
        # Redraw file info on page 0
        if page_num == 0:
            self.show_fileInfo()
        
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
        #TODO: peru muutokset kopioimalla viimeisin talletettu syöte uusimmaksi
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
        except FileNotFoundError:
            position = self.textbuffer.get_end_iter()
            self.textbuffer.insert_with_tags(position,"Ei tulostiedostoa " + _LOGFILE, e_tag)
        except Exception as e:
            position = self.textbuffer.get_end_iter()
            self.textbuffer.insert_with_tags(position,"Virhe {!r}".format(str(e), e_tag))
        finally:
            f.close()

    def on_displaystate_close(self, *args):
        ''' Suljetaan lokitiedosto-ikkuna '''
        self.disp_window.destroy()

    def on_combo_encoding_changed(self, combo):
        ''' Set input gedcom file encoding and show file info '''
        global run_args
        treeiter = combo.get_active_iter()
        model = combo.get_model()
        value = (model[treeiter][0])
        #value = combo.get_active_text()
        self.run_args['encoding'] = value
        self.st.push(self.st_id, "Valittu merkistö " + value)
        self.show_fileInfo()
    
    def on_combo_logging_changed(self, combo):
        ''' #TODO: Set loggind level '''
        value = combo.get_active_id()
        self.loglevel = int(value)
#         LOG.setLevel(int(value))
        self.st.push(self.st_id, "Lokitaso " + logging.getLevelName(value))

    def on_checkbutton_toggled(self, checkButton):
        ''' Fire checkbutton change: #TODO: what to do? '''
        self.st.push(self.st_id, "Painettu: " + checkButton.get_label())
        rev = self.builder.get_object("revertButton")
        rev.set_sensitive(False)
        
    def on_fileInfo_show(self, label):
        ''' Not in use? '''
        print(str(label))

    def on_inputFilechooser_file_set(self, button):
        ''' The user has selected a file '''
        name = button.get_filename()
        if name:
            self.input_gedcom = name
            self.run_args['input_gedcom'] = self.input_gedcom
            self.message_id = self.st.push(self.st_id, "Syöte " + self.input_gedcom)
            self.activate_run_button()
            self.show_fileInfo()
 
    def on_file_open_activate(self, menuitem, data=None):
        ''' Prepare file chooser for .ged input files '''
        self.dialog = Gtk.FileChooserDialog("Open...",
            self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
            )
        self.response = self.dialog.run()
        if self.response == Gtk.ResponseType.OK:
            self.input_gedcom = self.dialog.get_filename()
            self.run_args['input_gedcom'] = self.input_gedcom
            self.message_id = self.st.push(self.st_id, "Syöte " + self.input_gedcom)
            self.activate_run_button()
            self.dialog.destroy()
        else:
            self.st.push(self.st_id, "Outo palaute {}".format(self.response))

    def show_fileInfo(self):
        ''' Read gedcom HEAD info and display it '''
        combo = self.builder.get_object("combo_encoding")
        enc = combo.get_active_text()
        info = self.builder.get_object("fileInfo")
        if not self.input_gedcom:
            info.set_text("Valitse tiedosto")
            return
        
        msg = []
        msg.append(os.path.basename(self.input_gedcom) + '\n\n')
        try:
            with open(self.input_gedcom, 'r', encoding=enc) as f:
                for _ in range(100):
                    ln = f.readline()
                    if ln[:6] in ['2 VERS', '1 NAME', '1 CHAR']:
                        msg.append(ln[2:])
                    if ln.startswith('1 SOUR'):
                        msg.append('Source ' + ln[7:-1] + ' ')
                    if ln.startswith('1 GEDC'):
                        msg.append('Gedcom ')
                    if ln.startswith('2 CONT _COMMAND'):
                        msg.append('– ' + ln[16:-1])
                    if ln.startswith('2 CONT _DATE'):
                        msg.append(ln[13:])
                    if match('0.*SUBM', ln):
                        msg.append('Submitter ')
                    if match('0.*INDI', ln):
                        break
        except UnicodeDecodeError as e:
            msg.append("Väärä merkistö, kokeile toisella")
        except Exception as e:
            msg.append( type(e).__name__ + str(e))
        info.set_text( ''.join(msg))
                
    def activate_run_button(self):
        ''' If file and operation are choosen '''
        runb = self.builder.get_object("runButton")
        if self.input_gedcom and self.transformer: 
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

