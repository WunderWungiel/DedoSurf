#!/bin/sh

if ! command -v python25 &> /dev/null; then
    echo "Requires Python 2.5.4 to be installed."
    exit 1
fi

if [[ -z $1 ]] || [[ $1 == "" ]]; then
    echo "Usage: ./build.sh <version>"
    exit 0
fi

mypath=$(pwd -P)
pushd ../PythonForS60 > /dev/null
python25 ./ensymble.py py2sis --appname="DedoSurf" --version $1 --caption="DedoSurf" --shortcaption="DedoSurf" --vendor="Wunder Wungiel" --uid=0xF2395303 --icon="$mypath/res/icon.svg" --drive=c "$mypath/src" "$mypath"
popd > /dev/null
