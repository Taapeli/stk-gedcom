#
# Gedcom cleaner application window
# 12.12.2016 / Juha Mäkeläinen
#

import os 
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import importlib
import logging
from argparse import Namespace

from ui.gedder_handler import Handler
#import gedcom_transform
_LOGFILE="transform.log"
transformer = None

# Show menu in application window, not on the top of Ubuntu desktop
os.environ['UBUNTU_MENUPROXY']='0'
LOG = logging.getLogger(__name__)
run_args = Namespace(# Global options
                     input_gedcom=None, 
                     output_gedcom=None, 
                     display_changes=False, 
                     dryrun=False, 
                     nolog=False, 
                     encoding='utf-8',
                     # places options
                     reverse=False, 
                     add_commas=False, 
                     ignore_lowercase=False, 
                     display_nonchanges=False,
                     ignore_digits=False, 
                     minlen=0, 
                     auto_order=False, 
                     auto_combine=False, 
                     match='', 
                     parishfile="static/seurakunnat.txt", 
                     villagefile="static/seurakunnat.txt")


def get_transform(name):
    ''' Return the transform module and it's description from "transforms" package 
        if name == "marriages", a tranformer module "transforms.marriages" is imported
    '''
    global transformer

    filename = "transforms/" + name + ".py"
    if os.path.exists(filename):
        transformer = importlib.import_module("transforms."+name)
        doc = transformer.__doc__
        if doc:
            docline = doc.strip().splitlines()[0]
        else:
            docline = ""
        version = getattr(transformer, "version", "")
        return (transformer, version, docline)
    return (None, None, "Missing file")


if __name__ == "__main__":
    ''' Run Gedder.glade 
    TODO: with arguments from command line '''
    
    main = Handler(run_args, get_transform)
    Gtk.main()
