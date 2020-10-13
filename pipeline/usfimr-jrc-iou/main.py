""" Generate Intersection over Union for USFIMR + JRC Predictions

Pseudo-code:

for each directory in s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307 (1)
    for each tif in ./predict
        [x] load prediction tif from dir
        [x] load ground truth tif from elsewhere (2)
        [x] load nlcd tif and coregister a VRT matching the prediction tif chip (3)
        [x] create nlcd mask for urban 21 - 24 or not
        [x] convert all above tifs / masks into 1d numpy arrays
        [ ] Compute f1 score for prediction vs ground truth
        [ ] Compute IoU for prediction vs ground truth
        [ ] Compute f1 + IoU only over urban mask
        [ ] Compute f1 + IoU for inverse of urban mask
        [x] Write all computed scores to a row in CSV for the chip id


## Notes:

(1) Naming convention for TT, TF, FT, FF: First T/F is flag for whether HAND was used, Second T/F is flag for whether training is 3 class (perm water + flood water + other) or not (2 class, water + other).

(2) For fimr predictions, use s3://jrc-fimr-rasterized-labels/version2, for sen1floods11 predictionse use sen1floods11-data hand labeled tifs

(3) s3://geotrellis-test/courage-services/nlcd

## Running the Code

This file uses the noaa-catalogs conda env. Conda install <root_dir>/catalogs/requirements-conda.txt into a local conda env then run `python3 main.py` to generate the stats csv.

"""
import argparse
from collections import namedtuple
import csv
import os
from urllib.parse import urlparse

import boto3
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sklearn.metrics import f1_score, jaccard_score

DEFAULT_OUTPUT_CSV = os.path.join("results", "iou-f1-stats.csv")

NLCD_TIF_URI = (
    "s3://geotrellis-test/courage-services/nlcd/NLCD_2016_Land_Cover_L48_20190424.tif"
)

Experiment = namedtuple("Experiment", ["id", "s3_dir", "ground_truth_dir"])

EXPERIMENTS = [
    Experiment(
        "SEN1FLOODS11_HAND",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/SEN1FLOODS11_HAND/",
        "",
    ),
    # No predictions for this experiment...
    # Experiment(
    #     "SEN1FLOODS11_S1WEAK",
    #     "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/SEN1FLOODS11_S1WEAK/",
    #     "",
    # ),
    Experiment(
        "SEN1FLOODS11_S2WEAK",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/SEN1FLOODS11_S2WEAK/",
        "",
    ),
    Experiment(
        "USFIMR_FF",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_FF/",
        "s3://jrc-fimr-rasterized-labels/version2/",
    ),
    Experiment(
        "USFIMR_TF",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TF/",
        "s3://jrc-fimr-rasterized-labels/version2/",
    ),
    Experiment(
        "USFIMR_FT",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_FT/",
        "s3://jrc-fimr-rasterized-labels/version2/",
    ),
    Experiment(
        "USFIMR_TT",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TT/",
        "s3://jrc-fimr-rasterized-labels/version2/",
    ),
    Experiment(
        "USFIMR_TF_analyzed",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TF_analyzed/",
        "s3://jrc-fimr-rasterized-labels/version2/",
    ),
    Experiment(
        "USFIMR_TT_analyzed",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TT_analyzed/",
        "s3://jrc-fimr-rasterized-labels/version2/",
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output-csv", type=str, default=DEFAULT_OUTPUT_CSV)
    args = parser.parse_args()

    client = boto3.client("s3")

    for experiment in EXPERIMENTS:
        print("Processing Experiment: {}".format(experiment.id))
        experiment_url = urlparse(experiment.s3_dir)

        list_result = client.list_objects_v2(
            Bucket=experiment_url.hostname,
            Prefix=os.path.join(experiment_url.path.lstrip("/"), "predict"),
        )
        if list_result["IsTruncated"]:
            raise ValueError("Didn't get all results, implement ContinuationToken")

        try:
            s3_keys = list_result["Contents"]
        except KeyError:
            print("WARNING: No predictions for {}. Continuing...".format(experiment))
            continue

        with open(args.output_csv, "w") as fp_csv:
            csv_fieldnames = [
                "chip_id",
                "f1_all",
                "f1_urban",
                "f1_not_urban",
                "iou_all",
                "iou_urban",
                "iou_not_urban",
            ]
            writer = csv.DictWriter(fp_csv, csv_fieldnames)
            writer.writeheader()

            for obj in s3_keys:
                chip_id = os.path.basename(obj["Key"])
                prediction_tif_uri = "s3://{}/{}".format(
                    experiment_url.hostname, obj["Key"]
                )
                truth_tif_uri = os.path.join(experiment.ground_truth_dir, chip_id)

                with rasterio.open(prediction_tif_uri) as ds_p, rasterio.open(
                    truth_tif_uri
                ) as ds_t, rasterio.open(NLCD_TIF_URI) as ds_nlcd:
                    nlcd_vrt = WarpedVRT(
                        ds_nlcd,
                        crs=ds_p.crs,
                        height=ds_p.height,
                        width=ds_p.width,
                        resampling=Resampling.nearest,
                        transform=ds_p.transform,
                    )

                    p_band = ds_p.read(1).flatten()
                    t_band = ds_t.read(1).flatten()
                    nlcd_band = nlcd_vrt.read(1).flatten()

                nlcd_urban_mask = np.ma.masked_inside(nlcd_band, 21, 24)
                p_band_urban = np.ma.array(p_band, mask=nlcd_urban_mask.mask)
                p_band_not_urban = np.logical_not(p_band_urban)
                t_band_urban = np.ma.array(t_band, mask=nlcd_urban_mask.mask)
                t_band_not_urban = np.logical_not(t_band_urban)

                # TODO: Properly compute these scores by setting labels based on training classes
                scores = {
                    "chip_id": chip_id,
                    "f1_all": f1_score(t_band, p_band),
                    "f1_urban": f1_score(t_band_urban, p_band_urban),
                    "f1_not_urban": f1_score(t_band_not_urban, p_band_not_urban),
                    "iou_all": jaccard_score(t_band, p_band),
                    "iou_urban": jaccard_score(t_band_urban, p_band_urban),
                    "iou_not_urban": jaccard_score(t_band_not_urban, p_band_not_urban),
                }

                writer.writerow(scores)


if __name__ == "__main__":
    main()
