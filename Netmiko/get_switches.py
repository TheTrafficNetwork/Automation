import os

import pynetbox
import requests
from dotenv import find_dotenv, load_dotenv
from urllib3.exceptions import InsecureRequestWarning


# Disable warnings for self signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


# Load environment variables
load_dotenv(find_dotenv())


def get_switch_list() -> list:
    """Access a filtered list of network devices from Netbox.

    Returns:
        list: List of network devices.
    """
    NETBOX_API_KEY = os.getenv("NETBOX_API_KEY")
    NETBOX_URL = os.getenv("NETBOX_URL")
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_API_KEY)
    nb.http_session.verify = False
    switch_list = list(
        nb.dcim.devices.filter(
            role="lab-device", manufacturer="cisco", tag=["test"]
        )
    )
    return switch_list
