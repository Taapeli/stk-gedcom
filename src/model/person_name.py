'''
Created on 22.11.2016

@author: jm
'''

import re
import logging
LOG = logging.getLogger(__name__)

from classes.gedcom_line import GedcomLine

_NONAME = 'N'            # Marker for missing name part
_CHGTAG = "NOTE _orig_"   # Comment: original format

_UNNAMED = ['nimetön', 'tuntematon', 'N.N.', '?']
_PATRONYME = {'poika':'poika', 'p.':'poika', 'sson':'sson', 'ss.':'sson', 's.':'son',
             'tytär':'tytär', 't.':'tytär', 'dotter':'dotter', 'dr.':'dotter', }
_SURN = {'os.':'avionimi', 'o.s.':'avionimi', 'ent.':'otettu nimi', 'e.':'otettu nimi', \
         '/':'tunnettu myös', ',':'tunnettu myös'}
#_VON = ['von', 'af', 'de', 'la']
_BABY = {"vauva":"U", "poikavauva":"M", "tyttövauva":"F", 
         "poikalapsi":"M", "tyttölapsi":"F", "lapsi":"U",
         "(vauva)":"U", "(poikavauva)":"M", "(tyttövauva)":"F", 
         "(poikalapsi)":"M", "(tyttölapsi)":"F", "(lapsi)":"U"}
#TODO: Lyhenteet myös ruotsiksi

class PersonName(GedcomLine):
    '''
    Stores and fixes Gedcom individual name information.

    The preferred source of information is the '1 NAME givn/surn/nsfx' row.
    If NAME has significant changes, the original value is also written to 
    a 'NOTE _orig_' row.
    
    1. A patronyme in givn part is moved to nsfx part and a new NSFX row is created,
       if needed
    
    2. A missing givn or surn is replaced with noname mark 'N'
    
    3. If surname part has multiple surnames, a new "1 NAME" group is generated
       from each of them
    '''

#     def __str__(self):
#         return "{} NAME {}".format(self.level, self.value)


    def __init__(self, gedline):
        ''' Creates a new instance on person name definition from a '1 NAME' row.
            The arguments must be a NAME gedcom line.
        '''
#       Example: GedLine{
#         path='@I0001@.NAME'
#         level=2
#         tag='NAME'
#         value='Anders (Antti)/Puuhaara e. Träskalle/' }

        self.rows = []
        # pref_name shall carry information, if all descendant rows from input file 
        # are included in this default name
        self.pref_name = False
        if type(gedline) == GedcomLine:
            GedcomLine.__init__(self, (gedline.level, gedline.tag, gedline.value))
        else:
            GedcomLine.__init__(self, gedline)


    def add_line(self, gedline):
        ''' Adds a new, descendant row with higher level number to person name structure

        Arguments example:
            path='@I0002@.NAME'
            level=2
            tag='GIVN'
            value='GIVN Brita Kristiina/'
        '''
        self.rows.append(gedline)


    def get_person_rows(self): 
        ''' Analyze this NAME and return it's GedcomLines:
            first NAME and then the descendant rows in the level hierarchy.
            The rules about merging original and generated values should be applied here
        '''
        ''' 1) Full name parts like 'givn/surn/nsfx' will be isolated and analyzed '''
        # Split 'ginv/surn/nsfx' from NAME line
        s1 = self.value.find('/')
        s2 = self.value.rfind('/')
        if s1 >= 0 and s2 >= 0 and s1 != s2:     
            # Contains '.../Surname/...' or even '.../Surname1/Surname2/...' etc
            self.givn = self.value[:s1].rstrip()
            self.surn = self.value[s1+1:s2]
            self.nsfx = self.value[s2+1:]
        else:
            self.givn = ''
            self.surn = self.value
            self.nsfx = ''
            
        ''' 1.1) GIVN given name part rules '''
        self._evaluate_givn()
        ''' 1.2) nsfx Suffix part: nothing to do? '''
        pass
        ''' 1.3) SURN Surname part: pick each surname as a new PersonName
                 Creates NAME, GIVN, SURN, NSFX rows and their associated lines into self.rows
        '''
        ret = []    # List of merged lines
        for pn in self._extract_surnames():
            LOG.debug('#' + str(pn))
            # Merge original and new rows
            self._create_gedcom_rows(pn)
            # Collect merged rows
            ret.extend(pn.rows)

        del self.reported_value
        return ret

    
    def _evaluate_givn(self):
        ''' Process given name part of NAME record '''

        def _match_patronyme(nm):
            ''' Returns full patronyme name, if matches, else None
            '''
            for short, full in _PATRONYME.items():
                if nm.endswith(short):
                    # 'Matinp.' --> 'Matinpoika'
                    return nm[:-len(short)] + full
            return None


        if self.givn:
            gnames = self.givn.split()
            
            # 1.1a) Find if last givn is actually a patronyme; mark it as new nsfx 
            
            if (len(gnames) > 0):
                nm = gnames[-1]
                pn = _match_patronyme(nm)
                if pn != None:
                    self.nsfx_orig = self.nsfx
                    self.nsfx = pn
                    self.givn = ' '.join(gnames[0:-1])
                    gnames = self.givn.split()

            # 1.1b) A generic baby name replaced as no name

                elif gnames[0] in _BABY:
                    # A unnamed baby
                    self.givn = _NONAME
                    return
