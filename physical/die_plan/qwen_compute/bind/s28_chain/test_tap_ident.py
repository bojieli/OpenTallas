"""tap_ident.py FINAL-first rule (DIE-QC-100 11-13): s29 trial cases where REF identity reverted R-REACH-4 sources."""
import importlib
import json
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def ti(monkeypatch):
    fake = types.ModuleType("schema")

    class Plan:
        def __init__(self, raw, path=None):
            self.raw = raw

    fake.Plan = Plan
    fake.tap_grid = lambda P, tn: [(n, x, y) for n, (x, y) in P.raw["_taps"][tn].items()]
    monkeypatch.setitem(sys.modules, "schema", fake)
    sys.path.insert(0, HERE)
    try:
        sys.modules.pop("tap_ident", None)
        yield importlib.import_module("tap_ident")
    finally:
        sys.path.remove(HERE)
        sys.modules.pop("tap_ident", None)


def plan(tn, pin, src, xy, taps):
    return {"budgets": {"tap_pitch_um": 400.0}, "partitions": [{"name": "p0", "type": tn}],
            "partition_types": {tn: {"clock": {"tap_radius_um": 200.0, "landing_contract": {"pins": [
                {"name": pin, "kind": "clock", "dir": "out", "source_clock_port": src, "xy_um": list(xy)}]}}}},
            "_taps": {tn: taps}}


def run(ti, tmp_path, ref, fin, monkeypatch):
    r, f, o = tmp_path / "ref.json", tmp_path / "fin.json", tmp_path / "out.json"
    r.write_text(json.dumps(ref))
    f.write_text(json.dumps(fin))
    monkeypatch.setattr(sys, "argv", ["tap_ident.py", str(r), str(f), "--out", str(o),
                                      "--report", str(tmp_path / "rep.json"), "--eq", str(tmp_path / "eq.tsv")])
    try:
        ti.main()
        rc = 0
    except SystemExit as e:
        rc = e.code
    out = json.loads(o.read_text()) if o.exists() else None
    return rc, out, json.loads((tmp_path / "rep.json").read_text())


def src_of(p):
    t = next(iter(p["partition_types"].values()))
    return t["clock"]["landing_contract"]["pins"][0]["source_clock_port"]


@pytest.mark.parametrize("tn,pin,keep,old,old_hop", [
    ("slw_su_c__cl19bb38ef", "fclk_out_x_su_l1_p1_o", "clk_t12", "clk_t11", 1207.9),
    ("slw_stm_v1__cl2086fa2c", "fclk_out_x_su_c_ctl_o", "clk_t74", "clk_t75", 527.3),
])
def test_final_source_within_hop_is_kept(ti, tmp_path, monkeypatch, tn, pin, keep, old, old_hop):
    # R-REACH-4 re-sourced the pin to `keep` on the FINAL grid (hop 120 um).  In REF numbering `keep` sat where FINAL
    # now has `old`, so REF identity would re-point to `old` at old_hop um.  FINAL-first keeps it.
    pxy = (1000.0, 1000.0)
    ref = plan(tn, pin, keep, pxy, {keep: (1000.0 + old_hop, 1000.0), old: (3000.0, 3000.0)})
    fin = plan(tn, pin, keep, pxy, {keep: (1120.0, 1000.0), old: (1000.0 + old_hop, 1000.0)})
    rc, out, rep = run(ti, tmp_path, ref, fin, monkeypatch)
    assert rc == 0 and src_of(out) == keep and rep["repoints"] == 0


def test_dangling_source_long_final_hop_fails(ti, tmp_path, monkeypatch):
    pxy = (0.0, 0.0)
    ref = plan("t", "fclk_o", "clk_t9", pxy, {"clk_t9": (100.0, 0.0)})
    fin = plan("t", "fclk_o", "clk_t9", pxy, {"clk_t3": (500.0, 0.0)})     # clk_t9 gone; only tap 500 um away
    rc, out, rep = run(ti, tmp_path, ref, fin, monkeypatch)
    assert rc == 3 and out is None


def test_renumbered_source_repointed_by_ref_location(ti, tmp_path, monkeypatch):
    # source name now points 600 um away on FINAL (renumbered); the REF location is clk_t2 in FINAL at 100 um
    pxy = (0.0, 0.0)
    ref = plan("t", "fclk_o", "clk_t1", pxy, {"clk_t1": (100.0, 0.0)})
    fin = plan("t", "fclk_o", "clk_t1", pxy, {"clk_t1": (600.0, 0.0), "clk_t2": (100.0, 0.0)})
    rc, out, rep = run(ti, tmp_path, ref, fin, monkeypatch)
    assert rc == 0 and src_of(out) == "clk_t2" and rep["repoints"] == 1
