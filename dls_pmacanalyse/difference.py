from typing import Any, Dict, IO, List, Optional


class Difference:
    def __init__(self, names: List[str]) -> None:
        self.differences: Dict[str,  List] = {}
        self.names = names
        self.size = len(names)

    def add_difference(self, item: str, values: List):
        if len(values) != self.size:
            raise ValueError(f"a difference list must have {self.size} values")
        self.differences[item] = values

    def make_fix_file(self, fixfile: Optional[IO[Any]]):
        pass

    def make_unfix_file(self, unfixfile: Optional[IO[Any]]):
        pass

