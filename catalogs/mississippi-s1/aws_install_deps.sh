#!/bin/sh

# This file is written in anticipation of being run on the AWS version 2 series AMI

sudo yum -y update
sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum-config-manager --enable epel
sudo yum -y install make automake gcc gcc-c++ libcurl-devel proj-devel geos-devel
cd /tmp
curl -L http://download.osgeo.org/gdal/2.4.2/gdal-2.4.2.tar.gz | tar zxf -
cd gdal-2.4.2/
./configure --prefix=/usr/local --without-python
make -j4
sudo make install
cd /usr/local
tar zcvf ~/gdal-2.4.2-amz1.tar.gz *


# Installing gnu-parallel (quick and dirty)
(wget -O - pi.dk/3 || lynx -source pi.dk/3 || curl pi.dk/3/ || fetch -o - http://pi.dk/3 ) > install.sh
bash install.sh