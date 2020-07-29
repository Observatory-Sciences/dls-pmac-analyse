from pathlib import Path
from typing import Dict, List, Optional

from .pmac import Pmac


class GlobalConfig:
    def __init__(
        self,
        test: bool,
        verbose: bool,
        backupDir: Path,
        writeAnalysis: bool,
        comments: bool,
        resultsDir: Path,
        onlyPmacs: List[str],
        global_nocompare: List[str],
        checkPositions: bool,
        debug: bool,
        fixfile: Optional[Path],
        unfixfile: Optional[Path],
        include: str
    ):
        self.pmacs: Dict[str, Pmac] = {}

        self.test = test
        self.verbose = verbose
        self.backupDir = backupDir
        self.writeAnalysis = writeAnalysis
        self.comments = comments
        self.resultsDir = resultsDir
        self.onlyPmacs = onlyPmacs
        self.global_nocompare = global_nocompare
        self.checkPositions = checkPositions
        self.debug = debug
        self.fixfile = fixfile
        self.unfixfile = unfixfile
        # todo make this a list of Path
        self.include = include
