"""WINDOW-REDERIVE-1112: physical/die_plan/s81/events/window_rederive_1112/apply_window_rederive_1112.py raises the plan's
clock.tap_window.per_port_ps to min(measured need + 20, 208) only where the need exceeds the effective window, never
clips silently (need > cap is listed REGION-TREE BALANCE and not written), leaves signed types alone, is idempotent and
byte-identical without a table."""
import importlib.util
import json
from pathlib import Path

import pytest

import gen_phys
import schema

HERE = Path(__file__).parent
EV = HERE.parent.parent / "physical/die_plan/s81/events/window_rederive_1112/apply_window_rederive_1112.py"
_spec = importlib.util.spec_from_file_location("awr", EV)
AWR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AWR)

PORTS = ["clk", "clk_t1", "clk_t2", "clk_t3", "clk_t4", "clk_t5", "clk_t6", "clk_t7", "clk_t8"]


def _plan(tmp, per_port=None, form="indent"):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw["clock"]["seam_hold"] = dict(sender_ps=25, seam_ps=80)
    tw = dict(window_ps=80.0, note="flat W", per_type_ps={"src": 70})
    if per_port is not None:
        tw["per_port_ps"] = per_port
    raw["clock"]["tap_window"] = tw
    p = tmp / "in.json"
    p.write_text(json.dumps(raw, indent=1) + "\n" if form == "indent" else json.dumps(raw) + "\n")
    return p


def _table(tmp, m):
    p = tmp / "tab.json"
    p.write_text(json.dumps(dict(per_port_ps=m, plan_sha256="abc", corners=["TT", "FF"])))
    return p


def _run(tmp, plan, tab=None, *extra):
    out, rep = tmp / "out.json", tmp / "rep.json"
    argv = [str(plan), str(out), str(rep)] + (["--table", str(tab)] if tab else []) + list(extra)
    AWR.main(argv)
    return out, json.loads(rep.read_text())


def test_no_table_is_byte_identical(tmp_path):
    p = _plan(tmp_path)
    out, rep = _run(tmp_path, p)
    assert out.read_bytes() == p.read_bytes() and rep["applied"] is False


def test_only_over_window_ports_are_raised(tmp_path):
    p = _plan(tmp_path)
    m = {"src": {"clk": 10, "clk_t1": 70, "clk_t2": 71, "clk_t3": 150}}      # flat 70: only t2 and t3 are over
    out, rep = _run(tmp_path, p, _table(tmp_path, m))
    new = json.loads(out.read_text())["clock"]["tap_window"]["per_port_ps"]["src"]
    assert new == {"clk_t2": 91, "clk_t3": 170}
    P = schema.Plan(json.loads(out.read_text()))
    assert gen_phys.tap_window_port_table(P, "src")["clk_t3"] == 170.0
    assert rep["REGION_TREE_BALANCE"] == {}


def test_cap_soft_hard_not_clipped_silently(tmp_path):
    p = _plan(tmp_path)
    m = {"src": {"clk": 195, "clk_t1": 230, "clk_t2": 100}}
    out, rep = _run(tmp_path, p, _table(tmp_path, m))
    new = json.loads(out.read_text())["clock"]["tap_window"]["per_port_ps"]["src"]
    assert new == {"clk": 208, "clk_t2": 120}                                   # clk_t1 (230 > 208) not written
    b = rep["REGION_TREE_BALANCE"]["src"]
    assert b["clk"]["window_written"] == 208 and b["clk_t1"]["window_written"] is None and b["clk_t1"]["need"] == 230


def test_existing_entry_only_raised_never_lowered(tmp_path):
    p = _plan(tmp_path, per_port={"src": {"clk": 150, "clk_t1": 40}})
    m = {"src": {"clk": 90, "clk_t1": 60}}
    out, rep = _run(tmp_path, p, _table(tmp_path, m))
    new = json.loads(out.read_text())["clock"]["tap_window"]["per_port_ps"]["src"]
    assert new == {"clk": 150, "clk_t1": 80}


def test_signed_type_is_excluded_and_reported(tmp_path):
    p = _plan(tmp_path)
    s = tmp_path / "signed.txt"
    s.write_text("src\n")
    out, rep = _run(tmp_path, p, _table(tmp_path, {"src": {"clk": 150}}), "--signed", str(s))
    assert out.read_bytes() == p.read_bytes() and "src" in rep["signed_would_change"]


def test_idempotent_and_only_declared_keys_change(tmp_path):
    p = _plan(tmp_path, form="compact")
    t = _table(tmp_path, {"src": {"clk": 150, "clk_t4": 100}})
    out, _ = _run(tmp_path, p, t)
    a, b = json.loads(p.read_text()), json.loads(out.read_text())
    assert a["clock"]["tap_window"]["note"] != b["clock"]["tap_window"]["note"]
    b["clock"]["tap_window"]["note"] = a["clock"]["tap_window"]["note"]
    b["clock"]["tap_window"].pop("per_port_ps")
    assert a == b
    out1 = out.read_bytes()
    (tmp_path / "in2.json").write_bytes(out1)
    out2, _ = _run(tmp_path, tmp_path / "in2.json", t)
    assert out2.read_bytes() == out1


def test_refuses_stale_port_and_negative_need(tmp_path):
    p = _plan(tmp_path)
    with pytest.raises(SystemExit):
        _run(tmp_path, p, _table(tmp_path, {"src": {"not_a_port": 150}}))
    with pytest.raises(SystemExit):
        _run(tmp_path, p, _table(tmp_path, {"src": {"clk": -1}}))