#TODO: Tämä muutos ei näy Note-riveillä

            # 1.1b) Set call name, if one of given names are marked with '*'
    
            for nm in gnames:
                # Name has a star '*'
                if nm.endswith('*'):
                    # Remove star
                    nm = nm[:-1]
                    self.givn = ''.join(self.givn.split(sep='*', maxsplit=1))
                    self.call_name = nm
                # Nick name in parentehsins "(Jussi)"
                elif re.match(r"\(.*\)", nm) != None:
                    self.nick_name = nm[1:-1]
                    # Given names without nick name
                    self.givn = re.sub(r" *\(.*\) *", " ", self.givn).rstrip()
        else:
            self.givn = _NONAME


    def _extract_surnames(self):
        ''' Process surname part of NAME record and return a list of PersonNames,
            which are generated from each surname mentioned
        Examples:
            "Mattila"                  => PersonName[0]="givn/Mattila/"
            "Frisk os. Mattila"        => PersonName[0]="givn/Mattila/"
                                          PersonName[1]="givn/Frisk/" TYPE="avionimi"
            "Surname1/Surname2"        => PersonName[0]="givn/Surname1/"
                                          PersonName[1]="givn/Surname2/" TYPE="tunnettu myös"
            "Reipas e. Frisk os. Laine"=> PersonName[0]="givn/Laine/"
                                          PersonName[1]="givn/Frisk/" TYPE="avionimi"
                                          PersonName[2]="givn/Reipas/" TYPE="otettu nimi"
            "Lehti os. Lampi e. af Damm"=>PersonName[0]="givn/Damm/" SPFX="af"
                                          PersonName[1]="givn/Lampi/" TYP="otettu nimi"
                                          PersonName[2]="givn/Lehti/" TYPE="avionimi"
            "Mattila (Matts)"          => PersonName[0]="givn/Mattila/"
                                          PersonName[1]="givn/Matts/" TYPE="tunnettu myös"
        '''

        ret = []
        prefn = self.pref_name
        for nm, origin, prefix in self._get_surname_list():
            name = '{}/{}/{}'.format(self.givn, nm.strip(), self.nsfx)
            pn = PersonName((self.level, 'NAME', name))
            pn.surn = nm
            pn.givn = self.givn
            pn.nsfx = self.nsfx
            if hasattr(self,'nsfx_org'):
                pn.nsfx_orig = self.nsfx_orig
            if hasattr(self,'call_name'):
                pn.call_name = self.call_name
            if hasattr(self,'nick_name'):
                pn.nick_name = self.nick_name
            if prefix: # von
                pn.prefix = prefix
            if origin:
                pn.origin = origin
            # Mark the first generated surname of a person as preferred
            pn.pref_name = prefn
            prefn = False
            ret.append(pn)
        return ret


    def _get_surname_list(self):
        ''' Returns a list of tuples (name, origin, prefix) parsed from self.surn. 
            Origin is one of those in _SURN. 
            A noble prefix (SPFX value) is roughly recognized by its length max 3 chrs.
        '''
        
        if self.surn == "":
            # Empty surname is a surname, too
            surnames = list(" ")
        else:
            # convert "(", /" and "," to a single separator symbol " , " and remove ")"
            nm = re.sub(r'\)', '', re.sub(r' *[/,\(] *', ' , ', self.surn))
            surnames = nm.split()

        # Following surnames automate reads surnames and separators from right to left
        # and writes PersonNames to self.rows(?) '''
        #
        #    !state \ input !! '/'   ! delim  ! name  ! end   ! von
        #    |--------------++-------+-------+-------+--------
        #    | 0 "Started"  || -     | -     | 1,op1 | -     ! -
        #    | 1 "name"     || 0,op7 | 2,op2 | 1,op3 | 3,op4 ! 4,op5
        #    | 2 "delim"    || -     | -     | 1,op1 | -     ! -
        #    | 3 "end"      || -     | -     | -     | -     ! -
        #    | 4 "von"      || 0,op7 | 2,op2 | -     | -     | 4,op6
        #    | - "error"    || 
        ##TODO: Each '-' should cause an error!
        #    For example rule "2,op3" means operation op3 and new state 2.
        #        op1: save name=nm, clear origin and prefix
        #        op2: return (PersonName(name), origin[delim], prefix)
        #                    and saved 'known as' name
        #        op3: concatenate a two part name
        #        op4: return (PersonName(name), origin[delim], prefix)
        #        op5: create prefix
        #        op6: concatenate a two part prefix
        #        op7: save 'know as' name

        ret = []
        state = 0
        name = None
        prefix = None
        origin = None
        known_as = None
        self.reported_value = None

        def op2_return_name():
            # op2: return PersonName(name), origin[delim], prefix
            #             and saved 'known as' name
            nonlocal ret, name, origin, prefix, known_as
            ret.append((name, origin, prefix))
            if known_as:
                ret.append(known_as)
                known_as = None
            name = ''
            origin = None
            prefix = None


        for nm in reversed(surnames):
            if state == 0 or state == 3:        # Start state: Only a name expected
                #op1: save name=nm, clear origin and prefix
                name = nm.capitalize()
                state = 1
            elif state == 1 or state == 2:      # Possible separator state / 
                                                # left side name has been stored
                if nm in '(/,':
                    #op7: A known as -name; to be returned later
                    known_as = (name.capitalize(), _SURN[','], prefix)
                    name = ''
                    state = 0
                elif nm in _SURN: # other delim
                    #op2: Output PersonName rows 
                    op2_return_name()
                    origin = _SURN[nm]
                    state = 2
                elif len(nm) < 4 and not '.' in nm: # von
                    #op5: Propably a noble prefix
                    prefix = nm.lower()
                    state = 4
                else: # name
                    #op3: Another name found
                    name = str.rstrip(nm.capitalize() + ' ' + name)
            else: # state == 4:
                if nm in _SURN: # delim
                    #op2: A separator 'os.', ... found: 
                    #     Output PersonName rows 
                    op2_return_name()
                    origin = _SURN[nm]
                    state = 2
                else: # von
                    #op5: Propably a multi word prefix
                    prefix = str.rstrip(nm.lower() + ' ' + prefix)
                    state = 4

        #op4: End: output the last name
        if name:
            op2_return_name()
            
        if len(ret) == 0:
            # No surname: give empty name
            return (("", None, None), )
        return ret


    def _format_row(self, level, tag, value):
        ''' Builds a gedcom row '''
        return("{} {} {}".format(level, tag, str.strip(value)))


    def _create_gedcom_rows(self, pn):
        ''' Stores the given PersonName as GedcomLines so that previous values of pn.rows are merged.
            This is important, as original lines may have descentants like SOUR, which must be kept
            in place.
            1. Inset NAME row on the top
            2. Loop trough original GedcomLines self.rows
               2.0 If '2 NOTE' line's value doesn't start with '_CALL ', do not update
               2.1 If tag GIVN, SURN or NSFX is found, update/report the pn.row
               2.2 Else copy self.row the to pn.rows
            3. Create new pn.rows, if any of GIVN, SURN or NSFX is not used
        '''

        def in_tags(tag):
            ''' Is this one of my (unused) tags? Return corresponding value or None '''
            for i in range(len(my_tags)):
                if my_tags[i][0] == r.tag:
                    # Remove used tag and return it's value
                    ret = my_tags[i][1]
                    del my_tags[i]
                    return ret
            return None
        
        def report_change(tag, value, new_value):
            ''' Report a change for a tag '''
            if self.reported_value == value:
                return
            pn.rows.append(GedcomLine((self.level+1, _CHGTAG + tag, value)))
            if self.path.endswith(tag):
                path = self.path
            else:
                path = "{}.{}".format(self.path, tag)
            LOG.info("{} {!r:>36} --> {!r}".format(path, value, new_value))
            self.reported_value = value


        my_tags = [['NAME', pn.value], ['GIVN', pn.givn], ['SURN', pn.surn], ['NSFX', pn.nsfx]]
        if hasattr(pn, 'origin'):
            my_tags.append(['TYPE', pn.origin])
        if hasattr(pn, 'call_name'):
            my_tags.append(['NOTE', '_CALL ' + pn.call_name])
        if hasattr(pn, 'nick_name'):
            my_tags.append(['NICK', pn.nick_name])
        if hasattr(pn, 'prefix'):
            my_tags.append(['SPFX', pn.prefix])

        # 1. The first row is the PersonName (inherited class from GedcomLine)
        orig_rows = [self]
        if pn.pref_name:
            # Only the person's first NAME and there the first surname 
            # carries the gedcom lines inherited from input file
            orig_rows.extend(self.rows)
        # For name comparison
        name_self = re.sub(r'[ \*]', '', self.value).lower()

        # 2. r = original input gedcom self.row 
        for r in orig_rows:
            # 2.0 Pass a NOTE line without '_CALL' as is
            if r.tag == 'NOTE' and not self.value.startswith('_CALL '):
                LOG.debug("#{:>36} repl row[{}] {} {!r}".\
                      format(r.path, len(pn.rows), r.tag, r.value))
                pn.rows.append(GedcomLine((r.level, r.tag, r.value)))
            # 2.1 Is there a new value for this line
            new_value = in_tags(r.tag)
            if new_value:
                LOG.debug("#{:>36} repl row[{}] {} {!r}".\
                      format(r.path, len(pn.rows), r.tag, new_value))
                pn.rows.append(GedcomLine((r.level, r.tag, new_value)))
                # Show NAME differences 
                if r.tag == 'NAME':
                    if re.sub(r' ', '', pn.value.lower()) != name_self: 
                        report_change(r.tag, self.value, new_value)
                    pn.pref_name = False
                elif r.tag == 'NSFX' and hasattr(self, 'nsfx_orig'):
                    report_change(r.tag, self.value, self.nsfx_orig)
                continue
            # 2.2 Only append to pn.row
            LOG.debug("#{:>36} add  row[{}] {} {!r}".\
                  format(r.path, len(pn.rows), r.tag, r.value))
            pn.rows.append(GedcomLine((r.level, r.tag, r.value)))

        # 3 Create new rows for unused tags (except trivial ones)
        for tag, value in my_tags:
            if value and not tag in ('GIVN', 'SURN'):
                LOG.debug("#{:>36} new  row[{}] {} {!r}".\
                      format("{}.{}".format(self.path, tag), len(pn.rows), tag, value))
                pn.rows.append(GedcomLine((pn.level + 1, tag, value)))
