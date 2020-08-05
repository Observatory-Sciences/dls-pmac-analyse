#!/bin/env dls-python
# ------------------------------------------------------------------------------
# pmacanalyse.py
#
# Author:  Jonathan Thompson
# Created: 20 November 2009
# Purpose: Provide a whole range of PMAC monitoring services, backups, compares, etc.
#
# Major Overhaul: Giles Knap July 2020
#  ------------------------------------------------------------------------------

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import click
import regex as re
from click_configfile import Param, SectionSchema, matches_section

from dls_pmacanalyse.analyse import Analyse
from dls_pmacanalyse.configfilereader import ConfigFileReader2
from dls_pmacanalyse.errors import ArgumentError
from dls_pmacanalyse.globalconfig import GlobalConfig
from dls_pmacanalyse.pmac import Pmac
from dls_pmacanalyse.report import Report

# get the root logger to control application wide log levels
log = logging.getLogger()

SECTION_PREFIX = "pmac."

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


class ConfigSectionSchema(object):
    """Describes all config sections of this configuration file."""

    @matches_section("global")
    class Global(SectionSchema):
        # these global arguments can be overridden on the command line
        # their type checking is provided in the click.option decorators of main()
        resultsdir = Param()
        nocompare = Param(multiple=True)
        backup = Param()
        comments = Param(multiple=True)

    @matches_section("pmac.*")  # Matches multiple sections
    class Pmac(SectionSchema):
        ts = Param()
        tcpip = Param()
        geobrick = Param(type=bool)
        vme_pmac = Param(type=bool)
        reference = Param(type=click.Path(exists=True, dir_okay=False))
        include = Param(type=click.Path(exists=True, file_okay=False))
        nocompare = Param(multiple=True)
        compare = Param(multiple=True)
        comparewith = Param(type=click.Path(exists=True, dir_okay=False))
        nofactorydefs = Param(type=bool)


class ConfigFileProcessor(ConfigFileReader2):
    config_files = ["analyse.ini"]
    config_section_schemas = [
        ConfigSectionSchema.Global,  # PRIMARY SCHEMA
        ConfigSectionSchema.Pmac,
    ]


CONTEXT_SETTINGS = dict(
    default_map=ConfigFileProcessor.read_config(inline_comment_prefixes=[";", "#"])
)

