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
    def __init__(self, parent=None):
        # signal.signal(2, self.signalHandler)
        # setup signals

        QMainWindow.__init__(self, parent)
        self.setupUi(self)

        # Mode - set by the tab index of the GUI
        # 0 = backup
        # 1 = compare
        # 2 = download/recover
        self.mode = 0 

        # Text colors
        self.blackColor = QColor(0, 0, 0)
        self.blueColor = QColor(0, 0, 255)
        self.redColor = QColor(255, 0, 0)

        # IP/Port 
        # 0 = backup
        # 2 = download/recover
        server = "192.168.56.10"
        port = "22"
        self.lineServer0.setText(server)
        self.linePort0.setText(port)
        self.lineServer2.setText(server)
        self.linePort2.setText(port)

        # Back-up options
        self.backupOption = "all"
        if self.backupOption == "all":
            self.rdbAll.setChecked(True)
        elif self.backupOption == "project":
            self.rdbProject.setChecked(True)
        elif self.backupOption == "active":
            self.rdbActive.setChecked(True)

        # Sources for compare
        source1 = "192.168.56.10:22"
        source2 = "./"
        self.lineSource1.setText(source1)
        self.lineSource2.setText(source2)

        # Ignore file location 
        # 0 = backup
        # 1 = compare
        ignoreFile = "/dls_sw/work/motion/PPMAC_TEST/ignore"
        self.lineIgnoreFile0.setText(ignoreFile)
        self.lineIgnoreFile1.setText(ignoreFile)
        
        # Results file location
        # 0 = backup
        # 1 = compare
        # 2 = download/recover
        outputLocation = "./ppmacAnalyse"
        self.lineOutputDir0.setText(outputLocation)
        self.lineOutputDir1.setText(outputLocation)
        self.lineOutputDir2.setText(outputLocation)

        # Backup file location for download/recover
        self.lineBackupDir.setText("./")

        # Cancel buttons
        # 0 = backup
        # 1 = compare
        # 2 = download/recover
        self.pushCancel0.setEnabled(False)
        self.pushCancel1.setEnabled(False)
        self.pushCancel2.setEnabled(False)
        self.cancelBackup = False
        self.cancelCompare = False
        self.cancelDR = False

    def runBackup(self):
        # Tab index 0
        server_name = self.lineServer0.text()
        server_port = self.linePort0.text()
        ignore_file = self.lineIgnoreFile0.text()
        output_dir = self.lineOutputDir0.text()
        backup_option = "all"
        if self.rdbProject.isChecked():
            backup_option = "project"
        elif self.rdbActive.isChecked():
            backup_option = "active"

        self.cancelBackup = False
        self.pushCancel0.setEnabled(True)

        cmd = [
            "dls-ppmac-analyse-cli.py",
            "--interface",
            str(server_name) + ":" + str(server_port),
            "--backup",
            backup_option,
            str(ignore_file),
            "--resultsdir",
            str(output_dir),
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

        self.pushCancel0.setEnabled(False)
        success = True
        stderrStr = ""
        for line in process.stderr:
            unicode_text = str(line, "utf-8")
            if unicode_text != "":
                success = False
                # Just save the last line with the root error
                stderrStr = unicode_text

        # stdout, stderr = process.communicate()
        if self.cancelBackup:
            self.addTextLog("Backup cancelled...")
            self.cancelBackup = False
        elif not success:
            self.addTextError("\nBackup failed with errors: \n" + stderrStr)
        else:
            self.addTextLog(
                "\nBackup completed in: " + str(time.time() - start) + " secs"
            )

    def runCompare(self):
        # Tab index 1
        source1 = self.lineSource1.text()
        source2 = self.lineSource2.text()
        ignore_file = self.lineIgnoreFile1.text()
        output_dir = self.lineOutputDir1.text()

        self.cancelCompare = False
        self.pushCancel1.setEnabled(True)

        cmd = [
            "dls-ppmac-analyse-cli.py",
            "--compare",
            source1,
            source2,
            str(ignore_file),
            "--resultsdir",
            str(output_dir),
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

        self.pushCancel1.setEnabled(False)

        success = True
        stderrStr = ""
        for line in process.stderr:
            unicode_text = str(line, "utf-8")
            if unicode_text != "":
                success = False
                # Just save the last line with the root error
                stderrStr = unicode_text

        # stdout, stderr = process.communicate()
        if self.cancelCompare:
            self.addTextLog("Compare cancelled...")
            self.cancelCompare = False
        elif not success:
            self.addTextError("\nBackup failed with errors: \n" + stderrStr)
        else:
            self.addTextLog(
                "\nCompare completed in: " + str(time.time() - start) + " secs"
            )

    def runDownloadRecover(self, commandStr):
        # Tab index 2
        server_name = self.lineServer2.text()
        server_port = self.linePort2.text()
        backup_dir = self.lineBackupDir.text()
        output_dir = self.lineOutputDir2.text()

        if commandStr == "download":
            backup_dir += "/project/active"
        elif commandStr == "recover":
            backup_dir += "/project/saved"
        else:
            self.addTextLog("Not a valid ppmac-analyse option")
            return

        self.cancelDR = False
        self.pushCancel2.setEnabled(True)

        cmd = [
            "dls-ppmac-analyse-cli.py",
            "--interface",
            str(server_name) + ":" + str(server_port),
            "--"+commandStr,
            str(backup_dir),
            "--resultsdir",
            str(output_dir),
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
            if self.cancelDR:
                self.addTextError("\nCancelling")
                process.kill()
            time.sleep(0.1)

        self.pushCancel2.setEnabled(False)
        success = True
        stderrStr = ""
        for line in process.stderr:
            unicode_text = str(line, "utf-8")
            if unicode_text != "":
                success = False
                # Just save the last line with the root error
                stderrStr = unicode_text

        # stdout, stderr = process.communicate()
        if self.cancelDR:
            self.addTextLog(commandStr + " cancelled...")
            self.cancelDR = False
        elif not success:
            self.addTextError("\nBackup failed with errors: \n" + stderrStr)
        else:
            self.addTextLog(
                "\n" + commandStr + " completed in: " + str(time.time() - start) + " secs"
            )

    def runDownload(self):
        self.runDownloadRecover("download")   

    def runRecover(self):
        self.runDownloadRecover("recover")           

    def cancelBackup(self):
        self.cancelBackup = True

    def cancelCompare(self):
        self.cancelCompare = True

    def cancelDR(self):
        self.cancelDR = True

    def ignoreFileBrowser(self):
        filename, _filter = QFileDialog.getOpenFileName()
        if filename != "":
            if self.mode == 0:
                self.lineIgnoreFile.setText(filename)
            elif self.mode == 1:
                self.lineIgnoreFile2.setText(filename)

    def outputDirBrowser(self):
        directory = QFileDialog.getExistingDirectory()
        if directory != "":
            if self.mode == 0:
                self.lineOutputDir0.setText(directory)
            elif self.mode == 1:
                self.lineOutputDir1.setText(directory)
            elif self.mode == 2:
                self.lineOutputDir2.setText(directory)    

    def backupDirBrowser(self):
        directory = QFileDialog.getExistingDirectory()
        if directory != "":
            self.lineBackupDir.setText(directory)

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

    app = QApplication(sys.argv)
    app.lastWindowClosed.connect(app.quit)
    win = Controlform()
    win.show()
    # catch CTRL-C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app.exec_()


if __name__ == "__main__":
    main()
