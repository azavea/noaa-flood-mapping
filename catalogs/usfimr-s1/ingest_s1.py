#!/usr/bin/env python3

import argparse
from datetime import date, time, datetime
import logging
import sys

from area import area
import boto3
from pystac import Collection

from request_builders import (
    get_sentinel_hub_session,
    search_sentinelhub_s1,
    create_batch_request,
    analyze_batch_request,
    initiate_batch_request,
    check_batch_status,
)
from stac_utils.s3_io import register_s3_io

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


def get_flood_temporal_bounds(flood):
    flood_date = date.fromisoformat(flood.properties["Flood_Date"])
    flood_start_time = time.fromisoformat(flood.properties["Start_Time"])
    flood_end_time = time.fromisoformat(flood.properties["End_Time"])
    date_min = datetime.combine(flood_date, flood_start_time)
    date_max = datetime.combine(flood_date, flood_end_time)

    return date_min, date_max


def make_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--oauth-id",
        required=True,
        type=str,
        help="OAuth ID for requesting an authorization token",
    )
    parser.add_argument(
        "--oauth-secret",
        required=True,
        type=str,
        help="OAuth secret for requesting an authorization token",
    )
    parser.add_argument(
        "--sentinelhub-bucket",
        required=True,
        type=str,
        help="The bucket that should contain the output of the SentinelHub Batch Ingests",
    )
    return parser


if __name__ == "__main__":
    parser = make_parser()
    args = parser.parse_args()

    # Register methods for IO to/from S3
    register_s3_io()

    session = get_sentinel_hub_session(args.oauth_id, args.oauth_secret)

    # Read STAC from S3
    usfimr_collection = Collection.from_file("s3://usfimr-data/collection.json")
    usfimr_floods = usfimr_collection.get_items()

    # Iterate through GLOFIMR flood events
    flood_with_results = []
    for flood in usfimr_floods:
        # geom bounds
        flood_bounds = flood.bbox

        # temporal bounds
        date_min, date_max = get_flood_temporal_bounds(flood)
        search_results = search_sentinelhub_s1(
            date_min, date_max, flood_bounds, session
        )
        search_results = search_results.json()

        result_count = search_results["context"]["returned"]
        if result_count > 0:
            flood_with_results.append(flood)
            logger.info(
                "{result_count} results for USFIMR ID={flood_id}".format(
                    result_count=result_count, flood_id=flood.id
                )
            )
            # Estimate sq km of coverage
            logger.debug(
                "km2 of labelled region (estimated from convex hull of labels): {}".format(
                    area(flood.geometry) / 1000,
                )
            )
            logger.debug("km2 of flooding: {}".format(flood.properties["Flood_km2"]))

        else:
            logger.debug(
                "No S1 results found for USFIMR ID={flood_id}".format(flood_id=flood.id)
            )

    s3 = boto3.resource("s3")
    bucket = s3.Bucket(args.sentinelhub_bucket)

    for i, flood in enumerate(flood_with_results):

        # Check if data is already loaded
        filtered_bucket_contents = bucket.objects.filter(
            Prefix="glofimr/{}/".format(flood.id)
        )
        already_loaded = False
        for key in filtered_bucket_contents:
            already_loaded = True
            break

        if already_loaded:
            logger.info("Flood {} already ingested, skipping".format(flood.id))
        else:
            logger.info("Flood {} not ingested, ingesting".format(flood.id))
            # temporal bounds
            date_min, date_max = get_flood_temporal_bounds(flood)
            batch_ingest_path = "s3://{}/glofimr/{}/<tileName>/<outputId>.tiff".format(
                bucket.name, flood.id
            )
            batch_creation_request = create_batch_request(
                flood, date_min, date_max, batch_ingest_path, session
            )
            batch_creation_response = batch_creation_request.json()
            batch_request_id = batch_creation_response["id"]
            logger.info("Flood {} ingest ID: {}".format(flood.id, batch_request_id))

            analyze_batch_request(batch_request_id, session)

            initiate_batch_request(batch_request_id, session)

            for count in range(100):
                status_response = check_batch_status(batch_request_id, session)
                status_response_data = status_response.json()
                status = status_response_data["status"]

                if status == "DONE":
                    logger.info(
                        "Flood ingest for ID {} completed successfully.".format(
                            flood.id
                        )
                    )
                    logger.info("SUCCESSFUL REQUEST ID: {}".format(batch_request_id))
                    logger.info("Data ingested to {}".format(batch_ingest_path))
                    break
                elif status == "FAILED":
                    logger.error("Flood ingest for ID {} FAILED".format(flood.id))
                    logger.debug(status_response_data)
