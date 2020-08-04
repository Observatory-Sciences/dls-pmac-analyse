from dls_pmacanalyse.errors import ParserError
from dls_pmacanalyse.pmaclexer import PmacLexer
from dls_pmacanalyse.pmacvariables import PmacToken
from dls_pmacanalyse.utils import tokenIsFloat, tokenIsInt, tokenToFloat, tokenToInt


class PmacParser(object):
    def __init__(self, source, pmac, debug=False):
        self.lexer = PmacLexer(source, debug)
        self.pmac = pmac
        self.curCs = 1
        self.curMotor = 1
        self.debug = debug

    def tokens(self):
        return self.lexer.tokens

    def onLine(self):
        """Top level on-line command mode parser."""
        t = self.lexer.getToken()
        while t is not None:
            if t == "&":
                self.parseAmpersand()
            elif t == "%":
                self.parsePercent()
            elif t == "#":
                self.parseHash()
            elif t == "OPEN":
                self.parseOpen()
            elif t == "P":
                self.parseP()
            elif t == "Q":
                self.parseQ()
            elif t == "I":
                self.parseI()
            elif t == "M":
                self.parseM()
            elif t == "MS":
                self.parseMs()
            elif t == "UNDEFINE":
                self.parseUndefine()
            elif t == "CLOSE":
                pass  # Just ignore top level closes
            elif t == "ENDGATHER":
                pass  # Just ignore top level endgathers
            elif t == "ENABLE":
                self.parseEnable()
            elif t == "DELETE":
                self.parseDelete()
            elif t == "DISABLE":
                self.parseDisable()
            elif t == "W":
                self.parseWrite()
            else:
                raise ParserError("Unexpected token: %s" % t, t)
            t = self.lexer.getToken()

    def parseDisable(self):
        t = self.lexer.getToken()
        if t in ["PLC", "PLCC"]:
            t = self.lexer.getToken()
            if tokenIsInt(t):
                pass
            else:
                raise ParserError("Expected integer, got %s" % t, self.lexer.line)
        else:
            raise ParserError("Expected PLC or PLCC, got %s" % t, self.lexer.line)

    def parseWrite(self):
        _ = self.lexer.getToken()  # area
        _ = self.lexer.getToken()  # address
        comma = self.lexer.getToken()
        while comma == ",":
            _ = self.lexer.getToken()  # constant
            comma = self.lexer.getToken()
        self.lexer.putToken(comma)

    def parseDelete(self):
        t = self.lexer.getToken()
        if t == "ALL":
            t = self.lexer.getToken()
            if t != "TEMPS":
                self.lexer.putToken(t)
        elif t in [
            "BLCOMP",
            "CCUBUF",
            "BLCOMP",
            "COMP",
            "LOOKAHEAD",
            "GATHER",
            "PLCC",
            "ROTARY",
            "TBUF",
            "TCOMP",
            "TRACE",
        ]:
            pass
        else:
            raise ParserError("Expected DELETE type, got %s" % t, self.lexer.line)

    def parseEnable(self):
        t = self.lexer.getToken()
        if t not in ["PLC", "PLCC"]:
            raise ParserError("Expected PLC or PLCC, got: %s" % t, self.lexer.line)
        _ = tokenToInt(self.lexer.getToken())

    def parseUndefine(self):
        t = self.lexer.getToken()
        if t == "ALL":
            for cs in range(1, 17):
                for m in range(1, 33):
                    var = self.pmac.getCsAxisDef(cs, m)
                    var.clear()
                    var.add(PmacToken("0"))
        else:
            for m in range(1, 33):
                var = self.pmac.getCsAxisDef(self.curCs, m)
                var.clear()
                var.add(PmacToken("0"))

    def parseMs(self):
        t = None
        ms = self.lexer.getToken()
        if tokenIsInt(ms):
            ms = tokenToInt(ms)
            self.lexer.getToken(",")
            varType = self.lexer.getToken()
            if varType in ["I", "MI"]:
                n = tokenToInt(self.lexer.getToken())
                t = self.lexer.getToken()
                if t == "=":
                    val = tokenToFloat(self.lexer.getToken())
                    var = self.pmac.getMsIVariable(ms, n)
                    var.set(val)
                else:
                    self.lexer.putToken(t)
                    # Report variable value (do nothing)
            else:
                raise ParserError("Unsupported", t)
        else:
            raise ParserError("Unsupported", ms)

    def parseM(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == "=":
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getMVariable(n)
                    var.setValue(val)
                    n += increment
                    count -= 1
            elif t == "->":
                t = self.lexer.getToken()
                if t in [
                    "*",
                    "D",
                    "DP",
                    "F",
                    "L",
                    "TWB",
                    "TWD",
                    "TWR",
                    "TWS",
                    "X",
                    "Y",
                ]:
                    self.lexer.putToken(t)
                    self.parseMVariableAddress(start, count, increment)
                else:
                    self.lexer.putToken(t)
                    # Report M variable address (do nothing)
            else:
                self.lexer.putToken(t)
                # Report M variable values (do nothing)
        else:
            raise ParserError("Unexpected statement: M %s" % n, n)

    def parseMVariableAddress(self, start=0, count=0, increment=0, variable=None):
        type = self.lexer.getToken()
        address = 0
        offset = 0
        width = 1
        format = "U"
        if type == "*":
            pass
        elif type in ["D", "DP", "F", "L"]:
            t = self.lexer.getToken()
            if t == ":":
                t = self.lexer.getToken()
            address = tokenToInt(t)
        elif type in ["TWB", "TWD", "TWR", "TWS"]:
            t = self.lexer.getToken()
            if t == ":":
                t = self.lexer.getToken()
            address = tokenToInt(t)
        elif type in ["X", "Y"]:
            t = self.lexer.getToken()
            if t == ":":
                t = self.lexer.getToken()
            address = tokenToInt(t)
            self.lexer.getToken(",")
            offset = tokenToInt(self.lexer.getToken())
            if offset == 24:
                offset = 0
                width = 24
                t = self.lexer.getToken()
                if t == ",":
                    format = self.lexer.getToken()
                else:
                    self.lexer.putToken(t)
            else:
                t = self.lexer.getToken()
                if t == ",":
                    width = tokenToInt(self.lexer.getToken())
                    t = self.lexer.getToken()
                    if t == ",":
                        format = self.lexer.getToken()
                    else:
                        self.lexer.putToken(t)
                else:
                    self.lexer.putToken(t)
            if format not in ["U", "S"]:
                raise ParserError("Expected format, got %s" % format, t)
        if variable is not None:
            variable.set(type, address, offset, width, format)
        else:
            n = start
            while count > 0:
                var = self.pmac.getMVariable(n)
                var.set(type, address, offset, width, format)
                n += increment
                count -= 1

    def parseVarSpec(self):
        t = self.lexer.getToken()
        varType = ""
        nodeList = []
        if t in ["I", "P", "M"]:
            varType = t.lower()
        elif t == "MS":
            varType = t.lower()
            t = self.lexer.getToken()
            if t == "[":
                nodeList.append(tokenToInt(self.lexer.getToken()))
                t = self.lexer.getToken()
                if t == "..":
                    last = tokenToInt(self.lexer.getToken())
                    nodeList += range(nodeList[0] + 1, last + 1)
                else:
                    while t == ",":
                        nodeList.append(tokenToInt(self.lexer.getToken()))
                        t = self.lexer.getToken()
                    self.lexer.putToken(t)
                self.lexer.getToken("]")
            else:
                nodeList.append(tokenToInt(t))
            self.lexer.getToken(",")
            self.lexer.getToken("I")
        elif t == "&":
            varType = t.lower()
            t = self.lexer.getToken()
            if t == "[":
                nodeList.append(tokenToInt(self.lexer.getToken()))
                t = self.lexer.getToken()
                if t == "..":
                    last = tokenToInt(self.lexer.getToken())
                    nodeList += range(nodeList[0] + 1, last + 1)
                while t == ",":
                    nodeList.append(tokenToInt(self.lexer.getToken()))
                    t = self.lexer.getToken()
                    self.lexer.putToken(t)
                self.lexer.getToken("]")
            else:
                nodeList.append(tokenToInt(t))
            self.lexer.getToken("Q")
        else:
            raise ParserError("Expected variable type, got: %s" % t, t)
        start = tokenToInt(self.lexer.getToken())
        t = self.lexer.getToken()
        if t == "..":
            end = tokenToInt(self.lexer.getToken())
            if end <= start:
                raise ParserError("End of range lower than start", t)
            count = end + 1 - start
            increment = 1
        elif t == ",":
            count = tokenToInt(self.lexer.getToken())
            self.lexer.getToken(",")
            increment = tokenToInt(self.lexer.getToken())
        else:
            count = 1
            increment = 1
        return (varType, nodeList, start, count, increment)

    def parseI(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == "=":
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getIVariable(n)
                    var.set(val)
                    n += increment
                    count -= 1
            else:
                self.lexer.putToken(t)
                # Report I variable values (do nothing)
        elif n == "(":
            n = self.parseExpression()
            t = self.lexer.getToken(")")
            t = self.lexer.getToken()
            if t == "=":
                val = self.parseExpression()
                var = self.pmac.getIVariable(n)
                var.set(val)
            else:
                self.lexer.putToken(t)
                # Report I variable values (do nothing)
        else:
            raise ParserError("Unexpected statement: I %s" % n, n)

    def parseP(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == "=":
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getPVariable(n)
                    var.set(val)
                    n += increment
                    count -= 1
            else:
                self.lexer.putToken(t)
                # Report P variable values (do nothing)
        elif n == "(":
            n = self.parseExpression()
            t = self.lexer.getToken(")")
            t = self.lexer.getToken()
            if t == "=":
                val = self.parseExpression()
                var = self.pmac.getPVariable(n)
                var.set(val)
            else:
                self.lexer.putToken(t)
                # Report P variable values (do nothing)
        else:
            self.lexer.putToken(n)
            # Report motor position (do nothing)

    def parseQ(self):
        n = self.lexer.getToken()
        if tokenIsInt(n):
            (start, count, increment) = self.parseRange(tokenToInt(n))
            t = self.lexer.getToken()
            if t == "=":
                val = self.parseExpression()
                n = start
                while count > 0:
                    var = self.pmac.getQVariable(self.curCs, n)
                    var.set(val)
                    n += increment
                    count -= 1
            else:
                self.lexer.putToken(t)
                # Report Q variable values (do nothing)
        elif n == "(":
            n = self.parseExpression()
            t = self.lexer.getToken(")")
            t = self.lexer.getToken()
            if t == "=":
                val = self.parseExpression()
                var = self.pmac.getQVariable(self.curCs, n)
                var.set(val)
            else:
                self.lexer.putToken(t)
                # Report Q variable values (do nothing)
        else:
            self.lexer.putToken(n)
            # Quit program (do nothing)

    # def parseExpression(self):
    #    '''Returns the result of the expression.'''
    #    # Currently only supports a constant prefixed by an optional minus sign
    #    negative = False
    #    t = self.lexer.getToken()
    #    if t == '-':
    #        negative = True
    #        t = self.lexer.getToken()
    #    if not tokenIsFloat(t):
    #        raise ParserError('Unsupported', t)
    #    result = tokenToFloat(t)
    #    if negative:
    #        result = -result
    #    return result
    def parseExpression(self):
        """Returns the result of the expression."""
        # Currently supports syntax of the form:
        #    <expression> ::= <e1> { <sumop> <e1> }
        #    <e1> ::= <e2> { <multop> <e2> }
        #    <e2> ::= [ <monop> ] <e3>
        #    <e3> ::= '(' <expression> ')' | <constant> | 'P'<integer> |
        #             'Q'<integer> | 'I'<integer> | 'M' <integer>
        #    <sumop> ::= '+' | '-' | '|' | '^'
        #    <multop> ::= '*' | '/' | '%' | '&'
        #    <monop> ::= '+' | '-'
        result = self.parseE1()
        going = True
        while going:
            t = self.lexer.getToken()
            if t == "+":
                result = result + self.parseE1()
            elif t == "-":
                result = result - self.parseE1()
            elif t == "|":
                result = float(int(result) | int(self.parseE1()))
            elif t == "^":
                result = float(int(result) ^ int(self.parseE1()))
            else:
                self.lexer.putToken(t)
                going = False
        return result

    def parseE1(self):
        """Returns the result of a sub-expression containing multiplicative operands."""
        result = self.parseE2()
        going = True
        while going:
            t = self.lexer.getToken(wantEol=True)
            if t == "*":
                result = result * self.parseE2()
            elif t == "/":
                result = result / self.parseE2()
            elif t == "%":
                result = result % self.parseE2()
            elif t == "&":
                result = float(int(result) & int(self.parseE2()))
            elif t == '\n':
                going = False
            else:
                self.lexer.putToken(t)
                going = False
        return result

    def parseE2(self):
        """Returns the result of a sub-expression containing monadic operands."""
        monop = self.lexer.getToken()
        if monop not in ["+", "-"]:
            self.lexer.putToken(monop)
            monop = "+"
        result = self.parseE3()
        if monop == "-":
            result = -result
        return result

    def parseE3(self):
        """Returns the result of a sub-expression that is an I,P,Q or M variable or
           a constant or a parenthesised expression."""
        t = self.lexer.getToken()
        if t == "(":
            result = self.parseExpression()
            t = self.lexer.getToken(")")
        elif t == "I":
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionIValue(tokenToInt(t))
        elif t == "Q":
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionQValue(self.curCs, tokenToInt(t))
        elif t == "P":
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionPValue(tokenToInt(t))
        elif t == "M":
            t = self.lexer.getToken()
            result = self.pmac.getInlineExpressionMValue(tokenToInt(t))
        else:
            result = tokenToFloat(t)
        return result

    def parseRange(self, start):
        """Returns the range as (start, count, increment)."""
        t = self.lexer.getToken()
        if t == "..":
            last = tokenToInt(self.lexer.getToken())
            if last <= start:
                raise ParserError("End of range not greater than start", t)
            count = last - start + 1
            increment = 1
        elif t == ",":
            count = tokenToInt(self.lexer.getToken())
            self.lexer.getToken(",")
            increment = tokenToInt(self.lexer.getToken())
        else:
            self.lexer.putToken(t)
            count = 1
            increment = 1
        return (start, count, increment)

    def parseOpen(self):
        t = self.lexer.getToken()
        if t == "PROGRAM":
            n = self.lexer.getToken()
            if tokenIsInt(n):
                prog = self.pmac.getMotionProgram(tokenToInt(n))
                self.parseProgram(prog)
            else:
                raise ParserError("Expected integer, got: %s" % t, t)
        elif t == "PLC":
            n = self.lexer.getToken()
            if tokenIsInt(n):
                prog = self.pmac.getPlcProgram(tokenToInt(n))
                self.parseProgram(prog)
            else:
                raise ParserError("Expected integer, got: %s" % t, t)
        elif t == "FORWARD":
            prog = self.pmac.getForwardKinematicProgram(self.curCs)
            self.parseProgram(prog)
        elif t == "INVERSE":
            prog = self.pmac.getInverseKinematicProgram(self.curCs)
            self.parseProgram(prog)
        else:
            raise ParserError("Unknown buffer type: %s" % t, t)

    def parseProgram(self, prog):
        last = None
        t = self.lexer.getToken(wantEol=True)
        while t is not None and t != "CLOSE":
            if t == "CLEAR":
                prog.clear()
            elif t == "FRAX":
                prog.add(t)
                t = self.lexer.getToken(wantEol=True)
                if t == "(":
                    axes = {
                        "A": False,
                        "B": False,
                        "C": False,
                        "X": False,
                        "Y": False,
                        "Z": False,
                        "U": False,
                        "V": False,
                        "W": False,
                    }
                    t = self.lexer.getToken(wantEol=True)
                    while t in ["A", "B", "C", "X", "Y", "Z", "U", "V", "W"]:
                        axes[str(t)] = True
                        t = self.lexer.getToken()
                        if t == ",":
                            t = self.lexer.getToken()
                    self.lexer.putToken(t)
                    self.lexer.getToken(")")
                    allTrue = True
                    for x, t in axes.items():
                        if not t:
                            allTrue = False
                    if not allTrue:
                        prog.add(PmacToken("("))
                        first = True
                        for x in ["A", "B", "C", "U", "V", "W", "X", "Y", "Z"]:
                            if axes[x]:
                                if not first:
                                    prog.add(PmacToken(","))
                                first = False
                                prog.add(PmacToken(x))
                        prog.add(PmacToken(")"))
                else:
                    self.lexer.putToken(t)
            elif t == "&":
                # Drop any '&' followed by COMMAND
                n = self.lexer.getToken(wantEol=True)
                if n != "COMMAND":
                    prog.add(t)
                self.lexer.putToken(n)
            else:
                prog.add(t)
            if not t == "\n":
                last = t
            t = self.lexer.getToken(wantEol=True)
        if last is not None and last != "RETURN":
            prog.add(PmacToken("RETURN"))

    def parseHash(self):
        m = self.lexer.getToken()
        if tokenIsInt(m):
            a = self.lexer.getToken()
            if a == "->":
                t = self.lexer.getToken()
                if t == "0":
                    # Clear axis definition
                    var = self.pmac.getCsAxisDef(self.curCs, tokenToInt(m))
                    var.clear()
                    var.add(t)
                elif t == "I":
                    # Inverse kinematic axis definition
                    var = self.pmac.getCsAxisDef(self.curCs, tokenToInt(m))
                    var.clear()
                    var.add(t)
                elif tokenIsFloat(t) or t in [
                    "-",
                    "X",
                    "Y",
                    "Z",
                    "U",
                    "V",
                    "W",
                    "A",
                    "B",
                    "C",
                ]:
                    # Axis definition
                    var = self.pmac.getCsAxisDef(self.curCs, tokenToInt(m))
                    var.clear()
                    self.lexer.putToken(t)
                    self.parseAxisDefinition(var)
                else:
                    self.lexer.putToken(t)
                    # Report axis definition (do nothing)
            else:
                self.lexer.putToken(a)
                # Set current motor
                self.curMotor = tokenToInt(m)
        else:
            self.lexer.putToken(m)
            # Report current motor (do nothing)

    def parseAmpersand(self):
        t = self.lexer.getToken()
        if tokenIsInt(t):
            # Set current coordinate system
            self.curCs = tokenToInt(t)
        else:
            self.lexer.putToken(t)
            # Report coordinate system (do nothing)

    def parsePercent(self):
        t = self.lexer.getToken()
        if tokenIsFloat(t):
            # Set the feedrate override
            var = self.pmac.getFeedrateOverride(self.curCs)
            var.set(tokenToFloat(t))
        else:
            self.lexer.putToken(t)
            # Report feedrate override (do nothing)

    def parseAxisDefinition(self, var):
        first = True
        going = True
        while going:
            t = self.lexer.getToken()
            if t == "+":
                if not first:
                    var.add(t)
                t = self.lexer.getToken()
            elif t == "-":
                var.add(t)
                t = self.lexer.getToken()
            if tokenIsFloat(t):
                var.add(t)
                t = self.lexer.getToken()
            if t in ["X", "Y", "Z", "U", "V", "W", "A", "B", "C"]:
                var.add(t)
            elif first:
                raise ParserError("Expected axis definition, got: %s" % t, t)
            else:
                self.lexer.putToken(t)
                going = False
            first = False
