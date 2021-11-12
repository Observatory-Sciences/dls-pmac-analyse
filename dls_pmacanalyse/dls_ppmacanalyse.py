import dls_pmacremote
from scp import SCPClient
import time
import re
import warnings
import os
import numpy as np
import logging
import difflib
import argparse

def timer(func):
    def measureExecutionTime(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        print("Processing time of %s(): %.2f seconds." % (func.__qualname__, time.time() - startTime))
        return result
    return measureExecutionTime

def createEmptyDir(dir):
    if dir[0] == '/':
        if os.environ['PWD'] not in dir:
            raise IOError(f"Unable to delete directory {dir} as it is not in PWD")
    os.system(f'rm -rf {dir}')
    os.mkdir(dir)

def removeFile(file):
    if file[0] == '/':
        if os.environ['PWD'] not in file:
            raise IOError(f"Unable to delete directory {file} as it is not in PWD")
    os.system(f'rm -rf {file}')

def parseArgs():
    parser = argparse.ArgumentParser(description="Interact with a Power PMAC")
    parser.add_argument('-i', '--interface', nargs=1, help='Network interface address of Power PMAC <ip>:<port>')
    parser.add_argument('-b', '--backup', nargs='*', help='Back-up configuration of Power PMAC')
    parser.add_argument('-r', '--restore', nargs='*', help='Restore configuration of Power PMAC')
    parser.add_argument('-c', '--compare', nargs='*', help='Compare configuration of two Power PMACs')
    parser.add_argument('-d', '--resultsdir', nargs='*', help='Directory in which to place output of analysis')
    parser.add_argument('-v', '--verbosity', nargs=1, help='Verbosity level of output')
    parser.add_argument('-n', '--name', nargs=1, help='Name of Power PMAC')
    return parser.parse_args()


def exitGpascii():
    (exitGpascii, status) = sshClient.sendCommand('\x03')
    if not status:
        raise IOError("Failed to exit gpascii.")


def scpFromPowerPMACtoLocal(source, destination, recursive):
    try:
        scp = SCPClient(sshClient.client.get_transport())
        scp.get(source, destination, recursive)
        scp.close()
    except Exception as e:
        print(f"Error: {e}, unable to get directory from remote host: {source}")


def scpFromLocalToPowerPMAC(files, remote_path, recursive=False):
    try:
        scp = SCPClient(sshClient.client.get_transport())
        scp.put(files, remote_path, recursive)
        scp.close()
    except Exception as e:
        print(f"Error: {e}, unable to copy files {files} to remote path: {remote_path}")


def nthRepl(s, sub, repl, nth):
    find = s.find(sub)
    i = find != -1
    while find != -1 and i != nth:
        find = s.find(sub, find + 1)
        i += 1
    if i == nth:
        return s[:find] + repl + s[find + len(sub):]
    return s


def find_nth(s, sub, n):
    start = s.find(sub)
    while start >= 0 and n > 1:
        start = s.find(sub, start + len(sub))
        n -= 1
    return start


def responseListToDict(responseList, splitChars='='):
    responseDict = {}
    if responseList != ['', '']:
        for element in responseList:
            nameVal = element.split(splitChars)
            responseDict[nameVal[0]] = nameVal[1]
    return responseDict

class PPMACProject(object):
    """
    Class containing files and directories included in a project
    """
    class Directory(object):
        def __init__(self, path, files):
            self.path = path
            #self.subdirs = {}  # dict of directory objects
            self.files = files  # dict of files

    class File(object):
        def __init__(self, name, dir, proj):
            self.name = name
            self.dir = dir  # directory object
            filePath = f'{dir}/{name}'
            self.extension = os.path.splitext(filePath)[1]
            self.contents = proj.getFileContents(filePath)
            self.sha256 = None  # calculate sha256sum of file

    def __init__(self, source, root):
        # absolute path the project directory
        self.root = root
        # Source of project (hardware or repo)
        self.source = source
        # Dictionary of files contained in the project
        self.files = {}
        # Dictionary of directories contained in the project
        self.dirs = {}
        if self.source == 'hardware':
            if root.find('usrflash') == -1:
                raise RuntimeError(f'Root directory "{root}" invalid: not a project directory.')
            self.root = f'tmp/hardware{root}'
            os.system(f'rm -rf tmp/hardware')
            os.makedirs(self.root[0:self.root.rfind('/')])
            scpFromPowerPMACtoLocal(source=root, destination=self.root, recursive=True)
        elif self.source != 'repository':
            raise RuntimeError('Invalid project source: should be "hardware" or "repository".')
        self.buildProjectTree(self.root)

    def buildProjectTree(self, start):
        for root, dirs, files in os.walk(start):
            root_ = root.replace(start, '', 1)
            for name in dirs:
                dirName = os.path.join(root_, name)
                self.dirs[dirName] = self.Directory(dirName, files)
            for name in files:
                fileName = os.path.join(root_, name)
                self.files[fileName] = self.File(name, root_, self)

    def getFileContents(self, file):
        contents = []
        file = f'{self.root}/{file}'
        with open(file, 'r', encoding='ISO-8859-1') as readFile:
            for line in readFile:
                contents.append(line)
        return contents


class ProjectCompare(object):
    """
    Compare two project filesystems
    """
    class FileDiffs(object):
        """
        Object holding the differences between two project files
        """
        def __init__(self, fileA, fileB):
            self.fileA = fileA
            self.fileB = fileB
            self.same = (fileA.sha256 == fileB.sha256)
            # plus some object to hold the line-by-line differences

    def __init__(self, projectA, projectB, ignore=None):
        self.projectA = projectA
        self.projectB = projectB
        self.filesOnlyInA = {}
        self.filesOnlyInB = {}
        self.filesInAandB = {}

    def setProjectA(self, project):
        self.projectA = project

    def setprojectB(self, project):
        self.projectB = project

    def compareProjectFiles(self):
        fileNamesA = set(self.projectA.files.keys())
        fileNamesB = set(self.projectB.files.keys())
        fileNamesOnlyInA = fileNamesA - fileNamesB
        fileNamesOnlyInB = fileNamesB - fileNamesA
        fileNamesInAandB = fileNamesA & fileNamesB
        self.filesOnlyInA = self.filesOnlyInB = {}
        self.filesOnlyInA = {fileName: self.projectA.files[fileName] for fileName in fileNamesOnlyInA}
        self.filesOnlyInB = {fileName: self.projectB.files[fileName] for fileName in fileNamesOnlyInB}
        for fileName in fileNamesInAandB:
            self.filesInAandB[fileName] = {'A': self.projectA.files[fileName], 'B': self.projectB.files[fileName]}
        with open('compare/Project/Project.diff', 'w+') as projCompFile:
            projCompFile.write(f'@@ Project files in source \'{self.projectA.source}\' but not source '
                               f'\'{self.projectB.source}\' @@\n')
            for projFileName in fileNamesOnlyInA:
                projCompFile.write(f'>> {projFileName}\n')
            projCompFile.write(f'@@ Project files in source \'{self.projectB.source}\' but not source '
                               f'\'{self.projectA.source}\' @@\n')
            for projFileName in fileNamesOnlyInB:
                projCompFile.write(f'>> {projFileName}\n')
            projCompFile.write(f'@@ Project files in source \'{self.projectB.source}\' and source '
                               f'\'{self.projectA.source}\' with different contents @@\n')
            for projFileName in fileNamesInAandB:
                print(projFileName)
                projCompFile.writelines(difflib.unified_diff(projectA.files[projFileName].contents,
                                                        projectB.files[projFileName].contents,
                                                        fromfile=f'{projectA.source}: {projFileName}',
                                                        tofile=f'{projectB.source}: {projFileName}',
                                                        lineterm='\n'))


class PPMACCompare(object):
    """
    Compare two PowerPMAC objects
    """
    def __init__(self, ppmacA, ppmacB):
        self.ppmacInstanceA = ppmacA
        self.ppmacInstanceB = ppmacB
        # Set of element names only in A
        self.elemNamesOnlyInA = {}
        # Set of element names only in B
        self.elemNamesOnlyInB = {}
        # Set of element names in both A and B
        self.elemNamesInAandB = {}
        # Dictionary of active elements only in A. Keys refer to the active elem names, the values are
        # PowerPMAC.activeElement objects.
        self.activeElemsOnlyInA = {}
        # Dictionary of active elements only in B. Keys refer to the active elem names, the values are
        # PowerPMAC.activeElement objects.
        self.activeElemsOnlyInB = {}
        # A nested dictionary. The outer keys refer to the active elem names, the inner keys refer to ppmac
        # instance (A or B), the values are PowerPMAC.activeElement objects.
        self.activeElemsInAandB = {}

    def setPPMACInstanceA(self, ppmacA):
        self.ppmacInstanceA = ppmacA

    def setPPMACInstanceB(self, ppmacB):
        self.ppmacInstanceB = ppmacB

    def compareActiveElements(self):
        elementNamesA = set(self.ppmacInstanceA.activeElements.keys())
        elementNamesB = set(self.ppmacInstanceB.activeElements.keys())
        self.elemNamesOnlyInA = elementNamesA - elementNamesB
        self.elemNamesOnlyInB = elementNamesB - elementNamesA
        self.elemNamesInAandB = elementNamesA & elementNamesB
        self.activeElemsOnlyInA = {elemName: self.ppmacInstanceA.activeElements[elemName]
                                   for elemName in self.elemNamesOnlyInA}
        self.activeElemsOnlyInB = {elemName: self.ppmacInstanceB.activeElements[elemName]
                                   for elemName in self.elemNamesOnlyInB}
        for elemName in self.elemNamesInAandB:
            self.activeElemsInAandB[elemName] = {'A':self.ppmacInstanceA.activeElements[elemName],
                                                 'B':self.ppmacInstanceB.activeElements[elemName]}
        self.writeActiveElemDifferencesToFile()

    def writeActiveElemDifferencesToFile(self):
        dataStructCategoriesInA = set([elem.category for elem in list(self.ppmacInstanceA.activeElements.values())])
        dataStructCategoriesInB = set([elem.category for elem in list(self.ppmacInstanceB.activeElements.values())])
        filePrefixes = dataStructCategoriesInA.union(dataStructCategoriesInB)
        filePaths = ['compare/' + prefix + '.diff' for prefix in filePrefixes]
        diffFiles = {}
        try:
            sourceA = self.ppmacInstanceA.source
            sourceB = self.ppmacInstanceB.source
            for file in filePaths:
                diffFiles[file] = open(file, 'w+')
            print(diffFiles)
            # write first set of headers
            for file in diffFiles:
                diffFiles[file].write(f'@@ Active elements in source \'{sourceA}\' but not source \'{sourceB}\' @@\n')
            # write to file elements that are in ppmacA but not ppmacB
            for elemName in self.elemNamesOnlyInA:
                file = f'compare/{self.activeElemsOnlyInA[elemName].category}.diff'
                diffFiles[file].write('>> ' + self.activeElemsOnlyInA[elemName].name + ' = '
                                      + self.activeElemsOnlyInA[elemName].value + '\n')
            # write second set of headers
            for file in diffFiles:
                diffFiles[file].write(f'@@ Active elements in source \'{sourceB}\' but not source \'{sourceA}\' @@\n')
            # write to file elements that are in ppmacB but not ppmacA
            for elemName in self.elemNamesOnlyInB:
                file = f'compare/{self.activeElemsOnlyInB[elemName].category}.diff'
                diffFiles[file].write('>> ' + self.activeElemsOnlyInB[elemName].name + ' = '
                                      + self.activeElemsOnlyInB[elemName].value + '\n')
            # write to file elements that in ppmacB but not ppmacA but whose values differ
            for file in diffFiles:
                diffFiles[file].write(f'@@ Active elements in source \'{sourceA}\' and source \'{sourceB}\' with '
                                      f'different values @@\n')
            for elemName in self.elemNamesInAandB:
                valA = self.activeElemsInAandB[elemName]['A'].value
                valB = self.activeElemsInAandB[elemName]['B'].value
                if valA != valB:
                    file = 'compare/' + self.ppmacInstanceA.activeElements[elemName].category + '.diff'
                    diffFiles[file].write(f'@@ {elemName} @@\n{self.ppmacInstanceA.source} value >> {valA}\n'
                          f'{self.ppmacInstanceB.source} value >> {valB}\n')
        finally:
            for file in diffFiles:
                diffFiles[file].close()


class PPMACRepositoryWriteRead(object):
    def __init__(self, ppmac=None, repositoryPath='repository'):
        self.ppmacInstance = ppmac
        # source - will be set somewhere else
        if self.ppmacInstance.source == 'unknown':
            self.ppmacInstance.source = 'repository'
        self.repositoryPath = repositoryPath #os.environ['PWD'] + '/repository'

    def setPPMACInstance(self, ppmac):
        self.ppmacInstance = ppmac
        if self.ppmacInstance.source == 'unknown':
            self.ppmacInstance.source = 'repository'

    def setRepositoryPath(self, path):
        self.repositoryPath = path

    def writeVars(self, vars, file):
        with open(file, 'w+') as writeFile:
            for var in vars:
                writeFile.write(var.__str__() + '\n')

    def writePvars(self):
        file = self.repositoryPath + '/Pvars.txt'
        self.writeVars(self.ppmacInstance.Pvariables, file)

    def writeIvars(self):
        file = self.repositoryPath + '/Ivars.txt'
        self.writeVars(self.ppmacInstance.Ivariables, file)

    def writeMvars(self):
        file = self.repositoryPath + '/Mvars.txt'
        self.writeVars(self.ppmacInstance.Mvariables, file)

    def writeQvars(self):
        for i in range(self.ppmacInstance.numberOfCoordSystems):
            file = self.repositoryPath + f'/Qvars_CS{i}.txt'
            self.writeVars(self.ppmacInstance.Qvariables[i], file)

    def writeActiveState(self):
        self.writeDataStructures()
        self.writeActiveElements()
        self.writeAllPrograms()

    def writeDataStructures(self):
        file = self.repositoryPath + '/dataStructures.txt'
        with open(file, 'w+') as writeFile:
            for dataStructure in self.ppmacInstance.dataStructures:
                writeFile.write(self.ppmacInstance.dataStructures[dataStructure].__str__() + '\n')

    def writeActiveElements(self):
        file = self.repositoryPath + '/activeElements.txt'
        with open(file, 'w+') as writeFile:
            for elem in self.ppmacInstance.activeElements:
                writeFile.write(self.ppmacInstance.activeElements[elem].__str__() + '\n')

    def writePrograms(self, ppmacProgs, progsDir):
        """
        Write contents of dictionary of PPMAC programs to files. Each dict key corresponds to separate file written.
        :param ppmacProgs: dictionary of programs.
        :return:
        """
        progNames = ppmacProgs.keys()
        for progName in progNames:
            fileName = progsDir + '/' + progName.replace('&', 'CS')
            with open(fileName, 'w+') as writeFile:
                writeFile.write(ppmacProgs[progName].printInfo())
                writeFile.write('\n'.join(ppmacProgs[progName].listing))

    def writeAllPrograms(self):
        progsDir = self.repositoryPath + '/programs'
        createEmptyDir(progsDir)
        self.writePrograms(self.ppmacInstance.motionPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.subPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.plcPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.forwardPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.inversePrograms, progsDir)

    def readAndStoreActiveElements(self):
        file = self.repositoryPath + '/activeElements.txt'
        with open(file, 'r') as readFile:
            for line in readFile:
                line = line.split()
                line = [item.strip() for item in line]
                key = line[0]
                value = line[0:] # need to deal with the list of indices which is tha last column(s)
                self.ppmacInstance.activeElements[key] = self.ppmacInstance.ActiveElement(*value[0:5])

    def readAndStoreBufferedPrograms(self):
        progsPath = self.repositoryPath + '/programs'
        progFileNames = [file for file in os.listdir(progsPath) if os.path.isfile(f'{progsPath}/{file}')]
        for fileName in progFileNames:
            fileName = f'{progsPath}/{fileName}'
            with open(fileName, 'r') as readFile:
                header = readFile.readline().split()
                header = [item.strip(',') for item in header]
                progType, progName, progSize, progOffset = (header[i] for i in [0, 1, 3, 5])
                progListing = []
                for line in readFile:
                    progListing.append(line.rstrip('\n'))
            if progType == 'Motion':
                self.ppmacInstance.motionPrograms[progName] = \
                    self.ppmacInstance.Program(progName, progOffset, progSize, progType, progListing)
            elif progType == 'SubProg':
                self.ppmacInstance.subPrograms[progName] = \
                    self.ppmacInstance.Program(progName, progOffset, progSize, progType, progListing)
            elif progType == 'PlcProg':
                self.ppmacInstance.plcPrograms[progName] = \
                    self.ppmacInstance.Program(progName, progOffset, progSize, progType, progListing)
            elif progType == 'Forward':
                progCoordSystem = header[7]
                self.ppmacInstance.forwardPrograms[progName] = \
                    self.ppmacInstance.KinematicTransform(progName, progSize, progOffset, progType,
                                                          progCoordSystem, progListing)
            elif progType == 'Inverse':
                progCoordSystem = header[7]
                self.ppmacInstance.inversePrograms[progName] = \
                    self.ppmacInstance.KinematicTransform(progName, progSize, progOffset, progType,
                                                          progCoordSystem, progListing)


class PPMACHardwareWriteRead(object):
    def __init__(self, ppmac=None):
        self.ppmacInstance = ppmac
        # Set PPMAC source to hardware
        if self.ppmacInstance.source == 'unknown':
            self.ppmacInstance.source = 'hardware'
        # Path to directory containing symbols tables files on PPMAC
        self.remote_db_path = '/var/ftp/usrflash/Database'
        # Path to directory containing symbols tables files on local
        self.local_db_path = './tmp/Database'
        # File containing list of all base Data Structures
        self.pp_swtbl0_txtfile = 'pp_swtbl0.txt'
        # Standard Data Structure symbols tables
        self.pp_swtlbs_symfiles = ['pp_swtbl1.sym', 'pp_swtbl2.sym', 'pp_swtbl3.sym']
        # Read maximum values for the various configuration parameters
        self.readSysMaxes

    def setPPMACInstance(self, ppmac):
        self.ppmacInstance = ppmac
        if self.ppmacInstance.source == 'unknown':
            self.ppmacInstance.source = 'hardware'

    def getCommandReturnInt(self, cmd):
        (cmdReturn, status) = sshClient.sendCommand(cmd)
        print('here')
        if status:
            cmdReturnInt = int(cmdReturn[0:])
        else:
            raise IOError("Cannot retrieve variable value: error communicating with PMAC")
        return cmdReturnInt

    def readSysMaxes(self):
        if self.ppmacInstance == None:
            raise RuntimeError('No Power PMAC object has been specified')
        # number of active motors
        self.ppmacInstance.numberOfMotors = self.getCommandReturnInt('Sys.MaxMotors')
        # number of active coordinate systems
        self.ppmacInstance.numberOfCoordSystems = self.getCommandReturnInt('Sys.MaxCoords')
        # number of active compensation tables.
        self.ppmacInstance.numberOfCompTables = self.getCommandReturnInt('Sys.CompEnable')
        # number of active cam tables
        self.ppmacInstance.numberOfCamTables = self.getCommandReturnInt('Sys.CamEnable')
        # number EtherCAT networks that can be enabled
        self.ppmacInstance.numberOfECATs = self.getCommandReturnInt('Sys.MaxEcats')
        # Number of available encoder tables
        self.ppmacInstance.numberOfEncTables = self.getCommandReturnInt('Sys.MaxEncoders')

    def sendCommand(self, cmd):
        start = time.time()
        (data, status) = sshClient.sendCommand(cmd)
        tdiff = time.time() - start
        if not status:
            raise IOError('Cannot retrieve data structure: error communicating with PMAC')
        else:
            data = data.split("\r")[:-1]
            # print(data)
        # if 'error' in data[0]:
        #    errMessage = 'Error reading data.'
        #    raise IOError(errMessage + data[0])
        return data

    def swtblFileToList(self, pp_swtbl_file):
        """
        Generate a list of symbols from a symbols table file.
        :param pp_swtbl_file: full path to symbols table file.
        :return: swtbl_DSs: list of symbols, where each 'symbol' is represented by the contents of one row of the
        symbols table file.
        """
        try:
            file = open(file=pp_swtbl_file, mode="r", encoding='ISO-8859-1')
            multi_line = ''
            symbols = []
            for line in file:
                multi_line_ = multi_line
                if line[-2:] == '\\\n':
                    multi_line += line
                else:
                    line = multi_line_ + line
                    symbol = line.split('\x01')
                    symbol = [col.strip() for col in symbol]
                    multi_line = ''
                    symbols.append(symbol)
            file.close()
        except IOError as e:
            print(e)
        return symbols

    def getDataStructureCategory(self, dataStructure):
        if dataStructure.find('.') == -1:
            dataStructureCategory = dataStructure
        else:
            dataStructureCategory = dataStructure[0:dataStructure.find('.')]
        return dataStructureCategory.replace('[]','')

    def ignoreDataStructure(self, substructure, elementsToIgnore):
        """
        Determine whether a data structure or substructure should be ignored by checking if it or any of its parent,
        grandparent, great-grandparent etc. structures are included in the ignore list.
        :param substructure: name of data structure or substructure to check
        :return: True if data structure or substructure should be ignored, False otherwise
        """
        n = substructure.count('.')
        for _ in range(n + 1):
            # print('Checking if the following structure is in the ignore list: ' + substructure)
            if substructure in elementsToIgnore:
                # print('Ignoring data structure')
                return True
            substructure = substructure[0:substructure.rfind('.')]
        return False

    def fillDataStructureIndices_i(self, dataStructure, activeElements, elementsToIgnore, timeout=None):
        """
        Incrementally increase the index of a singly-indexed data structure and send the resulting command to the ppmac
        until the maximum accepted index is reached. Add the command string and return value of all commands accepted by
        the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active elements, where the key is the element
        name, and the value is a tuple containing the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        cmd_accepted = True
        while cmd_accepted:
            i_idex_string = f'[{i}]'
            dataStructure_i = dataStructure.replace('[]', i_idex_string)
            if self.ignoreDataStructure(dataStructure_i.replace(i_idex_string, f'[{i}:]'), elementsToIgnore):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                i += 1
                continue
            print(dataStructure_i)
            cmd_return = self.sendCommand(dataStructure_i)
            print(cmd_return)
            if 'ILLEGAL' in cmd_return[0]:
                cmd_accepted = False
            else:
                activeElements[dataStructure_i] = (dataStructure_i, cmd_return[0], dataStructureCategory,
                                                   dataStructure, [i])
            if applyTimeout and time.time() - startTime > timeout:
                logging.info(f'Timed-out generating active elements for {dataStructure}. '
                             f'Last i = {i}.')
                return
            i += 1
        # print(activeElements)

    def fillDataStructureIndices_ij(self, dataStructure, activeElements, elementsToIgnore, timeout=None):
        """
        Incrementally increase the indices of a doubly-indexed data structure and send the resulting command to the ppmac
        until the maximum accepted indices are reached. Add the command string and return value of all commands accepted by
        the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active elements, where the key is the element
        name, and the value is a tuple containing the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        while cmd_accepted:
            j = 0
            i_idex_string = f'[{i}]'
            dataStructure_i = nthRepl(dataStructure, '[]', i_idex_string, 1)
            if self.ignoreDataStructure(dataStructure_i.replace(i_idex_string, f'[{i}:]'), elementsToIgnore):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                last_i_accepted = i
                i += 1
                continue
            while cmd_accepted:
                j_idex_string = f'[{j}]'
                dataStructure_ij = nthRepl(dataStructure_i, '[]', j_idex_string, 1)
                if self.ignoreDataStructure(dataStructure_ij.replace(f'[{i}]', '[]', 1).replace(
                        j_idex_string, f'[{j}:]', 1), elementsToIgnore):
                    break
                if self.ignoreDataStructure(dataStructure_ij.replace(f'[{i}]', '[]', 1), elementsToIgnore):
                    j += 1
                    continue
                print(dataStructure_ij)
                cmd_return = self.sendCommand(dataStructure_ij)
                print(cmd_return)
                if 'ILLEGAL' in cmd_return[0]:
                    cmd_accepted = False
                else:
                    last_i_accepted = i
                    activeElements[dataStructure_ij] = (dataStructure_ij, cmd_return[0],
                                                        dataStructureCategory, dataStructure, [i, j])
                if applyTimeout and time.time() - startTime > timeout:
                    logging.info(f'Timed-out generating active elements for {dataStructure}. '
                                 f'Last i,j = {i},{j}.')
                    return
                j += 1
            cmd_accepted = True
            # print(last_i_accepted, i)
            if i - last_i_accepted > 1:
                cmd_accepted = False
            # print(cmd_accepted)
            i += 1
        # print(activeElements)

    def fillDataStructureIndices_ijk(self, dataStructure, activeElements, elementsToIgnore, timeout=None):
        """
        Incrementally increase the indices of a triply-indexed data structure and send the resulting command to the ppmac
        until the maximum accepted indices are reached. Add the command string and return value of all commands accepted by
        the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active elements, where the key is the element
        name, and the value is a tuple containing the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        print(dataStructure)
        while cmd_accepted:
            j = 0
            last_j_accepted = j
            i_idex_string = f'[{i}]'
            dataStructure_i = nthRepl(dataStructure, '[]', i_idex_string, 1)
            if self.ignoreDataStructure(dataStructure_i.replace(i_idex_string, f'[{i}:]'), elementsToIgnore):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                last_i_accepted = i
                i += 1
                continue
            #    break
            while cmd_accepted:
                k = 0
                j_idex_string = f'[{j}]'
                dataStructure_ij = nthRepl(dataStructure_i, '[]', j_idex_string, 1)
                if self.ignoreDataStructure(dataStructure_ij.replace(f'[{i}]', '[]', 1).replace(
                        j_idex_string, f'[{j}:]', 1), elementsToIgnore):
                    break
                if self.ignoreDataStructure(dataStructure_ij.replace(f'[{i}]', '[]', 1), elementsToIgnore):
                    last_j_accepted = j
                    j += 1
                    continue
                #    break
                while cmd_accepted:
                    k_idex_string = f'[{k}]'
                    dataStructure_ijk = nthRepl(dataStructure_ij, '[]', k_idex_string, 1)
                    if self.ignoreDataStructure(dataStructure_ijk.replace(
                            f'[{i}]', '[]', 1).replace(f'[{j}]', '[]', 1).replace(
                        k_idex_string, f'[{k}:]', 1), elementsToIgnore):
                        break
                    if self.ignoreDataStructure(dataStructure_ijk.replace(
                            f'[{i}]', '[]', 1).replace(f'[{j}]', '[]', 1), elementsToIgnore):
                        #    break
                        k += 1
                        continue
                    print(dataStructure_ijk)
                    cmd_return = self.sendCommand(dataStructure_ijk)
                    print(cmd_return)
                    if 'ILLEGAL' in cmd_return[0]:
                        cmd_accepted = False
                    else:
                        last_j_accepted = j
                        last_i_accepted = i
                        activeElements[dataStructure_ijk] = (dataStructure_ijk, cmd_return[0],
                                                             dataStructureCategory, dataStructure, [i, j, k])
                    if applyTimeout and time.time() - startTime > timeout:
                        logging.info(f'Timed-out generating active elements for {dataStructure}. '
                                     f'Last i,j,k = {i},{j},{k}.')
                        return
                    k += 1
                cmd_accepted = True
                if j - last_j_accepted > 1:
                    cmd_accepted = False
                j += 1
            cmd_accepted = True
            if i - last_i_accepted > 1:
                cmd_accepted = False
            i += 1
        # print(activeElements)

    def fillDataStructureIndices_ijkl(self, dataStructure, activeElements, elementsToIgnore, timeout=None):
        """
        Incrementally increase the indices of a quadruply-indexed data structure and send the resulting command to the ppmac
        until the maximum accepted indices are reached. Add the command string and return value of all commands accepted by
        the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active elements, where the key is the element
        name, and the value is a tuple containing the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        while cmd_accepted:
            j = 0
            last_j_accepted = j
            i_idex_string = f'[{i}]'
            dataStructure_i = nthRepl(dataStructure, '[]', i_idex_string, 1)
            # if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
            #    break
            if self.ignoreDataStructure(dataStructure_i.replace(i_idex_string, f'[{i}:]'), elementsToIgnore):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                last_i_accepted = i
                i += 1
                continue
            while cmd_accepted:
                k = 0
                last_k_accepted = k
                j_idex_string = f'[{j}]'
                dataStructure_ij = nthRepl(dataStructure_i, '[]', j_idex_string, 1)
                if self.ignoreDataStructure(dataStructure_ij.replace(f'[{i}]', '[]', 1).replace(
                        j_idex_string, f'[{j}:]', 1), elementsToIgnore):
                    break
                if self.ignoreDataStructure(dataStructure_ij.replace(f'[{i}]', '[]', 1), elementsToIgnore):
                    last_j_accepted = j
                    j += 1
                    continue
                while cmd_accepted:
                    l = 0
                    k_idex_string = f'[{k}]'
                    dataStructure_ijk = nthRepl(dataStructure_ij, '[]', k_idex_string, 1)
                    if self.ignoreDataStructure(dataStructure_ijk.replace(
                            f'[{i}]', '[]', 1).replace(f'[{j}]', '[]', 1).replace(
                        k_idex_string, f'[{k}:]', 1), elementsToIgnore):
                        break
                    if self.ignoreDataStructure(dataStructure_ijk.replace(
                            f'[{i}]', '[]', 1).replace(f'[{j}]', '[]', 1), elementsToIgnore):
                        #    break
                        last_k_accepted = k
                        k += 1
                        continue
                    while cmd_accepted:
                        l_idex_string = f'[{l}]'
                        dataStructure_ijkl = nthRepl(dataStructure_ijk, '[]', l_idex_string, 1)
                        if self.ignoreDataStructure(dataStructure_ijkl.replace(f'[{i}]', '[]', 1).replace(
                                f'[{j}]', '[]', 1).replace(f'[{k}]', '[]', 1).replace(
                            l_idex_string, f'[{l}:]', 1), elementsToIgnore):
                            break
                        if self.ignoreDataStructure(dataStructure_ijkl.replace(f'[{i}]', '[]', 1).replace(
                                f'[{j}]', '[]', 1).replace(f'[{k}]', '[]', 1), elementsToIgnore):
                            l += 1
                            continue
                        print(dataStructure_ijkl)
                        cmd_return = self.sendCommand(dataStructure_ijkl)
                        print(cmd_return)
                        if 'ILLEGAL' in cmd_return[0]:
                            cmd_accepted = False
                        else:
                            last_k_accepted = k
                            last_j_accepted = j
                            last_i_accepted = i
                            activeElements[dataStructure_ijkl] = (dataStructure_ijkl, cmd_return[0],
                                                                  dataStructureCategory, dataStructure, [i, j, k, l])
                        if applyTimeout and time.time() - startTime > timeout:
                            logging.info(f'Timed-out generating active elements for {dataStructure}. '
                                         f'Last i,j,k,l = {i},{j},{k},{l}.')
                            return
                        l += 1
                    cmd_accepted = True
                    if k - last_k_accepted > 1:
                        cmd_accepted = False
                    k += 1
                cmd_accepted = True
                if j - last_j_accepted > 1:
                    cmd_accepted = False
                j += 1
            cmd_accepted = True
            if i - last_i_accepted > 1:
                cmd_accepted = False
            i += 1
        # print(activeElements)

    def scpPPMACDatabaseToLocal(self, remote_db_path, local_db_path):
        if not os.path.isdir(local_db_path):
            os.system('mkdir ' + local_db_path)
        scpFromPowerPMACtoLocal(source=remote_db_path, destination=local_db_path, recursive=True)

    def createDataStructuresFromSymbolsTables(self, pp_swtlbs_symfiles, local_db_path):
        """
        Read the symbols tables and create a list of data structure names contained within them.
        :return: dataStructures: list of data structure names
        """
        # Clear current data structure dictionary
        dataStructures = {}
        # swtbl0 = []
        # with open(self.local_db_path + '/' + self.pp_swtbl0_txtfile, 'r') as readFile:
        #    for line in readFile:
        #        swtbl0.append(line.replace('\n',''))
        pp_swtbls = []
        for pp_swtbl_file in pp_swtlbs_symfiles:
            pp_swtbls.append(self.swtblFileToList(local_db_path + '/' + pp_swtbl_file))
        swtbl1_nparray = np.asarray(pp_swtbls[0])
        swtbl2_nparray = np.asarray(pp_swtbls[1])
        swtbl3_nparray = np.asarray(pp_swtbls[2])
        with open('active/dataStructures.txt', 'w+') as writeFile:
            # for baseDS in swtbl0:
            #    print(baseDS)
            #    substruct_01 = False
            for i in range(swtbl1_nparray.shape[0]):
                #    if baseDS == swtbl1_nparray[i, 1]:
                #        substruct_01 = True
                substruct_12 = False
                for j in range(swtbl2_nparray.shape[0]):
                    if swtbl1_nparray[i, 2] == swtbl2_nparray[j, 1]:
                        if (swtbl1_nparray[i, 1].replace('[]', '') != swtbl2_nparray[j, 5].replace('[]', '')) and \
                                (swtbl2_nparray[j, 5] != "NULL"):
                            continue
                        substruct_12 = True
                        substruct_23 = False
                        for k in range(swtbl3_nparray.shape[0]):
                            if swtbl2_nparray[j, 2] == swtbl3_nparray[k, 1]:
                                if (swtbl1_nparray[i, 1].replace('[]', '') != swtbl3_nparray[k, 5].replace('[]',
                                                                                                           '')) and \
                                        (swtbl3_nparray[k, 5] != "NULL"):
                                    continue
                                substruct_23 = True
                                dsName = swtbl1_nparray[i, 1] + '.' + swtbl2_nparray[j, 1] + \
                                         '.' + swtbl3_nparray[k, 1] + '.' + swtbl3_nparray[k, 2]
                                print(dsName)
                                dataStructures[dsName] = [dsName, swtbl1_nparray[i, 1],
                                                          *(swtbl3_nparray[k, 3:].tolist())]
                                #writeFile.write(dataStructures[dsName].__str__() + '\n')
                        if substruct_23 == False:
                            dsName = swtbl1_nparray[i, 1] + '.' + swtbl2_nparray[j, 1] + \
                                     '.' + swtbl2_nparray[j, 2]
                            print(dsName)
                            dataStructures[dsName] = [dsName, swtbl1_nparray[i, 1], *(swtbl2_nparray[j, 3:].tolist())]
                            #writeFile.write(dataStructures[dsName].__str__() + '\n')
                if substruct_12 == False:
                    dsName = swtbl1_nparray[i, 1] + '.' + swtbl1_nparray[i, 2]
                    print(dsName)
                    dataStructures[dsName] = [dsName, swtbl1_nparray[i, 1], *(swtbl1_nparray[i, 3:].tolist())]
                    #writeFile.write(dataStructures[dsName].__str__() + '\n')
        # if substruct_01 == False:
        #    print(baseDS)
        #    dataStructures.append(baseDS)
        #    writeFile.write(baseDS.__str__() + '\n')
        return dataStructures

    def checkDataStructuresValidity(self, dataStructures):
        """
        Remove invalid data structures from a dictionary of data structures. A data structure is defined as invalid
        if the ppmac rejects it when its indices are filled-in as zero.
        :param dataStructures:
        :return:
        """
        logging.info(f"checkDataStructuresValidity: checking if all data structures are valid, "
                     f"and removing any invalid data structures...")
        invalidCount = 0
        for ds in list(dataStructures):
            cmd_return = self.sendCommand(ds.replace('[]', '[0]'))
            if 'ILLEGAL' in cmd_return[0]:
                logging.debug(f"{ds.replace('[]', '[0]')} not a valid ppmac command, deleting from"
                              f" dictionary of data structures.")
                del dataStructures[ds]
                invalidCount += 1
        logging.info(f"checkDataStructuresValidity: removed {invalidCount} invalid data structures.")
        return dataStructures

    def getActiveElementsFromDataStructures(self, dataStructures, elementsToIgnore,
                                            recordTimings=False, timeout=None):
        """
        Generate a dictionary of active elements from an iterable containing data structure names.
        :param dataStructures: Iterable containing data structure names
        :param elementsToIgnore: Set of data structures not to be added to included in the active elements read from
        the ppmac.
        :return: Dictionary containing the current set of active elements, where the key is the active element
        name, and the value is a tuple containing the return value from the ppmac and the active element name.
        """
        logging.info('getActiveElementsFromDataStructures: generating dictionary of active elements...')
        fncStartTime = time.time()
        activeElements = {}
        for ds in dataStructures:
            loopStartTime = time.time()
            N_brackets = ds.count('[]')
            if N_brackets == 0:
                value = self.sendCommand(ds)[0]
                category = self.getDataStructureCategory(ds)
                activeElements[ds] = (ds, value, category, ds, None)
            elif N_brackets == 1:
                self.fillDataStructureIndices_i(ds, activeElements, elementsToIgnore, timeout=timeout)
            elif N_brackets == 2:
                self.fillDataStructureIndices_ij(ds, activeElements, elementsToIgnore, timeout=timeout)
            elif N_brackets == 3:
                self.fillDataStructureIndices_ijk(ds, activeElements, elementsToIgnore, timeout=timeout)
            elif N_brackets == 4:
                self.fillDataStructureIndices_ijkl(ds, activeElements, elementsToIgnore, timeout=timeout)
            else:
                logging.info('Too many indexed substructures in data structure. Ignoring.')
                continue
            if recordTimings:
                logging.info(ds + f'   time: {time.time() - loopStartTime} sec')
        logging.info('Finished generating dictionary of active elements. ')
        logging.info(f'Total time = {time.time() - fncStartTime} sec')
        return activeElements

    def expandSplicedIndices(self, splicedDataStructure):
        """
        Stuff
        :param splicedDataStructure: String containing a data structure name with one
        filled index that may or may not be spliced to indicate a range of values
        :return:
        """
        if splicedDataStructure.count(':') > 1:
            raise ('Too many indices')
        elif ':' not in splicedDataStructure:
            return [splicedDataStructure]
        else:
            splicedIndices = re.search('\[([0-9]+):([0-9]+)\]', splicedDataStructure)
            if splicedIndices == None:
                return [splicedDataStructure]
            startIndex = int(splicedIndices.group(1))
            endIndex = int(splicedIndices.group(2))
            expandedDataStructure = [re.sub('([0-9]+:[0-9]+)', str(i), splicedDataStructure)
                                     for i in range(startIndex, endIndex + 1)]
            return expandedDataStructure

    def generateIgnoreSet(self, ignoreFile):
        ignore = []
        with open(ignoreFile, 'r') as readFile:
            for line in readFile:
                line = line.split('#', 1)[0]
                line = line.strip()
                ignore += line.split()
        expandedIgnore = [item for dataStructure in ignore for item in self.expandSplicedIndices(dataStructure)]
        return set(expandedIgnore)

    def copyDict(self, destValueType, sourceDict):
        return {key: destValueType(*value) for key, value in sourceDict.items()}

    @timer
    def readAndStoreActiveState(self, pathToIgnoreFile):
        self.scpPPMACDatabaseToLocal(self.remote_db_path, self.local_db_path)
        # Store data structures in ppmac object
        dataStructures = self.createDataStructuresFromSymbolsTables(self.pp_swtlbs_symfiles, self.local_db_path)
        validDataStructures = self.checkDataStructuresValidity(dataStructures)
        self.ppmacInstance.dataStructures = \
            self.copyDict(self.ppmacInstance.DataStructure, validDataStructures)
        # Store active elements in ppmac object
        elementsToIgnore = self.generateIgnoreSet(pathToIgnoreFile)
        #activeElements = self.getActiveElementsFromDataStructures(validDataStructures, elementsToIgnore,
        #                                                          recordTimings=True, timeout=10.0)
        #self.ppmacInstance.activeElements = \
        #    self.copyDict(self.ppmacInstance.ActiveElement, activeElements)
        bufferedProgramsInfo = self.getBufferedProgramsInfo()
        self.appendBufferedProgramsInfoWithListings(bufferedProgramsInfo)
        self.ppmacInstance.forwardPrograms = \
            self.copyDict(self.ppmacInstance.KinematicTransform, bufferedProgramsInfo['Forward'])
        self.ppmacInstance.inversePrograms = \
            self.copyDict(self.ppmacInstance.KinematicTransform, bufferedProgramsInfo['Inverse'])
        self.ppmacInstance.subPrograms = self.copyDict(self.ppmacInstance.Program, bufferedProgramsInfo['SubProg'])
        self.ppmacInstance.motionPrograms = self.copyDict(self.ppmacInstance.Program, bufferedProgramsInfo['Motion'])
        self.ppmacInstance.plcPrograms = self.copyDict(self.ppmacInstance.Program, bufferedProgramsInfo['Plc'])
        #coordSystemDefs = self.getCoordSystemDefinitions()

    def appendBufferedProgramsInfoWithListings(self, bufferedProgramsInfo):
        for programType in bufferedProgramsInfo.keys():
            for programInfo in bufferedProgramsInfo[programType].values():
                programName = programInfo[0]
                if programType == 'Forward' or programType == 'Inverse':
                    progCoordSystem = programInfo[4]
                    programListing = self.sendCommand(f'&{progCoordSystem} list {programType}')
                    programInfo.append(programListing)
                else:
                    programListing = self.sendCommand(f'list {programName}')
                    programInfo.append(programListing)

    def getBufferedProgramsInfo(self):
        motion, subProgs, plcs, inverse, forward = ({} for _ in range(5))
        programBuffers = self.sendCommand('buffer')
        for progBuffInfo in programBuffers:
            progBuffInfo = progBuffInfo.split()
            progName = progBuffInfo[0].strip('., ')
            progOffset = progBuffInfo[2].strip('., ')
            progSize = progBuffInfo[4].strip('., ')
            if 'SubProg' in progName:
                subProgs[progName] = [progName, progOffset, progSize, 'SubProg']
            elif 'Prog' in progName:
                motion[progName] = [progName, progOffset, progSize, 'Motion']
            elif 'Plc' in progName:
                plcs[progName] = [progName, progOffset, progSize, 'Plc']
            elif 'Inverse' in progName:
                progCoordSystem = progName.rstrip('Inverse').lstrip('&')
                #progName = f'InverseKinCS{progCoordSystem}'
                inverse[progName] = [progName, progOffset, progSize, 'Inverse', progCoordSystem]
            elif 'Forward' in progName:
                progCoordSystem = progName.rstrip('Forward').lstrip('&')
                #progName = f'ForwardKinCS{progCoordSystem}'
                forward[progName] = [progName, progOffset, progSize, 'Forward', progCoordSystem]
        return {'SubProg': subProgs, 'Motion': motion, 'Plc': plcs, 'Inverse': inverse, 'Forward': forward}


    def test_CreateDataStructuresFromSymbolsTables(self):
        # dataStructuresFile = 'test/PPMACsoftwareRef_25102016_DataStructures.txt'
        dataStructuresFile = 'test/PPMACsoftwareRef_22032021_DataStructures.txt'
        softwareRefDataStructures = []
        with open(dataStructuresFile, 'r') as readFile:
            for line in readFile:
                if line[0] == '#' or line[0] == '\n':
                    continue
                softwareRefDataStructures.append(line.replace('\n', '').lower())
        softwareRefDataStructures = set(softwareRefDataStructures)
        ppmacActiveDataStructures = []
        for ds in self.createDataStructuresFromSymbolsTables():
            ppmacActiveDataStructures.append(ds.lower())
        ppmacActiveDataStructures = set(ppmacActiveDataStructures)
        diffA = softwareRefDataStructures - ppmacActiveDataStructures
        print(f'{len(diffA)} Data structures in soft. ref. manual but NOT found from ppmac database: ', diffA)
        diffB = ppmacActiveDataStructures - softwareRefDataStructures
        print(f'{len(diffB)} Data structures found from ppmac database but NOT in soft. ref. manual:', diffB)

    def test_getActiveElementsFromDataStructures(self):
        expectedOutputFilePath = 'test/FillAllDataStructuresIndices_ExpectedOutput.txt'
        ignoreListFilePath = 'test/FillAllDataStructuresIndices_IgnoreList.txt'
        unindexedDataFilePath = 'test/FillAllDataStructuresIndices_UnindexedDSs.txt'
        unindexedDataStructures = []
        with open(unindexedDataFilePath, 'r') as unindexedDataFile:
            for line in unindexedDataFile:
                if line[0] == '#' or line[0] == '\n':
                    continue
                unindexedDataStructures.append(line.replace('\n', ''))
        elementsToIgnore = self.generateIgnoreSet(ignoreListFilePath)
        expectedOutput = []
        with open(expectedOutputFilePath, 'r') as expectedOutputFile:
            for line in expectedOutputFile:
                if line[0] == '#' or line[0] == '\n':
                    continue
                expectedOutput.append(line.replace('\n', ''))
        expectedOutput = set(expectedOutput)
        self.sendCommand_ = self.sendCommand
        try:
            self.sendCommand = lambda x: ['1', '1']
            indexedDataStructures = set(
                self.getActiveElementsFromDataStructures(unindexedDataStructures, elementsToIgnore))
        finally:
            self.sendCommand = self.sendCommand_
        print('Expected: ', expectedOutput)
        print('Actual: ', indexedDataStructures)
        if expectedOutput == indexedDataStructures:
            print('PASS')
        else:
            print('FAIL')


class PowerPMAC:
    class DataStructure:
        def __init__(self, name='', base='', field1='', field2='', field3='', field4='',
                     field5='', field6='', field7='', field8='', field9='', field10='', field11='', field12=''):
            self.name = name
            self.base = base
            self.field1 = field1
            self.field2 = field2
            self.field3 = field3
            self.field4 = field4
            self.field5 = field5
            self.field6 = field6
            self.field7 = field7
            self.field8 = field8
            self.field9 = field9
            self.field10 = field10
            self.field11 = field11
            self.field12 = field12

        def __str__(self):
            s = self.name + ', ' + self.base + ', ' + self.field1 + ', ' + self.field2 + ', ' + self.field3 + \
                ', ' + self.field4 + ', ' + self.field5 + ', ' + self.field6 + ', ' + self.field7 + ', ' + \
                self.field8 + ', ' + self.field9 + ', ' + self.field10 + ', ' + self.field11 + ', ' + self.field12
            return s

    class ActiveElement:
        def __init__(self, name='', value='', category='', dataStructure='', indices=[]):
            self.name = name
            self.value = value
            self.category = category
            self.dataStructure = dataStructure
            self.indices = indices

        def __str__(self):
            s = self.name + '  ' + self.value + '  ' + self.category + '  ' + \
                self.dataStructure + '  ' + str(self.indices)
            return s

    class CoordSystemDefinition:
        def __init__(self, index=None, axis=None, forward=None, inverse=None):
            self.index = index
            self.axis = axis
            self.forward = forward
            self.inverse = inverse

    class Program:
        def __init__(self, name, size, offset, type, listing):
            self.name = name
            self.size = size
            self.offset = offset
            self.type = type
            self.listing = listing

        def printInfo(self):
            return f'{self.type}, {self.name}, size {self.size}, offset {self.offset}\n'

    class KinematicTransform(Program):
        def __init__(self, name, size, offset, type, coordSystem, listing):
            super().__init__(name, size, offset, type, listing)
            self.coodSystem = coordSystem

        def printInfo(self):
            return f'{self.type}, {self.name}, size {self.size}, offset {self.offset}, cs {self.coodSystem}\n'

    def __init__(self, name='unknown'):
        # Source: hardware or respository
        self.source = name
        # Dictionary mapping DS names to dataStructure objects
        self.dataStructures = {}
        # Dictionary of active elements
        self.activeElements = {}
        # Dictionary of programs
        self.motionPrograms = {}
        # Dictionary of sub-programs
        self.subPrograms = {}
        # Dictionary of plc-programs
        self.plcPrograms = {}
        # Dictionary of programs
        self.forwardPrograms = {}
        # Dictionary of programs
        self.inversePrograms = {}
        # Dictionary of coord system definitions
        self.coordSystemDefs = {}
        # 16384 total I variables, values range from I0 to I16383
        # 16384 total P variables, values range from P0 to P65535
        # 16384 total M variables, values range from M0 to M16383
        # 8192 Q variables per coordinate system, values range from Q0 to Q8191
        # 8192 L variables per communications thread, coordinate system, or PLC;
        # values range from L0 to L8191
        # Power PMAC supports up to 32 PLC programs
        # Power PMAC supports up to 256 motors
        # BufIo[i] can have i = 0,...,63 (software reference manual p.541-542)
        # Power PMAC supports up to 256 cam tables
        # Power PMAC supports up to 256 compensation tables
        # Power PMAC supports up to 128 coordinate systems
        # Power PMAC supports up to 9 ECAT networks
        # Power PMAC supports up to 768 encoder conversion tables (software reference manual p.206)
        # Gate1[i] can have i = 4,...,19 (software reference manual p.237)
        # Gate2[i] has an unknown range of indices i
        # self.numberOfGate2ICs = ???
        # Gate3[i] can have i = 0,..,15 (software reference manual p.289)
        # GateIo[i] can have i = 0,..,15 (software reference manual p.360), although
        # for some reason i > 15 does not return an error

class PPMACanalyse:
    def __init__(self, ppmacArgs):
        self.resultsDir = 'ppmacAnalysis'
        self.verbosity = 'info'
        self.ipAddress = '192.168.56.10'
        self.port = 1025
        # Configure logger
        if ppmacArgs.resultsdir is not None:
            self.resultsDir = ppmacArgs.resultsdir
        logfile = self.resultsDir + '/' + 'ppmacanalyse.log'
        removeFile(logfile)
        logging.basicConfig(filename=logfile, level=logging.INFO)
        if ppmacArgs.backup is not None:
            if ppmacArgs.interface is not None:
                self.ipAddress = ppmacArgs.interface.split(':')[0]
                self.port = ppmacArgs.interface.split(':')[1]
            createEmptyDir(self.resultsDir)
            self.name = 'hardware'
            if ppmacArgs.name is not None:
                self.name = ppmacArgs.name
            self.backupDir = f'{self.resultsDir}/repository'
            createEmptyDir(self.backupDir)
            self.ignoreFile = 'ignore/ignore'
            if len(ppmacArgs.backup) > 0:
                self.backupDir = f'{self.resultsDir}/{ppmacArgs.backup[0]}'
            if len(ppmacArgs.backup) > 1:
                self.ignoreFile = ppmacArgs.backup[1]
            sshClient.port = self.port
            sshClient.hostname = self.ipAddress
            sshClient.connect()
            self.backup()
            sshClient.disconnect()

    def backup(self):
        ppmacA = PowerPMAC(self.name)
        # read current state of ppmac and store in ppmacA object
        hardwareWriteRead = PPMACHardwareWriteRead(ppmacA)
        hardwareWriteRead.readAndStoreActiveState(self.ignoreFile)
        # write current state of ppmacA object to repository
        repositoryWriteRead = PPMACRepositoryWriteRead(ppmacA, self.backupDir)
        repositoryWriteRead.writeActiveState()


if __name__ == '__main__':
    start = time.time()

    ppmacArgs = parseArgs()
    sshClient = dls_pmacremote.PPmacSshInterface()
    analysis = PPMACanalyse(ppmacArgs)

    sshClient = dls_pmacremote.PPmacSshInterface()
    sshClient.port = 1025
    #sshClient.hostname = '10.2.2.77'
    sshClient.hostname = '192.168.56.10'
    sshClient.connect()

    """
    ppmacA = PowerPMAC()
    ppmacB = PowerPMAC()

    # read current state of ppmac and store in ppmacA object
    hardwareWriteRead = PPMACHardwareWriteRead(ppmacA)
    hardwareWriteRead.readAndStoreActiveState()

    # write current state of ppmacA object to repository
    repositoryWriteRead = PPMACRepositoryWriteRead(ppmacA)
    #repositoryWriteRead.writeActiveElements()
    repositoryWriteRead.writeAllPrograms()
    repositoryWriteRead.readAndStoreBufferedPrograms()

    # read state from repository and store in ppmacB object
    repositoryWriteRead = PPMACRepositoryWriteRead(ppmacB)
    #repositoryWriteRead.setPPMACInstance(ppmacB)
    repositoryWriteRead.readAndStoreActiveElements()

    # compare ppmacA and ppmacB objects
    ppmacComparison = PPMACCompare(ppmacA, ppmacB)
    ppmacComparison.compareActiveElements()

    projectA = PPMACProject('repository', 'tmp/opt')
    projectB = PPMACProject('hardware', '/opt/ppmac/usrflash')
    #projectB = PPMACProject('repository', 'tmp/var-ftp')
    projComparison = ProjectCompare(projectA, projectB)
    projComparison.compareProjectFiles()
    """

    # hardwareWriteRead.test_CreateDataStructuresFromSymbolsTables()
    # hardwareWriteRead.test_getActiveElementsFromDataStructures()

    sshClient.disconnect()

    print(time.time() - start)
