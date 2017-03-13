# stk-gedcom
Programs used for cleaning import gedcom files according to our standards

Please, use stucture advice from http://docs.python-guide.org/en/latest/writing/structure/
Carefully isolate functions with context and side-effects from
functions with logic (called pure functions)!

	docs/                     Documents
	
	gedder/                   # Code for gedcom processing; executable main functions here
		gedcom_transform.py*
		gedder.py*
	
	gedder/transforms         # Gedcom transformation programs
		hiskisources.py
		kasteet.py
		marriages.py
		names.py
		places.py
		unmark.py

	gedder/transforms/model   # Classes used by gedcom processing
		ged_output.py
		gedcom_line.py
		gedcom_record.py
		person_name.py

	gedder/ui                 # User interface files and code 
		Gedder.glade
		displaystate.glade
		gedder_handler.py
		tk_gedder.ui

	gedder/static/            # Static files like parameters and code lists
		kylat.txt
		seurakunnat.txt

	gedder/test/              # Test files and scripts
		Mun-testi.ged.1
		My-test.ged
		tests.sh
