#!/bin/sh

cd $(dirname "$0")

aws s3 ls s3://sen1floods11-data
STATUS=$?

if [ $STATUS -eq 0 ]; then
  python build_catalog.py
else
  echo "Ensure AWS_PROFILE is set to a profile that is able to read s3://sen1floods11-data"
fi
