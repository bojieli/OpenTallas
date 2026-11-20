"""PG-PINBAND-1 (FABLE-ROUTE lever 2): floorplan-time pin-access check (pg_pin_check.tcl) and its gen hook.
python3 -m pytest -q tools/die_plan/test_pg_pin_check.py"""
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402

TCL = HERE / "pg_pin_check.tcl"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("OT_PG_PIN_CHECK", "OT_PG_PIN_CHECK_BAND_UM"):
        monkeypatch.delenv(k, raising=False)


def test_mode_default_off(monkeypatch):
    assert not gen_phys.pg_pin_check_mode()
    monkeypatch.setenv("OT_PG_PIN_CHECK", "1")
    assert gen_phys.pg_pin_check_mode()
    monkeypatch.setenv("OT_PG_PIN_CHECK", "0")
    assert not gen_phys.pg_pin_check_mode()


def test_hook_text(monkeypatch):
    monkeypatch.setenv("OT_PG_PIN_CHECK", "warn")
    monkeypatch.setenv("OT_PG_PIN_CHECK_BAND_UM", "60")
    h = gen_phys.pg_pin_check_hook_tcl()
    assert "set ::env(BAND_UM) 60" in h and "OT_PG_PIN_CHECK_WARN) 1" in h
    assert "uplevel #0 {source /work/pg_pin_check.tcl}" in h


def test_tcl_gap_proc():
    """pgpc_gap: overlap negative, edge gap positive, diagonal hypot (proc extracted, run in plain tclsh)."""
    src = TCL.read_text()
    i = src.index("proc pgpc_gap")
    j = src.index("proc pgpc_run")
    prog = src[i:j] + "\nputs [pgpc_gap {0 0 10 10} {5 0 15 10}]\nputs [pgpc_gap {0 0 10 10} {13 0 20 10}]\nputs [pgpc_gap {0 0 10 10} {13 14 20 20}]\n"
    out = subprocess.run(["tclsh"], input=prog, capture_output=True, text=True, check=True).stdout.split()
    assert [float(x) for x in out] == [-5.0, 3.0, 5.0]


def test_tcl_complete():
    prog = "set f [open {%s}]\nputs [info complete [read $f]]\n" % TCL
    r = subprocess.run(["tclsh"], input=prog, capture_output=True, text=True)
    assert r.stdout.strip() == "1", r.stderr


def test_kit_hook_wired_last_in_post_pdn(tmp_path, monkeypatch):
    import copy
    import json
    import re
    import schema
    tiny = json.loads((HERE / "examples" / "tiny_plan.json").read_text())

    def mk(d):
        raw = copy.deepcopy(tiny)
        raw["die"]["name"] = "s81_head"
        kd = Path(gen_phys.write_type_kit(schema.Plan(raw), "mid", d, [], util=0.5))
        return kd, (kd / "config.mk").read_text()
    # Isolate the pin check; the default-on rail check has its own last-hook test.
    monkeypatch.setenv("OT_PG_RAIL_CHECK", "0")
    kd, cfg = mk(tmp_path / "off")
    assert "pg_pin_check_hook" not in cfg and not (kd / "pg_pin_check_hook.tcl").exists()
    monkeypatch.setenv("OT_PG_PIN_CHECK", "1")
    kd, cfg = mk(tmp_path / "on")
    assert (kd / "pg_pin_check.tcl").is_file() and (kd / "pg_pin_check_hook.tcl").is_file()
    post = re.search(r"^export POST_PDN_TCL = (\S+)", cfg, re.M).group(1)
    text = (kd / "post_pdn.tcl").read_text() if post.endswith("post_pdn.tcl") else post
    assert text.rstrip().endswith("pg_pin_check_hook.tcl") or post.endswith("pg_pin_check_hook.tcl")
