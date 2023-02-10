#!/usr/bin/env python3

# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

import ctypes

import arrow
import psutil

from modules.pretty_json import pretty_dumps

__all__ = [
    "full_info"
]


def get_size(bytes_value: int, suffix: str = "B"):
    """
    Converts bytes to kilobytes, megabytes, gigabytes, terabytes, petabytes.
    :param bytes_value: value in bytes
    :param suffix: default suffix
    :return: value in (bytes, kilobytes, megabytes, gigabytes, terabytes, petabytes)
    """

    units = ["", "K", "M", "G", "T", "P"]
    i = 0
    while bytes_value >= 1024 and i < len(units) - 1:
        bytes_value /= 1024
        i += 1

    return f"{bytes_value:.2f}{units[i]}{suffix}"


def cpu_info() -> dict:
    """
    Get information about CPU.
    :param lib: tuple
    :return: dict
    """

    load_avg = psutil.getloadavg()
    cpu_cores = psutil.cpu_count()

    load_1min = (load_avg[0] / cpu_cores) * 100
    load_5min = (load_avg[1] / cpu_cores) * 100
    load_15min = (load_avg[2] / cpu_cores) * 100

    return {
        "<strong>cpu_cores</strong>": cpu_cores,
        "<strong>cpu_frequency</strong>": f"{int(psutil.cpu_freq().current)}Mhz",
        "<strong>cpu_load_1min</strong>": f"{load_1min:.1f}%",
        "<strong>cpu_load_5min</strong>": f"{load_5min:.1f}%",
        "<strong>cpu_load_15min</strong>": f"{load_15min:.1f}%",
    }

def memory_info() -> dict:
    """
    Get information about RAM.
    :param lib: tuple
    :return: dict
    """

    proc = psutil.Process()
    memory_rss = proc.memory_info().rss / 1024 / 1024
    memory_percent = proc.memory_percent()

    most_hungry_processes = sorted(psutil.process_iter(), key=lambda p: p.memory_info().rss, reverse=True)[:3]
    most_hungry_processes_info = [f"{p.name()} (pid {p.pid}): {p.memory_info().rss / (1024 ** 2):.1f} MB"
                                  for p in most_hungry_processes]

    virtual_memory = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()

    return {
        "<strong>memory</strong>": {
            "<strong>total_memory</strong>": f"{virtual_memory.total / 1024**3:.1f} GB",
            "<strong>available_memory</strong>": f"{virtual_memory.available / 1024**3:.1f} GB",
            "<strong>used_memory</strong>": f"{virtual_memory.used / 1024**3:.1f} GB",
            "<strong>memory_percent_used</strong>": f"{virtual_memory.percent}%",
        },
        "<strong>swap</strong>": {
            "<strong>total_swap</strong>": f"{swap_memory.total / 1024**3:.1f} GB",
            "<strong>used_swap</strong>": f"{swap_memory.used / 1024**3:.1f} GB",
            "<strong>free_swap</strong>": f"{swap_memory.free / 1024**3:.1f} GB",
            "<strong>swap_percent_used</strong>": f"{swap_memory.percent}%"
        },
        "<strong>other</strong>": {
            "<strong>used_memory (bot)</strong>": f"{memory_rss:.2f} MB ({int(memory_percent)}%)",
            "<strong>most_hungry_process</strong>": most_hungry_processes_info,
        }
    }

def disk_info() -> dict:
    """
    Get information about all disk partitions.
    :param lib: ...
    :return: dict
    """

    disk_partitions = psutil.disk_partitions()
    disk_usage = {}

    for partition in disk_partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)

            disk_usage[partition.device] = {
                "<strong>mountpoint</strong>": partition.mountpoint,
                "<strong>file_system_type</strong>": partition.fstype,
                "<strong>total_space</strong>": f"{usage.total / 1024 ** 3:.1f} GB",
                "<strong>used_space</strong>": f"{usage.used / 1024 ** 3:.1f} GB",
                "<strong>free_space</strong>": f"{usage.free / 1024 ** 3:.1f} GB",
                "<strong>space_percent_used</strong>": f"{usage.percent}%"
            }
        except PermissionError as e:
            disk_usage[partition.device] = {
                "<strong>error</strong>": str(e)
            }

    return disk_usage


def sys_info() -> dict:
    """
    Get system information: uptime and available RAM.
    :return: dict
    """

    if time_zone := arrow.get(psutil.boot_time()):
        uptime = f"{time_zone.to('Asia/Krasnoyarsk').format('HH:mm DD/MM')} ~ {time_zone.humanize(locale='en')}"
    else:
        return {"error": "arrow.get is None"}

    return {
        "<strong>SystemRuntime</strong>": uptime,
        "<strong>Available RAM</strong>": f'{psutil.virtual_memory().total / (1024**3):.1f}Gb'
    }

def full_info(type_output: str = None) -> dict:
    """
    The function returns information about the system in the form of a dictionary.
    Takes as input a tuple of two elements, the first of which contains the name of the function,
    the second is the name of the module, as well as a string specifying the type of information output.
    Returns information as a dictionary.

    :param lib: tuple
    :param type_output: str
    :return: dict
    """

    handler = {"disk": disk_info, "cpu": cpu_info, "mem": memory_info}

    if type_output not in handler:
        host_info_dict = sys_info()
    else:
        host_info_dict = handler[type_output]()

    return pretty_dumps(host_info_dict)


if __name__ == "__main__":
    print(full_info(type_output="mem"))
