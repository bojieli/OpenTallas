"""CTS-DPL-DIAMOND-1123 b: tools/orfs_dpl_diamond.py writes the same Tcl lines as grt183_make.sh, once, before the erase."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import orfs_dpl_diamond as D  # noqa: E402

WRAP = ROOT / "physical/common_flow/grt183_make.sh"
CTS = "utl::set_metrics_stage \"cts__{}\"\nerase_non_stage_variables cts\nload_design 3_place.odb 3_place.sdc\n"
GRT = "utl::set_metrics_stage \"globalroute__{}\"\nerase_non_stage_variables grt\nlog_cmd detailed_placement\n"


def scripts(tmp):
    s = tmp / "scripts"
    s.mkdir()
    (s / "cts.tcl").write_text(CTS)
    (s / "global_route.tcl").write_text(GRT)
    return s


def wrapper_line(tag):
    g = WRAP.read_text()
    i = g.index("<<'" + tag + "'\n")
    body = g[i:g.index("\n" + tag + "\n", i)]
    a = body.index("line = (")
    ns = {}
    exec("line = " + body[a + len("line = "):body.index("\ns = p.read_text()", a)], ns)
    return ns["line"]


def test_same_lines_as_grt183_make_and_idempotent(tmp_path):
    assert D.CTS_LINE == wrapper_line("OT_CTS_DPL_PY") and "OT_CTS_DPL_ARGS" in D.CTS_LINE
    assert D.GRT_LINE == wrapper_line("OT_GRT_DPL_PY") and "OT_GRT_DPL_ARGS" in D.GRT_LINE
    s = scripts(tmp_path)
    assert D.patch(s) == {"cts.tcl": "patched", "global_route.tcl": "patched"}
    once = (s / "cts.tcl").read_text(), (s / "global_route.tcl").read_text()
    assert D.patch(s) == {"cts.tcl": "already patched", "global_route.tcl": "already patched"}
    assert once == ((s / "cts.tcl").read_text(), (s / "global_route.tcl").read_text())
    for n, stage, line in (("cts.tcl", "cts", D.CTS_LINE), ("global_route.tcl", "grt", D.GRT_LINE)):
        t = (s / n).read_text()
        assert t.index(line) < t.index("erase_non_stage_variables " + stage)


def test_opt_out_env_and_config(tmp_path, monkeypatch):
    s = scripts(tmp_path)
    cfg = tmp_path / "config.mk"
    cfg.write_text("export OT_GRT_DPL_ARGS = 0\n")
    monkeypatch.setenv("OT_CTS_DPL_ARGS", "0")
    assert D.patch(s, cfg) == {"cts.tcl": "opted out", "global_route.tcl": "opted out"}
    assert (s / "cts.tcl").read_text() == CTS and (s / "global_route.tcl").read_text() == GRT


def test_runner_patches_beside_hold_mm():
    src = (ROOT / "tools/run_abi3_physical.py").read_text()
    n_hold = src.count("python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts")
    assert n_hold >= 2
    assert src.count("python3 /src/tools/orfs_dpl_diamond.py /OpenROAD-flow-scripts/flow/scripts /work/config.mk") == n_hold
