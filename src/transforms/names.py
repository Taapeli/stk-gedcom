'''
    Processes gedcom lines trying to fix problems of individual name tags

    The input flow of GedcomLine objects have the following process:
      1. When an INDI line is found, a new GedcomRecord is created
        - The following lines associated to this person are stored in a list in the GedcomRecord:
          - When a "1 NAME" line is found, a new PersonName object is created and the following
            lines associated to this name are stored as a list in the PersonName
          - When all lines of current INDI record (0 INDI and all lower level rows)
            the transformed lines are written to output using GedcomRecord.emit() method.
      2. The other input records (HEAD, FAM etc.) are written out immediately line by line

Created on 26.11.2016

@author: JMä
'''
#     Input example (originally no indent):
#         0 @I0149@ INDI
#           1 NAME Johan Johanpoika /Sihvola/
#             2 TYPE aka
#             2 GIVN Johan Johanpoika
#             2 SURN Sihvola
#           1 NAME Johan /Johansson/
#             2 GIVN Johan
#             2 SURN Johansson
#             2 SOUR @S0015@
#               3 PAGE Aukeama 451, Kuva 289 Sihvola
#               3 DATA
#                 4 DATE 28 JAN 2015
#             3 NOTE @N0175@
#           1 SEX M
#             ...

#from classes.gedcom_line import GedcomLine
from classes.gedcom_record import GedcomRecord
from classes.person_name import PersonName

# Active Indi logical record GedcomRecord
indi_record = None
# state 0 = started, 1 = indi processing, 2 = name processing, 3 = birth processing
state = 0

def initialize(args):
    global indi_record
    global state            
    state = 0
    indi_record = None

def add_args(parser):
    pass


def phase3(args, gedline, f):
    '''
    Function phase3 is called once for each line in the input GEDCOM file.
    This function produce the output GEDCOM by calling output_file.emit() for each line.
    If an input line is not modified then the original lines are emitted as is.

    Arguments example:
        args=Namespace(display_changes=False, dryrun=True, encoding='utf-8', \
                       input_gedcom='../Mun-testi.ged', transform='names')
        gedline=(
            line='1 NAME Antti /Puuhaara/'
            level=1
            path='@I0001@.NAME'
            tag='NAME'
            value='Antti /Puuhaara/'
        )
        f=<__main__.Output object at 0x101960fd0>
    '''

    global logical_record
    global state
    #print("# Phase3: args={!r}, line={!r}, path={!r}, tag={!r}, value={!r}, f={!r}".\
    #      format(args,line,path,tag,value,f))

    ''' 
    ---- INDI automation engine for processing person data ----
         See automation rules below 
         Hei vaan!
    '''

    # For all states
    if gedline.level == 0:
        if gedline.value == 'INDI':  # Start new INDI
            # "0 INDI" starts a new logical record
            _T1_emit_and_start_record(gedline, f)
            state = 1
        else:
            # 0 level line ends previous logical record, if any and
            # starts a non-INDI logical record, which is emitted as is
            _T2_emit_record_and_gedline(gedline, f)
            state = 0
        return
    
    # For all but "0 INDI" lines
    if state == 0:      # Started, no active INDI
        # Lines are emitted as is
        _T3_emit_gedline(gedline, f)
        return

    if state == 1:      # INDI processing active
        if gedline.level == 1:
            if gedline.tag == 'NAME':
                # Start a new PersonName in GedcomRecord
                _T4_store_name(gedline)
                state = 2
                return

            if gedline.tag == 'BIRT':
                state = 3

        # Higher level lines are stored as a new members in the INDI logical record
        _T6_store_member(gedline)
        return
    
    if state == 2:      # NAME processing active in INDI
        if gedline.level == 1:
            # Level 1 lines terminate current NAME group
            if gedline.tag == 'NAME':
                # Start a new PersonName in GedcomRecord
                _T4_store_name(gedline)
                state = 2
                return
            # Other level 1 lines terminate NAME and are stored as INDI members
            if gedline.tag == 'BIRT':
                state = 3
            else:
                state = 1
            _T6_store_member(gedline)
        else:
            # Higher level lines are stored as a new members in the latest NAME group
            _T7_store_name_member(gedline)
        return

    if state == 3:       # BIRT processing (to find birth date) active in INDI
        if gedline.level == 2 and gedline.tag == 'DATE':
            _T5_save_date(gedline,'BIRT')
            state = 1
            return
        if gedline.level == 1:
            if gedline.tag == 'NAME':
                # Start a new PersonName in GedcomRecord
                _T4_store_name(gedline)
                state = 2
            else:
                _T6_store_member(gedline)
                state = 1
            return
        # Level > 1, still waiting DATE
        _T6_store_member(gedline)
        return

'''# ---- Automation rules ----

# !state \ input !! 0 INDI!!0 . . .!! 1 NAME !! 1 BIRT !! 2 DATE !! 2,3,4,...!!1 . . .!! end
# |--------------++-------++-------++--------++--------++--------++----------++-------++-----
# | 0  "Started" || 1,T1  || 0,T3  || 0,T3   || 0,T3   || 0,T3   || 0,T3     || 0,T3  || 0,T2
# | 1  "INDI"    || 1,T1  || 0,T2  || 2,T4   || 3,T6   || 1,T6   || 1,T6     || 1,T6  || 0,T2
# | 2  "NAME"    || 1,T1  || 0,T2  || 2,T4   || 3,T6   || 2,T7   || 2,T7     || 1,T6  || 0,T2
# | 3  "BIRT"    || 1,T1  || 0,T2  || 2,T4   || 1,T6   || 1,T5   || 3,T6     || 1,T6  || 0,T2
 For example rule "2,T4" means operation T4 and new state 2.
'''

def _T1_emit_and_start_record(gedline, f):
    ''' Emit previous logical person record (if any) and create a new one '''
    global indi_record
    if indi_record != None:
        indi_record.emit(f)
    # Create new logical record
    indi_record = GedcomRecord(gedline)

def _T2_emit_record_and_gedline(gedline, f):
    ''' Emit previous logical person record (if any) and emit line '''
    global indi_record
    if indi_record != None:
        indi_record.emit(f)
        indi_record = None
    # Emit current line to output file
    gedline.emit(f)

def _T3_emit_gedline(gedline, f): 
    ''' Emit current line '''
    gedline.emit(f)

def _T4_store_name(gedline):
    ''' Save gedline as a new PersonName to the logical person record '''
    global indi_record
    nm = PersonName(gedline)
    indi_record.add_member(nm)

def _T5_save_date(gedline, tag):
    ''' Pick year from gedline and store current gedline '''
    global indi_record
    indi_record.store_date(gedline.get_year(),tag)
    indi_record.add_member(gedline)
    
def _T6_store_member(gedline):
    ''' Save a new gedline member to the logical record '''
    global indi_record
    indi_record.add_member(gedline)

def _T7_store_name_member(gedline):
    ''' Save current line to the current name object '''
    global indi_record
    indi_record.get_nameobject().add_line(gedline)
