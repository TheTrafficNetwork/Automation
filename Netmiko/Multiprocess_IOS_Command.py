import os
import sys
from multiprocessing import Pool

import requests
from dotenv import find_dotenv, load_dotenv
from netmiko import ConnectHandler
from rich.progress import Progress

import get_switches
import netmiko_commands


# Load environment variables
load_dotenv(find_dotenv())


# List of commands to push to network devices
commands = netmiko_commands.test_command()


def should_i_make_changes():
    """
    Let's you know if it is a good idea to make changes today.
    """
    is_it_friday = requests.get(
        r"https://isitreadonlyfriday.com/api/isitreadonlyfriday/CDT"
    )
    if is_it_friday.json()["readonly"] is True:
        print("You really shouldn't make changes on a Friday!!!")
        sys.exit()


def ssh_config(device: dict, commands: list = commands) -> str:
    """SSH connection via Netmiko to push configuration commands to network
    devices. Saves configuration changes and logs errors in the process.

    Args:
        device (dict): Connection values needed for Netmiko
        commands (list, optional): List of switch commands to send to the
                                    network devices. Defaults to commands.

    Returns:
        str: Errors encountered from the Netmiko connection process.
    """
    try:
        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(commands)
            output += net_connect.save_config()
    except Exception as err:
        failure = f"Could not connect to {device['ip']}. Exception: {err}"
        return failure


def ssh_show(device: dict) -> str:
    """SSH connection via Netmiko to run a show command on a device.

    Args:
        device (dict): Connection values needed for Netmiko

    Returns:
        output (str): Result of the show command
        failure (str): Errors encountered from the Netmiko connection process.
    """
    try:
        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_command("show ip interface brief")
            return output
    except Exception as err:
        failure = f"Could not connect to {device['ip']}. Exception: {err}"
        return failure


if __name__ == "__main__":
    should_i_make_changes()
    NETWORK_USERNAME = os.getenv("NETWORK_USERNAME")
    NETWORK_PASSWORD = os.getenv("NETWORK_PASSWORD")
    switch_list = get_switches.get_switch_list()
    future_list = []
    for switch in switch_list:
        device = {
            "ip": str(switch.primary_ip).split("/")[0],
            "device_type": "cisco_ios",
            "username": NETWORK_USERNAME,
            "password": NETWORK_PASSWORD,
            "fast_cli": False,
            "conn_timeout": 15,
        }
        future_list.append(device)
    results = []
    max_procs = 20
    with Progress() as progress:
        task_id = progress.add_task("[cyan]Working...", total=len(future_list))
        with Pool(processes=max_procs) as pool:
            for result in pool.imap(ssh_show, future_list):
                results.append(result)
                progress.advance(task_id)

    print(*[result for result in results if result], sep="\n\n")
