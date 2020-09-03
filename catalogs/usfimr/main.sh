#!/bin/sh

cd $(dirname "$0")

if test -f ./data/USFIMR_merged.zip; then
  echo "USFIMR shapefile already downloaded. Continuing..."
else
  echo "Downloading USFIMR shapefile from s3://usfimr-data/shp/USFIMR_merged.zip"
  aws s3 cp s3://usfimr-data/shp/USFIMR_merged.zip ./data/USFIMR_merged.zip
fi

if test -f ./data/USFIMR_merged.shp; then
  echo "USFIMR shapefile already unzipped. Continuing..."
else
  unzip ./data/USFIMR_merged.zip -d ./data
fi

if test -d ./data/catalog; then
  echo "STAC catalog already exists."
else
  echo "Generating STAC Catalog..."
  python3 build_catalog.py --shapefile ./data/USFIMR_merged.shp
fi
