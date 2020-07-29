#!/bin/sh

if test -f /tmp/USFIMR_all.zip; then
  echo "/tmp/USFIMR_all.zip already downloaded. Continuing..."
else
  echo "/tmp/USFIMR_all.zip not downloaded. Downloading..."
  wget ftp://guest:guest@sdml-server.ua.edu/USFIMR/USFIMR_all.zip -O /tmp/USFIMR_all.zip
fi

if test -d /tmp/USFIMR_all; then
  echo "/tmp/USFIMR_all.zip already unzipped. Continuing..."
else
  echo "Unzipping /tmp/USFIMR_all.zip..."
  unzip /tmp/USFIMR_all.zip -d /tmp
fi

if test -f /tmp/latlng/USFIMR_07172018.shp; then
  echo "USFIMR already reprojected. Continuing..."
else
  echo "Reprojecting USFIMR..."
  mkdir -p /tmp/latlng
  ogr2ogr /tmp/latlng/USFIMR_07172018.shp -t_srs "EPSG:4326" /tmp/USFIMR_all/USFIMR_07172018.shp
fi

if test -d ./catalog; then
  echo "STAC catalog already exists."
else
  echo "STAC catalog not generated."
  python3 build_catalog.py --shapefile /tmp/latlng/USFIMR_07172018.shp
fi
