# USFIMR Correlated S1 Imagery STAC Catalog

This project is responsible for generating an S1 dataset and the corresponding STAC catalog. This S1
imagery is correlated with any matching floods from the [USFIMR dataset](https://cfim.ornl.gov/data/).

## Data ingest

A Sentinel Hub account with beta access to batch requests is necessary to complete the ingest. Once
that is available, an oauth client can be generated from within the user dashboard. This will provide
a user ID and a secret which jointly are sufficient to generate the token we will need to carry out
Sentinel Hub API calls.

Kick off the data ingest like this:

```bash
./ingest_s1.py --oauth-id '<user-id>' --oauth-secret '<user-secret>'
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
