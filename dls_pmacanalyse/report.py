from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from pathlib import Path
from shutil import copy
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from dls_pmacanalyse.constants import Constants
from dls_pmacanalyse.pmac import Pmac
from dls_pmacanalyse.pmacprogram import ProgInfo
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
        # TODO not using autoescape so that we can show newlines in the
        # plc code in the comparison.htm files but this is a sledgehammer
        self.environment = Environment(loader=self.templateLoader, autoescape=False)

        if target_dir is None:
            target_dir = Path.cwd()
        self.root_dir = target_dir
        self.root_dir.mkdir(exist_ok=True)

        css = jinja_path / "analysis.css"
        copy(css, self.root_dir)

    def _write_html(self, html, path):
        log.info(f"writing {path}")
        with path.open(mode="w") as stream:
            stream.write(html)

    def _render(self, template_name: str, filename: str, **args):
        path = self.root_dir / filename
        template = self.environment.get_template(template_name)
        if "title" in args:
            args["title"] += f" {datetime.now().strftime('(%Y/%m/%d %H:%M:%S)')}"
        html = template.render(**args)

        log.info(f"writing {path}")
        with path.open(mode="w") as stream:
            stream.write(html)

    def _render_indexes(self, pmacs_index):
        self._render(
            template_name="index.htm.jinja",
            filename="index.htm",
            title="PMAC Analysis",
            pmacs=pmacs_index,
        )

        for pmac in pmacs_index:
            sub_indexes = ["ivariables.htm"]
            if pmac.macro_stations:
                sub_indexes.append("msivariables.htm")

            for name in sub_indexes:
                self._render(
                    f"{name}.jinja", filename=f"{pmac.name}_{name}", pmac=pmac,
                )

    def _render_variables(
        self,
        title: str,
        variables: List[VariableInfo],
        filename: str,
        with_comments: bool = True,
        with_node: bool = False,
        var_range: range = None,
    ):
        if var_range:
            variables = variables[var_range.start : var_range.stop]
        self._render(
            "variables.htm.jinja",
            filename=filename,
            title=title,
            variables=variables,
            with_comments=with_comments,
            with_node=with_node,
        )

    def _render_cs(self, pmac, cs_list):
        title = f"Coordinte Systems for {pmac} {datetime.now().ctime()}"
        cs_template = self.environment.get_template("coordsystems.htm.jinja")

        html = cs_template.render(title=title, pmac=pmac, cs_list=cs_list)

        path = self.root_dir / f"{pmac}_coordsystems.htm"
        self._write_html(html, path)

    def _render_programs(
        self,
        title: str,
        programs: List[ProgInfo],
        pmac_name: str,
        prog_type: str = "plc",
        variables: List[VariableInfo] = None,
    ):
        self._render(
            template_name="programs.htm.jinja",
            filename=f"{pmac_name}_{prog_type}s.htm",
            title=title,
            pmac=pmac_name,
            programs=programs,
            prog_type=prog_type,
            with_variables=variables is not None,
        )

        for program in programs:
            self._render(
                template_name="prog.htm.jinja",
                filename=f"{pmac_name}_{prog_type}_{program.num}.htm",
                title=f"PLC {program.num} for {pmac_name}",
                lines=program.code,
            )

            if variables is not None:
                self._render_variables(
                    filename=f"{pmac_name}_{prog_type}_{program.num}_p.htm",
                    title=f"P Variables for {pmac_name} PLC{program.num} ",
                    variables=variables,
                    with_comments=False,
                    var_range=program.p_range,
                )

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
                filename=f"{pmac.name}_ivars_glob.htm",
            )

            # motor i variables
            for motor in range(1, pmac.numAxes + 1):
                self._render_variables(
                    title=f"motor {motor} I Variables for {pmac.name}",
                    variables=pmac.hardwareState.get_motor_ivariables(motor),
                    filename=f"{pmac.name}_ivars_motor{motor}.htm",
                )

            # P variables
            p_vars = pmac.hardwareState.get_pvariables()
            self._render_variables(
                title=f"P Variables for {pmac.name}",
                variables=p_vars,
                filename=f"{pmac.name}_pvariables.htm",
                with_comments=False,
            )

            # M variable addresses
            self._render_variables(
                title=f"M Variable Mappings for {pmac.name}",
                variables=pmac.hardwareState.get_mvariables(),
                filename=f"{pmac.name}_mvariables.htm",
                with_comments=False,
            )

            # M variable values
            self._render_variables(
                title=f"M Variable Values for {pmac.name}",
                variables=pmac.hardwareState.get_mvariables(content=True),
                filename=f"{pmac.name}_mvariablevalues.htm",
                with_comments=False,
            )

            # Coordinate Systems
            cs_list = pmac.hardwareState.get_coord_systems()
            self._render_cs(pmac.name, cs_list)

            # Q Variables
            for cs in Constants.coord_sys_numbers:
                self._render_variables(
                    title=f"CS {cs} Q Variables for {pmac.name}",
                    variables=pmac.hardwareState.get_qvariables(cs),
                    filename=f"{pmac.name}_cs{cs}_q.htm",
                    with_comments=False,
                )

            if pmac.numMacroStationIcs is not None and pmac.numMacroStationIcs > 0:
                # global msi variables
                self._render_variables(
                    title=f"Global MSI Variables for {pmac.name}",
                    variables=pmac.hardwareState.get_global_msivariables(),
                    filename=f"{pmac.name}_msivars_glob.htm",
                    with_node=True,
                )

                # motor msi variables
                for motor in range(1, pmac.numAxes + 1):
                    self._render_variables(
                        title=f"motor {motor} MSI Variables for {pmac.name}",
                        variables=pmac.hardwareState.get_motor_msivariables(motor),
                        filename=f"{pmac.name}_msivars_motor{motor}.htm",
                    )

            # PLCs
            self._render_programs(
                title=f"PLCs for {pmac.name}",
                programs=pmac.hardwareState.get_plcs(),
                pmac_name=pmac.name,
                variables=p_vars,
            )

            # PROGs
            self._render_programs(
                title=f"Motion Programs for {pmac.name}",
                programs=pmac.hardwareState.get_progs(),
                pmac_name=pmac.name,
                prog_type="prog",
            )

            # Comparison
            self._render(
                template_name="compare.htm.jinja",
                filename=f"{pmac.name}_compare.htm",
                title=f"Comparison Results for {pmac.name}",
                differences=pmac.differences.get_infos(),
            )
