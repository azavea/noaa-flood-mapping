#!/bin/sh

cd $(dirname "$0")

python3 build_catalog.py --root-uri https://hand-data.s3.amazonaws.com
