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
- initialize(run_args)                              # Called once in the beginning of the transformation
- phase1(run_args,line,level,path,tag,value)        # [optional] called once per GEDCOM line
- phase2(run_args)                                  # [optional] called between phase1 and phase2
- phase3(run_args,line,level,path,tag,value,output_file)
                                                # [optional] called once per GEDCOM line

The function "add_args" is called in the beginning of the program and it allows
the plugin to add its own arguments for the program. The values of the arguments
are stored in the "run_args" dictionary that is passed to the other functions.

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
- "run_args"    a dict object from the object returned by ArgumentParser.parse_args 
                or from gedder.py options.
- "gedline",    a GedcomLine() object, which includes
    - "line",   the original line in the input GEDCOM (unicode string)
    - "level",  the level number of the line (integer)
    - "path",   the current hierarchy of the GEDCOM tags, e.g @I123@.BIRT.DATE
                representing the DATE tag inside the BIRT tag for the individual @I123@.
    - "tag",    the current tag (last part of path)
    - "value",  the value for the current tag, e.g. a date or a name
- "output_file" is a file-like object containing the method emit(string) 
                that is used to produce the output
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

from transforms.model.gedcom_line import GedcomLine
from transforms.model.ged_output import Output

# def numeric(s):
#     return s.replace(".","").isdigit()


def read_gedcom(run_args):
    
    try:
        for linenum, line in enumerate(open(run_args['input_gedcom'], encoding=run_args['encoding'])):
            # Clean the line
            line = line[:-1]
            if line[0] == "\ufeff": 
                line = line[1:]
            # Return a gedcom line object
            gedline = GedcomLine(line, linenum)
            yield gedline

    except FileNotFoundError:
        LOG.error("Tiedostoa '{}' ei ole!".format(run_args['input_gedcom']))
        raise
    except Exception as err:
        LOG.error(type(err))
        LOG.error("Virhe: {0}".format(err))


def process_gedcom(run_args, transformer, task_name=''):

    LOG.info("------ Ajo '%s'   alkoi %s ------", \
             task_name, \
             datetime.datetime.now().strftime('%a %Y-%m-%d %H:%M:%S'))

    transformer.initialize(run_args)

    try:
        # 1st traverse
        if hasattr(transformer,"phase1"):
            for gedline in read_gedcom(run_args):
                transformer.phase1(run_args, gedline)
    
        # Intermediate processing of collected data
        if hasattr(transformer,"phase2"):
            transformer.phase2(run_args)
    
        do_phase4 = hasattr(transformer,"phase4")
    
        # 2nd traverse "phase3"
        with Output(run_args) as f:
            f.display_changes = run_args['display_changes']
            for gedline in read_gedcom(run_args):
                if do_phase4 and gedline.tag == "TRLR":
                    f.original_line = ""
                    transformer.phase4(run_args, f)
                f.original_line = gedline.line.strip()
                transformer.phase3(run_args, gedline, f)
    except FileNotFoundError as err:
        LOG.error("Ohjelma päättyi virheeseen {}: {}".format(type(err).__name__, str(err)))

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
            yield (modname, transformer, docline, version)


def find_transform(prefix):
    choices = []
    for modname, transformer, _docline, _version in get_transforms():
        if modname == prefix: 
            return transformer
        if modname.startswith(prefix):
            choices.append((modname, transformer))
    if len(choices) == 1: 
        return choices[0][1]
    if len(choices) > 1: 
        LOG.error("Ambiguous transform name: {}".format(prefix))
        LOG.error("Matching names: {}".format(",".join(name for name, _ in choices)))
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
    parser = argparse.ArgumentParser()
    parser.add_argument('input_gedcom', help="Name of the input GEDCOM file")
    parser.add_argument('-e, --encoding', type=str, default="utf-8",
                        help="e.g, UTF-8, ISO8859-1")
#     run_args = vars(parser.parse_args())

    print("\nTaapeli GEDCOM transform program A (version {})\n".format(_VERSION))

    transformer = None
    run_args = {}
    args = ""
    
    cmd = "-"
    pgm = os.path.basename(__file__)[:-3]
    prompt = pgm + "> "
    sys.stdout.write(prompt)
    sys.stdout.flush()
    
    while True:
        cmd = sys.stdin.readline()[:-1]
        if cmd == '' or cmd == 'loppu':
            break
        s = cmd.split()
        if len(s) == 1:
            ccmd = s[0]; copt = []
        else:
            ccmd = s[0]
            copt = s[1:]
                
        sys.stdout.write("  Komento '{}' opt='{}'\n{}".format(ccmd, copt, prompt))
        #TODO: Kaikkien komentojen toteutus
        
        if ccmd == "aja":
            disp_cmd = "".format(transformer, args)
            process_gedcom(run_args, transformer, task_name=disp_cmd)

    print('\nKiitos')
    

if __name__ == "__main__":
    main()
