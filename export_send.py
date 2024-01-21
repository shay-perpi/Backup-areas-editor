import os
import json

import requests

local_url = os.getenv("local_url", "http://export-backups-route-raster-qa.apps.j1lk3njp.eastus.aroapp.io/webhook")
url_tri = os.getenv("url_trigger",
                    'https://export-management-export-management-route-no-auth-integration.apps.j1lk3njp.eastus.aroapp.io/export-tasks')
header = os.getenv("header", {"Content-Type": "application/json"})
domain = os.getenv("domain", "RASTER")
token = os.getenv("token", None)

if token:
    url_tri += "?token=" + token


def create_data_export(record_id: str, foot_prints, resolution: float, domain: str):
    json_interface = {
        "catalogRecordID": record_id,
        "domain": domain,
        "ROI": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"maxResolutionDeg": resolution},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [foot_prints]
                    }
                }
            ]
        },
        "artifactCRS": "4326",
        "description": "string",
        "keywords": {
            "foo": "ExportBackup"
        },
        "parameters": {
            "foo": "ExportBackup"
        },
        "webhook": [
            {
                "events": [
                    "TASK_COMPLETED"
                ],
                "url": local_url
            }
        ]
    }
    return json_interface


def area_dict(zone_area):
    zones = [create_data_export(area["record_id"], area["Footprint"], float(area["resolutionDeg"]), domain) for area in
             zone_area]
    return zones


def export_to_send(list_of_areas):
    zones = area_dict(list_of_areas)
    url = url_tri
    request_count = 1
    for area in zones:
        resp = requests.post(
            url=url,
            json=area,
            headers=header,
            verify=False
        )
        request_count += 1
    print("End Sending requests successfully")
