import dls_pmacremote
from scp import SCPClient
import time
import re
import warnings
import os
import numpy as np
import logging


def timer(func):
    def measureExecutionTime(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        print("Processing time of %s(): %.2f seconds." % (func.__qualname__, time.time() - startTime))
        return result
    return measureExecutionTime


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
    # if find is not p1 we have found at least one match for the substring
    i = find != -1
    # loop util we find the nth or we find no match
    while find != -1 and i != nth:
        # find + 1 means we start at the last match start index + 1
        find = s.find(sub, find + 1)
        i += 1
    # if i  is equal to nth we found nth matches so replace
    if i == nth:
        return s[:find] + repl + s[find + len(sub):]
    return s

def find_nth(s, sub, n):
    start = s.find(sub)
    while start >= 0 and n > 1:
        start = s.find(sub, start+len(sub))
        n -= 1
    return start

def responseListToDict(responseList, splitChars='='):
    responseDict = {}
    if responseList != ['', '']:
        for element in responseList:
            nameVal = element.split(splitChars)
            responseDict[nameVal[0]] = nameVal[1]
    return responseDict

class PPMACRepositoryWriteRead(object):
    def __init__(self, ppmac=None):
        self.ppmacInstance = ppmac
        self.repositoryPath = os.environ['PWD'] + '/repository'

    def setPPMACInstance(self, ppmac):
        self.ppmacInstance = ppmac

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

class PPMACHardwareWriteRead(object):
    def __init__(self, ppmac=None):
        self.ppmacInstance = ppmac
        # Path to directory containing symbols tables files on PPMAC
        self.remote_db_path = '/var/ftp/usrflash/Database'
        # Path to directory containing symbols tables files on local
        self.local_db_path = './tmp/Database'
        # File containing list of all base Data Structures
        self.pp_swtbl0_txtfile = 'pp_swtbl0.txt'
        # Standard Data Structure symbols tables
        self.pp_swtlbs_symfiles = ['pp_swtbl1.sym', 'pp_swtbl2.sym', 'pp_swtbl3.sym']
        # List of data structures to be ignored when reading active elements
        self.dataStructureIgnoreList = set(['Sys.Uhex[]'])
        # Configure logger
        logging.basicConfig(filename=f'logs/ppmacanalyse.log', level=logging.INFO)

    def setPPMACInstance(self, ppmac):
        self.ppmacInstance = ppmac

    def getCommandReturnInt(self, cmd):
        (cmdReturn, status) = sshClient.sendCommand(cmd)
        if status:
            cmdReturnInt = int(cmdReturn[0:])
        else:
            raise IOError("Cannot retrieve variable value: error communicating with PMAC")
        return cmdReturnInt

    def getMaxNumberOfCoordSystems(self):
        '''
        returns: an int representing the largest number of potentially active coordinate
          systems. Note, a CS usually becomes active when a motor is assigned to it.
        '''
        return self.getCommandReturnInt('Sys.MaxCoords')

    def getNumberOfMotors(self):
        '''
        returns: an int representing the number of active motors.
        '''
        return self.getCommandReturnInt('Sys.MaxMotors')

    def getNumberOfCompTables(self):
        '''
        returns: an int representing the number of active compensation tables.
        '''
        return self.getCommandReturnInt('Sys.CompEnable')

    def getNumberOfCamTables(self):
        '''
        returns: an int representing the number of active compensation tables.
        '''
        return self.getCommandReturnInt('Sys.CamEnable')

    def getNumberOfECATs(self):
        '''
        returns: an int representing the number EtherCAT networks that can be enabled.
        '''
        return self.getCommandReturnInt('Sys.MaxEcats')

    def getNumberOfEncTables(self):
        '''
        returns: an int representing the number of available encoder conversion tables.
        '''
        return self.getCommandReturnInt('Sys.MaxEncoders')

    def readSysMaxes(self):
        if self.ppmacInstance == None:
            raise RuntimeError('No Power PMAC object has been specified')
        self.ppmacInstance.numberOfMotors = self.getNumberOfMotors()
        self.ppmacInstance.numberOfCoordSystems = self.getMaxNumberOfCoordSystems()
        self.ppmacInstance.numberOfCompTables = self.getNumberOfCompTables()
        self.ppmacInstance.numberOfCamTables = self.getNumberOfCamTables()
        self.ppmacInstance.numberOfECATs = self.getNumberOfECATs()
        # self.ppmacInstance.numberOfEncTables = self.getNumberOfEncTables()

    def sendCommand(self, cmd):
        start = time.time()
        (data, status) = sshClient.sendCommand(cmd)
        tdiff = time.time() - start
        if tdiff > 0.07:
            print(cmd, tdiff)
        if not status:
            raise IOError('Cannot retrieve data structure: error communicating with PMAC')
        else:
            data = data.split("\r")[:-1]
            #print(data)
        #if 'error' in data[0]:
        #    errMessage = 'Error reading data.'
        #    raise IOError(errMessage + data[0])
        return data

    def readVariables(self, type, variables, indexStart=0, indexEnd=1639, varsPerBlock=100):
        '''
        :param type: string defining type of variables to be read from ppmac, e.g. P,Q,M,I
        :param variables: reference to list of objects which are of type PowerPMAC.Variable()
        :param indexStart:
        :param indexEnd:
        :param varsPerBlock:
        :return:
        '''
        for lowerIndex in range(indexStart, indexEnd, varsPerBlock):
            upperIndex = min(lowerIndex + varsPerBlock - 1, indexEnd)
            cmd = type + str(lowerIndex) + '..' + str(upperIndex)
            varValues = self.sendCommand(cmd)
            for i in range(0, upperIndex - lowerIndex + 1):
                index = lowerIndex + i
                if i > indexEnd:  # - 1:
                    break
                name = type + str(index)
                value = varValues[i].split('=')[1]
                variables[index] = PowerPMAC.Variable(index, name, value)

    # @timer
    def readDSVariables(self, type, variables, indexStart=0, indexEnd=1639, varsPerBlock=100):
        '''
        :param type: string defining type of variables to be read from ppmac, e.g. P,Q,M,I,L,D,C
        :param variables: reference to list of objects which are of type PowerPMAC.Variable()
        :param indexStart:
        :param indexEnd:
        :param varsPerBlock:
        :return:
        '''
        for lowerIndex in range(indexStart, indexEnd, varsPerBlock):
            upperIndex = min(lowerIndex + varsPerBlock - 1, indexEnd)
            cmd = type + str(lowerIndex) + '..' + str(upperIndex)
            varValues = self.sendCommand(cmd)
            cmd = cmd + '->'
            elementNames = self.sendCommand(cmd)
            #print(elementNames)
            for i in range(0, upperIndex - lowerIndex + 1):
                index = lowerIndex + i
                if i > indexEnd:  # - 1:
                    break
                name = type + str(index)
                element = elementNames[i].split('->')[1]
                value = varValues[i].split('=')[1]
                group = re.split('\[|\.', element)[0]
                variables[index] = PowerPMAC.DSVariable(index, name, element, value, group)

    def readIVariables(self, indexStart=0, indexEnd=1639, varsPerBlock=100):
        """
        There are 16384 I-variables
        """
        if indexEnd > self.ppmacInstance.numberOfIVariables - 1 or indexStart < 0 or indexEnd < indexStart:
            warnings.warn('Requested I-variables out of allowed range; please adjust your range')
        else:
            self.readDSVariables('I', self.ppmacInstance.Ivariables, indexStart, indexEnd, varsPerBlock)

    @timer
    def readPVariables(self, indexStart=0, indexEnd=1639, varsPerBlock=100):
        """
        There are 65536 P-variables
        """
        if indexEnd > self.ppmacInstance.numberOfPVariables - 1 or indexStart < 0 or indexEnd < indexStart:
            warnings.warn('Requested P-variables out of allowed range; please adjust your range')
        else:
            self.readVariables('P', self.ppmacInstance.Pvariables, indexStart, indexEnd, varsPerBlock)

    def readMVariables(self, indexStart=0, indexEnd=1639, varsPerBlock=100):
        """
        There are 16384 M-variables
        """
        if indexEnd > self.ppmacInstance.numberOfMVariables - 1 or indexStart < 0 or indexEnd < indexStart:
            warnings.warn('Requested M-variables out of allowed range; please adjust your range')
        else:
            self.readDSVariables('M', self.ppmacInstance.Mvariables, indexStart, indexEnd, varsPerBlock)

    def readQVariables(self, coordSystem='all', indexStart=0, indexEnd=1639, varsPerBlock=100):
        """
        There are 8191 Q-variables per coordinate system
        """
        if indexEnd > self.ppmacInstance.numberOfQVariables - 1 or indexStart < 0 or indexEnd < indexStart:
            warnings.warn('Requested I-variables out of allowed range; please adjust your range')
        else:
            if coordSystem == 'all':
                for i in range(self.ppmacInstance.numberOfCoordSystems):
                    self.readVariables('Q', self.ppmacInstance.Qvariables[i], indexStart, indexEnd, varsPerBlock)
            elif isinstance(coordSystem, int):
                self.readVariables('Q', self.ppmacInstance.Qvariables[coordSystem], indexStart, indexEnd, varsPerBlock)
            else:
                warnings.warn('Unrecognised coordinate system number')


    def readDataStructure(self, cmd, ppmacDataStructure):
        '''
        Read entire data structure from the ppmac and store the result in the class PowerPMAC.
        :param cmd: command string to be sent to the ppmac
        :param ppmacDataStructure: reference to object of type PowerPMAC.SetupDataStructure whose
                    setupData member will be populated with the response from the ppmac.
        :return: n/a
        '''
        (setupData, status) = sshClient.sendCommand(cmd)
        if not status:
            raise IOError('Cannot retrieve data structure: error communicating with PMAC')
        else:
            setupData = setupData.split("\r")[:-1]
        if 'error' in setupData[0]:
            errMessage = 'Error reading data.'
            raise IOError(errMessage + setupData[0])
        ppmacDataStructure.setupData = responseListToDict(setupData)

    # @timer
    def readMotorSetupData(self, motorNumber):
        cmd = f'backup Motor[{motorNumber}].'
        self.readDataStructure(cmd, self.ppmacInstance.Motors[motorNumber])

    def readCoordSystemSetupData(self, csNumber):
        cmd = f'backup Coord[{csNumber}].'
        self.readDataStructure(cmd, self.ppmacInstance.CoordSystems[csNumber])

    def readBrickACData(self):
        cmd = 'backup BrickAC.'
        self.readDataStructure(cmd, self.ppmacInstance.BrickAC)

    def readBrickLVData(self):
        cmd = 'backup BrickLV.'
        self.readDataStructure(cmd, self.ppmacInstance.BrickLV)

    def readBufIOSetupData(self, bufIONumber):
        cmd = f'backup BufIo[{bufIONumber}].'
        self.readDataStructure(cmd, self.ppmacInstance.BufIOs[bufIONumber])

    def readCamTableSetupData(self, camTableNumber):
        cmd = f'backup CamTable[{camTableNumber}].'
        self.readDataStructure(cmd, self.ppmacInstance.CamTables[camTableNumber])

    def readCompTableSetupData(self, compTableNumber):
        cmd = f'backup CompTable[{compTableNumber}].'
        self.readDataStructure(cmd, self.ppmacInstance.CompTables[compTableNumber])

    def readECATSetupData(self, ECATNumber):
        cmd = f'backup ECAT[{ECATNumber}].'
        self.readDataStructure(cmd, self.ppmacInstance.ECATs[ECATNumber])

    def readEncTableSetupData(self, encTableNumber):
        cmd = f'backup EncTable[{encTableNumber}].'
        self.readDataStructure(cmd, self.ppmacInstance.EncTables[encTableNumber])

    def readGate1SetupData(self):
        cmd = 'backup Gate1'
        self.readDataStructure(cmd, self.ppmacInstance.Gate1)

    def readGate2SetupData(self):
        cmd = 'backup Gate2'
        self.readDataStructure(cmd, self.ppmacInstance.Gate2)

    def readGate3SetupData(self):
        cmd = 'backup Gate3'
        self.readDataStructure(cmd, self.ppmacInstance.Gate3)

    def readGateIoSetupData(self, gateIoNumber):
        # backup iogates
        i = gateIoNumber
        cmd = f'echo 0 GateIo[{i}].Init.CtrlReg '
        for j in range(0, 6):
            cmd += f'GateIo[{i}].Init.DataReg0[{j}] ' \
                   f'GateIo[{i}].Init.DataReg64[{j}] ' \
                   f'GateIo[{i}].Init.DataReg128[{j}] ' \
                   f'GateIo[{i}].Init.DataReg192[{j}] '
        cmd += f'GateIo[{i}].Init.IntrReg64 ' \
               f'GateIo[{i}].Init.IntrReg128 ' \
               f'GateIo[{i}].Init.IntrReg192 '
        self.readDataStructure(cmd, self.ppmacInstance.GateIOs[gateIoNumber])

    def readMacroSetupData(self):
        cmd = 'backup Macro.'
        self.readDataStructure(cmd, self.ppmacInstance.Macro)

    def readAllMotorsSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfMotors):
            self.readMotorSetupData(i)

    def readAllCSSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfCoordSystems):
            self.readCoordSystemSetupData(i)

    def readAllBufIOSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfBufIOs):
            self.readBufIOSetupData(i)

    def readAllCamTableSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfCamTables):
            self.readCamTableSetupData(i)

    def readAllCompTableSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfCompTables):
            self.readCompTableSetupData(i)

    def readAllECATsSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfECATs):
            self.readECATSetupData(i)

    def readAllEncTableSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfEncTables):
            self.readEncTableSetupData(i)

    def readAllGateIoSetupData(self):
        for i in range(0, self.ppmacInstance.numberOfGateIoICs):
            self.readGateIoSetupData(i)

    def swtblFileToList(self, pp_swtbl_file):
        """
        Generate a list of symbols from a symbols table file.
        :param pp_swtbl_file: full path to symbols table file.
        :return: swtbl_DSs: list of symbols.
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
                    multi_line = ''
                    symbols.append(symbol)
            file.close()
        except IOError as e:
            print(e)
        return symbols

    def ignoreDataStructure(self, substructure):
        """
        Determine whether a data structure or substructure should be ignored by checking if it or any of its parent,
        grandparent, great-grandparent etc. structures are included in the ignore list.
        :param substructure: name of data structure or substructure to check
        :return: True if data structure or substructure should be ignored, False otherwise
        """
        n = substructure.count('.')
        for _ in range(n + 1):
            #print('Checking if the following structure is in the ignore list: ' + substructure)
            if substructure in self.dataStructureIgnoreList:
                #print('Ignoring data structure')
                return True
            substructure = substructure[0:substructure.rfind('.')]
        return False


    def fillDataStructureIndices1(self, DS_string, DSs):
        i = 0
        cmd_accepted = True
        while cmd_accepted:
            i_idex_string = f'[{i}]'
            DS_string_ = DS_string.replace('[]', i_idex_string)
            if self.ignoreDataStructure(DS_string_):
                break
            print(DS_string_)
            cmd_return = self.sendCommand(DS_string_)
            print(cmd_return)
            if 'ILLEGAL' in cmd_return[0]:
                cmd_accepted = False
            else:
                DSs.append(DS_string_)
            i += 1

    def fillDataStructureIndices2(self, DS_string, DSs):
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        while cmd_accepted:
            j = 0
            i_idex_string = f'[{i}]'
            DS_string_ = nthRepl(DS_string, '[]', i_idex_string, 1)
            if self.ignoreDataStructure(DS_string_):
                break
            while cmd_accepted:
                j_idex_string = f'[{j}]'
                DS_string__ = nthRepl(DS_string_, '[]', j_idex_string, 1)
                if self.ignoreDataStructure(DS_string__.replace(f'[{i}]', '[]', 1)):
                    break
                print(DS_string__)
                cmd_return = self.sendCommand(DS_string__)
                print(cmd_return)
                if 'ILLEGAL' in cmd_return[0]:
                    cmd_accepted = False
                else:
                    last_i_accepted = i
                    DSs.append(DS_string__)
                j += 1
            cmd_accepted = True
            # print(last_i_accepted, i)
            if i - last_i_accepted > 1:
                cmd_accepted = False
            # print(cmd_accepted)
            i += 1

    def fillDataStructureIndices3(self, DS_string, DSs):
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        while cmd_accepted:
            j = 0
            last_j_accepted = j
            i_idex_string = f'[{i}]'
            DS_string_ = nthRepl(DS_string, '[]', i_idex_string, 1)
            if self.ignoreDataStructure(DS_string_):
                break
            while cmd_accepted:
                k = 0
                j_idex_string = f'[{j}]'
                DS_string__ = nthRepl(DS_string_, '[]', j_idex_string, 1)
                if self.ignoreDataStructure(DS_string__.replace(f'[{i}]', '[]', 1)):
                    break
                while cmd_accepted:
                    k_idex_string = f'[{k}]'
                    DS_string___ = nthRepl(DS_string__, '[]', k_idex_string, 1)
                    if self.ignoreDataStructure(DS_string___.replace(f'[{i}]', '[]', 1).replace(f'[{j}]', '[]', 1)):
                        break
                    print(DS_string___)
                    cmd_return = self.sendCommand(DS_string___)
                    print(cmd_return)
                    if 'ILLEGAL' in cmd_return[0]:
                        cmd_accepted = False
                    else:
                        last_j_accepted = j
                        last_i_accepted = i
                        DSs.append(DS_string___)
                    k += 1
                cmd_accepted = True
                if j - last_j_accepted > 1:
                    cmd_accepted = False
                j += 1
            cmd_accepted = True
            if i - last_i_accepted > 1:
                cmd_accepted = False
            i += 1

    def fillDataStructureIndices4(self, DS_string, DSs):
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        while cmd_accepted:
            j = 0
            last_j_accepted = j
            i_idex_string = f'[{i}]'
            DS_string_ = nthRepl(DS_string, '[]', i_idex_string, 1)
            if self.ignoreDataStructure(DS_string_):
                break
            while cmd_accepted:
                k = 0
                last_k_accepted = k
                j_idex_string = f'[{j}]'
                DS_string__ = nthRepl(DS_string_, '[]', j_idex_string, 1)
                if self.ignoreDataStructure(DS_string__.replace(f'[{i}]', '[]', 1)):
                    break
                while cmd_accepted:
                    l = 0
                    k_idex_string = f'[{k}]'
                    DS_string___ = nthRepl(DS_string__, '[]', k_idex_string, 1)
                    if self.ignoreDataStructure(DS_string___.replace(f'[{i}]', '[]', 1).replace(f'[{j}]', '[]', 1)):
                        break
                    while cmd_accepted:
                        l_idex_string = f'[{l}]'
                        DS_string____ = nthRepl(DS_string___, '[]', l_idex_string, 1)
                        if self.ignoreDataStructure(DS_string____.replace(f'[{i}]', '[]', 1).replace(
                                f'[{j}]', '[]', 1).replace(f'[{k}]', '[]', 1)):
                            break
                        print(DS_string____)
                        cmd_return = self.sendCommand(DS_string____)
                        print(cmd_return)
                        if 'ILLEGAL' in cmd_return[0]:
                            cmd_accepted = False
                        else:
                            last_k_accepted = k
                            last_j_accepted = j
                            last_i_accepted = i
                            DSs.append(DS_string____)
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


    def createDataStructuresFromSymbolsTables(self):
        """
        Read the symbols tables and create a list of data structure names contained within them.
        :return: dataStructures: list of data structure names
        """
        # delete old dict
        if not os.path.isdir(self.local_db_path):
            os.system('mkdir ' + self.local_db_path)
        scpFromPowerPMACtoLocal(source=self.remote_db_path, destination=self.local_db_path, recursive=True)
        #swtbl0 = []
        #with open(self.local_db_path + '/' + self.pp_swtbl0_txtfile, 'r') as readFile:
        #    for line in readFile:
        #        swtbl0.append(line.replace('\n',''))
        pp_swtbls = []
        for pp_swtbl_file in self.pp_swtlbs_symfiles:
            pp_swtbls.append(self.swtblFileToList(self.local_db_path + '/' + pp_swtbl_file))
        swtbl1_nparray = np.asarray(pp_swtbls[0])
        swtbl2_nparray = np.asarray(pp_swtbls[1])
        swtbl3_nparray = np.asarray(pp_swtbls[2])
        dataStructures = []
        with open('tmp/master_swtbl_3.txt', 'w+') as writeFile:
            #for baseDS in swtbl0:
            #    print(baseDS)
            #    substruct_01 = False
                for i in range(swtbl1_nparray.shape[0]):
                #    if baseDS == swtbl1_nparray[i, 1]:
                #        substruct_01 = True
                        substruct_12 = False
                        for j in range(swtbl2_nparray.shape[0]):
                            if swtbl1_nparray[i, 2] == swtbl2_nparray[j, 1]:
                                if (swtbl1_nparray[i, 1].replace('[]','') != swtbl2_nparray[j, 5].replace('[]','')) and \
                                        (swtbl2_nparray[j, 5] != "NULL"):
                                    continue
                                substruct_12 = True
                                substruct_23 = False
                                for k in range(swtbl3_nparray.shape[0]):
                                    if swtbl2_nparray[j, 2] == swtbl3_nparray[k, 1]:
                                        if (swtbl1_nparray[i, 1].replace('[]','') != swtbl3_nparray[k, 5].replace('[]','')) and \
                                                (swtbl3_nparray[k, 5] != "NULL"):
                                            continue
                                        substruct_23 = True
                                        ds_ = swtbl1_nparray[i, 1] + '.' + swtbl2_nparray[j, 1] + \
                                              '.' + swtbl3_nparray[k, 1] + '.' + swtbl3_nparray[k, 2]
                                        print(ds_)
                                        dataStructures.append(ds_)
                                        writeFile.write(ds_.__str__() + '\n')
                                if substruct_23 == False:
                                    ds_ = swtbl1_nparray[i, 1] + '.' + swtbl2_nparray[j, 1] + \
                                          '.' + swtbl2_nparray[j, 2]
                                    print(ds_)
                                    dataStructures.append(ds_)
                                    writeFile.write(ds_.__str__() + '\n')
                        if substruct_12 == False:
                            ds_ = swtbl1_nparray[i, 1] + '.' + swtbl1_nparray[i, 2]
                            print(ds_)
                            dataStructures.append(ds_)
                            writeFile.write(ds_.__str__() + '\n')
            #if substruct_01 == False:
            #    print(baseDS)
            #    dataStructures.append(baseDS)
            #    writeFile.write(baseDS.__str__() + '\n')
        return dataStructures


    def checkDataStructuresValidity(self, dataStructures):
        # Check that data structure names have been accepted
        acceptedDataStructures = []
        for ds in dataStructures:
            print(ds)
            cmd_return = self.sendCommand(ds.replace('[]','[0]'))
            if 'ILLEGAL' in cmd_return[0]:
                logging.info(f"{ds.replace('[]','[0]')} not a valid ppmac command")
            else:
                acceptedDataStructures.append(ds)
        return acceptedDataStructures


    def fillAllDataStructuresIndices(self, dataStructures):
        # Here we'll probably want to construct a big string of lots of commands to send
        # at once and then parse the response to see which were accepted, rather than
        # sending each command individually
        indexedDataStructures = []
        for ds in dataStructures:
                N_brackets = ds.count('[]')
                if N_brackets == 0:
                    indexedDataStructures.append(ds)
                elif N_brackets == 1:
                   self.fillDataStructureIndices1(ds, indexedDataStructures)
                elif N_brackets == 2:
                    self.fillDataStructureIndices2(ds, indexedDataStructures)
                elif N_brackets == 3:
                    self.fillDataStructureIndices3(ds, indexedDataStructures)
                elif N_brackets == 4:
                    self.fillDataStructureIndices4(ds, indexedDataStructures)
                else:
                    logging.info('Too many indexed substructures in data structure. Ignoring.')
                    continue
        return indexedDataStructures


    def generateActiveDataStructures(self):
        self.dataStructureIgnoreList = {'Sys.Uhex[0]', 'Sys.Cdata[10]', 'Motor[].New[5]', 'Motor[7]', 'Coord[4]',
                                        'Coord[].TPData[1]', 'Coord[].TPData[].Pos[27]', 'SubProg[0]',
                                        'Plc[].Ldata.L[0]', 'Plc[1].Ldata', 'Plc[].Ldata.Stack[0]', 'Acc72EX[].Data8[0]',
                                        'CompTable[].Data[][10]', 'CompTable[].Data[10][]', 'CompTable[60]'} #set
        DSs = self.createDataStructuresFromSymbolsTables()
        DSs_ = self.checkDataStructuresValidity(DSs)
        DSs__ = self.fillAllDataStructuresIndices(DSs_)


    def test_CreateDataStructuresFromSymbolsTables(self):
        #dataStructuresFile = 'test/PPMACsoftwareRef_25102016_DataStructures.txt'
        dataStructuresFile = 'test/PPMACsoftwareRef_22032021_DataStructures.txt'
        softwareRefDataStructures = []
        with open(dataStructuresFile, 'r') as readFile:
            for line in readFile:
                if line[0] == '#' or line[0] == '\n':
                    continue
                softwareRefDataStructures.append(line.replace('\n','').lower())
        softwareRefDataStructures = set(softwareRefDataStructures)
        ppmacActiveDataStructures = []
        for ds in self.createDataStructuresFromSymbolsTables():
            ppmacActiveDataStructures.append(ds.lower())
        ppmacActiveDataStructures = set(ppmacActiveDataStructures)
        diffA = softwareRefDataStructures - ppmacActiveDataStructures
        print(f'{len(diffA)} Data structures in soft. ref. manual but NOT found from ppmac database: ', diffA)
        diffB = ppmacActiveDataStructures - softwareRefDataStructures
        print(f'{len(diffB)} Data structures found from ppmac database but NOT in soft. ref. manual:', diffB)

    def test_fillAllDataStructuresIndices(self):
        expectedOutputFilePath = 'test/FillAllDataStructuresIndices_ExpectedOutput.txt'
        ignoreListFilePath = 'test/FillAllDataStructuresIndices_IgnoreList.txt'
        unindexedDataFilePath = 'test/FillAllDataStructuresIndices_UnindexedDSs.txt'
        unindexedDataStructures = []
        with open(unindexedDataFilePath, 'r') as unindexedDataFile:
            for line in unindexedDataFile:
                if line[0] == '#' or line[0] == '\n':
                    continue
                unindexedDataStructures.append(line.replace('\n',''))
        ignoreList = []
        with open(ignoreListFilePath, 'r') as ignoreListFile:
            for line in ignoreListFile:
                if line[0] == '#' or line[0] == '\n':
                    continue
                ignoreList.append(line.replace('\n',''))
        ignoreList = set(ignoreList)
        expectedOutput = []
        with open(expectedOutputFilePath, 'r') as expectedOutputFile:
            for line in expectedOutputFile:
                if line[0] == '#' or line[0] == '\n':
                    continue
                expectedOutput.append(line.replace('\n',''))
        expectedOutput = set(expectedOutput)
        self.dataStructureIgnoreList = ignoreList
        self.sendCommand = lambda x: ['1', '1']
        indexedDataStructures = set(self.fillAllDataStructuresIndices(unindexedDataStructures))
        print('Expected: ', expectedOutput)
        print('Actual: ', indexedDataStructures)
        if expectedOutput == indexedDataStructures:
            print('PASS')
        else:
            print('FAIL')


class PowerPMAC:
    class Variable:
        '''
        Super-class for all P,Q,M,I,L,R,C,D variables
        '''
        def __init__(self, index=None, name=None, value=None):
            self.index = index
            self.name = name
            self.value = value

        def __str__(self):
            return 'Variable=' + str(self.name) + ', Index=' + str(self.index) + \
                   ', Value=' + str(self.value)

    class DSVariable(Variable):
        def __init__(self, index=None, name=None, element=None, value=None, group=None):
            super().__init__(index, name, value)
            self.element = element
            self.group = group

        def __str__(self):
            return 'Variable=' + str(self.name) + ', Index=' + str(self.index) + \
                   ', Element=' + str(self.element) + ', Value=' + str(self.value) + \
                   ', Group=' + str(self.group)

    class SetupDataStructure:
        '''
        Class of all setup data structures
        index: instance of the structure (redundant)
        setupData: dictionary where data element descriptive name is key
        '''

        def __init__(self, number=None, setupData=None, nonSavedSetupData=None, statusBits=None):
            self.index = number
            '''
            Saved Data Structure Elements, i.e. those that are copied into the ppmac's flash
            memory upon a save command.
            '''
            self.setupData = setupData
            '''
            Non-Saved Data Structure Elements, i.e. those that are *not* copied into the ppmac's flash
            memory upon a save command.
            '''
            self.nonSavedSetupData = nonSavedSetupData
            self.statusBits = statusBits

    class PlcProgram:
        '''
        Will have own L-variables (Plc[i].Ldata.L[n], see PPMAC User Manual p.490)
        '''
        pass

    def __init__(self):
        # 16384 total I variables, values range from I0 to I16383
        self.numberOfIVariables = 16384
        # 16384 total P variables, values range from P0 to P65535
        self.numberOfPVariables = 65536
        # 16384 total M variables, values range from M0 to M16383
        self.numberOfMVariables = 16384
        # 8192 Q variables per coordinate system, values range from Q0 to Q8191
        self.numberOfQVariables = 8192
        # 8192 L variables per communications thread, coordinate system, or PLC;
        # values range from L0 to L8191
        self.numberOfLVariables = 8192
        # Power PMAC supports up to 32 PLC programs
        self.numberOfPlcPrograms = 32
        # Power PMAC supports up to 256 motors
        self.numberOfMotors = 256
        # BufIo[i] can have i = 0,...,63 (software reference manual p.541-542)
        self.numberOfBufIOs = 64
        # Power PMAC supports up to 256 cam tables
        self.numberOfCamTables = 256
        # Power PMAC supports up to 256 compensation tables
        self.numberOfCompTables = 256
        # Power PMAC supports up to 128 coordinate systems
        self.numberOfCoordSystems = 128
        # Power PMAC supports up to 9 ECAT networks
        self.numberOfECATs = 9
        # Power PMAC supports up to 768 encoder conversion tables (software reference manual p.206)
        self.numberOfEncTables = 3  # 768
        # Gate1[i] can have i = 4,...,19 (software reference manual p.237)
        # currently these are all stored in one instance of SetupDataStructure()
        # self.numberOfGate1ICs = 16
        # Gate2[i] has an UNKNOWN range of indices i
        # currently these are all stored in one instance of SetupDataStructure()
        # self.numberOfGate2ICs = ???
        # Gate3[i] can have i = 0,..,15 (software reference manual p.289)
        # currently these are all stored in one instance of SetupDataStructure()
        # self.numberOfGate3ICs = 16
        # GateIo[i] can have i = 0,..,15 (software reference manual p.360), although
        # for some reason i > 15 does not return an error
        self.numberOfGateIoICs = 17
        # Dictionary mapping between P,Q,M,I,L,R,C,D variables and the descriptive names of
        # the data structure elements they represent
        self.variableToElement = {}
        self.elementToVariable = {}

    def initDataStructures(self):
        # P,Q,M,I,L,D,C,R variables
        # P,Q,M,I
        self.Ivariables = [self.DSVariable() for _ in range(self.numberOfIVariables)]
        self.Pvariables = [self.Variable() for _ in range(self.numberOfPVariables)]
        self.Mvariables = [self.DSVariable() for _ in range(self.numberOfMVariables)]
        self.Qvariables = [[self.Variable() for _ in range(self.numberOfQVariables)]
                           for _ in range(self.numberOfCoordSystems)]
        # L,D,C,R
        # L variables local to a communication thread do not need to be backed-up
        # L variables local to plc programs probably do not need to be backed-up
        #self.PlcLvariables = [[self.Variable() for _ in range(self.numberOfLVariables)]
        #                   for _ in range(self.numberOfPlcPrograms)]
        # L variables local to coordinate systems...
        #self.CoordSystemLvariables = [[self.Variable() for _ in range(self.numberOfLVariables)]
        #                   for _ in range(self.numberOfCoordSystems)]

        # Data structures
        self.Motors = [self.SetupDataStructure() for _ in range(self.numberOfMotors)]
        self.CoordSystems = [self.SetupDataStructure() for _ in range(self.numberOfCoordSystems)]
        self.BufIOs = [self.SetupDataStructure() for _ in range(self.numberOfBufIOs)]
        self.CamTables = [self.SetupDataStructure() for _ in range(self.numberOfCamTables)]  # Untested.
        self.BrickAC = self.SetupDataStructure()
        self.BrickLV = self.SetupDataStructure()
        self.Clipper = self.SetupDataStructure()  # Alias to Gate3. Not Implemented.
        self.CompTables = [self.SetupDataStructure() for _ in range(self.numberOfCompTables)]  # Untested.
        self.ECATs = [self.SetupDataStructure() for _ in range(self.numberOfECATs)]
        self.EncTables = [self.SetupDataStructure() for _ in range(self.numberOfEncTables)]
        self.Gate1 = self.SetupDataStructure()  # Untested.
        self.Gate2 = self.SetupDataStructure()  # Untested.
        self.Gate3 = self.SetupDataStructure()
        self.GateIOs = [self.SetupDataStructure() for _ in range(self.numberOfGateIoICs)]
        self.Macro = self.SetupDataStructure()

    def buildVariable2Element(self):
        # I variables map
        for ivar in self.Ivariables:
            self.variableToElement[ivar.name] = ivar.element

    def buildElement2Variable(self):
        # I variables map
        for ivar in self.Ivariables:
            self.elementToVariable[ivar.element] = ivar.name
        self.elementToVariable['*'] = None

if __name__ == '__main__':

    start = time.time()

    sshClient = dls_pmacremote.PPmacSshInterface()
    sshClient.port = 1025
    # sshClient.hostname = '10.2.2.77'
    sshClient.hostname = '192.168.56.10'
    sshClient.connect()

    ppmac = PowerPMAC()

    hardwareWriteRead = PPMACHardwareWriteRead(ppmac)
    hardwareWriteRead.readSysMaxes()

    ppmac.initDataStructures()

    #hardwareWriteRead.readAllMotorsSetupData()
    #hardwareWriteRead.readAllCSSetupData()
    #hardwareWriteRead.readBrickACData()
    #hardwareWriteRead.readBrickLVData()
    #hardwareWriteRead.readAllBufIOSetupData()
    #hardwareWriteRead.readAllCamTableSetupData()
    #hardwareWriteRead.readAllCompTableSetupData()
    #hardwareWriteRead.readAllECATsSetupData()
    #hardwareWriteRead.readAllEncTableSetupData()
    #hardwareWriteRead.readGate1SetupData()
    #hardwareWriteRead.readGate2SetupData()
    #hardwareWriteRead.readGate3SetupData()
    #hardwareWriteRead.readAllGateIoSetupData()
    #hardwareWriteRead.readMacroSetupData()
    '''
    for i in range(0, ppmac.numberOfMotors):
        print(ppmac.Motors[i].setupData)
    for i in range(0, ppmac.numberOfCoordSystems):
        print(ppmac.CoordSystems[i].setupData)
    print(ppmac.BrickAC.setupData)
    print(ppmac.BrickLV.setupData)
    for i in range(0, ppmac.numberOfBufIOs):
        print(ppmac.BufIOs[i].setupData)
    for i in range(0, ppmac.numberOfCamTables):
        print(ppmac.CamTables[i].setupData)
    for i in range(0, ppmac.numberOfCompTables):
        print(ppmac.CompTables[i].setupData)
    for i in range(0, ppmac.numberOfECATs):
        print(ppmac.ECATs[i].setupData)
    for i in range(0, ppmac.numberOfEncTables):
        print(ppmac.EncTables[i].setupData)
    print(ppmac.Gate1.setupData)
    print(ppmac.Gate2.setupData)
    print(ppmac.Gate3.setupData)
    for i in range(0, ppmac.numberOfGateIoICs):
        print(ppmac.GateIOs[i].setupData)
    print(ppmac.Macro.setupData)
    '''
    #lw = 0 #16000
    #up = 250 #ppmac.numberOfIVariables - 1
    #hardwareWriteRead.readIVariables(lw, ppmac.numberOfIVariables - 1, 100)
    #hardwareWriteRead.readPVariables(lw, ppmac.numberOfPVariables - 1, 100)
    #hardwareWriteRead.readMVariables(lw, ppmac.numberOfMVariables - 1, 100)
    #hardwareWriteRead.readQVariables('all', lw, ppmac.numberOfQVariables - 1, 100)

    '''
    for i in range(0, up + 1):
        print(ppmac.Ivariables[i])
    for i in range(0, up + 1):
        print(ppmac.Pvariables[i])
    for i in range(0, up + 1):
        print(ppmac.Mvariables[i])
    for i in range(ppmac.numberOfCoordSystems):
        for j in range(0, up + 1):
            print(ppmac.Qvariables[i][j])

    repositoryWriteRead = PPMACRepositoryWriteRead(ppmac)
    repositoryWriteRead.writePvars()
    repositoryWriteRead.writeIvars()
    repositoryWriteRead.writeQvars()
    repositoryWriteRead.writeMvars()
    '''
    #ppmac.buildVariable2Element()
    #ppmac.buildElement2Variable()

    scpFromPowerPMACtoLocal(source='/var/ftp/usrflash/Database',
                        destination='/home/dlscontrols/Workspace/repository/Database', recursive=True)

    #hardwareWriteRead.scpFromLocalToPowerPMAC(files='/home/dlscontrols/Workspace/repository/Project_01',
    #                    remote_path='/var/ftp/usrflash/Project', recursive=True)

    #hardwareWriteRead.generateActiveDataStructures()

    #hardwareWriteRead.test_CreateDataStructuresFromSymbolsTables()
    hardwareWriteRead.test_fillAllDataStructuresIndices()

    sshClient.disconnect()

    print(time.time() - start)
