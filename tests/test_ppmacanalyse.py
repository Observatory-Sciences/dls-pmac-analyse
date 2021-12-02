import unittest
from mock import patch, Mock
import os

from dls_pmacanalyse import dls_ppmacanalyse
from dls_pmaclib import dls_pmacremote


class DummyPpmac:
    def __init__(self):
        self.source = "unknown"
        self.Pvariables = ["var"]
        self.Ivariables = ["var"]
        self.Mvariables = ["var"]
        self.Qvariables = ["var"]
        self.dataStructures = {"test": None}
        self.activeElements = {"test": None}


class DummyProj:
    class File:
        def __init__(self):
            self.contents = None

    def __init__(self):
        self.files = {
            "file1": self.File(),
            "file2": self.File(),
        }
        self.source = "repository"


class DummyPpmacArgs:
    def __init__(self):
        self.interface = None
        self.backup = None
        self.compare = ["test1", "test2"]
        self.recover = None
        self.download = None
        self.resultsdir = None


# class TestPpmacLexer(unittest.TestCase):
#   def setUp(self):
#      self.obj = dls_ppmacanalyse.PPMACLexer(None)

# def test_init(self):
# def test_lex(self):
# def test_scanSymbol(self):


class TestPpmacProject(unittest.TestCase):
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACProject.buildProjectTree")
    def setUp(self, mock_build_tree):
        test_source = "repository"
        test_root = "/tmp"
        self.obj = dls_ppmacanalyse.PPMACProject(test_source, test_root)

    def test_init(self):
        assert self.obj.root == "/tmp"
        assert self.obj.source == "repository"
        assert self.obj.files == {}
        assert self.obj.dirs == {}

    def test_getFileContents(self):
        test_file = "/tmp/test.txt"
        with open(test_file, "w") as f:
            f.write("test\n")
        ret = self.obj.getFileContents("test.txt")
        assert ret == ["test\n"]
        os.remove(test_file)


class TestPpmacProjectCompare(unittest.TestCase):
    def setUp(self):
        self.mockA = Mock()
        self.mockB = Mock()
        self.obj = dls_ppmacanalyse.ProjectCompare(self.mockA, self.mockB)

    def test_init(self):
        assert self.obj.projectA == self.mockA
        assert self.obj.projectB == self.mockB
        assert self.obj.filesOnlyInA == {}
        assert self.obj.filesOnlyInB == {}
        assert self.obj.filesInAandB == {}

    def test_set_projA(self):
        mock_proj = Mock()
        self.obj.setProjectA(mock_proj)
        assert self.obj.projectA == mock_proj

    def test_set_projB(self):
        mock_proj = Mock()
        self.obj.setProjectB(mock_proj)
        assert self.obj.projectB == mock_proj

    @patch("difflib.unified_diff")
    def test_compare_proj_files(self, mock_diff):
        test_file = "/tmp/test_diff.txt"
        with open(test_file, "w") as f:
            pass
        self.obj.projectA = DummyProj()
        self.obj.projectB = DummyProj()
        self.obj.compareProjectFiles("/tmp/test_diff.txt")
        assert self.obj.filesOnlyInA == {}
        assert self.obj.filesOnlyInB == {}
        f = open(test_file, "r")
        assert (
            f.read()
            == "@@ Project files in source 'repository' but not source 'repository' @@\n@@ Project files in source 'repository' but not source 'repository' @@\n@@ Project files in source 'repository' and source 'repository' with different contents @@\n"
        )
        f.close()
        os.remove(test_file)
        assert mock_diff.called


