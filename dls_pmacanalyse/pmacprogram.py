from dataclasses import dataclass
from logging import getLogger
from typing import List, Optional

from dls_pmacanalyse.pmacparser import PmacParser
from dls_pmacanalyse.pmacvariables import PmacToken, PmacVariable
from dls_pmacanalyse.utils import (
    compareFloats,
    isNumber,
    isString,
    stripStringQuotes,
    tokenToInt,
    toNumber,
)

log = getLogger(__name__)


@dataclass
class ProgInfo:
    num: int
    exists: bool
    code: Optional[List[str]]
    p_range: Optional[range] = None


class PmacProgram(PmacVariable):
    def __init__(self, prefix, name, variable, lines=None, offsets=None):
        PmacVariable.__init__(self, prefix, name, variable)
        self.offsets = offsets
        self.lines: List[str] = lines or []

    def add(self, t):
        if not isinstance(t, PmacToken):
            log.warning("PmacProgram: %s is not a token" % repr(t))
        self.value.append(t)

    def clear(self):
        self.value = []

    def valueText(self, typ=0, ignore_ret=False):
        result = ""
        last_line = len(self.value) - 1
        for i, t in enumerate(self.value):
            if t == "\n":
                if len(result) > 0 and not result[-1] == "\n":
                    result += str(t)
            elif not ignore_ret or t != "RETURN" or i < last_line:
                if len(result) == 0:
                    pass
                elif result[-1].isalpha() and str(t)[0].isalpha():
                    result += " "
                elif result[-1].isdigit() and str(t)[0].isdigit():
                    result += " "
                result += str(t)
                if typ == 1 and len(result.rsplit("\n", 1)[-1]) > 60:
                    result += "\n"
        if len(result) == 0 or result[-1] != "\n":
            result += "\n"
        return result

    def compare(self, other):
        # Strip the newline tokens from the two lists.  There's
        # probably a better way of doing this.
        a = []
        for i in self.value:
            if i == "\n":
                pass
            else:
                a.append(i)
        b = []
        for i in other.value:
            if i == "\n":
                pass
            else:
                b.append(i)
        # Now compare them token by token
        result = True
        while len(a) > 0 and len(b) > 0:
            # Extract the current head token from each list
            a0 = a[0]
            b0 = b[0]
            a[0:1] = []
            b[0:1] = []
            # Compare them
            if isNumber(a0) and isNumber(b0):
                if not compareFloats(toNumber(a0), toNumber(b0), 0.00001):
                    result = False
                    a0.compareFail = True
                    b0.compareFail = True
            elif a0 == "COMMAND" and b0 == "COMMAND" and len(a) > 0 and len(b) > 0:
                # Get the command strings
                a0 = a[0]
                b0 = b[0]
                a[0:1] = []
                b[0:1] = []
                if isString(str(a0)) and isString(str(b0)):
                    # Parse them
                    parserA = PmacParser([stripStringQuotes(str(a0))], self)
                    varA = PmacCommandString(parserA.tokens())
                    parserB = PmacParser([stripStringQuotes(str(b0))], self)
                    varB = PmacCommandString(parserB.tokens())
                    if not varA.compare(varB):
                        result = False
                        a0.compareFail = True
                        b0.compareFail = True
                else:
                    if a0 != b0:
                        result = False
                        a0.compareFail = True
                        b0.compareFail = True
            else:
                if a0 != b0:
                    result = False
                    a0.compareFail = True
                    b0.compareFail = True
        for a0 in a:
            a0.compareFail = True
            result = False
        for b0 in b:
            b0.compareFail = True
            result = False
        return result

    def isEmpty(self):
        a = []
        for i in self.value:
            if i == "\n":
                pass
            else:
                a.append(i)
        return len(a) == 0 or a == ["RETURN"]

    # TODO this is the code that prints red sections for non matching code
    # maybe reuse some of this ????
    def htmlCompare(self, page, parent, other):
        lineLen = 0
        for t in self.value:
            if t == "\n":
                if lineLen > 0:
                    page.lineBreak(parent)
                    lineLen = 0
            else:
                if t.compareFail:
                    page.text(page.emphasize(parent), t)
                else:
                    page.text(parent, t)
                lineLen += len(t)
                if lineLen > 60:
                    page.lineBreak(parent)
                    lineLen = 0


