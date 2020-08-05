from dls_pmacanalyse.errors import LexerError, ParserError
from dls_pmacanalyse.pmacvariables import PmacToken


class PmacLexer(object):
    tokens = [
        "!",
        "@",
        "#",
        "##",
        "$",
        "$$",
        "$$$",
        "$$$***",
        "$$*",
        "$*",
        "%",
        "&",
        "\\",
        "<",
        ">",
        "/",
        "?",
        "??",
        "???",
        "A",
        "ABR",
        "ABS",
        "X",
        "Y",
        "Z",
        "U",
        "V",
        "W",
        "B",
        "C",
        "CHECKSUM",
        "CID",
        "CLEAR",
        "ALL",
        "PLCS",
        "CLOSE",
        "CPU",
        "DATE",
        "DEFINE",
        "BLCOMP",
        "CCBUF",
        "COMP",
        "GATHER",
        "LOOKAHEAD",
        "ROTARY",
        "TBUF",
        "TCOMP",
        "TRACE",
        "UBUFFER",
        "DELETE",
        "TEMPS",
        "PLCC",
        "DISABLE",
        "PLC",
        "EAVERSION",
        "ENABLE",
        "ENDGATHER",
        "F",
        "FRAX",
        "H",
        "HOME",
        "HOMEZ",
        "I",
        "=",
        "*",
        "@",
        "IDC",
        "IDNUMBER",
        "INC",
        "J",
        "+",
        "-",
        ":",
        "==",
        "^",
        "K",
        "LEARN",
        "LIST",
        "DEF",
        "FORWARD",
        "INVERSE",
        "LDS",
        "LINK",
        "PC",
        "PE",
        "PROGRAM",
        "LOCK",
        ",",
        "P",
        "M",
        "->",
        "D",
        "DP",
        "L",
        "TWB",
        "TWD",
        "TWR",
        "TWS",
        "MACROASCII",
        "MACROAUX",
        "MACROAUXREAD",
        "MACROAUXWRITE",
        "MACROMST",
        "MACROMSTASCII",
        "MACROMSTREAD",
        "MACROMSTWRITE",
        "MS",
        "MSR",
        "MSW",
        "MACROSTASCII",
        "MFLUSH",
        "MOVETIME",
        "NOFRAX",
        "NORMAL",
        "O",
        "OPEN",
        "BINARY",
        "PASSWORD",
        "PAUSE",
        "PC",
        "PE",
        "PMATCH",
        "PR",
        "Q",
        "R",
        "RH",
        "RESUME",
        "S",
        "SAVE",
        "SETPHASE",
        "SID",
        "SIZE",
        "STN",
        "TIME",
        "TODAY",
        "TYPE",
        "UNDEFINE",
        "UNLOCK",
        "UPDATE",
        "VERSION",
        "VID",
        "ADDRESS",
        "ADIS",
        "AND",
        "AROT",
        "BLOCKSTART",
        "BLOCKSTOP",
        "CALL",
        "CC0",
        "CC1",
        "CC2",
        "CC3",
        "CCR",
        "CIRCLE1",
        "CIRCLE2",
        "COMMAND",
        "COMMANDS",
        "COMMANDP",
        "COMMANDR",
        "COMMANDA",
        "DELAY",
        "DISPLAY",
        "DWELL",
        "ELSE",
        "ENDIF",
        "ENDWHILE",
        "F",
        "FRAX",
        "G",
        "GOSUB",
        "GOTO",
        "IDIS",
        "IF",
        "IROT",
        "LINEAR",
        "LOCK",
        "N",
        "NX",
        "NY",
        "NZ",
        "OR",
        "PRELUDE",
        "PSET",
        "PVT",
        "RAPID",
        "RETURN",
        "SENDS",
        "SENDP",
        "SENDR",
        "SENDA",
        "SETPHASE",
        "SPLINE1",
        "SPLINE2",
        "STOP",
        "T",
        "TA",
        "TINIT",
        "TM",
        "TR",
        "TS",
        "TSELECT",
        "TX",
        "TY",
        "TZ",
        "UNLOCK",
        "WAIT",
        "WHILE",
        "TRIGGER",
        "(",
        ")",
        "|",
        "..",
        "[",
        "]",
        "END",
        "READ",
        "E",
        "ACOS",
        "ASIN",
        "ATAN",
        "ATAN2",
        "COS",
        "EXP",
        "INT",
        "LN",
        "SIN",
        "SQRT",
        "TAN",
        "~"
    ]
    shortTokens = {
        "CHKS": "CHECKSUM",
        "CLR": "CLEAR",
        "CLS": "CLOSE",
        "DAT": "DATE",
        "DEF": "DEFINE",
        "GAT": "GATHER",
        "GOS": "GOSUB",
        "LOOK": "LOOKAHEAD",
        "ENDI": "ENDIF",
        "ROT": "ROTARY",
        "UBUF": "UBUFFER",
        "DEL": "DELETE",
        "TEMP": "TEMPS",
        "DIS": "DISABLE",
        "EAVER": "EAVERSION",
        "ENA": "ENABLE",
        "ENDG": "ENDGATHER",
        "TRIG": "TRIGGER",
        "HM": "HOME",
        "HMZ": "HOMEZ",
        "LIS": "LIST",
        "FWD": "FORWARD",
        "INV": "INVERSE",
        "PROG": "PROGRAM",
        "MX": "MACROAUX",
        "MXR": "MACROAUXREAD",
        "MXW": "MACROAUXWRITE",
        "MM": "MACROMST",
        "MACMA": "MACROMSTASCII",
        "MMR": "MACROMSTREAD",
        "MMW": "MACROMSTWRITE",
        "MACROSLV": "MS",
        "MACROSLVREAD": "MSR",
        "MACROSLVWRITE": "MSW",
        "MACSTA": "MACROSTASCII",
        "MVTM": "MOVETIME",
        "NRM": "NORMAL",
        "BIN": "BINARY",
        "PAU": "PAUSE",
        "RES": "RESUME",
        "UNDEF": "UNDEFINE",
        "VER": "VERSION",
        "ADR": "ADDRESS",
        "BSTART": "BLOCKSTART",
        "BSTOP": "BLOCKSTOP",
        "CIR1": "CIRCLE1",
        "CIR2": "CIRCLE2",
        "CMD": "COMMAND",
        "CMDS": "COMMANDS",
        "CMDP": "COMMANDP",
        "CMDR": "COMMANDR",
        "CMDA": "COMMANDA",
        "DLY": "DELAY",
        "DWE": "DWELL",
        "ENDW": "ENDWHILE",
        "LIN": "LINEAR",
        "RPD": "RAPID",
        "RET": "RETURN",
        "TSEL": "TSELECT",
        "MI": "I",
    }
    tokenPairs = {"END WHILE": "ENDWHILE", "END IF": "ENDIF", "END GATHER": "ENDGATHER"}

    def __init__(self, source, debug=False):
        self.tokens = []
        self.curToken = ""
        self.matchToken = None
        self.line = 0
        self.fileName = ""
        self.debug = debug
        hasDebugInfo = False
        lastToken = None
        # Process every line...
        for line in source:
            if not hasDebugInfo:
                self.line += 1
            if line.startswith(";#*"):
                # Debug information
                hasDebugInfo = True
                parts = line.split()
                self.fileName = parts[1]
                self.line = int(parts[2])
            else:
                # Strip comments from the ends of lines
                line = line.split(";", 1)[0].strip().upper()
                while len(line) > 0:
                    token = self.findToken(line)
                    t = PmacToken()
                    t.set(self.expandToken(token), self.fileName, self.line)
                    # Replace token pairs with the single corresponding token
                    if lastToken is not None:
                        pair = "%s %s" % (lastToken, t)
                        if pair in self.tokenPairs:
                            self.tokens[-1].set(
                                self.tokenPairs[pair], self.fileName, self.line
                            )
                            lastToken = None
                        else:
                            self.tokens.append(t)
                            lastToken = t
                    else:
                        self.tokens.append(t)
                        lastToken = t
                    line = line[len(token) :].lstrip()
                t = PmacToken()
                t.set("\n", self.fileName, self.line)
                self.tokens.append(t)

    def findToken(self, text):
        """Find the longest token at the start of the text."""
        bestToken = ""
        # Try for a (possibly real) number
        if text[0].isdigit():
            isNumber = True
            hasDot = False
            pos = 0
            curToken = ""
            while pos < len(text) and isNumber:
                ch = text[pos]
                if ch.isdigit():
                    curToken += ch
                elif not hasDot and ch == ".":
                    hasDot = True
                    curToken += ch
                else:
                    isNumber = False
                pos += 1
            if len(curToken) > 0 and curToken[-1] == ".":
                # Float cannot have a trailing dot
                curToken = curToken[:-1]
            bestToken = curToken
        # Try for a hexadecimal number (also catches the single $ token)
        elif text[0] == "$":
            pos = 1
            curToken = "$"
            isNumber = True
            while pos < len(text) and isNumber:
                ch = text[pos]
                if ch in "0123456789ABCDEF":
                    curToken += ch
                else:
                    isNumber = False
                pos += 1
            bestToken = curToken
        # Try for a literal string
        elif text[0] == '"':
            curToken = '"'
            pos = 1
            noTerminator = True
            while pos < len(text) and noTerminator:
                ch = text[pos]
                curToken += ch
                if ch == '"':
                    noTerminator = False
                pos += 1
            if noTerminator:
                raise LexerError(text, self.fileName, self.line)
            else:
                bestToken = curToken
        else:
            # Try the tokens in the normal list
            for t in PmacLexer.tokens:
                if len(t) > len(bestToken) and text.startswith(t):
                    bestToken = t
            # Try the tokens in the short dictionary
            for t, f in PmacLexer.shortTokens.items():
                if len(t) > len(bestToken) and text.startswith(t):
                    bestToken = t
        if len(bestToken) == 0:
            raise LexerError(text, self.fileName, self.line)
        # log.debug('{%s from %s}' % (bestToken, text))
        return bestToken

    def expandToken(self, token):
        """If the token is a short form, it is expanded to the full form."""
        result = token
        if token in PmacLexer.shortTokens:
            result = PmacLexer.shortTokens[token]
        return result

    def getToken(self, shouldBe=None, wantEol=False):
        """Returns the first token and removes it from the list."""
        result = None
        # Skip any newline tokens unless they are wanted
        while not wantEol and len(self.tokens) > 0 and self.tokens[0] == "\n":
            self.line += 1
            self.tokens[:1] = []
        # Get the head token
        if len(self.tokens) > 0:
            result = self.tokens[0]
            self.tokens[:1] = []
        # Is it the expected one
        if shouldBe is not None and not shouldBe == result:
            raise ParserError("Expected %s, got %s" % (shouldBe, result), result)
        return result

    def putToken(self, token):
        """Puts a token at the head of the list."""
        self.tokens[:0] = [token]
