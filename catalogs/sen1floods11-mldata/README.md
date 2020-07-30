# Sen1Floods11 ML Data Catalog

This catalog is a mapping of the sen1floods11 catalog written in `../sen1floods11` that can be read by RasterVision in order to train ML models.

## Layout

The catalog generated in this directory has the following schema:

```
Root Catalog
  -> Collection: "train", properties: { "label:classes" }
    -> Item: "scene"
      -> Asset: "image"
      -> Asset: "labels"
  -> Collection: "test", properties: { "label:classes" }
    -> Item: "scene"
      -> Asset: "image"
      -> Asset: "labels"
```

A catalog can be generated for each of the following sen1floods11 experiments:

- S1 weakly labeled
- S2 weakly labeled
- Hand labeled
- Permanent water
