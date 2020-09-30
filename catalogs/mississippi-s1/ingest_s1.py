#!/usr/bin/env python3

import argparse
from datetime import date, time, datetime
import logging
import sys

import boto3
from dateutil import rrule, relativedelta

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

    # Set S3 write directory
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(args.sentinelhub_bucket)

    session = get_sentinel_hub_session(args.oauth_id, args.oauth_secret)

    # geom bounds
    bbox = [
        -88.02592402528022,
        29.038948834106055,
        -92.72807246278022,
        42.55475543734189,
    ]

    # temporal bounds
    # The JRC water dataset examines imagery from march, 1984 to december, 2019
    # S1 coverage starts in 2016 and, in this region, November
    date_iter_start = datetime.combine(date(2016, 11, 1), time.min)
    date_iter_end = datetime.combine(date(2019, 12, 1), time.min)

    for dt_min in rrule.rrule(
        rrule.MONTHLY, dtstart=date_iter_start, until=date_iter_end
    ):
        month_name = "{year}_{month}".format(year=dt_min.year, month=dt_min.month)
        dt_max = dt_min + relativedelta.relativedelta(
            day=31, hour=23, minute=59, second=59
        )
        search_results = search_sentinelhub_s1(dt_min, dt_max, bbox, session)
        search_results = search_results.json()

        result_count = search_results["context"]["returned"]
        if result_count > 0:
            logger.info(
                "{result_count} results for {month}".format(
                    result_count=result_count, month=month_name
                )
            )

        else:
            logger.info("No S1 results found for {month}".format(month=month_name))
            continue

        # Check if data is already loaded
        ingest_prefix = "mississippi-surface-water/{month}/".format(month=month_name)
        filtered_bucket_contents = bucket.objects.filter(Prefix=ingest_prefix)
        already_loaded = False
        for key in filtered_bucket_contents:
            already_loaded = True
            break

        if already_loaded:
            logger.info("Month {} already ingested, skipping".format(month_name))
        else:
            logger.info("Month {} not ingested, ingesting".format(month_name))
            # temporal bounds
            batch_ingest_path = (
                "s3://{bucket}/{ingest_prefix}<tileName>/<outputId>.tiff".format(
                    bucket=bucket.name, ingest_prefix=ingest_prefix
                )
            )
            batch_creation_request = create_batch_request(
                bbox, dt_min, dt_max, batch_ingest_path, session
            )
            batch_creation_response = batch_creation_request.json()
            batch_request_id = batch_creation_response["id"]
            logger.info("Month: {}; ingest ID: {}".format(month_name, batch_request_id))

            analyze_batch_request(batch_request_id, session)

            initiate_batch_request(batch_request_id, session)

            for count in range(100):
                status_response = check_batch_status(batch_request_id, session)
                status_response_data = status_response.json()
                status = status_response_data["status"]

                if status == "DONE":
                    logger.info(
                        "S1 ingest for {} completed successfully.".format(month_name)
                    )
                    logger.info("SUCCESSFUL REQUEST ID: {}".format(batch_request_id))
                    logger.info("Data ingested to {}".format(batch_ingest_path))
                    break
                elif status == "FAILED":
                    logger.info("S1 ingest for {} FAILED".format(month_name))
                    logger.debug(status_response_data)