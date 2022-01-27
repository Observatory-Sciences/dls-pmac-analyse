import signal
import subprocess
import sys
import time
from optparse import OptionParser

from PyQt5 import QtWidgets
from PyQt5.QtGui import QColor, QTextCursor
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow

from dls_pmacanalyse.ui_formAnalyseControl import Ui_ControlForm


class Controlform(QtWidgets.QMainWindow, Ui_ControlForm):
    def __init__(self, options, parent=None):
        # signal.signal(2, self.signalHandler)
        # setup signals

        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        # Mode
        self.mode = 0  # backup

        # Colors
        self.blackColor = QColor(0, 0, 0)
        self.blueColor = QColor(0, 0, 255)
        self.redColor = QColor(255, 0, 0)

        # Connection
        self.lineServer.setText(options.server)
        self.linePort.setText(options.port)

        # Back up options
        self.backupOption = options.backupOpt
        if self.backupOption == "all":
            self.rdbAll.setChecked(True)
        elif self.backupOption == "project":
            self.rdbProject.setChecked(True)
        elif self.backupOption == "active":
            self.rdbActive.setChecked(True)

        # Compare sources
        self.lineSource1.setText(options.source1)
        self.lineSource2.setText(options.source2)

        # Ignore file location
        self.lineIgnoreFile.setText(options.ignoreFile)
        self.lineBackupLoc.setText(options.backupLocation)
        self.lineIgnoreFile2.setText(options.ignoreFile)
        self.lineBackupLoc2.setText(options.backupLocation)

        # Cancel buttons
        self.pushCancelBackup.setEnabled(False)
        self.pushCancelCompare.setEnabled(False)
        self.cancelBackup = False
        self.cancelCompare = False

    def runBackup(self):
        server_name = self.lineServer.text()
        server_port = self.linePort.text()
        ignore_file = self.lineIgnoreFile.text()
        backup_dir = self.lineBackupLoc.text()
        backup_option = "all"
        if self.rdbProject.isChecked():
            backup_option = "project"
        elif self.rdbActive.isChecked():
            backup_option = "active"

        self.cancelBackup = False
        self.pushCancelBackup.setEnabled(True)

        cmd = [
            "dls-ppmac-analyse.py",
            "--interface",
            str(server_name) + ":" + str(server_port),
            "--backup",
            backup_option,
            str(ignore_file),
            "--resultsdir",
            str(backup_dir),
        ]

        self.addTextLog("Running cmd: '" + str(" ".join(cmd)) + "'")
        start = time.time()

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addTextProgress("Working.")

        logInterval = time.time()

        while process.poll() is None:
            # Only log every second
            if time.time() - logInterval > 1:
                self.addTextProgress(".")
                logInterval = time.time()
            QApplication.processEvents()
            if self.cancelBackup:
                self.addTextError("\nCancelling")
                process.kill()
            time.sleep(0.1)

        self.pushCancelBackup.setEnabled(False)
        success = True
        stdoutStr = ""
        for line in process.stdout:
            unicode_text = str(line, "utf-8")
            if unicode_text != "":
                success = False
                stdoutStr += unicode_text

        # stdout, stderr = process.communicate()
        if self.cancelBackup:
            self.addTextLog("Backup cancelled...")
            self.cancelBackup = False
        elif not success:
            self.addTextError("\nBackup failed with errors: \n" + stdoutStr)
        else:
            self.addTextLog(
                "\nBackup completed in: " + str(time.time() - start) + " secs"
            )

    def runCompare(self):
        source1 = self.lineSource1.text()
        source2 = self.lineSource2.text()
        ignore_file = self.lineIgnoreFile2.text()
        backup_dir = self.lineBackupLoc2.text()

        self.cancelCompare = False
        self.pushCancelCompare.setEnabled(True)

        cmd = [
            "dls-ppmac-analyse.py",
            "--compare",
            source1,
            source2,
            str(ignore_file),
            "--resultsdir",
            str(backup_dir),
        ]

        self.addTextLog("Running cmd: '" + str(" ".join(cmd)) + "'")

        start = time.time()

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addTextProgress("Working.")

        logInterval = time.time()

        while process.poll() is None:
            # Only log every second
            if time.time() - logInterval > 1:
                self.addTextProgress(".")
                logInterval = time.time()
            QApplication.processEvents()
            if self.cancelCompare:
                self.addTextError("\nCancelling")
                process.kill()
            time.sleep(0.1)

        self.pushCancelCompare.setEnabled(False)

        success = True
        stdoutStr = ""
        for line in process.stdout:
            unicode_text = str(line, "utf-8")
            if unicode_text != "":
                success = False
                stdoutStr += unicode_text

        # stdout, stderr = process.communicate()
        if self.cancelCompare:
            self.addTextLog("Compare cancelled...")
            self.cancelCompare = False
        elif not success:
            self.addTextError("\nCompare failed with errors: \n" + stdoutStr)
        else:
            self.addTextLog(
                "\nCompare completed in: " + str(time.time() - start) + " secs"
            )

    def cancelBackup(self):
        self.cancelBackup = True

    def cancelCompare(self):
        self.cancelCompare = True

    def ignoreFileBrowser(self):
        filename, _filter = QFileDialog.getOpenFileName()
        if filename != "":
            if self.mode == 0:
                self.lineIgnoreFile.setText(filename)
            elif self.mode == 1:
                self.lineIgnoreFile2.setText(filename)

    def backupLocationBrowser(self):
        directory = QFileDialog.getExistingDirectory()
        if directory != "":
            if self.mode == 0:
                self.lineBackupLoc.setText(directory)
            elif self.mode == 1:
                self.lineBackupLoc2.setText(directory)

    def source1LocationBrowser(self):
        directory = QFileDialog.getExistingDirectory()
        if directory != "":
            self.lineSource1.setText(directory)

    def source2LocationBrowser(self):
        directory = QFileDialog.getExistingDirectory()
        if directory != "":
            self.lineSource2.setText(directory)

    def addTextLog(self, text):
        self.addTxtToOuput(text, True, self.blackColor)

    def addTextProgress(self, text):
        self.addTxtToOuput(text, False, self.blueColor)

    def addTextError(self, text):
        self.addTxtToOuput(text, True, self.redColor)

    def addTxtToOuput(self, text, insertNewLine, color):
        self.textOutput.setTextColor(color)
        if insertNewLine:
            self.textOutput.insertPlainText(text + "\n")
        else:
            self.textOutput.insertPlainText(text)
        self.textOutput.moveCursor(QTextCursor.End)

    def setMode(self, tabId):
        self.mode = tabId


