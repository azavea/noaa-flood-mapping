#!/bin/bash

set -e

cd $(dirname "$0")

if [ -z ${SENTINELHUB_OAUTH_ID+x} ]; then
  echo "SENTINELHUB_OAUTH_ID is not set in the environment."
  exit 1
fi
if [ -z ${SENTINELHUB_OAUTH_SECRET+x} ]; then
  echo "SENTINELHUB_OAUTH_SECRET is not set in the environment."
  exit 1
fi

EU_BUCKET="noaafloodmapping-sentinelhub-batch-eu-central-1"
OUT_BUCKET_4326="glofimr-sar-4326"

python ingest_s1.py \
  --oauth-id "${SENTINELHUB_OAUTH_ID}" \
  --oauth-secret "${SENTINELHUB_OAUTH_SECRET}" \
  --sentinelhub-bucket "${EU_BUCKET}"

./reproject_tiffs.sh s3://${EU_BUCKET} s3://${OUT_BUCKET_4326}

python build_catalog.py --imagery-root-s3 s3://${OUT_BUCKET_4326}
