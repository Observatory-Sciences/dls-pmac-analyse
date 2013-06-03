#!/bin/env dls-python2.6
# ------------------------------------------------------------------------------
# pmacanalyse.py
# 
# Author:  Jonathan Thompson
# Created: 20 November 2009
# Purpose: Provide a whole range of PMAC monitoring services, backups, compares, etc.
# ------------------------------------------------------------------------------

import getopt, sys, re, os, datetime, os.path
from xml.dom.minidom import *
from pkg_resources import require
require('dls_pmaclib')
from dls_pmaclib.dls_pmcpreprocessor import *
from dls_pmaclib.dls_pmacremote import *

helpText = '''
  Analyse or backup a group of Delta-Tau PMAC motor controllers.

  Syntax:
    dls-pmac-analyse.py [<options>] [<configFile>]
        where <options> is one or more of:
        -v, --verbose             Verbose output
        -h, --help                Print the help text and exit
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
        --only=<name>             Only analyse the named pmac
        --macroics=<num>          As config file 'macroics' statement (see below)
        --checkpositions          Prints a warning if motor positions change during readout
        --debug                   Turns on extra debug output
        --fixfile=<file>          Generate a fix file that can be loaded to the PMAC

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
  '''

def tokenIsInt(token):
    '''Returns true if the token is an integer.'''
    if str(token)[0] == '$':
        result = len(str(token)) > 1
        for ch in str(token)[1:]:
            if ch not in '0123456789ABCDEFabcdef':
                result = False
    else:
        result = str(token).isdigit()
    return result
def tokenToInt(token):
    if not tokenIsInt(token):
        raise ParserError("Integer expected, got: %s" % token, token)
    if str(token)[0] == '$':
        result = int(str(token)[1:], 16)
    else:
        result = int(str(token))
    return result
def tokenIsFloat(token):
    '''Returns true if the token is a floating point number.'''
    result = True
    if not tokenIsInt(token):
        result = True
        for ch in str(token):
            if ch not in '0123456789.':
                result = False
    return result
def tokenToFloat(token):
    if tokenIsInt(token):
        result = tokenToInt(token)
    elif tokenIsFloat(token):
        result = float(str(token))
    else:
        raise ParserError("Float expected, got: %s" % token, token)
    return result
def numericSplit(a):
    '''Splits a into two parts, a numeric suffix (or 0 if none) and an
       alphanumeric prefix (the remainder).  The parts are returned
       as a tuple.'''
    splitPos = len(a)
    inSuffix = True
    while splitPos > 0 and inSuffix:
        if a[splitPos-1].isdigit():
            splitPos -= 1
        else:
            inSuffix = False
    prefix = a[:splitPos]
    suffix = a[splitPos:]
    if len(suffix) > 0:
        suffix = int(suffix)
    else:
        suffix = 0
    return (prefix, suffix)
def numericSort(a, b):
    '''Used by the sort algorithm to get numeric suffixes in the right order.'''
    prefixa, suffixa = numericSplit(a)
    prefixb, suffixb = numericSplit(b)
    if prefixa < prefixb:
        result = -1
    elif prefixa > prefixb: 
        result = 1
    elif suffixa < suffixb:
        result = -1
    elif suffixb < suffixa:
        result = 1
    else:
        result = 0
    return result

class PmacReadError(Exception):
    '''PMAC read error exception.'''
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class ArgumentError(Exception):
    '''Command line argument error exception.'''
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class ConfigError(Exception):
    '''Configuration file error exception.'''
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class AnalyseError(Exception):
    '''Analysis error exception.'''
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class LexerError(Exception):
    '''Lexer error exception.'''
    def __init__(self, token, fileName, line):
        self.token = token
        self.fileName = fileName
        self.line = line
    def __str__(self):
        return '[%s:%s] Unknown token: %s' % (self.fileName, self.line, self.token)

class ParserError(Exception):
    '''Parser error exception.'''
    def __init__(self, message, token):
        self.message = message
        self.line = token.line
        self.fileName = token.fileName
    def __str__(self):
        return '[%s:%s] %s' % (self.fileName, self.line, self.message)

class GeneralError(Exception):
    '''General error exception.'''
    def __init__(self, message, line):
        self.message = message
    def __str__(self):
        return self.message

class PmacToken(object):
    def __init__(self, text=None):
        self.fileName = ''
        self.line = ''
        self.text = ''
        self.compareFail = False
        if text is not None:
            self.text = text
    def set(self, text, fileName, line):
        self.text = text
        self.fileName = fileName
        self.line = line
        self.compareFail = False
    def __str__(self):
        return self.text
    def __eq__(self, other):
        return self.text == str(other)
    def __ne__(self, other):
        return self.text != str(other)
    def __len__(self):
        return len(self.text)
    def lower(self):
        return self.text.lower()

