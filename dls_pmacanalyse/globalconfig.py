import getopt
import logging
import sys
from typing import Dict

from dls_pmacanalyse.errors import ArgumentError, ConfigError
from dls_pmacanalyse.pmac import Pmac
from dls_pmacanalyse.pmacparser import PmacParser
from dls_pmacanalyse.pmacvariables import (
    PmacIVariable,
    PmacMsIVariable,
    PmacMVariable,
    PmacPVariable,
    PmacQVariable,
)

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
        self.resultsDir = "pmacAnalysis"
        self.onlyPmacs = None
        self.includePaths = None
        self.checkPositions = False
        self.debug = False
        self.fixfile = None
        self.unfixfile = None
        self.pmacs: Dict[str, Pmac] = {}

    def createOrGetPmac(self, name: str):
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
                    curPmac.setGeobrick(True)
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
