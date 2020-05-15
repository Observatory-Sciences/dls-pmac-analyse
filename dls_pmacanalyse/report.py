from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from pathlib import Path
from shutil import copy
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from dls_pmacanalyse.pmac import Pmac
from dls_pmacanalyse.pmacstate import VariableInfo

log = getLogger(__name__)


@dataclass
class PmacIndexInfo:
    name: str
    macro_stations: bool
    motors: int
    results: str


class Report:
    def __init__(self, target_dir: Optional[Path]) -> None:
        this_path = Path(__file__).parent
        jinja_path = this_path.parent / "jinja"
        self.templateLoader = FileSystemLoader(searchpath=jinja_path)
        self.environment = Environment(loader=self.templateLoader, autoescape=True)

        if target_dir is None:
            target_dir = Path.cwd()
        self.root_dir = target_dir / "pmacAnalysis"
        self.root_dir.mkdir(exist_ok=True)

        css = jinja_path / "analysis.css"
        copy(css, self.root_dir)

    def _render_indexes(self, pmacs_index):
        template = self.environment.get_template("index.htm.jinja")
        title = f"PMAC Analysis {datetime.now().ctime()}"
        html = template.render(title=title, pmacs=pmacs_index)
        path = self.root_dir / "index.htm"
        log.info(f"writing {path}")

        with path.open(mode="w") as stream:
            stream.write(html)

        for pmac in pmacs_index:
            sub_indexes = ["ivariables.htm"]
            if pmac.macro_stations:
                sub_indexes.append("msivariables.htm")

            for name in sub_indexes:
                template = self.environment.get_template(f"{name}.jinja")
                html = template.render(pmac=pmac)
                path = self.root_dir / f"{pmac.name}_{name}"
                log.info(f"writing {path}")

                with path.open(mode="w") as stream:
                    stream.write(html)

    def _render_variables(
        self,
        title: str,
        variables: List[VariableInfo],
        path: Path,
        with_comments: bool = True,
    ):
        vars_template = self.environment.get_template("variables.htm.jinja")
        title += f" {datetime.now().ctime()}"
        html = vars_template.render(
            title=title, variables=variables, with_comments=with_comments
        )

        log.info(f"writing {path}")
        with path.open(mode="w") as stream:
            stream.write(html)

    def _render_cs(self, pmac, cs_list):
        title = f"Coordinte Systems for {pmac} {datetime.now().ctime()}"
        cs_template = self.environment.get_template("coordsystems.htm.jinja")
        html = cs_template.render(
            title=title, pmac=pmac, cs_list=cs_list
        )
        path = self.root_dir / f"{pmac}_coordsystems.htm"
        log.info(f"writing {path}")
        with path.open(mode="w") as stream:
            stream.write(html)

    def pmacs_to_html(self, pmacs: Dict[str, Pmac]):
        index: List[PmacIndexInfo] = [
            PmacIndexInfo(
                name=name,
                macro_stations=pmac.numMacroStationIcs is not None
                and pmac.numMacroStationIcs > 0,
                motors=pmac.numAxes,
                results="todo",
            )
            for name, pmac in pmacs.items()
        ]
        self._render_indexes(index)

        for pmac in pmacs.values():
            # global i variables
            self._render_variables(
                title=f"Global I Variables for {pmac.name}",
                variables=pmac.hardwareState.get_global_ivariables(),
                path=self.root_dir / f"{pmac.name}_ivars_glob.htm",
            )

            # motor i variables
            for motor in range(1, pmac.numAxes + 1):
                self._render_variables(
                    title=f"motor {motor} I Variables for {pmac.name}",
                    variables=pmac.hardwareState.get_motor_ivariables(motor),
                    path=self.root_dir / f"{pmac.name}_ivars_motor{motor}.htm",
                )

            # P variables
            self._render_variables(
                title=f"P Variables for {pmac.name}",
                variables=pmac.hardwareState.get_pvariables(),
                path=self.root_dir / f"{pmac.name}_pvariables.htm",
                with_comments=False,
            )

            # M variable addresses
            self._render_variables(
                title=f"M Variable Mappings for {pmac.name}",
                variables=pmac.hardwareState.get_mvariables(),
                path=self.root_dir / f"{pmac.name}_mvariables.htm",
                with_comments=False,
            )

            # M variable values
            self._render_variables(
                title=f"M Variable Values for {pmac.name}",
                variables=pmac.hardwareState.get_mvariables(content=True),
                path=self.root_dir / f"{pmac.name}_mvariablevalues.htm",
                with_comments=False,
            )

            # Coordinate Systems
            cs_list = pmac.hardwareState.get_coord_systems()
            self._render_cs(pmac.name, cs_list)

            # Q Variables
            for cs in range(1, 17):
                self._render_variables(
                    title=f"CS {cs} Q Variables for {pmac.name}",
                    variables=pmac.hardwareState.get_qvariables(cs),
                    path=self.root_dir / f"{pmac.name}_cs{cs}_q.htm",
                    with_comments=False
                )

            if pmac.numMacroStationIcs is not None and pmac.numMacroStationIcs > 0:
                # global msi variables
                self._render_variables(
                    title=f"Global MSI Variables for {pmac.name}",
                    variables=pmac.hardwareState.get_global_msivariables(),
                    path=self.root_dir / f"{pmac.name}_msivars_glob.htm",
                )

                # motor msi variables
                for motor in range(1, pmac.numAxes + 1):
                    self._render_variables(
                        title=f"motor {motor} MSI Variables for {pmac.name}",
                        variables=pmac.hardwareState.get_motor_msivariables(motor),
                        path=self.root_dir / f"{pmac.name}_msivars_motor{motor}.htm",
                    )
