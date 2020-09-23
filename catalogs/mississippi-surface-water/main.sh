#!/bin/sh

cd $(dirname "$0")

aws s3 ls s3://global-surface-water/monthly/mississippi-river
STATUS=$?

if [ $STATUS -eq 0 ]; then
  python build_catalog.py --jrc-monthly-root-s3 s3://global-surface-water/monthly/mississippi-river
  tar -czvf data/mississippi-surface-water-monthly-catalog.tar.gz data/catalog
else
  echo "Ensure AWS_PROFILE is set to a profile that is able to read s3://global-surface-water/monthly/mississippi-river"
fi
