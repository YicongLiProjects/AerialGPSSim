from pymavlink import mavutil
from matplotlib import pyplot as plt
from ipaddress import ip_address
import time


def connect(mode: str, ip: str, port: int):
    if mode is None or ip is None or port is None:
        return None
    # Connect MAVLink
    mode = mode.lower()
    if mode != "tcp" and mode != "udp":
        mode = "udp"
    if not ip_address(ip):
        ip = "192.168.1.1"

    port = str(port)

    connection_string = f"{mode}:{ip}:{port}"
    return mavutil.mavlink_connection(connection_string, source_system=1)

def disconnect(mav):
    # mavudp or mavtcp, close connection
    if mav is None:
        return
    mav.close()

def reset():
    pass

def tick(running: bool, root_gui, con):
    pass

def send_heartbeat(con):
    con.mav.heartbeat_send(
        mavutil.mavlink.MAV_TYPE_QUADRATOR,
        mavutil.mavlink.MAV_AUTOPILOT.ARDUPILOTMEGA,
        0, 0,
        mavutil.mavlink.MAV_STATE_ACTIVE
    )

def send_global(con, lat, lon, time_0):
    con.mav.global_position_int_send(
        int(time.time() - time_0),
        int(lat * 1e7), int(lon * 1e7),
        150,
        100,
        0,0,0,
        65535
    )