from tkinter import *
from tkinter.simpledialog import askstring, askinteger

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from methods import *

# Create window
root = Tk()

# Change title of application
root.title("Drone GPS Simulator")

# Define frame and layout
frm = Frame(root)
frm.pack()

# Define window size
root.geometry("800x600")
root.resizable(width=False, height=False)

# GUI methods
m = None # MAVLink device
def connect_mavlink():
    mode = askstring("Connection mode", "What is the connection mode (TCP or UDP)?")
    ip_addr = askstring("IP address", "What is the IP address?")
    port_nbr = askinteger("Port number", "What is the port number?")
    if mode is not None and ip_addr is not None and port_nbr is not None:
        m = connect(mode, ip_addr, port_nbr)

def disconnect_mavlink():
    disconnect(m)

# Define UI components below
fig = Figure(figsize=(8, 6), dpi=100)

# Menu bar methods
menubar = Menu(root)

menubar.add_command(label="Connect", command=connect_mavlink)
menubar.add_command(label="Disconnect", command=disconnect_mavlink)
menubar.add_command(label="Start", command=start)
menubar.add_command(label="Stop", command=stop)
menubar.add_command(label="Reset", command=reset)
menubar.add_command(label="Export", command=export)

root.config(menu=menubar)

# Plot
plot_canvas = FigureCanvasTkAgg(fig, master=frm)
plot_canvas.get_tk_widget().pack()

# Open window as long as we don't close it (main loop of the app)
root.mainloop()