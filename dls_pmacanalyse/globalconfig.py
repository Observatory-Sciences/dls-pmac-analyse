import getopt
import logging
import os
import sys
import xml.dom.minidom as minidom
from datetime import datetime

from dls_pmacanalyse.errors import ArgumentError, ConfigError, PmacReadError
from dls_pmacanalyse.pmac import Pmac
from dls_pmacanalyse.pmacparser import PmacParser
from dls_pmacanalyse.pmacstate import PmacState
from dls_pmacanalyse.pmacvariables import (
    PmacIVariable,
    PmacMsIVariable,
    PmacMVariable,
    PmacPVariable,
    PmacQVariable,
)
from dls_pmacanalyse.webpage import WebPage

log = logging.getLogger(__name__)


class GlobalConfig(object):
    """A single instance of this class contains the global configuration."""

    def __init__(self):
        """Constructor."""
        self.verbose = False
        self.backupDir = None
        self.writeAnalysis = True
        self.comments = False
        self.configFile = None
        self.pmacs = {}
        self.pmacFactorySettings = PmacState("pmacFactorySettings")
        self.geobrickFactorySettings = PmacState("geobrickFactorySettings")
        self.resultsDir = "pmacAnalysis"
        self.onlyPmacs = None
        self.includePaths = None
        self.checkPositions = False
        self.debug = False
        self.fixfile = None
        self.unfixfile = None

    def createOrGetPmac(self, name):
        if name not in self.pmacs:
            self.pmacs[name] = Pmac(name)
        return self.pmacs[name]

    def processArguments(self):
        """Process the command line arguments.  Returns False
           if the program is to print(the help and exit."""
        try:
            opts, args = getopt.gnu_getopt(
                sys.argv[1:],
                "vh",
                [
                    "help",
                    "verbose",
                    "backup=",
                    "pmac=",
                    "ts=",
                    "tcpip=",
                    "geobrick",
                    "vmepmac",
                    "reference=",
                    "comparewith=",
                    "resultsdir=",
                    "nocompare=",
                    "only=",
                    "include=",
                    "nofactorydefs",
                    "macroics=",
                    "checkpositions",
                    "debug",
                    "comments",
                    "fixfile=",
                    "unfixfile=",
                    "loglevel=",
                ],
            )
        except getopt.GetoptError as err:
            raise ArgumentError(str(err))
        globalPmac = Pmac("global")
        curPmac = None
        for o, a in opts:
            if o in ("-h", "--help"):
                return False
            elif o in ("-v", "--verbose"):
                self.verbose = True
            elif o == "--backup":
                self.backupDir = a
            elif o == "--comments":
                self.comments = True
            elif o == "--pmac":
                curPmac = self.createOrGetPmac(a)
                curPmac.copyNoComparesFrom(globalPmac)
            elif o == "--ts":
                parts = a.split(":")
                if len(parts) != 2:
                    raise ArgumentError("Bad terminal server argument")
                elif curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setProtocol(parts[0], parts[1], True)
            elif o == "--tcpip":
                parts = a.split(":")
                if len(parts) != 2:
                    raise ArgumentError("Bad TCP/IP argument")
                elif curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setProtocol(parts[0], parts[1], False)
            elif o == "--geobrick":
                if curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setGeobrick(True)
            elif o == "--debug":
                self.debug = True
            elif o == "--vmepmac":
                if curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setGeobrick(False)
            elif o == "--nofactorydefs":
                if curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setNoFactoryDefs()
            elif o == "--reference":
                if curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setReference(a)
            elif o == "--fixfile":
                self.fixfile = a
            elif o == "--unfixfile":
                self.unfixfile = a
            elif o == "--comparewith":
                if curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setCompareWith(a)
            elif o == "--resultsdir":
                self.resultsDir = a
            elif o == "--nocompare":
                parser = PmacParser(a, None)
                (type, nodeList, start, count, increment) = parser.parseVarSpec()
                while count > 0:
                    var = self.makeVars(type, nodeList, start)
                    if curPmac is None:
                        globalPmac.setNoCompare(var)
                    else:
                        curPmac.setNoCompare(var)
                    start += increment
                    count -= 1
            elif o == "--compare":
                if curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    parser = PmacParser(a, None)
                    (type, nodeList, start, count, increment) = parser.parseVarSpec()
                    while count > 0:
                        var = self.makeVars(type, nodeList, start)
                        curPmac.clearNoCompare(var)
                        start += increment
                        count -= 1
            elif o == "--only":
                if self.onlyPmacs is None:
                    self.onlyPmacs = []
                self.onlyPmacs.append(a)
            elif o == "--include":
                self.includePaths = a
            elif o == "--macroics":
                if curPmac is None:
                    raise ArgumentError("No PMAC yet defined")
                else:
                    curPmac.setNumMacroStationIcs(int(a))
            elif o == "--checkpositions":
                self.checkPositions = True
            elif o == "--loglevel":
                numeric_level = getattr(logging, str(a).upper(), None)
                log.setLevel(numeric_level)
        if len(args) > 1:
            raise ArgumentError("Too many arguments.")
        if len(args) == 1:
            self.configFile = args[0]
        return True

    def processConfigFile(self):
        """Process the configuration file."""
        if self.configFile is None:
            return
        file = open(self.configFile, "r")
        if file is None:
            raise ConfigError("Could not open config file: %s" % self.configFile)
        globalPmac = Pmac("global")
        curPmac = None
        for line in file:
            words = line.split(";", 1)[0].strip().split()
            if len(words) >= 1:
                if words[0].lower() == "pmac" and len(words) == 2:
                    curPmac = self.createOrGetPmac(words[1])
                    curPmac.copyNoComparesFrom(globalPmac)
                elif (
                    words[0].lower() == "ts" and len(words) == 3 and curPmac is not None
                ):
                    curPmac.setProtocol(words[1], int(words[2]), True)
                elif (
                    words[0].lower() == "tcpip"
                    and len(words) == 3
                    and curPmac is not None
                ):
                    curPmac.setProtocol(words[1], int(words[2]), False)
                elif (
                    words[0].lower() == "geobrick"
                    and len(words) == 1
                    and curPmac is not None
                ):
                    curPmac.setGeobrick()
                elif (
                    words[0].lower() == "nofactorydefs"
                    and len(words) == 1
                    and curPmac is not None
                ):
                    curPmac.setNoFactoryDefs()
                elif (
                    words[0].lower() == "reference"
                    and len(words) == 2
                    and curPmac is not None
                ):
                    curPmac.setReference(words[1])
                elif (
                    words[0].lower() == "comparewith"
                    and len(words) == 2
                    and curPmac is not None
                ):
                    curPmac.setCompareWith(words[1])
                elif words[0].lower() == "resultsdir" and len(words) == 2:
                    self.resultsDir = words[1]
                elif words[0].lower() == "include" and len(words) == 2:
                    self.includePaths = words[1]
                elif words[0].lower() == "backup" and len(words) == 2:
                    self.backupDir = words[1]
                elif words[0].lower() == "comments" and len(words) == 1:
                    self.comments = True
                elif words[0].lower() == "nocompare" and len(words) == 2:
                    parser = PmacParser([words[1]], None)
                    (type, nodeList, start, count, increment) = parser.parseVarSpec()
                    while count > 0:
                        var = self.makeVars(type, nodeList, start)
                        if curPmac is None:
                            globalPmac.setNoCompare(var)
                        else:
                            curPmac.setNoCompare(var)
                        start += increment
                        count -= 1
                elif (
                    words[0].lower() == "compare"
                    and len(words) == 2
                    and curPmac is not None
                ):
                    parser = PmacParser([words[1]], None)
                    (type, nodeList, start, count, increment) = parser.parseVarSpec()
                    while count > 0:
                        var = self.makeVars(type, nodeList, start)
                        curPmac.clearNoCompare(var)
                        start += increment
                        count -= 1
                elif (
                    words[0].lower() == "macroics"
                    and len(words) == 2
                    and curPmac is not None
                ):
                    curPmac.setNumMacroStationIcs(int(words[1]))
                else:
                    raise ConfigError("Unknown configuration: %s" % repr(line))

    def makeVars(self, varType, nodeList, n):
        """Makes a variable of the correct type."""
        result = []
        if varType == "i":
            result.append(PmacIVariable(n))
        elif varType == "p":
            result.append(PmacPVariable(n))
        elif varType == "m":
            result.append(PmacMVariable(n))
        elif varType == "ms":
            for ms in nodeList:
                result.append(PmacMsIVariable(ms, n))
        elif varType == "&":
            for cs in nodeList:
                result.append(PmacQVariable(cs, n))
        else:
            raise ConfigError("Cannot decode variable type %s" % repr(varType))
        return result

    def analyse(self):
        """Performs the analysis of the PMACs."""
        # Load the factory settings
        factorySettingsFilename = os.path.join(
            os.path.dirname(__file__), "factorySettings_pmac.pmc"
        )
        self.loadFactorySettings(
            self.pmacFactorySettings, factorySettingsFilename, self.includePaths
        )
        factorySettingsFilename = os.path.join(
            os.path.dirname(__file__), "factorySettings_geobrick.pmc"
        )
        self.loadFactorySettings(
            self.geobrickFactorySettings, factorySettingsFilename, self.includePaths
        )
        # Make sure the results directory exists
        if self.writeAnalysis:
            if not os.path.exists(self.resultsDir):
                os.makedirs(self.resultsDir)
            elif not os.path.isdir(self.resultsDir):
                raise ConfigError(
                    "Results path exists but is not a directory: %s" % self.resultsDir
                )
        # Make sure the backup directory exists if it is required
        if self.backupDir is not None:
            if not os.path.exists(self.backupDir):
                os.makedirs(self.backupDir)
            elif not os.path.isdir(self.backupDir):
                raise ConfigError(
                    "Backup path exists but is not a directory: %s" % self.backupDir
                )
        if self.writeAnalysis is True:
            # Drop a style sheet
            wFile = open("%s/analysis.css" % self.resultsDir, "w+")
            wFile.write(
                """
                p{text-align:left; color:black; font-family:arial}
                h1{text-align:center; color:green}
                table{border-collapse:collapse}
                table, th, td{border:1px solid black}
                th, td{padding:5px; vertical-align:top}
                th{background-color:#EAf2D3; color:black}
                em{color:red; font-style:normal; font-weight:bold}
                #code{white-space:pre}
                #code{font-family:courier}
                """
            )
        # Analyse each pmac
        for name, pmac in self.pmacs.items():
            if self.onlyPmacs is None or name in self.onlyPmacs:
                # Create the comparison web page
                page = WebPage(
                    "Comparison results for %s (%s)"
                    % (pmac.name, datetime.today().strftime("%x %X")),
                    "%s/%s_compare.htm" % (self.resultsDir, pmac.name),
                    styleSheet="analysis.css",
                )
                # Read the hardware (or compare with file)
                if pmac.compareWith is None:
                    try:
                        pmac.readHardware(
                            self.backupDir,
                            self.checkPositions,
                            self.debug,
                            self.comments,
                            self.verbose,
                        )
                    except PmacReadError:
                        msg = "FAILED TO CONNECT TO " + pmac.name
                        log.debug(msg, exc_info=True)
                        log.error(msg)
                else:
                    pmac.loadCompareWith()
                # Load the reference
                factoryDefs = None
                if pmac.useFactoryDefs:
                    if pmac.geobrick:
                        factoryDefs = self.geobrickFactorySettings
                    else:
                        factoryDefs = self.pmacFactorySettings
                pmac.loadReference(factoryDefs, self.includePaths)
                # Make the comparison
                theFixFile = None
                if self.fixfile is not None:
                    theFixFile = open(self.fixfile, "w")
                theUnfixFile = None
                if self.unfixfile is not None:
                    theUnfixFile = open(self.unfixfile, "w")
                matches = pmac.compare(page, theFixFile, theUnfixFile)
                if theFixFile is not None:
                    theFixFile.close()
                if theUnfixFile is not None:
                    theUnfixFile.close()
                # Write out the HTML
                if matches:
                    # delete any existing comparison file
                    if os.path.exists(
                        "%s/%s_compare.htm" % (self.resultsDir, pmac.name)
                    ):
                        os.remove("%s/%s_compare.htm" % (self.resultsDir, pmac.name))
                else:
                    if self.writeAnalysis is True:
                        page.write()
        if self.writeAnalysis is True:
            # Create the top level page
            indexPage = WebPage(
                "PMAC analysis (%s)" % datetime.today().strftime("%x %X"),
                "%s/index.htm" % self.resultsDir,
                styleSheet="analysis.css",
            )
            table = indexPage.table(indexPage.body())
            for name, pmac in self.pmacs.items():
                row = indexPage.tableRow(table)
                indexPage.tableColumn(row, "%s" % pmac.name)
                if os.path.exists("%s/%s_compare.htm" % (self.resultsDir, pmac.name)):
                    indexPage.href(
                        indexPage.tableColumn(row),
                        "%s_compare.htm" % pmac.name,
                        "Comparison results",
                    )
                elif os.path.exists("%s/%s_plcs.htm" % (self.resultsDir, pmac.name)):
                    indexPage.tableColumn(row, "Matches")
                else:
                    indexPage.tableColumn(row, "No results")
                indexPage.href(
                    indexPage.tableColumn(row),
                    "%s_ivariables.htm" % pmac.name,
                    "I variables",
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    "%s_pvariables.htm" % pmac.name,
                    "P variables",
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    "%s_mvariables.htm" % pmac.name,
                    "M variables",
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    "%s_mvariablevalues.htm" % pmac.name,
                    "M variable values",
                )
                if pmac.numMacroStationIcs == 0:
                    indexPage.tableColumn(row, "-")
                elif pmac.numMacroStationIcs is None and not os.path.exists(
                    "%s/%s_msivariables.htm" % (self.resultsDir, pmac.name)
                ):
                    indexPage.tableColumn(row, "-")
                else:
                    indexPage.href(
                        indexPage.tableColumn(row),
                        "%s_msivariables.htm" % pmac.name,
                        "MS variables",
                    )
                indexPage.href(
                    indexPage.tableColumn(row),
                    "%s_coordsystems.htm" % pmac.name,
                    "Coordinate systems",
                )
                indexPage.href(
                    indexPage.tableColumn(row), "%s_plcs.htm" % pmac.name, "PLCs"
                )
                indexPage.href(
                    indexPage.tableColumn(row),
                    "%s_motionprogs.htm" % pmac.name,
                    "Motion programs",
                )
            indexPage.write()
            # Dump the I variables for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    # Create the I variables top level web page
                    page = WebPage(
                        "I Variables for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_ivariables.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    page.href(
                        page.body(),
                        "%s_ivars_glob.htm" % pmac.name,
                        "Global I variables",
                    )
                    page.lineBreak(page.body())
                    for motor in range(1, pmac.numAxes + 1):
                        page.href(
                            page.body(),
                            "%s_ivars_motor%s.htm" % (pmac.name, motor),
                            "Motor %s I variables" % motor,
                        )
                        page.lineBreak(page.body())
                    page.write()
                    # Create the global I variables page
                    page = WebPage(
                        "Global I Variables for %s" % pmac.name,
                        "%s/%s_ivars_glob.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    pmac.htmlGlobalIVariables(page)
                    page.write()
                    # Create each I variables page
                    for motor in range(1, pmac.numAxes + 1):
                        page = WebPage(
                            "Motor %s I Variables for %s" % (motor, pmac.name),
                            "%s/%s_ivars_motor%s.htm"
                            % (self.resultsDir, pmac.name, motor),
                            styleSheet="analysis.css",
                        )
                        pmac.htmlMotorIVariables(motor, page)
                        page.write()
            # Dump the macrostation I variables for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    if pmac.numMacroStationIcs > 0:
                        # Create the MS,I variables top level web page
                        page = WebPage(
                            "Macrostation I Variables for %s (%s)"
                            % (pmac.name, datetime.today().strftime("%x %X")),
                            "%s/%s_msivariables.htm" % (self.resultsDir, pmac.name),
                            styleSheet="analysis.css",
                        )
                        page.href(
                            page.body(),
                            "%s_msivars_glob.htm" % pmac.name,
                            "Global macrostation I variables",
                        )
                        page.lineBreak(page.body())
                        for motor in range(1, pmac.numAxes + 1):
                            page.href(
                                page.body(),
                                "%s_msivars_motor%s.htm" % (pmac.name, motor),
                                "Motor %s macrostation I variables" % motor,
                            )
                            page.lineBreak(page.body())
                        page.write()
                        # Create the global macrostation I variables page
                        page = WebPage(
                            "Global Macrostation I Variables for %s" % pmac.name,
                            "%s/%s_msivars_glob.htm" % (self.resultsDir, pmac.name),
                            styleSheet="analysis.css",
                        )
                        pmac.htmlGlobalMsIVariables(page)
                        page.write()
                        # Create each motor macrostation I variables page
                        for motor in range(1, pmac.numAxes + 1):
                            page = WebPage(
                                "Motor %s Macrostation I Variables for %s"
                                % (motor, pmac.name),
                                "%s/%s_msivars_motor%s.htm"
                                % (self.resultsDir, pmac.name, motor),
                                styleSheet="analysis.css",
                            )
                            pmac.htmlMotorMsIVariables(motor, page)
                            page.write()
            # Dump the M variables for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    page = WebPage(
                        "M Variables for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_mvariables.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    )
                    row = None
                    for m in range(8192):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, "m%s->" % m)
                        var = pmac.hardwareState.getMVariable(m)
                        page.tableColumn(row, var.valStr())
                    for i in range(8):
                        page.tableColumn(row, "")
                    page.write()
            # Dump the M variable values for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    page = WebPage(
                        "M Variable values for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_mvariablevalues.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    )
                    row = None
                    for m in range(8192):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, "m%s" % m)
                        var = pmac.hardwareState.getMVariable(m)
                        page.tableColumn(row, var.contentsStr())
                    for i in range(8):
                        page.tableColumn(row, "")
                    page.write()
            # Dump the P variables for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    page = WebPage(
                        "P Variables for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_pvariables.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                    )
                    row = None
                    for m in range(8192):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, "p%s" % m)
                        var = pmac.hardwareState.getPVariable(m)
                        page.tableColumn(row, var.valStr())
                    for i in range(8):
                        page.tableColumn(row, "")
                    page.write()
            # Dump the PLCs for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    # Create the PLC top level web page
                    page = WebPage(
                        "PLCs for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_plcs.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    table = page.table(page.body(), ["PLC", "Code", "P Variables"])
                    for id in range(32):
                        plc = pmac.hardwareState.getPlcProgramNoCreate(id)
                        row = page.tableRow(table)
                        page.tableColumn(row, "%s" % id)
                        if plc is not None:
                            page.href(
                                page.tableColumn(row),
                                "%s_plc_%s.htm" % (pmac.name, id),
                                "Code",
                            )
                        else:
                            page.tableColumn(row, "-")
                        page.href(
                            page.tableColumn(row),
                            "%s_plc%s_p.htm" % (pmac.name, id),
                            "P%d..%d" % (id * 100, id * 100 + 99),
                        )
                    page.write()
                    # Create the listing pages
                    for id in range(32):
                        plc = pmac.hardwareState.getPlcProgramNoCreate(id)
                        if plc is not None:
                            page = WebPage(
                                "%s PLC%s" % (pmac.name, id),
                                "%s/%s_plc_%s.htm" % (self.resultsDir, pmac.name, id),
                                styleSheet="analysis.css",
                            )
                            plc.html2(page, page.body())
                            page.write()
                    # Create the P variable pages
                    for id in range(32):
                        page = WebPage(
                            "P Variables for %s PLC %s" % (pmac.name, id),
                            "%s/%s_plc%s_p.htm" % (self.resultsDir, pmac.name, id),
                            styleSheet="analysis.css",
                        )
                        table = page.table(
                            page.body(),
                            ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                        )
                        row = None
                        for m in range(100):
                            if m % 10 == 0:
                                row = page.tableRow(table)
                                page.tableColumn(row, "p%s" % (m + id * 100))
                            var = pmac.hardwareState.getPVariable(m + id * 100)
                            page.tableColumn(row, var.valStr())
                        page.write()
            # Dump the motion programs for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    # Create the motion program top level web page
                    page = WebPage(
                        "Motion Programs for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_motionprogs.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    table = page.table(page.body())
                    for id in range(256):
                        prog = pmac.hardwareState.getMotionProgramNoCreate(id)
                        if prog is not None:
                            row = page.tableRow(table)
                            page.tableColumn(row, "prog%s" % id)
                            page.href(
                                page.tableColumn(row),
                                "%s_prog_%s.htm" % (pmac.name, id),
                                "Code",
                            )
                    page.write()
                    # Create the listing pages
                    for id in range(256):
                        prog = pmac.hardwareState.getMotionProgramNoCreate(id)
                        if prog is not None:
                            page = WebPage(
                                "Motion Program %s for %s" % (id, pmac.name),
                                "%s/%s_prog_%s.htm" % (self.resultsDir, pmac.name, id),
                                styleSheet="analysis.css",
                            )
                            prog.html2(page, page.body())
                            page.write()
            # Dump the coordinate systems for each pmac
            for name, pmac in self.pmacs.items():
                if self.onlyPmacs is None or name in self.onlyPmacs:
                    # Create the coordinate systems top level web page
                    page = WebPage(
                        "Coordinate Systems for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_coordsystems.htm" % (self.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    table = page.table(
                        page.body(),
                        [
                            "CS",
                            "Axis def",
                            "Forward Kinematic",
                            "Inverse Kinematic",
                            "Q Variables",
                            "%",
                        ],
                    )
                    for id in range(1, 17):
                        row = page.tableRow(table)
                        page.tableColumn(row, "%s" % id)
                        col = page.tableColumn(row)
                        for m in range(1, 33):
                            var = pmac.hardwareState.getCsAxisDefNoCreate(id, m)
                            if var is not None and not var.isZero():
                                page.text(col, "#%s->" % m)
                                var.html(page, col)
                        col = page.tableColumn(row)
                        var = pmac.hardwareState.getForwardKinematicProgramNoCreate(id)
                        if var is not None:
                            var.html(page, col)
                        col = page.tableColumn(row)
                        var = pmac.hardwareState.getInverseKinematicProgramNoCreate(id)
                        if var is not None:
                            var.html(page, col)
                        page.href(
                            page.tableColumn(row),
                            "%s_cs%s_q.htm" % (pmac.name, id),
                            "Q Variables",
                        )
                        col = page.tableColumn(row)
                        var = pmac.hardwareState.getFeedrateOverrideNoCreate(id)
                        if var is not None:
                            var.html(page, col)
                    page.write()
                    for id in range(1, 17):
                        page = WebPage(
                            "Q Variables for %s CS %s" % (pmac.name, id),
                            "%s/%s_cs%s_q.htm" % (self.resultsDir, pmac.name, id),
                            styleSheet="analysis.css",
                        )
                        table = page.table(
                            page.body(),
                            ["", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
                        )
                        row = None
                        for m in range(100):
                            if m % 10 == 0:
                                row = page.tableRow(table)
                                page.tableColumn(row, "q%s" % m)
                            var = pmac.hardwareState.getQVariable(id, m)
                            page.tableColumn(row, var.valStr())
                        page.write()
            self.hudsonXmlReport()

    def loadFactorySettings(self, pmac, fileName, includeFiles):
        for i in range(8192):
            pmac.getIVariable(i)
        for m in range(8192):
            pmac.getMVariable(m)
        for p in range(8192):
            pmac.getPVariable(p)
        for cs in range(1, 17):
            for m in range(1, 33):
                pmac.getCsAxisDef(cs, m)
            for q in range(1, 200):
                pmac.getQVariable(cs, q)
        pmac.loadPmcFileWithPreprocess(fileName, includeFiles)

    def hudsonXmlReport(self):
        # Write out an XML report for Hudson
        xmlDoc = minidom.getDOMImplementation().createDocument(None, "testsuite", None)
        xmlTop = xmlDoc.documentElement
        xmlTop.setAttribute("tests", str(len(self.pmacs)))
        xmlTop.setAttribute("time", "0")
        xmlTop.setAttribute("timestamp", "0")
        for name, pmac in self.pmacs.items():
            element = xmlDoc.createElement("testcase")
            xmlTop.appendChild(element)
            element.setAttribute("classname", "pmac")
            element.setAttribute("name", name)
            element.setAttribute("time", "0")
            if not pmac.compareResult:
                errorElement = xmlDoc.createElement("error")
                element.appendChild(errorElement)
                errorElement.setAttribute("message", "Compare mismatch")
                textNode = xmlDoc.createTextNode(
                    "See file:///%s/index.htm for details" % self.resultsDir
                )
                errorElement.appendChild(textNode)
        wFile = open("%s/report.xml" % self.resultsDir, "w")
        xmlDoc.writexml(wFile, indent="", addindent="  ", newl="\n")
