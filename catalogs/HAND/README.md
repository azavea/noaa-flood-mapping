# HAND STAC Catalog

This project is responsible for generating a STAC catalog for the [HAND dataset](https://cfim.ornl.gov/data/)
and cloud optimizing HAND tifs. Because a shapefile has been provided which documents the extent of the data
in the HAND collection, the STAC for this data is generated independently from the data it catalogs.

## COGify tifs and geojson shapefiles

This section serves as documentation for a process completed once on an on-demand AWS EC2 instance in order to populate the `s3://hand-data` bucket.

Once a new AWS instance is launched using an Amazon EC2 Linux AMI, upload the two scripts below and run them there.

```bash
aws_install_gdal.sh
prepare_all_data.sh s3://hand-data
```

### Generate data for a single HUC

For a given HUC `prepare_data.sh` generates the COGs and the geojson we're after. We need only
provide the HUC6 code and the root URI (note the use of an s3 uri instead of an https uri: this allows upload
via `s3 sync`)

```bash
prepare_data.sh 181002 s3://hand-data
```