# global settings
@click.option("--resultsdir", default="pmacAnalysis", type=click.Path(file_okay=False))
@click.option("--verbose", "-v", is_flag=True)
@click.option("--backup", type=click.Path(file_okay=False))
@click.option("--only", multiple=True)
@click.option("--checkpositions", is_flag=True)
@click.option("--debug", is_flag=True)
@click.option("--comments", is_flag=True)
@click.option("--fixfile", type=click.Path(dir_okay=False))
@click.option("--unfixfile", type=click.Path(dir_okay=False))
@click.option(
    "--loglevel", type=click.Choice(["error", "warning", "info", "debug", "critical"])
)
# settings for a single pmac
@click.option("--pmac")
@click.option("--include", type=click.Path(exists=True, dir_okay=False))
@click.option("--ts")
@click.option("--tcpip")
@click.option("--geobrick", type=bool)
@click.option("--vmepmac", type=bool)
@click.option("--reference", type=click.Path(exists=True, dir_okay=False))
@click.option("--comparewith", type=click.Path(exists=True, dir_okay=False))
@click.option("--nocompare", multiple=True)
@click.option("--compare", multiple=True)
@click.option("--nofactorydefs", is_flag=True)
@click.option("--macroics", type=int)
@click.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
def main(
    context,
    resultsdir,
    verbose,
    backup,
    only,
    nocompare,
    checkpositions,
    debug,
    comments,
    fixfile,
    unfixfile,
    loglevel,
    pmac,
    include,
    ts,
    tcpip,
    geobrick,
    vmepmac,
    reference,
    comparewith,
    compare,
    nofactorydefs,
    macroics,
):
    """Main entry point of the script."""

    # save the global command line parameters in a global config object
    config = GlobalConfig(
        verbose=verbose,
        backupDir=backup,
        comments=comments,
        resultsDir=resultsdir,
        onlyPmacs=only,
        global_nocompare=nocompare,
        checkPositions=checkpositions,
        debug=debug,
        fixfile=Path(fixfile) if fixfile else None,
        unfixfile=Path(unfixfile) if unfixfile else None,
        writeAnalysis=True,
        include=include,
    )

    # add in command line defined pmac if there was one
    if pmac:
        add_pmac(
            config=config,
            name=pmac,
            ts=ts,
            tcpip=tcpip,
            geobrick=geobrick,
            vme_pmac=vmepmac,
            no_factory_defaults=nofactorydefs,
            reference=reference,
            compareWith=comparewith,
            nocompare=[],
            compare=compare,
            macroics=macroics,
        )

    # set up logging
    numeric_level = getattr(logging, str(loglevel).upper(), "INFO")
    # interactive launch - setup logger appropriately
    console = logging.StreamHandler()
    console.setLevel(numeric_level)
    # add the handler to the root logger
    log.addHandler(console)
    log.setLevel(numeric_level)

    map: Dict[str, Any] = context.default_map

    # TODO Temporary debug of command line and config file parsing
    log.debug(f"Global Config - {config}")
    for section in map:
        log.debug(f"  {section}")
        if section.startswith("pmac"):
            for field in map[section]:
                log.debug(f"    {field}: {map[section][field]}")
        else:
            log.debug(map[section])

    for name, value in map.items():
        if name.startswith(SECTION_PREFIX):
            name = name[len(SECTION_PREFIX):]
            if only != () and name not in only:
                continue
            add_pmac(
                config=config,
                name=name,
                ts=value.get("ts"),
                tcpip=value.get("tcpip"),
                geobrick=value.get("geobrick"),
                vme_pmac=value.get("vme_pmac"),
                no_factory_defaults=value.get("no_factory_defaults"),
                reference=value.get("reference"),
                compareWith=value.get("comparewith"),
                nocompare=value.get("nocompare"),
                compare=value.get("compare"),
                macroics=value.get("macroics"),
            )

    analyse = Analyse(config)
    analyse.analyse()

    if config.writeAnalysis:
        report = Report(Path(config.resultsDir))
        report.pmacs_to_html(config.pmacs)
    else:
        log.error(helpText)
        return 1
    return 0


def add_pmac(
    config: GlobalConfig,
    name: str,
    ts: str,
    tcpip: str,
    geobrick: str,
    vme_pmac,
    no_factory_defaults: str,
    reference: str,
    compareWith: str,
    nocompare: List[str],
    compare: List[str],
    macroics: int,
):
    if name not in config.pmacs:
        config.pmacs[name] = Pmac(name)
        config.pmacs[name].setNoCompare(config.global_nocompare)
    pmac = config.pmacs[name]

    # todo get rid of all of these 'set' functions in Pmac and give it a
    # __init__ parameter for these elements instead

    if ts:
        parts = re.split(" |:", ts)
        if len(parts) != 2:
            raise ArgumentError("Bad terminal server argument")
        else:
            pmac.setProtocol(parts[0], parts[1], True)
    elif tcpip:
        parts = re.split(" |:", tcpip)
        if len(parts) != 2:
            raise ArgumentError("Bad TCP/IP argument")
        else:
            pmac.setProtocol(parts[0], parts[1], False)

    if geobrick:
        pmac.setGeobrick(True)
    elif vme_pmac:
        pmac.setGeobrick(False)

    if no_factory_defaults:
        pmac.setNoFactoryDefs()

    if reference:
        pmac.setReference(reference)
    else:
        raise (ArgumentError(f"no reference for pmac {name}"))

    if compareWith:
        pmac.setCompareWith(compareWith)

    if nocompare:
        pmac.setNoCompare(nocompare)
    if compare:
        pmac.clearNoCompare(compare)

    if macroics:
        pmac.setNumMacroStationIcs(macroics)


if __name__ == "__main__":
    sys.exit(main())
