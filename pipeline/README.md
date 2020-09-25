# Training a Torch Model Locally

Build the docker container, which upgrades pystac to 0.5.2 for compatibility with the catalogs generated in [catalogs](../catalogs).

```bash
docker build . --tag raster-vision:pytorch-pystac-b8e8c65
```

For STAC-creation instructions, please refer to [this page](../catalogs/sen1floods11-mldata/README.md) for instructions on how to build the STAC.

Start the container ensuring:

1. that environment variables are appropriately set to generate Raster Vision configuration.
2. that volume mounts are set such that `pipeline.py` and the machine learning STAC is accessible from within the container. Make sure that the `CATALOG_ROOT_URI` variable points to the machine learning STAC root mounted within the container.
3. that if documents are referred to using S3 URIs within the ML STAC, `~/.aws` is mounted to `/root/.aws` so that credentials are accessible within the container (if this is the case, be sure to run `aws configure` from within the container prior to running your Raster Vision job)

```bash
docker run -it --rm -v $HOME/.aws:/root/.aws:ro -w /workdir raster-vision:pytorch-pystac-b8e8c65 bash
```

Within the container, run the Raster Vision, pointing the process to file `usfimr_pipeline.py`. (Remember to run `aws configure` for credentials if necessary!)

```bash
rastervision run batch /workdir/usfimr_pipeline.py -a root_uri s3://mybucket/mypath/hand/ -a catalog_root /vsitar//vsis3/mybucket/catalogs.tar/mldata_hand/catalog.json -a epochs 1
```
