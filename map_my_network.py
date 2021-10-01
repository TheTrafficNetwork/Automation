"""
Maping the network starting with a single IP address and gaining the following
information fields by crawling through the network:
    Device Name
    FQDN
    Device Management Interface
    Device Management IP
    Vendor
    Model
    Serial Number
    OS version
    List of Neighbor adjacencies

Utilizes netmiko to gather neighboring ip addresses and napalm for device
information. Scripting assumes you have credentials to all of your devices.
Personalized variables are stored to a .env file in the folder to reference.
"""


# TODO Refactor Code
# TODO Figure out a way to use just NAPALM without the Netmiko addon
# TODO Revisit listing of data to add/remove new fields
# TODO Add localized documentation


import os

import pandas as pd
from dotenv import find_dotenv, load_dotenv
from napalm import get_network_driver
from netmiko import ConnectHandler


def Connect(device_info):
    """Define a Netmiko Session to get the output of "show cdp neighbors detail

    Args:
        device_info (Dictionary): Connection information for network devices

    Returns:
        string: Output from device's cdp neighbors
    """
    with ConnectHandler(**device_info) as session:
        cdp_info = session.send_command("show cdp neighbor detail")
    return cdp_info


def extract_cdp_info(cdp_info, DeviceDict):
    """Extracts neighboring device ip address and hostnames from cdp info

    Args:
        cdp_info (string): Output from device's cdp neighbors
        DeviceDict (dictionary): Dictionary of currently known devices

    Returns:
        dictionary: Updated dictionary with newly discovered devices
    """
    for line in cdp_info.split("\n"):
        if line.startswith("Device ID: "):
            DeviceName = line.split(" ")[-1].split(".")[0]
            if DeviceName in DeviceDict.keys():
                DeviceName = ""
        if ("IP address" in line) and (DeviceName != ""):
            DeviceIP = line.split(" ")[-1]
            DeviceDict.update({DeviceName: {"ip_address": DeviceIP}})
            DeviceName = ""
    return DeviceDict


def get_device_info(driver, ip_address, username, password, args, DeviceDict):
    """Get Device info with NAPALM Getters

    Args:
        driver ([type]): Napalm driver
        ip_address (string): Device ip address
        username (string): Device username
        password (string): Device password
        args (dictionary): Optional arguments for napalm connections
        DeviceDict (dictionary): Dictionary of currently known devices

    Returns:
        dictionary: Updated dictionary of known devices with device information
    """
    with driver(ip_address, username, password, optional_args=args) as device:
        # Get Device Information
        device_facts = device.get_facts()
        fqdn = device_facts["fqdn"]
        hostname = device_facts["hostname"]
        model = device_facts["model"]
        serial_number = device_facts["serial_number"]
        os_version = device_facts["os_version"].split(",")[1].split(" ")[2]
        vendor = device_facts["vendor"]
        # Get Management Information
        interface_ip_addresses = device.get_interfaces_ip()
        if len(interface_ip_addresses) == 1:
            management_interface = list(interface_ip_addresses.keys())[0]
        else:
            management_interface = "Loopback0"
        management_ip_address = list(
            interface_ip_addresses[management_interface]["ipv4"].keys()
        )[0]
        lldp = device.get_lldp_neighbors()
        neighbors = dict()
        for port, value in lldp.items():
            neighbors[value[0]["hostname"]] = port
        DeviceDict.update(
            {
                hostname: {
                    "fqdn": fqdn,
                    "model": model,
                    "serial": serial_number,
                    "os_version": os_version,
                    "vendor": vendor,
                    "management_interface": management_interface,
                    "management_ip": management_ip_address,
                    "neighbors": neighbors,
                }
            }
        )
    return DeviceDict


def map_the_network():
    """
    Main function
    """
    # Device Credentials - Should be usable on every device
    load_dotenv(find_dotenv())
    LAB_USER = os.getenv("LAB_USER")
    LAB_PASSWORD = os.getenv("LAB_PASSWORD")
    OUTPUT_LOCATION = os.getenv("OUTPUT_LOCATION")
    # Choose a base device to search the network from
    starting_device_ip = str(input("Enter a starting ip address: "))
    starting_device_name = str(input("Enter a starting hostname: "))
    Devices = {starting_device_name: {"ip_address": starting_device_ip}}
    unsearched_devices = [starting_device_name]
    # NAPALM Base Arguments
    driver = get_network_driver("ios")
    optional_args = {"conn_timeout": 20}
    # Get all the network devices and device info
    while len(unsearched_devices) > 0:
        for deviceName in unsearched_devices:
            device_info = {
                "device_type": "cisco_ios",
                "host": Devices[deviceName]["ip_address"],
                "username": LAB_USER,
                "password": LAB_PASSWORD,
                "conn_timeout": 15,
            }
            print(f"Getting info for {deviceName}")
            Devices = extract_cdp_info(Connect(device_info), Devices)
            Devices = get_device_info(
                driver,
                Devices[deviceName]["ip_address"],
                LAB_USER,
                LAB_PASSWORD,
                optional_args,
                Devices,
            )
            unsearched_devices.remove(deviceName)
        for device in Devices.keys():
            if ("vendor" not in Devices[device]) and (
                device not in unsearched_devices
            ):
                unsearched_devices.append(device)
    df = pd.DataFrame(Devices).transpose()
    df.index.name = "hostname"
    df = df.reindex(
        columns=[
            "fqdn",
            "vendor",
            "model",
            "serial",
            "os_version",
            "management_interface",
            "management_ip",
            "neighbors",
        ]
    )
    df.to_csv(OUTPUT_LOCATION)
    print(f"Your file is ready for viewing at {OUTPUT_LOCATION}")


if __name__ == "__main__":
    map_the_network()
