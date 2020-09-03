#!/bin/sh

cd $(dirname "$0")

if test -f ./data/sen1floods11-catalog.zip; then
  echo "Sen1Floods11 catalog already downloaded. Continuing..."
else
  echo "Downloading sen1floods11 catalog from s3://sen1floods11-data/stac-catalog.zip"
  aws s3 cp s3://sen1floods11-data/stac-catalog.zip ./data/sen1floods11-catalog.zip
fi

if ! test -f ./data/flood_valid_data.csv; then
  echo "Downloading validation csv..."
  aws s3 cp s3://sen1floods11-data/flood_valid_data.csv ./data/flood_valid_data.csv
fi

if ! test -f ./data/flood_test_data.csv; then
  echo "Downloading test csvs..."
  aws s3 cp s3://sen1floods11-data/flood_test_data.csv ./data/flood_test_data.csv
  aws s3 cp s3://sen1floods11-data/flood_bolivia_data.csv ./data/flood_bolivia_data.csv
fi

if test -d ./data/catalog; then
  echo "sen1floods11 catalog already unzipped. Continuing..."
else
  echo "Unzipping sen1floods11 catalog..."
  unzip -q ./data/sen1floods11-catalog.zip -d ./data
fi

echo "Generating catalogs (this may take awhile)..."
python3 build_catalog.py hand \
    --valid-csv ./data/flood_valid_data.csv \
    --test-csvs ./data/flood_test_data.csv \
    --test-csvs ./data/flood_bolivia_data.csv
python3 build_catalog.py s1weak \
    --valid-csv ./data/flood_valid_data.csv \
    --test-csvs ./data/flood_test_data.csv \
    --test-csvs ./data/flood_bolivia_data.csv
python3 build_catalog.py s2weak \
    --valid-csv ./data/flood_valid_data.csv \
    --test-csvs ./data/flood_test_data.csv \
    --test-csvs ./data/flood_bolivia_data.csv
