#!/usr/bin/env python3
"""
Tries to recognize place names and order them correctly
"""

version = "1.0"

from collections import defaultdict 

ignored_text = """
mlk
msrk
ksrk
tksrk
maalaiskunta
maaseurakunta
kaupunkiseurakunta
tuomiokirkkoseurakunta
rykmentti
pitäjä
kylä

hl
tl
ol
ul
vpl
vl

tai

de
las

"""


def add_args(parser):
    parser.add_argument('--reverse', action='store_true',
                        help='Reverse the order of places')
    parser.add_argument('--add-commas', action='store_true',
                        help='Replace spaces with commas')
    parser.add_argument('--ignore-lowercase', action='store_true',
                        help='Ignore lowercase words')
    parser.add_argument('--ignore-digits', action='store_true',
                        help='Ignore numeric words')
    parser.add_argument('--minlen', type=int, default=0,
                        help="Ignore words shorter that minlen")
    parser.add_argument('--auto-order', action='store_true',
                        help='Try to discover correct order...')
    parser.add_argument('--auto-combine', action='store_true',
                        help='Try to combine certain names...')
    parser.add_argument('--match', type=str, action='append',
                        help='Only process places containing any match string')
    parser.add_argument('--parishfile', type=str,
                        help='File with a list of parishes', default="seurakunnat.txt")
    parser.add_argument('--villagefile', type=str,
                        help='File with a list of villages', default="kylat.txt")
    #parser.add_argument('--display-changes', action='store_true',
    #                    help='Display changed places')
    parser.add_argument('--display-nonchanges', action='store_true',
                        help='Display unchanged places')
    parser.add_argument('--display-ignored', action='store_true',
                        help='Display ignored places')
    parser.add_argument('--mark-changes', action='store_true',
                        help='Replace changed PLAC tags with PLAC-X')
                        
def initialize(args):
    read_parishes(args.parishfile)
    read_villages(args.villagefile)


def phase2(args):
    pass

def phase3(args,gedline,f):
    if gedline.tag == "PLAC":
        if not gedline.value: return
        place = gedline.value
        newplace = process_place(args,place)
        if newplace != place: 
            if args.display_changes: print("'{}' -> '{}'".format(place,newplace))
            gedline.value = newplace  
            if args.mark_changes: gedline.tag = "PLAC-X"
        else:
            if args.display_nonchanges: print("Not changed: '{}'".format(place))
    gedline.emit(f)
            
ignored = [name.strip() for name in ignored_text.splitlines() if name.strip() != ""]

parishes = set()

countries = {
    "Finland",
    "Suomi",
    "USA",
    "Kanada",
    "Yhdysvallat",
    "Alankomaat",
    "Ruotsi",
    "Australia",
    "Venäjä",
    "Eesti","Viro",
}

villages = defaultdict(set)

def numeric(s):
    return s.replace(".","").isdigit()

def read_parishes(parishfile):
    for line in open(parishfile,encoding="utf-8"):
        line = line.strip()
        if line == "": continue
        num,name = line.split(None,1)
        for x in name.split("-"):
            name2 = x.strip().lower()
            parishes.add(auto_combine(name2))
         
def read_villages(villagefile):
    for line in open(villagefile,encoding="utf-8"):
        line = line.strip()
        if line == "": continue
        parish,village = line.split(":",1)
        parish = parish.strip().lower()
        village = village.strip().lower()
        villages[auto_combine(parish)].add(village)

def ignore(args,names):
    for name in names:
        if len(name) < args.minlen: return True
        if name.lower() in ignored: return True
        if args.ignore_digits and numeric(name): return True
        if args.ignore_lowercase and name.islower(): return True
    return False

auto_combines = [
    "n pitäjä",
    "n srk",
    "n seurakunta",
    "n maalaiskunta",
    "n maaseurakunta",
    "n kaupunkiseurakunta",
    "n tuomiokirkkoseurakunta",
    "n rykmentti",
    "n kylä",
    "n mlk",
    "n msrk",
    "n ksrk",
]

