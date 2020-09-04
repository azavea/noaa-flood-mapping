import os
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import boto3
import geopandas as gpd
import pystac

from coregister import coregister_raster
from stac_df import pystac_catalog_to_dataframe


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


def coregister_row(row):
    with TemporaryDirectory() as tmp_dir:
        tmp_file = os.path.join(tmp_dir, "HAND.tiff")

        coregister_raster(row["hand_uri"], row["sar_uri"], tmp_file)

        sar_url = urlparse(row["sar_uri"])
        hand_sar_path = "{}/HAND.tiff".format(os.path.dirname(sar_url.path)).lstrip("/")
        s3_client = boto3.client("s3")
        s3_client.upload_file(tmp_file, sar_url.netloc, hand_sar_path)

        output_uri = "{}://{}/{}".format(sar_url.scheme, sar_url.netloc, hand_sar_path)
        print("Saved coraster to {}".format(output_uri))
        row["hand_sar_uri"] = output_uri
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
    sar_hand_df_w_uris = sar_hand_df.apply(append_s3_uris, axis=1)
    print(sar_hand_df_w_uris.head())

    # Generate the hand corasters
    sar_hand_df_w_uris.head().apply(coregister_row, axis=1)


if __name__ == "__main__":
    main()
