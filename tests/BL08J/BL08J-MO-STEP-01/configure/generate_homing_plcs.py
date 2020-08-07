#!/bin/env dls-python

# Import the motorhome PLC generation library
from motorhome import *

# find the plc number, component name and filename
num, name, filename = parse_args()

# set some defaults
plc = PLC(num, post = None, ctype=BRICK)

# configure the axes according to name
if name == "T1":
    # , post="z-48000"
    plc.add_motor(4, htype=HSW, jdist=2000, group=2) # Sample X Coarse
    # , post="z57500"
    plc.add_motor(5, htype=RLIM, jdist=-2000, group=3) # Sample Y Coarse
elif name == "ZP":
    plc.add_motor(1, htype=HSW, jdist=2000, group=2) # ZPX
    plc.add_motor(2, htype=RLIM, jdist=-10000, group=3) #ZPY
    plc.add_motor(3, htype=HSW, jdist=-2000, group=4) #ZPZ
else:
    sys.stderr.write("***Error: Can't make homing PLC %d for %s\n" % (num, name))
    sys.exit(1)

# write out the plc
plc.write(filename)
