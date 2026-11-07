# AntennaTracker GPS location simulator
Made for McGill university's Aerial Design team, AerialGPSSim is a Python avionics simulator that allows the user to simulate a drone flying
and a persistent connection to ArduPilot's AntennaTracker.

The GUI is made using TkInter and the avionics software with pymavlink, a Python implementation of MAVLink. It is a lightweight messaging protocol 
used by drones to communicate with one another.

## Opening the app
Download the .zip folder from this GitHub page, and run main.py (double click or use the CLI)
### Command to run from CLI: python main.py

## How to use
1. Connect to the AntennaTracker   
  1. Press "Connect" on the menu bar
  2. Enter connection mode (TCP vs UDP)
  3. Enter IP address (use 0.0.0.0 if you are simulating without the hardware)
  4. Enter port number (14550 is the default port for MAVLink protocol)
2. Start simulation by pressing "Start" on the menu bar

- Press "Disconnect" to disconnect from AntennaTracker
- Press "Stop" to pause simulation
- Press "Reset" to reset simulation
