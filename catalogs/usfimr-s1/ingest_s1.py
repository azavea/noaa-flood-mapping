#!/usr/bin/env python3

from datetime import date, time, datetime
import urllib3
import argparse
import json


import boto3
from area import area
from s3_stac_io import register_s3_io
from request_builders import (
    get_sentinelhub_token,
    search_sentinelhub_s1,
    create_batch_request,
    analyze_batch_request,
    initiate_batch_request,
    check_batch_status,
)

from pystac import Collection


def get_flood_temporal_bounds(flood):
    flood_date = date.fromisoformat(flood.properties["Flood_Date"])
    flood_start_time = time.fromisoformat(flood.properties["Start_Time"])
    flood_end_time = time.fromisoformat(flood.properties["End_Time"])
    date_min = datetime.combine(flood_date, flood_start_time)
    date_max = datetime.combine(flood_date, flood_end_time)

    # Widen the min/max to hopefully get more results
    # date_min = date_min - timedelta(hours=24)
    # date_max = date_max + timedelta(hours=24)

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
    return parser


if __name__ == "__main__":
    parser = make_parser()
    args = parser.parse_args()

    # Register methods for IO to/from S3
    register_s3_io()

    # Set up urllib3 connection pool
    http_pool = urllib3.connectionpool.connection_from_url(
        "https://services.sentinel-hub.com"
    )

    # Get token for making further Sentinel-Hub requests
    token = get_sentinelhub_token(args.oauth_id, args.oauth_secret, http_pool)
    print("TOKEN", token)

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
        temporal_bounds_string = (
            date_min.isoformat() + "Z/" + date_max.isoformat() + "Z"
        )

        search_results = search_sentinelhub_s1(
            temporal_bounds_string, flood_bounds, http_pool, token
        )
        search_results = json.loads(search_results.data.decode("utf-8"))

        result_count = search_results["context"]["returned"]
        if result_count > 0:
            flood_with_results.append(flood)
            print(
                "{result_count} results for USFIMR ID={flood_id}".format(
                    result_count=result_count, flood_id=flood.id
                )
            )
            # Estimate sq km of coverage
            print(
                "km2 of labelled region (estimated from convex hull of labels)",
                area(flood.geometry) / 1000,
            )
            print("km2 of flooding", flood.properties["Flood_km2"])

        else:
            print(
                "No S1 results found for USFIMR ID={flood_id}".format(flood_id=flood.id)
            )

    s3 = boto3.resource("s3")
    bucket = s3.Bucket("noaafloodmapping-sentinelhub-batch-eu-central-1")

    for i, flood in enumerate(flood_with_results):

        # Check if data is already loaded
        filtered_bucket_contents = bucket.objects.filter(
            Prefix="glofimr/{}".format(flood.id)
        )
        already_loaded = False
        for key in filtered_bucket_contents:
            already_loaded = True
            break

        if already_loaded:
            print("Flood {} already ingested, skipping".format(flood.id))
        else:
            print("Flood {} not ingested, ingesting".format(flood.id))
            # temporal bounds
            date_min, date_max = get_flood_temporal_bounds(flood)
            temporal_bounds_string = (
                date_min.isoformat() + "Z/" + date_max.isoformat() + "Z"
            )
            batch_creation_request = create_batch_request(
                flood, temporal_bounds_string, http_pool, token
            )
            # from IPython import embed; embed()
            batch_creation_response = json.loads(
                batch_creation_request.data.decode("utf-8")
            )
            batch_request_id = batch_creation_response["id"]

            analyze_batch_request(batch_request_id, http_pool, token)

            initiate_batch_request(batch_request_id, http_pool, token)

            for count in range(100):
                status_response = check_batch_status(batch_request_id, http_pool, token)
                status_response_data = json.loads(status_response.data.decode("utf-8"))
                status = status_response_data["status"]

                if status == "DONE":
                    print(
                        "Flood ingest for ID {} completed successfully.".format(
                            flood.id
                        )
                    )
                    print("SUCCESSFUL REQUEST ID: {}".format(batch_request_id))
                    break
                elif status == "FAILED":
                    print("Flood ingest for ID {} FAILED".format(flood.id))
                    print(status_response_data)

