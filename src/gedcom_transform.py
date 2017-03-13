#!/usr/bin/env python3

"""
Generic GEDCOM transformer 
Kari Kujansuu, 2016.

The transforms are specified by separate Python modules ("plugins") in the subdirectory "transforms".

Parameters of main():
 1. The name of the plugin. This can be the name of the Python file ("module.py")
    or just the name of the module ("module").
    In both case the .py file must be in the current directory or on the PYTHONPATH.

 2. The name of the input GEDCOM file. This is also the name of the output file.

 3. "--encoding" [optional] specifies the character encoding used to read and write
    the GEDCOM files. The default is UTF-8.

 4. "--display_changes" [optional] can be specified to allow the plugins to
    show the modification. The plugin must implement the logic to do that.

 5. "--dryrun" [optional] means that no changes are saved and the input file is not modified.

If the --dryrun parameter is not specified then the original input file is
renamed by adding a sequence number to the file name and the new version of
the file is saved with the same name as the input file. These names are displayed at the
end of the program.

A plugin may contain the following functions:

- add_args(parser)
- initialize(args)                              # Called once in the beginning of the transformation
- phase1(args,line,level,path,tag,value)        # [optional] called once per GEDCOM line
- phase2(args)                                  # [optional] called between phase1 and phase2
- phase3(args,line,level,path,tag,value,output_file)
                                                # [optional] called once per GEDCOM line

The function "add_args" is called in the beginning of the program and it allows
the plugin to add its own arguments for the program. The values of the arguments
are stored in the "args" object that is passed to the other functions.

Function "initialize" is called in the beginning of the transformation.

If function "phase1" is defined, it is called once for each line in the input GEDCOM file.
It can be used to collect information to be used in the subsequent phases.

Function "phase2" may be defined for processing all the information got from phase1
before phase3.

Function "phase3" is called once for each line in the input GEDCOM file.
This function should produce the output GEDCOM by calling output_file.emit()
for each line in the output file.
If an input line is not modified then emit should be called with the original line
as it's parameter.

The parameters of each phases:
- "args" is the object returned by ArgumentParser.parse_args.
- "gedline", a GedcomLine() object, which includes
    - "line", the original line in the input GEDCOM (unicode string)
    - "level", the level number of the line (integer)
    - "path", the current hierarchy of the GEDCOM tags, e.g @I123@.BIRT.DATE
      representing the DATE tag inside the BIRT tag for the individual @I123@.
    - "tag", the current tag (last part of path)
    - "value", the value for the current tag, e.g. a date or a name
- "output_file" is a file-like object containing the method emit(string) that is used to produce the output

"""
_VERSION="0.3"
_LOGFILE="transform.log"

import sys
import os
import argparse
import importlib
import datetime
import logging
LOG = logging.getLogger(__name__)

from classes.gedcom_line import GedcomLine
from classes.ged_output import Output

def numeric(s):
    return s.replace(".","").isdigit()


def read_gedcom(args):
    
    try:
        for linenum, line in enumerate(open(args.input_gedcom, encoding=args.encoding)):
            # Clean the line
            line = line[:-1]
            if line[0] == "\ufeff": 
                line = line[1:]
            # Return a gedcom line object
            gedline = GedcomLine(line, linenum)
            yield gedline

    except FileNotFoundError:
        LOG.error("Tiedostoa '{}' ei ole!".format(args.input_gedcom))
        raise
    except Exception as err:
        LOG.error(type(err))
        LOG.error("Virhe: {0}".format(err))


