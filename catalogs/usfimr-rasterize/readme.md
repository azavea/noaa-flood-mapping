# USFIMR+JRC Correlated S1 Imagery STAC Catalog

This directory is responsible for producing a rasterized set of labels for flood events from the USFIMR dataset (https://sdml.ua.edu/usfimr/) along with labels for permanent water from the JRC global surface water dataset (https://global-surface-water.appspot.com/download)

In order to generate the data and STAC catalog, the following steps are performed:

1. Threshold JRC global surface water occurrence data to produce a binary approximation of permanent water (>40% has been used for data generated in training).
2. Rasterize USFIMR flood vectors.
3. Merge thresholded JRC global surface water with USFIMR data (steps 1-3 accomplished via `src/main/scala/RasterizeFimrFlood.scala`)
4. Chip out the data according to a USFIMR-S1 training catalog (generated by way of `../usfimr-s1`). Data is chipped out by `src/main/scala/MakeLabelChips.scala`
5. Generate a new STAC by scanning a USFIMR-S1 training catalog (again, generated by way of `../usfimr-s1`)
