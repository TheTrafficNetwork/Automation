"""
Takes a list of devices from NetBox with a LibreNMS tag and checks to see if 
they are programmed in LibreNMS. If they are missing, they are then added.
"""

import json
import os

import pynetbox
import requests
from dotenv import find_dotenv, load_dotenv
from sty import fg
from urllib3.exceptions import InsecureRequestWarning

# Disable warnings for self signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


# Load environment variables
load_dotenv(find_dotenv())


def create_missing_devices() -> None:
    """Parse NetBox for a list of all devices in the system.
    Create an instance in LibreNMS for each device.

    Args:
        api_key (str): API key to access LibreNMS.
        api_url (str): API URL for LibreNMS device creation.
    """
    NETBOX_API_KEY = os.getenv("NETBOX_API_KEY")
    NETBOX_URL = os.getenv("NETBOX_URL")
    LIBRENMS_URL = os.getenv("LIBRENMS_URL")
    LIBRENMS_API_KEY = os.getenv("LIBRENMS_API_KEY")
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_API_KEY)
    nb.http_session.verify = False
    device_list = nb.dcim.devices.filter(tag="librenms")
    for device in device_list:
        device_ip = (str(device.primary_ip).split("/"))[0]
        if device_ip == "None":
            color = fg.red
            print(f"{color}{device.name} missing primary ip address.{fg.rs}")
            continue
        check = check_in_librenms(device_ip, LIBRENMS_API_KEY, LIBRENMS_URL)
        if check is False:
            create_librenms_device(device_ip, LIBRENMS_API_KEY, LIBRENMS_URL)


def check_in_librenms(ip: str, api: str, url: str) -> bool:
    """Checks LibreNMS for the existance of a device.

    Args:
        ip (str): IP address of the device to add to LibreNMS.
        api (str): API Key to access LibreNMS.
        url (str): API URL for LibreNMS device creation.

    Returns:
        bool: Boolean response whether the device exists in LibreNMS.
    """
    get_device_url = url + ip
    headers = {"X-Auth-Token": api}
    response = requests.request("GET", get_device_url, headers=headers).json()
    # TODO raise an error for message in response
    return True if response["status"] == "ok" else False


def create_librenms_device(ip: str, api: str, url: str) -> None:
    """Creates a device instance in LibreNMS

    Args:
        ip (str): IP address of the device to add to LibreNMS.
        api (str): API Key to access LibreNMS.
        url (str): API URL for LibreNMS device creation.
    """
    version = "v2c"
    SNMP_COMMUNITY = os.getenv("SNMP_COMMUNITY")
    payload = {"hostname": ip, "version": version, "community": SNMP_COMMUNITY}
    data = json.dumps(payload)
    headers = {"X-Auth-Token": api, "Content-Type": "text/plain"}
    response = requests.request("POST", url, headers=headers, data=data)
    if response.status_code == 200:
        color = fg.green
    elif response.status_code == 500:
        color = fg.yellow
    else:
        color = fg.red
    print(f"{color}{response.text}{fg.rs}")


if __name__ == "__main__":
    create_missing_devices()
