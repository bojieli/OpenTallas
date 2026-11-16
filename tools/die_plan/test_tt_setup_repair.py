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
    assert (k / "tt_setup_repair.on").read_text().strip() == "cts"
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


def test_modes_cts_grt_both_write_the_mode_into_the_flag_file(tmp_path, monkeypatch):
    for env, want in (("1", "cts"), ("cts", "cts"), ("grt", "grt"), ("both", "both")):
        monkeypatch.setenv("OT_TT_SETUP_REPAIR", env)
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / env), [])
        assert (tmp_path / env / "fa" / "tt_setup_repair.on").read_text().strip() == want
    monkeypatch.setenv("OT_TT_SETUP_REPAIR", "0")
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / "off"), [])
    assert not (tmp_path / "off" / "fa" / "tt_setup_repair.on").exists()


def test_grt_step_runs_before_the_postcts_gate_reads_tt_and_routes_incrementally():
    t = gen_phys.RUN_KIT
    i = t.index("OT_TT_SETUP_RC=grt")
    assert t.index("OT_VCLK_CORNER=ff \\$MF grt CORNER=BC") < i < t.index("O5=\\$(ls /work/run/results/asap7/*/base/5_1_grt.odb | tail -1)")
    assert "5_1_grt.odb unchanged" in t
    x = (HERE / "tt_setup_repair.tcl").read_text()
    assert "global_route -start_incremental -allow_congestion" in x and "global_route -end_incremental -allow_congestion" in x and "estimate_parasitics -global_routing" in x


def test_effective_mode_is_in_every_kit_config_and_json(tmp_path, monkeypatch):
    for env, want in (("0", "off"), ("1", "cts"), ("grt", "grt"), ("both", "both")):
        monkeypatch.setenv("OT_TT_SETUP_REPAIR", env)
        gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / env), [])
        k = tmp_path / env / "fa"
        assert f"export OT_TT_SETUP_REPAIR = {want}" in (k / "config.mk").read_text().splitlines()
        import json
        assert json.loads((k / "kit_effective_env.json").read_text()) == {"OT_TT_SETUP_REPAIR": want}
    monkeypatch.delenv("OT_TT_SETUP_REPAIR", raising=False)
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path / "unset"), [])
    assert "export OT_TT_SETUP_REPAIR = off" in (tmp_path / "unset" / "fa" / "config.mk").read_text().splitlines()
