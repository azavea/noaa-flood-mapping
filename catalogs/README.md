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
