from urllib.parse import urlparse

import geopandas as gpd
import pystac

from stac_df import pystac_catalog_to_dataframe


def https_to_s3_url(https_url_str):
    https_url = urlparse(https_url_str)
    bucket, *_ = https_url.netloc.split(".")
    return "s3://{}{}".format(bucket, https_url.path)


def assets_to_s3_url(row):
    row['assets_hand'] = https_to_s3_url(row.get('assets_hand', {}).get('hand', {}).get('href', ''))
    row['assets_sar'] = https_to_s3_url(row.get('assets_sar', {}).get('sar', {}).get('href', ''))
    return row


def main():
    # Load S1 chips catalog
    sar_catalog = pystac.Catalog.from_file("./data/usfimr-sar-catalog/catalog.json")
    sar_df = pystac_catalog_to_dataframe(sar_catalog, crs="EPSG:32616")
    # TODO: Cleanup -- will eventually already be in 4326
    sar_df = sar_df.to_crs("EPSG:4326")

    # Load HAND catalog
    hand_catalog = pystac.Collection.from_file("./data/hand-catalog/collection.json")
    hand_df = pystac_catalog_to_dataframe(hand_catalog)
    hand_df = hand_df.to_crs("EPSG:4326")

    sar_hand_df = gpd.sjoin(sar_df, hand_df, op="intersects", how="inner", lsuffix="sar", rsuffix="hand")
    sar_hand_df = sar_hand_df[['geometry', 'bbox_sar', 'index_hand', 'assets_hand', 'assets_sar']]
    sar_hand_df = sar_hand_df.apply(assets_to_s3_url, axis=1)

if __name__ == "__main__":
    main()
