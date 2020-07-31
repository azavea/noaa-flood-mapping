#!/bin/sh

AWS_ROOT_PATH=$1

for line in `cat huc6.list`; do
  ./prepare_data.sh ${line} $AWS_ROOT_PATH
  rm -rf /tmp/${line}*
done
