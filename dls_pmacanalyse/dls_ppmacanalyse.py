import dls_pmacremote
from scp import SCPClient
import time


class PowerPMACVariable():
    def __init__(self, definition=None, value=None):
        self.definition = definition
        self.value = value


class PowerPMACIVariable(PowerPMACVariable):
    def __init__(self, index=None, definition=None, value=None):
        PowerPMACVariable.__init__(self, definition, value)
        self.index = index

    def __str__(self):
        return 'I' + str(self.index) + ':' + self.definition + ':' + str(self.value)


class PowerPMACMotor:
    def __init__(self, number=None, setupData=None,
                 statusBits=None, servoData=None):
        self.number = number
        self.setupData = setupData
        self.statusBits = statusBits
        self.servoData = servoData


def timer(func):
    def measureExecutionTime(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        print("Processing time of %s(): %.2f seconds." % (func.__qualname__, time.time() - startTime))
        return result
    return measureExecutionTime


def exitGpascii():
    (exitGpascii, status) = ssh_iface.sendCommand('\x03')
    print(exitGpascii.split("\r"))


def responseListToDict(responseList, splitChars='='):
    responseDict = {}
    for element in responseList:
        nameVal = element.split(splitChars)
        responseDict[nameVal[0]] = nameVal[1]
    return responseDict


class PowerPMAC():
    def __init__(self):
        self.PowerPMACIVariables = [None] * 16383  # Number of I variables
        self.numberOfMotors = ssh_iface.getNumberOfAxes() # Number of motors
        self.PowerPMACMotors = [PowerPMACMotor()] * self.numberOfMotors

    @timer
    def readIVariables(self, indexStart=0, indexLimit=1639, varsPerBlock=100):
        """
        There are 16383 I-variables
        """
        for lowerIndex in range(indexStart, indexLimit, varsPerBlock):
            upperIndex = min(lowerIndex + varsPerBlock, indexLimit)
            cmd = 'I' + str(lowerIndex) + '..' + str(upperIndex)
            (Ivalues, status) = ssh_iface.sendCommand(cmd)
            if status:
                Ivalues = Ivalues.replace("\r\r\r", "\r").split("\r")[:-1]
            else:
                raise IOError("Cannot retrieve variable value: error communicating with PMAC")
            cmd = cmd + '->'
            (Idescriptions, status) = ssh_iface.sendCommand(cmd)
            if status:
                Idescriptions = Idescriptions.replace("\r\r\r", "\r").split("\r")[:-1]
            else:
                raise IOError("Cannot retrieve variable description: error communicating with PMAC")
            for index in range(0, min(indexLimit % varsPerBlock, varsPerBlock)):
                self.PowerPMACIVariables.append(PowerPMACIVariable(index, Idescriptions[index], Ivalues[index]))

    @timer
    def readMotorSetupData(self, motorNumber):
        cmd = 'backup Motor[' + str(motorNumber) + '].'
        (setupData, status) = ssh_iface.sendCommand(cmd)
        if not status:
            raise IOError('Cannot retrieve motor data structure: error communicating with PMAC')
        else:
            setupData = setupData.replace("\r\r\r", "\r").split("\r")[:-1]
        if 'error' in setupData[0]:
            errMessage = f'Error reading data from motor {motorNumber}: '
            raise IOError(errMessage + setupData[0])
        self.PowerPMACMotors[motorNumber].setupData = \
            responseListToDict(setupData)
        print(self.PowerPMACMotors[motorNumber].setupData)

    @timer
    def readMotorServoData(self, motorNumber):
        cmd = 'backup Motor[' + str(motorNumber) + '].Servo.'
        (servoData, status) = ssh_iface.sendCommand(cmd)
        if not status:
            raise IOError("Cannot retrieve motor servo data structure: error communicating with PMAC")
        else:
            servoData = servoData.replace("\r\r\r", "\r").split("\r")[:-1]
        if 'error' in servoData[0]:
            errMessage = f'Error reading servo data from motor {motorNumber}: '
            raise IOError(errMessage + servoData[0])
        self.PowerPMACMotors[motorNumber].servoDataElements = \
            responseListToDict(servoData)

    def readAllMotorsSetupData(self):
        for i in range(0, self.numberOfMotors):
            self.readMotorSetupData(i)


def scpFromPowerPMACtoLocal(source, destination):
    try:
        scp = SCPClient(ssh_iface.client.get_transport())
        scp.get(source, destination)
        scp.close()
    except Exception as e:
        print("Unable to get directory from remote host: ", source)


if __name__ == '__main__':
    ssh_iface = dls_pmacremote.PPmacSshInterface()
    ssh_iface.port = 1025
    ssh_iface.hostname = '192.168.56.10'
    ssh_iface.connect()

    ppmac = PowerPMAC()

    # scpFromPowerPMACtoLocal(source='/opt/ppmac/usrflash/Project/Configuration/pp_diff.cfg',
    #                        destination='/home/dlscontrols/Workspace/pp_diff.cfg')

    # ppmac.readIVariables()
    ppmac.readMotorSetupData(motorNumber=1)
    ppmac.readMotorServoData(motorNumber=2)
    ppmac.readAllMotorsSetupData()

    ssh_iface.disconnect()
