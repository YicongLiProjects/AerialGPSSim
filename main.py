import math
import queue
import threading
import time
from collections import deque
from tkinter import *
from tkinter import messagebox
from tkinter.simpledialog import askstring, askinteger

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Your helpers from methods.py (assumed signatures)
from methods import connect, disconnect, send_heartbeat

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
LAT0, LON0 = 45.5017, -73.5673      # tracker position (set to your tracker's)
ALT_AMSL = 130.0                    # constant altitude above sea level (m)
ALT_REL = 100.0                     # constant altitude above home (m)

HEARTBEAT_S = 1.0                   # heartbeat period
POSITION_S = 0.2                    # position message period (5 Hz)
REFRESH_MS = 1000                   # GUI refresh period
MAX_POINTS = 3600                   # keep the last hour of path at 1 Hz
MAX_LOG_LINES = 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def latlon_to_xy(lat, lon):
    """Lat/lon -> east/north metres relative to the tracker."""
    x = (lon - LON0) * 111_320 * math.cos(math.radians(LAT0))
    y = (lat - LAT0) * 110_540
    return x, y


def send_position(c, lat, lon, t0):
    """Send GLOBAL_POSITION_INT; unused fields get constants.
    (You could move this into methods.py next to send_heartbeat.)"""
    c.mav.global_position_int_send(
        int((time.time() - t0) * 1000) & 0xFFFFFFFF,   # time_boot_ms
        int(lat * 1e7),
        int(lon * 1e7),
        int(ALT_AMSL * 1000),
        int(ALT_REL * 1000),
        0, 0, 0,                                        # vx, vy, vz
        65535,                                          # heading unknown
    )


# ---------------------------------------------------------------------------
# Simulator: anything with get_position() -> (lat, lon) works here
# ---------------------------------------------------------------------------
class SimulatedFlight:
    """Circle of radius `radius_m` around the tracker."""

    def __init__(self, radius_m=300, period_s=120):
        self.r = radius_m
        self.period = period_s
        self.t0 = time.time()

    def get_position(self):
        a = 2 * math.pi * (time.time() - self.t0) / self.period
        east, north = self.r * math.cos(a), self.r * math.sin(a)
        lat = LAT0 + north / 110_540
        lon = LON0 + east / (111_320 * math.cos(math.radians(LAT0)))
        return lat, lon


