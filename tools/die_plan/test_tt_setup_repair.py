"""FABLE-PD-HEAD-1650 finding 1 (COORD r190): TT setup repair step between CTS and GRT, opt-in (gen env OT_TT_SETUP_REPAIR=1)."""
import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
from test_g2 import PAIR  # noqa: E402

TCLSH = shutil.which("tclsh")


def _kit(tmp, monkeypatch, on):
    monkeypatch.delenv("OT_TT_SETUP_REPAIR", raising=False)
    if on:
        monkeypatch.setenv("OT_TT_SETUP_REPAIR", "1")
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp), [])
    return Path(tmp) / "fa"


def test_default_kit_has_no_tt_step_files(tmp_path, monkeypatch):
    k = _kit(tmp_path, monkeypatch, False)
    assert not (k / "tt_setup_repair.tcl").exists() and not (k / "tt_setup_repair.on").exists()


def test_flag_writes_the_step_files(tmp_path, monkeypatch):
    k = _kit(tmp_path, monkeypatch, True)
    assert (k / "tt_setup_repair.on").read_text().strip() == "1"
    assert (k / "tt_setup_repair.tcl").read_text() == (HERE / "tt_setup_repair.tcl").read_text()


def test_run_kit_step_is_flag_gated_fail_open_and_between_cts_and_grt():
    t = gen_phys.RUN_KIT
    i = t.index("tt_setup_repair.on")
    assert t.index("$M cts SKIP_CTS_REPAIR_TIMING=1") < i < t.index("hold_gate.tcl")
    assert "OT_TT_SETUP_REPAIR FALLBACK" in t and "4_cts.odb unchanged" in t         # failure keeps the CTS result


def test_tcl_step_repairs_setup_only_in_the_tt_scene():
    t = (HERE / "tt_setup_repair.tcl").read_text()
    assert "print-TC_LIB_FILES" in t and "repair_timing -setup " in t and "-hold" not in t.replace("hold repair", "")
    assert "SETUP_SLACK_MARGIN" not in t.split("\n", 8)[-1].replace("SETUP_SLACK_MARGIN is NOT used", "")
    assert "set_clock_latency -source $::env(OT_VCLK_TT)" in t and "core_taps_ff" not in t


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_tcl_is_syntactically_complete():
    out = subprocess.run([TCLSH], input=f"set f [open {HERE / 'tt_setup_repair.tcl'}]; puts [info complete [read $f]]\n", capture_output=True, text=True)
    assert out.stdout.strip() == "1"
