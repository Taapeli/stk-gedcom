@echo off
set PATH=C:\Progra~1\GrampsAIO64-4.2.5
set PYTHONHOME=%PATH%
set PYTHONPATH=%PATH%;%PATH%\lib;%PATH%\lib\python35.zip
set PYTHONNOUSERSITE=1
%PATH%\pythonn.exe gedder.py -W ignore::Warning %* 
pause