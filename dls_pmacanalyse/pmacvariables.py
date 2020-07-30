from dataclasses import dataclass
from dls_pmacanalyse.errors import ConfigError
from logging import getLogger
from typing import Optional

from dls_pmacanalyse.utils import tokenIsFloat, tokenToFloat

log = getLogger(__name__)


@dataclass
class VariableInfo:
    """A basic representation of a pmac variable for representation to a user"""

    name: str
    value: str
    comment: Optional[str] = None
    node: Optional[int] = None  # TODO lets get rid of this and include it in the 'name'


class PmacToken(object):
    def __init__(self, text=None):
        self.fileName = ""
        self.line = ""
        self.text = ""
        self.compareFail = False
        if text is not None:
            self.text = text

    def set(self, text, fileName, line):
        self.text = text
        self.fileName = fileName
        self.line = line
        self.compareFail = False

    def __str__(self):
        return self.text

    def __eq__(self, other):
        return self.text == str(other)

    def __ne__(self, other):
        return self.text != str(other)

    def __len__(self):
        return len(self.text)

    def lower(self):
        return self.text.lower()


class PmacVariable(object):
    spaces = "                        "

    def __init__(self, prefix, number, value, comment=None):
        self.typeStr = "%s%s" % (prefix, number)
        self.number = number
        self.value = value
        self.read_only = False
        self.comment = None

    def info(self, comment: Optional[str] = None) -> VariableInfo:
        raise NotImplementedError

    def dump(self):
        raise NotImplementedError

    def addr(self):
        return self.typeStr

    def set(self, v):
        self.value = v

    def compare(self, other):
        if self.value == "" or other.value == "":
            return False
        elif self.read_only or other.read_only:
            return True
        elif tokenIsFloat(self.value) and tokenIsFloat(other.value):
            a = tokenToFloat(self.value)
            b = tokenToFloat(other.value)
            return (a >= b - 0.00001) and (a <= b + 0.00001)
        else:
            return self.value == other.value

    def valStr(self):
        if isinstance(self.value, float):
            result = ("%.12f" % self.value).rstrip("0")
            if result.endswith("."):
                result += "0"
        else:
            result = "%s" % self.value
        return result

    def getIntValue(self):
        return int(self.value)

    def getFloatValue(self):
        return float(self.value)

    def isEmpty(self):
        return False

    # a factory method for creating a PmacVariable from a string
    @classmethod
    def makeVars(cls, varType, nodeList, n):
        """Makes a variable of the correct type."""
        result = []
        if varType == "i":
            result.append(PmacIVariable(n))
        elif varType == "p":
            result.append(PmacPVariable(n))
        elif varType == "m":
            result.append(PmacMVariable(n))
        elif varType == "ms":
            for ms in nodeList:
                result.append(PmacMsIVariable(ms, n))
        elif varType == "&":
            for cs in nodeList:
                result.append(PmacQVariable(cs, n))
        else:
            raise ConfigError("Cannot decode variable type %s" % repr(varType))
        return result


class PmacIVariable(PmacVariable):
    useHexAxis = [2, 3, 4, 5, 10, 24, 25, 42, 43, 44, 55, 81, 82, 83, 84, 91, 95]
    useHexGlobal = range(8000, 8192)
    axisVarMin = 100
    axisVarMax = 3299
    varsPerAxis = 100

    def __init__(self, number, value=0, read_only=False):
        PmacVariable.__init__(self, "i", number, value)
        self.read_only = read_only

    def info(self, comment: Optional[str] = None):
        return VariableInfo(
            name=f"i{self.number}", value=self.valStr(), comment=comment
        )

    def dump(self, typ=0, comment=""):
        result = ""
        if typ == 1:
            result = "%s" % self.valStr()
        else:
            if self.read_only:
                result += ";"
            result += "i%s=%s" % (self.number, self.valStr())
            if len(comment) == 0:
                result += "\n"
            else:
                if len(result) < len(self.spaces):
                    result += self.spaces[len(result) :]
                result += ";%s\n" % comment
        return result

    def copyFrom(self):
        result = PmacIVariable(self.number)
        result.value = self.value
        result.read_only = self.read_only
        return result

    def valStr(self):
        if isinstance(self.value, float):
            result = ("%.12f" % self.value).rstrip("0")
            if result.endswith("."):
                result += "0"
        else:
            useHex = False
            if self.number >= self.axisVarMin and self.number <= self.axisVarMax:
                useHex = (self.number % self.varsPerAxis) in self.useHexAxis
            else:
                useHex = self.number in self.useHexGlobal
            if useHex:
                result = "$%x" % self.value
            else:
                result = "%s" % self.value
        return result


