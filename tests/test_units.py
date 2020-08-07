from dls_pmacanalyse.pmacstate import PmacState
import pytest
from pathlib import Path

from dls_pmacanalyse.pmac import Pmac
from dls_pmacanalyse.pmacparser import PmacParser

plc1_short = """
IF(M4900=0) M4900=1 M4965=393216 DISPLC2..31 I5112=1000*8388608/I10 WHILE(I5112>0) ENDW ENAPLC6 I5112=100*8388608/I10 WHILE(I5112>0) ENDW WHILE(M5006=0) ENDW ENDI ADR&16 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&15 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&14 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&13 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&12 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&11 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&10 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&9 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&8 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&7 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&6 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&5 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&4 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&3 CMD" DEFINE LOOKAHEAD 50, 10 " ADR&2 CMD" DEFINE LOOKAHEAD 50, 10 " DISPLC2 DISPLC3 ENAPLC4 DISPLC5 ENAPLC7 DISPLC8 DISPLC9 DISPLC10 DISPLC11 DISPLC12 DISPLC13 DISPLC14 DISPLC15 DISPLC16 DISPLC17 DISPLC18 DISPLC19 DISPLC20 DISPLC21 DISPLC22 DISPLC23 DISPLC24 DISPLC25 DISPLC26 DISPLC27 DISPLC28 DISPLC29 DISPLC30 DISPLC31 DISPLC1 RET
"""

data_folder = Path(__file__).parent / 'data'

def test_plc1():
    plc1_pmc = data_folder / 'plc1.pmc'

    pmac_state1 = PmacState("one")
    pmac_state1.loadPmcFileWithPreprocess(plc1_pmc, None)
    lines1 = pmac_state1.vars['plc1'].valStr()

    pmac_state2 = PmacState("two")
    parser2 = PmacParser(source=[plc1_short], pmac=pmac_state2)
    plc1_2 = pmac_state2.getPlcProgram(1)
    parser2.parseProgram(plc1_2)
    lines2 = plc1_2.dump()

    for line in range(len(lines1)):
        assert lines1[line] == lines2[line], f"plc1 line {line} does not match"
