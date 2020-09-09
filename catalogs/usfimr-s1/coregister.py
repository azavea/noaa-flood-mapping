import argparse
import logging
import os
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import boto3
import geopandas as gpd
import pystac

from coregister import coregister_raster, coregister_rasters
from stac_utils.dataframes import pystac_catalog_to_dataframe

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


def https_to_s3_url(https_url_str):
    https_url = urlparse(https_url_str)
    bucket, *_ = https_url.netloc.split(".")
    return "s3://{}{}".format(bucket, https_url.path)


def append_s3_uris(row):
    row["hand_uri"] = https_to_s3_url(
        row.get("assets_hand", {}).get("hand", {}).get("href", "")
    )
    row["sar_uri"] = https_to_s3_url(
        row.get("assets_sar", {}).get("MASK", {}).get("href", "")
    )
    return row


def coregister_and_publish_to_s3(row):
    with TemporaryDirectory() as tmp_dir:
        logger.info(
            "Generating coraster for {} using HAND {}".format(row.name, row["id_hand"])
        )
        tmp_file = os.path.join(tmp_dir, "HAND.tif")

        hand_uris = row["hand_uri"]
        sar_uri = row["sar_uri"][0]
        if len(hand_uris) > 1:
            coregister_rasters(hand_uris, sar_uri, tmp_file)
        else:
            coregister_raster(hand_uris[0], sar_uri, tmp_file)

        sar_url = urlparse(sar_uri)
        hand_sar_path = "{}/HAND.tif".format(os.path.dirname(sar_url.path)).lstrip("/")
        s3_client = boto3.client("s3")
        s3_client.upload_file(
            tmp_file,
            sar_url.netloc,
            hand_sar_path,
            ExtraArgs={"ContentType": "image/tiff"},
        )

        output_uri = "{}://{}/{}".format(sar_url.scheme, sar_url.netloc, hand_sar_path)
        logger.info("\tSaved to {}".format(output_uri))
        row["hand_sar_uri"] = output_uri
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--s1-catalog",
        required=True,
        type=str,
        help="Path to catalog generated with build_catalog.py",
    )
    parser.add_argument(
        "--hand-catalog",
        required=True,
        type=str,
        help="Path to HAND Dataset STAC Catalog",
    )
    args = parser.parse_args()

    # Load S1 chips catalog
    sar_catalog = pystac.Catalog.from_file(args.s1_catalog)
    sar_df = pystac_catalog_to_dataframe(sar_catalog)

    # Load HAND catalog
    hand_catalog = pystac.Collection.from_file(args.hand_catalog)
    hand_df = pystac_catalog_to_dataframe(hand_catalog)

    sar_hand_df = gpd.sjoin(
        sar_df, hand_df, op="intersects", how="inner", lsuffix="sar", rsuffix="hand"
    )
    sar_hand_df = sar_hand_df.apply(append_s3_uris, axis=1)
    chips_df = sar_hand_df.groupby("id_sar").agg(list)[
        ["geometry", "id_hand", "hand_uri", "sar_uri"]
    ]

    # Generate the hand corasters
    logger.info("\nGenerating {} corasters...\n".format(len(chips_df)))
    chips_df.apply(coregister_and_publish_to_s3, axis=1)


if __name__ == "__main__":
    main()
