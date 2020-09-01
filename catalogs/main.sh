#!/bin/bash
set -e

cd $(dirname "$0")

function usage() {
    echo -n "
Usage: $(basename "$0") <dataset>

Generate a STAC Catalog for the requested dataset. Allowed values
for <dataset> are the folder names within this directory:

$(ls -d */)

"
}

if [ "${1:-}" = "--help" ]; then
    usage
elif [ "${1:-}" = "" ]; then
    usage
else
    ./"$1"/main.sh
fi
