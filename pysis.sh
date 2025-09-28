#!/bin/sh

if [[ -z $1 ]] || [[ $1 == "" ]]; then
    echo "Usage: ./build.sh <version>"
    exit 0
fi

python2 pys60-app-builder/pysis.py \
    --name="DedoSurf" \
    --vendor="Wunder Wungiel" \
    --version=$1 \
    --pys60=1 \
    --uid=0xF2395303 \
    --caps=allcaps \
#    --caps=NetworkServices+LocalServices+ReadUserData+WriteUserData+UserEnvironment \
    --menuname="DedoSurf" \
    --titlename="DedoSurf" \
    --filesdir=src \
    --exportdir=export
