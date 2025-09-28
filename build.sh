#!/bin/sh

if ! command -v python2.2 &> /dev/null; then
    echo "Requires Python 2.2 to be installed."
    exit 1
fi

if [[ -z $1 ]] || [[ $1 == "" ]]; then
    echo "Usage: ./build.sh <version>"
    exit 0
fi

python2.2 ./ensymble_python2.2-0.27.py py2sis --appname="DedoSurf" --version $1 --caption="DedoSurf" --shortcaption="DedoSurf" --vendor="Wunder Wungiel" --uid=0xF2395303 --icon="res/icon.svg" --caps=NetworkServices+LocalServices+ReadUserData+WriteUserData+UserEnvironment --drive=c "src" "."
