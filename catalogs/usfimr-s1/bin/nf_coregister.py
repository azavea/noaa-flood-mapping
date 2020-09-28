import csv
import json
import logging
import os
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import boto3

from coregister import coregister_raster, coregister_rasters


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


def coregister_and_publish_to_s3(sar_id, hand_id, sar_uri, hand_uris):
    with TemporaryDirectory() as tmp_dir:
        logger.info("Generating coraster for {} using HAND {}".format(sar_id, hand_id))
        tmp_file = os.path.join(tmp_dir, "HAND.tif")

        if len(hand_uris) > 1:
            coregister_rasters(hand_uris, sar_uri, tmp_file)
        else:
            coregister_raster(hand_uris[0], sar_uri, tmp_file)

        sar_url = urlparse(sar_uri)
        hand_sar_path = "{}/HAND-nftest.tif".format(
            os.path.dirname(sar_url.path)
        ).lstrip("/")
        s3_client = boto3.client("s3")
        s3_client.upload_file(
            tmp_file,
            sar_url.netloc,
            hand_sar_path,
            ExtraArgs={"ContentType": "image/tiff"},
        )

        output_uri = "{}://{}/{}".format(sar_url.scheme, sar_url.netloc, hand_sar_path)
        logger.info("\tSaved to {}".format(output_uri))


def main():
    reader = csv.reader(sys.stdin)
    for line in reader:
        coregister_and_publish_to_s3(
            line[0],
            json.loads(line[1].replace("'", '"')),
            json.loads(line[3].replace("'", '"'))[0],
            json.loads(line[2].replace("'", '"')),
        )


if __name__ == "__main__":
    main()