class TestPpmacCompare(unittest.TestCase):
    def setUp(self):
        self.mockA = Mock()
        self.mockB = Mock()
        self.obj = dls_ppmacanalyse.PPMACCompare(self.mockA, self.mockB)

    def test_init(self):
        assert self.obj.ppmacInstanceA == self.mockA
        assert self.obj.ppmacInstanceB == self.mockB
        assert self.obj.elemNamesOnlyInA == {}
        assert self.obj.elemNamesOnlyInB == {}
        assert self.obj.elemNamesInAandB == {}
        assert self.obj.activeElemsOnlyInA == {}
        assert self.obj.activeElemsOnlyInB == {}
        assert self.obj.activeElemsInAandB == {}

    def test_set_projA(self):
        mock_proj = Mock()
        self.obj.setPPMACInstanceA(mock_proj)
        assert self.obj.ppmacInstanceA == mock_proj

    def test_set_projB(self):
        mock_proj = Mock()
        self.obj.setPPMACInstanceB(mock_proj)
        assert self.obj.ppmacInstanceB == mock_proj

    # def test_compareActiveElements(self):
    # def test_writeActiveElemDifferencesToFile(self):


class TestPpmacRepositoryWriteRead(unittest.TestCase):
    def setUp(self):
        self.mock_ppmac = DummyPpmac()
        self.obj = dls_ppmacanalyse.PPMACRepositoryWriteRead(self.mock_ppmac)

    def test_init(self):
        assert self.obj.ppmacInstance == self.mock_ppmac
        assert self.obj.ppmacInstance.source == "repository"
        assert self.obj.repositoryPath == "repository"

    def test_setPPMACInstance(self):
        mock_ppmac = DummyPpmac()
        self.obj.setPPMACInstance(mock_ppmac)
        assert self.obj.ppmacInstance == mock_ppmac
        assert self.obj.ppmacInstance.source == "repository"

    def test_setRepositoryPath(self):
        test_path = os.getcwd()
        self.obj.setRepositoryPath(test_path)
        assert self.obj.repositoryPath == test_path

    def test_writeVars(self):
        test_file = "/tmp/test.txt"
        fh = open(test_file, "w")
        fh.close()
        test_vars = ["var1", "var2", "var3"]
        self.obj.writeVars(test_vars, test_file)
        f = open(test_file, "r")
        assert f.read() == "var1\nvar2\nvar3\n"
        f.close()
        os.remove(test_file)

    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACRepositoryWriteRead.writeVars")
    def test_writePvars(self, mock_writeVars):
        self.obj.repositoryPath = "path"
        self.obj.writePvars()
        mock_writeVars.assert_called_with(
            self.obj.ppmacInstance.Pvariables, "path/Pvars.txt"
        )

    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACRepositoryWriteRead.writeVars")
    def test_writeIvars(self, mock_writeVars):
        self.obj.repositoryPath = "path"
        self.obj.writeIvars()
        mock_writeVars.assert_called_with(
            self.obj.ppmacInstance.Ivariables, "path/Ivars.txt"
        )

    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACRepositoryWriteRead.writeVars")
    def test_writeMvars(self, mock_writeVars):
        self.obj.repositoryPath = "path"
        self.obj.writeMvars()
        mock_writeVars.assert_called_with(
            self.obj.ppmacInstance.Mvariables, "path/Mvars.txt"
        )

    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACRepositoryWriteRead.writeVars")
    def test_writeQvars(self, mock_writeVars):
        self.obj.ppmacInstance.numberOfCoordSystems = 1
        self.obj.repositoryPath = "path"
        self.obj.writeQvars()
        mock_writeVars.assert_called_with(
            self.obj.ppmacInstance.Pvariables[0], "path/Qvars_CS0.txt"
        )

    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACRepositoryWriteRead.writeAllPrograms")
    @patch(
        "dls_pmacanalyse.dls_ppmacanalyse.PPMACRepositoryWriteRead.writeActiveElements"
    )
    @patch(
        "dls_pmacanalyse.dls_ppmacanalyse.PPMACRepositoryWriteRead.writeDataStructures"
    )
    def test_writeActiveState(self, mock_write, mock_write_active, mock_write_all):
        self.obj.writeActiveState()
        assert mock_write.called
        assert mock_write_active.called
        assert mock_write_all.called

    def test_writeDataStructures(self):
        test_file = "/tmp/dataStructures.txt"
        self.obj.repositoryPath = "/tmp"
        self.obj.writeDataStructures()
        f = open(test_file, "r")
        assert f.read() == "None\n"
        f.close()
        os.remove(test_file)

    def test_writeActiveElements(self):
        test_file = "/tmp/activeElements.txt"
        self.obj.repositoryPath = "/tmp"
        self.obj.writeActiveElements()
        f = open(test_file, "r")
        assert f.read() == "None\n"
        f.close()
        os.remove(test_file)

    # def test_readAndStoreBufferedPrograms(self):


