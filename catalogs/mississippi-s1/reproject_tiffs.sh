#!/bin/bash
set -e

export INPUT_ROOT=$1
export INPUT_BUCKET=$(echo $1 | cut -d '/' -f 3)
export OUTPUT_ROOT=$2
export OUTPUT_BUCKET=$(echo $2 | cut -d '/' -f 3)
export PARALLELISM=${3:-4}


# requires path (minus bucket)
function reproject_to_new_root {
  IN_PATH="s3://${INPUT_BUCKET}/$1"
  OUT_PATH="s3://${OUTPUT_BUCKET}/$1"
  TEMP_UTM=$(mktemp /tmp/utm.XXXXXXXXXXXXXXXXXXXXXXX.tiff)
  TEMP_4326=$(mktemp /tmp/4326.XXXXXXXXXXXXXXXXXXXXXXX.tiff)
  echo "Reprojecting from ${IN_PATH} to ${OUT_PATH}"
  aws s3 cp $IN_PATH $TEMP_UTM
  gdalwarp -overwrite -r bilinear -t_srs EPSG:4326 $TEMP_UTM $TEMP_4326
  aws s3 cp $TEMP_4326 ${OUT_PATH}
  echo "Successfully wrote to ${OUT_PATH}"
  rm -rf $TEMP_4326
  rm -rf $TEMP_UTM
}


function main {
  # size
  S=`echo $1 | tr -s ' ' | cut -d ' ' -f 3`
  # path
  P=`echo $1 | tr -s ' ' | cut -d ' ' -f 4`
  FILE_EXT=${P##*.}

  if [ "$FILE_EXT" = "tiff" ]; then
    # An empty mask should be 5837 bytes
    if [ $(basename $P) = "MASK.tiff" ] && [ "$S" -gt 5837 ]; then
      echo "working on $P"
      reproject_to_new_root $P

    # An empty vv/vh should be 60815 bytes
    elif [ "$S" -gt 60815 ]; then
      echo "working on $P"
      reproject_to_new_root $P
    else
      echo "SKIPPING $P, size $S"
    fi
  else
    echo "File without .tiff extension encountered: $P"
  fi
}

export -f reproject_to_new_root
export -f main
export IFS=$'\n'
aws s3 ls --recursive ${INPUT_ROOT} | parallel -j $PARALLELISM -n 1 main {}