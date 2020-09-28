import argparse
import logging
import sys
from urllib.parse import urlparse

import geopandas as gpd
import pystac

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
        ["id_hand", "hand_uri", "sar_uri"]
    ]
    chips_df.to_csv("./chips.csv", header=False, index_label="sar_id")


if __name__ == "__main__":
    main()