class GlobalConfig(object):
    '''A single instance of this class contains the global configuration.'''
    def __init__(self):
        '''Constructor.'''
        self.verbose = False
        self.backupDir = None
        self.comments = False
        self.configFile = None
        self.pmacs = {}
        self.pmacFactorySettings = PmacState('pmacFactorySettings')
        self.geobrickFactorySettings = PmacState('geobrickFactorySettings')
        self.resultsDir = 'pmacAnalysis'
        self.onlyPmac = None
        self.includePaths = None
        self.checkPositions = False
        self.debug = False
        self.fixfile = None
    def createOrGetPmac(self, name):
        if name not in self.pmacs:
            self.pmacs[name] = Pmac(name)
        return self.pmacs[name]
    def processArguments(self):
        '''Process the command line arguments.  Returns False
           if the program is to print the help and exit.'''
        try:
            opts, args = getopt.gnu_getopt(sys.argv[1:], 'vh', 
                ['help', 'verbose', 'backup=', 'pmac=', 'ts=', 'tcpip=',
                'geobrick', 'vmepmac', 'reference=', 'comparewith=',
                'resultsdir=', 'nocompare=', 'only=', 'include=',
                'nofactorydefs', 'macroics=', 'checkpositions', 'debug', 'comments',
                'fixfile='])
        except getopt.GetoptError, err:
            raise ArgumentError(str(err))
        globalPmac = Pmac('global')
        curPmac = None
        for o, a in opts:
            if o in ('-h', '--help'):
                return False
            elif o in ('-v', '--verbose'):
                self.verbose = True
            elif o == '--backup':
                self.backupDir = a
            elif o == '--comments':
                self.comments = True
            elif o == '--pmac':
                curPmac = self.createOrGetPmac(a)
                curPmac.copyNoComparesFrom(globalPmac)
            elif o == '--ts':
                parts = a.split(':')
                if len(parts) != 2:
                    raise ArgumentError('Bad terminal server argument')
                elif curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setProtocol(parts[0], parts[1], True)
            elif o == '--tcpip':
                parts = a.split(':')
                if len(parts) != 2:
                    raise ArgumentError('Bad TCP/IP argument')
                elif curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setProtocol(parts[0], parts[1], False)
            elif o == '--geobrick':
                if curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setGeobrick(True)
            elif o == '--debug':
                self.debug = True
            elif o == '--vmepmac':
                if curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setGeobrick(False)
            elif o == '--nofactorydefs':
                if curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setNoFactoryDefs()
            elif o == '--reference':
                if curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setReference(a)
            elif o == '--fixfile':
                self.fixfile = a
            elif o == '--comparewith':
                if curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setCompareWith(a)
            elif o == '--resultsdir':
                self.resultsDir = a
            elif o == '--nocompare':
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
            elif o == '--compare':
                if curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    parser = PmacParser(a, None)
                    (type, nodeList, start, count, increment) = parser.parseVarSpec()
                    while count > 0:
                        var = self.makeVars(type, nodeList, start)
                        curPmac.clearNoCompare(var)
                        start += increment
                        count -= 1
            elif o == '--only':
                self.onlyPmac = a
            elif o == '--include':
                self.includePaths = a
            elif o == '--macroics':
                if curPmac is None:
                    raise ArgumentError('No PMAC yet defined')
                else:
                    curPmac.setNumMacroStationIcs(int(a))
            elif o == '--checkpositions':
                self.checkPositions = True
        if len(args) > 1:
            raise ArgumentError('Too many arguments.')
        if len(args) == 1:
            self.configFile = args[0]
        return True
    def processConfigFile(self):
        '''Process the configuration file.'''
        if self.configFile is None:
            return
        file = open(self.configFile, 'r')
        if file is None:
            raise ConfigError('Could not open config file: %s' % self.configFile)
        globalPmac = Pmac('global')
        curPmac = None
        for line in file:
            words = line.split(';', 1)[0].strip().split()
            if len(words) >= 1:
                if words[0].lower() == 'pmac' and len(words) == 2:
                    curPmac = self.createOrGetPmac(words[1])
                    curPmac.copyNoComparesFrom(globalPmac)
                elif words[0].lower() == 'ts' and len(words) == 3 and curPmac is not None:
                    curPmac.setProtocol(words[1], int(words[2]), True)
                elif words[0].lower() == 'tcpip' and len(words) == 3 and curPmac is not None:
                    curPmac.setProtocol(words[1], int(words[2]), False)
                elif words[0].lower() == 'geobrick' and len(words) == 1 and curPmac is not None:
                    curPmac.setGeobrick()
                elif words[0].lower() == 'nofactorydefs' and len(words) == 1 and curPmac is not None:
                    curPmac.setNoFactoryDefs()
                elif words[0].lower() == 'reference' and len(words) == 2 and curPmac is not None:
                    curPmac.setReference(words[1])
                elif words[0].lower() == 'comparewith' and len(words) == 2 and curPmac is not None:
                    curPmac.setCompareWith(words[1])
                elif words[0].lower() == 'resultsdir' and len(words) == 2:
                    self.resultsDir = words[1]
                elif words[0].lower() == 'include' and len(words) == 2:
                    self.includePaths = words[1]
                elif words[0].lower() == 'backup' and len(words) == 2:
                    self.backupDir = words[1]
                elif words[0].lower() == 'comments' and len(words) == 1:
                    self.comments = True
                elif words[0].lower() == 'nocompare' and len(words) == 2:
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
                elif words[0].lower() == 'compare' and len(words) == 2 and curPmac is not None:
                    parser = PmacParser([words[1]], None)
                    (type, nodeList, start, count, increment) = parser.parseVarSpec()
                    while count > 0:
                        var = self.makeVars(type, nodeList, start)
                        curPmac.clearNoCompare(var)
                        start += increment
                        count -= 1
                elif words[0].lower() == 'macroics' and len(words) == 2 and curPmac is not None:
                    curPmac.setNumMacroStationIcs(int(words[1]))
                else:
                    raise ConfigError("Unknown configuration: %s" % repr(line))
    def makeVars(self, varType, nodeList, n):
        '''Makes a variable of the correct type.'''
        result = []
        if varType == 'i':
            result.append(PmacIVariable(n))
        elif varType == 'p':
            result.append(PmacPVariable(n))
        elif varType == 'm':
            result.append(PmacMVariable(n))
        elif varType == 'ms':
            for ms in nodeList:
                result.append(PmacMsIVariable(ms, n))
        elif varType == '&':
            for cs in nodeList:
                result.append(PmacQVariable(cs, n))
        else:
            raise ConfigError('Cannot decode variable type %s' % repr(varType))
        return result
    def analyse(self):
        '''Performs the analysis of the PMACs.'''
        # Load the factory settings
        factorySettingsFilename = os.path.join(os.path.dirname(__file__),
            'factorySettings_pmac.pmc')
        self.loadFactorySettings(self.pmacFactorySettings,
            factorySettingsFilename, self.includePaths)
        factorySettingsFilename = os.path.join(os.path.dirname(__file__),
            'factorySettings_geobrick.pmc')
        self.loadFactorySettings(self.geobrickFactorySettings,
            factorySettingsFilename, self.includePaths)
        # Make sure the results directory exists
        if not os.path.exists(self.resultsDir):
            os.makedirs(self.resultsDir)
        elif not os.path.isdir(self.resultsDir):
            raise ConfigError('Results path exists but is not a directory: %s' %\
                self.resultsDir)
        # Make sure the backup directory exists if it is required
        if self.backupDir is not None:
            if not os.path.exists(self.backupDir):
                os.makedirs(self.backupDir)
            elif not os.path.isdir(self.backupDir):
                raise ConfigError('Backup path exists but is not a directory: %s' %\
                    self.backupDir)
        # Drop a style sheet
        wFile = open('%s/analysis.css' % self.resultsDir, 'w+')
        wFile.write('''
            p{text-align:left; color:black; font-family:arial}
            h1{text-align:center; color:green}
            table{border-collapse:collapse}
            table, th, td{border:1px solid black}
            th, td{padding:5px; vertical-align:top}
            th{background-color:#EAf2D3; color:black}
            em{color:red; font-style:normal; font-weight:bold}
            #code{white-space:pre}
            #code{font-family:courier}
            ''')
        # Analyse each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                # Create the comparison web page
                page = WebPage('Comparison results for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_compare.htm' % (self.resultsDir, pmac.name),
                    styleSheet='analysis.css')
                # Read the hardware (or compare with file)
                if pmac.compareWith is None:
                    try:
                        pmac.readHardware(self.backupDir, self.checkPositions, self.debug, self.comments)
                    except PmacReadError as pErr:
                    	import traceback
                    	traceback.print_exc()
                        print "FAILED TO CONNECT TO " + pmac.name
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
                matches = pmac.compare(page, theFixFile)
                if theFixFile is not None:
                    theFixFile.close()
                # Write out the HTML
                if matches:
                    # delete any existing comparison file
                    if os.path.exists('%s/%s_compare.htm' % (self.resultsDir, pmac.name)):
                        os.remove('%s/%s_compare.htm' % (self.resultsDir, pmac.name))
                else:
                    page.write()
        # Create the top level page
        indexPage = WebPage('PMAC analysis (%s)' % datetime.datetime.today().strftime('%x %X'), 
            '%s/index.htm' % self.resultsDir,
            styleSheet='analysis.css')
        table = indexPage.table(indexPage.body())
        for name,pmac in self.pmacs.iteritems():
            row = indexPage.tableRow(table)
            indexPage.tableColumn(row, '%s' % pmac.name)
            if os.path.exists('%s/%s_compare.htm' % (self.resultsDir, pmac.name)):
                indexPage.href(indexPage.tableColumn(row), 
                    '%s_compare.htm' % pmac.name, 'Comparison results')
            elif os.path.exists('%s/%s_plcs.htm' % (self.resultsDir, pmac.name)):
                indexPage.tableColumn(row, 'Matches')
            else:
                indexPage.tableColumn(row, 'No results')
            indexPage.href(indexPage.tableColumn(row), 
                '%s_ivariables.htm' % pmac.name, 'I variables')
            indexPage.href(indexPage.tableColumn(row), 
                '%s_pvariables.htm' % pmac.name, 'P variables')
            indexPage.href(indexPage.tableColumn(row), 
                '%s_mvariables.htm' % pmac.name, 'M variables')
            indexPage.href(indexPage.tableColumn(row), 
                '%s_mvariablevalues.htm' % pmac.name, 'M variable values')
            if pmac.numMacroStationIcs == 0:
                indexPage.tableColumn(row, '-')
            elif pmac.numMacroStationIcs is None and \
                    not os.path.exists('%s/%s_msivariables.htm' % (self.resultsDir, pmac.name)):
                indexPage.tableColumn(row, '-')
            else:
                indexPage.href(indexPage.tableColumn(row), 
                    '%s_msivariables.htm' % pmac.name, 'MS variables')
            indexPage.href(indexPage.tableColumn(row), 
                '%s_coordsystems.htm' % pmac.name, 'Coordinate systems')
            indexPage.href(indexPage.tableColumn(row), 
                '%s_plcs.htm' % pmac.name, 'PLCs')
            indexPage.href(indexPage.tableColumn(row), 
                '%s_motionprogs.htm' % pmac.name, 'Motion programs')
        indexPage.write()
        # Dump the I variables for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                # Create the I variables top level web page
                page = WebPage('I Variables for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_ivariables.htm' % (self.resultsDir, pmac.name), 
                    styleSheet='analysis.css')
                page.href(page.body(), '%s_ivars_glob.htm' % pmac.name, 'Global I variables')
                page.lineBreak(page.body())
                for motor in range(1, pmac.numAxes+1):
                    page.href(page.body(), '%s_ivars_motor%s.htm' % (pmac.name, motor), 
                        'Motor %s I variables' % motor)
                    page.lineBreak(page.body())
                page.write()
                # Create the global I variables page
                page = WebPage('Global I Variables for %s' % pmac.name, 
                    '%s/%s_ivars_glob.htm' % (self.resultsDir, pmac.name),
                    styleSheet='analysis.css')
                pmac.htmlGlobalIVariables(page)
                page.write()
                # Create each I variables page
                for motor in range(1, pmac.numAxes+1):
                    page = WebPage('Motor %s I Variables for %s' % (motor, pmac.name), 
                        '%s/%s_ivars_motor%s.htm' % (self.resultsDir, pmac.name, motor),
                        styleSheet='analysis.css')
                    pmac.htmlMotorIVariables(motor, page)
                    page.write()
        # Dump the macrostation I variables for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                if pmac.numMacroStationIcs > 0:
                    # Create the MS,I variables top level web page
                    page = WebPage('Macrostation I Variables for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')),
                        '%s/%s_msivariables.htm' % (self.resultsDir, pmac.name), 
                        styleSheet='analysis.css')
                    page.href(page.body(), '%s_msivars_glob.htm' % pmac.name, 'Global macrostation I variables')
                    page.lineBreak(page.body())
                    for motor in range(1, pmac.numAxes+1):
                        page.href(page.body(), '%s_msivars_motor%s.htm' % (pmac.name, motor), 
                            'Motor %s macrostation I variables' % motor)
                        page.lineBreak(page.body())
                    page.write()
                    # Create the global macrostation I variables page
                    page = WebPage('Global Macrostation I Variables for %s' % pmac.name, 
                        '%s/%s_msivars_glob.htm' % (self.resultsDir, pmac.name),
                        styleSheet='analysis.css')
                    pmac.htmlGlobalMsIVariables(page)
                    page.write()
                    # Create each motor macrostation I variables page
                    for motor in range(1, pmac.numAxes+1):
                        page = WebPage('Motor %s Macrostation I Variables for %s' % (motor, pmac.name), 
                            '%s/%s_msivars_motor%s.htm' % (self.resultsDir, pmac.name, motor),
                            styleSheet='analysis.css')
                        pmac.htmlMotorMsIVariables(motor, page)
                        page.write()
        # Dump the M variables for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                page = WebPage('M Variables for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_mvariables.htm' % (self.resultsDir, pmac.name), 
                    styleSheet='analysis.css')
                table = page.table(page.body(), ['','0','1','2','3','4','5','6','7','8','9'])
                row = None
                for m in range(8192):
                    if m % 10 == 0:
                        row = page.tableRow(table)
                        page.tableColumn(row, 'm%s->' % m)
                    var = pmac.hardwareState.getMVariable(m)
                    page.tableColumn(row, var.valStr())
                for i in range(8):
                    page.tableColumn(row, '')
                page.write()
        # Dump the M variable values for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                page = WebPage('M Variable values for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_mvariablevalues.htm' % (self.resultsDir, pmac.name), 
                    styleSheet='analysis.css')
                table = page.table(page.body(), ['','0','1','2','3','4','5','6','7','8','9'])
                row = None
                for m in range(8192):
                    if m % 10 == 0:
                        row = page.tableRow(table)
                        page.tableColumn(row, 'm%s' % m)
                    var = pmac.hardwareState.getMVariable(m)
                    page.tableColumn(row, var.contentsStr())
                for i in range(8):
                    page.tableColumn(row, '')
                page.write()
        # Dump the P variables for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                page = WebPage('P Variables for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_pvariables.htm' % (self.resultsDir, pmac.name), 
                    styleSheet='analysis.css')
                table = page.table(page.body(), ['','0','1','2','3','4','5','6','7','8','9'])
                row = None
                for m in range(8192):
                    if m % 10 == 0:
                        row = page.tableRow(table)
                        page.tableColumn(row, 'p%s' % m)
                    var = pmac.hardwareState.getPVariable(m)
                    page.tableColumn(row, var.valStr())
                for i in range(8):
                    page.tableColumn(row, '')
                page.write()
        # Dump the PLCs for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                # Create the PLC top level web page
                page = WebPage('PLCs for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_plcs.htm' % (self.resultsDir, pmac.name),
                    styleSheet='analysis.css')
                table = page.table(page.body(), 
                    ['PLC', 'Code', 'P Variables'])
                for id in range(32):
                    plc = pmac.hardwareState.getPlcProgramNoCreate(id)
                    row = page.tableRow(table)
                    page.tableColumn(row, '%s' % id)
                    if plc is not None:
                        page.href(page.tableColumn(row), '%s_plc_%s.htm' % (pmac.name, id), 'Code')
                    else:
                        page.tableColumn(row, '-')
                    page.href(page.tableColumn(row), '%s_plc%s_p.htm' % (pmac.name, id),
                        'P%d..%d' % (id*100, id*100+99))
                page.write()
                # Create the listing pages
                for id in range(32):
                    plc = pmac.hardwareState.getPlcProgramNoCreate(id)
                    if plc is not None:
                        page = WebPage('%s PLC%s' % (pmac.name, id), 
                            '%s/%s_plc_%s.htm' % (self.resultsDir, pmac.name, id),
                            styleSheet='analysis.css')
                        plc.html2(page, page.body())
                        page.write()
                # Create the P variable pages
                for id in range(32):
                    page = WebPage('P Variables for %s PLC %s' % (pmac.name, id), 
                        '%s/%s_plc%s_p.htm' % (self.resultsDir, pmac.name, id),
                        styleSheet='analysis.css')
                    table = page.table(page.body(), ['','0','1','2','3','4','5','6','7','8','9'])
                    row = None
                    for m in range(100):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, 'p%s' % (m+id*100))
                        var = pmac.hardwareState.getPVariable(m+id*100)
                        page.tableColumn(row, var.valStr())
                    page.write()
        # Dump the motion programs for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                # Create the motion program top level web page
                page = WebPage('Motion Programs for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_motionprogs.htm' % (self.resultsDir, pmac.name),
                    styleSheet='analysis.css')
                table = page.table(page.body())
                for id in range(256):
                    prog = pmac.hardwareState.getMotionProgramNoCreate(id)
                    if prog is not None:
                        row = page.tableRow(table)
                        page.tableColumn(row, 'prog%s' % id)
                        page.href(page.tableColumn(row), '%s_prog_%s.htm' % (pmac.name, id), 'Code')
                page.write()
                # Create the listing pages
                for id in range(256):
                    prog = pmac.hardwareState.getMotionProgramNoCreate(id)
                    if prog is not None:
                        page = WebPage('Motion Program %s for %s' % (id, pmac.name), 
                            '%s/%s_prog_%s.htm' % (self.resultsDir, pmac.name, id),
                            styleSheet='analysis.css')
                        prog.html2(page, page.body())
                        page.write()
        # Dump the coordinate systems for each pmac
        for name,pmac in self.pmacs.iteritems():
            if self.onlyPmac is None or self.onlyPmac == name:
                # Create the coordinate systems top level web page
                page = WebPage('Coordinate Systems for %s (%s)' % (pmac.name, datetime.datetime.today().strftime('%x %X')), 
                    '%s/%s_coordsystems.htm' % (self.resultsDir, pmac.name),
                    styleSheet='analysis.css')
                table = page.table(page.body(), 
                    ['CS', 'Axis def', 'Forward Kinematic', 'Inverse Kinematic', 'Q Variables', '%'])
                for id in range(1, 17):
                    row = page.tableRow(table)
                    page.tableColumn(row, '%s' % id)
                    col = page.tableColumn(row)
                    for m in range(1,33):
                        var = pmac.hardwareState.getCsAxisDefNoCreate(id, m)
                        if var is not None and not var.isZero():
                            page.text(col, '#%s->' % m)
                            var.html(page, col)
                    col = page.tableColumn(row)
                    var = pmac.hardwareState.getForwardKinematicProgramNoCreate(id)
                    if var is not None:
                        var.html(page, col)
                    col = page.tableColumn(row)
                    var = pmac.hardwareState.getInverseKinematicProgramNoCreate(id)
                    if var is not None:
                        var.html(page, col)
                    page.href(page.tableColumn(row), '%s_cs%s_q.htm' % (pmac.name, id),
                        'Q Variables')
                    col = page.tableColumn(row)
                    var = pmac.hardwareState.getFeedrateOverrideNoCreate(id)
                    if var is not None:
                        var.html(page, col)
                page.write()
                for id in range(1,17):
                    page = WebPage('Q Variables for %s CS %s' % (pmac.name, id), 
                        '%s/%s_cs%s_q.htm' % (self.resultsDir, pmac.name, id),
                        styleSheet='analysis.css')
                    table = page.table(page.body(), ['','0','1','2','3','4','5','6','7','8','9'])
                    row = None
                    for m in range(100):
                        if m % 10 == 0:
                            row = page.tableRow(table)
                            page.tableColumn(row, 'q%s' % m)
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
        xmlDoc = getDOMImplementation().createDocument(None, "testsuite", None)
        xmlTop = xmlDoc.documentElement
        xmlTop.setAttribute("tests", str(len(self.pmacs)))
        xmlTop.setAttribute("time", "0")
        xmlTop.setAttribute("timestamp", "0")
        for name,pmac in self.pmacs.iteritems():
            element = xmlDoc.createElement("testcase")
            xmlTop.appendChild(element)
            element.setAttribute("classname", "pmac")
            element.setAttribute("name", name)
            element.setAttribute("time", "0")
            if not pmac.compareResult:
                errorElement = xmlDoc.createElement("error")
                element.appendChild(errorElement)
                errorElement.setAttribute("message", "Compare mismatch")
                textNode = xmlDoc.createTextNode("See file:///%s/index.htm for details" % self.resultsDir)
                errorElement.appendChild(textNode)
        wFile = open('%s/report.xml' % self.resultsDir, "w")
        xmlDoc.writexml(wFile, indent="", addindent="  ", newl="\n")

class WebPage(object):
    def __init__(self, title, fileName, styleSheet=None):
        '''Initialises a web page, creating all the necessary header stuff'''
        self.fileName = fileName
        self.doc = getDOMImplementation().createDocument(None, "html", None)
        self.topElement = self.doc.documentElement
        h = self.doc.createElement('head')
        self.topElement.appendChild(h)
        if styleSheet is not None:
            l = self.doc.createElement('link')
            h.appendChild(l)
            l.setAttribute('rel', 'stylesheet')
            l.setAttribute('type', 'text/css')
            l.setAttribute('href', styleSheet)
        t = self.doc.createElement('title')
        self.topElement.appendChild(t)
        t.appendChild(self.doc.createTextNode(str(title)))
        self.theBody = self.doc.createElement('body')
        self.topElement.appendChild(self.theBody)
        h = self.doc.createElement('h1')
        self.theBody.appendChild(h)
        h.appendChild(self.doc.createTextNode(str(title)))
    def body(self):
        return self.theBody
    def href(self, parent, tag, descr):
        '''Creates a hot link.'''
        a = self.doc.createElement('a')
        parent.appendChild(a)
        a.setAttribute('href', tag)
        a.appendChild(self.doc.createTextNode(descr))
    def lineBreak(self, parent):
        '''Creates a line break.'''
        parent.appendChild(self.doc.createElement('br'))
    def doc_node(self, text, desc):
        anode = self.doc.createElement('a') 
        anode.setAttribute('class','body_con')
        anode.setAttribute('title',desc)
        self.text(anode,text)
        return anode
    def text(self, parent, t):
        '''Creates text.'''
        parent.appendChild(self.doc.createTextNode(str(t)))
    def paragraph(self, parent, text=None, id=None):
        '''Creates a paragraph optionally containing text'''
        para = self.doc.createElement("p")
        if id is not None:
            para.setAttribute('id', id)
        if text is not None:
            para.appendChild(self.doc.createTextNode(str(text)))
        parent.appendChild(para)
        return para
    def write(self):
        '''Writes out the HTML file.'''
        wFile = open(self.fileName, "w+")
        self.doc.writexml(wFile, indent="", addindent="", newl="")
    def table(self, parent, colHeadings=None, id=None):
        '''Returns a table with optional column headings.'''
        table = self.doc.createElement("table")
        if id is not None:
            table.setAttribute('id', id)
        parent.appendChild(table)
        if colHeadings is not None:
            row = self.doc.createElement("tr")
            if id is not None:
                row.setAttribute('id', id)
            table.appendChild(row)
            for colHeading in colHeadings:
                col = self.doc.createElement("th")
                if id is not None:
                    col.setAttribute('id', id)
                row.appendChild(col)
                col.appendChild(self.doc.createTextNode(str(colHeading)))
        return table
    def tableRow(self, table, columns=None, id=None):
        '''Returns a table row, optionally with columns already created.'''
        row = self.doc.createElement("tr")
        if id is not None:
            row.setAttribute('id', id)
        table.appendChild(row)
        if columns is not None:
            for column in columns:
                col = self.doc.createElement("td")
                if id is not None:
                    col.setAttribute('id', id)
                row.appendChild(col)
                col.appendChild(self.doc.createTextNode(str(column)))
        return row
    def tableColumn(self, tableRow, text=None, id=None):
        '''Returns a table column, optionally containing the text.'''
        col = self.doc.createElement("td")
        if id is not None:
            col.setAttribute('id', id)
        tableRow.appendChild(col)
        if text is not None:
            if hasattr(text, "appendChild"):
                # this is a node
                col.appendChild(text)
            else:
                col.appendChild(self.doc.createTextNode(str(text)))
        return col
    def emphasize(self, parent, text=None):
        '''Returns an emphasis object, optionally containing the text.'''
        result = self.doc.createElement('em')
        parent.appendChild(result)
        if text is not None:
            result.appendChild(self.doc.createTextNode(str(text)))
        return result

