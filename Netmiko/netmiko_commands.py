import os


# NTP
def ntp_update_commands():
    command_list = []
    for old_ntp in os.getenv("OLD_NTP_SERVERS").split(","):
        command_list.append(f"no ntp server {old_ntp}")
    for new_ntp in os.getenv("NEW_NTP_SERVERS").split(","):
        command_list.append(f"ntp server {new_ntp}")
    return command_list


def base_update_commands():
    command_list = [
        "udld enable",
        "lldp run",
        "service timestamps debug datetime msec",
        "service timestamps log datetime msec",
        "service password-encryption",
    ]
    return command_list


def test_command():
    command_list = ["banner exec %\nTest\nTest\nTest\n%\n", "end"]
    return command_list
