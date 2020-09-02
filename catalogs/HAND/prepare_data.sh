#!/bin/sh
set -ex

HUC6=$1
S3_URI=$2


function shp2geojson {
  if test -f /tmp/$HUC6-out/$1.geojson; then
    echo "/tmp/${HUC6}-out/$1.geojson exists. Continuing..."
  else
    echo "/tmp/${HUC6}-out/$1.geojson does not exist. Generating..."
    ogr2ogr -f GeoJSON -t_srs crs:84 /tmp/$HUC6-out/$1.geojson /tmp/$HUC6/$1.shp
  fi
}

function cogify_bilinear {
  if test -f /tmp/$HUC6-out/$1.tif; then
    echo "/tmp/${HUC6}-out/$1.tif exists. Continuing..."
  else
    echo "/tmp/${HUC6}-out/$1.tif does not exist. Generating..."
    gdaladdo -r bilinear /tmp/$HUC6/$1.tif 2 4 8 16
    gdal_translate /tmp/$HUC6/$1.tif /tmp/$HUC6-out/$1.tif -co COMPRESS=DEFLATE -co TILED=YES -co INTERLEAVE=BAND -co BIGTIFF=IF_SAFER
  fi
}

function cogify_nearest {
  if test -f /tmp/$HUC6-out/$1.tif; then
    echo "/tmp/${HUC6}-out/$1.tif exists. Continuing..."
  else
    echo "/tmp/${HUC6}-out/$1.tif does not exist. Generating..."
    gdaladdo -r near /tmp/$HUC6/$1.tif 2 4 8 16
    gdal_translate /tmp/$HUC6/$1.tif /tmp/$HUC6-out/$1.tif -co COMPRESS=DEFLATE -co TILED=YES -co INTERLEAVE=BAND -co BIGTIFF=IF_SAFER
  fi
}

if test -f /tmp/$HUC6.zip; then
  echo "/tmp/${HUC6}.zip exists. Continuing..."
else
  echo "/tmp/${HUC6}.zip does not exist. Downloading..."
  wget https://cfim.ornl.gov/data/HAND/20200301/${HUC6}.zip -O /tmp/$HUC6.zip
fi

if test -d "/tmp/${HUC6}"; then
  echo "/tmp/${HUC6} exists. Continuing..."
else
  echo "/tmp/${HUC6} does not exist. Unzipping..."
  unzip /tmp/$HUC6.zip -d /tmp/
fi

mkdir -p /tmp/$HUC6-out

echo "================================="
echo "Generating data..."
echo "================================="
cogify_bilinear ${HUC6}hand
shp2geojson ${HUC6}-wbd
shp2geojson ${HUC6}-flows
shp2geojson ${HUC6}-inlets
cogify_bilinear ${HUC6}-weights
cogify_bilinear ${HUC6}
cogify_bilinear ${HUC6}fel
cogify_bilinear ${HUC6}p
cogify_bilinear ${HUC6}sd8
cogify_bilinear ${HUC6}ang
cogify_bilinear ${HUC6}slp
cogify_bilinear ${HUC6}ssa
cogify_bilinear ${HUC6}src
cogify_bilinear ${HUC6}dd
cogify_nearest ${HUC6}catchmask
cogify_nearest ${HUC6}catchhuc
cp /tmp/${HUC6}/${HUC6}_comid.txt /tmp/${HUC6}-out/${HUC6}_comid.txt
cp /tmp/${HUC6}/hydrogeo-fulltable-${HUC6}.csv /tmp/${HUC6}-out/hydrogeo-fulltable-${HUC6}.csv


echo "================================="
echo "Uploading data..."
echo "================================="
aws s3 sync /tmp/${HUC6}-out ${S3_URI}/${HUC6}

echo "Data for HUC6 ${HUC6} successfully generated and uploaded"
exit 0