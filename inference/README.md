# Training a Torch Model Locally

Build the docker container, which upgrades pystac to 0.4.0 for compatibility with the catalogs generated in [catalogs](../catalogs).

```bash
docker build . --tag raster-vision:pytorch-pystac-v0.4.0
```

Start the container ensuring:

1. that environment variables are appropriately set to generate Raster Vision configuration.
2. that volume mounts are set such that `rv_stac_config.py` and the machine learning STAC is accessible from within the container. Make sure that the `CATALOG_ROOT_URI` variable points to the machine learning STAC root mounted within the container.
3. that if documents are referred to using S3 URIs within the ML STAC, `~/.aws` is mounted to `/root/.aws` so that credentials are accessible within the container (if this is the case, be sure to run `aws configure` from within the container prior to running your Raster Vision job)

```bash
docker run --rm -it \
  -e OUTPUT_ROOT_URI=/opt/data/output \
  -e CATALOG_ROOT_URI=/opt/src/code/ml_stac/catalog.json \
  -v ~/.aws:/root/.aws \
  -v ${RV_CODE_DIR}:/opt/src/code \
  -v ${RV_OUT_DIR}:/opt/data/output \
  raster-vision:pytorch-pystac-v0.4.0 /bin/bash
```

Within the container, run the Raster Vision process locally, pointing the process to `rv_stac_config.py`. (Remember to run `aws configure` for credentials if necessary!)

```bash
rastervision run local /opt/src/code/rv_stac_config.py
```
