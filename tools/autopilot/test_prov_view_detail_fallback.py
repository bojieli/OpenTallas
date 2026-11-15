#!/usr/bin/env python3
"""KV-KITFIX-1 11-13 (DIEVIEW-KV U1): a configured detailed abstract is the module's PDN-0006 fix; when every detailed
candidate is refused, a later candidate WITHOUT detail must not silently bring back a blanket OBS over the PG pins
(kvN2 pc x6: pcf c0 receipt check_ok false, c1 never fetched, c2 = blanket base -> PDN-0006 at floorplan)."""
import argparse
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import prov_view as P  # noqa: E402
import abstract_detail as A  # noqa: E402

PINS = [dict(name="a", x=0.1, y=5.0, layer="M4"), dict(name="y", x=99.9, y=5.0, layer="M4"),
        dict(name="clk", x=50.0, y=0.1, layer="M5")]
DIRS = {"a": "INPUT", "y": "OUTPUT", "clk": "INPUT"}
DETAIL = dict(detailed_lef="detail_view.lef", detailed_receipt="detail_receipt.json", detail_bloat_factor=0)


def plan(d):
    json.dump({"pins": PINS}, open(d / "core_pins.json", "w"))
    p = {"die": {"name": "qwen_kvsys", "period_ps": 833},
         "partition_types": {"T": {"hard_cores": [{"module": "core", "inst": "u_c", "outline_um": [100, 50],
                                                   "pins_file": "core_pins.json"}]}}}
    json.dump(p, open(d / "plan.json", "w"))
    return d / "plan.json"


def candidate(out, name, meta, obs_top=7, detail=None):
    """routed candidate dir: base LEF (contract form, OBS M1..obs_top), libs, meta; detail = 'good' / 'stale' / None"""
    c = out / "routed" / "core" / name
    c.mkdir(parents=True)
    base = P.contract_lef("core", 100, 50, PINS, DIRS, obs_top)
    (c / "core.lef").write_text(base)
    for corner in ("tt", "ff"):
        (c / f"core_{corner}.lib").write_text(P.contract_lib("core", corner, 100, 50, PINS, DIRS, {"clk": (0.0, 0.0)}, 833))
    if detail:
        lines = A.splice(base.splitlines(True), {"M6": ["      RECT 20 20 30 20.1 ;\n"],
                                                 "M7": ["      RECT 50 0 50.2 50 ;\n"]}, ["M6", "M7"])
        (c / "detail_view.lef").write_text("".join(lines))
        r = dict(base_sha256=P.sha256(c / "core.lef"), out_sha256=P.sha256(c / "detail_view.lef"),
                 layers_detailed=["M6", "M7"], check_ok=detail == "good", detail_pins_equal_base=detail == "good",
                 bloat_factor=0)
        (c / "detail_receipt.json").write_text(json.dumps(r))
    (c / "meta.json").write_text(json.dumps(meta))


def make(tmp_path, cands):
    pf = plan(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    for name, meta, kw in cands:
        candidate(out, name, meta, **kw)
    a = argparse.Namespace(plan=str(pf), type="T", out=str(out), src=str(ROOT), routed=str(out / "routed"), rtl=[])
    rc = P.make(a)
    pv = out / "provisional_views.json"
    return rc, (json.loads(pv.read_text()) if pv.exists() else None)


def test_pg_blanket_layers(tmp_path):
    for top, want in ((5, []), (7, ["M6", "M7"])):
        f = tmp_path / f"c{top}.lef"
        f.write_text(P.contract_lef("core", 100, 50, PINS, DIRS, top))
        assert P.pg_blanket_layers(str(f)) == want
    nopg = tmp_path / "nopg.lef"
    nopg.write_text("MACRO core\n  SIZE 10 BY 10 ;\n  OBS\n    LAYER M7 ;\n      RECT 0 0 10 10 ;\n  END\nEND core\n")
    assert P.pg_blanket_layers(str(nopg)) == []


def test_good_detail_is_selected(tmp_path):
    rc, m = make(tmp_path, [("c0", dict(DETAIL, job="detail"), dict(detail="good")),
                            ("c1", dict(job="plain"), {})])
    assert rc == 0 and m["children"]["core"]["job"] == "detail" and "abstract_detail" in m["children"]["core"]


def test_refused_detail_does_not_fall_back_to_blanket(tmp_path, capsys):
    """the kvN2 pcf case: c0 detail with a check_ok false receipt, c1 detail never fetched, c2 blanket base"""
    rc, m = make(tmp_path, [("c0", dict(DETAIL, job="stale"), dict(detail="stale")),
                            ("c1", dict(DETAIL, job="unfetched", fetch_errors=["intel2:/x/detail_view.lef rc=23"]), {}),
                            ("c2", dict(job="plain"), {})])
    out = capsys.readouterr().out
    assert rc == 3 and m is None
    assert "blanket fallback refused" in out and "M6,M7" in out and "staging fetch failed" in out


def test_without_configured_detail_blanket_base_still_selected(tmp_path):
    rc, m = make(tmp_path, [("c0", dict(job="plain"), {})])
    assert rc == 0 and m["children"]["core"]["job"] == "plain"


def test_refused_detail_falls_back_to_non_blanket_base(tmp_path):
    rc, m = make(tmp_path, [("c0", dict(DETAIL, job="stale"), dict(detail="stale")),
                            ("c1", dict(job="plain_m5"), dict(obs_top=5))])
    assert rc == 0 and m["children"]["core"]["job"] == "plain_m5"


def test_kit_wave_stage_records_fetch_errors():
    src = (HERE / "kit_wave.py").read_text()
    assert 'staged["fetch_errors"] = fetch_errors' in src