class PmacVariable(object):
    spaces = '                        '
    def __init__(self, prefix, n, v):
        self.typeStr = '%s%s' % (prefix, n)
        self.n = n
        self.v = v
        self.ro = False
    def addr(self):
        return self.typeStr
    def set(self,v):
        self.v = v
    def compare(self, other):
        if self.ro or other.ro:
            return True
        elif tokenIsFloat(self.v) and tokenIsFloat(other.v):
            a = tokenToFloat(self.v)
            b = tokenToFloat(other.v)
            return (a >= b-0.00001) and (a <= b+0.00001)
        else:
            return self.v == other.v
    def valStr(self):
        if isinstance(self.v, float):
            result = ('%.12f' % self.v).rstrip('0')
            if result.endswith('.'):
                result += '0'
        else:
            result = '%s' % self.v
        return result
    def getFloatValue(self):
        return float(self.v)
    def html(self, page, parent):
        page.text(parent, self.valStr())
    def isEmpty(self):
        return False
    def htmlCompare(self, page, parent, other):
        return self.html(page, parent)

class PmacIVariable(PmacVariable):
    useHexAxis = [2, 3, 4, 5, 10, 24, 25, 42, 43, 44, 55, 81, 82, 83, 84, 91, 95]
    useHexGlobal = range(8000, 8192)
    axisVarMin = 100
    axisVarMax = 3299
    varsPerAxis = 100
    def __init__(self, n, v=0, ro=False):
        PmacVariable.__init__(self, 'i', n, v)
        self.ro = ro
    def dump(self, typ=0, comment=""):
        result = ''
        if typ == 1:
            result = '%s' % self.valStr()
        else:
            if self.ro:
                result += ';'
            result += 'i%s=%s' % (self.n, self.valStr())
            if len(comment) == 0:
                result += '\n'
            else:
                if len(result) < len(self.spaces):
                    result += self.spaces[len(result):]
                result += ';%s\n' % comment
        return result
    def copyFrom(self):
        result = PmacIVariable(self.n)
        result.v = self.v
        result.ro = self.ro
        return result
    def valStr(self):
        if isinstance(self.v, float):
            result = ('%.12f' % self.v).rstrip('0')
            if result.endswith('.'):
                result += '0'
        else:
            useHex = False
            if self.n >= self.axisVarMin and self.n <= self.axisVarMax:
                useHex = (self.n % self.varsPerAxis) in self.useHexAxis
            else:
                useHex = self.n in self.useHexGlobal
            if useHex:
                result = '$%x' % self.v
            else: 
                result = '%s' % self.v
        return result

class PmacMVariable(PmacVariable):
    def __init__(self, n, type='*', address=0, offset=0, width=0, format='U'):
        PmacVariable.__init__(self, 'm', n, 0)
        self.set(type, address, offset, width, format)
    def dump(self, typ=0):
        if typ == 1:
            result = '%s' % self.valStr()
        else:
            result = 'm%s->%s\n' % (self.n, self.valStr())
        return result
    def valStr(self):
        result = ''
        if self.type == '*':
            result += '*'
        elif self.type in ['X', 'Y']:
            result += '%s:$%x' % (self.type, self.address)
            if self.width == 24:
                result += ',24'
                if not self.format == 'U':
                    result += ',%s' % self.format 
            else:
                result += ',%s' % self.offset
                if not self.width == 1 or not self.format == 'U':
                    result += ',%s' % self.width
                    if not self.format == 'U':
                        result += ',%s' % self.format
        elif self.type in ['D','DP','F','L']:
            result += '%s:$%x' % (self.type, self.address)
        else:
            raise GeneralError('Unsupported')
        return result
    def contentsStr(self):
        return PmacVariable.valStr(self)
    def set(self, type, address, offset, width, format):
        self.type = type
        self.address = address
        self.offset = offset
        self.width = width
        self.format = format
    def setValue(self, v):
        self.v = v
    def copyFrom(self):
        result = PmacMVariable(self.n)
        result.v = self.v
        result.ro = self.ro
        result.type = self.type
        result.address = self.address
        result.offset = self.offset
        result.width = self.width
        result.format = self.format
        return result
    def compare(self, other):
        if self.ro or other.ro:
            return True
        else:
            return self.type == other.type and self.address == other.address and \
                self.offset == other.offset and self.width == other.width and \
                self.format == other.format

class PmacPVariable(PmacVariable):
    def __init__(self, n, v=0):
        PmacVariable.__init__(self, 'p', n, v)
    def dump(self, typ=0):
        if typ == 1:
            result = '%s' % self.valStr()
        else:
            result = 'p%s=%s\n' % (self.n, self.valStr())
        return result
    def copyFrom(self):
        result = PmacPVariable(self.n)
        result.v = self.v
        result.ro = self.ro
        return result

class PmacQVariable(PmacVariable):
    def __init__(self, cs, n, v=0):
        PmacVariable.__init__(self, '&%sq'%cs, n, v)
        self.cs = cs
    def dump(self, typ=0):
        if typ == 1:
            result = '%s' % self.valStr()
        else:
            result = '&%sq%s=%s\n' % (self.cs, self.n, self.valStr())
        return result
    def copyFrom(self):
        result = PmacQVariable(self.cs, self.n)
        result.v = self.v
        result.ro = self.ro
        return result

class PmacFeedrateOverride(PmacVariable):
    def __init__(self, cs, v=0):
        PmacVariable.__init__(self, '&%s%%'%cs, 0, v)
        self.cs = cs
    def dump(self, typ=0):
        if typ == 1:
            result = '%s' % self.valStr()
        else:
            result = '&%s%%%s\n' % (self.cs, self.valStr())
        return result
    def copyFrom(self):
        result = PmacFeedrateOverride(self.cs)
        result.v = self.v
        result.ro = self.ro
        return result

class PmacMsIVariable(PmacVariable):
    def __init__(self, ms, n, v='', ro=False):
        PmacVariable.__init__(self, 'ms%si'%ms, n, v)
        self.ms = ms
        self.ro = ro
    def dump(self, typ=0):
        if typ == 1:
            result = '%s' % self.valStr()
        else:
            result = ''
            if self.ro:
                result += ';'
            result += 'ms%s,i%s=%s\n' % (self.ms, self.n, self.valStr())
        return result
    def copyFrom(self):
        result = PmacMsIVariable(self.ms, self.n)
        result.v = self.v
        result.ro = self.ro
        return result

def isNumber(t):
    if len(str(t)) == 0:
        result = False
    elif t == '$':
        result = False
    elif str(t)[0] == '$':
        result = True
        for ch in str(t)[1:]:
            if ch not in '0123456789ABCDEF':
                result = False
    elif str(t)[0].isdigit():
        result = True
        for ch in str(t)[1:]:
            if ch not in '0123456789.':
                result = False
    else:
        result = False
    return result

def toNumber(t):
    if len(str(t)) == 0:
        result = 0
    elif str(t)[0] == '$':
        result = int(str(t)[1:], 16)
    elif str(t)[0].isdigit():
        if str(t).find('.') >= 0:
            result = float(str(t))
        else:
            result = int(str(t))
    else:
        result = 0
    return result

def isString(t):
    return len(t)>=2 and t[0]=='"' and t[-1]=='"'

def stripStringQuotes(t):
    return t.strip('"')

def compareFloats(a, b, delta):
    return a >= (b-delta) and a <= (b+delta)


class PmacProgram(PmacVariable):
    def __init__(self, prefix, n, v, lines=None,offsets=None):
        PmacVariable.__init__(self, prefix, n, v)
        self.offsets = offsets
        self.lines = lines
    def add(self, t):
        if not isinstance(t, PmacToken):
            print 'PmacProgram: %s is not a token' % repr(t)
        self.v.append(t)
    def clear(self):
        self.v = []
    def valueText(self, typ=0):
        result = ''
        for t in self.v:
            if t == '\n':
                if len(result) > 0 and not result[-1] == '\n':
                    result += str(t)
            else:
                if len(result) == 0:
                    pass
                elif result[-1].isalpha() and str(t)[0].isalpha():
                    result += ' '
                elif result[-1].isdigit() and str(t)[0].isdigit():
                    result += ' '
                result += str(t)
                if typ==1 and len(result.rsplit('\n',1)[-1]) > 60:
                    result += '\n'
        if len(result) == 0 or result[-1] != '\n':
            result += '\n'
        return result
    def compare(self, other):
        # Strip the newline tokens from the two lists.  There's
        # probably a better way of doing this.
        a = []
        for i in self.v:
            if i == '\n':
                pass
            else:
                a.append(i)
        b = []
        for i in other.v:
            if i == '\n':
                pass
            else:
                b.append(i)
        # Now compare them token by token
        result = True
        while len(a)>0 and len(b)>0:
            # Extract the current head token from each list
            a0 = a[0]
            b0 = b[0]
            a[0:1] = []
            b[0:1] = []
            # Compare them
            if isNumber(a0) and isNumber(b0):
                if not compareFloats(toNumber(a0), toNumber(b0), 0.00001):
                    result = False
                    a0.compareFail = True
                    b0.compareFail = True
            elif a0 == 'COMMAND' and b0 == 'COMMAND' and len(a)>0 and len(b)>0:
                # Get the command strings
                a0 = a[0]
                b0 = b[0]
                a[0:1] = []
                b[0:1] = []
                if isString(str(a0)) and isString(str(b0)):
                    # Parse them
                    parserA = PmacParser([stripStringQuotes(str(a0))], self)
                    varA = PmacCommandString(parserA.tokens())
                    parserB = PmacParser([stripStringQuotes(str(b0))], self)
                    varB = PmacCommandString(parserB.tokens())
                    if not varA.compare(varB):
                        result = False
                        a0.compareFail = True
                        b0.compareFail = True
                else:
                    if a0 != b0:
                        result = False
                        a0.compareFail = True
                        b0.compareFail = True
            else:
                if a0 != b0:
                    result = False
                    a0.compareFail = True
                    b0.compareFail = True
        for a0 in a:
            a0.compareFail = True
            result = False
        for b0 in b:
            b0.compareFail = True
            result = False
        return result
    def html(self, page, parent):
        lines = self.valueText(typ=1).split()
        for line in lines:
            page.text(parent, line)
            page.lineBreak(parent)
    def html2(self, page, parent):
        text = ''
        for i in range(len(self.lines)):
            text += '%s:\t%s\n' % (self.offsets[i], self.lines[i])
        page.paragraph(parent, text, id='code')
    def isEmpty(self):
        a = []
        for i in self.v:
            if i == '\n':
                pass
            else:
                a.append(i)
        return len(a) == 0 or a == ['RETURN']
    def htmlCompare(self, page, parent, other):
        lineLen = 0
        for t in self.v:
            if t == '\n':
                if lineLen > 0:
                    page.lineBreak(parent)
                    lineLen = 0
            else:
                if t.compareFail:
                    page.text(page.emphasize(parent), t)
                else:
                    page.text(parent, t)
                lineLen += len(t)
                if lineLen > 60:
                    page.lineBreak(parent)
                    lineLen = 0

class PmacCommandString(PmacProgram):
    def __init__(self, v):
        PmacProgram.__init__(self, 'CMD', 0, v)

class PmacCsAxisDef(PmacProgram):
    def __init__(self, cs, n, v=[PmacToken('0')]):
        PmacProgram.__init__(self, '&%s#'%cs, n, v)
        self.cs = cs
    def dump(self, typ=0):
        if typ == 1:
            result = '%s' % self.valueText()
        else:
            result = '&%s#%s->%s' % (self.cs, self.n, self.valueText())
        return result
    def isZero(self):
        result = True
        for t in self.v:
            if t == '0' or t == '0.0' or t == '\n':
                pass
            else:
                result = False
        return result
    def copyFrom(self):
        result = PmacCsAxisDef(self.cs, self.n)
        result.v = self.v
        result.ro = self.ro
        result.offsets = self.offsets
        result.lines = self.lines
        return result

class PmacForwardKinematicProgram(PmacProgram):
    def __init__(self, n, v=[]):
        PmacProgram.__init__(self, 'fwd', n, v)
    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ''
            if len(self.v) > 0:
                result = '\n&%s open forward clear\n' % self.n
                result += self.valueText()
                result += 'close\n'
        return result
    def copyFrom(self):
        result = PmacForwardKinematicProgram(self.n)
        result.v = self.v
        result.ro = self.ro
        result.offsets = self.offsets
        result.lines = self.lines
        return result

class PmacInverseKinematicProgram(PmacProgram):
    def __init__(self, n, v=[]):
        PmacProgram.__init__(self, 'inv', n, v)
    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ''
            if len(self.v) > 0:
                result = '\n&%s open inverse clear\n' % self.n
                result += self.valueText()
                result += 'close\n'
        return result
    def copyFrom(self):
        result = PmacInverseKinematicProgram(self.n)
        result.v = self.v
        result.ro = self.ro
        result.offsets = self.offsets
        result.lines = self.lines
        return result

class PmacMotionProgram(PmacProgram):
    def __init__(self, n, v=[], lines=None, offsets=None):
        PmacProgram.__init__(self, 'prog', n, v, lines, offsets)
    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ''
            if len(self.v) > 0:
                result = '\nopen program %s clear\n' % self.n
                result += self.valueText()
                result += 'close\n'
        return result
    def copyFrom(self):
        result = PmacMotionProgram(self.n)
        result.v = self.v
        result.ro = self.ro
        result.offsets = self.offsets
        result.lines = self.lines
        return result

class PmacPlcProgram(PmacProgram):
    def __init__(self, n, v=[], lines=None, offsets=None):
        PmacProgram.__init__(self, 'plc', n, v, lines, offsets)
        self.isRunning = False
        self.shouldBeRunning = False
    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ''
            if len(self.v) > 0:
                result = '\nopen plc %s clear\n' % self.n
                result += self.valueText()
                result += 'close\n'
        return result
    def copyFrom(self):
        result = PmacPlcProgram(self.n)
        result.v = self.v
        result.ro = self.ro
        result.offsets = self.offsets
        result.lines = self.lines
        return result
    def setShouldBeRunning(self):
        '''Sets the shouldBeRunning flag if the PLC does not contain a disable statement for itself.'''
        self.shouldBeRunning = True
        state = "idle"
        for i in self.v:
            if state == "idle":
                if i == 'DISABLE':
                    state = "disable"
            elif state == "disable":
                if i == 'PLC':
                    state = "plc"
                else:
                    state = "idle"
            elif state == "plc":
                if tokenToInt(i) == self.n:
                    self.shouldBeRunning = False
                state = "idle"
    def setIsRunning(self, state):
        self.isRunning = state

