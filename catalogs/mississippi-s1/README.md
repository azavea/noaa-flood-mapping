# Mississippi River Correlated S1 Imagery ~~STAC Catalog~~

This project is responsible for generating an S1 dataset correlated with the Mississippi river system for the purposes of training against monthly JRC data. There is currently no corresponding STAC catalog for this imagery. That work will be completed later, in anticipation of training RV models

In order to generate the correctly projected S1 imagery, the following steps are performed:

1a. Compute intersection of S1 chips and the region of interest over the Mississippi river system via the SentinelHub Search API (`ingest_s1.py`)
1b. Retrieve orthorectified S1 GRD chips intersecting each USFIMR flood area via the SentinelHub Batch API, saved to an S3 bucket (also `ingest_s1.py`)

```bash
./ingest_s1.py --oauth-id '<sentinel-hub-oauth-id>' --oauth-secret '<sentinel-hub-oauth-secret>' --sentinelhub-bucket noaafloodmapping-sentinelhub-batch-eu-central-1
```

2a. Boot up an ec2 instance (prefer a large, compute optimized instance as there are many smallish tiffs to work through).
2b. Install GDAL and gnu-parallel (`aws_install_deps.sh`)
2c. Reproject SentinelHub S1 GRD chips to 4326 and save to an S3 bucket (`reproject_tiffs.sh`). This is also a good time to move data outside the EU if that happens to be desirable

```bash
./aws_install_deps.sh
# assuming 36 cores as, e.g., with c5.9xlarge
./reproject_tiffs.sh s3://noaafloodmapping-sentinelhub-batch-eu-central-1/mississippi-surface-water s3://mississippi-sar-4326 36
```

Unlike other subdirectories within `../catalog`, `main.sh` is not used to generate this data. This is because this process is expensive in time and storage costs. Proceed with care.
