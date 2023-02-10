#!/usr/bin/env python3

# Copyright 2022 Andrew Ivanov <okolefleef@disr.it>
# All rights reserved

"""
This code imports the ctypes and Enum modules from Python 3, 
and defines three structures: CPUInfo, MemoryInfo, and DiskInfo. 
It also defines an Enum class called Commands which contains a list of commands. 
Finally, it loads three dynamic libraries: cpu_info.so, memory_info.so, 
and disk_info.so, and sets the argument types and return types for 
the get_disk_info function in disk_info.so.
"""


# import ctypes
from enum import Enum

#
# class CPUInfo(ctypes.Structure):
#     """Structure for CPU information."""
#
#     _fields_ = [
#         ("processor", ctypes.c_char * 128),
#         ("cores", ctypes.c_int),
#         ("frequency", ctypes.c_float),
#         ("total", ctypes.c_float),
#         ("per_core", ctypes.c_float * 128),
#     ]
#
#
# class MemoryInfo(ctypes.Structure):
#     _fields_ = [
#         ("total", ctypes.c_ulonglong),
#         ("available", ctypes.c_ulonglong),
#         ("used", ctypes.c_ulonglong),
#         ("percentage", ctypes.c_float)
#     ]
#
#
# class DiskInfo(ctypes.Structure):
#     _fields_ = [
#         ("mountpoint", ctypes.c_char * 1024),
#         ("type", ctypes.c_char * 1024),
#         ("total", ctypes.c_char * 1024),
#         ("used", ctypes.c_char * 1024),
#         ("free", ctypes.c_char * 1024),
#         ("percentage", ctypes.c_char * 1024)
#     ]

class Commands(str, Enum):
    test = "ping"  # Used to check if a host is reachable
    short = "shorten_url"  # Used to shorten a given URL 
    ps = "host_information"  # Used to retrieve information about the host 
    tr = "translate_text"  # Used to translate text from one language to another 
    ban = "ban_user"  # Used to ban a user from accessing certain resources 
    unban = "unban_user"  # Used to unban a user from accessing certain resources 
    sp = "text_to_speech"  # Used to convert text into speech 
    stat = "retrieve_url_statistics"  # Used to retrieve statistics about a given URL 
    dd = "delete_messages"  # Used to delete messages from a chat or forum 
    wt = "weather"  # Used to retrieve weather information for a given location
    py = "execute_python"  # Used to execute Python code
    sh = "execute_shell"  # Used to execute Shell code


    s = "searchig"  # Used for searching for specific content in databases or websites
    cs = "check_session"  # Used for checking the status of an active session
    screen = "screen"  # Used for capturing screenshots of webpages or applications
    # genc = "generate_code"
    # rec = "rewrite_code"


# cpu_info_lib = ctypes.CDLL('./lib/cpu_info.so')
#
# memory_info_lib = ctypes.CDLL('./lib/memory_info.so')
#
# disk_info_lib = ctypes.CDLL("./lib/disk_info.so")
# disk_info_lib.get_disk_info.argtypes = [ctypes.POINTER(ctypes.c_int)]
# disk_info_lib.get_disk_info.restype = ctypes.POINTER(DiskInfo)
