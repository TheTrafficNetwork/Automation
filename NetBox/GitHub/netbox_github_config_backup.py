"""
Script to backup network devices to GitHub that are tagged "Backup" in NetBox
"""

# Imports
import os
import logging

import pynetbox
import requests
from tqdm import tqdm
from dotenv import find_dotenv, load_dotenv
from github import Github
from urllib3.exceptions import InsecureRequestWarning


# Logging setup
logging.basicConfig(
    filename="Config_Backup_Logs.txt",
    level=logging.INFO,
    format="--- %(asctime)s - Line:%(lineno)d - %(levelname)s - %(message)s",
)


# Disable warnings for self signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


# Load environment variables
load_dotenv(find_dotenv())
NETBOX_API_KEY = os.getenv("NETBOX_API_KEY")
NETBOX_URL = os.getenv("NETBOX_URL")
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL")
GITHUB_DIRECTORY = os.getenv("GITHUB_DIRECTORY")


# Initialize the netbox api
nb = pynetbox.api(NETBOX_URL, token=NETBOX_API_KEY)
nb.http_session.verify = False


# Get devices slated to be backed up
backup_devices = list(nb.dcim.devices.filter(tag="backup"))


# GitHub Information
g = Github(GITHUB_ACCESS_TOKEN)
repo = g.get_repo(GITHUB_REPO_URL)
commit_msg = "Auto-Backup"


# Get list of files in GitHub folder
github_configs = []
contents = repo.get_contents(GITHUB_DIRECTORY)
while contents:
    content = contents.pop(0)
    github_configs.append(
        str(content).replace('ContentFile(path="', "").replace('")', "")
    )


# Loop through list of devices to be backed up
logging.info("****** Configuration Backup Started ******")
for device in tqdm(backup_devices, desc="Configuration Backup"):
    try:
        # Pull Running Configs via NAPALM by PyNetBox
        get_configs = nb.dcim.devices.get(name=device).napalm.list(
            method="get_config"
        )
        running_config = list(get_configs)[0]["get_config"]["running"]
        # Assignment of GitHub config path
        file_path = f"{GITHUB_DIRECTORY}/{device}.txt"
        # Write config to Github. Create file if none, else update
        if file_path not in github_configs:
            logging.info(f"Creating new file for {file_path}.")
            repo.create_file(
                file_path, commit_msg, running_config, branch="master"
            )
        else:
            old_file = repo.get_contents(file_path)
            repo.update_file(
                old_file.path,
                commit_msg,
                running_config,
                old_file.sha,
                branch="master",
            )
    except pynetbox.RequestError as e:
        logging.error(f"Failed to connect to {device}.\n{str(e)}")


logging.info("****** Configuration Backup Finsihed ******")
