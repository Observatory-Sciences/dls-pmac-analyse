#!/bin/env dls-python
# ------------------------------------------------------------------------------
# pmacanalyse.py
#
# Author:  Jonathan Thompson
# Created: 20 November 2009
# Purpose: Provide a whole range of PMAC monitoring services, backups, compares, etc.
# ------------------------------------------------------------------------------

import logging
import pickle
import sys
from pathlib import Path

from dls_pmacanalyse.analyse import Analyse
from dls_pmacanalyse.globalconfig import GlobalConfig
from dls_pmacanalyse.report import Report

# get the root logger to control application wide log levels
log = logging.getLogger()


helpText = """
  Analyse or backup a group of Delta-Tau PMAC motor controllers.

  Syntax:
    dls-pmac-analyse.py [<options>] [<configFile>]
        where <options> is one or more of:
        -v, --verbose             Verbose output
        -h, --help                print(the help text and exit
        --backup=<dir>            As config file 'backup' statement (see below)
        --comments                As config file 'comments' statement (see below)
        --resultsdir=<dir>        As config file 'resultsdir' statement (see below)
        --pmac=<name>             As config file 'pmac' statement (see below)
        --ts=<ip>:<port>          As config file 'ts' statement (see below)
        --tcpip=<ip>:<port>       As config file 'tcpip' statement (see below)
        --comparewith=<pmcFile>   As config file 'comparewith' statement (see below)
        --nocompare=<varSpec>     As config file 'nocompare' statement (see below)
        --compare=<varSpec>       As config file 'compare' statement (see below)
        --reference=<filename>    As config file 'reference' statement (see below)
        --include=<paths>         As config file 'include' statement (see below)
        --nofactorydefs           As config file 'nofactorydefs' statement (see below)
        --only=<name>             Only analyse the named pmac. There can be more than
                                  one of these.
        --macroics=<num>          As config file 'macroics' statement (see below)
        --checkpositions          Prints a warning if motor positions change during
                                  readout
        --debug                   Turns on extra debug output
        --fixfile=<file>          Generate a fix file that can be loaded to the PMAC
        --unfixfile=<file>        Generate a file that can be used to correct the
                                  reference
        --loglevel=<level>        set logging to error warning info or debug

  Config file syntax:
    resultsdir <dir>
      Directory into which to place the results HTML files.  Defaults to pmacAnalysis.
    pmac <name>
      Define a PMAC.
        name = Name of the PMAC
    ts <host> <port>
      Connect through a terminal server
        host = Name or IP address of terminal server
        port = Host port number
    tcpip <host> <port>
      Connect through TCP/IP
        host = Name or IP address of host
        port = Host port number
    backup <dir>
      Write backup files in the specified directory.  Defaults to no backup written.
    comments
      Write comments into backup files.
    comparewith <pmcfile>
      Rather than reading the hardware, use this PMC file as
      the current PMAC state.
    nocompare <varSpec>
      Specify one or more variables that are not to be compared.
        varSpec = variables specification, no embedded spaces allowed.
          <type><start>
          <type><start>..<end>
          <type><start>,<count>,<increment>
        the <type> is one of
            i
            p
            m
            ms<node>,i
            ms<nodeList>,i
            &<cs>q
        node = macrostation node number
        nodeList = [<node>,<node>...] comma seperated list of nodes
        cs = coordinate system number
        start = first (or only) variable number
        count = number of variables
        increment = increment between variables
        end = last variable number
    compare <varSpec>
      Specify one or more variables should be compared.  Reverses the effect of
      a previous nocompare.  Useful for overriding defaults.
        varSpec = variables specification, no embedded spaces allowed.
          <type><start>
          <type><start>..<end>
          <type><start>,<count>,<increment>
        the <type> is one of
            i
            p
            m
            ms<node>,i
            ms<nodeList>,i
            &<cs>q
        node = macrostation node number
        nodeList = [<node>,<node>...] comma seperated list of nodes
        cs = coordinate system number
        start = first (or only) variable number
        count = number of variables
        increment = increment between variables
        end = last variable number
    reference <filename>
      The PMC file to use as the reference during compares
        filename = PMC file name
    include <paths>
      Colon seperated list of include pathnames for PMC file preprocessor
    nofactorydefs
      Specifies that the factory defaults should not be used to initialise the
      the reference state before loading the reference PMC file.
    macroics <num>
      The number of macro ICs the PMAC has.  If not specified, the number
      is automatically determined.
  """


def main():
    """Main entry point of the script."""

    config = GlobalConfig()

    # interactive launch - setup logger appropriately
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # add the handler to the root logger
    log.addHandler(console)
    log.setLevel(logging.INFO)

    if config.processArguments():
        config.processConfigFile()
        if config.test:
            config_pickle = Path(__file__).parent / "../tests/config.pickle"
            with open(config_pickle, "rb") as pickle_in:
                config: GlobalConfig = pickle.load(pickle_in)
            analyse = Analyse(config, pre_loaded=True)
            analyse.analyse()
        else:
            analyse = Analyse(config)
            analyse.analyse()
        # TODO this is for testing - will use correct path when old HTML code is removed
        report = Report(Path("/tmp"))
        report.pmacs_to_html(config.pmacs)
    else:
        log.error(helpText)
    return 0


if __name__ == "__main__":
    sys.exit(main())
