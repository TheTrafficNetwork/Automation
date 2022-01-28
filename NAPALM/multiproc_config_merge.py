import os
from concurrent.futures import ProcessPoolExecutor
from getpass import getpass

import pynetbox
import requests
from dotenv import find_dotenv, load_dotenv
from napalm import get_network_driver
from napalm.base.exceptions import MergeConfigException
from urllib3.exceptions import InsecureRequestWarning


# Disable warnings for self signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


# Load environment variables
load_dotenv(find_dotenv())


# Static Objects
USERNAME = (
    os.getenv("LAB_USER") if os.getenv("LAB_USER") else input("Username: ")
)
PASSWORD = (
    os.getenv("LAB_PASSWORD")
    if os.getenv("LAB_PASSWORD")
    else getpass("Password: ")
)
SECRET = (
    os.getenv("LAB_SECRET")
    if os.getenv("LAB_SECRET")
    else getpass("Enable Secret: ")
)
optional_args = {"secret": SECRET, "conn_timeout": 15}
CONFIG = os.getenv("NAPALM_CONFIG_FILE")
driver = get_network_driver("ios")


def get_switch_list():
    NETBOX_API_KEY = os.getenv("LAB_NETBOX_API_KEY")
    NETBOX_URL = os.getenv("LAB_NETBOX_URL")
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_API_KEY)
    nb.http_session.verify = False
    switch_list = list(
        nb.dcim.devices.filter(tag="napalm", manufacturer="cisco")
    )
    return switch_list


def napalm_merge(address, driver=driver, config=CONFIG):
    with driver(
        hostname=address,
        username=USERNAME,
        password=PASSWORD,
        optional_args=optional_args,
    ) as device:
        try:
            device.load_merge_candidate(filename=config)
            device.commit_config()
            print(f"Config merged for {address}.")
        except MergeConfigException:
            print(f"MERGE FAILED FOR {address}!!!!")


if __name__ == "__main__":
    switch_list = get_switch_list()
    future_list = [
        str(switch.primary_ip).split("/")[0] for switch in switch_list
    ]
    max_procs = 20
    with ProcessPoolExecutor(max_procs) as pool:
        results = pool.map(napalm_merge, future_list)
