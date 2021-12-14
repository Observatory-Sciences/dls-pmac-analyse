from dls_pmacanalyse.errors import ParserError


def isNumber(t):
    if len(str(t)) == 0:
        result = False
    elif t == "$":
        result = False
    elif str(t)[0] == "$":
        result = True
        for ch in str(t)[1:]:
            if ch not in "0123456789ABCDEF":
                result = False
    elif str(t)[0].isdigit():
        result = True
        for ch in str(t)[1:]:
            if ch not in "0123456789.":
                result = False
    else:
        result = False
    return result


def toNumber(t):
    if len(str(t)) == 0:
        result = 0
    elif str(t)[0] == "$":
        result = int(str(t)[1:], 16)
    elif str(t)[0].isdigit():
        if str(t).find(".") >= 0:
            result = float(str(t))
        else:
            result = int(str(t))
    else:
        result = 0
    return result


def isString(t):
    return len(t) >= 2 and t[0] == '"' and t[-1] == '"'


def stripStringQuotes(t):
    return t.strip('"')


def compareFloats(a, b, delta):
    return a >= (b - delta) and a <= (b + delta)


def tokenIsInt(token):
    """Returns true if the token is an integer."""
    if str(token)[0] == "$":
        result = len(str(token)) > 1
        for ch in str(token)[1:]:
            if ch not in "0123456789ABCDEFabcdef":
                result = False
    else:
        result = str(token).isdigit()
    return result


def tokenToInt(token):
    if not tokenIsInt(token):
        raise ParserError("Integer expected, got: %s" % token, token)
    if str(token)[0] == "$":
        result = int(str(token)[1:], 16)
    else:
        result = int(str(token))
    return result


def tokenIsFloat(token):
    """Returns true if the token is a floating point number."""
    result = True
    if not tokenIsInt(token):
        result = True
        for ch in str(token):
            if ch not in "0123456789.":
                result = False
    return result


def tokenToFloat(token):
    if tokenIsInt(token):
        result = tokenToInt(token)
    elif tokenIsFloat(token):
        result = float(str(token))
    else:
        raise ParserError("Float expected, got: %s" % token, token)
    return result


def numericSplit(a):
    """Splits a into two parts, a numeric suffix (or 0 if none) and an
    alphanumeric prefix (the remainder).  The parts are returned
    as a tuple."""
    splitPos = len(a)
    inSuffix = True
    while splitPos > 0 and inSuffix:
        if a[splitPos - 1].isdigit():
            splitPos -= 1
        else:
            inSuffix = False
    prefix = a[:splitPos]
    suffix = a[splitPos:]
    if len(suffix) > 0:
        suffix = int(suffix)
    else:
        suffix = 0
    return (prefix, suffix)


def numericSort(a, b):
    """Used by the sort algorithm to get numeric suffixes in the right order."""
    prefixa, suffixa = numericSplit(a)
    prefixb, suffixb = numericSplit(b)

    if prefixa < prefixb:
        result = -1
    elif prefixa > prefixb:
        result = 1
    elif suffixa < suffixb:
        result = -1
    elif suffixb < suffixa:
        result = 1
    else:
        result = 0
    return result
