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
        ControlForm.resize(1033, 600)
        self.centralwidget = QtWidgets.QWidget(ControlForm)
        self.centralwidget.setObjectName("centralwidget")
        self.textOutput = QtWidgets.QTextEdit(self.centralwidget)
        self.textOutput.setGeometry(QtCore.QRect(20, 260, 991, 171))
        self.textOutput.setObjectName("textOutput")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setGeometry(QtCore.QRect(20, 20, 991, 221))
        self.tabWidget.setObjectName("tabWidget")
        self.Backup = QtWidgets.QWidget()
        self.Backup.setObjectName("Backup")
        self.groupBox_4 = QtWidgets.QGroupBox(self.Backup)
        self.groupBox_4.setGeometry(QtCore.QRect(20, 10, 991, 171))
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
        self.lineServer = QtWidgets.QLineEdit(self.layoutWidget)
        self.lineServer.setObjectName("lineServer")
        self.gridLayout.addWidget(self.lineServer, 0, 1, 1, 1)
        self.textLabel2 = QtWidgets.QLabel(self.layoutWidget)
        self.textLabel2.setMinimumSize(QtCore.QSize(75, 27))
        self.textLabel2.setMaximumSize(QtCore.QSize(75, 27))
        self.textLabel2.setWordWrap(False)
        self.textLabel2.setObjectName("textLabel2")
        self.gridLayout.addWidget(self.textLabel2, 1, 0, 1, 1)
        self.linePort = QtWidgets.QLineEdit(self.layoutWidget)
        self.linePort.setObjectName("linePort")
        self.gridLayout.addWidget(self.linePort, 1, 1, 1, 1)
        self.groupBox_2 = QtWidgets.QGroupBox(self.groupBox_4)
        self.groupBox_2.setGeometry(QtCore.QRect(260, 30, 541, 141))
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
        self.lineIgnoreFile = QtWidgets.QLineEdit(self.layoutWidget2)
        self.lineIgnoreFile.setObjectName("lineIgnoreFile")
        self.gridLayout_2.addWidget(self.lineIgnoreFile, 0, 1, 1, 2)
        self.pushIgnoreLocate = QtWidgets.QPushButton(self.layoutWidget2)
        self.pushIgnoreLocate.setObjectName("pushIgnoreLocate")
        self.gridLayout_2.addWidget(self.pushIgnoreLocate, 0, 3, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.layoutWidget2)
        self.label_2.setObjectName("label_2")
        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 2)
        self.lineBackupLoc = QtWidgets.QLineEdit(self.layoutWidget2)
        self.lineBackupLoc.setObjectName("lineBackupLoc")
        self.gridLayout_2.addWidget(self.lineBackupLoc, 1, 2, 1, 1)
        self.pushDirLocate = QtWidgets.QPushButton(self.layoutWidget2)
        self.pushDirLocate.setObjectName("pushDirLocate")
        self.gridLayout_2.addWidget(self.pushDirLocate, 1, 3, 1, 1)
        self.groupBox_3 = QtWidgets.QGroupBox(self.groupBox_4)
        self.groupBox_3.setGeometry(QtCore.QRect(810, 30, 171, 131))
        self.groupBox_3.setObjectName("groupBox_3")
        self.pushBackup = QtWidgets.QPushButton(self.groupBox_3)
        self.pushBackup.setGeometry(QtCore.QRect(10, 30, 92, 36))
        self.pushBackup.setObjectName("pushBackup")
        self.pushCancelBackup = QtWidgets.QPushButton(self.groupBox_3)
        self.pushCancelBackup.setGeometry(QtCore.QRect(10, 70, 92, 36))
        self.pushCancelBackup.setObjectName("pushCancelBackup")
        self.tabWidget.addTab(self.Backup, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.groupBox_5 = QtWidgets.QGroupBox(self.tab_2)
        self.groupBox_5.setGeometry(QtCore.QRect(20, 10, 1001, 171))
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
        self.groupBox_7.setGeometry(QtCore.QRect(370, 30, 451, 121))
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
        self.lineIgnoreFile2 = QtWidgets.QLineEdit(self.layoutWidget_3)
        self.lineIgnoreFile2.setObjectName("lineIgnoreFile2")
        self.gridLayout_4.addWidget(self.lineIgnoreFile2, 0, 1, 1, 2)
        self.pushIgnoreLocate_2 = QtWidgets.QPushButton(self.layoutWidget_3)
        self.pushIgnoreLocate_2.setObjectName("pushIgnoreLocate_2")
        self.gridLayout_4.addWidget(self.pushIgnoreLocate_2, 0, 3, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.layoutWidget_3)
        self.label_4.setObjectName("label_4")
        self.gridLayout_4.addWidget(self.label_4, 1, 0, 1, 2)
        self.lineBackupLoc2 = QtWidgets.QLineEdit(self.layoutWidget_3)
        self.lineBackupLoc2.setObjectName("lineBackupLoc2")
        self.gridLayout_4.addWidget(self.lineBackupLoc2, 1, 2, 1, 1)
        self.pushDirLocate_2 = QtWidgets.QPushButton(self.layoutWidget_3)
        self.pushDirLocate_2.setObjectName("pushDirLocate_2")
        self.gridLayout_4.addWidget(self.pushDirLocate_2, 1, 3, 1, 1)
        self.groupBox_8 = QtWidgets.QGroupBox(self.groupBox_5)
        self.groupBox_8.setGeometry(QtCore.QRect(830, 30, 121, 121))
        self.groupBox_8.setObjectName("groupBox_8")
        self.pushCompare = QtWidgets.QPushButton(self.groupBox_8)
        self.pushCompare.setGeometry(QtCore.QRect(10, 30, 92, 36))
        self.pushCompare.setObjectName("pushCompare")
        self.pushCancelCompare = QtWidgets.QPushButton(self.groupBox_8)
        self.pushCancelCompare.setGeometry(QtCore.QRect(10, 70, 92, 36))
        self.pushCancelCompare.setObjectName("pushCancelCompare")
        self.tabWidget.addTab(self.tab_2, "")
        ControlForm.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(ControlForm)
        self.statusbar.setObjectName("statusbar")
        ControlForm.setStatusBar(self.statusbar)

        self.retranslateUi(ControlForm)
        self.tabWidget.setCurrentIndex(0)
        self.pushBackup.clicked.connect(ControlForm.runBackup)
        self.pushDirLocate.clicked.connect(ControlForm.backupLocationBrowser)
        self.pushIgnoreLocate.clicked.connect(ControlForm.ignoreFileBrowser)
        self.pushCompare.clicked.connect(ControlForm.runCompare)
        self.tabWidget.currentChanged['int'].connect(ControlForm.setMode)
        self.pushDirLocate_4.clicked.connect(ControlForm.source1LocationBrowser)
        self.pushDirLocate_3.clicked.connect(ControlForm.source2LocationBrowser)
        self.pushIgnoreLocate_2.clicked.connect(ControlForm.ignoreFileBrowser)
        self.pushDirLocate_2.clicked.connect(ControlForm.backupLocationBrowser)
        self.pushCancelBackup.clicked.connect(ControlForm.cancelBackup)
        self.pushCancelCompare.clicked.connect(ControlForm.cancelCompare)
        QtCore.QMetaObject.connectSlotsByName(ControlForm)

    def retranslateUi(self, ControlForm):
        _translate = QtCore.QCoreApplication.translate
        ControlForm.setWindowTitle(_translate("ControlForm", "Power-PMAC Analyse Tool"))
        self.groupBox_4.setTitle(_translate("ControlForm", "Power PMAC Backup Configuration"))
        self.groupBox.setTitle(_translate("ControlForm", "Connection to Power PMAC"))
        self.textLabel1.setText(_translate("ControlForm", "Server:"))
        self.lineServer.setToolTip(_translate("ControlForm", "Specify the IP address of the Power PMAC to backup"))
        self.textLabel2.setText(_translate("ControlForm", "Port:"))
        self.linePort.setToolTip(_translate("ControlForm", "Specify the port number of which to connect."))
        self.groupBox_2.setTitle(_translate("ControlForm", "Backup Options"))
        self.rdbActive.setToolTip(_translate("ControlForm", "Only back up the active elements, buffered programs and coordinate system axes definitions."))
        self.rdbActive.setText(_translate("ControlForm", "active"))
        self.rdbProject.setToolTip(_translate("ControlForm", "Only backup the saved and active Project files."))
        self.rdbProject.setText(_translate("ControlForm", "project"))
        self.rdbAll.setToolTip(_translate("ControlForm", "Back up everything."))
        self.rdbAll.setText(_translate("ControlForm", "all"))
        self.label.setText(_translate("ControlForm", "Ignore file:"))
        self.lineIgnoreFile.setToolTip(_translate("ControlForm", "Path to the file listing which data structures should be ignored."))
        self.pushIgnoreLocate.setText(_translate("ControlForm", "Browse"))
        self.label_2.setText(_translate("ControlForm", "Backup location:"))
        self.lineBackupLoc.setToolTip(_translate("ControlForm", "Directory in which the backup will be written."))
        self.pushDirLocate.setText(_translate("ControlForm", "Browse"))
        self.groupBox_3.setTitle(_translate("ControlForm", "Run"))
        self.pushBackup.setText(_translate("ControlForm", "Backup"))
        self.pushCancelBackup.setText(_translate("ControlForm", "Cancel"))
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
        self.lineIgnoreFile2.setToolTip(_translate("ControlForm", "Path to the file listing which data structures should be ignored."))
        self.pushIgnoreLocate_2.setText(_translate("ControlForm", "Browse"))
        self.label_4.setText(_translate("ControlForm", "Compare location:"))
        self.lineBackupLoc2.setToolTip(_translate("ControlForm", "Directory in which the compare will be written."))
        self.pushDirLocate_2.setText(_translate("ControlForm", "Browse"))
        self.groupBox_8.setTitle(_translate("ControlForm", "Run"))
        self.pushCompare.setText(_translate("ControlForm", "Compare"))
        self.pushCancelCompare.setText(_translate("ControlForm", "Cancel"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("ControlForm", "Compare"))