class PmacPlcProgram(PmacProgram):
    def __init__(self, n, v=[], lines=None, offsets=None):
        PmacProgram.__init__(self, "plc", n, v, lines, offsets)
        self.isRunning = False
        self.shouldBeRunning = False

    def info(self, comment: Optional[str] = None):
        return ProgInfo(
            num=self.name,
            exists=self.lines is not None,
            code=self.lines,
            p_range=range(self.name * 100, self.name * 100 + 100),
        )

    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ""
            if len(self.value) > 0:
                result = "\nopen plc %s clear\n" % self.name
                result += self.valueText(ignore_ret=True)
                result += "close\n"
        return result

    def copyFrom(self):
        result = PmacPlcProgram(self.name)
        result.value = self.value
        result.read_only = self.read_only
        result.offsets = self.offsets
        result.lines = self.lines
        return result

    def setShouldBeRunning(self):
        """
        Sets the shouldBeRunning flag if the PLC does not contain a disable
        statement for itself.
        """
        self.shouldBeRunning = True
        state = "idle"
        for i in self.value:
            if state == "idle":
                if i == "DISABLE":
                    state = "disable"
            elif state == "disable":
                if i == "PLC":
                    state = "plc"
                else:
                    state = "idle"
            elif state == "plc":
                if tokenToInt(i) == self.name:
                    self.shouldBeRunning = False
                state = "idle"

    def setIsRunning(self, state):
        self.isRunning = state


class PmacCommandString(PmacProgram):
    def __init__(self, v):
        PmacProgram.__init__(self, "CMD", 0, v)


class PmacCsAxisDef(PmacProgram):
    def __init__(self, cs, n, v=[PmacToken("0")]):
        PmacProgram.__init__(self, "&%s#" % cs, n, v)
        self.cs = cs

    def dump(self, typ=0):
        if typ == 1:
            result = "%s" % self.valueText()
        else:
            result = "&%s#%s->%s" % (self.cs, self.name, self.valueText())
        return result

    def isZero(self):
        result = True
        for t in self.value:
            if t == "0" or t == "0.0" or t == "\n":
                pass
            else:
                result = False
        return result

    def copyFrom(self):
        result = PmacCsAxisDef(self.cs, self.name)
        result.value = self.value
        result.read_only = self.read_only
        result.offsets = self.offsets
        result.lines = self.lines
        return result


class PmacForwardKinematicProgram(PmacProgram):
    def __init__(self, n, v=[]):
        PmacProgram.__init__(self, "fwd", n, v)

    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ""
            if len(self.value) > 0:
                result = "\n&%s open forward clear\n" % self.name
                result += self.valueText(ignore_ret=True)
                result += "close\n"
        return result

    def copyFrom(self):
        result = PmacForwardKinematicProgram(self.name)
        result.value = self.value
        result.read_only = self.read_only
        result.offsets = self.offsets
        result.lines = self.lines
        return result


class PmacInverseKinematicProgram(PmacProgram):
    def __init__(self, n, v=[]):
        PmacProgram.__init__(self, "inv", n, v)

    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ""
            if len(self.value) > 0:
                result = "\n&%s open inverse clear\n" % self.name
                result += self.valueText(ignore_ret=True)
                result += "close\n"
        return result

    def copyFrom(self):
        result = PmacInverseKinematicProgram(self.name)
        result.value = self.value
        result.read_only = self.read_only
        result.offsets = self.offsets
        result.lines = self.lines
        return result


class PmacMotionProgram(PmacProgram):
    def __init__(self, n, v=[], lines=None, offsets=None):
        PmacProgram.__init__(self, "prog", n, v, lines, offsets)

    def info(self, comment: Optional[str] = None):
        return ProgInfo(num=self.name, exists=self.lines is not None, code=self.lines)

    def dump(self, typ=0):
        if typ == 1:
            result = self.valueText()
        else:
            result = ""
            if len(self.value) > 0:
                result = "\nopen program %s clear\n" % self.name
                result += self.valueText(ignore_ret=True)
                result += "close\n"
        return result

    def copyFrom(self):
        result = PmacMotionProgram(self.name)
        result.value = self.value
        result.read_only = self.read_only
        result.offsets = self.offsets
        result.lines = self.lines
        return result
