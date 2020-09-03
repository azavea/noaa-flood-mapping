#!/bin/sh

cd $(dirname "$0")

if ! test -f ./data/hand-catalog.tar.gz; then
    echo "Downloading HAND STAC catalog to ./data/hand-catalog.tar.gz"
    aws s3 cp s3://hand-data/catalog.tar.gz ./data/hand-catalog.tar.gz
fi

if ! test -d ./data/hand-catalog; then
    echo "Unzipping HAND STAC catalog to ./data/hand-catalog"
    pushd data > /dev/null 2>&1
    tar -xzf hand-catalog.tar.gz
    mv catalog hand-catalog
    popd > /dev/null 2>&1
fi

python3 build_catalog.py
