from pymavlink import mavutil
from matplotlib import pyplot as plt
from ipaddress import ip_address


def connect(mode: str, ip: str, port: int):
    # Connect MAVLink
    if mode is not None:
        mode = mode.lower() + "out"
        if mode != "tcpout" and mode != "udpout":
            mode = "udpout"
    if ip is not None:
        if not ip_address(ip):
            ip = "192.168.1.1"

    if port is not None:
        port = str(port)

    connection_string = f"{mode}:{ip}:{port}"
    return mavutil.mavlink_connection(connection_string, source_system=1)

def disconnect(mav):
    # mavudp or mavtcp, close connection
    mav.close()

def start():
    pass

def stop():
    pass

def reset():
    pass

def export():
    pass