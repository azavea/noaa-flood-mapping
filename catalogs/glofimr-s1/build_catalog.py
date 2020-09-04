from functools import partial
import logging
import os
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import boto3
import geopandas as gpd
import progressbar
import pystac

from coregister import coregister_raster
from stac_df import pystac_catalog_to_dataframe

# Must call before setting up logger
progressbar.streams.wrap_stderr()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
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


def coregister_row(progress_bar, row):
    with TemporaryDirectory() as tmp_dir:
        logger.info(
            "Generating coraster for {} using HAND {}".format(
                row["id_sar"], row["id_hand"]
            )
        )
        tmp_file = os.path.join(tmp_dir, "HAND.tif")

        coregister_raster(row["hand_uri"], row["sar_uri"], tmp_file)

        sar_url = urlparse(row["sar_uri"])
        hand_sar_path = "{}/HAND.tif".format(os.path.dirname(sar_url.path)).lstrip("/")
        s3_client = boto3.client("s3")
        s3_client.upload_file(tmp_file, sar_url.netloc, hand_sar_path)

        output_uri = "{}://{}/{}".format(sar_url.scheme, sar_url.netloc, hand_sar_path)
        logger.info("\tSaved to {}".format(output_uri))
        row["hand_sar_uri"] = output_uri
        progress_bar.update(progress_bar.value + 1)
    return row


def main():
    # Load S1 chips catalog
    sar_catalog = pystac.Catalog.from_file("./data/usfimr-sar-catalog/catalog.json")
    sar_df = pystac_catalog_to_dataframe(sar_catalog)

    # Load HAND catalog
    hand_catalog = pystac.Collection.from_file("./data/hand-catalog/collection.json")
    hand_df = pystac_catalog_to_dataframe(hand_catalog)

    sar_hand_df = gpd.sjoin(
        sar_df, hand_df, op="intersects", how="inner", lsuffix="sar", rsuffix="hand"
    )
    sar_hand_df_w_uris = sar_hand_df.apply(append_s3_uris, axis=1).head(3)

    # Generate the hand corasters
    total_count = len(sar_hand_df_w_uris.index)
    bar = progressbar.ProgressBar(
        min_value=0, initial_value=0, max_value=total_count
    ).start()
    sar_hand_df_w_uris.apply(partial(coregister_row, bar), axis=1)
    bar.finish()


if __name__ == "__main__":
    main()