def process_gedcom(args, transformer, task_name=''):

    LOG.info("------ Ajo '%s'   alkoi %s ------", \
             task_name, \
             datetime.datetime.now().strftime('%a %Y-%m-%d %H:%M:%S'))

    transformer.initialize(args)

    try:
        # 1st traverse
        if hasattr(transformer,"phase1"):
            for gedline in read_gedcom(args):
                transformer.phase1(args, gedline)
    
        # Intermediate processing of collected data
        if hasattr(transformer,"phase2"):
            transformer.phase2(args)
    
        do_phase4 = hasattr(transformer,"phase4")
    
        # 2nd traverse "phase3"
        with Output(args) as f:
            f.display_changes = args.display_changes
            for gedline in read_gedcom(args):
                if do_phase4 and gedline.tag == "TRLR":
                    f.original_line = ""
                    transformer.phase4(args, f)
                f.original_line = gedline.line.strip()
                transformer.phase3(args, gedline, f)
    except FileNotFoundError as err:
        LOG.error("Ohjelma päättyi virheeseen: {}".format(err))

    LOG.info("------ Ajo '%s' päättyi %s ------", \
             task_name, \
             datetime.datetime.now().strftime('%a %Y-%m-%d %H:%M:%S'))



def get_transforms():
    # all transform modules should be .py files in the package/subdirectory "transforms"
    for name in os.listdir("transforms"):
        if name.endswith(".py") and name != "__init__.py": 
            modname = name[0:-3]
            transformer = importlib.import_module("transforms."+modname)
            doc = transformer.__doc__
            if doc:
                docline = doc.strip().splitlines()[0]
            else:
                docline = ""
            version = getattr(transformer,"version","")
            yield (modname,transformer,docline,version)


def find_transform(prefix):
    choices = []
    for modname,transformer,docline,version in get_transforms():
        if modname == prefix: return transformer
        if modname.startswith(prefix):
            choices.append((modname,transformer))
    if len(choices) == 1: return choices[0][1]
    if len(choices) > 1: 
        LOG.error("Ambiguous transform name: {}".format(prefix))
        LOG.error("Matching names: {}".format(",".join(name for name,t in choices)))
    return False


def init_log():
    ''' Define log file and save one previous log '''
    try:
        if os.open(_LOGFILE, os.O_RDONLY):
            os.rename(_LOGFILE, _LOGFILE + '~')
    except:
        pass
    logging.basicConfig(filename=_LOGFILE,level=logging.INFO, format='%(levelname)s:%(message)s')


def main():
    print("\nTaapeli GEDCOM transform program A (version {})\n".format(_VERSION))
    print("Lokitiedot: {!r}".format(_LOGFILE))
    init_log()

    parser = argparse.ArgumentParser()
    parser.add_argument('transform', help="Name of the transform (Python module)")
    parser.add_argument('input_gedcom', help="Name of the input GEDCOM file")
    parser.add_argument('--output_gedcom', help="Name of the output GEDCOM file; this file will be created/overwritten" )
    parser.add_argument('--display-changes', action='store_true',
                        help='Display changed rows')
    parser.add_argument('--dryrun', action='store_true',
                        help='Do not produce an output file')
    parser.add_argument('--nolog', action='store_true',
                        help='Do not produce a log in the output file')
    #parser.add_argument('--display-nonchanges', action='store_true',
    #                    help='Display unchanged places')
    parser.add_argument('--encoding', type=str, default="utf-8",
                        help="e.g, UTF-8, ISO8859-1")
    parser.add_argument('-l', '--list', action='store_true', help="List transforms")

    if len(sys.argv) > 1 and sys.argv[1] in ("-l","--list"):
        print("List of transforms:")
        for modname,transformer,docline,version in get_transforms():
            print("  {:20.20} {:10.10} {}".format(modname,version,docline))
        return

    if len(sys.argv) > 1 and sys.argv[1][0] == '-' and sys.argv[1] not in ("-h","--help"):
        print("First argument must be the name of the transform")
        return

    if len(sys.argv) > 1 and sys.argv[1][0] != '-':
        task_name = sys.argv[1]
        transformer = find_transform(task_name)
        if not transformer: 
            print("Transform not found; use -l to list the available transforms")
            return
        transformer.add_args(parser)

    args = parser.parse_args()

    process_gedcom(args, transformer, task_name)

if __name__ == "__main__":
    main()