class TestPpmacHardwareWriteRead(unittest.TestCase):
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.readSysMaxes")
    def setUp(self, mock_readsys):
        self.mock_ppmac = DummyPpmac()
        self.obj = dls_ppmacanalyse.PPMACHardwareWriteRead(self.mock_ppmac)

    def test_init(self):
        assert self.obj.ppmacInstance == self.mock_ppmac
        assert self.obj.ppmacInstance.source == "hardware"
        assert self.obj.remote_db_path == "/var/ftp/usrflash/Database"
        assert self.obj.local_db_path == "./tmp/Database"
        assert self.obj.pp_swtbl0_txtfile == "pp_swtbl0.txt"
        assert self.obj.pp_swtlbs_symfiles == [
            "pp_swtbl1.sym",
            "pp_swtbl2.sym",
            "pp_swtbl3.sym",
        ]

    def test_setPPMACInstance(self):
        mock_ppmac = DummyPpmac()
        self.obj.setPPMACInstance(mock_ppmac)
        assert self.obj.ppmacInstance == mock_ppmac
        assert self.obj.ppmacInstance.source == "hardware"

    def test_getCommandReturnInt(self):
        dls_ppmacanalyse.sshClient = Mock()
        attrs = {"sendCommand.return_value": ("0", True)}
        dls_ppmacanalyse.sshClient.configure_mock(**attrs)
        assert self.obj.getCommandReturnInt("cmd") == 0
        dls_ppmacanalyse.sshClient.sendCommand.assert_called_with("cmd")

    @patch(
        "dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.getCommandReturnInt"
    )
    def test_readSysMaxes(self, mock_getint):
        mock_getint.return_value = 1
        self.obj.readSysMaxes()
        assert mock_getint.call_count == 6
        assert self.obj.ppmacInstance.numberOfMotors == 1
        assert self.obj.ppmacInstance.numberOfCoordSystems == 1
        assert self.obj.ppmacInstance.numberOfCompTables == 1
        assert self.obj.ppmacInstance.numberOfCamTables == 1
        assert self.obj.ppmacInstance.numberOfECATs == 1
        assert self.obj.ppmacInstance.numberOfEncTables == 1

    def test_sendCommand(self):
        dls_ppmacanalyse.sshClient = Mock()
        attrs = {"sendCommand.return_value": ("0\r0\r0\r\x06", True)}
        dls_ppmacanalyse.sshClient.configure_mock(**attrs)
        assert self.obj.sendCommand("cmd") == ["0", "0", "0"]
        dls_ppmacanalyse.sshClient.sendCommand.assert_called_with("cmd")

    def test_swtblFileToList(self):
        test_file = "/tmp/test.txt"
        with open(test_file, mode="w") as f:
            f.write("test\n\x06")
        ret = self.obj.swtblFileToList(test_file)
        assert ret == [["test"], ["\x06"]]
        os.remove(test_file)

    def test_getDataStructureCategory_1(self):
        ret = self.obj.getDataStructureCategory("test")
        assert ret == "test"

    def test_getDataStructureCategory_2(self):
        ret = self.obj.getDataStructureCategory("other.test[]")
        assert ret == "other"

    def test_ignoreDataStructure_true(self):
        ret = self.obj.ignoreDataStructure("another.test[]", ["another"])
        assert ret == True

    def test_ignoreDataStructure_false(self):
        ret = self.obj.ignoreDataStructure("another.test[]", [])
        assert ret == False

    @patch(
        "dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.ignoreDataStructure"
    )
    @patch(
        "dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.getDataStructureCategory"
    )
    def test_fillDataStructureIndices_i_ignore_true(
        self, mock_getcategory, mock_ignore
    ):
        data_structure = "test.this[]"
        mock_getcategory.return_value = "test"
        mock_ignore.return_value = True
        self.obj.fillDataStructureIndices_i(data_structure, None, None)
        mock_getcategory.assert_called_with("test.this[]")
        mock_ignore.assert_called_with("test.this[0:]", None)

    @patch(
        "dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.ignoreDataStructure"
    )
    @patch(
        "dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.getDataStructureCategory"
    )
    def test_fillDataStructureIndices_i_ignore_false_illegalcmd(
        self, mock_getcategory, mock_ignore
    ):
        dls_ppmacanalyse.sshClient = Mock()
        attrs = {"sendCommand.return_value": ("ILLEGAL\rNone", True)}
        dls_ppmacanalyse.sshClient.configure_mock(**attrs)
        data_structure = "test.this[]"
        mock_getcategory.return_value = "test"
        mock_ignore.return_value = False
        self.obj.fillDataStructureIndices_i(data_structure, None, None)
        mock_getcategory.assert_called_with("test.this[]")
        mock_ignore.assert_called_with("test.this[0]", None)
        dls_ppmacanalyse.sshClient.sendCommand.assert_called_with("test.this[0]")

    # def test_fillDataStructureIndices_ij(self):
    # def test_fillDataStructureIndices_ijk(self):
    # def test_fillDataStructureIndices_ijkl(self):
    # def test_createDataStructuresFromSymbolsTables(self):
    # def test_getActiveElementsFromDataStructures(self):
    # def test_expandSplicedIndices(self):
    # def test_readAndStoreActiveState(self):
    # def test_getBufferedProgramsInfo(self):
    # def test_test_getActiveElementsFromDataStructures