class PmacState(object):
    '''Represents the internal state of a PMAC.'''
    globalIVariableDescriptions = {0:'Serial card number', 1:'Serial card mode',
        2:'Control panel port activation', 3:'I/O handshake control',
        4:'Communications integrity mode', 5:'PLC program control',
        6:'Error reporting mode', 7:'Phase cycle extension',
        8:'Real-time interrupt period', 9:'Full/abbreviated listing control',
        10:'Servo interrupt time', 11:'Programmed move calculation time',
        12:'Lookahead spline time', 13:'Foreground in-position check enable',
        14:'Temporary buffer save enable', 15:'Degree/radian control for user trig functions',
        16:'Rotary buffer request on point', 17:'Rotary buffer request off point',
        18:'Fixed buffer full warning point', 19:'Clock source I-variable number',
        20:'Macro IC 0 base address', 21:'Macro IC 1 base address',
        22:'Macro IC 2 base address', 23:'Macro IC 3 base address',
        24:'Main DPRAM base address', 25:'Reserved', 26:'Reserved', 27:'Reserved',
        28:'Reserved', 29:'Reserved', 30:'Compensation table wrap enable',
        31:'Reserved', 32:'Reserved', 33:'Reserved', 34:'Reserved', 35:'Reserved',
        36:'Reserved', 37:'Additional wait states', 38:'Reserved',
        39:'UBUS accessory ID variable display control', 40:'Watchdog timer reset value',
        41:'I-variable lockout control', 42:'Spline/PVT time control mode',
        43:'Auxiliary serial port parser disable', 44:'PMAC ladder program enable',
        45:'Foreground binary rotary buffer transfer enable',
        46:'P&Q-variable storage location', 
        47:'DPRAM motor data foreground reporting period',
        48:'DPRAM motor data foreground reporting enable',
        49:'DPRAM background data reporting enable', 50:'DPRAM background data reporting period',
        51:'Compensation table enable', 52:'CPU frequency control',
        53:'Auxiliary serial port baud rate control',
        54:'Serial port baud rate control',
        55:'DPRAM background variable buffers enable',
        56:'DPRAM ASCII communications interrupt enable',
        57:'DPRAM motor data background reporting enable',
        58:'DPRAM ASCII communications enable', 59:'Motor/CS group select',
        60:'Filtered velocity sample time', 61:'Filtered velocity shift',
        62:'Internal message carriage return control', 63:'Control-X echo enable',
        64:'Internal response tag enable', 65:'Reserved', 66:'Reserved', 67:'Reserved',
        68:'Coordinate system activation control', 69:'Reserved',
        70:'Macro IC 0 node auxiliary register enable', 71:'Macro IC 0 node protocol type control',
        72:'Macro IC 1 node auxiliary register enable', 73:'Macro IC 1 node protocol type control',
        74:'Macro IC 2 node auxiliary register enable', 75:'Macro IC 2 node protocol type control',
        76:'Macro IC 3 node auxiliary register enable', 77:'Macro IC 3 node protocol type control',
        78:'Macro type 1 master/slave communications timeout',
        79:'Macro type 1 master/master communications timeout',
        80:'Macro ring check period', 81:'Macro maximum ring error count',
        82:'Macro minimum sync packet count', 83:'Macro parallel ring enable mask',
        84:'Macro IC# for master communications', 85:'Macro ring order number',
        86:'Reserved', 87:'Reserved', 88:'Reserved', 89:'Reserved',
        90:'VME address modifier', 91:'VME address modifier don\'t care bits',
        92:'VME base address bits A31-A24',
        93:'VME mailbox base address bits A23-A16 ISA DPRAM base address bits A23-A16',
        94:'VME mailbox base address bits A15-A08 ISA DPRAM base address bits A15-A14 & control',
        95:'VME interrupt level', 96:'VME interrupt vector', 
        97:'VME DPRAM base address bits A23-A20', 98:'VME DPRAM enable',
        99:'VME address width control'}
    motorIVariableDescriptions = {0:'Activation control', 1:'Commutation enable', 
        2:'Command output address', 3:'Position loop feedback address', 
        4:'Velocity loop feedback address', 5:'Master position address',
        6:'Position following enable and mode', 7:'Master (handwheel) scale factor',
        8:'Position scale factor', 9:'Velocity-loop scale factor',
        10:'Power-on servo position address', 11:'Fatal following error limit',
        12:'Warning following error limit', 13:'Positive software position limit',
        14:'Negative software position limit', 15:'Abort/limit deceleration rate',
        16:'Maximum program velocity', 17:'Maximum program acceleration',
        18:'Reserved', 19:'Maximum jog/home acceleration', 
        20:'Jog/home acceleration time', 21:'Jog/home S-curve time',
        22:'Jog speed', 23:'Home speed and direction', 24:'Flag mode control',
        25:'Flag address', 26:'Home offset', 27:'Position rollover range',
        28:'In-position band', 29:'Output/first phase offset',
        30:'PID proportional gain', 31:'PID derivative gain',
        32:'PID velocity feedforward gain', 33:'PID integral gain',
        34:'PID integration mode', 35:'PID acceleration feedforward gain',
        36:'PID notch filter coefficient N1', 37:'PID notch filter coefficient N2',
        38:'PID notch filter coefficient D1', 39:'PID notch filter coefficient D2',
        40:'Net desired position filter gain', 41:'Desired position limit band',
        42:'Amplifier flag address', 43:'Overtravel-limit flag address',
        44:'Reserved', 45:'Reserved', 46:'Reserved', 47:'Reserved', 48:'Reserved',
        49:'Reserved', 50:'Reserved', 51:'Reserved', 52:'Reserved', 53:'Reserved',
        54:'Reserved', 55:'Commutation table address offset',
        56:'Commutation table delay compensation', 57:'Continuous current limit',
        58:'Integrated current limit', 59:'User-written servo/phase enable',
        60:'Servo cycle period extension period', 61:'Current-loop integral gain',
        62:'Current-loop forward-path proportional gain', 63:'Integration limit',
        64:'Deadband gain factor', 65:'Deadband size', 66:'PWM scale factor',
        67:'Position error limit', 68:'Friction feedforward', 
        69:'Output command limit', 70:'Number of commutation cycles (N)',
        71:'Counts per N commutation cycles', 72:'Commuation phase angle',
        73:'Phase finding output value', 74:'Phase finding time',
        75:'Phase position offset', 76:'Current-loop back-path proportional gain',
        77:'Magnetization current', 78:'Slip gain', 79:'Second phase offset',
        80:'Power-up mode', 81:'Power-on phase position address', 
        82:'Current-loop feedback address', 83:'Commutation position address',
        84:'Current-loop feedback mask word', 85:'Backlash take-up rate',
        86:'Backlash size', 87:'Backlash hysteresis', 88:'In-position number of scans',
        89:'Reserved', 90:'Rapid mode speed select', 91:'Power-on phase position format',
        92:'Jog move calculation time', 93:'Reserved', 94:'Reserved',
        95:'Power-on servo position format', 96:'Command output mode control',
        97:'Position capture & trigger mode', 98:'Third resolver gear ratio',
        99:'Second resolver gear ratio'}
    globalMsIVariableDescriptions = {0:'Software firmware version',
        2:'Station ID and user configutation word', 3:'Station rotary switch setting',
        6:'Maximum permitted ring errors in one second', 8:'Macro ring check period',
        9:'Macro ring error shutdown count', 10:'Macro ring sync packet shutdown dount',
        11:'Station order number', 14:'Macro IC source of phase clock',
        15:'Enable macro PLCC', 16:'Encoder fault reporting control',
        17:'Amplifier fault disable control', 18:'Amplifier fault polarity',
        19:'I/O data transfer period', 20:'Data transfer enable mask',
        21:'Data transfer source and destination address',22:'Data transfer source and destination address',
        23:'Data transfer source and destination address',24:'Data transfer source and destination address',
        25:'Data transfer source and destination address',26:'Data transfer source and destination address',
        27:'Data transfer source and destination address',28:'Data transfer source and destination address',
        29:'Data transfer source and destination address',30:'Data transfer source and destination address',
        31:'Data transfer source and destination address',32:'Data transfer source and destination address',
        33:'Data transfer source and destination address',34:'Data transfer source and destination address',
        35:'Data transfer source and destination address',36:'Data transfer source and destination address',
        37:'Data transfer source and destination address',38:'Data transfer source and destination address',
        39:'Data transfer source and destination address',40:'Data transfer source and destination address',
        41:'Data transfer source and destination address',42:'Data transfer source and destination address',
        43:'Data transfer source and destination address',44:'Data transfer source and destination address',
        45:'Data transfer source and destination address',46:'Data transfer source and destination address',
        47:'Data transfer source and destination address',48:'Data transfer source and destination address',
        49:'Data transfer source and destination address',50:'Data transfer source and destination address',
        51:'Data transfer source and destination address',52:'Data transfer source and destination address',
        53:'Data transfer source and destination address',54:'Data transfer source and destination address',
        55:'Data transfer source and destination address',56:'Data transfer source and destination address',
        57:'Data transfer source and destination address',58:'Data transfer source and destination address',
        59:'Data transfer source and destination address',60:'Data transfer source and destination address',
        61:'Data transfer source and destination address',62:'Data transfer source and destination address',
        63:'Data transfer source and destination address',64:'Data transfer source and destination address',
        65:'Data transfer source and destination address',66:'Data transfer source and destination address',
        67:'Data transfer source and destination address',68:'Data transfer source and destination address',
        69:'I/O board 16 bit transfer control',70:'I/O board 16 bit transfer control',
        71:'I/O board 24 bit transfer control',72:'Output power-on/shutdown state',
        73:'Output power-on/shutdown state',74:'Output power-on/shutdown state',
        75:'Output power-on/shutdown state',76:'Output power-on/shutdown state',
        77:'Output power-on/shutdown state',78:'Output power-on/shutdown state',
        79:'Output power-on/shutdown state',80:'Output power-on/shutdown state',
        81:'Output power-on/shutdown state',82:'Output power-on/shutdown state',
        83:'Output power-on/shutdown state',84:'Output power-on/shutdown state',
        85:'Output power-on/shutdown state',86:'Output power-on/shutdown state',
        87:'Output power-on/shutdown state',88:'Output power-on/shutdown state',
        89:'Output power-on/shutdown state',90:'Y:MTR servo channel disanle and MI996 enable',
        91:'Phase interrupt 24 bit data copy',92:'Phase interrupt 24 bit data copy',
        93:'Phase interrupt 24 bit data copy',94:'Phase interrupt 24 bit data copy',
        95:'Phase interrupt 24 bit data copy',96:'Phase interrupt 24 bit data copy',
        97:'Phase interrupt 24 bit data copy',98:'Phase interrupt 24 bit data copy',
        99:'Reserved', 101:'Ongoing position source address',102:'Ongoing position source address',
        103:'Ongoing position source address',104:'Ongoing position source address',
        105:'Ongoing position source address',106:'Ongoing position source address',
        107:'Ongoing position source address',108:'Ongoing position source address',
        111:'Power-up position source address',112:'Power-up position source address',
        113:'Power-up position source address',114:'Power-up position source address',
        115:'Power-up position source address',116:'Power-up position source address',
        117:'Power-up position source address',118:'Power-up position source address',
        120:'Encoder conversion table entries',121:'Encoder conversion table entries',
        122:'Encoder conversion table entries',123:'Encoder conversion table entries',
        124:'Encoder conversion table entries',125:'Encoder conversion table entries',
        126:'Encoder conversion table entries',127:'Encoder conversion table entries',
        128:'Encoder conversion table entries',129:'Encoder conversion table entries',
        130:'Encoder conversion table entries',131:'Encoder conversion table entries',
        132:'Encoder conversion table entries',133:'Encoder conversion table entries',
        134:'Encoder conversion table entries',135:'Encoder conversion table entries',
        136:'Encoder conversion table entries',137:'Encoder conversion table entries',
        138:'Encoder conversion table entries',139:'Encoder conversion table entries',
        140:'Encoder conversion table entries',141:'Encoder conversion table entries',
        142:'Encoder conversion table entries',143:'Encoder conversion table entries',
        144:'Encoder conversion table entries',145:'Encoder conversion table entries',
        146:'Encoder conversion table entries',147:'Encoder conversion table entries',
        148:'Encoder conversion table entries',149:'Encoder conversion table entries',
        150:'Encoder conversion table entries',151:'Encoder conversion table entries',
        152:'Phase-clock latched I/O',153:'Phase-clock latched I/O',
        161:'MLDT frequency control',162:'MLDT frequency control',163:'MLDT frequency control',
        164:'MLDT frequency control',165:'MLDT frequency control',166:'MLDT frequency control',
        167:'MLDT frequency control',168:'MLDT frequency control',
        169:'I/O board 72 bit transfer control',170:'I/O board 72 bit transfer control',
        171:'I/O board 144 bit transfer control',172:'I/O board 144 bit transfer control',
        173:'I/O board 144 bit transfer control',
        174:'12 bit A/D transfer',175:'12 bit A/D transfer',176:'Macro IC base address',
        177:'Macro IC address for node 14', 178:'Macro IC address for node 15',
        179:'Macro/servo IC #1 base address',180:'Macro/servo IC #2 base address',
        181:'Macro/servo channels 1-8 address',182:'Macro/servo channels 1-8 address',
        183:'Macro/servo channels 1-8 address',184:'Macro/servo channels 1-8 address',
        185:'Macro/servo channels 1-8 address',186:'Macro/servo channels 1-8 address',
        187:'Macro/servo channels 1-8 address',188:'Macro/servo channels 1-8 address',
        189:'Macro/encoder IC #3 base address',190:'Macro/encoder IC #4 base address',
        191:'Encoder channels 9-14 base address',192:'Encoder channels 9-14 base address',
        193:'Encoder channels 9-14 base address',194:'Encoder channels 9-14 base address',
        195:'Encoder channels 9-14 base address',196:'Encoder channels 9-14 base address',
        198:'Direct read/write format and address',199:'Direct read/write variable',
        200:'Macro/servo ICs detected and saved',203:'Phase period',204:'Phase execution time',
        205:'Background cycle time',206:'Maximum background cycle time',207:'Identification break down',
        208:'User RAM start',
        210:'Servo IC identification variables',211:'Servo IC identification variables',
        212:'Servo IC identification variables',213:'Servo IC identification variables',
        214:'Servo IC identification variables',215:'Servo IC identification variables',
        216:'Servo IC identification variables',217:'Servo IC identification variables',
        218:'Servo IC identification variables',219:'Servo IC identification variables',
        220:'Servo IC identification variables',221:'Servo IC identification variables',
        222:'Servo IC identification variables',223:'Servo IC identification variables',
        224:'Servo IC identification variables',225:'Servo IC identification variables',
        250:'I/O card identification variables',251:'I/O card identification variables',
        252:'I/O card identification variables',253:'I/O card identification variables',
        254:'I/O card identification variables',255:'I/O card identification variables',
        256:'I/O card identification variables',257:'I/O card identification variables',
        258:'I/O card identification variables',259:'I/O card identification variables',
        260:'I/O card identification variables',261:'I/O card identification variables',
        262:'I/O card identification variables',263:'I/O card identification variables',
        264:'I/O card identification variables',265:'I/O card identification variables',
        900:'PWM 1-4 frequency control',903:'Hardware clock control channels 1-4',
        904:'PWM 1-4 deadtime / PFM 1-4 pluse width control',905:'DAC 1-4 strobe word',
        906:'PWM 5-8 frequency control',907:'Hardware clock control channels 5-8',
        908:'PWM 5-8 deadtime / PFM 5-8 pulse width control',909:'DAC 5-8 strobe word',
        940:'ADC 1-4 strobe word', 941:'ADC 5-8 strobe word',
        942:'ADC strobe word channel 1* & 2*',943:'Phase and servo direction',
        975:'Macro IC 0 I/O node enable', 976:'Macro IC 0 motor node disable',
        977:'Motor nodes reporting ring break',987:'A/D input enable',
        988:'A/D unipolar/bipolar control',989:'A/D source address',
        992:'Max phase frequence control', 993:'Hardware clock control handwheel channels',
        994:'PWM deadtime / PFM pulse width control for handwheel',
        995:'Macro ring configuration/status',996:'Macro node activate control',
        997:'Phase clock frequency control',998:'Servo clock frequency control',
        999:'Handwheel DAC strobe word'}
    motorMsIVariableDescriptions = {910:'Encoder/timer decode control', 
        911:'Position compare channel select', 912:'Encoder capture control',
        913:'Capture flag select control', 914:'Encoder gated index select',
        915:'Encoder index gate state', 916:'Output mode select',
        917:'Output invert control', 918:'Output PFM direction signal invert control',
        921:'Flag capture position',
        922:'ADC A input value', 923:'Compare auto-increment value', 924:'ADC B input value',
        925:'Compare A position value', 926:'Compare B position value',
        927:'Encoder loss status bit', 928:'Compare-state write enable',
        929:'Compare-output initial state', 930:'Absolute power-on position',
        938:'Servo IC status word', 939:'Servo IC control word'}
    motorI7000VariableDescriptions = {0:'Encoder/timer decode control',
        1:'Position compare channel select', 2:'Encoder capture control',
        3:'Capture flag select control', 4:'Encoder gated index select',
        5:'Encoder index gate state', 6:'Output mode select',
        7:'Output invert control', 8:'Output PFM direction signal invert control',
        9:'Hardware 1/T control'}
    axisToNode = {1:0, 2:1, 3:4, 4:5, 5:8, 6:9, 7:12, 8:13,
        9:16, 10:17, 11:20, 12:21, 13:24, 14:25, 15:28, 16:29,
        17:32, 18:33, 19:36, 20:37, 21:40, 22:41, 23:44, 24:45,
        25:48, 26:49, 27:52, 28:53, 29:56, 30:57, 31:60, 32:61}
    axisToMn = {1:10, 2:20, 3:30, 4:40, 5:110, 6:120, 7:130, 8:140,
                9:210, 10:220, 11:230, 12:240, 13:310, 14:320, 15:330, 16:340}
    def __init__(self, descr):
        self.vars = {}
        self.descr = descr
        self.inlineExpressionResolutionState = None
    def setInlineExpressionResolutionState(self, state):
        self.inlineExpressionResolutionState = state
    def getInlineExpressionIValue(self, n):
        return self.inlineExpressionResolutionState.getIVariable(n).getFloatValue()
    def getInlineExpressionPValue(self, n):
        return self.inlineExpressionResolutionState.getPVariable(n).getFloatValue()
    def getInlineExpressionQValue(self, n):
        return self.inlineExpressionResolutionState.getQVariable(n).getFloatValue()
    def getInlineExpressionMValue(self, n):
        return self.inlineExpressionResolutionState.getMVariable(n).getFloatValue()
    def addVar(self, var):
        self.vars[var.addr()] = var
    def removeVar(self, var):
        if var.addr() in self.vars:
            del self.vars[var.addr()]
    def copyFrom(self, other):
        for k,v in other.vars.iteritems():
            self.vars[k] = v.copyFrom()
    def getVar(self, t, n):
        addr = '%s%s' % (t,n)
        if addr in self.vars:
            result = self.vars[addr]
        else:
            if t == 'prog':
                result = PmacMotionProgram(n)
            elif t == 'plc':
                result = PmacPlcProgram(n)
            elif t == 'fwd':
                result = PmacForwardKinematicProgram(n)
            elif t == 'inv':
                result = PmacInverseKinematicProgram(n)
            elif t == 'p':
                result = PmacPVariable(n)
            elif t == 'i':
                result = PmacIVariable(n)
            elif t == 'm':
                result = PmacMVariable(n)
            else:
                raise GeneralError('Illegal program type: %s' % t)
            self.vars[addr] = result
        return result
    def getVar2(self, t1, n1, t2, n2):
        addr = '%s%s%s%s' % (t1,n1,t2,n2)
        if addr in self.vars:
            result = self.vars[addr]
        else:
            if t2 == 'q':
                result = PmacQVariable(n1, n2)
            elif t2 == 'i':
                result = PmacMsIVariable(n1, n2)
            elif t2 == '#':
                result = PmacCsAxisDef(n1, n2)
            elif t2 == '%':
                result = PmacFeedrateOverride(n1)
            else:
                raise GeneralError('Illegal program type: %sx%s' % (t1, t2))
            self.vars[addr] = result
        return result
    def getVarNoCreate(self, t, n):
        addr = '%s%s' % (t,n)
        result = None
        if addr in self.vars:
            result = self.vars[addr]
        return result
    def getVarNoCreate2(self, t1, n1, t2, n2):
        addr = '%s%s%s%s' % (t1,n1,t2,n2)
        result = None
        if addr in self.vars:
            result = self.vars[addr]
        return result
    def getMotionProgram(self, n):
        return self.getVar('prog', n)
    def getMotionProgramNoCreate(self, n):
        return self.getVarNoCreate('prog', n)
    def getPlcProgram(self, n):
        return self.getVar('plc', n)
    def getPlcProgramNoCreate(self, n):
        return self.getVarNoCreate('plc', n)
    def getForwardKinematicProgram(self, n):
        return self.getVar('fwd', n)
    def getInverseKinematicProgram(self, n):
        return self.getVar('inv', n)
    def getForwardKinematicProgramNoCreate(self, n):
        return self.getVarNoCreate('fwd', n)
    def getInverseKinematicProgramNoCreate(self, n):
        return self.getVarNoCreate('inv', n)
    def getPVariable(self,n):
        return self.getVar('p', n)
    def getIVariable(self,n):
        return self.getVar('i', n)
    def getMVariable(self,n):
        return self.getVar('m', n)
    def getQVariable(self,cs,n):
        return self.getVar2('&', cs, 'q', n)
    def getFeedrateOverride(self,cs):
        return self.getVar2('&', cs, '%', 0)
    def getFeedrateOverrideNoCreate(self,cs):
        return self.getVarNoCreate2('&', cs, '%', 0)
    def getMsIVariable(self,ms,n):
        return self.getVar2('ms', ms, 'i', n)
    def getCsAxisDef(self,cs,m):
        return self.getVar2('&', cs, '#', m)
    def getCsAxisDefNoCreate(self,cs,m):
        return self.getVarNoCreate2('&', cs, '#', m)
    def dump(self):
        result = ''
        for a,v in self.vars.iteritems():
            result += v.dump()
        return result
    def htmlGlobalIVariables(self, page):
        table = page.table(page.body(), ["I-Variable", "Value", "Description"])
        for i in range(0, 100):
            page.tableRow(table, 
                ['i%s' % i, 
                '%s' % self.getIVariable(i).valStr(),
                '%s' % PmacState.globalIVariableDescriptions[i]])
    def htmlMotorIVariables(self, motor, page, geobrick):
        table = page.table(page.body(), ["I-Variable", "Value", "Description"])
        for n in range(0, 100):
            i = motor*100 + n
            page.tableRow(table, 
                ['i%s' % i,
                '%s' % self.getIVariable(i).valStr(),
                '%s' % PmacState.motorIVariableDescriptions[n]])
        if geobrick:
            for n in range(10):
                i = 7000 + PmacState.axisToMn[motor] + n
                page.tableRow(table, 
                    ['i%s' % i,
                    '%s' % self.getIVariable(i).valStr(),
                    '%s' % PmacState.motorI7000VariableDescriptions[n]])
    def htmlGlobalMsIVariables(self, page):
        table = page.table(page.body(), ["MS I-Variable", "Node", "Value", "Description"])
        for i,description in PmacState.globalMsIVariableDescriptions.iteritems():
            for node in [0,16,32,64]:
                page.tableRow(table, 
                    ['i%s' % i, '%s' % node,
                    '%s' % self.getMsIVariable(0,i).valStr(),
                    '%s' % description])
    def htmlMotorMsIVariables(self, motor, page):
        table = page.table(page.body(), ["MS I-Variable", "Value", "Description"])
        node = PmacState.axisToNode[motor]
        for i,description in PmacState.motorMsIVariableDescriptions.iteritems():
            page.tableRow(table, 
                ['i%s' % i,
                '%s' % self.getMsIVariable(node, i).valStr(),
                '%s' % description])
    def compare(self, other, noCompare, pmacName, page, fixfile):
        '''Compares the state of this PMAC with the other.'''
        result = True
        table = page.table(page.body(), ["Element", "Reason", "Reference", "Hardware"])
        # Build the list of variable addresses to test
        addrs = sorted((set(self.vars.keys()) | set(other.vars.keys())) - \
            set(noCompare.vars.keys()), numericSort)
        # For each of these addresses, compare the variable
        for a in addrs:
            texta = a
            if texta.endswith("%0"):
                texta = texta[:-1]
            if texta.startswith("i") and not texta.startswith("inv"):
                i = int(texta[1:])
                if i in range(100):
                    desc = PmacState.globalIVariableDescriptions[i]
                elif i in range(3300):
                    desc = PmacState.motorIVariableDescriptions[i%100]
                else:
                    desc = "No description available"
                texta = page.doc_node(a, desc)
            if a not in other.vars:
                if not self.vars[a].ro and not self.vars[a].isEmpty():
                    result = False
                    self.writeHtmlRow(page, table, texta, 'Missing', None, self.vars[a])
            elif a not in self.vars:
                if not other.vars[a].ro and not other.vars[a].isEmpty():
                    result = False
                    self.writeHtmlRow(page, table, texta, 'Missing', other.vars[a], None)
                    if fixfile is not None:
                        fixfile.write(other.vars[a].dump())
            elif not self.vars[a].compare(other.vars[a]):
                if not other.vars[a].ro and not self.vars[a].ro:
                    result = False
                    self.writeHtmlRow(page, table, texta, 'Mismatch', other.vars[a],
                        self.vars[a])
                    if fixfile is not None:
                        fixfile.write(other.vars[a].dump())
        # Check the running PLCs
        for n in range(32):
            plc = self.getPlcProgramNoCreate(n)
            if plc is not None:
                plc.setShouldBeRunning()
                #print "PLC%s, isRunning=%s, shouldBeRunning=%s" % (n, plc.isRunning, plc.shouldBeRunning)
                if plc.shouldBeRunning and not plc.isRunning:
                    result = False
                    self.writeHtmlRow(page, table, 'plc%s'%n, 'Not running', None, None)
                    if fixfile is not None:
                        fixfile.write('enable plc %s\n' % n)
                elif not plc.shouldBeRunning and plc.isRunning:
                    result = False
                    self.writeHtmlRow(page, table, 'plc%s'%n, 'Running', None, None)
                    if fixfile is not None:
                        fixfile.write('disable plc %s\n' % n)
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
            page.text(col, '-')
        else:
            referenceVar.htmlCompare(page, col, hardwareVar)
        # The hardware column
        col = page.tableColumn(row)
        if hardwareVar is None:
            page.text(col, '-')
        else:
            hardwareVar.htmlCompare(page, col, referenceVar)
    def loadPmcFile(self, fileName):
        '''Loads a PMC file into this PMAC state.'''
        file = open(fileName, 'r')
        if file is None:
            raise AnalyseError('Could not open reference file: %s' % fileName)
        print 'Loading PMC file %s...' % fileName
        parser = PmacParser(file, self)
        parser.onLine()
    def loadPmcFileWithPreprocess(self, fileName, includePaths):
        '''Loads a PMC file into this PMAC state having expanded includes and defines.'''
        if includePaths is not None:
            p = clsPmacParser(includePaths = includePaths.split(':'))
        else:
            p = clsPmacParser()
        print 'Loading PMC file %s...' % fileName
        converted = p.parse(fileName, debug=True)
        if converted is None:
            raise AnalyseError('Could not open reference file: %s' % fileName)
        parser = PmacParser(p.output, self)
        parser.onLine()

