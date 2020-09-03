# USFIMR Correlated S1 Imagery STAC Catalog

This project is responsible for generating an S1 dataset and the corresponding STAC catalog. This S1
imagery is correlated with any matching floods from the [USFIMR dataset](https://cfim.ornl.gov/data/).

## Data ingest

A Sentinel Hub account with beta access to batch requests is necessary to complete the ingest. Once
that is available, an oauth client can be generated from within the user dashboard. This will provide
a user ID and a secret which jointly are sufficient to generate the token we will need to carry out
Sentinel Hub API calls.

Prepare the EU bucket following [these instructions](https://docs.sentinel-hub.com/api/latest/api/batch/#aws-s3-bucket-settings)

Kick off the data ingest like this:

```bash
./ingest_s1.py --oauth-id '<user-id>' --oauth-secret '<user-secret>'
```

At this point, it might be prudent to copy data from the EU region bucket configured above to one which
will cost less for repeated reads/writes. Killing two birds with one stone, the `reproject_tiffs.sh` script
will recursively copy from {INPUT_ROOT} to {OUTPUT_ROOT}, preserving directory structure and reprojecting
tiffs from UTM to 4326 as it goes.

```bash
./reproject_tiffs.sh s3://${EU_BUCKET} s3://${4326-bucket}
```

## Building the Catalog

Install all python requirements

```bash
pip3 install -r requirements.txt
```

Run `build_catalog.py`, providing the s3 root at which images have been ingested. For example

```bash
./build_catalog.py --imagery-root-s3 <s3-path>
```
