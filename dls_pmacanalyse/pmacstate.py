from dataclasses import dataclass
from functools import cmp_to_key
from logging import getLogger
from typing import Dict, List, Optional, Union, cast

from dls_pmaclib.dls_pmcpreprocessor import ClsPmacParser

from dls_pmacanalyse.pmacparser import PmacParser
from dls_pmacanalyse.pmacprogram import (
    PmacCsAxisDef,
    PmacForwardKinematicProgram,
    PmacInverseKinematicProgram,
    PmacMotionProgram,
    PmacPlcProgram,
)
from dls_pmacanalyse.pmacvariables import (
    PmacFeedrateOverride,
    PmacIVariable,
    PmacMsIVariable,
    PmacMVariable,
    PmacPVariable,
    PmacQVariable,
    PmacVariable,
    VariableInfo,
)

from .errors import AnalyseError, GeneralError
from .utils import numericSort

log = getLogger(__name__)

PmacVariableResult = Optional[PmacVariable]


@dataclass
class CoordinateSysInfo:
    """A basic representation of a coordinate system for representation to a user"""

    num: int
    axis_defs: str
    forward: str
    inverse: str
    feedrate: int


class PmacState(object):
    """
    Represents the internal state of a PMAC.

    Provides a function to compare two PmacState.

    Provides functions to extract views of logical groupings of
    state variables for representation to a user.
    """

    def __init__(self, descr):
        self.geobrick: Optional[bool] = None
        self.vars: Dict[
            str,
            Union[
                PmacMotionProgram,
                PmacPlcProgram,
                PmacForwardKinematicProgram,
                PmacInverseKinematicProgram,
                PmacPVariable,
                PmacIVariable,
                PmacMVariable,
                PmacQVariable,
                PmacMsIVariable,
                PmacCsAxisDef,
                PmacFeedrateOverride,
            ],
        ] = {}
        self.descr = descr
        self.inlineExpressionResolutionState = None

    def setInlineExpressionResolutionState(self, state):
        self.inlineExpressionResolutionState = state

    def getInlineExpressionIValue(self, n):
        return self.inlineExpressionResolutionState.getIVariable(n).getFloatValue()

    def getInlineExpressionPValue(self, n):
        return self.inlineExpressionResolutionState.getPVariable(n).getFloatValue()

    def getInlineExpressionQValue(self, cs, n):
        return self.inlineExpressionResolutionState.getQVariable(cs, n).getFloatValue()

    def getInlineExpressionMValue(self, n):
        return self.inlineExpressionResolutionState.getMVariable(n).getFloatValue()

    def addVar(self, var):
        self.vars[var.addr()] = var

    def removeVar(self, var):
        if var.addr() in self.vars:
            del self.vars[var.addr()]

    def copyFrom(self, other):
        for k, v in other.vars.items():
            self.vars[k] = v.copyFrom()

    def getVar(self, t: str, n: int) -> PmacVariable:
        addr = "%s%s" % (t, n)
        if addr in self.vars:
            result = self.vars[addr]
        else:
            if t == "prog":
                result = PmacMotionProgram(n)
            elif t == "plc":
                result = PmacPlcProgram(n)
            elif t == "fwd":
                result = PmacForwardKinematicProgram(n)
            elif t == "inv":
                result = PmacInverseKinematicProgram(n)
            elif t == "p":
                result = PmacPVariable(n)
            elif t == "i":
                result = PmacIVariable(n)
            elif t == "m":
                result = PmacMVariable(n)
            else:
                raise GeneralError("Illegal program type: %s" % t)
            self.vars[addr] = result
        return result

    def getVar2(self, t1: str, n1: int, t2: str, n2: int) -> PmacVariable:
        addr = "%s%s%s%s" % (t1, n1, t2, n2)
        if addr in self.vars:
            result = self.vars[addr]
        else:
            if t2 == "q":
                result = PmacQVariable(n1, n2)
            elif t2 == "i":
                result = PmacMsIVariable(n1, n2)
            elif t2 == "#":
                result = PmacCsAxisDef(n1, n2)
            elif t2 == "%":
                result = PmacFeedrateOverride(n1)
            else:
                raise GeneralError("Illegal program type: %sx%s" % (t1, t2))
            self.vars[addr] = result
        return result

    def getVarNoCreate(self, t: str, n: int) -> PmacVariableResult:
        addr = "%s%s" % (t, n)
        result = None
        if addr in self.vars:
            result = self.vars[addr]
        return result

    def getVarNoCreate2(self, t1: str, n1: int, t2: str, n2: int) -> PmacVariableResult:
        addr = "%s%s%s%s" % (t1, n1, t2, n2)
        result = None
        if addr in self.vars:
            result = self.vars[addr]
        return result

    def getMotionProgram(self, n):
        return cast(PmacMotionProgram, self.getVar("prog", n))

    def getMotionProgramNoCreate(self, n):
        return cast(PmacMotionProgram, self.getVarNoCreate("prog", n))

    def getPlcProgram(self, n):
        return cast(PmacPlcProgram, self.getVar("plc", n))

    def getPlcProgramNoCreate(self, n):
        return cast(PmacPlcProgram, self.getVarNoCreate("plc", n))

    def getForwardKinematicProgram(self, n):
        return self.getVar("fwd", n)

    def getInverseKinematicProgram(self, n):
        return self.getVar("inv", n)

    def getForwardKinematicProgramNoCreate(self, n: int):
        return cast(PmacForwardKinematicProgram, self.getVarNoCreate("fwd", n))

    # TODO these should return list of lines instead of text
    def getForwardKinematicProgramText(self, n: int):
        result = self.getForwardKinematicProgramNoCreate(n)
        if result:
            result = result.valueText()
        return result

    def getInverseKinematicProgramNoCreate(self, n: int):
        return cast(PmacInverseKinematicProgram, self.getVarNoCreate("inv", n))

    def getInverseKinematicProgramText(self, n: int):
        result = self.getInverseKinematicProgramNoCreate(n)
        if result:
            result = result.valueText()
        return result

    def getPVariable(self, n):
        return self.getVar("p", n)

    def getIVariable(self, n):
        return self.getVar("i", n)

    def getMVariable(self, n):
        return cast(PmacMVariable, self.getVar("m", n))

    def getQVariable(self, cs, n):
        return self.getVar2("&", cs, "q", n)

    def getFeedrateOverride(self, cs):
        return self.getVar2("&", cs, "%", 0)

    def getFeedrateOverrideNoCreate(self, cs):
        return self.getVarNoCreate2("&", cs, "%", 0)

    def getFeedRateOverrideValue(self, cs: int) -> int:
        rate = self.getFeedrateOverrideNoCreate(cs)
        if rate:
            result = int(rate.valStr())
        else:
            result = 100
        return result

    def getMsIVariable(self, ms, n):
        return cast(PmacMsIVariable, self.getVar2("ms", ms, "i", n))

    def getCsAxisDef(self, cs, m):
        return cast(PmacCsAxisDef, self.getVar2("&", cs, "#", m))

    def getCsAxisDefNoCreate(self, cs, m):
        return cast(PmacCsAxisDef, self.getVarNoCreate2("&", cs, "#", m))

    def dump(self):
        result = ""
        for a, v in self.vars.items():
            result += v.dump()
        return result

    #############################################################################
    # functions to extract descriptive logical groupings of brick variables
    #############################################################################
    def get_ivariables(
        self, start: int, count: int, descriptions: Dict[int, str]
    ) -> List[VariableInfo]:
        return [
            self.getIVariable(i + start).info(descriptions[i]) for i in range(count)
        ]

    def get_global_ivariables(self) -> List[VariableInfo]:
        return self.get_ivariables(0, 100, PmacState.globalIVariableDescriptions)

    def get_motor_ivariables(self, motor: int) -> List[VariableInfo]:
        vars = self.get_ivariables(
            motor * 100, 100, PmacState.motorIVariableDescriptions
        )
        if self.geobrick:
            i = 7000 + PmacState.axisToMn[motor] + motor
            vars += self.get_ivariables(i, 10, PmacState.motorIVariableDescriptions)
        return vars

    def get_pvariables(self) -> List[VariableInfo]:
        return [self.getPVariable(p).info() for p in range(8192)]

    def get_mvariables(self, content: bool = False):
        return [self.getMVariable(m).info(content=content) for m in range(8192)]

    def get_coord_systems(self):
        cs_list = []
        for cs in range(1, 17):
            # combine axis defs into a space separated list (TODO maybe rethink this)
            axis_defs = ""
            for motor in range(1, 33):
                var = self.getCsAxisDefNoCreate(cs, motor)
                if var is not None and not var.isZero():
                    axis_defs += f"{var.dump()} "

            cs_list.append(
                CoordinateSysInfo(
                    num=cs,
                    axis_defs=axis_defs,
                    forward=self.getForwardKinematicProgramText(cs),
                    inverse=self.getInverseKinematicProgramText(cs),
                    feedrate=self.getFeedRateOverrideValue(cs),
                )
            )
        return cs_list

    def htmlGlobalIVariables(self, page):
        table = page.table(page.body(), ["I-Variable", "Value", "Description"])
        for i in range(0, 100):
            page.tableRow(
                table,
                [
                    "i%s" % i,
                    "%s" % self.getIVariable(i).valStr(),
                    "%s" % PmacState.globalIVariableDescriptions[i],
                ],
            )

    def htmlMotorIVariables(self, motor, page, geobrick):
        table = page.table(page.body(), ["I-Variable", "Value", "Description"])
        for n in range(0, 100):
            i = motor * 100 + n
            page.tableRow(
                table,
                [
                    "i%s" % i,
                    "%s" % self.getIVariable(i).valStr(),
                    "%s" % PmacState.motorIVariableDescriptions[n],
                ],
            )
        if geobrick:
            for n in range(10):
                i = 7000 + PmacState.axisToMn[motor] + n
                page.tableRow(
                    table,
                    [
                        "i%s" % i,
                        "%s" % self.getIVariable(i).valStr(),
                        "%s" % PmacState.motorI7000VariableDescriptions[n],
                    ],
                )

    def htmlGlobalMsIVariables(self, page):
        table = page.table(
            page.body(), ["MS I-Variable", "Node", "Value", "Description"]
        )
        for i, description in PmacState.globalMsIVariableDescriptions.items():
            for node in [0, 16, 32, 64]:
                page.tableRow(
                    table,
                    [
                        "i%s" % i,
                        "%s" % node,
                        "%s" % self.getMsIVariable(0, i).valStr(),
                        "%s" % description,
                    ],
                )

    def htmlMotorMsIVariables(self, motor, page):
        table = page.table(page.body(), ["MS I-Variable", "Value", "Description"])
        node = PmacState.axisToNode[motor]
        for i, description in PmacState.motorMsIVariableDescriptions.items():
            page.tableRow(
                table,
                [
                    "i%s" % i,
                    "%s" % self.getMsIVariable(node, i).valStr(),
                    "%s" % description,
                ],
            )

    #############################################################################
    # end of functions to extract logical grouping of brick variables
    #############################################################################

    def compare(self, other, noCompare, pmacName, page, fixfile, unfixfile):
        """Compares the state of this PMAC with the other."""
        result = True
        table = page.table(page.body(), ["Element", "Reason", "Reference", "Hardware"])
        # Build the list of variable addresses to test
        addrs = sorted(
            (set(self.vars.keys()) | set(other.vars.keys()))
            - set(noCompare.vars.keys()),
            key=cmp_to_key(numericSort),
        )
        # For each of these addresses, compare the variable
        for a in addrs:
            texta = a
            commentargs = {}
            if texta.endswith("%0"):
                texta = texta[:-1]
            if texta.startswith("i") and not texta.startswith("inv"):
                i = int(texta[1:])
                if i in range(100):
                    desc = PmacState.globalIVariableDescriptions[i]
                    commentargs["comment"] = desc
                elif i in range(3300):
                    desc = PmacState.motorIVariableDescriptions[i % 100]
                    commentargs["comment"] = desc
                elif i in range(7000, 7350):
                    desc = PmacState.motorI7000VariableDescriptions[i % 10]
                    commentargs["comment"] = desc
                else:
                    desc = "No description available"
                texta = page.doc_node(a, desc)
            if a not in other.vars:
                if not self.vars[a].ro and not self.vars[a].isEmpty():
                    result = False
                    self.writeHtmlRow(page, table, texta, "Missing", None, self.vars[a])
                    if unfixfile is not None:
                        unfixfile.write(self.vars[a].dump(**commentargs))
            elif a not in self.vars:
                if not other.vars[a].ro and not other.vars[a].isEmpty():
                    result = False
                    self.writeHtmlRow(
                        page, table, texta, "Missing", other.vars[a], None
                    )
                    if fixfile is not None:
                        fixfile.write(other.vars[a].dump())
            elif not self.vars[a].compare(other.vars[a]):
                if not other.vars[a].ro and not self.vars[a].ro:
                    result = False
                    self.writeHtmlRow(
                        page, table, texta, "Mismatch", other.vars[a], self.vars[a]
                    )
                    if fixfile is not None:
                        fixfile.write(other.vars[a].dump())
                    if unfixfile is not None:
                        unfixfile.write(self.vars[a].dump(**commentargs))
        # Check the running PLCs
        for n in range(32):
            plc = self.getPlcProgramNoCreate(n)
            if plc is not None:
                plc.setShouldBeRunning()
                log.debug(
                    "PLC%s, isRunning=%s, shouldBeRunning=%s",
                    n,
                    plc.isRunning,
                    plc.shouldBeRunning,
                )
                if plc.shouldBeRunning and not plc.isRunning:
                    result = False
                    self.writeHtmlRow(
                        page, table, "plc%s" % n, "Not running", None, None
                    )
                    if fixfile is not None:
                        fixfile.write("enable plc %s\n" % n)
                    if unfixfile is not None:
                        unfixfile.write("disable plc %s\n" % n)
                elif not plc.shouldBeRunning and plc.isRunning:
                    result = False
                    self.writeHtmlRow(page, table, "plc%s" % n, "Running", None, None)
                    if fixfile is not None:
                        fixfile.write("disable plc %s\n" % n)
                    if unfixfile is not None:
                        unfixfile.write("enable plc %s\n" % n)
        return result

    def writeHtmlRow(self, page, parent, addr, reason, referenceVar, hardwareVar):
        row = page.tableRow(parent)
        # The address column
        col = page.tableColumn(row, addr)
        # The reason column
        col = page.tableColumn(row, reason)
        # The reference column
        col = page.tableColumn(row)
        if referenceVar is None:
            page.text(col, "-")
        else:
            referenceVar.htmlCompare(page, col, hardwareVar)
        # The hardware column
        col = page.tableColumn(row)
        if hardwareVar is None:
            page.text(col, "-")
        else:
            hardwareVar.htmlCompare(page, col, referenceVar)

    def loadPmcFile(self, fileName):
        """Loads a PMC file into this PMAC state."""
        file = open(fileName, "r")
        if file is None:
            raise AnalyseError("Could not open reference file: %s" % fileName)
        log.info("Loading PMC file %s...", fileName)
        parser = PmacParser(file, self)
        parser.onLine()

    def loadPmcFileWithPreprocess(self, fileName, includePaths):
        """
        Loads a PMC file into this PMAC state having expanded includes and defines.
        """
        if includePaths is not None:
            p = ClsPmacParser(includePaths=includePaths.split(":"))
        else:
            p = ClsPmacParser()
        log.info("Loading PMC file %s...", fileName)
        converted = p.parse(fileName, debug=True)
        if converted is None:
            raise AnalyseError("Could not open reference file: %s" % fileName)
        parser = PmacParser(p.output, self)
        parser.onLine()

    #############################################################################
    # Dictionaries that detail variable semantics
    #############################################################################
    globalIVariableDescriptions = {
        0: "Serial card number",
        1: "Serial card mode",
        2: "Control panel port activation",
        3: "I/O handshake control",
        4: "Communications integrity mode",
        5: "PLC program control",
        6: "Error reporting mode",
        7: "Phase cycle extension",
        8: "Real-time interrupt period",
        9: "Full/abbreviated listing control",
        10: "Servo interrupt time",
        11: "Programmed move calculation time",
        12: "Lookahead spline time",
        13: "Foreground in-position check enable",
        14: "Temporary buffer save enable",
        15: "Degree/radian control for user trig functions",
        16: "Rotary buffer request on point",
        17: "Rotary buffer request off point",
        18: "Fixed buffer full warning point",
        19: "Clock source I-variable number",
        20: "Macro IC 0 base address",
        21: "Macro IC 1 base address",
        22: "Macro IC 2 base address",
        23: "Macro IC 3 base address",
        24: "Main DPRAM base address",
        25: "Reserved",
        26: "Reserved",
        27: "Reserved",
        28: "Reserved",
        29: "Reserved",
        30: "Compensation table wrap enable",
        31: "Reserved",
        32: "Reserved",
        33: "Reserved",
        34: "Reserved",
        35: "Reserved",
        36: "Reserved",
        37: "Additional wait states",
        38: "Reserved",
        39: "UBUS accessory ID variable display control",
        40: "Watchdog timer reset value",
        41: "I-variable lockout control",
        42: "Spline/PVT time control mode",
        43: "Auxiliary serial port parser disable",
        44: "PMAC ladder program enable",
        45: "Foreground binary rotary buffer transfer enable",
        46: "P&Q-variable storage location",
        47: "DPRAM motor data foreground reporting period",
        48: "DPRAM motor data foreground reporting enable",
        49: "DPRAM background data reporting enable",
        50: "DPRAM background data reporting period",
        51: "Compensation table enable",
        52: "CPU frequency control",
        53: "Auxiliary serial port baud rate control",
        54: "Serial port baud rate control",
        55: "DPRAM background variable buffers enable",
        56: "DPRAM ASCII communications interrupt enable",
        57: "DPRAM motor data background reporting enable",
        58: "DPRAM ASCII communications enable",
        59: "Motor/CS group select",
        60: "Filtered velocity sample time",
        61: "Filtered velocity shift",
        62: "Internal message carriage return control",
        63: "Control-X echo enable",
        64: "Internal response tag enable",
        65: "Reserved",
        66: "Reserved",
        67: "Reserved",
        68: "Coordinate system activation control",
        69: "Reserved",
        70: "Macro IC 0 node auxiliary register enable",
        71: "Macro IC 0 node protocol type control",
        72: "Macro IC 1 node auxiliary register enable",
        73: "Macro IC 1 node protocol type control",
        74: "Macro IC 2 node auxiliary register enable",
        75: "Macro IC 2 node protocol type control",
        76: "Macro IC 3 node auxiliary register enable",
        77: "Macro IC 3 node protocol type control",
        78: "Macro type 1 master/slave communications timeout",
        79: "Macro type 1 master/master communications timeout",
        80: "Macro ring check period",
        81: "Macro maximum ring error count",
        82: "Macro minimum sync packet count",
        83: "Macro parallel ring enable mask",
        84: "Macro IC# for master communications",
        85: "Macro ring order number",
        86: "Reserved",
        87: "Reserved",
        88: "Reserved",
        89: "Reserved",
        90: "VME address modifier",
        91: "VME address modifier don't care bits",
        92: "VME base address bits A31-A24",
        93: "VME mailbox base address bits A23-A16 ISA DPRAM base address bits A23-A16",
        94: "VME mailbox base address bits A15-A08 ISA DPRAM base address bits A15-A14"
        " & control",
        95: "VME interrupt level",
        96: "VME interrupt vector",
        97: "VME DPRAM base address bits A23-A20",
        98: "VME DPRAM enable",
        99: "VME address width control",
    }
    motorIVariableDescriptions = {
        0: "Activation control",
        1: "Commutation enable",
        2: "Command output address",
        3: "Position loop feedback address",
        4: "Velocity loop feedback address",
        5: "Master position address",
        6: "Position following enable and mode",
        7: "Master (handwheel) scale factor",
        8: "Position scale factor",
        9: "Velocity-loop scale factor",
        10: "Power-on servo position address",
        11: "Fatal following error limit",
        12: "Warning following error limit",
        13: "Positive software position limit",
        14: "Negative software position limit",
        15: "Abort/limit deceleration rate",
        16: "Maximum program velocity",
        17: "Maximum program acceleration",
        18: "Reserved",
        19: "Maximum jog/home acceleration",
        20: "Jog/home acceleration time",
        21: "Jog/home S-curve time",
        22: "Jog speed",
        23: "Home speed and direction",
        24: "Flag mode control",
        25: "Flag address",
        26: "Home offset",
        27: "Position rollover range",
        28: "In-position band",
        29: "Output/first phase offset",
        30: "PID proportional gain",
        31: "PID derivative gain",
        32: "PID velocity feedforward gain",
        33: "PID integral gain",
        34: "PID integration mode",
        35: "PID acceleration feedforward gain",
        36: "PID notch filter coefficient N1",
        37: "PID notch filter coefficient N2",
        38: "PID notch filter coefficient D1",
        39: "PID notch filter coefficient D2",
        40: "Net desired position filter gain",
        41: "Desired position limit band",
        42: "Amplifier flag address",
        43: "Overtravel-limit flag address",
        44: "Reserved",
        45: "Reserved",
        46: "Reserved",
        47: "Reserved",
        48: "Reserved",
        49: "Reserved",
        50: "Reserved",
        51: "Reserved",
        52: "Reserved",
        53: "Reserved",
        54: "Reserved",
        55: "Commutation table address offset",
        56: "Commutation table delay compensation",
        57: "Continuous current limit",
        58: "Integrated current limit",
        59: "User-written servo/phase enable",
        60: "Servo cycle period extension period",
        61: "Current-loop integral gain",
        62: "Current-loop forward-path proportional gain",
        63: "Integration limit",
        64: "Deadband gain factor",
        65: "Deadband size",
        66: "PWM scale factor",
        67: "Position error limit",
        68: "Friction feedforward",
        69: "Output command limit",
        70: "Number of commutation cycles (N)",
        71: "Counts per N commutation cycles",
        72: "Commuation phase angle",
        73: "Phase finding output value",
        74: "Phase finding time",
        75: "Phase position offset",
        76: "Current-loop back-path proportional gain",
        77: "Magnetization current",
        78: "Slip gain",
        79: "Second phase offset",
        80: "Power-up mode",
        81: "Power-on phase position address",
        82: "Current-loop feedback address",
        83: "Commutation position address",
        84: "Current-loop feedback mask word",
        85: "Backlash take-up rate",
        86: "Backlash size",
        87: "Backlash hysteresis",
        88: "In-position number of scans",
        89: "Reserved",
        90: "Rapid mode speed select",
        91: "Power-on phase position format",
        92: "Jog move calculation time",
        93: "Reserved",
        94: "Reserved",
        95: "Power-on servo position format",
        96: "Command output mode control",
        97: "Position capture & trigger mode",
        98: "Third resolver gear ratio",
        99: "Second resolver gear ratio",
    }
    globalMsIVariableDescriptions = {
        0: "Software firmware version",
        2: "Station ID and user configutation word",
        3: "Station rotary switch setting",
        6: "Maximum permitted ring errors in one second",
        8: "Macro ring check period",
        9: "Macro ring error shutdown count",
        10: "Macro ring sync packet shutdown dount",
        11: "Station order number",
        14: "Macro IC source of phase clock",
        15: "Enable macro PLCC",
        16: "Encoder fault reporting control",
        17: "Amplifier fault disable control",
        18: "Amplifier fault polarity",
        19: "I/O data transfer period",
        20: "Data transfer enable mask",
        21: "Data transfer source and destination address",
        22: "Data transfer source and destination address",
        23: "Data transfer source and destination address",
        24: "Data transfer source and destination address",
        25: "Data transfer source and destination address",
        26: "Data transfer source and destination address",
        27: "Data transfer source and destination address",
        28: "Data transfer source and destination address",
        29: "Data transfer source and destination address",
        30: "Data transfer source and destination address",
        31: "Data transfer source and destination address",
        32: "Data transfer source and destination address",
        33: "Data transfer source and destination address",
        34: "Data transfer source and destination address",
        35: "Data transfer source and destination address",
        36: "Data transfer source and destination address",
        37: "Data transfer source and destination address",
        38: "Data transfer source and destination address",
        39: "Data transfer source and destination address",
        40: "Data transfer source and destination address",
        41: "Data transfer source and destination address",
        42: "Data transfer source and destination address",
        43: "Data transfer source and destination address",
        44: "Data transfer source and destination address",
        45: "Data transfer source and destination address",
        46: "Data transfer source and destination address",
        47: "Data transfer source and destination address",
        48: "Data transfer source and destination address",
        49: "Data transfer source and destination address",
        50: "Data transfer source and destination address",
        51: "Data transfer source and destination address",
        52: "Data transfer source and destination address",
        53: "Data transfer source and destination address",
        54: "Data transfer source and destination address",
        55: "Data transfer source and destination address",
        56: "Data transfer source and destination address",
        57: "Data transfer source and destination address",
        58: "Data transfer source and destination address",
        59: "Data transfer source and destination address",
        60: "Data transfer source and destination address",
        61: "Data transfer source and destination address",
        62: "Data transfer source and destination address",
        63: "Data transfer source and destination address",
        64: "Data transfer source and destination address",
        65: "Data transfer source and destination address",
        66: "Data transfer source and destination address",
        67: "Data transfer source and destination address",
        68: "Data transfer source and destination address",
        69: "I/O board 16 bit transfer control",
        70: "I/O board 16 bit transfer control",
        71: "I/O board 24 bit transfer control",
        72: "Output power-on/shutdown state",
        73: "Output power-on/shutdown state",
        74: "Output power-on/shutdown state",
        75: "Output power-on/shutdown state",
        76: "Output power-on/shutdown state",
        77: "Output power-on/shutdown state",
        78: "Output power-on/shutdown state",
        79: "Output power-on/shutdown state",
        80: "Output power-on/shutdown state",
        81: "Output power-on/shutdown state",
        82: "Output power-on/shutdown state",
        83: "Output power-on/shutdown state",
        84: "Output power-on/shutdown state",
        85: "Output power-on/shutdown state",
        86: "Output power-on/shutdown state",
        87: "Output power-on/shutdown state",
        88: "Output power-on/shutdown state",
        89: "Output power-on/shutdown state",
        90: "Y:MTR servo channel disanle and MI996 enable",
        91: "Phase interrupt 24 bit data copy",
        92: "Phase interrupt 24 bit data copy",
        93: "Phase interrupt 24 bit data copy",
        94: "Phase interrupt 24 bit data copy",
        95: "Phase interrupt 24 bit data copy",
        96: "Phase interrupt 24 bit data copy",
        97: "Phase interrupt 24 bit data copy",
        98: "Phase interrupt 24 bit data copy",
        99: "Reserved",
        101: "Ongoing position source address",
        102: "Ongoing position source address",
        103: "Ongoing position source address",
        104: "Ongoing position source address",
        105: "Ongoing position source address",
        106: "Ongoing position source address",
        107: "Ongoing position source address",
        108: "Ongoing position source address",
        111: "Power-up position source address",
        112: "Power-up position source address",
        113: "Power-up position source address",
        114: "Power-up position source address",
        115: "Power-up position source address",
        116: "Power-up position source address",
        117: "Power-up position source address",
        118: "Power-up position source address",
        120: "Encoder conversion table entries",
        121: "Encoder conversion table entries",
        122: "Encoder conversion table entries",
        123: "Encoder conversion table entries",
        124: "Encoder conversion table entries",
        125: "Encoder conversion table entries",
        126: "Encoder conversion table entries",
        127: "Encoder conversion table entries",
        128: "Encoder conversion table entries",
        129: "Encoder conversion table entries",
        130: "Encoder conversion table entries",
        131: "Encoder conversion table entries",
        132: "Encoder conversion table entries",
        133: "Encoder conversion table entries",
        134: "Encoder conversion table entries",
        135: "Encoder conversion table entries",
        136: "Encoder conversion table entries",
        137: "Encoder conversion table entries",
        138: "Encoder conversion table entries",
        139: "Encoder conversion table entries",
        140: "Encoder conversion table entries",
        141: "Encoder conversion table entries",
        142: "Encoder conversion table entries",
        143: "Encoder conversion table entries",
        144: "Encoder conversion table entries",
        145: "Encoder conversion table entries",
        146: "Encoder conversion table entries",
        147: "Encoder conversion table entries",
        148: "Encoder conversion table entries",
        149: "Encoder conversion table entries",
        150: "Encoder conversion table entries",
        151: "Encoder conversion table entries",
        152: "Phase-clock latched I/O",
        153: "Phase-clock latched I/O",
        161: "MLDT frequency control",
        162: "MLDT frequency control",
        163: "MLDT frequency control",
        164: "MLDT frequency control",
        165: "MLDT frequency control",
        166: "MLDT frequency control",
        167: "MLDT frequency control",
        168: "MLDT frequency control",
        169: "I/O board 72 bit transfer control",
        170: "I/O board 72 bit transfer control",
        171: "I/O board 144 bit transfer control",
        172: "I/O board 144 bit transfer control",
        173: "I/O board 144 bit transfer control",
        174: "12 bit A/D transfer",
        175: "12 bit A/D transfer",
        176: "Macro IC base address",
        177: "Macro IC address for node 14",
        178: "Macro IC address for node 15",
        179: "Macro/servo IC #1 base address",
        180: "Macro/servo IC #2 base address",
        181: "Macro/servo channels 1-8 address",
        182: "Macro/servo channels 1-8 address",
        183: "Macro/servo channels 1-8 address",
        184: "Macro/servo channels 1-8 address",
        185: "Macro/servo channels 1-8 address",
        186: "Macro/servo channels 1-8 address",
        187: "Macro/servo channels 1-8 address",
        188: "Macro/servo channels 1-8 address",
        189: "Macro/encoder IC #3 base address",
        190: "Macro/encoder IC #4 base address",
        191: "Encoder channels 9-14 base address",
        192: "Encoder channels 9-14 base address",
        193: "Encoder channels 9-14 base address",
        194: "Encoder channels 9-14 base address",
        195: "Encoder channels 9-14 base address",
        196: "Encoder channels 9-14 base address",
        198: "Direct read/write format and address",
        199: "Direct read/write variable",
        200: "Macro/servo ICs detected and saved",
        203: "Phase period",
        204: "Phase execution time",
        205: "Background cycle time",
        206: "Maximum background cycle time",
        207: "Identification break down",
        208: "User RAM start",
        210: "Servo IC identification variables",
        211: "Servo IC identification variables",
        212: "Servo IC identification variables",
        213: "Servo IC identification variables",
        214: "Servo IC identification variables",
        215: "Servo IC identification variables",
        216: "Servo IC identification variables",
        217: "Servo IC identification variables",
        218: "Servo IC identification variables",
        219: "Servo IC identification variables",
        220: "Servo IC identification variables",
        221: "Servo IC identification variables",
        222: "Servo IC identification variables",
        223: "Servo IC identification variables",
        224: "Servo IC identification variables",
        225: "Servo IC identification variables",
        250: "I/O card identification variables",
        251: "I/O card identification variables",
        252: "I/O card identification variables",
        253: "I/O card identification variables",
        254: "I/O card identification variables",
        255: "I/O card identification variables",
        256: "I/O card identification variables",
        257: "I/O card identification variables",
        258: "I/O card identification variables",
        259: "I/O card identification variables",
        260: "I/O card identification variables",
        261: "I/O card identification variables",
        262: "I/O card identification variables",
        263: "I/O card identification variables",
        264: "I/O card identification variables",
        265: "I/O card identification variables",
        900: "PWM 1-4 frequency control",
        903: "Hardware clock control channels 1-4",
        904: "PWM 1-4 deadtime / PFM 1-4 pluse width control",
        905: "DAC 1-4 strobe word",
        906: "PWM 5-8 frequency control",
        907: "Hardware clock control channels 5-8",
        908: "PWM 5-8 deadtime / PFM 5-8 pulse width control",
        909: "DAC 5-8 strobe word",
        940: "ADC 1-4 strobe word",
        941: "ADC 5-8 strobe word",
        942: "ADC strobe word channel 1* & 2*",
        943: "Phase and servo direction",
        975: "Macro IC 0 I/O node enable",
        976: "Macro IC 0 motor node disable",
        977: "Motor nodes reporting ring break",
        987: "A/D input enable",
        988: "A/D unipolar/bipolar control",
        989: "A/D source address",
        992: "Max phase frequence control",
        993: "Hardware clock control handwheel channels",
        994: "PWM deadtime / PFM pulse width control for handwheel",
        995: "Macro ring configuration/status",
        996: "Macro node activate control",
        997: "Phase clock frequency control",
        998: "Servo clock frequency control",
        999: "Handwheel DAC strobe word",
    }
    motorMsIVariableDescriptions = {
        910: "Encoder/timer decode control",
        911: "Position compare channel select",
        912: "Encoder capture control",
        913: "Capture flag select control",
        914: "Encoder gated index select",
        915: "Encoder index gate state",
        916: "Output mode select",
        917: "Output invert control",
        918: "Output PFM direction signal invert control",
        921: "Flag capture position",
        922: "ADC A input value",
        923: "Compare auto-increment value",
        924: "ADC B input value",
        925: "Compare A position value",
        926: "Compare B position value",
        927: "Encoder loss status bit",
        928: "Compare-state write enable",
        929: "Compare-output initial state",
        930: "Absolute power-on position",
        938: "Servo IC status word",
        939: "Servo IC control word",
    }
    motorI7000VariableDescriptions = {
        0: "Encoder/timer decode control",
        1: "Position compare channel select",
        2: "Encoder capture control",
        3: "Capture flag select control",
        4: "Encoder gated index select",
        5: "Encoder index gate state",
        6: "Output mode select",
        7: "Output invert control",
        8: "Output PFM direction signal invert control",
        9: "Hardware 1/T control",
    }
    axisToNode = {
        1: 0,
        2: 1,
        3: 4,
        4: 5,
        5: 8,
        6: 9,
        7: 12,
        8: 13,
        9: 16,
        10: 17,
        11: 20,
        12: 21,
        13: 24,
        14: 25,
        15: 28,
        16: 29,
        17: 32,
        18: 33,
        19: 36,
        20: 37,
        21: 40,
        22: 41,
        23: 44,
        24: 45,
        25: 48,
        26: 49,
        27: 52,
        28: 53,
        29: 56,
        30: 57,
        31: 60,
        32: 61,
    }
    axisToMn = {
        1: 10,
        2: 20,
        3: 30,
        4: 40,
        5: 110,
        6: 120,
        7: 130,
        8: 140,
        9: 210,
        10: 220,
        11: 230,
        12: 240,
        13: 310,
        14: 320,
        15: 330,
        16: 340,
    }
