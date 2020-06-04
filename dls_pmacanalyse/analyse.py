import logging
import os
import pickle
from xml.dom.minidom import getDOMImplementation

from dls_pmacanalyse.errors import ConfigError, PmacReadError
from dls_pmacanalyse.globalconfig import GlobalConfig
from dls_pmacanalyse.pmacstate import PmacState

log = logging.getLogger(__name__)


class Analyse:
    def __init__(self, config: GlobalConfig, pre_loaded=False):
        """Constructor."""
        self.pre_loaded = pre_loaded
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
            self.pmacFactorySettings,
            factorySettingsFilename,
            self.config.includePaths,
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
        # Analyse each pmac
        for name, pmac in self.config.pmacs.items():
            if self.config.onlyPmacs is None or name in self.config.onlyPmacs:

                if not self.pre_loaded:
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
                            continue
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
                matches = pmac.compare(theFixFile, theUnfixFile)
                if theFixFile is not None:
                    theFixFile.close()
                if theUnfixFile is not None:
                    theUnfixFile.close()

        # TODO this is a temporary mechanism for generating test data without
        # connecting to all pmacs every time
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
        xmlDoc = getDOMImplementation().createDocument(None, "testsuite", None)  # noqa
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