# ---------------------------------------------------------------------------
# Sender thread: owns all writes to the MAVLink connection while running
# ---------------------------------------------------------------------------
class SenderThread(threading.Thread):
    def __init__(self, conn, sim, out_queue):
        super().__init__(daemon=True)
        self.conn = conn
        self.sim = sim
        self.out_queue = out_queue
        self.stop_event = threading.Event()

    def run(self):
        t0 = time.time()
        next_hb = next_pos = time.monotonic()
        try:
            while not self.stop_event.is_set():
                now = time.monotonic()
                if now >= next_hb:
                    send_heartbeat(self.conn)
                    next_hb += HEARTBEAT_S
                if now >= next_pos:
                    lat, lon = self.sim.get_position()
                    send_position(self.conn, lat, lon, t0)
                    self.out_queue.put(("pos", lat, lon))
                    next_pos += POSITION_S
                self.stop_event.wait(0.01)
        except Exception as e:                      # connection dropped, etc.
            self.out_queue.put(("error", str(e)))

    def stop(self):
        self.stop_event.set()
        self.join(timeout=2)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("Drone GPS Simulator")
        root.geometry("800x600")
        root.resizable(width=False, height=False)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.c = None                       # MAVLink connection
        self.sim = SimulatedFlight()
        self.sender = None
        self.queue = queue.Queue()
        self.after_id = None
        self.xs = deque(maxlen=MAX_POINTS)
        self.ys = deque(maxlen=MAX_POINTS)

        self.build_menu()
        self.build_ui()

    # ---- UI construction --------------------------------------------------
    def build_menu(self):
        menubar = Menu(self.root)
        menubar.add_command(label="Connect", command=self.connect_mavlink)
        menubar.add_command(label="Disconnect", command=self.disconnect_mavlink)
        menubar.add_command(label="Start", command=self.start_sim)
        menubar.add_command(label="Stop", command=self.stop_sim)
        menubar.add_command(label="Reset", command=self.reset_sim)
        self.root.config(menu=menubar)

    def build_ui(self):
        # Log at the bottom (packed first so it keeps its height)
        log_frame = Frame(self.root)
        log_frame.pack(side=BOTTOM, fill=X)
        self.log = Text(log_frame, height=7, state="disabled",
                        font=("Courier", 10))
        scroll = Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side=RIGHT, fill=Y)
        self.log.pack(side=LEFT, fill=X, expand=True)

        # Plot on top
        frm = Frame(self.root)
        frm.pack(side=TOP, fill=BOTH, expand=True)

        self.fig = Figure(figsize=(8, 4.6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_aspect("equal", adjustable="datalim")
        self.ax.set_xlabel("East (m)")
        self.ax.set_ylabel("North (m)")
        self.ax.grid(True)
        self.ax.plot(0, 0, "^", color="green", markersize=10, label="Tracker")
        (self.path,) = self.ax.plot([], [], "-", lw=1, label="Path")
        (self.now,) = self.ax.plot([], [], "o", color="red", label="Drone")
        self.ax.legend(loc="upper right")

        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=frm)
        self.plot_canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    # ---- Menu actions -----------------------------------------------------
    def connect_mavlink(self):
        mode = askstring("Connection mode", "What is the connection mode (TCP or UDP)?")
        ip_addr = askstring("IP address", "What is the IP address?")
        port_nbr = askinteger("Port number", "What is the port number?")
        if mode is not None and ip_addr is not None and port_nbr is not None:
            self.stop_sim()
            self.c = connect(mode, ip_addr, port_nbr)
            self.write_log("Connected")

    def disconnect_mavlink(self):
        self.stop_sim()
        if self.c is not None:
            disconnect(self.c)
            self.c = None
            self.write_log("Disconnected")

    def start_sim(self):
        if self.c is None:
            messagebox.showwarning("Not connected", "Connect to MAVLink first.")
            return
        if self.sender is not None and self.sender.is_alive():
            return                                  # already running
        self.sender = SenderThread(self.c, self.sim, self.queue)
        self.sender.start()
        self.write_log("Simulation started")
        self.refresh()

    def stop_sim(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.sender is not None:
            self.sender.stop()
            self.sender = None
            self.write_log("Simulation stopped")

    def reset_sim(self):
        self.sim = SimulatedFlight()                # restart the flight from t=0
        if self.sender is not None:
            self.sender.sim = self.sim              # keep a running sender in sync
        self.xs.clear()
        self.ys.clear()
        while not self.queue.empty():
            self.queue.get_nowait()
        self.path.set_data([], [])
        self.now.set_data([], [])
        self.plot_canvas.draw_idle()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ---- Periodic GUI update (runs on the Tk thread) ----------------------
    def refresh(self):
        latest = None
        try:
            while True:
                msg = self.queue.get_nowait()
                if msg[0] == "pos":
                    _, lat, lon = msg
                    x, y = latlon_to_xy(lat, lon)
                    self.xs.append(x)
                    self.ys.append(y)
                    latest = (lat, lon, x, y)
                elif msg[0] == "error":
                    self.write_log(f"ERROR: {msg[1]}")
        except queue.Empty:
            pass

        if latest is not None:
            lat, lon, x, y = latest
            self.write_log(f"lat {lat:.6f}  lon {lon:.6f}")   # one line per refresh
            self.path.set_data(self.xs, self.ys)
            self.now.set_data([x], [y])
            self.ax.relim()
            self.ax.autoscale_view()
            self.plot_canvas.draw_idle()

        self.after_id = self.root.after(REFRESH_MS, self.refresh)

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", f"{time.strftime('%H:%M:%S')}  {text}\n")
        self.log.see("end")                          # newest line at the bottom
        if int(self.log.index("end-1c").split(".")[0]) > MAX_LOG_LINES:
            self.log.delete("1.0", "2.0")
        self.log.configure(state="disabled")

    def on_close(self):
        self.disconnect_mavlink()
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    root = Tk()
    App(root)
    root.mainloop()