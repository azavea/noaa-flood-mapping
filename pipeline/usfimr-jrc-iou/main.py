""" Generate Intersection over Union for USFIMR + JRC Predictions

Pseudo-code:

for each directory in s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307 (1)
    for each tif in ./predict
        load prediction tif
        load ground truth tif
        load nlcd tif and coregister a VRT matching the prediction tif chip
        create nlcd mask for urban 21 - 24 or not
        convert all above tifs / masks into 1d numpy arrays
        Compute f1 score for prediction vs ground truth
        Compute IoU for prediction vs ground truth
        Compute f1 + IoU only over urban mask
        Compute f1 + IoU for inverse of urban mask
        Write all computed scores to a row in CSV for the chip id


## Notes:

(1) Naming convention for TT, TF, FT, FF: First T/F is flag for whether HAND was used, Second T/F is flag for whether training is 3 class (perm water (1) + flood water (2) + other) or not (2 class, water (1) + other).

## Running the Code

This file uses the noaa-catalogs conda env. Conda install <root_dir>/catalogs/requirements-conda.txt into a local conda env then run `python3 main.py` to generate the stats csv. Ensure you've send AWS_PROFILE in your shell so that you have access to the necessary s3 directories.

"""
import argparse
from collections import namedtuple
import csv
import logging
import os
import sys
from urllib.parse import urlparse

import boto3
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from sklearn.metrics import f1_score, jaccard_score

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

DEFAULT_OUTPUT_DIR = "results"

NLCD_TIF_URI = (
    "s3://geotrellis-test/courage-services/nlcd/NLCD_2016_Land_Cover_L48_20190424.tif"
)

NODATA = -999

Experiment = namedtuple("Experiment", ["id", "s3_dir", "ground_truth_dir", "labels"])

EXPERIMENTS = [
    Experiment(
        "SEN1FLOODS11_HAND",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/SEN1FLOODS11_HAND/",
        "s3://sen1floods11-data/QC_v2/",
        labels=[1],
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
        "s3://sen1floods11-data/QC_v2/",
        [1],
    ),
    Experiment(
        "USFIMR_FF",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_FF/",
        "s3://jrc-fimr-rasterized-labels/version2/",
        [1],
    ),
    Experiment(
        "USFIMR_TF",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TF/",
        "s3://jrc-fimr-rasterized-labels/version2/",
        [1],
    ),
    Experiment(
        "USFIMR_FT",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_FT/",
        "s3://jrc-fimr-rasterized-labels/version2/",
        [1, 2],
    ),
    Experiment(
        "USFIMR_TT",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TT/",
        "s3://jrc-fimr-rasterized-labels/version2/",
        [1, 2],
    ),
    Experiment(
        "USFIMR_TF_analyzed",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TF_analyzed/",
        "s3://jrc-fimr-rasterized-labels/version2/",
        [1],
    ),
    Experiment(
        "USFIMR_TT_analyzed",
        "s3://noaafloodmap-data-us-east-1/jmcclain/October_13_1307/USFIMR_TT_analyzed/",
        "s3://jrc-fimr-rasterized-labels/version2/",
        [1, 2],
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing CSVs in output dir"
    )
    args = parser.parse_args()

    client = boto3.client("s3")

    for experiment in EXPERIMENTS:
        logger.info("Processing Experiment: {}".format(experiment.id))
        experiment_url = urlparse(experiment.s3_dir)

        output_csv = os.path.join(
            args.output_dir, "{}-iou-f1.csv".format(experiment.id)
        )
        if not args.overwrite and os.path.isfile(output_csv):
            logger.info("SKIPPING Experiment {}. Already exists".format(experiment.id))
            continue

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

        with open(output_csv, "w") as fp_csv:
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
                logger.info("\tprediction: {}".format(prediction_tif_uri))

                # TODO: Encode this in Experiment somehow
                # Replace chip S1 qualifier with QC to match filenames in ground truth dir
                if chip_id.startswith("SEN1FLOODS11"):
                    truth_tif_uri = os.path.join(experiment.ground_truth_dir, chip_id)
                else:
                    chip_name = chip_id.replace("_S1.tif", "_QC.tif")
                    truth_tif_uri = os.path.join(experiment.ground_truth_dir, chip_name)
                logger.info("\ttruth: {}".format(truth_tif_uri))

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
                        nodata=NODATA,
                    )

                    p_band = ds_p.read(1).flatten()
                    t_band = ds_t.read(1).flatten()
                    nlcd_band = nlcd_vrt.read(1).flatten()

                assert len(p_band) == len(t_band)
                assert len(p_band) == len(nlcd_band)

                # TODO: Encode this in Experiment somehow...
                # For two class USFIMR experiments, collapse ground truth three class
                # labels for water to two class: 2 (flood) + 1 (perm) -> 1 (water)
                if experiment.id.startswith("USFIMR") and len(experiment.labels) == 1:
                    t_band = np.where(t_band == 2, 1, t_band)

                nlcd_urban_mask = np.ma.masked_outside(nlcd_band, 21, 24).mask
                p_band_urban = np.ma.array(p_band, mask=nlcd_urban_mask).filled(NODATA)
                t_band_urban = np.ma.array(t_band, mask=nlcd_urban_mask).filled(NODATA)

                nlcd_not_urban_mask = np.ma.masked_inside(nlcd_band, 21, 24).mask
                p_band_not_urban = np.ma.array(p_band, mask=nlcd_not_urban_mask).filled(
                    NODATA
                )
                t_band_not_urban = np.ma.array(t_band, mask=nlcd_not_urban_mask).filled(
                    NODATA
                )

                labels = experiment.labels
                scores = {
                    "chip_id": chip_id,
                    "f1_all": f1_score(t_band, p_band, labels=labels, average=None),
                    "f1_urban": f1_score(
                        t_band_urban, p_band_urban, labels=labels, average=None
                    ),
                    "f1_not_urban": f1_score(
                        t_band_not_urban, p_band_not_urban, labels=labels, average=None
                    ),
                    "iou_all": jaccard_score(
                        t_band, p_band, labels=labels, average=None
                    ),
                    "iou_urban": jaccard_score(
                        t_band_urban, p_band_urban, labels=labels, average=None
                    ),
                    "iou_not_urban": jaccard_score(
                        t_band_not_urban, p_band_not_urban, labels=labels, average=None
                    ),
                }
                logger.debug("\t\t{}".format(scores))
                writer.writerow(scores)

        client.upload_file(
            output_csv,
            experiment_url.hostname,
            os.path.join(experiment_url.path, "stats-iou-f1.csv"),
        )


if __name__ == "__main__":
    main()
