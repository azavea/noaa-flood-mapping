# Sen1Floods11 ML Data Catalog

This catalog is a mapping of ML experiments in the sen1floods11 catalog written in `../sen1floods11` that can be read by RasterVision in order to train ML models.

## Getting Started

Pull down the sen1floods11 catalog to the `./data` folder:

```
aws s3 cp s3://sen1floods11-data/stac-catalog.zip ./data/
cd data && unzip stac-catalog.zip
```

Install python dependencies `pip install -r requirements.txt`.

Run `python main.py <experiment>`. Run with `--help` to see possible values for `<experiment>`.

## Layout

The catalog generated in this directory has the following schema:

```
Root Catalog
  -> Collection: "train", properties: { "label:classes" }
    -> Item: "scene", "geometry": <raster footprint>, "datetime": <raster creation time>, ...
      -> Asset: "image"
      -> Link: rel=labels, <Label STAC Item in "labels" Collection>
      -> Link: rel=labels, <Label STAC Item in "labels" Collection>
      -> Link: rel=labels, <Label STAC Item in "labels" Collection>
      -> ...
  -> Collection: "test", properties: { "label:classes" }
    -> Item: "scene", "geometry": <raster footprint>, "datetime": <raster creation time>, ...
      -> Asset: "image"
      -> Link: rel=labels, <Label STAC Item in "labels" Collection>
      -> Link: rel=labels, <Label STAC Item in "labels" Collection>
      -> Link: rel=labels, <Label STAC Item in "labels" Collection>
      -> ...
  -> Collection: "labels"
    -> Item:
      -> Asset: "labels"
```
