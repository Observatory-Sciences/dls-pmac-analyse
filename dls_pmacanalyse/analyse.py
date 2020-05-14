import logging
import os
from datetime import datetime
from typing import cast
from xml.dom.minidom import getDOMImplementation
import pickle

from dls_pmacanalyse.errors import ConfigError, PmacReadError
from dls_pmacanalyse.globalconfig import GlobalConfig
from dls_pmacanalyse.pmacstate import PmacState
from dls_pmacanalyse.pmacvariables import PmacMVariable
from dls_pmacanalyse.webpage import WebPage

log = logging.getLogger(__name__)


class Analyse:
    def __init__(self, config: GlobalConfig):
        """Constructor."""
        self.config = config
        self.pmacFactorySettings = PmacState("pmacFactorySettings")
        self.geobrickFactorySettings = PmacState("geobrickFactorySettings")

    def analyse(self):
        """Performs the analysis of the PMACs."""
        # Load the factory settings
        factorySettingsFilename = os.path.join(
            os.path.dirname(__file__), "factorySettings_pmac.pmc"
        )
        self.loadFactorySettings(
            self.pmacFactorySettings, factorySettingsFilename, self.config.includePaths
        )
        factorySettingsFilename = os.path.join(
            os.path.dirname(__file__), "factorySettings_geobrick.pmc"
        )
        self.loadFactorySettings(
            self.geobrickFactorySettings,
            factorySettingsFilename,
            self.config.includePaths,
        )
        # Make sure the results directory exists
        if self.config.writeAnalysis:
            if not os.path.exists(self.config.resultsDir):
                os.makedirs(self.config.resultsDir)
            elif not os.path.isdir(self.config.resultsDir):
                raise ConfigError(
                    "Results path exists but is not a directory: %s"
                    % self.config.resultsDir
                )
        # Make sure the backup directory exists if it is required
        if self.config.backupDir is not None:
            if not os.path.exists(self.config.backupDir):
                os.makedirs(self.config.backupDir)
            elif not os.path.isdir(self.config.backupDir):
                raise ConfigError(
                    "Backup path exists but is not a directory: %s"
                    % self.config.backupDir
                )
        if self.config.writeAnalysis is True:
            # Drop a style sheet
            wFile = open("%s/analysis.css" % self.config.resultsDir, "w+")
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
        for name, pmac in self.config.pmacs.items():
            if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                # Create the comparison web page
                page = WebPage(
                    "Comparison results for %s (%s)"
                    % (pmac.name, datetime.today().strftime("%x %X")),
                    "%s/%s_compare.htm" % (self.config.resultsDir, pmac.name),
                    styleSheet="analysis.css",
                )
                # Read the hardware (or compare with file)
                if pmac.compareWith is None:
                    try:
                        pmac.readHardware(
                            self.config.backupDir,
                            self.config.checkPositions,
                            self.config.debug,
                            self.config.comments,
                            self.config.verbose,
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
                    if pmac.hardwareState.geobrick:
                        factoryDefs = self.geobrickFactorySettings
                    else:
                        factoryDefs = self.pmacFactorySettings
                pmac.loadReference(factoryDefs, self.config.includePaths)
                # Make the comparison
                theFixFile = None
                if self.config.fixfile is not None:
                    theFixFile = open(self.config.fixfile, "w")
                theUnfixFile = None
                if self.config.unfixfile is not None:
                    theUnfixFile = open(self.config.unfixfile, "w")
                matches = pmac.compare(page, theFixFile, theUnfixFile)
                if theFixFile is not None:
                    theFixFile.close()
                if theUnfixFile is not None:
                    theUnfixFile.close()
                # Write out the HTML
                if matches:
                    # delete any existing comparison file
                    if os.path.exists(
                        "%s/%s_compare.htm" % (self.config.resultsDir, pmac.name)
                    ):
                        os.remove(
                            "%s/%s_compare.htm" % (self.config.resultsDir, pmac.name)
                        )
                else:
                    if self.config.writeAnalysis is True:
                        page.write()
        if self.config.writeAnalysis is True:
            # Create the top level page
            indexPage = WebPage(
                "PMAC analysis (%s)" % datetime.today().strftime("%x %X"),
                "%s/index.htm" % self.config.resultsDir,
                styleSheet="analysis.css",
            )
            table = indexPage.table(indexPage.body())
            for name, pmac in self.config.pmacs.items():
                row = indexPage.tableRow(table)
                indexPage.tableColumn(row, "%s" % pmac.name)
                if os.path.exists(
                    "%s/%s_compare.htm" % (self.config.resultsDir, pmac.name)
                ):
                    indexPage.href(
                        indexPage.tableColumn(row),
                        "%s_compare.htm" % pmac.name,
                        "Comparison results",
                    )
                elif os.path.exists(
                    "%s/%s_plcs.htm" % (self.config.resultsDir, pmac.name)
                ):
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
                    "%s/%s_msivariables.htm" % (self.config.resultsDir, pmac.name)
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
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the I variables top level web page
                    page = WebPage(
                        "I Variables for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_ivariables.htm" % (self.config.resultsDir, pmac.name),
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
                        "%s/%s_ivars_glob.htm" % (self.config.resultsDir, pmac.name),
                        styleSheet="analysis.css",
                    )
                    pmac.htmlGlobalIVariables(page)
                    page.write()
                    # Create each I variables page
                    for motor in range(1, pmac.numAxes + 1):
                        page = WebPage(
                            "Motor %s I Variables for %s" % (motor, pmac.name),
                            "%s/%s_ivars_motor%s.htm"
                            % (self.config.resultsDir, pmac.name, motor),
                            styleSheet="analysis.css",
                        )
                        pmac.htmlMotorIVariables(motor, page)
                        page.write()
            # Dump the macrostation I variables for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    if pmac.numMacroStationIcs > 0:
                        # Create the MS,I variables top level web page
                        page = WebPage(
                            "Macrostation I Variables for %s (%s)"
                            % (pmac.name, datetime.today().strftime("%x %X")),
                            "%s/%s_msivariables.htm"
                            % (self.config.resultsDir, pmac.name),
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
                            "%s/%s_msivars_glob.htm"
                            % (self.config.resultsDir, pmac.name),
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
                                % (self.config.resultsDir, pmac.name, motor),
                                styleSheet="analysis.css",
                            )
                            pmac.htmlMotorMsIVariables(motor, page)
                            page.write()
            # Dump the M variables for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    page = WebPage(
                        "M Variables for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_mvariables.htm" % (self.config.resultsDir, pmac.name),
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
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    page = WebPage(
                        "M Variable values for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_mvariablevalues.htm"
                        % (self.config.resultsDir, pmac.name),
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
                        mvar = cast(PmacMVariable, (pmac.hardwareState.getMVariable(m)))
                        page.tableColumn(row, mvar.contentsStr())
                    for i in range(8):
                        page.tableColumn(row, "")
                    page.write()
            # Dump the P variables for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    page = WebPage(
                        "P Variables for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_pvariables.htm" % (self.config.resultsDir, pmac.name),
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
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the PLC top level web page
                    page = WebPage(
                        "PLCs for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_plcs.htm" % (self.config.resultsDir, pmac.name),
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
                                "%s/%s_plc_%s.htm"
                                % (self.config.resultsDir, pmac.name, id),
                                styleSheet="analysis.css",
                            )
                            plc.html2(page, page.body())
                            page.write()
                    # Create the P variable pages
                    for id in range(32):
                        page = WebPage(
                            "P Variables for %s PLC %s" % (pmac.name, id),
                            "%s/%s_plc%s_p.htm"
                            % (self.config.resultsDir, pmac.name, id),
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
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the motion program top level web page
                    page = WebPage(
                        "Motion Programs for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_motionprogs.htm" % (self.config.resultsDir, pmac.name),
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
                                "%s/%s_prog_%s.htm"
                                % (self.config.resultsDir, pmac.name, id),
                                styleSheet="analysis.css",
                            )
                            prog.html2(page, page.body())
                            page.write()
            # Dump the coordinate systems for each pmac
            for name, pmac in self.config.pmacs.items():
                if self.config.onlyPmacs is None or name in self.config.onlyPmacs:
                    # Create the coordinate systems top level web page
                    page = WebPage(
                        "Coordinate Systems for %s (%s)"
                        % (pmac.name, datetime.today().strftime("%x %X")),
                        "%s/%s_coordsystems.htm" % (self.config.resultsDir, pmac.name),
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
                            "%s/%s_cs%s_q.htm"
                            % (self.config.resultsDir, pmac.name, id),
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

            pickle_out = open("config.pickle", "wb")
            pickle.dump(self.config, pickle_out)
            pickle_out.close()

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
        xmlDoc = getDOMImplementation().createDocument(
            None, "testsuite", None
        )  # noqa
        xmlTop = xmlDoc.documentElement
        xmlTop.setAttribute("tests", str(len(self.config.pmacs)))
        xmlTop.setAttribute("time", "0")
        xmlTop.setAttribute("timestamp", "0")
        for name, pmac in self.config.pmacs.items():
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
                    "See file:///%s/index.htm for details" % self.config.resultsDir
                )
                errorElement.appendChild(textNode)
        wFile = open("%s/report.xml" % self.config.resultsDir, "w")
        xmlDoc.writexml(wFile, indent="", addindent="  ", newl="\n")
