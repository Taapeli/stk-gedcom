'''
Created on 16.1.2017

@author: jm
'''

import logging
import datetime
LOG = logging.getLogger(__name__)

from classes.gedcom_line import GedcomLine
from classes.person_name import PersonName


class GedcomRecord(GedcomLine):
    '''
    Stores a Gedcom logical record, which includes level 0 record (0 INDI) 
    with all it's lines (with level > 0)

    Methods:
    __init__(...)    An object instance is created using the level 0 line
    add(...)         Other, higher level rows are added
    get_lines()      Returns an iterable containing the lines
    
    The fixes are done mostly from '1 NAME givn/surn/nsfx' row.
    If NAME has significant changes, the original value is also written to 'NOTE orig_'
    
    '''
    def __init__(self, gedline):
        ''' Creates a new instance of gedcom logical record
            which includes a group of gredcom lines starting with a level0 record.
        '''
        self.rows = []
        # optional attributes {'BIRT':1820}
        self.attributes = {}
        # Latest PersonName index in self.rows
        self.currname = -1
        # Store level 0 line
        if not type(gedline) is GedcomLine:
            raise RuntimeError("GedcomLine argument expected")
        self.level = gedline.level
        self.path = gedline.path
        self.value = gedline.value
        self.add_member(gedline)

    
    def __str__(self):
        return "GedcomRecord({})".format(self.id)


    def add_member(self, gedline):
        ''' Adds a gedcom line to record set.
            "2 NAME" line is added as a PersonName object, others as GedcomLine objects
        '''
        if type(gedline) is PersonName:
            # gedline is "1 NAME ...". The first one is the preferred name
            gedline.pref_name = (self.currname < 0)
#             print("#record row({}) <= {} (name {!r})".format(len(self.rows), gedline.path, gedline.name), file=stderr)
            self.currname = len(self.rows)
            self.rows.append(gedline)
        else:
#             print("#record row({}) <= {} ({!r})".format(len(self.rows), gedline.path, gedline.value), file=stderr)
            self.rows.append(gedline)

 
    def emit(self, f):
        ''' Find the stored data associated to this person and
            writes them as new gedcom lines to file f
        '''
        # Each original NAME row
        for obj in self.rows: 
            if isinstance(obj, PersonName):
                # Each NAME row generated from /surname1, surname2/
                for x in obj.get_person_rows(): 
                    f.emit(str(x))
            else:
                # A GedcomLine outside NAME and its descendants
                f.emit(str(obj))


    def store_date(self, year, tag):
        if type(year) == int:
            self.set_attr(tag, year)
        else:
            LOG.warning("{} ERROR: Invalid {} year".format(self.path, tag))


    def get_nameobject(self):
        ''' Returns the latest object of type PersonName '''
        if self.currname >= 0:
            return self.rows[self.currname]


if __name__ == '__main__':
    # Test set
    from classes.ged_output import Output
    from argparse import Namespace
    logging.basicConfig(filename='example.log',level=logging.INFO, format='%(levelname)s:%(message)s')
    LOG.info("------ Ajo '%s' alkoi %s", "Testi", datetime.datetime.now().strftime('%a %Y-%m-%d %H:%M:%S') + " ------")

    # One person with two NAME lines
    my_record = GedcomRecord(GedcomLine('0 @I2@ INDI'))
    my_name = PersonName(GedcomLine('1 NAME Amalia Saima* (Sanni) Erikint./Raitala os. von Krats/Ericsdr.'))
    my_record.add_member(my_name)
    my_name.add_line(GedcomLine(('2','GIVN','Saimi')))
    my_name.add_line(GedcomLine('3 SOUR Äidiltä'))
    my_name.add_line(GedcomLine('2 SURN Raitala'))
    my_name.add_line(GedcomLine('2 NOTE Kummin kaima'))
    my_name = PersonName(GedcomLine('1 NAME vauva//Ericsdr.'))
    my_record.add_member(my_name)
    my_name = PersonName(GedcomLine('1 NAME Niilo/Niemelä/Niemeläinen/'))
    my_record.add_member(my_name)
    my_name = PersonName(GedcomLine('1 NAME Janne/Mattila (Matts)/'))
    my_record.add_member(my_name)
    args = Namespace(nolog=True, output_gedcom='out.txt', encoding='UTF-8', dryrun=False)
    with Output(args) as f:
        my_record.emit(f)

    LOG.info("------ Ajo '%s' päättyi %s", "Testi", datetime.datetime.now().strftime('%a %Y-%m-%d %H:%M:%S') + " ------")

