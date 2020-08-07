#!/bin/env dls-python

# Import the motorhome PLC generation library
from motorhome import *

# find the plc number, component name and filename
num, name, filename = parse_args()

print(name)

# ---- BL13J-MO-STEP-06 ----- 
if name == "MJ2":
	plc = PLC(num, ctype=1) # ctype=1 means GEOBRICK
	for axis in [2, 3]: # group 2 is :X1 :X2
		plc.add_motor(axis, htype=HSW, jdist=-1000, group=2)
	for axis in [4, 5, 6]: # group 3 is :Y1 :Y2 :Y3
		plc.add_motor(axis, htype=HSW, jdist=-1000, group=3)
	for axis in [7, 8]: # group 4 is :BEND1 :BEND2
		plc.add_motor(axis, htype=RLIM, jdist=0, group=4)
	plc.write(filename)
elif name == "DJ7":
	plc = PLC(num, ctype=1) # ctype=1 means GEOBRICK
	plc.add_motor(1, htype=HSW, jdist=-1000, group=2)
	plc.write(filename)

else:
	sys.stderr.write("***Error: Can't make homing PLC %d for %s\n" % (num, name))
	sys.exit(1)


####################################################################
#    dls_motorhome.motorhome.PLC#
#
#    class PLC
#     |  Create an object that can create a homing PLC for some motors.
#     |  plc = plc number (any free plc number on the PMAC)
#     |  timeout = timout for any move in ms
#     |  htype = default homing type for any motor added, see add_motor
#     |  jdist = default after trigger jog dist, see add_motor
#     |  post = default post home behaviour, see add_motor
#     |  ctype = 0=PMAC, 1=GEOBRICK
#     |
#     |  Methods defined here:
#     |
#     |  __init__(self, plc, timeout=600000, htype=0, jdist=0, post=None, ctype=0)
#     |
#     |  add_motor(self, axis, group=1, htype=None, jdist=None, post=None)
#     |        """Add a motor for the PLC to home. If htype, jdist or post are not
#     |        specified, they take the default value as specified when creating PLC().
#     |        axis = motor axis number
#     |        group = homing group. Each group will be homed sequentially, I.e all of
#     |        group 2 together, then all of group 3 together, etc. When asked to home
#     |        group 1, the PLC will home group 1 then all other defined groups 
#     |        sequentially, so you shouldn't add axes to group 1 if you are going to
#     |        use multiple groups in your homing PLC
#     |        htype = homing type enum (hdir is homing direction)
#     |        * HOME: dumb home, shouldn't be needed
#     |        * LIMIT: jog in hdir to limit, jog off it, disable limits, home. Use for
#     |        homing against limit switches
#     |        * HSW: jog in -hdir until flag, jog in hdir until flag, jog in -hdir off
#     |        it, home. Use for reference marks or home switches. If using a reference
#     |        mark be sure to set jdist.
#     |        * HSW_HLIM: jog in hdir until flag, if limit switch hit jog in -hdir
#     |        until flag, jog in -hdir off it, home. Use for reference marks or home 
#     |        switches which are generally in hdir from a normal motor position. If
#     |        using a reference mark be sure to set jdist.
#     |        * HSW_DIR: jog in -hdir until not flag, jog in hdir until flag, jog in 
#     |        -hdir until not flag, home. Use for directional (Newport style) home
#     |        switches.
#     |        * RLIM: jog in -hdir to limit, home. Use for homing on release of limit
#     |        switches
#     |        * HOMEZ: Zero move home.  The home position is where the motor currently is.
#     |        Useful for encoder only axes where the motor is driven from a different axis
#     |        and is homed first.
#     |        jdist = distance to jog by after finding the trigger. Should always be
#     |        in a -hdir. E.g if ix23 = -1, jdist should be +ve. This should only be
#     |        needed for reference marks or bouncy limit switches. A recommended 
#     |        value in these cases is about 1000 counts in -hdir.
#     |        post = where to move after the home. This can be:
#     |        * None: Stay at the home position
#     |        * an integer: move to this position in motor cts
#     |        * "i": go to the initial position (does nothing for HOME htype motors)
#     |        * "l": go to the low limit (ix13)
#     |        * "h": go to the high limit (ix14)"""
#     |        # jdist should always be opposite direction to ix23, only add it if you have a bouncy limit switch