class Pmac(object):
    '''A class that represents a single PMAC and its state.'''
    def __init__(self, name):
        self.name = name
        self.noCompare = PmacState('noCompare')
        self.reference = None
        self.compareWith = None
        self.host = ''
        self.port = 1
        self.termServ = False
        self.geobrick = None
        self.numMacroStationIcs = None
        self.pti = None
        self.backupFile = None
        self.referenceState = PmacState('reference')
        self.hardwareState = PmacState('hardware')
        self.compareResult = True
        self.useFactoryDefs = True
        self.numAxes = 0
        self.positionsBefore = []
        self.positionsAfter = []
    def readCurrentPositions(self):
        '''Read the current motor positions of the PMAC.'''
        for axis in range(self.numAxes):
            (returnStr, status) = self.sendCommand('#%sP' % (axis+1))
            self.initialPositions[axis+1] = returnStr
            text += '%s ' % returnStr[:-2]
        print text
    def htmlMotorIVariables(self, motor, page):
        self.hardwareState.htmlMotorIVariables(motor, page, self.geobrick)
    def htmlGlobalIVariables(self, page):
        self.hardwareState.htmlGlobalIVariables(page)
    def htmlMotorMsIVariables(self, motor, page):
        self.hardwareState.htmlMotorMsIVariables(motor, page)
    def htmlGlobalMsIVariables(self, page):
        self.hardwareState.htmlGlobalMsIVariables(page)
    def compare(self, page, fixfile):
        print 'Comparing...'
        self.compareResult = self.hardwareState.compare(self.referenceState, self.noCompare, self.name, page, fixfile)
        if self.compareResult:
            print 'Hardware matches reference'
        else:
            print 'Hardware to reference mismatch detected'
        return self.compareResult
    def setProtocol(self, host, port, termServ):
        self.host = host
        self.port = port
        self.termServ = termServ
    def setGeobrick(self, g):
        self.geobrick = g
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
    def readHardware(self, backupDir, checkPositions, debug, comments):
        '''Loads the current state of the PMAC.  If a backupDir is provided, the
           state is written as it is read.'''
        self.checkPositions = checkPositions
        self.debug = debug
        self.comments = comments
        try:
            # Open the backup file if required
            if backupDir is not None:
                fileName = '%s/%s.pmc' % (backupDir, self.name)
                print "Opening backup file %s" % fileName
                self.backupFile = open(fileName, 'w')
                if file is None:
                    raise AnalyseError('Could not open backup file: %s' % fileName)
            # Open either a Telnet connection to a terminal server,
            # or a direct TCP/IP connection to a PMAC
            if self.termServ:
                self.pti = PmacTelnetInterface()
            else:
                self.pti = PmacEthernetInterface()
            self.pti.setConnectionParams(self.host, self.port)
            msg = self.pti.connect()
            if msg != None:
                raise PmacReadError(msg)
            print 'Connected to a PMAC via "%s" using port %s.' % (self.host, self.port)
            # Work out what kind of PMAC we have, if necessary
            self.determinePmacType()
            self.determineNumAxes()
            self.determineNumCoordSystems()
            # Read the axis current positions
            self.positionsBefore = self.readCurrentPositions()
            #print 'Current positions: %s' % self.positionsBefore
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
                print 'Disconnecting from PMAC...'
                msg = self.pti.disconnect()
                self.pti = None
                print 'Connection to the PMAC closed.'
            # Close the backup file
            if self.backupFile is not None:
                self.backupFile.close()
                self.backupFile = None
    def verifyCurrentPositions(self, positions):
        ''' Checks the axis current positions to see if any have moved.'''
        if self.checkPositions:
            now = self.readCurrentPositions()
            match = True
            for i in range(len(now)):
                if match and now[i] < positions[i]+10.0 and now[i] > positions[i]-10.0:
                    pass
                else:
                    match = False
            if match:
                print 'No axes moved during hardware readout'
            else:
                print 'One or more axes have moved:'
                print '  Before: %s' % positions
                print '  Now:    %s' % now
    def sendCommand(self, text):
        (returnStr, status) = self.pti.sendCommand(text)
        if self.debug:
            print '%s --> %s' % (repr(text), repr(returnStr))
        return (returnStr, status)
    def readCurrentPositions(self):
        ''' Returns the current position as a list.'''
        positions = []
        for axis in range(self.numAxes):
            (returnStr, status) = self.sendCommand('#%sP' % (axis+1))
            positions.append(float(returnStr[:-2]))
        return positions
    def determinePmacType(self):
        '''Discovers whether the PMAC is a Geobrick or a VME style PMAC'''
        if self.geobrick is None:
            (returnStr, status) = self.sendCommand('cid')
            if not status:
                raise PmacReadError(returnStr)
            id = returnStr[:-2]
            if id == '602413':
                self.geobrick = False
            elif id == '603382':
                self.geobrick = True
            else:
                self.geobrick = False
            print 'Geobrick= %s' % self.geobrick
    def determineNumAxes(self):
        '''Determines the number of axes the PMAC has by determining the
           number of macro station ICs.'''
        if self.numMacroStationIcs is None:
            (returnStr, status) = self.sendCommand('i20 i21 i22 i23')
            if not status:
                raise PmacReadError(returnStr)
            macroIcAddresses = returnStr[:-2].split('\r')
            self.numMacroStationIcs = 0
            for i in range(4):
                if macroIcAddresses[i] != '$0':
                    self.numMacroStationIcs += 1
        self.numAxes = self.numMacroStationIcs * 8
        if self.geobrick:
            self.numAxes += 8
        print 'Num axes= %s' % self.numAxes
    def determineNumCoordSystems(self):
        '''Determines the number of coordinate systems that are active by
           reading i68.'''
        (returnStr, status) = self.sendCommand('i68')
        if not status:
            raise PmacReadError(returnStr)
        self.numCoordSystems = int(returnStr[:-2]) + 1
    def writeBackup(self, text):
        '''If a backup file is open, write the text.'''
        if self.backupFile is not None:
            self.backupFile.write(text)
    def readIvars(self):
        '''Reads the I variables.'''
        print 'Reading I-variables...'
        self.writeBackup('\n; I-variables\n')
        roVars = set([3,4,6,9,20,21,22,23,24,41,58]+range(4900,5000)+
            [5111,5112,5211,5212,5311,5312,5411,5412,5511,5512,5611,5612,5711,
            5712,5811,5812,5911,5912,6011,6012,6111,6112,6211,6212,6311,6312,
            6411,6412,6511,6512,6611,6612])
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand('i%s..%s' % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            ivars = enumerate(returnStr.split("\r")[:-1])
            for o,x in ivars:
                ro = i+o in roVars
                var = PmacIVariable(i+o, self.toNumber(x), ro=ro)
                self.hardwareState.addVar(var)
                motor = (i+o) / 100
                index = (i+o) % 100
                text = ""
                if self.comments:
                   if motor == 0 and index in PmacState.globalIVariableDescriptions:
                       text = PmacState.globalIVariableDescriptions[index]
                   if motor >= 1 and motor <= 32 and index in PmacState.motorIVariableDescriptions:
                       text = PmacState.motorIVariableDescriptions[index]
                self.writeBackup(var.dump(comment=text))
            i += varsPerBlock
    def readPlcDisableState(self):
        '''Reads the PLC disable state from the M variables 5000..5031.'''
        (returnStr, status) = self.sendCommand('m5000..5031')
        if not status:
            raise PmacReadError(returnStr)
        mvars = enumerate(returnStr.split("\r")[:-1])
        for o,x in mvars:
            plc = self.hardwareState.getPlcProgramNoCreate(o)
            if plc is not None:
                runningState = False
                if x == '0':
                    runningState = True
                plc.setIsRunning(runningState)
    def readPvars(self):
        '''Reads the P variables.'''
        print 'Reading P-variables...'
        self.writeBackup('\n; P-variables\n')
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand('p%s..%s' % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            pvars = enumerate(returnStr.split("\r")[:-1])
            for o,x in pvars:
                var = PmacPVariable(i+o, self.toNumber(x))
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
            i += varsPerBlock
    def readQvars(self):
        '''Reads the Q variables of a coordinate system.'''
        print 'Reading Q-variables...'
        for cs in range(1,self.numCoordSystems+1):
            self.writeBackup('\n; &%s Q-variables\n' % cs)
            (returnStr, status) = self.sendCommand('&%sq1..199' % cs)
            if not status:
                raise PmacReadError(returnStr)
            qvars = enumerate(returnStr.split("\r")[:-1])
            for o,x in qvars:
                var = PmacQVariable(cs, o+1, self.toNumber(x))
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
    def readFeedrateOverrides(self):
        '''Reads the feedrate overrides of the coordinate systems.'''
        print 'Reading feedrate overrides...'
        self.writeBackup('\n; Feedrate overrides\n')
        for cs in range(1,self.numCoordSystems+1):
            (returnStr, status) = self.sendCommand('&%s%%' % cs)
            if not status:
                raise PmacReadError(returnStr)
            val = returnStr.split("\r")[0]
            var = PmacFeedrateOverride(cs, self.toNumber(val))
            self.hardwareState.addVar(var)
            self.writeBackup(var.dump())
    def readMvarDefinitions(self):
        '''Reads the M variable definitions.'''
        print 'Reading M-variable definitions...'
        self.writeBackup('\n; M-variables\n')
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand('m%s..%s->' % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            mvars = enumerate(returnStr.split("\r")[:-1])
            for o,x in mvars:
                var = PmacMVariable(i+o)
                parser = PmacParser([x], self)
                parser.parseMVariableAddress(variable=var)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
            i += varsPerBlock
    def readMvarValues(self):
        '''Reads the M variable values.'''
        print 'Reading M-variable values...'
        varsPerBlock = 100
        i = 0
        while i < 8192:
            iend = i + varsPerBlock - 1
            if iend >= 8192:
                iend = 8191
            (returnStr, status) = self.sendCommand('m%s..%s' % (i, iend))
            if not status:
                raise PmacReadError(returnStr)
            mvars = enumerate(returnStr.split("\r")[:-1])
            for o,x in mvars:
                var = self.hardwareState.getMVariable(i+o)
                var.setValue(self.toNumber(x))
                #if (i+o) == 99:
                #    print "m99 ->%s, =%s, x=%s" % (var.valStr(), var.contentsStr(), x)
            i += varsPerBlock
    def readCoordinateSystemDefinitions(self):
        '''Reads the coordinate system definitions.'''
        print 'Reading coordinate system definitions...'
        self.writeBackup('\n; Coordinate system definitions\n')
        self.writeBackup('undefine all\n')
        for cs in range(1,self.numCoordSystems+1):
            for axis in range(1,32+1):  # Note range is always 32 NOT self.numAxes
                # Ask for the motor status in the coordinate system
                cmd = '&%s#%s->' % (cs, axis)
                (returnStr, status) = self.sendCommand(cmd)
                if not status or len(returnStr) <= 2:
                    raise PmacReadError(returnStr)
                # Note the dropping of the last two characters, ^m^f
                parser = PmacParser([returnStr[:-2]], self)
                var = PmacCsAxisDef(cs, axis, parser.tokens())
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
    def readKinematicPrograms(self):
        '''Reads the kinematic programs.  Note that this
           function will fail if a program exceeds 1350 characters and small buffers
           are required.'''
        print 'Reading kinematic programs...'
        self.writeBackup('\n; Kinematic programs\n')
        for cs in range(1,self.numCoordSystems+1):
            (returnStr, status) = self.sendCommand('&%s list forward' % cs)
            if not status:
                raise PmacReadError(returnStr)
            if not self.termServ and len(returnStr) > 1350:
                raise PmacReadError('Possibly incomplete program')
            lines = returnStr.split('\r')[:-1]
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacForwardKinematicProgram(cs, parser.tokens())
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
            (returnStr, status) = self.sendCommand('&%s list inverse' % cs)
            if not status:
                raise PmacReadError(returnStr)
            if not self.termServ and len(returnStr) > 1350:
                raise PmacReadError('Possibly incomplete program')
            lines = returnStr.split('\r')[:-1]
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacInverseKinematicProgram(cs, parser.tokens())
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
    def getListingLines(self, thing):
        '''Returns the listing of a motion program or PLC using
           small blocks.  It uses the start and length parameters
           of the list command to slowly build up the listing.  Note
           that the function fails if any chuck exceeds 1350 characters.
           For use in small buffer mode.'''
        lines = []
        offsets = []
        startPos = 0
        increment = 80
        going = True
        possiblyIncomplete = False
        while going:
            (returnStr, status) = self.sendCommand('list %s,%s,%s' % (thing, startPos, increment))
            startPos += increment
            if not status:
                raise PmacReadError(returnStr)
            if len(returnStr) > 1350:
                raise PmacReadError('String too long for small buffer mode')
            if returnStr.find('ERR') >= 0:
                going = False
            else:
                # Print a warning if the last block may have been incomplete
                if possiblyIncomplete:
                    raise PmacReadError('Less that 2 lines in a buffer, completion not gauranteed')
                # Seperate into lines
                more = returnStr.split('\r')[:-1]
                # Add the lines to the current set of lines, removing the
                # word number that is on the beginning of each line.
                lastStartPos = 0
                for m in more:
                    parts = m.split(':', 1)
                    if len(parts) == 2:
                        lastStartPos = int(parts[0])
                        line = parts[1]
                        lines.append(line)
                        offsets.append(parts[0])
                    else:
                        print "Warning: could not split line into offset and text for %s, got %s" % (thing, repr(m))
                        #raise PmacReadError("Warning: could not split line into offset and text")
                if len(more) < 2:
                    # If we only got one line, it may be incomplete
                    possiblyIncomplete = True
                else:
                    # Chop off the last line (it may be incomplete) and adjust the start pos
                    lines = lines[:-1]
                    offsets = offsets[:-1]
                    startPos = lastStartPos
        return (lines, offsets)
    def readPlcPrograms(self):
        '''Reads the PLC programs'''
        print 'Reading PLC programs...'
        self.writeBackup('\n; PLC programs\n')
        for plc in range(32):
            (lines, offsets) = self.getListingLines('plc %s' % plc)
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacPlcProgram(plc, parser.tokens(), lines, offsets)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
    def readMotionPrograms(self):
        '''Reads the motion programs. Note
           that only the first 256 programs are read, there are actually 32768.'''
        print 'Reading motion programs...'
        self.writeBackup('\n; Motion programs\n')
        for prog in range(1,256):
            (lines, offsets) = self.getListingLines('program %s' % prog)
            if len(lines) == 1 and lines[0].find('ERR003') >= 0:
                lines = []
                offsets = []
            if len(lines) > 0:
                parser = PmacParser(lines, self)
                var = PmacMotionProgram(prog, parser.tokens(), lines, offsets)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
    def readMsIvars(self):
        '''Reads the macrostation I variables.'''
        if self.numMacroStationIcs > 0:
            print 'Reading macro station I-variables'
            self.writeBackup('\n; Macro station I-variables\n')
            reqMacroStations = []
            if self.numMacroStationIcs >= 1:
                reqMacroStations += [0,1,4,5,8,9,12,13]
            if self.numMacroStationIcs >= 2:
                reqMacroStations += [16,17,20,21,24,25,28,29]
            if self.numMacroStationIcs >= 3:
                reqMacroStations += [32,33,36,37,40,41,44,45]
            if self.numMacroStationIcs >= 4:
                reqMacroStations += [48,49,52,53,56,57,60,61]
            reqVars = [910,911,912,913,914,915,916,917,918,923,925,926,927,928,929]
            roVars = [921,922,924,930,938,939]
            for ms in reqMacroStations:
                self.doMsIvars(ms, reqVars, roVars)
    def readGlobalMsIvars(self):
        '''Reads the global macrostation I variables.'''
        if self.numMacroStationIcs > 0:
            print 'Reading global macrostation I-variables'
            self.writeBackup('\n; Macro station global I-variables\n')
            if self.numMacroStationIcs in [1,2]:
                reqMacroStations = [0]
            elif self.numMacroStationIcs in [3,4]:
                reqMacroStations = [0,32]
            else:
                reqMacroStations = []
            reqVars = [0,2,3,6,8,9,10,11,14]
            reqVars += range(14,100)
            reqVars += range(101,109)
            reqVars += range(111,119)
            reqVars += range(120,154)
            reqVars += range(161,197)
            reqVars += [198,199,200,203,204,205,206,207,208]
            reqVars += range(210,226)
            reqVars += range(250,266)
            reqVars += [900,903,904,905,906,907,908,909,940,941,942,943,975,976,977]
            reqVars += [987,988,989,992,993,994,995,996,996,998,999]
            roVars = [4,5,12,13,209,974]
            for ms in reqMacroStations:
                self.doMsIvars(ms, reqVars, roVars)
            reqVars = range(16,100)
            reqVars += range(101,109)
            reqVars += range(111,119)
            reqVars += range(120,154)
            reqVars += range(161,197)
            reqVars += [198,199]
            reqVars += [900,903,904,905,906,907,908,909,940,941,942,943,975,976,977]
            reqVars += [987,988,989,992,993,994,995,996,996,998,999]
            roVars = [4,5,12,13,209,974]
            reqMacroStations = [16,48]
            for ms in reqMacroStations:
                self.doMsIvars(ms, reqVars, roVars)
    def doMsIvars(self, ms, reqVars, roVars):
        '''Reads the specified set of global macrostation I variables.'''
        for v in reqVars:
            (returnStr, status) = self.sendCommand('ms%s,i%s' % (ms, v))
            if not status:
                raise PmacReadError(returnStr)
            if returnStr[0] != '\x07':
                var = PmacMsIVariable(ms, v, self.toNumber(returnStr[:-2]))
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
        for v in roVars:
            (returnStr, status) = self.sendCommand('ms%s,i%s' % (ms, v))
            if not status:
                raise PmacReadError(returnStr)
            if returnStr[0] != '\x07':
                var = PmacMsIVariable(ms, v, self.toNumber(returnStr[:-2]), ro=True)
                self.hardwareState.addVar(var)
                self.writeBackup(var.dump())
    def loadReference(self, factorySettings, includePaths=None):
        '''Loads the reference PMC file after first initialising the state.'''
        # Feedrate overrides default to 100
        for cs in range(1,self.numCoordSystems+1):
            var = PmacFeedrateOverride(cs, 100.0)
            self.referenceState.addVar(var)
        if factorySettings is not None:
            self.referenceState.copyFrom(factorySettings)
        if self.reference is not None:
            self.referenceState.setInlineExpressionResolutionState(self.hardwareState)
            self.referenceState.loadPmcFileWithPreprocess(self.reference, includePaths)
    def loadCompareWith(self):
        '''Loads the compare with file.'''
        self.hardwareState.loadPmcFile(self.compareWith)
    def toNumber(self, text):
        if text[0] == '$':
            result = int(text[1:], 16)
        elif text.find('.') >= 0:
            result = float(text)
        else:
            result = int(text)
        return result

class PmacParser(object):
    def __init__(self, source, pmac, debug=False):
        self.lexer = PmacLexer(source, debug)
        self.pmac = pmac
        self.curCs = 1
        self.curMotor = 1
        self.debug = debug
    def tokens(self):
        return self.lexer.tokens
    def onLine(self):
        '''Top level on-line command mode parser.'''
        t = self.lexer.getToken()
        while t is not None:
            if t == '&':
                self.parseAmpersand()
            elif t == '%':
                self.parsePercent()
            elif t == '#':
                self.parseHash()
            elif t == 'OPEN':
                self.parseOpen()
            elif t == 'P':
                self.parseP()
            elif t == 'Q':
                self.parseQ()
            elif t == 'I':
                self.parseI()
            elif t == 'M':
                self.parseM()
            elif t == 'MS':
                self.parseMs()
            elif t == 'UNDEFINE':
                self.parseUndefine()
            elif t == 'CLOSE':
                pass   # Just ignore top level closes
            elif t == 'ENDGATHER':
                pass   # Just ignore top level endgathers
            elif t == 'ENABLE':
                self.parseEnable()
            elif t == 'DELETE':
                self.parseDelete()
            elif t == 'DISABLE':
                self.parseDisable()
            elif t == 'W':
                self.parseWrite()
            else:
                raise ParserError('Unexpected token: %s' % t, t)
            t = self.lexer.getToken()
    def parseDisable(self):
        t = self.lexer.getToken()
        if t in ['PLC', 'PLCC']: 
            t = self.lexer.getToken()
            if tokenIsInt(t):
                pass
            else:
                raise ParseError('Expected integer, got %s' % t, self.lexer.line)
        else:
            raise ParseError('Expected PLC or PLCC, got %s' % t, self.lexer.line)
    def parseWrite(self):
        area = self.lexer.getToken()
        address = self.lexer.getToken()
        comma = self.lexer.getToken()
        while comma == ',':
            constant = self.lexer.getToken()
            comma = self.lexer.getToken()
        self.lexer.putToken(comma)
    def parseDelete(self):
        t = self.lexer.getToken()
        if t == 'ALL':
            t = self.lexer.getToken()
            if t != 'TEMPS':
                self.lexer.putToken(t)
        elif t in ['BLCOMP', 'CCUBUF', 'BLCOMP', 'COMP', 'LOOKAHEAD', 'GATHER', 
                'PLCC', 'ROTARY', 'TBUF', 'TCOMP', 'TRACE']:
            pass
        else:
            raise ParseError('Expected DELETE type, got %s' % t, self.lexer.line)
    def parseEnable(self):
        t = self.lexer.getToken()
        if t not in ['PLC', 'PLCC']:
            raise ParseError('Expected PLC or PLCC, got: %s' % t, self.lexer.line)
        p = tokenToInt(self.lexer.getToken())
    def parseUndefine(self):
        t = self.lexer.getToken()
        if t == 'ALL':
            for cs in range(1,17):
                for m in range(1,33):
                    var = self.pmac.getCsAxisDef(cs, m)
                    var.clear()
                    var.add(PmacToken('0'))
        else:
            for m in range(1,33):
                var = self.pmac.getCsAxisDef(self.curCs, m)
                var.clear()
                var.add(PmacToken('0'))
    def parseMs(self):
        ms = self.lexer.getToken()
        if tokenIsInt(ms):
            ms = tokenToInt(ms)
            self.lexer.getToken(',')
            varType = self.lexer.getToken()
            if varType in ['I', 'MI']:
                n = tokenToInt(self.lexer.getToken())
                t = self.lexer.getToken()
                if t == '=':
                    val = tokenToFloat(self.lexer.getToken())
                    var = self.pmac.getMsIVariable(ms, n)
                    var.set(val)
                else:
                    self.lexer.putToken(t)
                    # Report variable value (do nothing)
            else:
                raise ParserError('Unsupported', t)
        else:
            raise ParserError('Unsupported', ms)
    def parseM(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == '=':
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getMVariable(n)
                    var.setValue(val)
                    n += increment
                    count -= 1
            elif t == '->':
                t = self.lexer.getToken()
                if t in ['*', 'D', 'DP', 'F', 'L', 'TWB', 'TWD', 'TWR', 'TWS', 'X', 'Y']:
                    self.lexer.putToken(t)
                    self.parseMVariableAddress(start, count, increment)
                else:
                    self.lexer.putToken(t)
                    # Report M variable address (do nothing)
            else:
                self.lexer.putToken(t)
                # Report M variable values (do nothing)
        else:
            raise ParserError('Unexpected statement: M %s' % t, t)
    def parseMVariableAddress(self, start=0, count=0, increment=0, variable=None):
        type = self.lexer.getToken()
        address = 0
        offset = 0
        width = 1
        format = 'U'
        if type == '*':
            pass
        elif type in ['D', 'DP', 'F', 'L']:
            t = self.lexer.getToken()
            if t == ':':
                t = self.lexer.getToken()
            address = tokenToInt(t)
        elif type in ['TWB', 'TWD', 'TWR', 'TWS']:
            raise ParseError('Unsupported', self.lexer.line)
        elif type in ['X', 'Y']:
            t = self.lexer.getToken()
            if t == ':':
                t = self.lexer.getToken()
            address = tokenToInt(t)
            self.lexer.getToken(',')
            offset = tokenToInt(self.lexer.getToken())
            if offset == 24:
                offset = 0
                width = 24
                t = self.lexer.getToken()
                if t == ',':
                    format = self.lexer.getToken()
                else:
                    self.lexer.putToken(t)
            else:
                t = self.lexer.getToken()
                if t == ',':
                    width = tokenToInt(self.lexer.getToken())
                    t = self.lexer.getToken()
                    if t == ',':
                        format = self.lexer.getToken()
                    else:
                        self.lexer.putToken(t)
                else:
                    self.lexer.putToken(t)
            if format not in ['U', 'S']:
                raise ParserError('Expected format, got %s' % format, t)
        if variable is not None:
            variable.set(type, address, offset, width, format)
        else:
            n = start
            while count > 0:
                var = self.pmac.getMVariable(n)
                var.set(type, address, offset, width, format)
                n += increment
                count -= 1
    def parseVarSpec(self):
        t = self.lexer.getToken()
        varType = ''
        nodeList = []
        if t in ['I','P','M']:
            varType = t.lower()
        elif t == 'MS':
            varType = t.lower()
            t = self.lexer.getToken()
            if t == '[':
                nodeList.append(tokenToInt(self.lexer.getToken()))
                t = self.lexer.getToken()
                if t == '..':
                    last = tokenToInt(self.lexer.getToken())
                    nodeList += range(nodeList[0]+1, last+1)
                else:
                    while t == ',':
                        nodeList.append(tokenToInt(self.lexer.getToken()))
                        t = self.lexer.getToken()
                    self.lexer.putToken(t)
                self.lexer.getToken(']')
            else:
                nodeList.append(tokenToInt(t))
            self.lexer.getToken(',')
            self.lexer.getToken('I')
        elif t == '&':
            varType = t.lower()
            t = self.lexer.getToken()
            if t == '[':
                nodeList.append(tokenToInt(self.lexer.getToken()))
                t = self.lexer.getToken()
                if t == '..':
                    last = tokenToInt(self.lexer.getToken())
                    nodeList += range(nodeList[0]+1, last+1)
                while t == ',':
                    nodeList.append(tokenToInt(self.lexer.getToken()))
                    t = self.lexer.getToken()
                    self.lexer.putToken()
                self.lexer.getToken(']')
            else:
                nodeList.append(tokenToInt(t))
            self.lexer.getToken('Q')
        else:
            raise ParserError('Expected variable type, got: %s' % t, t)
        start = tokenToInt(self.lexer.getToken())
        t = self.lexer.getToken()
        if t == '..':
            end = tokenToInt(self.lexer.getToken())
            if end <= start:
                raise ParserError('End of range lower than start', t)
            count = end + 1 - start
            increment = 1
        elif t == ',':
            count = tokenToInt(self.lexer.getToken())
            self.lexer.getToken(',')
            increment = tokenToInt(self.lexer.getToken())
        else:
            count = 1
            increment = 1
        return (varType, nodeList, start, count, increment)
    def parseI(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == '=':
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getIVariable(n)
                    var.set(val)
                    n += increment
                    count -= 1
            else:
                self.lexer.putToken(t)
                # Report I variable values (do nothing)
        elif n == '(':
            n = self.parseExpression()
            t = self.lexer.getToken(')')
            t = self.lexer.getToken()
            if t == '=':
                val = self.parseExpression()
                var = self.pmac.getIVariable(n)
                var.set(val)
            else:
                self.lexer.putToken(t)
                # Report I variable values (do nothing)
        else:
            raise ParserError('Unexpected statement: I %s' % n, n)
    def parseP(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == '=':
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getPVariable(n)
                    var.set(val)
                    n += increment
                    count -= 1
            else:
                self.lexer.putToken(t)
                # Report P variable values (do nothing)
        elif n == '(':
            n = self.parseExpression()
            t = self.lexer.getToken(')')
            t = self.lexer.getToken()
            if t == '=':
                val = self.parseExpression()
                var = self.pmac.getPVariable(n)
                var.set(val)
            else:
                self.lexer.putToken(t)
                # Report P variable values (do nothing)
        else:
            self.lexer.putToken(n)
            # Report motor position (do nothing)
    def parseQ(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == '=':
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getQVariable(self.curCs, n)
                    var.set(val)
                    n += increment
                    count -= 1
            else:
                self.lexer.putToken(t)
                # Report Q variable values (do nothing)
        elif n == '(':
            n = self.parseExpression()
            t = self.lexer.getToken(')')
            t = self.lexer.getToken()
            if t == '=':
                val = self.parseExpression()
                var = self.pmac.getQVariable(n)
                var.set(val)
            else:
                self.lexer.putToken(t)
                # Report Q variable values (do nothing)
        else:
            self.lexer.putToken(n)
            # Quit program (do nothing)
    #def parseExpression(self):
    #    '''Returns the result of the expression.'''
    #    # Currently only supports a constant prefixed by an optional minus sign
    #    negative = False
    #    t = self.lexer.getToken()
    #    if t == '-':
    #        negative = True
    #        t = self.lexer.getToken()
    #    if not tokenIsFloat(t):
    #        raise ParserError('Unsupported', t)
    #    result = tokenToFloat(t)
    #    if negative:
    #        result = -result
    #    return result
    def parseExpression(self):
        '''Returns the result of the expression.'''
        # Currently supports syntax of the form:
        #    <expression> ::= <e1> { <sumop> <e1> }
        #    <e1> ::= <e2> { <multop> <e2> }
        #    <e2> ::= [ <monop> ] <e3>
        #    <e3> ::= '(' <expression> ')' | <constant> | 'P'<integer> | 'Q'<integer> | 'I'<integer> | 'M' <integer>
        #    <sumop> ::= '+' | '-' | '|' | '^'
        #    <multop> ::= '*' | '/' | '%' | '&'
        #    <monop> ::= '+' | '-'
        result = self.parseE1()
        going = True
        while going:
            t = self.lexer.getToken()
            if t == '+':
                result = result + self.parseE1()
            elif t == '-':
                result = result - self.parseE1()
            elif t == '|':
                result = float(int(result) | int(self.parseE1()))
            elif t == '^':
                result = float(int(result) ^ int(self.parseE1()))
            else:
                self.lexer.putToken(t)
                going = False
        return result
    def parseE1(self):
        '''Returns the result of a sub-expression containing multiplicative operands.'''
        result = self.parseE2()
        going = True
        while going:
            t = self.lexer.getToken()
            if t == '*':
                result = result * self.parseE2()
            elif t == '/':
                result = result / self.parseE2()
            elif t == '%':
                result = result % self.parseE2()
            elif t == '&':
                result = float(int(result) & int(self.parseE2()))
            else:
                self.lexer.putToken(t)
                going = False
        return result
    def parseE2(self):
        '''Returns the result of a sub-expression containing monadic operands.'''
        monop = self.lexer.getToken()
        if monop not in ['+', '-']:
            self.lexer.putToken(monop)
            monop = '+'
        result = self.parseE3()
        if monop == '-':
            result = -result;
        return result
    def parseE3(self):
        '''Returns the result of a sub-expression that is an I,P,Q or M variable or
           a constant or a parenthesised expression.'''
        t = self.lexer.getToken()
        if t == '(':
            result = self.parseExpression()
            t = self.lexer.getToken(')')
        elif t == 'I':
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionIValue(tokenToInt(t))
        elif t == 'Q':
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionQValue(tokenToInt(t))
        elif t == 'P':
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionPValue(tokenToInt(t))
        elif t == 'M':
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionMValue(tokenToInt(t))
        else:
            result = tokenToFloat(t)
        return result
    def parseRange(self, start):
        '''Returns the range as (start, count, increment).'''
        t = self.lexer.getToken()
        if t == '..':
            last = tokenToInt(self.lexer.getToken())
            if last <= start:
                raise ParserError('End of range not greater than start', t)
            count = last - start + 1
            increment = 1
        elif t == ',':
            count = tokenToInt(self.lexer.getToken())
            self.lexer.getToken(',')
            increment = tokenToInt(self.lexer.getToken())
        else:
            self.lexer.putToken(t)
            count = 1
            increment = 1
        return (start, count, increment)
    def parseOpen(self):
        t = self.lexer.getToken()
        if t == 'PROGRAM':
            n = self.lexer.getToken()
            if tokenIsInt(n):
                prog = self.pmac.getMotionProgram(tokenToInt(n))
                self.parseProgram(prog)
            else:
                raise ParserError('Expected integer, got: %s' % t, t)
        elif t == 'PLC':
            n = self.lexer.getToken()
            if tokenIsInt(n):
                prog = self.pmac.getPlcProgram(tokenToInt(n))
                self.parseProgram(prog)
            else:
                raise ParserError('Expected integer, got: %s' % t, t)
        elif t == 'FORWARD':
            prog = self.pmac.getForwardKinematicProgram(self.curCs)
            self.parseProgram(prog)
        elif t == 'INVERSE':
            prog = self.pmac.getInverseKinematicProgram(self.curCs)
            self.parseProgram(prog)
        else:
            raise ParserError('Unknown buffer type: %s' % t, t)
    def parseProgram(self, prog):
        last = None
        t = self.lexer.getToken(wantEol=True)
        while t is not None and t != 'CLOSE':
            if t == 'CLEAR':
                prog.clear()
            elif t == 'FRAX':
                prog.add(t)
                t = self.lexer.getToken(wantEol=True)
                if t == '(':
                    axes = {'A':False, 'B':False, 'C':False, 
                            'X':False, 'Y':False, 'Z':False,
                            'U':False, 'V':False, 'W':False}
                    t = self.lexer.getToken(wantEol=True)
                    while t in ['A', 'B', 'C', 'X', 'Y', 'Z', 'U', 'V', 'W']:
                        axes[str(t)] = True
                        t = self.lexer.getToken()
                        if t == ',':
                            t = self.lexer.getToken()
                    self.lexer.putToken(t)
                    self.lexer.getToken(')')
                    allTrue = True
                    for x,t in axes.iteritems():
                        if not t:
                            allTrue = False
                    if not allTrue:
                        prog.add(PmacToken('('))
                        first = True
                        for x in ['A','B','C','U','V','W','X','Y','Z']:
                            if axes[x]:
                                if not first:
                                    prog.add(PmacToken(','))
                                first = False
                                prog.add(PmacToken(x))
                        prog.add(PmacToken(')'))
                else:
                    self.lexer.putToken(t)
            elif t == '&':
                # Drop any '&' followed by COMMAND
                n = self.lexer.getToken(wantEol=True)
                if n != 'COMMAND':
                    prog.add(t)
                self.lexer.putToken(n)
            else:
                prog.add(t)
            if not t == '\n':
                last = t
            t = self.lexer.getToken(wantEol=True)
        if last is not None and last != 'RETURN':
            prog.add(PmacToken('RETURN'))
    def parseHash(self):
        m = self.lexer.getToken()
        if tokenIsInt(m):
            a = self.lexer.getToken()
            if a == '->':
                t = self.lexer.getToken()
                if t == '0':
                    # Clear axis definition
                    var = self.pmac.getCsAxisDef(self.curCs, tokenToInt(m))
                    var.clear()
                    var.add(t)
                elif t == 'I':
                    # Inverse kinematic axis definition
                    var = self.pmac.getCsAxisDef(self.curCs, tokenToInt(m))
                    var.clear()
                    var.add(t)
                elif tokenIsFloat(t) or t in ['-','X','Y','Z','U','V','W','A','B','C']:
                    # Axis definition
                    var = self.pmac.getCsAxisDef(self.curCs, tokenToInt(m))
                    var.clear()
                    self.lexer.putToken(t)
                    self.parseAxisDefinition(var)
                else:
                    self.lexer.putToken(t)
                    # Report axis definition (do nothing)
            else:
                self.lexer.putToken(a)
                # Set current motor
                self.curMotor = tokenToInt(m)
        else:
            self.lexer.putToken(m)
            # Report current motor (do nothing)
    def parseAmpersand(self):
        t = self.lexer.getToken()
        if tokenIsInt(t):
            # Set current coordinate system
            self.curCs = tokenToInt(t)
        else:
            self.lexer.putToken(t)
            # Report coordinate system (do nothing)
    def parsePercent(self):
        t = self.lexer.getToken()
        if tokenIsFloat(t):
            # Set the feedrate override
            var = self.pmac.getFeedrateOverride(self.curCs)
            var.set(tokenToFloat(t))
        else:
            self.lexer.putToken(t)
            # Report feedrate override (do nothing)
    def parseAxisDefinition(self, var):
        first = True
        going = True
        while going:
            t = self.lexer.getToken()
            if t == '+':
                if not First:
                    var.add(t)
                t = self.lexer.getToken()
            elif t == '-':
                var.add(t)
                t = self.lexer.getToken()
            if tokenIsFloat(t):
                var.add(t)
                t = self.lexer.getToken()
            if t in ['X','Y','Z','U','V','W','A','B','C']:
                var.add(t)
            elif first:
                raise ParserError("Expected axis definition, got: %s" % t, t)
            else:
                self.lexer.putToken(t)
                going = False
            first = False

class PmacLexer(object):
    tokens = ['!', '@', '#', '##', '$', '$$', '$$$', '$$$***', '$$*', '$*', '%', '&',
        '\\', '<', '>', '/', '?', '??', '???', 'A', 'ABR', 'ABS', 'X', 'Y', 'Z', 'U', 'V',
        'W', 'B', 'C', 'CHECKSUM', 'CID', 'CLEAR', 'ALL', 'PLCS', 'CLOSE', 'CPU', 'DATE',
        'DEFINE', 'BLCOMP', 'CCBUF', 'COMP', 'GATHER', 'LOOKAHEAD', 'ROTARY', 'TBUF', 'TCOMP', 'TRACE',
        'UBUFFER', 'DELETE', 'TEMPS', 'PLCC', 'DISABLE', 'PLC', 'EAVERSION', 'ENABLE', 'ENDGATHER',
        'F', 'FRAX', 'H', 'HOME', 'HOMEZ', 'I', '=', '*', '@', 'IDC', 'IDNUMBER', 'INC',
        'J', '+', '-', ':', '==', '^', 'K', 'LEARN', 'LIST', 'DEF', 'FORWARD', 'INVERSE',
        'LDS', 'LINK', 'PC', 'PE', 'PROGRAM', 'LOCK', ',', 'P', 'M', '->', 'D', 'DP', 'L', 'TWB',
        'TWD', 'TWR', 'TWS', 'MACROASCII', 'MACROAUX', 'MACROAUXREAD', 'MACROAUXWRITE', 
        'MACROMST', 'MACROMSTASCII', 'MACROMSTREAD', 'MACROMSTWRITE', 'MS', 'MSR',
        'MSW', 'MACROSTASCII', 'MFLUSH', 'MOVETIME', 'NOFRAX', 'NORMAL', 'O', 'OPEN',
        'BINARY', 'PASSWORD', 'PAUSE', 'PC', 'PE', 'PMATCH', 'PR', 'Q', 'R', 'RH', 'RESUME',
        'S', 'SAVE', 'SETPHASE', 'SID', 'SIZE', 'STN', 'TIME', 'TODAY', 'TYPE', 'UNDEFINE',
        'UNLOCK', 'UPDATE', 'VERSION', 'VID', 'ADDRESS', 'ADIS', 'AND', 'AROT', 'BLOCKSTART',
        'BLOCKSTOP', 'CALL', 'CC0', 'CC1', 'CC2', 'CC3', 'CCR', 'CIRCLE1', 'CIRCLE2',
        'COMMAND', 'COMMANDS', 'COMMANDP', 'COMMANDR', 'COMMANDA', 'DELAY', 'DISPLAY', 
        'DWELL', 'ELSE', 'ENDIF', 'ENDWHILE', 'F', 'FRAX', 'G', 'GOSUB', 'GOTO', 'IDIS', 
        'IF', 'IROT', 'LINEAR', 'LOCK', 'N', 'NX', 'NY', 'NZ', 'OR', 'PRELUDE', 'PSET',
        'PVT', 'RAPID', 'RETURN', 'SENDS', 'SENDP', 'SENDR', 'SENDA', 'SETPHASE', 'SPLINE1',
        'SPLINE2', 'STOP', 'T', 'TA', 'TINIT', 'TM', 'TR', 'TS', 'TSELECT', 'TX', 'TY', 'TZ',
        'UNLOCK', 'WAIT', 'WHILE', 'TRIGGER', '(', ')', '|', '..', '[', ']', 'END', 'READ',
        'E', 'ACOS', 'ASIN', 'ATAN', 'ATAN2', 'COS', 'EXP', 'INT', 'LN', 'SIN', 'SQRT', 'TAN', '~']
    shortTokens = {'CHKS':'CHECKSUM', 'CLR':'CLEAR', 'CLS':'CLOSE', 'DAT':'DATE', 'DEF':'DEFINE',
        'GAT':'GATHER', 'LOOK':'LOOKAHEAD', 'ENDI':'ENDIF', 'ROT':'ROTARY', 'UBUF':'UBUFFER',
        'DEL':'DELETE', 'TEMP':'TEMPS', 'DIS':'DISABLE', 'EAVER':'EAVERSION', 'ENA':'ENABLE',
        'ENDG':'ENDGATHER', 'TRIG':'TRIGGER', 'HM':'HOME', 'HMZ':'HOMEZ', 'LIS':'LIST',
        'FWD':'FORWARD', 'INV':'INVERSE', 'PROG':'PROGRAM', 'MX':'MACROAUX', 'MXR':'MACROAUXREAD',
        'MXW':'MACROAUXWRITE', 'MM':'MACROMST', 'MACMA':'MACROMSTASCII', 'MMR':'MACROMSTREAD',
        'MMW':'MACROMSTWRITE', 'MACROSLV':'MS', 'MACROSLVREAD':'MSR', 'MACROSLVWRITE':'MSW',
        'MACSTA':'MACROSTASCII', 'MVTM':'MOVETIME', 'NRM':'NORMAL', 'BIN':'BINARY', 'PAU':'PAUSE',
        'RES':'RESUME', 'UNDEF':'UNDEFINE', 'VER':'VERSION', 'ADR':'ADDRESS', 'BSTART':'BLOCKSTART',
        'BSTOP':'BLOCKSTOP', 'CIR1':'CIRCLE1', 'CIR2':'CIRCLE2', 'CMD':'COMMAND',
        'CMDS':'COMMANDS', 'CMDP':'COMMANDP', 'CMDR':'COMMANDR', 'CMDA':'COMMANDA', 'DLY':'DELAY',
        'DWE':'DWELL', 'ENDW':'ENDWHILE', 'LIN':'LINEAR', 'RPD':'RAPID',
        'RET':'RETURN', 'TSEL':'TSELECT', 'MI':'I'}
    tokenPairs = {'END WHILE':'ENDWHILE', 'END IF':'ENDIF', 'END GATHER':'ENDGATHER'}
    def __init__(self, source, debug=False):
        self.tokens = []
        self.curToken = ''
        self.matchToken = None
        self.line = 0
        self.fileName = ''
        self.debug = debug
        hasDebugInfo = False
        lastToken = None
        # Process every line...
        for line in source:
            if not hasDebugInfo:
                self.line += 1
            if line.startswith(';#*'):
                # Debug information
                hasDebugInfo = True
                parts = line.split()
                self.fileName = parts[1]
                self.line = int(parts[2])
            else:
                # Strip comments from the ends of lines
                line = line.split(';', 1)[0].strip().upper()
                while len(line) > 0:
                    token = self.findToken(line)
                    t = PmacToken()
                    t.set(self.expandToken(token), self.fileName, self.line)
                    # Replace token pairs with the single corresponding token
                    if lastToken is not None:
                        pair = '%s %s' % (lastToken, t)
                        if pair in self.tokenPairs:
                            self.tokens[-1].set(self.tokenPairs[pair], self.fileName, self.line)
                            lastToken = None
                        else:
                            self.tokens.append(t)
                            lastToken = t
                    else:
                        self.tokens.append(t)
                        lastToken = t
                    line = line[len(token):].lstrip()
                t = PmacToken()
                t.set('\n', self.fileName, self.line)
                self.tokens.append(t)
    def findToken(self, text):
        '''Find the longest token at the start of the text.'''
        bestToken = ''
        # Try for a (possibly real) number
        if text[0].isdigit():
            isNumber = True
            hasDot = False
            pos = 0
            curToken = ''
            while pos < len(text) and isNumber:
                ch = text[pos]
                if ch.isdigit():
                    curToken += ch
                elif not hasDot and ch == '.':
                    hasDot = True
                    curToken += ch
                else:
                    isNumber = False
                pos += 1
            if len(curToken) > 0 and curToken[-1] == '.':
                # Float cannot have a trailing dot
                curToken = curToken[:-1]
            bestToken = curToken
        # Try for a hexadecimal number (also catches the single $ token)
        elif text[0] == '$':
            pos = 1
            curToken = '$'
            isNumber = True
            while pos < len(text) and isNumber:
                ch = text[pos]
                if ch in '0123456789ABCDEF':
                    curToken += ch
                else:
                    isNumber = False
                pos += 1
            bestToken = curToken
        # Try for a literal string
        elif text[0] == '"':
            curToken = '"'
            pos = 1
            noTerminator = True
            while pos<len(text) and noTerminator:
                ch = text[pos]
                curToken += ch
                if ch == '"':
                    noTerminator = False
                pos += 1
            if noTerminator:
                raise LexerError(line, self.fileName, self.line)
            else:
                bestToken = curToken
        else:
            # Try the tokens in the normal list
            for t in PmacLexer.tokens:
                if len(t) > len(bestToken) and text.startswith(t):
                    bestToken = t
            # Try the tokens in the short dictionary
            for t,f in PmacLexer.shortTokens.iteritems():
                if len(t) > len(bestToken) and text.startswith(t):
                    bestToken = t
        if len(bestToken) == 0:
            raise LexerError(text, self.fileName, self.line)
        if self.debug:
            print '{%s from %s}' % (bestToken, text)
        return bestToken
    def expandToken(self, token):
        '''If the token is a short form, it is expanded to the full form.'''
        result = token
        if token in PmacLexer.shortTokens:
            result = PmacLexer.shortTokens[token]
        return result
    def getToken(self, shouldBe=None, wantEol=False):
        '''Returns the first token and removes it from the list.'''
        result = None
        # Skip any newline tokens unless they are wanted
        while not wantEol and len(self.tokens) > 0 and self.tokens[0] == '\n':
            self.line += 1
            self.tokens[:1] = []
        # Get the head token
        if len(self.tokens) > 0:
            result = self.tokens[0]
            self.tokens[:1] = []
        # Is it the expected one
        if shouldBe is not None and not shouldBe == result:
            raise ParserError('Expected %s, got %s' % (shouldBe, result), result)
        #print "{%s:%s}" % (repr(result), self.line)
        return result
    def putToken(self, token):
        '''Puts a token at the head of the list.'''
        self.tokens[:0] = [token]

def main():
    '''Main entry point of the script.'''
    config = GlobalConfig()
    if config.processArguments():
        config.processConfigFile()
        config.analyse()
    else:
        print helpText
    return 0

if __name__ == '__main__':
    sys.exit(main())


