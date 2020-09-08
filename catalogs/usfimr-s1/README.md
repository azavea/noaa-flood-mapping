# USFIMR Correlated S1 Imagery STAC Catalog

This project is responsible for generating an S1 dataset correlated with [USFIMR floods](https://cfim.ornl.gov/data/) and the HAND dataset. Then it generates the corresponding STAC catalog.

In order to generate the data and STAC catalog, the following steps are performed:

1. Compute intersection of S1 chips and USFIMR dataset via the SentinelHub Search API (`ingest_s1.py`)
1. Retrieve orthorectified S1 GRD chips intersecting each USFIMR flood area via the SentinelHub Batch API, saved to an S3 bucket (`ingest_s1.py`)
1. Reproject SentinelHub S1 GRD chips to 4326 and save to an S3 bucket (`reproject_tiffs.sh`)
1. Generate STAC Catalog automatically by scanning the bucket containing the 4326 S1 GRD chips (`build_catalog.py`). The catalog is written to `./data/catalog`.

`main.sh` serves as an example of how to run each of these scripts in sequence to achieve the desired output.

Once the prerequisites described below are in place, the pipeline can be run with `docker-compose run --rm catalogs usfimr-s1`.

## Prerequisites

### Data Ingest -- SentinelHub Account

A Sentinel Hub account with beta access to batch requests is necessary to complete the ingest. Once that is available, an oauth client can be generated from within the user dashboard. This will provide a user ID and a secret which jointly are sufficient to generate the token we will need to carry out Sentinel Hub API calls. Set these credentials in your shell environment as `SENTINELHUB_OAUTH_ID` and `SENTINELHUB_OAUTH_SECRET`.

### Data Ingest -- SentinelHub Output Bucket

Prepare the EU bucket following [these instructions](https://docs.sentinel-hub.com/api/latest/api/batch/#aws-s3-bucket-settings). One such bucket has already been created for those with the credentials to access it: `s3://noaafloodmapping-sentinelhub-batch-eu-central-1`
