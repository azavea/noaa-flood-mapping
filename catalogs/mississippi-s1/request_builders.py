import datetime
import json
import logging
import sys
import time

import requests

SENTINEL_HUB_HOSTNAME = "https://services.sentinel-hub.com"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_sentinel_hub_session(oauth_id, oauth_secret):
    response = requests.post(
        "{}/oauth/token".format(SENTINEL_HUB_HOSTNAME),
        data={
            "grant_type": "client_credentials",
            "client_id": oauth_id,
            "client_secret": oauth_secret,
        },
    )
    if response.status_code == 200:
        one_hour_later = datetime.datetime.now() + datetime.timedelta(hours=1)
        logger.info(
            "Logged in. Sentinel-Hub session valid until {}".format(one_hour_later)
        )
        access_token = response.json()["access_token"]
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": "Bearer {}".format(access_token),
                "Content-Type": "application/json",
            }
        )
        return session
    else:
        sys.exit(
            "Failure to acquire Sentine-Hub token. Status: {}".format(
                response.status_code
            )
        )


def search_sentinelhub_s1(date_min, date_max, bbox, session):
    """ Example curl:
        curl -X "POST" "https://services.sentinel-hub.com/api/v1/catalog/search" \
            -H 'Content-Type: application/json' \
            -H 'Authorization: Bearer <token>' \
            -d $'{
                "limit": 1,
                "fields": {
                    "include": [
                        "properties.eo:gsd"
                    ]
                },
                "datetime": "2019-05-22T00:00:00Z/2019-05-23T00:00:00Z",
                "collections": [
                    "sentinel-1-grd"
                ],
                "bbox": [
                    -94.3670654296875,
                    38.371808917147554,
                    -95.712890625,
                    40.30885442563764
                ]
            }'
    """
    datetime_str = "{}Z/{}Z".format(date_min.isoformat(), date_max.isoformat())
    parameters = {
        "limit": 300,
        "fields": {"include": ["properties.eo:gsd"]},
        "datetime": datetime_str,
        "collections": ["sentinel-1-grd"],
        "bbox": bbox,
    }
    logger.debug("search_sentinelhub_s1 params: {}".format(parameters))
    encoded = json.dumps(parameters).encode("utf-8")
    return session.post(
        "{}/api/v1/catalog/search".format(SENTINEL_HUB_HOSTNAME),
        data=encoded,
    )


def create_batch_request(bbox, min_date, max_date, ingest_path, session):
    with open("ingest_s1_evalscript.js", "r") as script:
        evalscript = script.read()
    parameters = {
        "tilingGrid": {"id": 0, "resolution": "10"},
        "output": {"cogOutput": True, "defaultTilePath": ingest_path},
        "description": "Batch request for S1 data related to Mississippi river system; month: {}_{}".format(
            min_date.year, min_date.month
        ),
        "processRequest": {
            "input": {
                "bounds": {
                    "bbox": bbox,
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "S1GRD",
                        "processing": {
                            "backCoeff": "SIGMA0_ELLIPSOID",
                            "orthorectify": True,
                        },
                        "dataFilter": {
                            "timeRange": {
                                "from": min_date.isoformat() + "Z",
                                "to": max_date.isoformat() + "Z",
                            },
                            "polarization": "DV",
                            "acquisitionMode": "IW",
                            "resolution": "HIGH",
                        },
                    }
                ],
            },
            "evalscript": evalscript,
            "output": {
                "responses": [
                    {"format": {"type": "image/tiff"}, "identifier": "VV"},
                    {"format": {"type": "image/tiff"}, "identifier": "VH"},
                    {"format": {"type": "image/tiff"}, "identifier": "MASK"},
                ]
            },
        },
    }
    encoded = json.dumps(parameters).encode("utf-8")

    creation_request = session.post(
        "{}/api/v1/batch/process/".format(SENTINEL_HUB_HOSTNAME), data=encoded
    )
    return creation_request


def check_batch_status(request_id, session):
    """
    GET https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>
    """
    return session.get(
        "{}/api/v1/batch/process/{}".format(SENTINEL_HUB_HOSTNAME, request_id)
    )


def analyze_batch_request(request_id, session):
    """
    POST https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>/analyse.
    GET https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>
    """
    session.post(
        "{}/api/v1/batch/process/{}/analyse".format(SENTINEL_HUB_HOSTNAME, request_id)
    )
    for count in range(100):
        check = check_batch_status(request_id, session)
        response_data = check.json()
        status = response_data["status"]
        print("Status check {}/100: {}".format(count, status))
        if status == "ANALYSIS_DONE":
            print(
                "Tile estimate: {tiles} tiles; Value estimate: {value} processing units".format(
                    tiles=response_data["tileCount"],
                    value=response_data["valueEstimate"],
                )
            )
            return check
        elif status == "FAILED":
            print("STATUS: FAILED")
            print(response_data)
            break
        else:
            time.sleep(10)


def initiate_batch_request(request_id, session):
    """
    POST https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>/start
    """
    return session.post(
        "{}/api/v1/batch/process/{}/start".format(SENTINEL_HUB_HOSTNAME, request_id)
    )
