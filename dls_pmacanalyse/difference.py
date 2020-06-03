from dataclasses import dataclass
from enum import Enum
from typing import IO, Any, Dict, List, Optional, Tuple, Union, cast

from dls_pmacanalyse.pmacvariables import PmacVariable


@dataclass
class DifferenceInfo:
    name: str
    reason: str
    reference_value: List[str]
    hardware_value: List[str]


class Reason(Enum):
    Mismatch = "Mismatch"
    NotRunning = "Not Running"
    Running = "Is Running"
    Missing = "Missing"


class Differences:
    def __init__(self, name1: str, name2: str) -> None:
        self.differences: Dict[
            str, Tuple[Optional[PmacVariable], Optional[PmacVariable], Reason]
        ] = {}
        self.plc_run_differences: Dict[int, Tuple[bool, bool]] = {}
        self.name1 = name1
        self.name2 = name2

    def __len__(self) -> int:
        return len(self.differences) + len(self.plc_run_differences)

    def add(
        self,
        item: str,
        value1: Optional[PmacVariable],
        value2: Optional[PmacVariable],
        reason: Reason = Reason.Mismatch,
    ):
        self.differences[item] = (value1, value2, reason)

    def add_plc(self, number: int, running1: bool, running2: bool):
        self.plc_run_differences[number] = (running1, running2)

    def make_fix_file(self, fixfile: Optional[IO[Any]]):
        pass

    def make_unfix_file(self, unfixfile: Optional[IO[Any]]):
        pass

    @staticmethod
    def listify(item: Union[str, List[str]]) -> List[str]:
        if type(item) is not list:
            result = [cast(str, item)]
        else:
            result = cast(List[str], item)
        return result

    def get_infos(self):
        result = [
            DifferenceInfo(
                name=hardware.addr() if hardware else reference.addr(),
                reason=reason.value,
                reference_value=self.listify(reference.valStr()) if reference else [],
                hardware_value=self.listify(hardware.valStr()) if hardware else [],
            )
            for (hardware, reference, reason) in self.differences.values()
        ]
        return result

    # TODO might want to use these

    # def clever_comment_extraction(self, texta: str):
    #     commentargs = {}
    #     if texta.startswith("i") and not texta.startswith("inv"):
    #         i = int(texta[1:])
    #         if i in range(100):
    #             desc = PmacState.globalIVariableDescriptions[i]
    #             commentargs["comment"] = desc
    #         elif i in range(3300):
    #             desc = PmacState.motorIVariableDescriptions[i % 100]
    #             commentargs["comment"] = desc
    #         elif i in range(7000, 7350):
    #             desc = PmacState.motorI7000VariableDescriptions[i % 10]
    #             commentargs["comment"] = desc
    #         else:
    #             desc = "No description available"
    """
    enabling and disabling PLCs

            if plc is not None:
                plc.setShouldBeRunning()
                log.debug(
                    "PLC%s, isRunning=%s, shouldBeRunning=%s",
                    n,
                    plc.isRunning,
                    plc.shouldBeRunning,
                )
                if plc.shouldBeRunning and not plc.isRunning:
                    difference.add_plc(n, False, True)
                    result = False
                    if fixfile is not None:
                        fixfile.write("enable plc %s\n" % n)
                    if unfixfile is not None:
                        unfixfile.write("disable plc %s\n" % n)
                elif not plc.shouldBeRunning and plc.isRunning:
                    difference.add_plc(n, True, False)
                    result = False
                    if fixfile is not None:
                        fixfile.write("disable plc %s\n" % n)
                    if unfixfile is not None:
                        unfixfile.write("enable plc %s\n" % n)

    """