def auto_combine(place):
    for s in auto_combines:
        place = place.replace(s,s.replace(" ","-"))
    return place
    
def revert_auto_combine(place):
    for s in auto_combines:
        place = place.replace(s.replace(" ","-"),s)
    return place

def stringmatch(place,matches):
    for match in matches:
        if place.find(match) >= 0: return True
    return False
    
def process_place(args,place):
    if args.match and not stringmatch(place,args.match): return place
    if args.add_commas and "," not in place:
        if args.auto_combine:
            place = auto_combine(place)
        names = place.split()
        if ignore(args,names): 
            if args.auto_combine: place = revert_auto_combine(place)
            if args.display_ignored: print("ignored: " + place)
            return place
        place = ", ".join(names)
    if "," in place:
        names = [name.strip() for name in place.split(",") if name.strip() != ""]
        if len(names) == 1: 
            if args.auto_combine: place = revert_auto_combine(place)
            return place
        do_reverse = False
        if args.auto_order:
            #print(sorted(parishes))
            #print(sorted(villages["helsingin-pitäjä"]))
            #print(names)
            if names[0].lower() in parishes and names[1].lower() in villages[names[0].lower()] and names[-1] not in countries:
                do_reverse = True
            if names[0] in countries:
                do_reverse = True
        if args.reverse or do_reverse:
            names.reverse()
            place = ", ".join(names)
    if args.auto_combine:
        place = revert_auto_combine(place)
    return place
 


def check(input,expected_output,reverse=False,add_commas=False,ignore_lowercase=False,ignore_digits=False):
    class Args: pass
    args = Args()
    args.reverse = reverse
    args.add_commas = add_commas
    args.ignore_lowercase = ignore_lowercase
    args.ignore_digits = ignore_digits
    args.display_ignored = False
    args.display_ignored = False
    args.auto_order = True
    args.auto_combine = True
    args.minlen = 0
    args.match = None
 
    newplace = process_place(args,input)
    if newplace != expected_output:
        print("{}: expecting '{}', got '{}'".format(input,expected_output,newplace))
        

def test():
    check("Helsingin pitäjä Herttoniemi","Herttoniemi, Helsingin pitäjä",add_commas=True,reverse=False)
    check("Rättölä, Heinjoki","Heinjoki, Rättölä",reverse=True)
    check("Rättölä Heinjoki","Rättölä, Heinjoki",add_commas=True)
    check("Rättölä Heinjoki","Heinjoki, Rättölä",add_commas=True,reverse=True)
    check("Rättölä, Heinjoki","Rättölä, Heinjoki",add_commas=True)
    check("Viipurin mlk","Viipurin mlk",add_commas=True)
    check("Viipurin msrk","Viipurin msrk",add_commas=True)
    check("Koski tl","Koski tl",add_commas=True)
    check("Koski TL","Koski TL",add_commas=True)
    check("Koski","Koski",add_commas=True)
    check("Koski","Koski",reverse=True)

    check("Koski förs","Koski, förs",add_commas=True,ignore_lowercase=False)
    check("Koski förs","Koski förs",add_commas=True,ignore_lowercase=True)

    #check("Rio de Janeiro","Rio, de, Janeiro",add_commas=True,ignore_lowercase=False)
    check("Rio de Janeiro","Rio de Janeiro",add_commas=True,ignore_lowercase=True)

    check("Stratford upon Avon","Stratford, upon, Avon",add_commas=True,ignore_lowercase=False)
    check("Stratford upon Avon","Stratford upon Avon",add_commas=True,ignore_lowercase=True)
    
    check("Äyräpää Vuosalmi N:o 4", "Äyräpää, Vuosalmi, N:o, 4",add_commas=True,ignore_digits=False)
    check("Äyräpää Vuosalmi N:o 4", "Äyräpää Vuosalmi N:o 4",add_commas=True,ignore_digits=True)

    
if __name__ == "__main__":
    test()


