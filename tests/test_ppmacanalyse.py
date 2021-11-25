import unittest
from mock import patch, Mock
import os

from dls_pmacanalyse import dls_ppmacanalyse

# from dls_pmaclib import dls_pmacremote


class MockPpmac:
    def __init__(self):
        self.source = "unknown"
        self.Pvariables = ["var"]
        self.Ivariables = ["var"]
        self.Mvariables = ["var"]
        self.Qvariables = ["var"]
        self.dataStructures = {"test": None}
        self.activeElements = {"test": None}


class MockProj:
    class File:
        def __init__(self):
            self.contents = None

    def __init__(self):
        self.files = {
            "file1": self.File(),
            "file2": self.File(),
        }  # should hold file objects not None
        self.source = "repository"


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
        self.obj.projectA = MockProj()
        self.obj.projectB = MockProj()
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

    #def test_compareActiveElements(self):
    #def test_writeActiveElemDifferencesToFile(self):

class TestPpmacRepositoryWriteRead(unittest.TestCase):
    def setUp(self):
        self.mock_ppmac = MockPpmac()
        self.obj = dls_ppmacanalyse.PPMACRepositoryWriteRead(self.mock_ppmac)

    def test_init(self):
        assert self.obj.ppmacInstance == self.mock_ppmac
        assert self.obj.ppmacInstance.source == "repository"
        assert self.obj.repositoryPath == "repository"

    def test_setPPMACInstance(self):
        mock_ppmac = MockPpmac()
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


    #def test_writePrograms(self):
    #def test_writeAllPrograms(self):
    #def test_readAndStoreActiveElements(self):
    #def test_readAndStoreBufferedPrograms(self):

class TestPpmacRepositoryWriteRead(unittest.TestCase):
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.readSysMaxes")
    def setUp(self, mock_readsys):
        self.mock_ppmac = MockPpmac()
        self.obj = dls_ppmacanalyse.PPMACHardwareWriteRead(self.mock_ppmac)

    def test_init(self):
        assert self.obj.ppmacInstance == self.mock_ppmac
        assert self.obj.ppmacInstance.source == 'hardware'
        assert self.obj.remote_db_path == '/var/ftp/usrflash/Database'
        assert self.obj.local_db_path == './tmp/Database'
        assert self.obj.pp_swtbl0_txtfile == 'pp_swtbl0.txt'
        assert self.obj.pp_swtlbs_symfiles == ['pp_swtbl1.sym', 'pp_swtbl2.sym', 'pp_swtbl3.sym']

    def test_setPPMACInstance(self):
        mock_ppmac = MockPpmac()
        self.obj.setPPMACInstance(mock_ppmac)
        assert self.obj.ppmacInstance == mock_ppmac
        assert self.obj.ppmacInstance.source == 'hardware'

    @unittest.skip("need to mock sshClient sendCommand")
    @patch("dls_pmaclib.dls_pmacremote.PPmacSshInterface.sendCommand")
    #@patch("dls_pmacanalyse.dls_ppmacanalyse.sshClient.sendCommand")
    #@patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.sshClient.sendCommand")
    def test_getCommandReturnInt(self, mock_sendcmd):
        mock_sendcmd.return_value = ("0", True)
        assert self.obj.getCommandReturnInt("cmd") == 0
        mock_sendcmd.assert_called_with("cmd")

    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.getCommandReturnInt")
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

    @unittest.skip("need to mock sshClient sendCommand")
    @patch("dls_pmaclib.dls_pmacremote.PPmacSshInterface.sendCommand")
    def test_sendCommand(self, mock_sendcmd):
        mock_sendcmd.return_value = ("0\r0\r0\r\x06", True)
        assert self.obj.sendCommand("cmd") == ["0","0","0"]
        mock_sendcmd.assert_called_with("cmd")

    #def test_swtblFileToList(self):

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

    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.ignoreDataStructure")
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.getDataStructureCategory")
    def test_fillDataStructureIndices_i_ignore_true(self, mock_getcategory, mock_ignore):
        data_structure = "test.this[]"
        mock_getcategory.return_value = "test"
        mock_ignore.return_value = True
        self.obj.fillDataStructureIndices_i(data_structure, None, None)
        mock_getcategory.assert_called_with("test.this[]")
        mock_ignore.assert_called_with("test.this[0:]", None)

    @unittest.skip("need to mock sshClient sendCommand")
    @patch("dls_pmaclib.dls_pmacremote.PPmacSshInterface.sendCommand")
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.ignoreDataStructure")
    @patch("dls_pmacanalyse.dls_ppmacanalyse.PPMACHardwareWriteRead.getDataStructureCategory")
    def test_fillDataStructureIndices_i_ignore_false_illegalcmd(self, mock_getcategory, mock_ignore, mock_sendcmd):
        data_structure = "test.this[]"
        mock_getcategory.return_value = "test"
        mock_ignore.return_value = False
        mock_sendcmd.return_value = ["ILLEGAL", None]
        self.obj.fillDataStructureIndices_i(data_structure, None, None)
        mock_getcategory.assert_called_with("test.this[]")
        mock_ignore.assert_called_with("test.this[0:]", None)
        mock_sendcmd.assert_called_with("test.this[0]")
