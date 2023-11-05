@echo off

SET mypath=%~dp0
cd C:\Program Files (x86)\PythonForS60
C:\Python25\python.exe .\ensymble.py py2sis --appname="DedoSurf" --version 0.0.3 --caption="DedoSurf" --shortcaption="DedoSurf" --vendor="Wunder Wungiel" --uid=0xF2395303 --drive=c --icon="%mypath:~0,-1%\res\icon.svg" "%mypath:~0,-1%\src" "%mypath:~0,-1%"
cd %mypath:~0,-1%
