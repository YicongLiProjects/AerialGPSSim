from tkinter import *

# Create window
root = Tk()

# Change title of application
root.title("Drone GPS Simulator")

# Define frame and layout
frm = Frame(root)
frm.grid()

# Define UI components below

# Define window size
root.geometry("800x600")

# Open window as long as we don't close it (main loop of the app)
root.mainloop()