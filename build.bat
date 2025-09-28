@echo off

SET mypath=%~dp0
C:\Python22\python.exe .\ensymble_python2.2-0.27.py py2sis --appname="DedoSurf" --version 0.0.4 --caption="DedoSurf" --shortcaption="DedoSurf" --vendor="Wunder Wungiel" --uid=0xF2395304 --drive=c --icon="%mypath:~0,-1%\res\icon.svg" --caps=NetworkServices+LocalServices+ReadUserData+WriteUserData+UserEnvironment "%mypath:~0,-1%\src" "%mypath:~0,-1%"