class TestPowerPMAC(unittest.TestCase):
    def setUp(self):
        self.obj = dls_ppmacanalyse.PowerPMAC()

    def test_init(self):
        assert self.obj.source == "unknown"
        assert self.obj.dataStructures == {}
        assert self.obj.activeElements == {}
        assert self.obj.motionPrograms == {}
        assert self.obj.subPrograms == {}
        assert self.obj.plcPrograms == {}
        assert self.obj.forwardPrograms == {}
        assert self.obj.inversePrograms == {}
        assert self.obj.coordSystemDefs == {}


class TestPPMACanalyse(unittest.TestCase):
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACanalyse.compare")
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACanalyse.processCompareOptions")
    @patch("logging.basicConfig")
    @patch("dls_pmacanalyse.dls_ppmacanalyse.createEmptyDir")
    def setUp(self, mock_create, mock_log, mock_opts, mock_comp):
        self.ppmacArgs = DummyPpmacArgs()
        self.obj = dls_ppmacanalyse.PPMACanalyse(self.ppmacArgs)

    def test_init(self):
        assert self.obj.resultsDir == "ppmacAnalyse"
        assert self.obj.verbosity == "info"
        assert self.obj.ipAddress == "192.168.56.10"
        assert self.obj.port == 1025
        assert self.obj.operationType == "all"
        assert self.obj.operationTypes == ["all", "active", "project"]
        assert self.obj.backupDir == None
        assert self.obj.reboot == False

    @patch("dls_pmacanalyse.dls_ppmacanalyse.fileExists")
    @patch("dls_pmacanalyse.dls_ppmacanalyse.createEmptyDir")
    @patch("dls_pmacanalyse.dls_ppmacanalyse.isValidNetworkInterface")
    def test_processCompareOptions(self, mock_valid, mock_create, mock_exists):
        mock_valid.return_value = True
        mock_exists.return_value = True
        self.obj.processCompareOptions(self.ppmacArgs)
        assert self.obj.compareSourceA == "test1"
        assert self.obj.compareSourceB == "test2"
        mock_valid.assert_called_with("test2")
        mock_create.assert_called_with("ppmacAnalyse/compare")
        mock_exists.assert_called_with("ignore/ignore")

    # def test_compare(self):
    # def test_processBackupOptions(self):
    # def test_backup(self):
