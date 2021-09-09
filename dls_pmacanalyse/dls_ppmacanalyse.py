import dls_pmacremote
from scp import SCPClient
import time


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
        #self.ppmacInstance.numberOfEncTables = self.getNumberOfEncTables()

    #@timer
    def readIVariables(self, indexStart=0, indexLimit=1639, varsPerBlock=100):
        """
        There are 16383 I-variables
        """
        for lowerIndex in range(indexStart, indexLimit, varsPerBlock):
            upperIndex = min(lowerIndex + varsPerBlock - 1, indexLimit)
            cmd = 'I' + str(lowerIndex) + '..' + str(upperIndex)
            (Ivalues, status) = sshClient.sendCommand(cmd)
            if status:
                Ivalues = Ivalues.split("\r")[:-1]
            else:
                raise IOError("Cannot retrieve variable value: error communicating with PMAC")
            cmd = cmd + '->'
            (Idescriptions, status) = sshClient.sendCommand(cmd)
            if status:
                Idescriptions = Idescriptions.split("\r")[:-1]
            else:
                raise IOError("Cannot retrieve variable description: error communicating with PMAC")
            for index in range(0, upperIndex - lowerIndex + 1):
                if index > indexLimit:
                    break
                self.ppmacInstance.IVariables[lowerIndex + index] = \
                    (PowerPMAC.IVariable(lowerIndex + index, Idescriptions[index], Ivalues[index]))

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
        print(setupData)
        ppmacDataStructure.setupData = responseListToDict(setupData)

    #@timer
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
        def __init__(self, definition=None, value=None):
            self.definition = definition
            self.value = value

    class IVariable(Variable):
        '''
        Class representing a single I-variable
        '''
        def __init__(self, index=None, definition=None, value=None):
            super().__init__(definition, value)
            self.index = index

        def __str__(self):
            return 'I' + str(self.index) + ' = ' + self.definition + ' = ' + str(self.value)

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

    def __init__(self):
        # 16383 total I variables
        self.numberOfIVariables = 16383
        self.numberOfMotors = 32
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
        self.numberOfEncTables = 3 #768
        # Gate1[i] can have i = 4,...,19 (software reference manual p.237)
        # currently these are all stored in one instance of SetupDataStructure()
        #self.numberOfGate1ICs = 16
        # Gate2[i] has an UNKNOWN range of indices i
        # currently these are all stored in one instance of SetupDataStructure()
        #self.numberOfGate2ICs = ???
        # Gate3[i] can have i = 0,..,15 (software reference manual p.289)
        # currently these are all stored in one instance of SetupDataStructure()
        #self.numberOfGate3ICs = 16
        # GateIo[i] can have i = 0,..,15 (software reference manual p.360), although
        # for some reason i > 15 does not return an error
        self.numberOfGateIoICs = 17

    def initDataStructures(self):
        self.Motors = [self.SetupDataStructure() for _ in range(self.numberOfMotors)]
        self.CoordSystems = [self.SetupDataStructure() for _ in range(self.numberOfCoordSystems)]
        self.BufIOs = [self.SetupDataStructure() for _ in range(self.numberOfBufIOs)]
        self.CamTables = [self.SetupDataStructure() for _ in range(self.numberOfCamTables)]  # Untested.
        self.BrickAC = self.SetupDataStructure()
        self.BrickLV = self.SetupDataStructure()
        self.IVariables = [self.IVariable() for _ in range(self.numberOfIVariables)]
        self.Clipper = self.SetupDataStructure()  # Alias to Gate3. Not Implemented.
        self.CompTables = [self.SetupDataStructure() for _ in range(self.numberOfCompTables)]  # Untested.
        self.ECATs = [self.SetupDataStructure() for _ in range(self.numberOfECATs)]
        self.EncTables = [self.SetupDataStructure() for _ in range(self.numberOfEncTables)]
        self.Gate1 = self.SetupDataStructure()  # Untested.
        self.Gate2 = self.SetupDataStructure()  # Untested.
        self.Gate3 = self.SetupDataStructure()
        self.GateIOs = [self.SetupDataStructure() for _ in range(self.numberOfGateIoICs)]

if __name__ == '__main__':
    sshClient = dls_pmacremote.PPmacSshInterface()
    sshClient.port = 1025
    #sshClient.hostname = '10.2.2.77'
    sshClient.hostname = '192.168.56.10'
    sshClient.connect()

    ppmac = PowerPMAC()

    hardwareWriteRead = PPMACHardwareWriteRead(ppmac)
    hardwareWriteRead.readSysMaxes()

    ppmac.initDataStructures()

    #hardwareWriteRead.readIVariables(10, 31, 5)
    hardwareWriteRead.readAllMotorsSetupData()
    hardwareWriteRead.readAllCSSetupData()
    hardwareWriteRead.readBrickACData()
    hardwareWriteRead.readBrickLVData()
    #hardwareWriteRead.readAllBufIOSetupData()
    hardwareWriteRead.readAllCamTableSetupData()
    hardwareWriteRead.readAllCompTableSetupData()
    hardwareWriteRead.readAllECATsSetupData()
    hardwareWriteRead.readAllEncTableSetupData()
    hardwareWriteRead.readGate1SetupData()
    hardwareWriteRead.readGate2SetupData()
    hardwareWriteRead.readGate3SetupData()
    hardwareWriteRead.readAllGateIoSetupData()

    for i in range(0, ppmac.numberOfMotors):
        print(ppmac.Motors[i].setupData)
    for i in range(0, ppmac.numberOfCoordSystems):
        print(ppmac.CoordSystems[i].setupData)
    print(ppmac.BrickAC.setupData)
    print(ppmac.BrickLV.setupData)
    #for i in range(0, ppmac.numberOfBufIOs):
    #    print(ppmac.BufIOs[i].setupData)
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

    # scpFromPowerPMACtoLocal(source='/opt/ppmac/usrflash/Project/Configuration/pp_diff.cfg',
    #                        destination='/home/dlscontrols/Workspace/pp_diff.cfg')

    sshClient.disconnect()
