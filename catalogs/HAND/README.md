# HAND STAC Catalog

This project is responsible for generating a STAC catalog for the [HAND dataset](https://cfim.ornl.gov/data/)
and cloud optimizing HAND tifs. Because a shapefile has been provided which documents the extent of the data
in the HAND collection, the STAC for this data is generated independently from the data it catalogs.

## Building STAC

Install all python requirements

```bash
pip3 install -r requirements.txt
```

Run `build_catalog.py`, providing the root uri at which this catalog (and the collection it indexes) will sit

```bash
python3 build_catalog.py --root-uri https://hand-data.s3.amazonaws.com
```

## COGify tifs and geojson shapefiles

Conveniently accessing the data we're cataloging will require storage in formats that are designed for access
via the web. Assuming that we're doing this on an ec2 instance, Proj and GDAL dependencies must be installed.
A script has been provided for just this use case:

```bash
aws_install_gdal.sh
```

For a given HUC `prepare_data.sh` generates the COGs and the geojson we're after. We need only
provide the HUC6 code and the root URI (note the use of an s3 uri instead of an https uri: this allows upload
via `s3 sync`)

```bash
prepare_data.sh 181002 s3://hand-data
```

Producing this data for all HUCs is also possible:

```bash
prepare_all_data.sh s3://hand-data
```
