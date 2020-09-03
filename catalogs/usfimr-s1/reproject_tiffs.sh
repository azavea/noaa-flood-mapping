#!/bin/bash
set -ex

INPUT_ROOT=$1
OUTPUT_ROOT=$2

for line in `aws s3 ls --recursive ${INPUT_ROOT} | awk '{print $4}'`; do
  FILE_EXT=${line##*.}
  IN_PATH=${INPUT_ROOT}/${line}
  OUT_PATH=${OUTPUT_ROOT}/${line}
  if [ "$FILE_EXT" = "tiff" ]; then
    echo "Reprojecting from ${IN_PATH} to ${OUT_PATH}"
    aws s3 cp $IN_PATH /tmp/utm.tiff
    gdalwarp -r bilinear -t_srs EPSG:4326 /tmp/utm.tiff /tmp/4326.tiff
    aws s3 cp /tmp/4326.tiff ${OUT_PATH}
    rm -rf /tmp/utm.tiff
    rm -rf /tmp/4326.tiff
  else
    aws s3 cp ${IN_PATH} ${OUT_PATH}
  fi
done