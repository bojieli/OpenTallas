"""R-FLOW (RULES-FLOW-1 11-13, coord lanes/RULEBOOK-1113.md): the default flow set of every gen_phys type kit.
python3 -m pytest -q tools/die_plan/test_rflow_defaults.py"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("OT_RFLOW", "OT_PLACE_MAX_FANOUT", "OT_GEN_M8_GRANT"):
        monkeypatch.delenv(k, raising=False)


def kit(d, die="s81_head", **kw):
    raw = copy.deepcopy(TINY)
    if die is not None:
        raw["die"]["name"] = die
    kd = gen_phys.write_type_kit(schema.Plan(raw), "mid", d, [], util=0.5, **kw)
    return kd, dict(re.findall(r"^export (\w+) = (.*)$", (Path(kd) / "config.mk").read_text(), re.M))


def test_default_set(tmp_path):
    kd, c = kit(tmp_path)
    assert (c["SLEW_MARGIN"], c["CAP_MARGIN"]) == ("50", "20")
    assert c["GPL_KEEP_OVERFLOW"] == "0.25"
    assert c["OT_PLACE_MAX_FANOUT"] == "32" and c["PRE_RESIZE_TCL"] == "/work/gp_noconverge_gate.tcl"
    assert c["OT_MAXWIRE_UM"] == "120" and (Path(kd) / "grt_maxwire.tcl").is_file()
    assert c["OT_HOLD_BUDGET_PCT"] == "10"
    # hold repair is unchanged: no repair-target margin, the tool cap stays the guard value
    assert "OT_HOLD_REPAIR_MARGIN" not in c and c["HOLD_SLACK_MARGIN"] == "5" and c["OT_MAX_BUFFER_PERCENT"] == "100"
    # CTS and the router keep the platform behaviour (no grant: resistance-aware layer assignment stays on)
    assert not any(k.startswith("CTS_") for k in c) and "ENABLE_RESISTANCE_AWARE" not in c


def test_explicit_arguments_win(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PLACE_MAX_FANOUT", "48")
    _, c = kit(tmp_path, margins=(35.0, None), max_wire_um=80.0)
    assert (c["SLEW_MARGIN"], c["CAP_MARGIN"]) == ("35", "20")
    assert c["OT_MAXWIRE_UM"] == "80" and c["OT_PLACE_MAX_FANOUT"] == "48"


def test_gpl_plain_kit_has_no_keep_overflow():
    assert not any("GPL_KEEP_OVERFLOW" in line for line in gen_phys.rflow_cfg(gpl_plain=True, die="s81"))
    assert any(line == "export GPL_KEEP_OVERFLOW = 0.25" for line in gen_phys.rflow_cfg(die="s81"))


def test_only_proven_kit_classes_take_the_defaults(tmp_path, monkeypatch):
    # per kit class: a die plan without its own same-netlist proof build keeps the old kit (QC until coll_ftc, HBM)
    assert set(gen_phys.RFLOW_DIES) == {"s81", "s81_head", "qwen_kvsys", "qwen_compute"}
    for die in ("hbm", "some_new_die"):
        assert not gen_phys.rflow_on(die)
        _, c = kit(tmp_path / die, die=die)
        assert "SLEW_MARGIN" not in c and "OT_MAXWIRE_UM" not in c and "OT_PLACE_MAX_FANOUT" not in c
    for die in gen_phys.RFLOW_DIES:
        assert gen_phys.rflow_on(die) and gen_phys.place_max_fanout(die) == 32
    monkeypatch.setenv("OT_RFLOW", "1")                      # proof build of a new class
    _, c = kit(tmp_path / "forced", die="some_new_die")
    assert c["SLEW_MARGIN"] == "50" and c["OT_PLACE_MAX_FANOUT"] == "32"


def test_rflow_off_is_the_old_kit(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_RFLOW", "0")
    kd, c = kit(tmp_path)
    for k in ("SLEW_MARGIN", "CAP_MARGIN", "GPL_KEEP_OVERFLOW", "OT_PLACE_MAX_FANOUT", "OT_MAXWIRE_UM",
              "OT_HOLD_BUDGET_PCT"):
        assert k not in c, k
    assert not (Path(kd) / "grt_maxwire.tcl").exists()
    assert gen_phys.rflow_margins(None, "s81") == (None, None) and gen_phys.rflow_max_wire_um(None, "s81") is None
    assert gen_phys.place_max_fanout("s81") == 0


def test_hold_budget_line_reports_and_never_stops():
    t = (HERE / "hold_repair_pre.tcl").read_text()
    # the budget line reports only; the wrapped call's own result / error is passed through unchanged
    assert "OT_HOLD_BUDGET added" in t and "return -options $opts $msg" in t
    assert not re.search(r"OT_HOLD_BUDGET[^\n]*\n\s*error ", t)
    # no repair-target margin: the hook never writes HOLD_SLACK_MARGIN
    assert "set ::env(HOLD_SLACK_MARGIN)" not in t


def test_values_are_the_rulebook_set():
    assert gen_phys.RFLOW == {"slew_margin": 50.0, "cap_margin": 20.0, "gpl_keep_overflow": 0.25,
                              "place_max_fanout": 32, "max_wire_um": 120.0, "hold_budget_pct": 10.0}
