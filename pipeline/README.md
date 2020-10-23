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
rastervision run inprocess /workdir/sen1floods11_pipeline.py -a root_uri /tmp/sen1floods11/ -a catalog_root /vsitar/vsis3/sen1floods11-data/catalogs.tar/mldata_s1weak/catalog.json
rastervision run inprocess /workdir/usfimr_vector_pipeline.py -a root_uri /tmp/usfimr/ -a catalog_root /vsitar/vsigzip/vsis3/usfimr-s1-mldata/usfimr-s1-mldata-catalog_seed42.tar.gz/mldata-catalog/catalog.json
rastervision run inprocess /workdir/usfimr_raster_pipeline.py -a root_uri /tmp/usfimr/ -a catalog_root /vsitar/vsigzip/vsis3/jrc-fimr-rasterized-labels/version2/usfimr-mldata-catalog-tif.tar.gz/usfimr-mldata-catalog-tif/catalog.json
rastervision run inprocess /workdir/usfimr_inference_pipeline.py -a root_uri /tmp/harvey/ -a analyze_uri /tmp/usfimr/analyze -a train_uri /tmp/usfimr/train -a prefixes harvey.json -a use_hand True -a three_class True predict
```
