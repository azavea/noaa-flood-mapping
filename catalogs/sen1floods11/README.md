# sen1floods11 STAC Catalog

This project is responsible for generating a STAC catalog for the [sen1floods11 dataset](https://github.com/cloudtostreet/Sen1Floods11).

## Building

Before building for the first time:

- [ ] Install all project dependencies (into a virtualenv for best results) with `pip3 install -r requirements.txt`
- [ ] Ensure you have AWS credentials that can access `s3://sen1floods11-data`

Once first time setup is complete, you can rebuild the catalog at any time with:

```bash
AWS_PROFILE=<profile> python3 build.py
```
