import dls_pmacremote
from scp import SCPClient
import time
import re
import warnings
import os


def timer(func):
    def measureExecutionTime(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        print("Processing time of %s(): %.2f seconds." % (func.__qualname__, time.time() - startTime))
        return result
    return measureExecutionTime


def exitGpascii():
    (exitGpascii, status) = sshClient.sendCommand('\x03')
    print(exitGpascii.split("\r"))


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
        if 'error' in data[0]:
            errMessage = 'Error reading data.'
            raise IOError(errMessage + data[0])
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

    def scpFromPowerPMACtoLocal(source, destination):
        try:
            scp = SCPClient(sshClient.client.get_transport())
            scp.get(source, destination)
            scp.close()
        except Exception as e:
            print("Unable to get directory from remote host: ", source)


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

    hardwareWriteRead.readAllMotorsSetupData()
    hardwareWriteRead.readAllCSSetupData()
    hardwareWriteRead.readBrickACData()
    hardwareWriteRead.readBrickLVData()
    hardwareWriteRead.readAllBufIOSetupData()
    hardwareWriteRead.readAllCamTableSetupData()
    hardwareWriteRead.readAllCompTableSetupData()
    hardwareWriteRead.readAllECATsSetupData()
    hardwareWriteRead.readAllEncTableSetupData()
    hardwareWriteRead.readGate1SetupData()
    hardwareWriteRead.readGate2SetupData()
    hardwareWriteRead.readGate3SetupData()
    hardwareWriteRead.readAllGateIoSetupData()
    hardwareWriteRead.readMacroSetupData()
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
    lw = 0 #16000
    up = 250 #ppmac.numberOfIVariables - 1
    hardwareWriteRead.readIVariables(lw, ppmac.numberOfIVariables - 1, 100)
    hardwareWriteRead.readPVariables(lw, ppmac.numberOfPVariables - 1, 100)
    hardwareWriteRead.readMVariables(lw, ppmac.numberOfMVariables - 1, 100)
    hardwareWriteRead.readQVariables('all', lw, ppmac.numberOfQVariables - 1, 100)

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

    # scpFromPowerPMACtoLocal(source='/opt/ppmac/usrflash/Project/Configuration/pp_diff.cfg',
    #                        destination='/home/dlscontrols/Workspace/pp_diff.cfg')

    sshClient.disconnect()

    print(time.time() - start)