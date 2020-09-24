import datetime
import json
import logging
import sys

import requests

SENTINEL_HUB_HOSTNAME = "https://services.sentinel-hub.com"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


def get_session(oauth_id, oauth_secret):
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


def stac_search(bbox, collection, date_min, date_max, session):
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

    VALID_COLLECTIONS = set(['sentinel-1-grd', 'sentinel-2-l2a', 'sentinel-2-l1c'])
    if collection not in VALID_COLLECTIONS:
        raise ValueError("stac_search collection must be one of {}".format(VALID_COLLECTIONS))

    date_min_str = date_min.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_max_str = date_max.strftime("%Y-%m-%dT%H:%M:%SZ")
    datetime_str = "{}/{}".format(date_min_str, date_max_str)
    parameters = {
        "fields": {"include": ["properties.eo:gsd"]},
        "datetime": datetime_str,
        "collections": [collection],
        "bbox": bbox,
    }
    logger.debug("search_sentinelhub_s1 params: {}".format(parameters))
    encoded = json.dumps(parameters).encode("utf-8")
    return session.post(
        "{}/api/v1/catalog/search".format(SENTINEL_HUB_HOSTNAME), data=encoded,
    )
