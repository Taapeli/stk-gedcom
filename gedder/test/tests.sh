for f in tests/kasteet-*
do
   python3 gedcom_transform.py kasteet $f --nolog --out x 
   diff $f.expected x
done

for f in tests/marriages-*
do
   python3 gedcom_transform.py marriages $f --nolog --out x 
   diff $f.expected x
done

exit

for f in tests/places-*
do
   python3 gedcom_transform.py places $f --nolog --out x 
   diff $f.expected x
done

for f in tests/names-*
do
   python3 gedcom_transform.py names $f --nolog --out x 
   diff $f.expected x
done