def main():
    usage = """usage: %prog [options] %prog is a graphical frontend to the
    Deltatau motorcontroller known as PMAC."""
    parser = OptionParser(usage)
    parser.add_option(
        "-s",
        "--server",
        action="store",
        dest="server",
        default="192.168.56.10",
        help="Set server name (default: 192.168.56.10)",
    )
    parser.add_option(
        "-p",
        "--port",
        action="store",
        dest="port",
        default="22",
        help="Set IP port number to connect to (default: 22)",
    )
    parser.add_option(
        "-b",
        "--backup",
        action="store",
        dest="backupOpt",
        default="all",
        help="Set backup option (default: all)",
    )
    parser.add_option(
        "-i",
        "--ignoreFile",
        action="store",
        dest="ignoreFile",
        default="/dls_sw/work/motion/PPMAC_TEST/ignore",
        help="Specify ignore file location"
        + " (default: /dls_sw/work/motion/PPMAC_TEST/ignore)",
    )
    parser.add_option(
        "-f",
        "--backupLocation",
        action="store",
        dest="backupLocation",
        default="./",
        help="Specify the location to create backup (default: ./)",
    )
    parser.add_option(
        "",
        "--source1",
        action="store",
        dest="source1",
        default="192.168.56.10:22",
        help="Specify the first source to comparre (default: 192.168.56.10:22)",
    )
    parser.add_option(
        "",
        "--source2",
        action="store",
        dest="source2",
        default="./",
        help="Specify the second source to comparre (default: ./)",
    )
    (options, args) = parser.parse_args()
    app = QApplication(sys.argv)
    app.lastWindowClosed.connect(app.quit)
    win = Controlform(options)
    win.show()
    # catch CTRL-C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.exec_()


if __name__ == "__main__":
    main()
