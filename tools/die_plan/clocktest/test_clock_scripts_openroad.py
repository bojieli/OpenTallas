"""KIT-OPS-6 lever 7 (FABLE-METHOD): known-answer regression tests for the clock Tcl scripts, run in OpenROAD (docker openroad/orfs:asap7lock
or `openroad` on PATH; skipped where neither exists, run by ot-run from the merge-queue suite with OT_CLOCKTEST_OTRUN=1).
    python3 -m pytest -q tools/die_plan/clocktest/test_clock_scripts_openroad.py
subtree_balance.tcl STB-EDGE-1: ONE clock port -> BUF -> {2 flops, INV -> 1 flop}.  Every sink must be measured from the same source edge, so
the tree spread is a few ps.  The pre-STB-EDGE-1 script read arrival_max_rise on the inverted sink and measured T/2 + a few ps (424 ps here)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RUN = HERE / "run_openroad.sh"
HAVE = shutil.which("openroad") is not None or shutil.which("docker") is not None
needs_or = pytest.mark.skipif(not HAVE, reason="no openroad / docker")


def run(script, *env):
    r = subprocess.run(["bash", str(RUN), script, *env], capture_output=True, text=True, timeout=1500)
    if r.returncode == 77:
        pytest.skip("no openroad")
    return r.stdout + r.stderr


@needs_or
def test_stb_inverted_sink_is_measured_on_the_same_source_edge():
    out = run("stb_known.tcl")
    m = re.search(r"OT_STB before clk \(placement RC\): (\d+) tree nodes, sinks (\d+) .*\(spread (\d+),", out)
    assert m, out[-800:]
    nodes, sinks, spread = map(int, m.groups())
    assert (nodes, sinks) == (2, 3)
    assert spread <= 20, f"spread {spread} ps: the inverted sink is read on the wrong edge (T/2 artefact ~ 416 ps)"
    assert "OT_KNOWN_DONE" in out


def test_harness_files_exist():
    for f in ("stb_known.tcl", "stb_known.v", "run_openroad.sh"):
        assert (HERE / f).is_file()
    assert "source /tools/subtree_balance.tcl" in (HERE / "stb_known.tcl").read_text()
