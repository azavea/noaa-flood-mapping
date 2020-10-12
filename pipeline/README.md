# Training #

## Build Image ##

```bash
docker build . --tag raster-vision:pytorch-pystac-de47ed3
```

## Build STAC if Necessary ##

For STAC-creation instructions, please refer to [this page](../catalogs/sen1floods11-mldata/README.md) for instructions on how to build the STAC.

## Start Container ##

```bash
docker run -it --rm -v $HOME/.aws:/root/.aws:ro -w /workdir raster-vision:pytorch-pystac-de47ed3 bash
```

## Run Pipeline ##

```bash
rastervision run inprocess /workdir/usfimr_vector_pipeline.py -a root_uri /tmp/usfimr/ -a catalog_root /vsitar/vsigzip/vsis3/usfimr-s1-mldata/usfimr-s1-mldata-catalog_seed42.tar.gz/mldata-catalog/catalog.json
rastervision run inprocess /workdir/usfimr_raster_pipeline.py -a root_uri /tmp/usfimr/ -a catalog_root /vsitar/vsigzip/vsis3/jrc-fimr-rasterized-labels/version2/usfimr-mldata-catalog-tif.tar.gz/usfimr-mldata-catalog-tif/catalog.json
```
