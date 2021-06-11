from os import chdir
from pathlib import Path

from click.testing import CliRunner

from dls_pmacanalyse.dls_pmacanalyse import main

this_dir = Path(__file__).parent


def test_brick_6():
    bl08j = this_dir / "BL08J"
    chdir(bl08j)

    runner = CliRunner()
    result = runner.invoke(main, ["--only", "BL08J-MO-STEP-06"])

    assert "Hardware to reference mismatch detected" in result.output