class PmacMVariable(PmacVariable):
    def __init__(self, number, type="*", address=0, offset=0, width=0, format="U"):
        PmacVariable.__init__(self, "m", number, 0)
        self.set(type, address, offset, width, format)

    def info(self, comment: Optional[str] = None, content: bool = False):
        value = self.contentsStr() if content else self.valStr()
        return VariableInfo(name=f"m{self.number}", value=value, comment=comment)

    def dump(self, typ=0):
        if typ == 1:
            result = "%s" % self.valStr()
        else:
            result = "m%s->%s\n" % (self.number, self.valStr())
        return result

    def valStr(self):
        result = ""
        if self.type == "*":
            result += "*"
        elif self.type in ["X", "Y"]:
            result += "%s:$%x" % (self.type, self.address)
            if self.width == 24:
                result += ",24"
                if not self.format == "U":
                    result += ",%s" % self.format
            else:
                result += ",%s" % self.offset
                if not self.width == 1 or not self.format == "U":
                    result += ",%s" % self.width
                    if not self.format == "U":
                        result += ",%s" % self.format
        elif self.type in ["D", "DP", "F", "L"]:
            result += "%s:$%x" % (self.type, self.address)
        elif self.type in ["TWS", "TWR", "TWD", "TWB"]:
            result += "%s:$%x" % (self.type, self.address)
        else:
            log.error(f"Unsupported type {self.type} in mvar {self.address}")
        return result

    def contentsStr(self):
        return PmacVariable.valStr(self)

    def set(self, type, address, offset, width, format):
        self.type = type
        self.address = address
        self.offset = offset
        self.width = width
        self.format = format

    def setValue(self, value):
        self.value = value

    def copyFrom(self):
        result = PmacMVariable(self.number)
        result.value = self.value
        result.read_only = self.read_only
        result.type = self.type
        result.address = self.address
        result.offset = self.offset
        result.width = self.width
        result.format = self.format
        return result

    def compare(self, other):
        if self.read_only or other.read_only:
            return True
        else:
            return (
                self.type == other.type
                and self.address == other.address
                and self.offset == other.offset
                and self.width == other.width
                and self.format == other.format
            )


class PmacPVariable(PmacVariable):
    def __init__(self, number, value=0):
        PmacVariable.__init__(self, "p", number, value)

    def info(self, comment: Optional[str] = None):
        return VariableInfo(
            name=f"p{self.number}", value=self.valStr(), comment=comment
        )

    def dump(self, typ=0):
        if typ == 1:
            result = "%s" % self.valStr()
        else:
            result = "p%s=%s\n" % (self.number, self.valStr())
        return result

    def copyFrom(self):
        result = PmacPVariable(self.number)
        result.value = self.value
        result.read_only = self.read_only
        return result


class PmacQVariable(PmacVariable):
    def __init__(self, cs, number, value=0):
        PmacVariable.__init__(self, "&%sq" % cs, number, value)
        self.cs = cs

    def info(self, comment: Optional[str] = None):
        return VariableInfo(
            name=f"q{self.number}", value=self.valStr(), comment=comment
        )

    def dump(self, typ=0):
        if typ == 1:
            result = "%s" % self.valStr()
        else:
            result = "&%sq%s=%s\n" % (self.cs, self.number, self.valStr())
        return result

    def copyFrom(self):
        result = PmacQVariable(self.cs, self.number)
        result.value = self.value
        result.read_only = self.read_only
        return result


class PmacFeedrateOverride(PmacVariable):
    def __init__(self, cs, value=0):
        PmacVariable.__init__(self, "&%s%%" % cs, 0, value)
        self.cs = cs

    def dump(self, typ=0):
        if typ == 1:
            result = "%s" % self.valStr()
        else:
            result = "&%s%%%s\n" % (self.cs, self.valStr())
        return result

    def copyFrom(self):
        result = PmacFeedrateOverride(self.cs)
        result.value = self.value
        result.read_only = self.read_only
        return result


class PmacMsIVariable(PmacVariable):
    def __init__(self, ms, number, value="", read_only=False):
        PmacVariable.__init__(self, "ms%si" % ms, number, value)
        self.ms = ms
        self.read_only = read_only

    def info(self, comment: Optional[str] = None):
        return VariableInfo(
            name=f"i{self.number}", value=self.valStr(), comment=comment, node=self.ms
        )

    def dump(self, typ=0):
        if typ == 1:
            result = "%s" % self.valStr()
        else:
            result = ""
            if self.read_only:
                result += ";"
            result += "ms%s,i%s=%s\n" % (self.ms, self.number, self.valStr())
        return result

    def copyFrom(self):
        result = PmacMsIVariable(self.ms, self.number)
        result.value = self.value
        result.read_only = self.read_only
        return result
