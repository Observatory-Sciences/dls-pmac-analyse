# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dls_pmacanalyse/formAnalyseControl.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_ControlForm(object):
    def setupUi(self, ControlForm):
        ControlForm.setObjectName("ControlForm")
        ControlForm.resize(1038, 600)
        self.centralwidget = QtWidgets.QWidget(ControlForm)
        self.centralwidget.setObjectName("centralwidget")
        self.textOutput = QtWidgets.QTextEdit(self.centralwidget)
        self.textOutput.setGeometry(QtCore.QRect(20, 260, 991, 281))
        self.textOutput.setObjectName("textOutput")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(20, 20, 991, 221))
        self.tabWidget.setObjectName("tabWidget")
        self.Backup = QtWidgets.QWidget()
        self.Backup.setObjectName("Backup")
        self.groupBox_4 = QtWidgets.QGroupBox(self.Backup)
        self.groupBox_4.setGeometry(QtCore.QRect(10, 10, 951, 171))
        self.groupBox_4.setObjectName("groupBox_4")
        self.groupBox = QtWidgets.QGroupBox(self.groupBox_4)
        self.groupBox.setGeometry(QtCore.QRect(10, 30, 241, 131))
        self.groupBox.setObjectName("groupBox")
        self.layoutWidget = QtWidgets.QWidget(self.groupBox)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 30, 220, 80))
        self.layoutWidget.setObjectName("layoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.layoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.textLabel1 = QtWidgets.QLabel(self.layoutWidget)
        self.textLabel1.setMinimumSize(QtCore.QSize(75, 27))
        self.textLabel1.setMaximumSize(QtCore.QSize(75, 25))
        self.textLabel1.setWordWrap(False)
        self.textLabel1.setObjectName("textLabel1")
        self.gridLayout.addWidget(self.textLabel1, 0, 0, 1, 1)
        self.lineServer0 = QtWidgets.QLineEdit(self.layoutWidget)
        self.lineServer0.setObjectName("lineServer0")
        self.gridLayout.addWidget(self.lineServer0, 0, 1, 1, 1)
        self.textLabel2 = QtWidgets.QLabel(self.layoutWidget)
        self.textLabel2.setMinimumSize(QtCore.QSize(75, 27))
        self.textLabel2.setMaximumSize(QtCore.QSize(75, 27))
        self.textLabel2.setWordWrap(False)
        self.textLabel2.setObjectName("textLabel2")
        self.gridLayout.addWidget(self.textLabel2, 1, 0, 1, 1)
        self.linePort0 = QtWidgets.QLineEdit(self.layoutWidget)
        self.linePort0.setObjectName("linePort0")
        self.gridLayout.addWidget(self.linePort0, 1, 1, 1, 1)
        self.groupBox_2 = QtWidgets.QGroupBox(self.groupBox_4)
        self.groupBox_2.setGeometry(QtCore.QRect(260, 30, 541, 131))
        self.groupBox_2.setObjectName("groupBox_2")
        self.layoutWidget1 = QtWidgets.QWidget(self.groupBox_2)
        self.layoutWidget1.setGeometry(QtCore.QRect(10, 31, 77, 92))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.rdbActive = QtWidgets.QRadioButton(self.layoutWidget1)
        self.rdbActive.setObjectName("rdbActive")
        self.verticalLayout.addWidget(self.rdbActive)
        self.rdbProject = QtWidgets.QRadioButton(self.layoutWidget1)
        self.rdbProject.setObjectName("rdbProject")
        self.verticalLayout.addWidget(self.rdbProject)
        self.rdbAll = QtWidgets.QRadioButton(self.layoutWidget1)
        self.rdbAll.setObjectName("rdbAll")
        self.verticalLayout.addWidget(self.rdbAll)
        self.layoutWidget2 = QtWidgets.QWidget(self.groupBox_2)
        self.layoutWidget2.setGeometry(QtCore.QRect(100, 30, 431, 80))
        self.layoutWidget2.setObjectName("layoutWidget2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.layoutWidget2)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.label = QtWidgets.QLabel(self.layoutWidget2)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)
        self.lineIgnoreFile0 = QtWidgets.QLineEdit(self.layoutWidget2)
        self.lineIgnoreFile0.setObjectName("lineIgnoreFile0")
        self.gridLayout_2.addWidget(self.lineIgnoreFile0, 0, 1, 1, 2)
        self.pushIgnoreLocate = QtWidgets.QPushButton(self.layoutWidget2)
        self.pushIgnoreLocate.setObjectName("pushIgnoreLocate")
        self.gridLayout_2.addWidget(self.pushIgnoreLocate, 0, 3, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.layoutWidget2)
        self.label_2.setObjectName("label_2")
        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 2)
        self.lineOutputDir0 = QtWidgets.QLineEdit(self.layoutWidget2)
        self.lineOutputDir0.setObjectName("lineOutputDir0")
        self.gridLayout_2.addWidget(self.lineOutputDir0, 1, 2, 1, 1)
        self.pushDirLocate = QtWidgets.QPushButton(self.layoutWidget2)
        self.pushDirLocate.setObjectName("pushDirLocate")
        self.gridLayout_2.addWidget(self.pushDirLocate, 1, 3, 1, 1)
        self.groupBox_3 = QtWidgets.QGroupBox(self.groupBox_4)
        self.groupBox_3.setGeometry(QtCore.QRect(810, 30, 111, 131))
        self.groupBox_3.setObjectName("groupBox_3")
        self.pushBackup = QtWidgets.QPushButton(self.groupBox_3)
        self.pushBackup.setGeometry(QtCore.QRect(10, 30, 92, 36))
        self.pushBackup.setObjectName("pushBackup")
        self.pushCancel0 = QtWidgets.QPushButton(self.groupBox_3)
        self.pushCancel0.setGeometry(QtCore.QRect(10, 70, 92, 36))
        self.pushCancel0.setObjectName("pushCancel0")
        self.tabWidget.addTab(self.Backup, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.groupBox_5 = QtWidgets.QGroupBox(self.tab_2)
        self.groupBox_5.setGeometry(QtCore.QRect(10, 10, 951, 171))
        self.groupBox_5.setObjectName("groupBox_5")
        self.groupBox_6 = QtWidgets.QGroupBox(self.groupBox_5)
        self.groupBox_6.setGeometry(QtCore.QRect(10, 30, 341, 121))
        self.groupBox_6.setObjectName("groupBox_6")
        self.widget = QtWidgets.QWidget(self.groupBox_6)
        self.widget.setGeometry(QtCore.QRect(11, 28, 314, 80))
        self.widget.setObjectName("widget")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.widget)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.textLabel1_2 = QtWidgets.QLabel(self.widget)
        self.textLabel1_2.setMinimumSize(QtCore.QSize(75, 27))
        self.textLabel1_2.setMaximumSize(QtCore.QSize(75, 25))
        self.textLabel1_2.setWordWrap(False)
        self.textLabel1_2.setObjectName("textLabel1_2")
        self.gridLayout_3.addWidget(self.textLabel1_2, 0, 0, 1, 1)
        self.lineSource1 = QtWidgets.QLineEdit(self.widget)
        self.lineSource1.setObjectName("lineSource1")
        self.gridLayout_3.addWidget(self.lineSource1, 0, 1, 1, 1)
        self.pushDirLocate_4 = QtWidgets.QPushButton(self.widget)
        self.pushDirLocate_4.setObjectName("pushDirLocate_4")
        self.gridLayout_3.addWidget(self.pushDirLocate_4, 0, 2, 1, 1)
        self.textLabel1_3 = QtWidgets.QLabel(self.widget)
        self.textLabel1_3.setMinimumSize(QtCore.QSize(75, 27))
        self.textLabel1_3.setMaximumSize(QtCore.QSize(75, 25))
        self.textLabel1_3.setWordWrap(False)
        self.textLabel1_3.setObjectName("textLabel1_3")
        self.gridLayout_3.addWidget(self.textLabel1_3, 1, 0, 1, 1)
        self.lineSource2 = QtWidgets.QLineEdit(self.widget)
        self.lineSource2.setObjectName("lineSource2")
        self.gridLayout_3.addWidget(self.lineSource2, 1, 1, 1, 1)
        self.pushDirLocate_3 = QtWidgets.QPushButton(self.widget)
        self.pushDirLocate_3.setObjectName("pushDirLocate_3")
        self.gridLayout_3.addWidget(self.pushDirLocate_3, 1, 2, 1, 1)
        self.groupBox_7 = QtWidgets.QGroupBox(self.groupBox_5)
        self.groupBox_7.setGeometry(QtCore.QRect(360, 30, 451, 121))
        self.groupBox_7.setObjectName("groupBox_7")
        self.layoutWidget_3 = QtWidgets.QWidget(self.groupBox_7)
        self.layoutWidget_3.setGeometry(QtCore.QRect(10, 30, 431, 80))
        self.layoutWidget_3.setObjectName("layoutWidget_3")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.layoutWidget_3)
        self.gridLayout_4.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.label_3 = QtWidgets.QLabel(self.layoutWidget_3)
        self.label_3.setObjectName("label_3")
        self.gridLayout_4.addWidget(self.label_3, 0, 0, 1, 1)
        self.lineIgnoreFile1 = QtWidgets.QLineEdit(self.layoutWidget_3)
        self.lineIgnoreFile1.setObjectName("lineIgnoreFile1")
        self.gridLayout_4.addWidget(self.lineIgnoreFile1, 0, 1, 1, 2)
        self.pushIgnoreLocate_2 = QtWidgets.QPushButton(self.layoutWidget_3)
        self.pushIgnoreLocate_2.setObjectName("pushIgnoreLocate_2")
        self.gridLayout_4.addWidget(self.pushIgnoreLocate_2, 0, 3, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.layoutWidget_3)
        self.label_4.setObjectName("label_4")
        self.gridLayout_4.addWidget(self.label_4, 1, 0, 1, 2)
        self.lineOutputDir1 = QtWidgets.QLineEdit(self.layoutWidget_3)
        self.lineOutputDir1.setObjectName("lineOutputDir1")
        self.gridLayout_4.addWidget(self.lineOutputDir1, 1, 2, 1, 1)
        self.pushDirLocate_2 = QtWidgets.QPushButton(self.layoutWidget_3)
        self.pushDirLocate_2.setObjectName("pushDirLocate_2")
        self.gridLayout_4.addWidget(self.pushDirLocate_2, 1, 3, 1, 1)
        self.groupBox_8 = QtWidgets.QGroupBox(self.groupBox_5)
        self.groupBox_8.setGeometry(QtCore.QRect(820, 30, 111, 121))
        self.groupBox_8.setObjectName("groupBox_8")
        self.pushCompare = QtWidgets.QPushButton(self.groupBox_8)
        self.pushCompare.setGeometry(QtCore.QRect(10, 30, 92, 36))
        self.pushCompare.setObjectName("pushCompare")
        self.pushCancel1 = QtWidgets.QPushButton(self.groupBox_8)
        self.pushCancel1.setGeometry(QtCore.QRect(10, 70, 92, 36))
        self.pushCancel1.setObjectName("pushCancel1")
        self.tabWidget.addTab(self.tab_2, "")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.groupBox_9 = QtWidgets.QGroupBox(self.tab)
        self.groupBox_9.setGeometry(QtCore.QRect(10, 10, 971, 161))
        self.groupBox_9.setObjectName("groupBox_9")
        self.groupBox_10 = QtWidgets.QGroupBox(self.groupBox_9)
        self.groupBox_10.setGeometry(QtCore.QRect(10, 30, 241, 121))
        self.groupBox_10.setObjectName("groupBox_10")
        self.layoutWidget_2 = QtWidgets.QWidget(self.groupBox_10)
        self.layoutWidget_2.setGeometry(QtCore.QRect(10, 30, 220, 80))
        self.layoutWidget_2.setObjectName("layoutWidget_2")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.layoutWidget_2)
        self.gridLayout_5.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.textLabel1_4 = QtWidgets.QLabel(self.layoutWidget_2)
        self.textLabel1_4.setMinimumSize(QtCore.QSize(75, 27))
        self.textLabel1_4.setMaximumSize(QtCore.QSize(75, 25))
        self.textLabel1_4.setWordWrap(False)
        self.textLabel1_4.setObjectName("textLabel1_4")
        self.gridLayout_5.addWidget(self.textLabel1_4, 0, 0, 1, 1)
        self.lineServer2 = QtWidgets.QLineEdit(self.layoutWidget_2)
        self.lineServer2.setObjectName("lineServer2")
        self.gridLayout_5.addWidget(self.lineServer2, 0, 1, 1, 1)
        self.textLabel2_2 = QtWidgets.QLabel(self.layoutWidget_2)
        self.textLabel2_2.setMinimumSize(QtCore.QSize(75, 27))
        self.textLabel2_2.setMaximumSize(QtCore.QSize(75, 27))
        self.textLabel2_2.setWordWrap(False)
        self.textLabel2_2.setObjectName("textLabel2_2")
        self.gridLayout_5.addWidget(self.textLabel2_2, 1, 0, 1, 1)
        self.linePort2 = QtWidgets.QLineEdit(self.layoutWidget_2)
        self.linePort2.setObjectName("linePort2")
        self.gridLayout_5.addWidget(self.linePort2, 1, 1, 1, 1)
        self.groupBox_11 = QtWidgets.QGroupBox(self.groupBox_9)
        self.groupBox_11.setGeometry(QtCore.QRect(260, 30, 481, 121))
        self.groupBox_11.setObjectName("groupBox_11")
        self.layoutWidget_5 = QtWidgets.QWidget(self.groupBox_11)
        self.layoutWidget_5.setGeometry(QtCore.QRect(10, 30, 461, 80))
        self.layoutWidget_5.setObjectName("layoutWidget_5")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.layoutWidget_5)
        self.gridLayout_6.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.label_5 = QtWidgets.QLabel(self.layoutWidget_5)
        self.label_5.setObjectName("label_5")
        self.gridLayout_6.addWidget(self.label_5, 0, 0, 1, 1)
        self.lineBackupDir = QtWidgets.QLineEdit(self.layoutWidget_5)
        self.lineBackupDir.setObjectName("lineBackupDir")
        self.gridLayout_6.addWidget(self.lineBackupDir, 0, 1, 1, 2)
        self.pushBackupDir = QtWidgets.QPushButton(self.layoutWidget_5)
        self.pushBackupDir.setObjectName("pushBackupDir")
        self.gridLayout_6.addWidget(self.pushBackupDir, 0, 3, 1, 1)
        self.label_6 = QtWidgets.QLabel(self.layoutWidget_5)
        self.label_6.setObjectName("label_6")
        self.gridLayout_6.addWidget(self.label_6, 1, 0, 1, 2)
        self.lineOutputDir2 = QtWidgets.QLineEdit(self.layoutWidget_5)
        self.lineOutputDir2.setObjectName("lineOutputDir2")
        self.gridLayout_6.addWidget(self.lineOutputDir2, 1, 2, 1, 1)
        self.pushOutputDir = QtWidgets.QPushButton(self.layoutWidget_5)
        self.pushOutputDir.setObjectName("pushOutputDir")
        self.gridLayout_6.addWidget(self.pushOutputDir, 1, 3, 1, 1)
        self.groupBox_12 = QtWidgets.QGroupBox(self.groupBox_9)
        self.groupBox_12.setGeometry(QtCore.QRect(750, 30, 211, 121))
        self.groupBox_12.setObjectName("groupBox_12")
        self.pushDownload = QtWidgets.QPushButton(self.groupBox_12)
        self.pushDownload.setGeometry(QtCore.QRect(10, 30, 92, 36))
        self.pushDownload.setObjectName("pushDownload")
        self.pushCancel2 = QtWidgets.QPushButton(self.groupBox_12)
        self.pushCancel2.setGeometry(QtCore.QRect(60, 70, 92, 36))
        self.pushCancel2.setObjectName("pushCancel2")
        self.pushRecover = QtWidgets.QPushButton(self.groupBox_12)
        self.pushRecover.setGeometry(QtCore.QRect(110, 30, 92, 36))
        self.pushRecover.setObjectName("pushRecover")
        self.tabWidget.addTab(self.tab, "")
        ControlForm.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(ControlForm)
        self.statusbar.setObjectName("statusbar")
        ControlForm.setStatusBar(self.statusbar)

        self.retranslateUi(ControlForm)
        self.tabWidget.setCurrentIndex(0)
        self.pushBackup.clicked.connect(ControlForm.runBackup)
        self.pushIgnoreLocate.clicked.connect(ControlForm.ignoreFileBrowser)
        self.pushCompare.clicked.connect(ControlForm.runCompare)
        self.tabWidget.currentChanged['int'].connect(ControlForm.setMode)
        self.pushDirLocate_4.clicked.connect(ControlForm.source1LocationBrowser)
        self.pushDirLocate_3.clicked.connect(ControlForm.source2LocationBrowser)
        self.pushIgnoreLocate_2.clicked.connect(ControlForm.ignoreFileBrowser)
        self.pushCancel0.clicked.connect(ControlForm.cancelBackup)
        self.pushCancel1.clicked.connect(ControlForm.cancelCompare)
        self.pushDownload.clicked.connect(ControlForm.runDownload)
        self.pushRecover.clicked.connect(ControlForm.runRecover)
        self.pushCancel2.clicked.connect(ControlForm.cancelDR)
        self.pushDirLocate.clicked.connect(ControlForm.outputDirBrowser)
        self.pushDirLocate_2.clicked.connect(ControlForm.outputDirBrowser)
        self.pushBackupDir.clicked.connect(ControlForm.backupDirBrowser)
        self.pushOutputDir.clicked.connect(ControlForm.outputDirBrowser)
        QtCore.QMetaObject.connectSlotsByName(ControlForm)

    def retranslateUi(self, ControlForm):
        _translate = QtCore.QCoreApplication.translate
        ControlForm.setWindowTitle(_translate("ControlForm", "Power-PMAC Analyse Tool"))
        self.groupBox_4.setTitle(_translate("ControlForm", "Power PMAC Backup Configuration"))
        self.groupBox.setTitle(_translate("ControlForm", "Connection to Power PMAC"))
        self.textLabel1.setText(_translate("ControlForm", "Server:"))
        self.lineServer0.setToolTip(_translate("ControlForm", "Specify the IP address of the Power PMAC to backup"))
        self.textLabel2.setText(_translate("ControlForm", "Port:"))
        self.linePort0.setToolTip(_translate("ControlForm", "Specify the port number of which to connect."))
        self.groupBox_2.setTitle(_translate("ControlForm", "Backup Options"))
        self.rdbActive.setToolTip(_translate("ControlForm", "Only back up the active elements, buffered programs and coordinate system axes definitions."))
        self.rdbActive.setText(_translate("ControlForm", "active"))
        self.rdbProject.setToolTip(_translate("ControlForm", "Only backup the saved and active Project files."))
        self.rdbProject.setText(_translate("ControlForm", "project"))
        self.rdbAll.setToolTip(_translate("ControlForm", "Back up everything."))
        self.rdbAll.setText(_translate("ControlForm", "all"))
        self.label.setText(_translate("ControlForm", "Ignore file:"))
        self.lineIgnoreFile0.setToolTip(_translate("ControlForm", "Path to the file listing which data structures should be ignored."))
        self.pushIgnoreLocate.setText(_translate("ControlForm", "Browse"))
        self.label_2.setText(_translate("ControlForm", "Output directory:"))
        self.lineOutputDir0.setToolTip(_translate("ControlForm", "Directory in which the Backup and log will be written."))
        self.pushDirLocate.setText(_translate("ControlForm", "Browse"))
        self.groupBox_3.setTitle(_translate("ControlForm", "Run"))
        self.pushBackup.setToolTip(_translate("ControlForm", "Backup the Power PMAC to a local file."))
        self.pushBackup.setText(_translate("ControlForm", "Backup"))
        self.pushCancel0.setToolTip(_translate("ControlForm", "Cancel the current action."))
        self.pushCancel0.setText(_translate("ControlForm", "Cancel"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Backup), _translate("ControlForm", "Backup"))
        self.groupBox_5.setTitle(_translate("ControlForm", "Power PMAC Compare Configuration"))
        self.groupBox_6.setTitle(_translate("ControlForm", "Compare sources"))
        self.textLabel1_2.setText(_translate("ControlForm", "Source 1"))
        self.lineSource1.setToolTip(_translate("ControlForm", "<html><head/><body><p>Source to compare can be:</p><p>  - path to a back-up directory</p><p>  - a network interface &lt;ip.address&gt;:&lt;port&gt; </p></body></html>"))
        self.pushDirLocate_4.setText(_translate("ControlForm", "Browse"))
        self.textLabel1_3.setText(_translate("ControlForm", "Source 2"))
        self.lineSource2.setToolTip(_translate("ControlForm", "<html><head/><body><p>Source to compare can be:</p><p>  - path to a back-up directory</p><p>  - a network interface &lt;ip.address&gt;:&lt;port&gt; </p></body></html>"))
        self.pushDirLocate_3.setText(_translate("ControlForm", "Browse"))
        self.groupBox_7.setTitle(_translate("ControlForm", "Compare Options"))
        self.label_3.setText(_translate("ControlForm", "Ignore file:"))
        self.lineIgnoreFile1.setToolTip(_translate("ControlForm", "Path to the file listing which data structures should be ignored."))
        self.pushIgnoreLocate_2.setText(_translate("ControlForm", "Browse"))
        self.label_4.setText(_translate("ControlForm", "Output directory:"))
        self.lineOutputDir1.setToolTip(_translate("ControlForm", "Directory in which the Compare information and log will be written."))
        self.pushDirLocate_2.setText(_translate("ControlForm", "Browse"))
        self.groupBox_8.setTitle(_translate("ControlForm", "Run"))
        self.pushCompare.setToolTip(_translate("ControlForm", "Compare two sources and save the output."))
        self.pushCompare.setText(_translate("ControlForm", "Compare"))
        self.pushCancel1.setToolTip(_translate("ControlForm", "Cancel the current action."))
        self.pushCancel1.setText(_translate("ControlForm", "Cancel"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("ControlForm", "Compare"))
        self.groupBox_9.setTitle(_translate("ControlForm", "Power PMAC Download/Recover Configuration"))
        self.groupBox_10.setTitle(_translate("ControlForm", "Connection to Power PMAC"))
        self.textLabel1_4.setText(_translate("ControlForm", "Server:"))
        self.lineServer2.setToolTip(_translate("ControlForm", "Specify the IP address of the Power PMAC to download to."))
        self.textLabel2_2.setText(_translate("ControlForm", "Port:"))
        self.linePort2.setToolTip(_translate("ControlForm", "Specify the port number of which to connect."))
        self.groupBox_11.setTitle(_translate("ControlForm", "Download/Recover Options"))
        self.label_5.setText(_translate("ControlForm", "Backup location:"))
        self.lineBackupDir.setToolTip(_translate("ControlForm", "Location of the backup (output directory from running a Backup)."))
        self.pushBackupDir.setText(_translate("ControlForm", "Browse"))
        self.label_6.setText(_translate("ControlForm", "Output directory:"))
        self.lineOutputDir2.setToolTip(_translate("ControlForm", "Output directory for the log file."))
        self.pushOutputDir.setText(_translate("ControlForm", "Browse"))
        self.groupBox_12.setTitle(_translate("ControlForm", "Run"))
        self.pushDownload.setToolTip(_translate("ControlForm", "<html><head/><body><p>Copied the specified built projects into the active project site of the Power PMAC (/var/ftp/usrflash/Project) and then loads it into active memory.</p></body></html>"))
        self.pushDownload.setText(_translate("ControlForm", "Download"))
        self.pushCancel2.setToolTip(_translate("ControlForm", "Cancel the current action."))
        self.pushCancel2.setText(_translate("ControlForm", "Cancel"))
        self.pushRecover.setToolTip(_translate("ControlForm", "<html><head/><body><p>Restore a previous saved configuration. Project, Database and Temp directories which have been copied from the /opt/ppmac/usrflash site on the Power PMAC are copied back into that site and the Project will become active upon power cycling the Power PMAC.</p></body></html>"))
        self.pushRecover.setText(_translate("ControlForm", "Recover"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("ControlForm", "Download/Recover"))