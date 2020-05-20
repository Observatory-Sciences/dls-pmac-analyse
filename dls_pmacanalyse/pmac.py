import logging
import re

from dls_pmaclib.dls_pmacremote import PmacEthernetInterface, PmacTelnetInterface

from dls_pmacanalyse.errors import AnalyseError, PmacReadError
from dls_pmacanalyse.pmacparser import PmacParser
from dls_pmacanalyse.pmacprogram import (
    PmacCsAxisDef,
    PmacForwardKinematicProgram,
    PmacInverseKinematicProgram,
    PmacMotionProgram,
    PmacPlcProgram,
)
from dls_pmacanalyse.pmacstate import PmacState
from dls_pmacanalyse.pmacvariables import (
    PmacFeedrateOverride,
    PmacIVariable,
    PmacMsIVariable,
    PmacMVariable,
    PmacPVariable,
    PmacQVariable,
)

log = logging.getLogger(__name__)


class Pmac(object):
    """A class that represents a single PMAC and its state."""

    def __init__(self, name):
        self.name = name
        self.noCompare = PmacState("noCompare")
        self.reference = None
        self.compareWith = None
        self.host = ""
        self.port = 1
        self.termServ = False
        self.numMacroStationIcs = None
        self.pti = None
        self.backupFile = None
        self.referenceState = PmacState("reference")
        self.hardwareState = PmacState("hardware")
        self.compareResult = True
        self.useFactoryDefs = True
        self.numAxes = 0
        self.positionsBefore = []
        self.positionsAfter = []

    # def readCurrentPositions(self):
    #     """Read the current motor positions of the PMAC."""
    #     text = ""
    #     for axis in range(self.numAxes):
    #         (returnStr, status) = self.sendCommand("#%sP" % (axis + 1))
    #         self.initialPositions[axis + 1] = returnStr
    #         text += "%s " % returnStr[:-2]
    #     log.info(text)

    def compare(self, fixfile, unfixfile):
        log.info("Comparing...")
        self.compareResult = self.hardwareState.compare(
            self.referenceState, self.noCompare, self.name, fixfile, unfixfile
        )
        if self.compareResult:
            log.warning("Hardware matches reference")
        else:
            log.warning("Hardware to reference mismatch detected")
        return self.compareResult

    def setProtocol(self, host, port, termServ):
        self.host = host
        self.port = port
        self.termServ = termServ

    def setGeobrick(self, g):
        self.hardwareState.geobrick = g

    def setNumMacroStationIcs(self, n):
        self.numMacroStationIcs = n

    def setNoFactoryDefs(self):
        self.useFactoryDefs = False

    def setReference(self, reference):
        self.reference = reference

    def setCompareWith(self, compareWith):
        self.compareWith = compareWith

    def setNoCompare(self, vars):
        for var in vars:
            self.noCompare.addVar(var)

    def clearNoCompare(self, vars):
        for var in vars:
            self.noCompare.removeVar(var)

    def copyNoComparesFrom(self, otherPmac):
        self.noCompare.copyFrom(otherPmac.noCompare)

    def readHardware(self, backupDir, checkPositions, debug, comments, verbose):
        """Loads the current state of the PMAC.  If a backupDir is provided, the
           state is written as it is read."""
        self.checkPositions = checkPositions
        self.debug = debug
        self.comments = comments
        try:
            # Open the backup file if required
            if backupDir is not None:
                fileName = "%s/%s.pmc" % (backupDir, self.name)
                log.info("Opening backup file %s" % fileName)
                self.backupFile = open(fileName, "w")
                if self.backupFile is None:
                    raise AnalyseError("Could not open backup file: %s" % fileName)
            # Open either a Telnet connection to a terminal server,
            # or a direct TCP/IP connection to a PMAC
            if self.termServ:
                self.pti = PmacTelnetInterface(verbose=verbose)
            else:
                self.pti = PmacEthernetInterface(verbose=verbose)
            self.pti.setConnectionParams(self.host, self.port)
            msg = self.pti.connect()
            if msg is not None:
                raise PmacReadError(msg)
            log.warning(
                'Connected to a PMAC via "%s" using port %s.', self.host, self.port
            )
            # Work out what kind of PMAC we have, if necessary
            self.determinePmacType()
            self.determineNumAxes()
            self.determineNumCoordSystems()
            # Read the axis current positions
            self.positionsBefore = self.readCurrentPositions()
            log.debug("Current positions: %s", self.positionsBefore)
            # Read the data
            self.readCoordinateSystemDefinitions()
            self.readMotionPrograms()
            self.readKinematicPrograms()
            self.readPlcPrograms()
            self.readPvars()
            self.readQvars()
            self.readFeedrateOverrides()
            self.readIvars()
            self.readMvarDefinitions()
            self.readMvarValues()
            self.readMsIvars()
            self.readGlobalMsIvars()
            self.readPlcDisableState()
            self.verifyCurrentPositions(self.positionsBefore)
            # Read the current axis positions again
        finally:
            # Disconnect from the PMAC
            if self.pti is not None:
                log.info("Disconnecting from PMAC...")
                msg = self.pti.disconnect()
                self.pti = None
                log.info("Connection to the PMAC closed.")
            # Close the backup file
            if self.backupFile is not None:
                self.backupFile.close()
                self.backupFile = None

    def verifyCurrentPositions(self, positions):
        """ Checks the axis current positions to see if any have moved."""
        if self.checkPositions:
            now = self.readCurrentPositions()
            match = True
            for i in range(len(now)):
                if (
                    match
                    and now[i] < positions[i] + 10.0
                    and now[i] > positions[i] - 10.0
                ):
                    pass
                else:
                    match = False
            if match:
                log.warning("No axes moved during hardware readout")
            else:
                log.warning("One or more axes have moved:")
                log.warning("  Before: %s" % positions)
                log.warning("  Now:    %s" % now)

    def sendCommand(self, text):
        (returnStr, status) = self.pti.sendCommand(text)
        # log.debug('%s --> %s', repr(text), repr(returnStr))
        return (returnStr, status)

    def readCurrentPositions(self):
        """ Returns the current position as a list."""
        positions = []
        for axis in range(self.numAxes):
            (returnStr, status) = self.sendCommand("#%sP" % (axis + 1))
            positions.append(float(returnStr[:-2]))
        return positions

    def determinePmacType(self):
        """Discovers whether the PMAC is a Geobrick or a VME style PMAC"""
        if self.hardwareState.geobrick is None:
            (returnStr, status) = self.sendCommand("cid")
            if not status:
                raise PmacReadError(returnStr)
            id = returnStr[:-2]
            if id == "602413":
                self.hardwareState.geobrick = False
            elif id == "603382":
                self.hardwareState.geobrick = True
            else:
                self.hardwareState.geobrick = False
            log.warning("Geobrick= %s" % self.hardwareState.geobrick)

    def determineNumAxes(self):
        """Determines the number of axes the PMAC has by determining the
           number of macro station ICs."""
        if self.numMacroStationIcs is None:
            (returnStr, status) = self.sendCommand("i20 i21 i22 i23")
            if not status:
                raise PmacReadError(returnStr)
            macroIcAddresses = returnStr[:-2].split("\r")
            self.numMacroStationIcs = 0
            for i in range(4):
                if macroIcAddresses[i] != "$0":
                    self.numMacroStationIcs += 1
        self.numAxes = self.numMacroStationIcs * 8
        if self.hardwareState.geobrick:
            self.numAxes += 8
        log.info("Num axes= %s" % self.numAxes)

    def determineNumCoordSystems(self):
        """Determines the number of coordinate systems that are active by
           reading i68."""
        (returnStr, status) = self.sendCommand("i68")
        if not status:
            raise PmacReadError(returnStr)
        self.numCoordSystems = int(returnStr[:-2]) + 1

    def writeBackup(self, text):
        """If a backup file is open, write the text."""
        if self.backupFile is not None:
            self.backupFile.write(text)

    def readIvars(self):
        """Reads the I variables."""
        log.info("Reading I-variables...")
        self.writeBackup("\n; I-variables\n")
        roVars = set(
            [3, 4, 6, 9, 20, 21, 22, 23, 24, 41, 58]
            + list(range(4900, 5000))
            + [
                5111,
                5112,
                5211,
                5212,
                5311,
                5312,
                5411,
                5412,
                5511,
                5512,
                5611,
                5612,
                5711,
                5712,
                5811,
                5812,
                5911,
                5912,
                6011,
                6012,
                6111,
                6112,
                6211,
                6212,
                6311,
                6312,
                6411,
                6412,
                6511,
                6512,
                6611,
                6612,
            ]
        )
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand("i%s..%s" % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            ivars = enumerate(returnStr.split("\r")[:-1])
            for o, x in ivars:
                ro = i + o in roVars
                var = PmacIVariable(i + o, self.toNumber(x), read_only=ro)
                self.hardwareState.addVar(var)
                motor = (i + o) / 100
                index = (i + o) % 100
                text = ""
                if self.comments:
                    if motor == 0 and index in PmacState.globalIVariableDescriptions:
                        text = PmacState.globalIVariableDescriptions[index]
                    if (
                        motor >= 1
                        and motor <= 32
                        and index in PmacState.motorIVariableDescriptions
                    ):
                        text = PmacState.motorIVariableDescriptions[index]
                self.writeBackup(var.dump(comment=text))
            i += varsPerBlock

    def readPlcDisableState(self):
        """Reads the PLC disable state from the M variables 5000..5031."""
        (returnStr, status) = self.sendCommand("m5000..5031")
        if not status:
            raise PmacReadError(returnStr)
        mvars = enumerate(returnStr.split("\r")[:-1])
        for o, x in mvars:
            plc = self.hardwareState.getPlcProgramNoCreate(o)
            if plc is not None:
                runningState = False
                if x == "0":
                    runningState = True
                plc.setIsRunning(runningState)

    def readPvars(self):
        """Reads the P variables."""
        log.info("Reading P-variables...")
        self.writeBackup("\n; P-variables\n")
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand("p%s..%s" % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            pvars = enumerate(returnStr.split("\r")[:-1])
            for o, x in pvars:
                var = PmacPVariable(i + o, self.toNumber(x))
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
            i += varsPerBlock

    def readQvars(self):
        """Reads the Q variables of a coordinate system."""
        log.info("Reading Q-variables...")
        for cs in range(1, self.numCoordSystems + 1):
            self.writeBackup("\n; &%s Q-variables\n" % cs)
            (returnStr, status) = self.sendCommand("&%sq1..199" % cs)
            if not status:
                raise PmacReadError(returnStr)
            qvars = enumerate(returnStr.split("\r")[:-1])
            for o, x in qvars:
                var = PmacQVariable(cs, o + 1, self.toNumber(x))
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())

    def readFeedrateOverrides(self):
        """Reads the feedrate overrides of the coordinate systems."""
        log.info("Reading feedrate overrides...")
        self.writeBackup("\n; Feedrate overrides\n")
        for cs in range(1, self.numCoordSystems + 1):
            (returnStr, status) = self.sendCommand("&%s%%" % cs)
            if not status:
                raise PmacReadError(returnStr)
            val = returnStr.split("\r")[0]
            var = PmacFeedrateOverride(cs, self.toNumber(val))
            self.hardwareState.addVar(var)
            self.writeBackup(var.dump())

    def readMvarDefinitions(self):
        """Reads the M variable definitions."""
        log.info("Reading M-variable definitions...")
        self.writeBackup("\n; M-variables\n")
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand("m%s..%s->" % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            mvars = enumerate(returnStr.split("\r")[:-1])
            for o, x in mvars:
                var = PmacMVariable(i + o)
                parser = PmacParser([x], self)
                parser.parseMVariableAddress(variable=var)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
            i += varsPerBlock

    def readMvarValues(self):
        """Reads the M variable values."""
        log.info("Reading M-variable values...")
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand("m%s..%s" % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            mvars = enumerate(returnStr.split("\r")[:-1])
            for o, x in mvars:
                var = self.hardwareState.getMVariable(i + o)
                var.setValue(self.toNumber(x))
                # if (i+o) == 99:
                #    print("m99 ->%s, =%s, x=%s" % (var.valStr(), var.contentsStr(), x)
            i += varsPerBlock

    def readCoordinateSystemDefinitions(self):
        """Reads the coordinate system definitions."""
        log.info("Reading coordinate system definitions...")
        self.writeBackup("\n; Coordinate system definitions\n")
        self.writeBackup("undefine all\n")
        for cs in range(1, self.numCoordSystems + 1):
            for axis in range(1, 32 + 1):  # Note range is always 32 NOT self.numAxes
                # Ask for the motor status in the coordinate system
                cmd = "&%s#%s->" % (cs, axis)
                (returnStr, status) = self.sendCommand(cmd)
                if not status or len(returnStr) <= 2:
                    raise PmacReadError(returnStr)
                # Note the dropping of the last two characters, ^m^f
                parser = PmacParser([returnStr[:-2]], self)
                var = PmacCsAxisDef(cs, axis, parser.tokens())
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())

    def readKinematicPrograms(self):
        """Reads the kinematic programs.  Note that this
           function will fail if a program exceeds 1350 characters and small buffers
           are required."""
        log.info("Reading kinematic programs...")
        self.writeBackup("\n; Kinematic programs\n")
        for cs in range(1, self.numCoordSystems + 1):
            lines, _ = self.getListingLines("forward", f"&{cs}")
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacForwardKinematicProgram(cs, parser.tokens())
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())

            lines, _ = self.getListingLines("inverse", f"&{cs}")
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacInverseKinematicProgram(cs, parser.tokens())
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())

    def getListingLines(self, thing, pre_thing=""):
        """Returns the listing of a motion program or PLC using
           small blocks.  It uses the start and length parameters
           of the list command to slowly build up the listing.  Note
           that the function fails if any chuck exceeds 1350 characters.
           For use in small buffer mode."""
        lines = []
        offsets = []
        startPos = 0
        increment = 80
        going = True
        while going:
            (returnStr, status) = self.sendCommand(
                f"{pre_thing}list {thing},{startPos},{increment}"
            )
            startPos += increment
            if not status:
                if returnStr.endswith("PMAC communication error"):
                    # Can get this instead of ERR for a missing program
                    going = False
                else:
                    raise PmacReadError(returnStr)
            if len(returnStr) > 1350:
                raise PmacReadError("String too long for small buffer mode")
            if returnStr.find("ERR") >= 0:
                going = False
            else:
                if not re.match(r"\d+:", returnStr):
                    log.error(
                        "Warning: first line not starting with offset for %s",
                        repr(returnStr),
                    )
                    return (lines, offsets)
                # Separate into offset and line
                more = re.split(r"\r(\d+):", f"\r{returnStr}")[1:]
                if not more or len(more) % 2 == 1:
                    log.error(
                        "Warning: could not split lines into offset and text for %s",
                        repr(returnStr),
                    )
                    return (lines, offsets)
                for index in range(0, len(more), 2):
                    offsets.append(more[index])
                    lines.append(more[index + 1])
                # get rid of ending \r\x06
                lines[-1] = lines[-1][:-2]
        return (lines, offsets)

    def readPlcPrograms(self):
        """Reads the PLC programs"""
        log.info("Reading PLC programs...")
        self.writeBackup("\n; PLC programs\n")
        for plc in range(32):
            (lines, offsets) = self.getListingLines("plc %s" % plc)
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacPlcProgram(plc, parser.tokens(), lines, offsets)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())

    def readMotionPrograms(self):
        """Reads the motion programs. Note
           that only the first 256 programs are read, there are actually 32768."""
        log.info("Reading motion programs...")
        self.writeBackup("\n; Motion programs\n")
        for prog in range(1, 256):
            (lines, offsets) = self.getListingLines("program %s" % prog)
            if len(lines) == 1 and lines[0].find("ERR003") >= 0:
                lines = []
                offsets = []
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacMotionProgram(prog, parser.tokens(), lines, offsets)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())

    def readMsIvars(self):
        """Reads the macrostation I variables."""
        if self.numMacroStationIcs > 0:
            log.info("Reading macro station I-variables")
            self.writeBackup("\n; Macro station I-variables\n")
            reqMacroStations = []
            if self.numMacroStationIcs >= 1:
                (bits, status) = self.sendCommand("i6841")
                if status and bits[0] != "\x07":
                    bits = self.toNumber(bits[:-2])
                    for i in range(0, 14):
                        if bits & 1 == 1:
                            reqMacroStations += [i]
                        bits = bits >> 1
            if self.numMacroStationIcs >= 2:
                (bits, status) = self.sendCommand("i6891")
                if status and bits[0] != "\x07":
                    bits = self.toNumber(bits[:-2])
                    for i in range(0, 14):
                        if bits & 1 == 1:
                            reqMacroStations += [i + 16]
                        bits = bits >> 1
            if self.numMacroStationIcs >= 3:
                (bits, status) = self.sendCommand("i6941")
                if status and bits[0] != "\x07":
                    bits = self.toNumber(bits[:-2])
                    for i in range(0, 14):
                        if bits & 1 == 1:
                            reqMacroStations += [i + 32]
                        bits = bits >> 1
            if self.numMacroStationIcs >= 4:
                (bits, status) = self.sendCommand("i6991")
                if status and bits[0] != "\x07":
                    bits = self.toNumber(bits[:-2])
                    for i in range(0, 14):
                        if bits & 1 == 1:
                            reqMacroStations += [i + 48]
                        bits = bits >> 1
            reqVars = [
                910,
                911,
                912,
                913,
                914,
                915,
                916,
                917,
                918,
                923,
                925,
                926,
                927,
                928,
                929,
            ]
            roVars = [921, 922, 924, 930, 938, 939]
            for ms in reqMacroStations:
                self.doMsIvars(ms, reqVars, roVars)

    def readGlobalMsIvars(self):
        """Reads the global macrostation I variables."""
        if self.numMacroStationIcs > 0:
            log.info("Reading global macrostation I-variables")
            self.writeBackup("\n; Macro station global I-variables\n")
            if self.numMacroStationIcs in [1, 2]:
                reqMacroStations = [0]
            elif self.numMacroStationIcs in [3, 4]:
                reqMacroStations = [0, 32]
            else:
                reqMacroStations = []
            reqVars = [0, 2, 3, 6, 8, 9, 10, 11, 14]
            reqVars += range(14, 100)
            reqVars += range(101, 109)
            reqVars += range(111, 119)
            reqVars += range(120, 154)
            reqVars += range(161, 197)
            reqVars += [198, 199, 200, 203, 204, 205, 206, 207, 208]
            reqVars += range(210, 226)
            reqVars += range(250, 266)
            reqVars += [
                900,
                903,
                904,
                905,
                906,
                907,
                908,
                909,
                940,
                941,
                942,
                943,
                975,
                976,
                977,
            ]
            reqVars += [987, 988, 989, 992, 993, 994, 995, 996, 996, 998, 999]
            roVars = [4, 5, 12, 13, 209, 974]
            for ms in reqMacroStations:
                self.doMsIvars(ms, reqVars, roVars)
            reqVars = list(range(16, 100))
            reqVars += range(101, 109)
            reqVars += range(111, 119)
            reqVars += range(120, 154)
            reqVars += range(161, 197)
            reqVars += [198, 199]
            reqVars += [
                900,
                903,
                904,
                905,
                906,
                907,
                908,
                909,
                940,
                941,
                942,
                943,
                975,
                976,
                977,
            ]
            reqVars += [987, 988, 989, 992, 993, 994, 995, 996, 996, 998, 999]
            roVars = [4, 5, 12, 13, 209, 974]
            reqMacroStations = [16, 48]
            for ms in reqMacroStations:
                self.doMsIvars(ms, reqVars, roVars)

    def doMsIvars(self, ms, reqVars, roVars):
        """Reads the specified set of global macrostation I variables."""
        for v in reqVars:
            (returnStr, status) = self.sendCommand("ms%s,i%s" % (ms, v))
            if status and returnStr[0] != "\x07":
                var = PmacMsIVariable(ms, v, self.toNumber(returnStr[:-2]))
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
        for v in roVars:
            (returnStr, status) = self.sendCommand("ms%s,i%s" % (ms, v))
            if status and returnStr[0] != "\x07":
                var = PmacMsIVariable(ms, v, self.toNumber(returnStr[:-2]), read_only=True)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())

    def loadReference(self, factorySettings, includePaths=None):
        """Loads the reference PMC file after first initialising the state."""
        # Feedrate overrides default to 100
        for cs in range(1, self.numCoordSystems + 1):
            var = PmacFeedrateOverride(cs, 100.0)
            self.referenceState.addVar(var)
        if factorySettings is not None:
            self.referenceState.copyFrom(factorySettings)
        if self.reference is not None:
            # when interpreting inline expressions, the actual current value of
            # variables in the hardware is used. Otherwise we would always only
            # be comparing against the initial state immediately after reference
            # had been uploaded.
            self.referenceState.setInlineExpressionResolutionState(self.hardwareState)
            self.referenceState.loadPmcFileWithPreprocess(self.reference, includePaths)

    def loadCompareWith(self):
        """Loads the compare with file."""
        self.hardwareState.loadPmcFile(self.compareWith)

    def toNumber(self, text):
        if text[0] == "$":
            result = int(text[1:], 16)
        elif text.find(".") >= 0:
            result = float(text)
        else:
            result = int(text)
        return result
