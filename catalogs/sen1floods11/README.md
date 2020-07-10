# sen1floods11 STAC Catalog

This project is responsible for generating a STAC catalog for the [sen1floods11 dataset](https://github.com/cloudtostreet/Sen1Floods11).

## Building

Before building for the first time:

- [ ] Follow the instructions at [Setup Google Authentication](#setup-google-authentication)
- [ ] Install all project dependencies (into a virtualenv for best results) with `pip3 install -r requirements.txt`

Once first time setup is complete, you can rebuild the catalog at any time with:

```bash
python3 build.py
```

### Setup Google Authentication

To generate the STAC Catalog you'll need to setup authentication for Google Cloud Storage client libraries. 

Go [here](https://cloud.google.com/storage/docs/reference/libraries#setting_up_authentication) and follow the instructions to get a "service account key".

Once you have the key, place it at any `[path]` on your hard drive. Then set:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="[PATH]"
```
