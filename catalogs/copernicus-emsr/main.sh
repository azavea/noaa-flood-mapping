#!/bin/bash

set -e

cd $(dirname "$0")

python build_catalog.py
