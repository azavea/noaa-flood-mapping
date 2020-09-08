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

# Search for USFIMR + S1 intersections and
# create SentinelHub Batch Ingest jobs writing to EU_BUCKET
python ingest_s1.py \
  --oauth-id "${SENTINELHUB_OAUTH_ID}" \
  --oauth-secret "${SENTINELHUB_OAUTH_SECRET}" \
  --sentinelhub-bucket "${EU_BUCKET}"

# Reproject SentinelHub Batch results to 4326
# and copy to a US East 1 bucket
./reproject_tiffs.sh s3://${EU_BUCKET} s3://${OUT_BUCKET_4326}

# Generate initial catalog without coregistered HAND tifs
python build_catalog.py --imagery-root-s3 s3://${OUT_BUCKET_4326}

# Pull HAND catalog
if ! test -f ./data/hand-catalog.tar.gz; then
    echo "Downloading HAND STAC catalog to ./data/hand-catalog.tar.gz"
    aws s3 cp s3://hand-data/catalog.tar.gz ./data/hand-catalog.tar.gz
fi
if ! test -d ./data/hand-catalog; then
    echo "Unzipping HAND STAC catalog to ./data/hand-catalog"
    tar -xzf ./data/hand-catalog.tar.gz -C ./data/hand-catalog
fi
# Coregister HAND tifs with projection, extent, and resolution to S1 chips
# Upload coregistered HAND tifs to the same path as the S1 chips
python coregister.py \
  --s1-catalog ./data/catalog/catalog.json \
  --hand-catalog ./data/hand-catalog/catalog/collection.json

# Re-generate catalog in order to include HAND tifs generated in coregister step
rm -rf ./data/catalog
python build_catalog.py --imagery-root-s3 s3://${OUT_BUCKET_4326}
