"""CORE-MAXWIRE 11-09: every core kit gets the repeater-pitch hook (grt_maxwire.tcl via grt_pre.tcl): 80 um on a
core whose top routing layer is M7 or lower, 450 um where M8/M9 hops exist; a kit value wins; empty = off."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _cfg(tmp_path):
    import core_flow
    return core_flow.apply(tmp_path, core_flow.binding(250.0, 202.5), "t_kit", rc_cal=False)


def test_core_kit_gets_maxwire_hook(tmp_path):
    import core_flow
    cfg = _cfg(tmp_path)
    assert core_flow.CORE_MAXWIRE_LINE in cfg
    assert (tmp_path / "grt_maxwire.tcl").read_text() == (HERE / "grt_maxwire.tcl").read_text()
    # grt_pre_core.tcl sources grt_pre.tcl, which sources grt_maxwire.tcl when OT_MAXWIRE_UM is non-empty
    assert "source /work/grt_pre.tcl" in (tmp_path / "grt_pre_core.tcl").read_text()
    assert "grt_maxwire.tcl" in (HERE / "grt_pre.tcl").read_text()


def _make_value(tmp_path, cfg_lines):
    mk = tmp_path / "Makefile"
    mk.write_text("\n".join(cfg_lines) + "\nall:\n\t@echo \"V=[$$OT_MAXWIRE_UM]\"\n")
    out = subprocess.run(["make", "-s", "-f", str(mk)], capture_output=True, text=True, check=True).stdout
    return out.strip()


@pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")
def test_maxwire_value_by_top_layer_and_override(tmp_path):
    import core_flow
    line = core_flow.CORE_MAXWIRE_LINE
    assert _make_value(tmp_path, [line]) == "V=[80]"                                   # platform default top (M7)
    assert _make_value(tmp_path, [line, "export MAX_ROUTING_LAYER = M7"]) == "V=[80]"
    assert _make_value(tmp_path, [line, "export MAX_ROUTING_LAYER = M9"]) == "V=[450]"  # set after the line: still seen
    assert _make_value(tmp_path, ["export MAX_ROUTING_LAYER = M8", line]) == "V=[450]"
    assert _make_value(tmp_path, ["export OT_MAXWIRE_UM = 150", line]) == "V=[150]"    # kit value wins
    assert _make_value(tmp_path, ["export OT_MAXWIRE_UM =", line]) == "V=[]"           # explicit off
