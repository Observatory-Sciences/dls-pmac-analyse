import argparse
import difflib
import logging
import os
import re
import sys
import time

import numpy as np
from dls_pmaclib import dls_pmacremote
from scp import SCPClient
import dls_pmacanalyse.ppmacanalyse_control


def timer(func):
    def measureExecutionTime(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        logging.info(
            "Processing time of %s(): %.2f seconds."
            % (func.__qualname__, time.time() - startTime)
        )
        return result

    return measureExecutionTime


def connectDisconnect(func):
    def wrapped_func(self, *args):
        sshClient.port = self.port
        sshClient.hostname = self.ipAddress
        sshClient.connect()
        func(self, *args)
        sshClient.disconnect()

    return wrapped_func


def fileExists(file):
    return os.path.isfile(file)


def parseArgs():
    parser = argparse.ArgumentParser(
        description="Interact with a Power PMAC",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--interface",
        metavar="",
        nargs=1,
        help=(
            "Network interface address of Power PMAC.\n--interface <ip address>:<port>."
        ),
    )
    parser.add_argument(
        "-b",
        "--backup",
        metavar="",
        nargs="*",
        help=(
            "Back-up configuration of Power PMAC.\n"
            "--backup <type>/<type> <ignore>\n"
            "<type> = all/active/project\n"
            "<ignore> = path to ignore file"
        ),
    )
    parser.add_argument(
        "-r",
        "--recover",
        metavar="",
        nargs=1,
        help=(
            "Recover configuration of Power PMAC using the recovery"
            "stick method.\n"
            "--recover <usrflash dir>\n"
            "<usrflash dir> = local copy of the /opt/ppmac/usrflash\n"
            "directory on a Power PMAC."
        ),
    )
    parser.add_argument(
        "-c",
        "--compare",
        metavar="",
        nargs="*",
        help=(
            "Compare configuration of two Power PMACs.\n--compare <source_a> <source_b>"
            " <ignore_file>\n<source_a> and <source_b> define"
            " the two sources to compare. They can \ntake the form of a path to a"
            " back-up directory or a network interface <ip_address>:<port>.\n<ignore"
            " file> is the path to the file listing which data structures should be"
            " ignored."
        ),
    )
    parser.add_argument(
        "-d",
        "--download",
        metavar="",
        nargs=1,
        help=(
            "Download configuration onto Power PMAC.\n"
            "--download <usrflash dir>\n"
            "<project dir> = local copy of the /var/ftp/usrflash/Project\n"
            "directory on a Power PMAC."
        ),
    )
    parser.add_argument(
        "-f",
        "--resultsdir",
        metavar="",
        nargs=1,
        help=(
            "Directory in which to place output of analysis.\n"
            "--resultsdir <results dir>"
        ),
    )
    parser.add_argument(
        "-g",
        "--gui",
        action="store_true",
        help=(
            "Launch Power PMAC analyse GUI."
        ),
    )
    parser.add_argument(
        "-u",
        "--username",
        metavar="",
        nargs=1,
        help=(
            "Power PMAC username"
        ),
    )
    parser.add_argument(
        "-p",
        "--password",
        metavar="",
        nargs=1,
        help=(
            "Power Pmac password"
        ),
    )
    parser.add_argument("-n", "--name", metavar="", nargs=1, help="Name of Power PMAC.")
    return parser.parse_args()


def isValidNetworkInterface(interface):
    interfaceSplit = interface.split(":")
    if len(interfaceSplit) != 2:
        return False
    ipAddress = interfaceSplit[0]
    port = interfaceSplit[1]
    isValid = False
    if "." in ipAddress:
        elems = ipAddress.strip().split(".")
        if len(elems) == 4:
            for i in elems:
                if i.isnumeric() and int(i) >= 0 and int(i) <= 255:
                    isValid = True
                else:
                    isValid = False
                    break
    if not port.isnumeric():
        isValid = False
    return isValid


def exitGpascii():
    (exitGpascii, status) = sshClient.sendCommand("\x03")
    if not status:
        raise IOError("Failed to exit gpascii.")


def executeRemoteShellCommand(cmd):
    """
    Execute a command on a remote server. The call to stdout.channel.recv_exit_status()
    blocks until the resulting
    process on the remote server has finished.
    :param cmd: string containing command to be executed.
    :return:
    """
    logging.info(f"Executing '{cmd}' on remote server...")
    stdin, stdout, stderr = sshClient.client.exec_command(cmd)
    if stdout.channel.recv_exit_status() != 0:
        raise RuntimeError(f"Error executing command {cmd} on remote machine.")
    logging.info(f"Command wrote to stdout '{stdout.read()}'.")


def scpFromPowerPMACtoLocal(source, destination, recursive=True):
    logging.info(
        f"scp files/dirs '{source}' from remote server into local dir '{destination}'."
    )
    try:
        scp = SCPClient(sshClient.client.get_transport(), sanitize=lambda x: x)
        scp.get(source, destination, recursive)
        scp.close()
    except Exception as e:
        print(f"Error: {e}, unable to get directory from remote host: {source}")


def scpFromLocalToPowerPMAC(files, remote_path, recursive=False):
    logging.info(
        f"scp files/dirs '{files}' into remote server directory '{remote_path}'."
    )
    try:
        scp = SCPClient(sshClient.client.get_transport(), sanitize=lambda x: x)
        scp.put(files, remote_path, recursive)
        scp.close()
    except Exception as e:
        print(f"Error: {e}, unable to copy files {files} to remote path: {remote_path}")


def nthRepl(s, sub, repl, nth):
    find = s.find(sub)
    i = find != -1
    while find != -1 and i != nth:
        find = s.find(sub, find + 1)
        i += 1
    if i == nth:
        return s[:find] + repl + s[find + len(sub) :]
    return s


def find_nth(s, sub, n):
    start = s.find(sub)
    while start >= 0 and n > 1:
        start = s.find(sub, start + len(sub))
        n -= 1
    return start


def responseListToDict(responseList, splitChars="="):
    responseDict = {}
    if responseList != ["", ""]:
        for element in responseList:
            nameVal = element.split(splitChars)
            responseDict[nameVal[0]] = nameVal[1]
    return responseDict


def mergeDicts(*dict_args):
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def comparedicts(d1, d2):
    d1Keys = set(d1.keys())
    d2Keys = set(d2.keys())
    shared_keys = d1Keys.intersection(d2Keys)
    added = d1Keys - d2Keys
    removed = d2Keys - d1Keys
    modified = {o: (d1[o], d2[o]) for o in shared_keys if d1[o] != d2[o]}
    same = set(o for o in shared_keys if d1[o] == d2[o])
    return added, removed, modified, same


recoveryCmds = """
#!/bin/bash

echo "Entering /tmp/recover." > /tmp/recover.log 2>&1
cd /tmp/recover
if [[ $? -ne 0 ]] ; then
    echo "Unable to cd into /tmp/recover. Exiting." >> /tmp/recover.log 2>&1
    exit 1
fi

echo "Starting sync." >> /tmp/recover.log 2>&1
echo "Mounting /opt file system as read/write" >> /tmp/recover.log 2>&1
mount -o remount,rw /opt/ >> /tmp/recover.log 2>&1

# Copy backup files into /opt/ppmac/usrflash
echo "Copying backup files into /opt/ppmac/usrflash/" >> /tmp/recover.log
cp -a * /opt/ppmac/usrflash/ >> /tmp/recover.log 2>&1

echo "Syncing file system." >> /tmp/recover.log 2>&1
sync >> /tmp/recover.log 2>&1

echo "Mounting /opt file system as read only." >> /tmp/recover.log 2>&1
mount -o remount,ro /opt/ >> /tmp/recover.log 2>&1

echo "Sync completed." >> /tmp/recover.log 2>&1
"""


class PPMACLexer(object):
    # Tokens formed from the 'Power PMAC on-line commands' and
    # 'Power PMAC program commands'.
    # As given in the Power PMAC Software reference manual 22nd Mar 2021 p.40-47
    commandTokens = {
        "a",
        "aa",
        "abort",
        "abs",
        "adisable",
        "alias",
        "all",
        "apc",
        "assign",
        "b",
        "bb",
        "begin",
        "bgcplc",
        "break",
        "bstart",
        "bstop",
        "buffers",
        "c",
        "cc",
        "call",
        "callsub",
        "case",
        "ccall",
        "cclr",
        "ccmode0",
        "ccmode1",
        "ccmode2",
        "ccmode3",
        "ccr",
        "cdef",
        "cexec",
        "cipserialnumber",
        "cipvendorcode",
        "circle",
        "clear",
        "close",
        "clrf",
        "cmd",
        "config",
        "continue",
        "cout",
        "cpu",
        "cpx",
        "cset",
        "cskip",
        "cundef",
        "cx",
        "d",
        "dd",
        "date",
        "ddisable",
        "define",
        "delete",
        "disable",
        "dkill",
        "do",
        "dread",
        "dtogread",
        "dwell",
        "ecat",
        "echo",
        "else",
        "enable",
        "f",
        "ff",
        "fload",
        "forward",
        "frax",
        "frax2",
        "fread",
        "free",
        "fsave",
        "g",
        "gg",
        "gather",
        "gosub",
        "goto",
        "h",
        "hh",
        "halt",
        "hm",
        "hmz",
        "hold",
        "home",
        "homez",
        "i",
        "if",
        "inc",
        "inverse",
        "j",
        "jog",
        "jogret",
        "k",
        "kill",
        "l",
        "ll",
        "lh",
        "lhpurge",
        "linear",
        "list",
        "lookahead",
        "lotnum",
        "m",
        "mm",
        "macroauxiliary",
        "macroauxiliaryread",
        "macroauxiliarywrite",
        "macrocontrolledetect",
        "macrocontrollerinit",
        "macromaster",
        "macromasterread",
        "macromasterwrite",
        "macroport",
        "macroportclose",
        "macroportstate",
        "macroring",
        "macroringmasterslave",
        "macroringmasterslaveread",
        "macroringmasterslavewrite",
        "macroringorder",
        "macroringorderbackup",
        "macroringorderclrf",
        "macroringorderdetect",
        "macroringorderinit",
        "macroringorderload",
        "macroringorderrepair",
        "macroringorderrestore",
        "macroringordersave",
        "macroringorderstations",
        "macroringordersync",
        "macroringorderverify",
        "macroringorderverifybackup",
        "macroslave",
        "macroslaveread",
        "macroslavewrite",
        "macrostation",
        "macrostationclearerrors",
        "macrostationclose",
        "macrostationenable",
        "macrostationerrors",
        "macrostationfrequency",
        "macrostationringcheck",
        "macrostationstatus",
        "macrostationtype",
        "n",
        "nn",
        "nofrax",
        "nofrax2",
        "nop",
        "normal",
        "nxyz",
        "oo",
        "open",
        "out",
        "p",
        "pp",
        "pause",
        "pc",
        "pclear",
        "phase",
        "plc",
        "pload",
        "pmatch",
        "pread",
        "productcode",
        "prog",
        "pset",
        "pstore",
        "pvt",
        "q",
        "qq",
        "r",
        "rr",
        "rapid",
        "read",
        "reboot",
        "reset",
        "resetverbose",
        "resume",
        "return",
        "rotary",
        "rotfree",
        "rotfreeall",
        "rtiplc",
        "run",
        "s",
        "ss",
        "save",
        "send",
        "sendall",
        "sendallcmds",
        "sendallsystemcmds",
        "serialnum",
        "setverbose",
        "size",
        "slaves",
        "spline",
        "start",
        "step",
        "step",
        "stop",
        "string",
        "subprog",
        "switch",
        "system",
        "t",
        "tt",
        "ta",
        "td",
        "tm",
        "tread",
        "ts",
        "tsd",
        "tsel",
        "txyz",
        "txyzscale",
        "type",
        "uu",
        "undefine",
        "v",
        "vv",
        "vers",
        "vread",
        "ww",
        "xx",
        "yy",
        "z",
        "#",
        "->",
        "$",
        "$$",
        "$$$",
        "$$$***",
        "%",
        "&",
        "\\",
        "?",
        ":",
    }
    arithmeticOperatorTokens = {"+", "-", "*", "/", "%"}
    bitByBitLogicalOperatorTokens = {"&", "|", "^", "~", "<<", ">>"}
    standardAssignmentOperatorTokens = {
        "=",
        "+=",
        "-=",
        "*=",
        "/=",
        "%=",
        "&=",
        "|=",
        "^=",
        ">>=",
        "<<=",
        "++",
        "--",
    }
    synchronousAssignmentOperatorTokens = {
        "==",
        "+==",
        "-==",
        "*==",
        "/==",
        "&==",
        "|==",
        "^==",
        "++=",
        "--=",
    }
    conditionalComparatorTokens = {
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
        "~",
        "!~",
        "<>",
        "!>",
        "!<",
    }
    conditionalCombinatorialOperatorTokens = {"&&", "||", "!"}
    otherTokens = {"(", ")", "{", "}", "..", ","}
    # Full list of PPMAC tokens
    tokens = (
        commandTokens.union(arithmeticOperatorTokens)
        .union(bitByBitLogicalOperatorTokens)
        .union(standardAssignmentOperatorTokens)
        .union(synchronousAssignmentOperatorTokens)
        .union(conditionalComparatorTokens)
        .union(conditionalCombinatorialOperatorTokens)
        .union(otherTokens)
    )
    spaces = " \n\t\r"
    nonAlphaNumeric = {
        "=",
        "+",
        "-",
        "*",
        "/",
        "%",
        "<",
        ">",
        "&",
        "|",
        "^",
        "!",
        "~",
        "$",
        "#",
        "?",
        ":",
        "\\",
        "(",
        ")",
        "}",
        "{",
        ".",
        ",",
    }

    class Chars(object):
        def __init__(self, chars):
            self.chars = chars
            self._chars = ""

        def isEmpty(self):
            if len(self.chars) == 0:
                return True
            else:
                return False

        def peekNext(self):
            return self.chars[1]

        def peek(self):
            return self.chars[0]

        def moveNext(self):
            c = self.chars[0]
            self._chars += self.chars[0]
            self.chars = self.chars[1:]
            return c

        def rewind(self, pos):
            if pos > 0:
                self.chars = self._chars[-pos:] + self.chars
                self._chars = self._chars[0:-pos]

    def __init__(self, chars, extendedTokens={""}):
        self.extendedTokens = {token.lower() for token in extendedTokens}
        self.tokens = []
        self.chars = self.Chars(chars.lower())
        for token in self.lex(self.chars):
            self.tokens.append(token)

    def pop(self, n=0):
        token = self.tokens[n]
        self.tokens = self.tokens[n + 1 :]
        return token

    def getTokenTypes(self):
        return [token[0] for token in self.tokens]

    def getTokenValues(self):
        return [token[1] for token in self.tokens]

    def getTokensAsString(self):
        return "".join([token[1] for token in self.tokens])

    def lex(self, chars):
        while not chars.isEmpty():
            c = chars.moveNext()
            if c in PPMACLexer.spaces:
                pass
            elif c == "$":
                yield ("hex", self.scanHexadecimal(c, chars))
            elif c in ("'", '"'):
                yield ("string", self.scanString(c, chars))
            elif re.match("[.0-9]", c):
                yield ("number", self.scanNumber(c, chars))
            elif re.match("[a-zA-Z]", c):
                yield ("symbol", self.scanSymbol(c, chars))
            elif c in PPMACLexer.nonAlphaNumeric:
                yield ("", self.scanNonAlphaNumeric(c, chars))
            else:
                raise IOError(f"Unknown token type {c}")

    def scanHexadecimal(self, c, chars):
        ret = c
        if chars.isEmpty():
            return ret
        next = chars.peek()
        allowed = "[a-f0-9]"
        while re.match(allowed, next) is not None:
            ret += chars.moveNext()
            if chars.isEmpty():
                break
            next = chars.peek()
        return ret

    def scanNonAlphaNumeric(self, c, chars):
        ret = c
        if chars.isEmpty():
            return ret
        existingToken = ""
        if ret in PPMACLexer.tokens:
            existingToken = ret
        next = chars.peek()
        allowed = PPMACLexer.nonAlphaNumeric
        while next in allowed:
            ret += chars.moveNext()
            if ret in PPMACLexer.tokens:
                existingToken = ret
            if chars.isEmpty():
                break
        if len(existingToken) > 0:
            chars.rewind(len(ret) - len(existingToken))
            ret = existingToken
        return ret

    def scanSymbol(self, c, chars):
        ret = c
        if chars.isEmpty():
            return ret
        existingToken = ""
        if ret in PPMACLexer.tokens:
            existingToken = ret
        next = chars.peek()
        # if c in "PLQRCMDI" and next.isdigit():
        #    # We have a P/L/Q/M/R/C variable
        #    allowed = "[0-9]"
        #    while re.match(allowed, next) != None:
        #        ret += chars.moveNext()
        #        if chars.isEmpty():
        #            break
        #        next = chars.peek()
        # else:
        if True:
            # Check to see if we can find an existing token in the subsequent
            # characters. If we do, take the longest existing token we find.
            # If we don't, assume the token can take the form of an active element name.
            allowed_ = "[a-zA-Z.\\[]"
            # allowed_ = "[a-zA-Z0-9.\[]"
            allowed = allowed_
            while re.match(allowed, next) is not None:
                if next == "[":
                    allowed = "[0-9\\]]"
                if next == "]":
                    allowed = allowed_
                ret += chars.moveNext()
                if ret in PPMACLexer.tokens:
                    existingToken = ret
                # Use this condition to catch active element names
                if re.sub("\\[([0-9]+)\\]", "[]", ret) in self.extendedTokens:
                    existingToken = ret
                if chars.isEmpty():
                    break
                # Use this condition to catch the few PPMACLexer.tokens that end
                # in a digit, e.g. frax2
                if (
                    re.match("[0-9]", chars.peek())
                    and ret + chars.peek() in PPMACLexer.tokens
                ):
                    existingToken = ret + chars.moveNext()
                    break
                next = chars.peek()
            if len(existingToken) > 0:
                chars.rewind(len(ret) - len(existingToken))
                ret = existingToken
        return ret

    def scanNumber(self, c, chars):
        ret = c
        if chars.isEmpty():
            return ret
        next = chars.peek()
        allowed = "[.0-9]"
        while re.match(allowed, next) is not None:
            # to catch '..' used to indicate ranges
            if next == ".":
                if chars.peekNext() == ".":
                    break
            ret += chars.moveNext()
            if chars.isEmpty():
                break
            next = chars.peek()
        return ret

    def scanMathsChars(self, c, chars):
        ret = c
        if chars.isEmpty():
            return ret
        while ret + chars.peek() in PPMACLexer.maths:
            c = chars.moveNext()
            ret += c
            if chars.isEmpty():
                break
        return (self.mathsDict[ret], ret)

    def scanString(self, delim, chars):
        ret = ""
        next = chars.peek()
        while next != delim:
            ret += chars.moveNext()
            if chars.isEmpty():
                break
            next = chars.peek()
        chars.moveNext()
        return ret


class PPMACProject(object):
    """
    Class containing files and directories included in a project
    """

    class Directory(object):
        def __init__(self, path, files):
            self.path = path
            # self.subdirs = {}  # dict of directory objects
            self.files = files  # dict of files

    class File(object):
        def __init__(self, name, dir, proj):
            self.name = name
            self.dir = dir  # directory object
            filePath = f"{dir}/{name}"
            self.extension = os.path.splitext(filePath)[1]
            self.contents = proj.getFileContents(filePath)

    def __init__(self, source, root, tempDir=None):
        # absolute path the project directory
        self.root = root
        # Source of project (hardware or repo)
        self.source = source
        # Dictionary of files contained in the project
        self.files = {}
        # Dictionary of directories contained in the project
        self.dirs = {}
        if self.source == "hardware":
            if root.find("usrflash") == -1:
                raise RuntimeError(
                    f'Root directory "{root}" invalid: not a project directory.'
                )
            if tempDir is None:
                raise RuntimeError(
                    "Please define a temporary directory into which the project from "
                    "the ppmac will be copied."
                )
            self.root = tempDir
            os.makedirs(tempDir, exist_ok=True)
            scpFromPowerPMACtoLocal(source=root, destination=tempDir, recursive=True)
        elif self.source != "repository":
            raise RuntimeError(
                'Invalid project source: should be "hardware" or "repository".'
            )
        self.buildProjectTree(self.root)

    def buildProjectTree(self, start):
        for root, dirs, files in os.walk(start):
            root_ = root.replace(start, "", 1)
            for name in dirs:
                dirName = os.path.join(root_, name)
                self.dirs[dirName] = self.Directory(dirName, files)
            for name in files:
                fileName = os.path.join(root_, name)
                self.files[fileName] = self.File(name, root_, self)

    def getFileContents(self, file):
        contents = []
        file = f"{self.root}/{file}"
        with open(file, "r", encoding="ISO-8859-1") as readFile:
            for line in readFile:
                contents.append(line)
        return contents


class ProjectCompare(object):
    """
    Compare two project filesystems
    """

    class FileDiffs(object):
        """
        Object holding the differences between two project files
        """

        def __init__(self, fileA, fileB):
            self.fileA = fileA
            self.fileB = fileB
            self.same = fileA.sha256 == fileB.sha256
            # plus some object to hold the line-by-line differences

    def __init__(self, projectA, projectB, ignore=None):
        self.projectA = projectA
        self.projectB = projectB
        self.filesOnlyInA = {}
        self.filesOnlyInB = {}
        self.filesInAandB = {}

    def setProjectA(self, project):
        self.projectA = project

    def setprojectB(self, project):
        self.projectB = project

    def compareProjectFiles(self, diffDirPath):
        fileNamesA = set(self.projectA.files.keys())
        fileNamesB = set(self.projectB.files.keys())
        fileNamesOnlyInA = fileNamesA - fileNamesB
        fileNamesOnlyInB = fileNamesB - fileNamesA
        fileNamesInAandB = fileNamesA & fileNamesB
        self.filesOnlyInA = self.filesOnlyInB = {}
        self.filesOnlyInA = {
            fileName: self.projectA.files[fileName] for fileName in fileNamesOnlyInA
        }
        self.filesOnlyInB = {
            fileName: self.projectB.files[fileName] for fileName in fileNamesOnlyInB
        }
        for fileName in fileNamesInAandB:
            self.filesInAandB[fileName] = {
                "A": self.projectA.files[fileName],
                "B": self.projectB.files[fileName],
            }
        missingFile = f"{diffDirPath}/missingFiles.txt"
        with open(missingFile, "w+") as writeFile:
            writeFile.write(
                f"@@ Project files in source '{self.projectA.source}' but not source "
                f"'{self.projectB.source}' @@\n"
            )
            for projFileName in fileNamesOnlyInA:
                writeFile.write(f">>>> {projFileName}\n")
            writeFile.write(
                f"@@ Project files in source '{self.projectB.source}' but not source "
                f"'{self.projectA.source}' @@\n"
            )
            for projFileName in fileNamesOnlyInB:
                writeFile.write(f">>>> {projFileName}\n")
        for projFileName in fileNamesInAandB:
            projFileName_ = projFileName.split("/")[-1]
            diffFilePath = f"{diffDirPath}/{projFileName_}.diff"
            with open(diffFilePath, "w+") as diffFile:
                diffFile.writelines(
                    difflib.unified_diff(
                        self.projectA.files[projFileName].contents,
                        self.projectB.files[projFileName].contents,
                        fromfile=f"{self.projectA.source}: {projFileName}",
                        tofile=f"{self.projectB.source}: {projFileName}",
                        lineterm="\n",
                    )
                )


class PPMACCompare(object):
    """
    Compare two PowerPMAC objects
    """

    def __init__(self, ppmacA, ppmacB, compareDir):
        self.ppmacInstanceA = ppmacA
        self.ppmacInstanceB = ppmacB
        self.compareDir = compareDir
        # Set of element names only in A
        self.elemNamesOnlyInA = {}
        # Set of element names only in B
        self.elemNamesOnlyInB = {}
        # Set of element names in both A and B
        self.elemNamesInAandB = {}
        # Dictionary of active elements only in A. Keys refer to the active
        # elem names, the values are PowerPMAC.activeElement objects.
        self.activeElemsOnlyInA = {}
        # Dictionary of active elements only in B. Keys refer to the active
        # elem names, the values are PowerPMAC.activeElement objects.
        self.activeElemsOnlyInB = {}
        # A nested dictionary. The outer keys refer to the active elem names,
        # the inner keys refer to ppmac instance (A or B), the values
        # are PowerPMAC.activeElement objects.
        self.activeElemsInAandB = {}
        self.progNamesOnlyInA = {}
        self.progNamesOnlyInB = {}
        self.progNamesInAandB = {}

    def setPPMACInstanceA(self, ppmacA):
        self.ppmacInstanceA = ppmacA

    def setPPMACInstanceB(self, ppmacB):
        self.ppmacInstanceB = ppmacB

    def compareActiveElements(self):
        elementNamesA = set(self.ppmacInstanceA.activeElements.keys())
        elementNamesB = set(self.ppmacInstanceB.activeElements.keys())
        self.elemNamesOnlyInA = elementNamesA - elementNamesB
        self.elemNamesOnlyInB = elementNamesB - elementNamesA
        self.elemNamesInAandB = elementNamesA & elementNamesB
        self.activeElemsOnlyInA = {
            elemName: self.ppmacInstanceA.activeElements[elemName]
            for elemName in self.elemNamesOnlyInA
        }
        self.activeElemsOnlyInB = {
            elemName: self.ppmacInstanceB.activeElements[elemName]
            for elemName in self.elemNamesOnlyInB
        }
        for elemName in self.elemNamesInAandB:
            self.activeElemsInAandB[elemName] = {
                "A": self.ppmacInstanceA.activeElements[elemName],
                "B": self.ppmacInstanceB.activeElements[elemName],
            }
        self.writeActiveElemDifferencesToFile()

    def comparePrograms(self):
        outputDir = f"{self.compareDir}/active/programs"
        os.makedirs(outputDir, exist_ok=True)
        programsA = mergeDicts(
            self.ppmacInstanceA.motionPrograms,
            self.ppmacInstanceA.subPrograms,
            self.ppmacInstanceA.plcPrograms,
            self.ppmacInstanceA.forwardPrograms,
            self.ppmacInstanceA.inversePrograms,
        )
        programsB = mergeDicts(
            self.ppmacInstanceB.motionPrograms,
            self.ppmacInstanceB.subPrograms,
            self.ppmacInstanceB.plcPrograms,
            self.ppmacInstanceB.forwardPrograms,
            self.ppmacInstanceB.inversePrograms,
        )
        progNamesA = set(programsA.keys())
        progNamesB = set(programsB.keys())
        self.progNamesOnlyInA = progNamesA - progNamesB
        self.progNamesOnlyInB = progNamesB - progNamesA
        self.progNamesInAandB = progNamesA & progNamesB
        with open(f"{outputDir}/missingPrograms.txt", "w+") as writeFile:
            writeFile.write(
                f"@@ Programs in source '{self.ppmacInstanceA.source}' but not source "
                f"'{self.ppmacInstanceB.source}'\n"
            )
            for progName in self.progNamesOnlyInA:
                writeFile.write(f">>>> {progName}\n")
                writeFile.write(f"{programsA[progName].printInfo()}\n")
            writeFile.write(
                f"@@ Programs in source '{self.ppmacInstanceB.source}' but not source "
                f"'{self.ppmacInstanceA.source}'\n"
            )
            for progName in self.progNamesOnlyInB:
                writeFile.write(f">>>> {progName}\n")
                writeFile.write(f"{programsB[progName].printInfo()}\n")
        for progName in self.progNamesInAandB:
            filePath = f"{outputDir}/{progName}.diff"
            with open(filePath, "w+") as writeFile:
                writeFile.writelines(
                    difflib.unified_diff(
                        programsA[progName].listing,
                        programsB[progName].listing,
                        fromfile=f"{self.ppmacInstanceA.source}: {progName}",
                        tofile=f"{self.ppmacInstanceB.source}: {progName}",
                        lineterm="\n",
                    )
                )

    def compareCoordSystemAxesDefinitions(self):
        outputDir = f"{self.compareDir}/active/axes"
        os.makedirs(outputDir, exist_ok=True)
        coordSysDefsA = self.ppmacInstanceA.coordSystemDefs
        coordSysDefsB = self.ppmacInstanceB.coordSystemDefs
        coordSysNumbersA = set(coordSysDefsA.keys())
        coordSysNumbersB = set(coordSysDefsB.keys())
        self.coordSystemsOnlyInA = coordSysNumbersA - coordSysNumbersB
        self.coordSystemsOnlyInB = coordSysNumbersB - coordSysNumbersA
        self.coordSystemsInAandB = coordSysNumbersA & coordSysNumbersB
        with open(f"{outputDir}/missingCoordSystems.txt", "w+") as writeFile:
            writeFile.write(
                "@@ Coordinate Systems defined in source"
                f" '{self.ppmacInstanceA.source}' but not source"
                f" '{self.ppmacInstanceB.source}'\n"
            )
            for coordSysNumber in self.coordSystemsOnlyInA:
                writeFile.write(f">>>> &{coordSysNumber}\n")
                writeFile.write(
                    self.ppmacInstanceA.coordSystemDefs[coordSysNumber].printInfo()
                )
            writeFile.write(
                "@@ Coordinate Systems defined in source"
                f" '{self.ppmacInstanceB.source}' but not source"
                f" '{self.ppmacInstanceA.source}'\n"
            )
            for coordSysNumber in self.coordSystemsOnlyInB:
                writeFile.write(f">>>> &{coordSysNumber}\n")
                writeFile.write(
                    self.ppmacInstanceB.coordSystemDefs[coordSysNumber].printInfo()
                )
        for coordSysNumber in self.coordSystemsInAandB:
            filePath = f"{outputDir}/cs{coordSysNumber}Axes.diff"
            with open(filePath, "w+") as writeFile:
                added, removed, modified, same = comparedicts(
                    coordSysDefsA[coordSysNumber].motor,
                    coordSysDefsB[coordSysNumber].motor,
                )
                for motorNumber in modified:
                    writeFile.write(
                        "@@ Motor"
                        f" {motorNumber} @@\n{self.ppmacInstanceA.source} definition = "
                        f"&{coordSysNumber}#{motorNumber}->{modified[motorNumber][0]}\n"
                        f"{self.ppmacInstanceB.source} definition = "
                        f"&{coordSysNumber}#{motorNumber}->{modified[motorNumber][1]}\n"
                    )

    def writeActiveElemDifferencesToFile(self):
        outputDir = f"{self.compareDir}/active"
        os.makedirs(outputDir, exist_ok=True)
        dataStructCategoriesInA = set(
            [
                elem.category
                for elem in list(self.ppmacInstanceA.activeElements.values())
            ]
        )
        dataStructCategoriesInB = set(
            [
                elem.category
                for elem in list(self.ppmacInstanceB.activeElements.values())
            ]
        )
        filePrefixes = dataStructCategoriesInA.union(dataStructCategoriesInB)
        filePaths = [f"{outputDir}/{prefix}.diff" for prefix in filePrefixes]
        diffFiles = {}
        try:
            sourceA = self.ppmacInstanceA.source
            sourceB = self.ppmacInstanceB.source
            for file in filePaths:
                diffFiles[file] = open(file, "w+")
            # write first set of headers
            for file in diffFiles:
                diffFiles[file].write(
                    f"@@ Active elements in source '{sourceA}' but not source"
                    f" '{sourceB}' @@\n"
                )
            # write to file elements that are in ppmacA but not ppmacB
            for elemName in self.elemNamesOnlyInA:
                file = (
                    f"{self.compareDir}/active/"
                    f"{self.activeElemsOnlyInA[elemName].category}.diff"
                )
                diffFiles[file].write(
                    ">>>> "
                    + self.activeElemsOnlyInA[elemName].name
                    + " = "
                    + self.activeElemsOnlyInA[elemName].value
                    + "\n"
                )
            # write second set of headers
            for file in diffFiles:
                diffFiles[file].write(
                    f"@@ Active elements in source '{sourceB}' but not source"
                    f" '{sourceA}' @@\n"
                )
            # write to file elements that are in ppmacB but not ppmacA
            for elemName in self.elemNamesOnlyInB:
                file = (
                    f"{self.compareDir}/active/"
                    f"{self.activeElemsOnlyInB[elemName].category}.diff"
                )
                diffFiles[file].write(
                    ">>>> "
                    + self.activeElemsOnlyInB[elemName].name
                    + " = "
                    + self.activeElemsOnlyInB[elemName].value
                    + "\n"
                )
            # write to file elements that in ppmacB but not ppmacA but whose
            # values differ
            for file in diffFiles:
                diffFiles[file].write(
                    f"@@ Active elements in source '{sourceA}' and source '{sourceB}'"
                    " with different values @@\n"
                )
            for elemName in self.elemNamesInAandB:
                valA = self.activeElemsInAandB[elemName]["A"].value
                valB = self.activeElemsInAandB[elemName]["B"].value
                if valA != valB:
                    file = (
                        f"{self.compareDir}/active/"
                        f"{self.ppmacInstanceA.activeElements[elemName].category}.diff"
                    )
                    diffFiles[file].write(
                        f">>>> {elemName} @@\n{self.ppmacInstanceA.source} value ="
                        f" {valA}\n{self.ppmacInstanceB.source} value = {valB}\n"
                    )
        finally:
            for file in diffFiles:
                diffFiles[file].close()


class PPMACRepositoryWriteRead(object):
    def __init__(self, ppmac, repositoryPath):
        self.ppmacInstance = ppmac
        # source - will be set somewhere else
        if self.ppmacInstance.source == "unknown":
            self.ppmacInstance.source = "repository"
        self.repositoryPath = repositoryPath

    def setPPMACInstance(self, ppmac):
        self.ppmacInstance = ppmac
        if self.ppmacInstance.source == "unknown":
            self.ppmacInstance.source = "repository"

    def setRepositoryPath(self, path):
        self.repositoryPath = path

    def writeActiveState(self):
        os.makedirs(self.repositoryPath + "/active", exist_ok=True)
        self.writeDataStructures()
        self.writeActiveElements()
        self.writeAllPrograms()
        self.writeCSAxesDefinitions()

    def writeDataStructures(self):
        file = self.repositoryPath + "/active/dataStructures.txt"
        with open(file, "w+") as writeFile:
            for dataStructure in self.ppmacInstance.dataStructures:
                writeFile.write(
                    self.ppmacInstance.dataStructures[dataStructure].printInfo() + "\n"
                )

    def writeActiveElements(self):
        file = self.repositoryPath + "/active/activeElements.txt"
        with open(file, "w+") as writeFile:
            for elem in self.ppmacInstance.activeElements:
                writeFile.write(
                    self.ppmacInstance.activeElements[elem].printInfo() + "\n"
                )

    def writePrograms(self, ppmacProgs, progsDir):
        """
        Write contents of dictionary of PPMAC programs to files. Each dict key
        corresponds to separate file written.
        :param ppmacProgs: dictionary of programs.
        :return:
        """
        progNames = ppmacProgs.keys()
        for progName in progNames:
            fileName = progsDir + "/" + progName.replace("&", "CS")
            with open(fileName, "w+") as writeFile:
                writeFile.write(ppmacProgs[progName].printInfo())
                for line in ppmacProgs[progName].listing:
                    writeFile.write(line)

    def writeAllPrograms(self):
        progsDir = self.repositoryPath + "/active/programs"
        os.makedirs(progsDir, exist_ok=True)
        self.writePrograms(self.ppmacInstance.motionPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.subPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.plcPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.forwardPrograms, progsDir)
        self.writePrograms(self.ppmacInstance.inversePrograms, progsDir)

    def writeCSAxesDefinitions(self):
        csAxesDefsPath = self.repositoryPath + "/active/axes"
        os.makedirs(csAxesDefsPath, exist_ok=True)
        for coordSystem in self.ppmacInstance.coordSystemDefs:
            fileName = f"{csAxesDefsPath}/cs{coordSystem}Axes"
            with open(fileName, "w+") as writeFile:
                writeFile.write(
                    self.ppmacInstance.coordSystemDefs[coordSystem].printInfo()
                )

    def readAndStoreActiveElements(self):
        fileName = self.repositoryPath + "/active/activeElements.txt"
        with open(fileName, "r") as readFile:
            for line in readFile:
                line = line.split()
                line = [item.strip() for item in line]
                if line == "":
                    continue
                key = line[0]
                value = line[
                    0:
                ]  # need to deal with the list of indices which is tha last column(s)
                self.ppmacInstance.activeElements[
                    key
                ] = self.ppmacInstance.ActiveElement(*value[0:5])

    def readAndStoreCSAxesDefinitions(self):
        csAxesDefsPath = self.repositoryPath + "/active/axes"
        csAxesFileNames = [
            file
            for file in os.listdir(csAxesDefsPath)
            if os.path.isfile(f"{csAxesDefsPath}/{file}")
        ]
        for fileName in csAxesFileNames:
            file = f"{csAxesDefsPath}/{fileName}"
            csNumber = str(re.search(r"\d+", fileName).group())
            self.ppmacInstance.coordSystemDefs[csNumber] = [csNumber, []]
            with open(file, "r") as readFile:
                motorDefs = []
                for line in readFile:
                    line = line.strip()
                    if line == "":
                        continue
                    csNumber_ = PPMACLexer(line).pop(1)[1]
                    if csNumber is not csNumber_:
                        raise IOError(
                            f"Inconsistent coordinate system numbers in file: {file}"
                        )
                    motorDefinition = line.rstrip("\n")
                    motorDefs.append(motorDefinition)
            self.ppmacInstance.coordSystemDefs[
                csNumber
            ] = self.ppmacInstance.CoordSystemDefinition(csNumber, motorDefs)

    def readAndStoreBufferedPrograms(self):
        progsPath = self.repositoryPath + "/active/programs"
        progFileNames = [
            file
            for file in os.listdir(progsPath)
            if os.path.isfile(f"{progsPath}/{file}")
        ]
        for fileName in progFileNames:
            fileName = f"{progsPath}/{fileName}"
            with open(fileName, "r") as readFile:
                header = readFile.readline().split()
                header = [item.strip(",") for item in header]
                progType, progName, progSize, progOffset = (
                    header[i] for i in [0, 1, 3, 5]
                )
                progListing = []
                for line in readFile:
                    if line.strip() == "":
                        continue
                    progListing.append(line)
            if progType == "Motion":
                self.ppmacInstance.motionPrograms[
                    progName
                ] = self.ppmacInstance.Program(
                    progName, progOffset, progSize, progType, progListing
                )
            elif progType == "SubProg":
                self.ppmacInstance.subPrograms[progName] = self.ppmacInstance.Program(
                    progName, progOffset, progSize, progType, progListing
                )
            elif progType == "Plc":
                self.ppmacInstance.plcPrograms[progName] = self.ppmacInstance.Program(
                    progName, progOffset, progSize, progType, progListing
                )
            elif progType == "Forward":
                progCoordSystem = header[7]
                self.ppmacInstance.forwardPrograms[
                    progName
                ] = self.ppmacInstance.KinematicTransform(
                    progName,
                    progSize,
                    progOffset,
                    progType,
                    progCoordSystem,
                    progListing,
                )
            elif progType == "Inverse":
                progCoordSystem = header[7]
                self.ppmacInstance.inversePrograms[
                    progName
                ] = self.ppmacInstance.KinematicTransform(
                    progName,
                    progSize,
                    progOffset,
                    progType,
                    progCoordSystem,
                    progListing,
                )


class PPMACHardwareWriteRead(object):
    def __init__(self, ppmac=None, tempDir=None):
        self.ppmacInstance = ppmac
        # Set PPMAC source to hardware
        if self.ppmacInstance.source == "unknown":
            self.ppmacInstance.source = "hardware"
        # Path to directory containing symbols tables files on local
        if tempDir is not None:
            self.local_db_path = tempDir
        # File containing list of all base Data Structures
        self.pp_swtbl0_txtfile = "pp_swtbl0.txt"
        # Standard Data Structure symbols tables
        self.pp_swtlbs_symfiles = ["pp_swtbl1.sym", "pp_swtbl2.sym", "pp_swtbl3.sym"]
        # Read maximum values for the various configuration parameters
        # self.readSysMaxes()

    def setPPMACInstance(self, ppmac):
        self.ppmacInstance = ppmac
        if self.ppmacInstance.source == "unknown":
            self.ppmacInstance.source = "hardware"

    def getCommandReturnInt(self, cmd):
        (cmdReturn, status) = sshClient.sendCommand(cmd)
        if status:
            cmdReturnInt = int(cmdReturn[0:])
        else:
            raise IOError(
                "Cannot retrieve variable value: error communicating with PMAC"
            )
        return cmdReturnInt

    def readSysMaxes(self):
        if self.ppmacInstance is None:
            raise RuntimeError("No Power PMAC object has been specified")
        # number of active motors
        self.ppmacInstance.numberOfMotors = self.getCommandReturnInt("Sys.MaxMotors")
        # number of active coordinate systems
        self.ppmacInstance.numberOfCoordSystems = self.getCommandReturnInt(
            "Sys.MaxCoords"
        )
        # number of active compensation tables.
        self.ppmacInstance.numberOfCompTables = self.getCommandReturnInt(
            "Sys.CompEnable"
        )
        # number of active cam tables
        self.ppmacInstance.numberOfCamTables = self.getCommandReturnInt("Sys.CamEnable")
        # number EtherCAT networks that can be enabled
        self.ppmacInstance.numberOfECATs = self.getCommandReturnInt("Sys.MaxEcats")
        # Number of available encoder tables
        self.ppmacInstance.numberOfEncTables = self.getCommandReturnInt(
            "Sys.MaxEncoders"
        )

    def sendCommand(self, cmd):
        (data, status) = sshClient.sendCommand(cmd)
        if not status:
            raise IOError(
                "Cannot retrieve data structure: error communicating with PMAC"
            )
        else:
            data = data.split("\r")[:-1]
        return data

    def swtblFileToList(self, pp_swtbl_file):
        """
        Generate a list of symbols from a symbols table file.
        :param pp_swtbl_file: full path to symbols table file.
        :return: swtbl_DSs: list of symbols, where each 'symbol' is represented by
        the contents of one row of the symbols table file.
        """
        symbols = []
        try:
            file = open(file=pp_swtbl_file, mode="r", encoding="ISO-8859-1")
            multi_line = ""
            for line in file:
                multi_line_ = multi_line
                if line[-2:] == "\\\n":
                    multi_line += line
                else:
                    line = multi_line_ + line
                    symbol = line.split("\x01")
                    symbol = [col.strip() for col in symbol]
                    multi_line = ""
                    symbols.append(symbol)
            file.close()
        except IOError as e:
            print(e)
        return symbols

    def getDataStructureCategory(self, dataStructure):
        if dataStructure.find(".") == -1:
            dataStructureCategory = dataStructure
        else:
            dataStructureCategory = dataStructure[0 : dataStructure.find(".")]
        return dataStructureCategory.replace("[]", "")

    def ignoreDataStructure(self, substructure, elementsToIgnore):
        """
        Determine whether a data structure or substructure should be ignored by
        checking if it or any of its parent, grandparent, great-grandparent etc.
        structures are included in the ignore list.
        :param substructure: name of data structure or substructure to check
        :return: True if data structure or substructure should be ignored, False
        otherwise
        """
        n = substructure.count(".")
        for _ in range(n + 1):
            if substructure in elementsToIgnore:
                return True
            substructure = substructure[0 : substructure.rfind(".")]
        return False

    def fillDataStructureIndices_i(
        self, dataStructure, activeElements, elementsToIgnore, timeout=None
    ):
        """
        Incrementally increase the index of a singly-indexed data structure and send
        the resulting command to the ppmac until the maximum accepted index is reached.
        Add the command string and return value of all commands accepted by
        the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active elements,
        where the key is the element name, and the value is a tuple containing
        the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to
        activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        cmd_accepted = True
        while cmd_accepted:
            i_idex_string = f"[{i}]"
            dataStructure_i = dataStructure.replace("[]", i_idex_string)
            if self.ignoreDataStructure(
                dataStructure_i.replace(i_idex_string, f"[{i}:]"), elementsToIgnore
            ):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                i += 1
                continue
            # print(dataStructure_i)
            cmd_return = self.sendCommand(dataStructure_i)
            # print(cmd_return)
            if "ILLEGAL" in cmd_return[0]:
                cmd_accepted = False
            else:
                activeElements[dataStructure_i] = (
                    dataStructure_i,
                    cmd_return[0],
                    dataStructureCategory,
                    dataStructure,
                    [i],
                )
            if applyTimeout and time.time() - startTime > timeout:
                logging.info(
                    f"Timed-out generating active elements for {dataStructure}. "
                    f"Last i = {i}."
                )
                return
            i += 1

    def fillDataStructureIndices_ij(
        self, dataStructure, activeElements, elementsToIgnore, timeout=None
    ):
        """
        Incrementally increase the indices of a doubly-indexed data structure and send
        the resulting command to the ppmac until the maximum accepted indices are
        reached. Add the command string and return value of all commands accepted by
        the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active
        elements, where the key is the element name, and the value is a tuple
        containing the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to
        activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        while cmd_accepted:
            j = 0
            i_idex_string = f"[{i}]"
            dataStructure_i = nthRepl(dataStructure, "[]", i_idex_string, 1)
            if self.ignoreDataStructure(
                dataStructure_i.replace(i_idex_string, f"[{i}:]"), elementsToIgnore
            ):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                last_i_accepted = i
                i += 1
                continue
            while cmd_accepted:
                j_idex_string = f"[{j}]"
                dataStructure_ij = nthRepl(dataStructure_i, "[]", j_idex_string, 1)
                if self.ignoreDataStructure(
                    dataStructure_ij.replace(f"[{i}]", "[]", 1).replace(
                        j_idex_string, f"[{j}:]", 1
                    ),
                    elementsToIgnore,
                ):
                    break
                if self.ignoreDataStructure(
                    dataStructure_ij.replace(f"[{i}]", "[]", 1), elementsToIgnore
                ):
                    j += 1
                    continue
                # print(dataStructure_ij)
                cmd_return = self.sendCommand(dataStructure_ij)
                # print(cmd_return)
                if "ILLEGAL" in cmd_return[0]:
                    cmd_accepted = False
                else:
                    last_i_accepted = i
                    activeElements[dataStructure_ij] = (
                        dataStructure_ij,
                        cmd_return[0],
                        dataStructureCategory,
                        dataStructure,
                        [i, j],
                    )
                if applyTimeout and time.time() - startTime > timeout:
                    logging.info(
                        f"Timed-out generating active elements for {dataStructure}. "
                        f"Last i,j = {i},{j}."
                    )
                    return
                j += 1
            cmd_accepted = True
            # print(last_i_accepted, i)
            if i - last_i_accepted > 1:
                cmd_accepted = False
            # print(cmd_accepted)
            i += 1
        # print(activeElements)

    def fillDataStructureIndices_ijk(
        self, dataStructure, activeElements, elementsToIgnore, timeout=None
    ):
        """
        Incrementally increase the indices of a triply-indexed data structure and send
        the resulting command to the ppmac until the maximum accepted indices are
        reached. Add the command string and return value of all commands accepted by
        the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active
        elements, where the key is the element name, and the value is a
        tuple containing the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to
        activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        # print(dataStructure)
        while cmd_accepted:
            j = 0
            last_j_accepted = j
            i_idex_string = f"[{i}]"
            dataStructure_i = nthRepl(dataStructure, "[]", i_idex_string, 1)
            if self.ignoreDataStructure(
                dataStructure_i.replace(i_idex_string, f"[{i}:]"), elementsToIgnore
            ):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                last_i_accepted = i
                i += 1
                continue
            #    break
            while cmd_accepted:
                k = 0
                j_idex_string = f"[{j}]"
                dataStructure_ij = nthRepl(dataStructure_i, "[]", j_idex_string, 1)
                if self.ignoreDataStructure(
                    dataStructure_ij.replace(f"[{i}]", "[]", 1).replace(
                        j_idex_string, f"[{j}:]", 1
                    ),
                    elementsToIgnore,
                ):
                    break
                if self.ignoreDataStructure(
                    dataStructure_ij.replace(f"[{i}]", "[]", 1), elementsToIgnore
                ):
                    last_j_accepted = j
                    j += 1
                    continue
                #    break
                while cmd_accepted:
                    k_idex_string = f"[{k}]"
                    dataStructure_ijk = nthRepl(
                        dataStructure_ij, "[]", k_idex_string, 1
                    )
                    if self.ignoreDataStructure(
                        dataStructure_ijk.replace(f"[{i}]", "[]", 1)
                        .replace(f"[{j}]", "[]", 1)
                        .replace(k_idex_string, f"[{k}:]", 1),
                        elementsToIgnore,
                    ):
                        break
                    if self.ignoreDataStructure(
                        dataStructure_ijk.replace(f"[{i}]", "[]", 1).replace(
                            f"[{j}]", "[]", 1
                        ),
                        elementsToIgnore,
                    ):
                        #    break
                        k += 1
                        continue
                    # print(dataStructure_ijk)
                    cmd_return = self.sendCommand(dataStructure_ijk)
                    # print(cmd_return)
                    if "ILLEGAL" in cmd_return[0]:
                        cmd_accepted = False
                    else:
                        last_j_accepted = j
                        last_i_accepted = i
                        activeElements[dataStructure_ijk] = (
                            dataStructure_ijk,
                            cmd_return[0],
                            dataStructureCategory,
                            dataStructure,
                            [i, j, k],
                        )
                    if applyTimeout and time.time() - startTime > timeout:
                        logging.info(
                            f"Timed-out generating active elements for {dataStructure}."
                            f" Last i,j,k = {i},{j},{k}."
                        )
                        return
                    k += 1
                cmd_accepted = True
                if j - last_j_accepted > 1:
                    cmd_accepted = False
                j += 1
            cmd_accepted = True
            if i - last_i_accepted > 1:
                cmd_accepted = False
            i += 1
        # print(activeElements)

    def fillDataStructureIndices_ijkl(
        self, dataStructure, activeElements, elementsToIgnore, timeout=None
    ):
        """
        Incrementally increase the indices of a quadruply-indexed data structure and
        send the resulting command to the ppmac until the maximum accepted
        indices are reached. Add the command string and return value of all commands
        accepted by the ppmac to the dictionary of active elements.
        :param dataStructure: String containing the data structure name.
        :param activeElements: Dictionary containing the current set of active
        elements, where the key is the element name, and the value is a tuple
        containing the return value from the ppmac and the active element name.
        :param elementsToIgnore: Set of data structures not to be added to
        activeElements.
        :return:
        """
        applyTimeout = False
        if isinstance(timeout, int) or isinstance(timeout, float):
            applyTimeout = True
            startTime = time.time()
        dataStructureCategory = self.getDataStructureCategory(dataStructure)
        i = 0
        last_i_accepted = i
        cmd_accepted = True
        while cmd_accepted:
            j = 0
            last_j_accepted = j
            i_idex_string = f"[{i}]"
            dataStructure_i = nthRepl(dataStructure, "[]", i_idex_string, 1)
            # if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
            #    break
            if self.ignoreDataStructure(
                dataStructure_i.replace(i_idex_string, f"[{i}:]"), elementsToIgnore
            ):
                break
            if self.ignoreDataStructure(dataStructure_i, elementsToIgnore):
                last_i_accepted = i
                i += 1
                continue
            while cmd_accepted:
                k = 0
                last_k_accepted = k
                j_idex_string = f"[{j}]"
                dataStructure_ij = nthRepl(dataStructure_i, "[]", j_idex_string, 1)
                if self.ignoreDataStructure(
                    dataStructure_ij.replace(f"[{i}]", "[]", 1).replace(
                        j_idex_string, f"[{j}:]", 1
                    ),
                    elementsToIgnore,
                ):
                    break
                if self.ignoreDataStructure(
                    dataStructure_ij.replace(f"[{i}]", "[]", 1), elementsToIgnore
                ):
                    last_j_accepted = j
                    j += 1
                    continue
                while cmd_accepted:
                    m = 0
                    k_idex_string = f"[{k}]"
                    dataStructure_ijk = nthRepl(
                        dataStructure_ij, "[]", k_idex_string, 1
                    )
                    if self.ignoreDataStructure(
                        dataStructure_ijk.replace(f"[{i}]", "[]", 1)
                        .replace(f"[{j}]", "[]", 1)
                        .replace(k_idex_string, f"[{k}:]", 1),
                        elementsToIgnore,
                    ):
                        break
                    if self.ignoreDataStructure(
                        dataStructure_ijk.replace(f"[{i}]", "[]", 1).replace(
                            f"[{j}]", "[]", 1
                        ),
                        elementsToIgnore,
                    ):
                        #    break
                        last_k_accepted = k
                        k += 1
                        continue
                    while cmd_accepted:
                        m_idex_string = f"[{m}]"
                        dataStructure_ijkm = nthRepl(
                            dataStructure_ijk, "[]", m_idex_string, 1
                        )
                        if self.ignoreDataStructure(
                            dataStructure_ijkm.replace(f"[{i}]", "[]", 1)
                            .replace(f"[{j}]", "[]", 1)
                            .replace(f"[{k}]", "[]", 1)
                            .replace(m_idex_string, f"[{m}:]", 1),
                            elementsToIgnore,
                        ):
                            break
                        if self.ignoreDataStructure(
                            dataStructure_ijkm.replace(f"[{i}]", "[]", 1)
                            .replace(f"[{j}]", "[]", 1)
                            .replace(f"[{k}]", "[]", 1),
                            elementsToIgnore,
                        ):
                            m += 1
                            continue
                        # print(dataStructure_ijkm)
                        cmd_return = self.sendCommand(dataStructure_ijkm)
                        # print(cmd_return)
                        if "ILLEGAL" in cmd_return[0]:
                            cmd_accepted = False
                        else:
                            last_k_accepted = k
                            last_j_accepted = j
                            last_i_accepted = i
                            activeElements[dataStructure_ijkm] = (
                                dataStructure_ijkm,
                                cmd_return[0],
                                dataStructureCategory,
                                dataStructure,
                                [i, j, k, m],
                            )
                        if applyTimeout and time.time() - startTime > timeout:
                            logging.info(
                                "Timed-out generating active elements for"
                                f" {dataStructure}. Last i,j,k,m = {i},{j},{k},{m}."
                            )
                            return
                        m += 1
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
        # print(activeElements)

    def scpPPMACDatabaseToLocal(self, remote_db_path, local_db_path):
        if not os.path.isdir(local_db_path):
            os.system("mkdir " + local_db_path)
        scpFromPowerPMACtoLocal(
            source=remote_db_path, destination=local_db_path, recursive=True
        )

    def createDataStructuresFromSymbolsTables(self, pp_swtlbs_symfiles, local_db_path):
        """
        Read the symbols tables and create a list of data structure names contained
        within them.
        :return: dataStructures: list of data structure names
        """
        # Clear current data structure dictionary
        dataStructures = {}
        # swtbl0 = []
        # with open(self.local_db_path + '/' + self.pp_swtbl0_txtfile, 'r') as readFile:
        #    for line in readFile:
        #        swtbl0.append(line.replace('\n',''))
        pp_swtbls = []
        for pp_swtbl_file in pp_swtlbs_symfiles:
            pp_swtbls.append(self.swtblFileToList(local_db_path + "/" + pp_swtbl_file))
        swtbl1_nparray = np.asarray(pp_swtbls[0])
        swtbl2_nparray = np.asarray(pp_swtbls[1])
        swtbl3_nparray = np.asarray(pp_swtbls[2])
        # for baseDS in swtbl0:
        #    print(baseDS)
        #    substruct_01 = False
        for i in range(swtbl1_nparray.shape[0]):
            #    if baseDS == swtbl1_nparray[i, 1]:
            #        substruct_01 = True
            substruct_12 = False
            for j in range(swtbl2_nparray.shape[0]):
                if swtbl1_nparray[i, 2] == swtbl2_nparray[j, 1]:
                    if (
                        swtbl1_nparray[i, 1].replace("[]", "")
                        != swtbl2_nparray[j, 5].replace("[]", "")
                    ) and (swtbl2_nparray[j, 5] != "NULL"):
                        continue
                    substruct_12 = True
                    substruct_23 = False
                    for k in range(swtbl3_nparray.shape[0]):
                        if swtbl2_nparray[j, 2] == swtbl3_nparray[k, 1]:
                            if (
                                swtbl1_nparray[i, 1].replace("[]", "")
                                != swtbl3_nparray[k, 5].replace("[]", "")
                            ) and (swtbl3_nparray[k, 5] != "NULL"):
                                continue
                            substruct_23 = True
                            dsName = (
                                swtbl1_nparray[i, 1]
                                + "."
                                + swtbl2_nparray[j, 1]
                                + "."
                                + swtbl3_nparray[k, 1]
                                + "."
                                + swtbl3_nparray[k, 2]
                            )
                            # print(dsName)
                            dataStructures[dsName] = [
                                dsName,
                                swtbl1_nparray[i, 1],
                                *(swtbl3_nparray[k, 3:].tolist()),
                            ]
                    if substruct_23 is False:
                        dsName = (
                            swtbl1_nparray[i, 1]
                            + "."
                            + swtbl2_nparray[j, 1]
                            + "."
                            + swtbl2_nparray[j, 2]
                        )
                        # print(dsName)
                        dataStructures[dsName] = [
                            dsName,
                            swtbl1_nparray[i, 1],
                            *(swtbl2_nparray[j, 3:].tolist()),
                        ]
            if substruct_12 is False:
                dsName = swtbl1_nparray[i, 1] + "." + swtbl1_nparray[i, 2]
                # print(dsName)
                dataStructures[dsName] = [
                    dsName,
                    swtbl1_nparray[i, 1],
                    *(swtbl1_nparray[i, 3:].tolist()),
                ]
        # if substruct_01 == False:
        #    print(baseDS)
        #    dataStructures.append(baseDS)
        #    writeFile.write(baseDS.printInfo() + '\n')
        return dataStructures

    def checkDataStructuresValidity(self, dataStructures):
        """
        Remove invalid data structures from a dictionary of data structures. A data
        structure is defined as invalid if the ppmac rejects it when its indices
        are filled-in as zero.
        :param dataStructures:
        :return:
        """
        logging.info(
            "checkDataStructuresValidity: checking if all data structures are valid, "
            "and removing any invalid data structures..."
        )
        invalidCount = 0
        for ds in list(dataStructures):
            cmd_return = self.sendCommand(ds.replace("[]", "[0]"))
            if "ILLEGAL" in cmd_return[0]:
                logging.debug(
                    f"{ds.replace('[]', '[0]')} not a valid ppmac command, deleting"
                    " from dictionary of data structures."
                )
                del dataStructures[ds]
                invalidCount += 1
        logging.info(
            f"checkDataStructuresValidity: removed {invalidCount} invalid data"
            " structures."
        )
        return dataStructures

    def getActiveElementsFromDataStructures(
        self, dataStructures, elementsToIgnore, recordTimings=False, timeout=None
    ):
        """
        Generate a dictionary of active elements from an iterable containing data
        structure names.
        :param dataStructures: Iterable containing data structure names
        :param elementsToIgnore: Set of data structures not to be added to included
        in the active elements read from the ppmac.
        :return: Dictionary containing the current set of active elements, where the
        key is the active element name, and the value is a tuple containing the return
        value from the ppmac and the active element name.
        """
        logging.info(
            "getActiveElementsFromDataStructures: generating dictionary of active"
            " elements..."
        )
        fncStartTime = time.time()
        activeElements = {}
        for ds in dataStructures:
            loopStartTime = time.time()
            N_brackets = ds.count("[]")
            if N_brackets == 0:
                value = self.sendCommand(ds)[0]
                category = self.getDataStructureCategory(ds)
                activeElements[ds] = (ds, value, category, ds, None)
            elif N_brackets == 1:
                self.fillDataStructureIndices_i(
                    ds, activeElements, elementsToIgnore, timeout=timeout
                )
            elif N_brackets == 2:
                self.fillDataStructureIndices_ij(
                    ds, activeElements, elementsToIgnore, timeout=timeout
                )
            elif N_brackets == 3:
                self.fillDataStructureIndices_ijk(
                    ds, activeElements, elementsToIgnore, timeout=timeout
                )
            elif N_brackets == 4:
                self.fillDataStructureIndices_ijkl(
                    ds, activeElements, elementsToIgnore, timeout=timeout
                )
            else:
                logging.info(
                    f"Too many indexed substructures in data structure '{ds}'."
                    " Ignoring."
                )
                continue
            if recordTimings:
                logging.info(ds + f"   time: {time.time() - loopStartTime} sec")
        logging.info("Finished generating dictionary of active elements. ")
        logging.info(f"Total time = {time.time() - fncStartTime} sec")
        return activeElements

    def expandSplicedIndices(self, splicedDataStructure):
        """
        Stuff
        :param splicedDataStructure: String containing a data structure name with one
        filled index that may or may not be spliced to indicate a range of values
        :return:
        """
        if splicedDataStructure.count(":") > 1:
            raise ("Too many indices")
        elif ":" not in splicedDataStructure:
            return [splicedDataStructure]
        else:
            splicedIndices = re.search("\\[([0-9]+):([0-9]+)\\]", splicedDataStructure)
            if splicedIndices is None:
                return [splicedDataStructure]
            startIndex = int(splicedIndices.group(1))
            endIndex = int(splicedIndices.group(2))
            expandedDataStructure = [
                re.sub("([0-9]+:[0-9]+)", str(i), splicedDataStructure)
                for i in range(startIndex, endIndex + 1)
            ]
            return expandedDataStructure

    def generateIgnoreSet(self, ignoreFile):
        ignore = []
        logging.info(f"Using ignore file {ignoreFile}.")
        with open(ignoreFile, "r") as readFile:
            for line in readFile:
                line = line.split("#", 1)[0]
                line = line.strip()
                ignore += line.split()
        expandedIgnore = [
            item
            for dataStructure in ignore
            for item in self.expandSplicedIndices(dataStructure)
        ]
        return set(expandedIgnore)

    def copyDict(self, destValueType, sourceDict):
        return {key: destValueType(*value) for key, value in sourceDict.items()}

    @timer
    def readAndStoreActiveState(self, pathToIgnoreFile):
        if self.local_db_path is None:
            raise IOError(
                "Need to specify temporary directory where Power PMAC Database can be"
                " copied to."
            )
        os.makedirs(self.local_db_path, exist_ok=True)
        self.scpPPMACDatabaseToLocal("/var/ftp/usrflash/Database/*", self.local_db_path)
        # Store data structures in ppmac object
        dataStructures = self.createDataStructuresFromSymbolsTables(
            self.pp_swtlbs_symfiles, self.local_db_path
        )
        validDataStructures = self.checkDataStructuresValidity(dataStructures)
        # Store the dictionary of data strutures in the ppmac object
        self.ppmacInstance.dataStructures = self.copyDict(
            self.ppmacInstance.DataStructure, validDataStructures
        )
        # Store active elements in ppmac object
        elementsToIgnore = self.generateIgnoreSet(pathToIgnoreFile)
        activeElements = self.getActiveElementsFromDataStructures(
            validDataStructures, elementsToIgnore, recordTimings=True
        )  # timeout=10.0
        self.ppmacInstance.activeElements = self.copyDict(
            self.ppmacInstance.ActiveElement, activeElements
        )
        bufferedProgramsInfo = self.getBufferedProgramsInfo()
        self.appendBufferedProgramsInfoWithListings(bufferedProgramsInfo)
        self.ppmacInstance.forwardPrograms = self.copyDict(
            self.ppmacInstance.KinematicTransform, bufferedProgramsInfo["Forward"]
        )
        self.ppmacInstance.inversePrograms = self.copyDict(
            self.ppmacInstance.KinematicTransform, bufferedProgramsInfo["Inverse"]
        )
        self.ppmacInstance.subPrograms = self.copyDict(
            self.ppmacInstance.Program, bufferedProgramsInfo["SubProg"]
        )
        self.ppmacInstance.motionPrograms = self.copyDict(
            self.ppmacInstance.Program, bufferedProgramsInfo["Motion"]
        )
        self.ppmacInstance.plcPrograms = self.copyDict(
            self.ppmacInstance.Program, bufferedProgramsInfo["Plc"]
        )
        coordSystemMotorDefs = self.getCoordSystemMotorDefinitions()
        self.ppmacInstance.coordSystemDefs = self.copyDict(
            self.ppmacInstance.CoordSystemDefinition, coordSystemMotorDefs
        )

    def getCoordSystemMotorDefinitions(self):
        coordSystemMotorDefinitions = {}
        currentCoordSystem = self.sendCommand("&")
        axesDefStatements = self.sendCommand("#*->")
        for definition in axesDefStatements:
            motorDefinitionTokens = PPMACLexer(definition)
            firstToken = motorDefinitionTokens.pop()[1]  # either '&' or '#' token
            if firstToken == "&":
                currentCoordSystem = motorDefinitionTokens.pop()[
                    1
                ]  # coord system number token
                motorDefinitionTokens.pop()[1]  # '#' token
            elif firstToken != "#":
                raise IOError(f"Unexpected token '{firstToken}'")
            motorDefinition = (
                f"&{currentCoordSystem}#{motorDefinitionTokens.getTokensAsString()}"
            )
            if currentCoordSystem in coordSystemMotorDefinitions:
                coordSystemMotorDefinitions[currentCoordSystem][1].append(
                    motorDefinition
                )
            else:
                coordSystemMotorDefinitions[currentCoordSystem] = [
                    currentCoordSystem,
                    [motorDefinition],
                ]
        return coordSystemMotorDefinitions

    def appendBufferedProgramsInfoWithListings(self, bufferedProgramsInfo):
        for programType in bufferedProgramsInfo.keys():
            for programInfo in bufferedProgramsInfo[programType].values():
                programName = programInfo[0]
                programListing = []
                if programType == "Forward" or programType == "Inverse":
                    progCoordSystem = programInfo[4]
                    listing = self.sendCommand(f"&{progCoordSystem} list {programType}")
                else:
                    listing = self.sendCommand(f"list {programName}")
                for line in listing:
                    programListing.append(line + "\n")
                programInfo.append(programListing)

    def getBufferedProgramsInfo(self):
        motion, subProgs, plcs, inverse, forward = ({} for _ in range(5))
        programBuffers = self.sendCommand("buffer")
        for progBuffInfo in programBuffers:
            progBuffInfo = progBuffInfo.split()
            if len(progBuffInfo) < 5:
                continue
            progName = progBuffInfo[0].strip("., ")
            progOffset = progBuffInfo[2].strip("., ")
            progSize = progBuffInfo[4].strip("., ")
            if "SubProg" in progName:
                subProgs[progName] = [progName, progOffset, progSize, "SubProg"]
            elif "Prog" in progName:
                motion[progName] = [progName, progOffset, progSize, "Motion"]
            elif "Plc" in progName:
                plcs[progName] = [progName, progOffset, progSize, "Plc"]
            elif "Inverse" in progName:
                progCoordSystem = progName.rstrip("Inverse").lstrip("&")
                inverse[progName] = [
                    progName,
                    progOffset,
                    progSize,
                    "Inverse",
                    progCoordSystem,
                ]
            elif "Forward" in progName:
                progCoordSystem = progName.rstrip("Forward").lstrip("&")
                forward[progName] = [
                    progName,
                    progOffset,
                    progSize,
                    "Forward",
                    progCoordSystem,
                ]
        return {
            "SubProg": subProgs,
            "Motion": motion,
            "Plc": plcs,
            "Inverse": inverse,
            "Forward": forward,
        }


class PowerPMAC:
    class DataStructure:
        def __init__(
            self,
            name="",
            base="",
            field1="",
            field2="",
            field3="",
            field4="",
            field5="",
            field6="",
            field7="",
            field8="",
            field9="",
            field10="",
            field11="",
            field12="",
        ):
            self.name = name
            self.base = base
            self.field1 = field1
            self.field2 = field2
            self.field3 = field3
            self.field4 = field4
            self.field5 = field5
            self.field6 = field6
            self.field7 = field7
            self.field8 = field8
            self.field9 = field9
            self.field10 = field10
            self.field11 = field11
            self.field12 = field12

        def printInfo(self):
            s = (
                self.name
                + ", "
                + self.base
                + ", "
                + self.field1
                + ", "
                + self.field2
                + ", "
                + self.field3
                + ", "
                + self.field4
                + ", "
                + self.field5
                + ", "
                + self.field6
                + ", "
                + self.field7
                + ", "
                + self.field8
                + ", "
                + self.field9
                + ", "
                + self.field10
                + ", "
                + self.field11
                + ", "
                + self.field12
            )
            return s

    class ActiveElement:
        def __init__(
            self, name="", value="", category="", dataStructure="", indices=[]
        ):
            self.name = name
            self.value = value
            if dataStructure == "":
                self.dataStructure = re.sub("\\[([0-9]+)\\]", "[]", self.name)
            else:
                self.dataStructure = dataStructure
            if category == "":
                if self.dataStructure.find(".") == -1:
                    category = self.dataStructure
                else:
                    category = self.dataStructure[0 : self.dataStructure.find(".")]
                self.category = category.replace("[]", "")
            else:
                self.category = category
            self.indices = indices

        def printInfo(self):
            return self.name + "  " + self.value

    class CoordSystemDefinition:
        def __init__(self, csNumber=None, definitions=[], forward=None, inverse=None):
            self.csNumber = csNumber  # coordinate system number
            self.motors = []  # list of motors assigned to CS
            self.motor = {}  # dict definition of each motor in terms of the axes
            # List of strings containing axes defs. I don't think these need
            # to be sorted.
            self.axisDefs = definitions
            self.parseAxesDefinitions(self.axisDefs)
            self.forward = forward  # instance of _KinematicTransform. Not implemented
            self.inverse = inverse  # instance of _KinematicTransform. Not implemented

        def parseAxesDefinitions(self, definitions):
            for definition in definitions:
                tokens = PPMACLexer(definition)
                motorNum = tokens.pop(3)[1]
                self.motors.append(motorNum)
                tokens.pop()
                self.motor[motorNum] = tokens.getTokensAsString()

        def printInfo(self):
            return "".join(
                [
                    f"&{self.csNumber}#{key}->{value}\n"
                    for key, value in self.motor.items()
                ]
            )

    def Program(self, name, size, offset, type, listing):
        return self._Program(self, name, size, offset, type, listing)

    class _Program:
        def __init__(self, ppmac, name, size, offset, type, listing):
            self.name = name
            self.size = size
            self.offset = offset
            self.type = type
            self.listing = listing
            self.dataStructureNames = set(ppmac.dataStructures.keys())
            # Currently dataStructures are not read from the repository
            # self.lexer = PPMACLexer('\n'.join(self.listing), self.dataStructureNames)
            # self.tokens = self.lexer.tokens

        def printInfo(self):
            s = (
                f"{self.type}, {self.name}, size {self.size}, offset {self.offset}\n"
                + "".join(self.listing)
            )
            return s

    def KinematicTransform(self, name, size, offset, type, coordSystem, listing):
        return self._KinematicTransform(
            self, name, size, offset, type, coordSystem, listing
        )

    class _KinematicTransform(_Program):
        def __init__(self, ppmac, name, size, offset, type, coordSystem, listing):
            super().__init__(ppmac, name, size, offset, type, listing)
            self.coodSystem = coordSystem

        def printInfo(self):
            return (
                f"{self.type}, {self.name}, size {self.size}, offset {self.offset}, cs"
                f" {self.coodSystem}\n"
            )

    def __init__(self, name="unknown"):
        # Source: hardware or respository
        self.source = name
        # Dictionary mapping DS names to dataStructure objects
        self.dataStructures = {}
        # Dictionary of active elements
        self.activeElements = {}
        # Dictionary of programs
        self.motionPrograms = {}
        # Dictionary of sub-programs
        self.subPrograms = {}
        # Dictionary of plc-programs
        self.plcPrograms = {}
        # Dictionary of programs
        self.forwardPrograms = {}
        # Dictionary of programs
        self.inversePrograms = {}
        # Dictionary of coord system definitions
        self.coordSystemDefs = {}
        # 16384 total I variables, values range from I0 to I16383
        # 16384 total P variables, values range from P0 to P65535
        # 16384 total M variables, values range from M0 to M16383
        # 8192 Q variables per coordinate system, values range from Q0 to Q8191
        # 8192 L variables per communications thread, coordinate system, or PLC;
        # values range from L0 to L8191
        # Power PMAC supports up to 32 PLC programs
        # Power PMAC supports up to 256 motors
        # BufIo[i] can have i = 0,...,63 (software reference manual p.541-542)
        # Power PMAC supports up to 256 cam tables
        # Power PMAC supports up to 256 compensation tables
        # Power PMAC supports up to 128 coordinate systems
        # Power PMAC supports up to 9 ECAT networks
        # Power PMAC supports up to 768 encoder conversion tables (software
        # reference manual p.206)
        # Gate1[i] can have i = 4,...,19 (software reference manual p.237)
        # Gate2[i] has an unknown range of indices i
        # self.numberOfGate2ICs = ???
        # Gate3[i] can have i = 0,..,15 (software reference manual p.289)
        # GateIo[i] can have i = 0,..,15 (software reference manual p.360),
        # although i > 15 does not return an error


class PPMACanalyse:
    def __init__(self, ppmacArgs):
        self.resultsDir = "ppmacAnalyse"
        self.verbosity = "info"
        self.ipAddress = "192.168.56.10"
        self.port = 1025
        self.operationType = "all"
        self.operationTypes = ["all", "active", "project"]
        self.backupDir = None
        self.username = None
        self.password = None
        if ppmacArgs.interface is not None:
            if not isValidNetworkInterface(ppmacArgs.interface[0]):
                raise IOError(
                    f"Interface {ppmacArgs.interface} not a valid network interface"
                    " <ipaddress>:<port>"
                )
            self.ipAddress = ppmacArgs.interface[0].split(":")[0]
            self.port = ppmacArgs.interface[0].split(":")[1]
        # Configure logger
        if ppmacArgs.resultsdir is not None:
            self.resultsDir = ppmacArgs.resultsdir[0]
        os.makedirs(self.resultsDir, exist_ok=True)
        logfile = self.resultsDir + "/" + "ppmacanalyse.log"
        logging.basicConfig(filename=logfile, level=logging.INFO)
        if ppmacArgs.username is not None:
            self.username = ppmacArgs.username
        if ppmacArgs.password is not None:
            self.password = ppmacArgs.password
        # Perform the backup, compare, recover or download
        if ppmacArgs.backup is not None:
            self.processBackupOptions(ppmacArgs)
            self.backup(self.operationType)
        if ppmacArgs.compare is not None:
            self.processCompareOptions(ppmacArgs)
            self.compare(self.operationType)
        if ppmacArgs.recover is not None:
            self.processRecoverOptions(ppmacArgs)
            self.recover()
        if ppmacArgs.download is not None:
            self.processDownloadOptions(ppmacArgs)
            self.download()

    def processCompareOptions(self, ppmacArgs):
        if len(ppmacArgs.compare) < 3:
            raise IOError(
                "Insufficient number of arguments, please specify compare option and"
                " TWO sources for comparison."
            )
        if ppmacArgs.compare[0] not in self.operationTypes:
            raise IOError(
                f"Unrecognised backup option {ppmacArgs.compare[0]}, "
                'should be "all","active" or "project".'
            )
        self.operationType = ppmacArgs.compare[0]
        self.compareSourceA = ppmacArgs.compare[1]
        self.compareSourceB = ppmacArgs.compare[2]
        if not isValidNetworkInterface(self.compareSourceA) and not os.path.isdir(
            self.compareSourceA
        ):
            raise IOError(
                f"{self.compareSourceA} not an existing directory or valid network"
                " interface <ipaddress>:<port>"
            )
        if not isValidNetworkInterface(self.compareSourceB) and not os.path.isdir(
            self.compareSourceB
        ):
            raise IOError(
                f"{self.compareSourceB} not an existing directory or valid network"
                " interface <ipaddress>:<port>"
            )
        self.compareDir = self.resultsDir
        os.makedirs(self.compareDir, exist_ok=True)
        self.ignoreFile = "ignore/ignore"
        if len(ppmacArgs.compare) > 3:
            self.ignoreFile = ppmacArgs.compare[3]
        if not fileExists(self.ignoreFile):
            raise IOError(f"Ignore file {self.ignoreFile} not found.")

    def compare(self, type="all"):
        ppmacA = PowerPMAC()
        ppmacB = PowerPMAC()
        if isValidNetworkInterface(self.compareSourceA):
            sshClient.hostname = self.compareSourceA.strip().split(":")[0]
            sshClient.port = self.compareSourceA.strip().split(":")[1]
            # Check that we can connect
            self.checkConnection(False)
            #sshClient.connect()
            if type == "all" or type == "active":
                hardwareWriteRead = PPMACHardwareWriteRead(
                    ppmacA, f"{self.compareDir}/tmp/databaseA"
                )
                hardwareWriteRead.readAndStoreActiveState(self.ignoreFile)
            if type == "all" or type == "project":
                projectASaved = PPMACProject(
                    "hardware",
                    "/opt/ppmac/usrflash/*",
                    f"{self.compareDir}/tmp/projectA/saved",
                )
                projectAActive = PPMACProject(
                    "hardware",
                    "/var/ftp/usrflash/*",
                    f"{self.compareDir}/tmp/projectA/active",
                )
            sshClient.disconnect()
        else:
            if type == "all" or type == "active":
                repositoryWriteRead = PPMACRepositoryWriteRead(ppmacA, self.compareSourceA)
                repositoryWriteRead.readAndStoreActiveElements()
                repositoryWriteRead.readAndStoreBufferedPrograms()
                repositoryWriteRead.readAndStoreCSAxesDefinitions()
            if type == "all" or type == "project":
                projectASaved = PPMACProject(
                    "repository", f"{self.compareSourceA}/project/saved"
                )
                projectAActive = PPMACProject(
                    "repository", f"{self.compareSourceA}/project/active"
                )
        if isValidNetworkInterface(self.compareSourceB):
            sshClient.hostname = self.compareSourceB.strip().split(":")[0]
            sshClient.port = self.compareSourceB.strip().split(":")[1]
            # Check that we can connect
            self.checkConnection(False)
            #sshClient.connect()
            if type == "all" or type == "active":
                hardwareWriteRead = PPMACHardwareWriteRead(
                    ppmacB, f"{self.compareDir}/tmp/databaseB"
                )
                hardwareWriteRead.readAndStoreActiveState(self.ignoreFile)
            if type == "all" or type == "project":
                projectBSaved = PPMACProject(
                    "hardware",
                    "/opt/ppmac/usrflash/*",
                    f"{self.compareDir}/tmp/projectB/saved",
                )
                projectBActive = PPMACProject(
                    "hardware",
                    "/var/ftp/usrflash/*",
                    f"{self.compareDir}/tmp/projectB/active",
                )
            sshClient.disconnect()
        else:
            if type == "all" or type == "active":
                repositoryWriteRead = PPMACRepositoryWriteRead(ppmacB, self.compareSourceB)
                repositoryWriteRead.readAndStoreActiveElements()
                repositoryWriteRead.readAndStoreBufferedPrograms()
                repositoryWriteRead.readAndStoreCSAxesDefinitions()
            if type == "all" or type == "project":    
                projectBSaved = PPMACProject(
                    "repository", f"{self.compareSourceB}/project/saved"
                )
                projectBActive = PPMACProject(
                    "repository", f"{self.compareSourceB}/project/active"
                )
        # Run comparison        
        ppmacComparison = PPMACCompare(ppmacA, ppmacB, self.compareDir)
        if type == "all" or type == "active":
            ppmacComparison.compareActiveElements()
            ppmacComparison.comparePrograms()
            ppmacComparison.compareCoordSystemAxesDefinitions()
        if type == "all" or type == "project":    
            savedProjComparison = ProjectCompare(projectASaved, projectBSaved)
            savedProjDiffPath = f"{self.compareDir}/project/saved"
            os.makedirs(savedProjDiffPath, exist_ok=True)
            savedProjComparison.compareProjectFiles(savedProjDiffPath)
            activeProjComparison = ProjectCompare(projectAActive, projectBActive)
            activeProjDiffPath = f"{self.compareDir}/project/active"
            os.makedirs(activeProjDiffPath, exist_ok=True)
            activeProjComparison.compareProjectFiles(activeProjDiffPath)

    def processBackupOptions(self, ppmacArgs):
        self.name = "hardware"
        if ppmacArgs.name is not None:
            self.name = ppmacArgs.name[0]
        if len(ppmacArgs.backup) > 0:
            if ppmacArgs.backup[0] not in self.operationTypes:
                raise IOError(
                    f"Unrecognised backup option {ppmacArgs.backup[0]}, "
                    'should be "all","active" or "project".'
                )
            self.operationType = ppmacArgs.backup[0]
        self.backupDir = self.resultsDir
        os.makedirs(self.backupDir, exist_ok=True)
        self.ignoreFile = "ignore/ignore"
        if len(ppmacArgs.backup) > 1:
            self.ignoreFile = ppmacArgs.backup[1]
        if not fileExists(self.ignoreFile):
            raise IOError(f"Ignore file {self.ignoreFile} not found.")

    @connectDisconnect
    def backup(self, type="all"):
        ppmacA = PowerPMAC(self.name)
        # Check that we can connect
        self.checkConnection(False)
        if type == "all" or type == "active":
            # read current state of ppmac and store in ppmacA object
            hardwareWriteRead = PPMACHardwareWriteRead(ppmacA, f"{self.backupDir}/tmp")
            hardwareWriteRead.readAndStoreActiveState(self.ignoreFile)
            # write current state of ppmacA object to repository
            activeDir = self.backupDir
            repositoryWriteRead = PPMACRepositoryWriteRead(ppmacA, activeDir)
            repositoryWriteRead.writeActiveState()
        if type == "all" or type == "project":
            savedProjectDir = f"{self.backupDir}/project/saved"
            os.makedirs(savedProjectDir, exist_ok=True)
            scpFromPowerPMACtoLocal(
                "/opt/ppmac/usrflash/*", savedProjectDir, recursive=True
            )
            activeProjectDir = f"{self.backupDir}/project/active"
            os.makedirs(activeProjectDir, exist_ok=True)
            scpFromPowerPMACtoLocal(
                "/var/ftp/usrflash/*", activeProjectDir, recursive=True
            )

    def checkConnection(self, disconnectAfter):
        if self.username is not None and self.password is not None:
            logging.info(self.username)
            connect_status = sshClient.connect(username=self.username[0],
                password=self.password[0])
        else:
            connect_status = sshClient.connect()
        if connect_status is None:
            #All OK
            return
        if "Invalid username or password" in connect_status:
            raise IOError(f"ERROR: Invalid username and/or password.")
        if "Cannot connect" in connect_status:
            logging.error("Cannot establish connection to Power PMAC at "+
                str(self.ipAddress)+":"+str(self.port)) 
            raise IOError(f"ERROR: Cannot establish connection to Power PMAC at "
            f" {self.ipAddress}:{self.port}")
        if disconnectAfter:
            sshClient.disconnect()


    def processRecoverOptions(self, ppmacArgs):
        # Specify directory containing backup
        if len(ppmacArgs.recover) < 1:
            raise IOError("Unspecified directory to use for recovery.")
        self.backupDir = ppmacArgs.recover[0]
        if not os.path.isdir(self.backupDir):
            raise IOError(f"Repository directory {self.backupDir} does not exist.")


    @connectDisconnect
    def recover(self):
        # Check that we can connect
        self.checkConnection(False)
        recoverScript = "recover.sh"
        with open(recoverScript, "w+") as writeFile:
            writeFile.write(recoveryCmds)
        scpFromLocalToPowerPMAC(recoverScript, "/tmp/")
        os.system("rm recover.sh")
        executeRemoteShellCommand(f"chmod 777 /tmp/{recoverScript}")
        executeRemoteShellCommand("mkdir /tmp/recover")
        scpFromLocalToPowerPMAC(
            f"{self.backupDir}/Project", "/tmp/recover/", recursive=True
        )
        scpFromLocalToPowerPMAC(
            f"{self.backupDir}/Database", "/tmp/recover/", recursive=True
        )
        scpFromLocalToPowerPMAC(
            f"{self.backupDir}/Temp", "/tmp/recover/", recursive=True
        )
        executeRemoteShellCommand("/tmp/recover.sh")
        scpFromPowerPMACtoLocal(
            "/tmp/recover.log", f"{self.resultsDir}/", recursive=False
        )

    def processDownloadOptions(self, ppmacArgs):
        # Specify directory containing backup
        if len(ppmacArgs.download) < 1:
            raise IOError("Unspecified directory to use for recovery.")
        self.backupDir = ppmacArgs.download[0]
        if not os.path.isdir(self.backupDir):
            raise IOError(f"Repository directory {self.backupDir} does not exist.")


    @connectDisconnect
    def download(self):
        # Check that we can connect
        #self.checkConnection(False)
        # Copy usrflash files into ppmac
        executeRemoteShellCommand("rm -rf /var/ftp/usrflash/Project/*")
        for file in os.listdir(self.backupDir):
            scpFromLocalToPowerPMAC(
                f"{self.backupDir}/{file}", "/var/ftp/usrflash/Project", recursive=True
            )
        # Make directory that projpp will log to
        executeRemoteShellCommand("mkdir -p /var/ftp/usrflash/Project/Log")
        # Looks like everything in project dir needs to be rwx
        executeRemoteShellCommand("chmod 777 -R -f /var/ftp/usrflash/Project")
        # Finally execute a projpp to parse and load new project
        executeRemoteShellCommand("projpp -l")


sshClient = dls_pmacremote.PPmacSshInterface()


def main():
    """Main entry point of the script."""
    if len(sys.argv) < 2:
        print(" -> Run dls-ppmac-analyse.py --help for details on how to" 
        + " use the Power-Pmac analyse tool")
        return
    ppmacArgs = parseArgs()
    if ppmacArgs.gui:
        dls_pmacanalyse.ppmacanalyse_control.main()
    else:
        PPMACanalyse(ppmacArgs)


if __name__ == "__main__":
    main()
