# NOAA Flood STAC Catalogs

This folder contains a number of subprojects that generate STAC Catalogs for individual datasets identified as useful for this project.

In order to generate a STAC Catalog for any of the subprojects contained in a subfolder, run:

```shell
docker-compose run --rm catalogs <subfolder>
```

For example, to generate a STAC Catalog for the HAND dataset, run:

```shell
docker-compose run --rm catalogs HAND
```

Upon catalog generation, the catalog for each subproject should be available at `<subproject>/data/catalog`.

For more information about each subproject, check each project's README.

## Adding a new Catalog

If you want to build a new STAC Catalog for some data source, create a new subfolder and add an executable `main.sh` there, which serves as the entrypoint for whatever you need to do. For consistency, the STAC Catalog should be written to `<subfolder>/data/catalog`. Any data that needs to be downloaded to generate the catalog should be placed in `<subfolder>/data` and gitignored.

If your project requires additional python dependencies, add them to the `requirements.txt` in this folder and rebuild the catalogs container with `docker-compose build catalogs`.

## Hosted Catalogs

| name                              | location                                                                                           | description                                                                          |
| --------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| HAND                              | s3://hand-data/catalog.tar.gz                                                                      | Height Above Nearest Drainage (derived from https://cfim.ornl.gov/data/)             |
| Mississippi monthly water         | s3://global-surface-water/monthly/mississippi-river/global-water-monthly-catalog.tar.gz            | JRC Global Surface Water monthly observations of the Mississippi river region        |
| Sen1Floods11                      | s3://sen1floods11-data/stac-catalog.zip                                                            | Sen1Floods11 dataset (https://github.com/cloudtostreet/Sen1Floods11)                 |
| Sen1Floods11 s1weak ML            | s3://sen1floods11-data/mldata_s1weak_sen1.tar.gz                                                   | Sen1Floods11 imagery (w/ weak labels derived from Sentinel-1)                        |
| Sen1Floods11 s2weak ML            | s3://sen1floods11-data/mldata_s2weak_sen1.tar.gz                                                   | Sen1Floods11 imagery (w/ weak labels derived from Sentinel-2)                        |
| Sen1Floods11 hand ML              | s3://sen1floods11-data/mldata_hand_sen1.tar.gz                                                     | Sen1Floods11 imagery (w/ hand-made labels)                                           |
| Copernicus EMSR                   | https://github.com/azavea/noaa-flood-mapping/files/5279206/sentinel2-cems-rapid-mapping-floods.zip | Copernicus Emergency Management Service early warning system (floods)                |
| GLOFIMR Correlated SAR            | s3://glofimr-sar-4326/glofimr-sar-catalog.zip                                                      | S1 SAR imagery corresponding to flood IDs 1, 2, 3, 15, and 16 of the GLOFIMR dataset |
| GLOFIMR + SAR ML (vector)         | s3://usfimr-s1-mldata/usfimr-s1-mldata-catalog_seed42.tar.gz                                       | S1 SAR imagery + GLOFIMR vector labels                                               |
| GLOFIMR and JRC + SAR ML (raster) | s3://jrc-fimr-rasterized-labels/version2/usfimr-mldata-catalog-tif.tar.gz                          | S1 SAR imagery + GLOFIMR and >50% occurence global surface water raster labels       |
