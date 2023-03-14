import io
import logging
import os
import pathlib
import pprint
import sys

import peewee
import requests

_logger = logging.getLogger(__name__)

outfile = pathlib.Path("geo.sh")
request_url = "https://api.ip2location.io"
session = requests.Session()

db = peewee.SqliteDatabase("geo.db")


class IP2L(peewee.Model):
    ip = peewee.CharField()
    country_code = peewee.CharField(null=True)
    country_name = peewee.CharField(null=True)
    region_name = peewee.CharField(null=True)
    city_name = peewee.CharField(null=True)
    latitude = peewee.CharField(null=True)
    longitude = peewee.CharField(null=True)
    zip_code = peewee.CharField(null=True)
    time_zone = peewee.CharField(null=True)
    asn = peewee.CharField(null=True)
    as_ = peewee.CharField(null=True)
    is_proxy = peewee.CharField(null=True)

    class Meta:
        database = db  # see module level db var
        db_table = "geo"


def ip_geolocation(ips: list[str]) -> dict:
    def quick_check(ips):
        vfile = io.StringIO("")

        vfile.write("#!/usr/bin/env bash")
        vfile.write("\n")

        for ip in ips:
            out = f"""
            curl 'https://api.ip2location.io/?key={key}&ip={ip}'
            """
            out = out.strip()
            vfile.write(out)

            vfile.write("\n")
            vfile.write("echo")

            vfile.write("\n")
        return vfile

    key = get_api_key_from_env()

    _logger.debug("quick check")
    strio = quick_check(ips).getvalue()
    debug = f"\n{strio}"

    outfile.write_text(debug)

    _logger.debug(debug)


def get_api_key_from_env() -> str:
    key = os.getenv("VAR_IP2LOCATION_API_KEY", None)

    if not key:
        raise ValueError("VAR_IP2LOCATION_API_KEY")

    return key


def fetch_data_for_ip(ip: str, api_key: str) -> dict:
    payload = {
        "key": api_key,
        "ip": ip,
    }

    try:
        response = requests.get(request_url, params=payload, timeout=5)
        _logger.debug(f"{response.url=}")

        # Raises a HTTPError if the status is 4xx, 5xxx
        response.raise_for_status()

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.critical(f"can't reach {request_url}")
        sys.exit(-1)

    except requests.exceptions.HTTPError:
        _logger.critical("4xx, 5xx")
        raise

    else:
        _logger.debug(f"Great!  I'm able to reach {request_url}")

    _logger.debug(response.text)

    return response.json()


if __name__ == "__main__":
    IP2L.create_table()
    api_key = get_api_key_from_env()
    ips = [
        "104.149.140.130",
        "172.30.0.119",
        "172.30.0.19",
        "172.30.0.201",
        "172.30.0.215",
        "172.30.0.235",
        "172.30.0.249",
        "172.30.0.30",
        "172.30.1.120",
        "172.30.1.132",
        "172.30.1.144",
        "172.30.1.146",
        "172.30.1.162",
        "172.30.1.236",
        "174.195.132.192",
        "174.236.100.88",
        "174.243.177.111",
        "174.243.181.106",
        "174.243.245.199",
        "174.61.166.74",
        "184.72.223.50",
        "24.56.229.65",
        "44.205.139.197",
        "89.189.176.193",
        "96.79.192.49",
        "98.97.56.92",
    ]

    for ip in ips:
        records = IP2L.select().where(IP2L.ip == ip).dicts()
        for row in records:
            pprint.pprint(row)

        if not records:
            dct = fetch_data_for_ip(ip, api_key)
            dct["as_"] = dct["as"]
            del dct["as"]
            pprint.pprint(dct)
            ipl = IP2L(**dct)
            ipl.save()
