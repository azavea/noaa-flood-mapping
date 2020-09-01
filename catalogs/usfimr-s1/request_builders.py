#!/usr/bin/env python

import urllib3
import datetime
import time
import json
import sys


def get_sentinelhub_token(oauth_id, oauth_secret, connection_pool):
    """ Example curl:
    curl --request POST --url https://services.sentinel-hub.com/oauth/token
            -H "content-type: application/x-www-form-urlencoded"
            -d 'grant_type=client_credentials&client_id=<client_id>'
            --data-urlencode 'client_secret=<client_secret>'
    """
    r = connection_pool.request(
        "POST",
        "/oauth/token",
        encode_multipart=False,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        fields={
            "grant_type": "client_credentials",
            "client_id": oauth_id,
            "client_secret": oauth_secret,
        },
    )
    if r.status == 200:
        one_hour_later = datetime.datetime.now() + datetime.timedelta(hours=1)
        print(
            "Successfully acquired Sentinel-Hub token. It will be valid until {}".format(
                one_hour_later
            )
        )
        return json.loads(r.data.decode("utf-8"))["access_token"]
    else:
        sys.exit("Failure to acquire Sentine-Hub token. Status: {}".format(r.status))


def search_sentinelhub_s1(flood_temporal_bounds, flood_bbox, connection_pool, token):
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
    parameters = {
        "fields": {"include": ["properties.eo:gsd"]},
        "datetime": flood_temporal_bounds,
        "collections": ["sentinel-1-grd"],
        "bbox": flood_bbox,
    }
    encoded = json.dumps(parameters).encode("utf-8")
    r = connection_pool.request(
        "POST",
        "/api/v1/catalog/search",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(token),
        },
        body=encoded,
    )
    return r


def create_batch_request(flood_item, flood_temporal_bounds, connection_pool, token):
    """ Example curl
        curl -X "POST" "https://services.sentinel-hub.com/api/v1/batch/process/" \
            -H 'Authorization: Bearer <token>' \
            -H 'Content-Type: application/json' \
            -d $'{
        "tilingGridId": 0,
        "output": {
            "cogOutput": true,
            "defaultTilePath": "s3://noaafloodmapping-sentinelhub-batch-eu-central-1/<requestId>/<tileName>/<outputId>.tiff"
        },
        "description": "Azavea Test: US KS Flood",
        "processRequest": {
            "input": {
            "bounds": {
                "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                    [
                        -95.712890625,
                        38.371808917147554
                    ],
                    [
                        -94.3670654296875,
                        38.371808917147554
                    ],
                    [
                        -94.3670654296875,
                        40.30885442563764
                    ],
                    [
                        -95.712890625,
                        40.30885442563764
                    ],
                    [
                        -95.712890625,
                        38.371808917147554
                    ]
                    ]
                ]
                },
                "properties": {
                "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                }
            },
            "data": [
                {
                "type": "S1GRD",
                "processing": {
                    "backCoeff": "SIGMA0_ELLIPSOID",
                    "orthorectify": true
                },
                "dataFilter": {
                    "timeRange": {
                    "to": "2020-05-23T00:00:00Z",
                    "from": "2020-05-22T00:00:00Z"
                    },
                    "polarization": "DV",
                    "acquisitionMode": "IW",
                    "resolution": "HIGH"
                }
                }
            ]
            },
            "evalscript": "//VERSION=3\\nfunction setup() {\\n  return {\\n    input: [\\"VV\\", \\"VH\\", \\"dataMask\\"],\\n    output: [{\\n      id: \\"VV\\",\\n      bands: 1,\\n      sampleType: \\"FLOAT32\\"\\n      },{\\n      id: \\"VH\\",\\n      bands: 1,\\n      sampleType: \\"FLOAT32\\"\\n      },{\\n      id: \\"MASK\\",\\n      bands: 1,\\n      sampleType: \\"UINT8\\"}\\n    ]\\n  };\\n}\\n\\nfunction evaluatePixel(samples) {\\n  return {\\n    VV: [samples.VV],\\n    VH: [samples.VH],\\n    MASK: [samples.dataMask]\\n  };\\n}",
            "output": {
            "responses": [
                {
                "format": {
                    "type": "image/tiff"
                },
                "identifier": "VV"
                },
                {
                "format": {
                    "type": "image/tiff"
                },
                "identifier": "VH"
                },
                {
                "format": {
                    "type": "image/tiff"
                },
                "identifier": "MASK"
                }
            ]
            }
        },
        "resolution": "10"
        }'
    """
    with open("ingest_s1_evalscript.js", "r") as script:
        evalscript = script.read()
    parameters = {
        "tilingGrid": {"id": 0, "resolution": "10"},
        "output": {
            "cogOutput": True,
            "defaultTilePath": "s3://noaafloodmapping-sentinelhub-batch-eu-central-1/glofimr/{}/<requestId>/<tileName>/<outputId>.tiff".format(
                flood_item.id
            ),
        },
        "description": "Batch request for S1 data related to {}".format(flood_item.id),
        "processRequest": {
            "input": {
                "bounds": {
                    "geometry": flood_item.geometry,
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
                                "from": flood_temporal_bounds.split("/")[0],
                                "to": flood_temporal_bounds.split("/")[1],
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

    creation_request = connection_pool.request(
        "POST",
        "/api/v1/batch/process/",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(token),
        },
        body=encoded,
    )
    return creation_request


def check_batch_status(request_id, connection_pool, token):
    """
    GET https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>
    """
    return connection_pool.request(
        "GET",
        "/api/v1/batch/process/{}".format(request_id),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(token),
        },
    )


def analyze_batch_request(request_id, connection_pool, token):
    """
        POST https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>/analyse.
        GET https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>
    """
    connection_pool.request(
        "POST",
        "/api/v1/batch/process/{}/analyse".format(request_id),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(token),
        },
    )
    for count in range(100):
        check = check_batch_status(request_id, connection_pool, token)
        response_data = json.loads(check.data.decode("utf-8"))
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


def initiate_batch_request(request_id, connection_pool, token):
    """
    POST https://services.sentinel-hub.com/api/v1/batch/process/<batch_request_id>/start
    """
    return connection_pool.request(
        "POST",
        "/api/v1/batch/process/{}/start".format(request_id),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(token),
        },
    )

