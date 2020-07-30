# USFIMR STAC Catalog

This project is responsible for generating a STAC catalog for the [USFIMR dataset](https://cfim.ornl.gov/data/)
and for the reprojection and conversion of USFIMR geometries to WKB, WKT, and geojson which serve as assets in
said STAC catalog.

## Building the Catalog

Install all python requirements

```bash
pip3 install -r requirements.txt
```

Run `build_catalog.sh`. This script downloads the dataset, unzips it, and processes it with `build_catalog.py`.
Because `build_catalog.py` is called from within `build_catalog.sh`, it is only necessary to run the bash script.

```bash
./build_catalog.sh
```
