"""FABLE-FIX-S81-RINGS 11-16: ring_place=ff guard (compose and kit preflight) for landing rings of >= 256 bits."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP
import kit_preflight as KP

R = [0, 0, 10, 10]


def _bands(**kw):
    b = {"wide": dict(rect_um=R, width=1104), "edge": dict(rect_um=R, width=256), "narrow": dict(rect_um=R, width=255),
         "monitor_0": dict(rect_um=R, width=600), "core": dict(rect_um=R, width=1104, hard_core="u_c"),
         "fail": dict(width=1104, placement="FAIL")}
    for k, v in kw.items():
        b[k].update(v)
    return b


def test_missing_lists_only_wide_soft_ring_bands():
    assert CP.ring_place_missing(_bands()) == [("edge", 256), ("wide", 1104)]
    assert CP.ring_place_missing(_bands(wide=dict(ring_place="ff"), edge=dict(ring_place="ff"))) == []
    assert CP.ring_place_missing(_bands(), min_bits=2000) == []
    assert CP.ring_place_missing(None) == []


def _plan(bands):
    return {"partition_types": {"t": {"clock": {"landing_contract": {"bands": bands}}}}}


def test_compose_guard_fails_closed(monkeypatch):
    monkeypatch.setattr(CP, "_compose", lambda *a, **k: (_plan(_bands()), {}))
    assert CP.compose(None, None)[0]                      # guard off by default: other dies unchanged
    with pytest.raises(ValueError, match="RING-FF-GUARD: 2 landing ring band"):
        CP.compose(None, None, ring_ff_min_bits=256)
    monkeypatch.setattr(CP, "_compose", lambda *a, **k: (_plan(_bands(wide=dict(ring_place="ff"), edge=dict(ring_place="ff"))), {}))
    assert CP.compose(None, None, ring_ff_min_bits=256)[0]


def test_compose_guard_does_not_reach_compose_kwargs(monkeypatch):
    seen = {}
    monkeypatch.setattr(CP, "_compose", lambda *a, **k: (seen.update(k), (_plan({}), {}))[1])
    CP.compose(None, None, ring_ff_min_bits=256, band_ring="ff")
    assert seen == {"band_ring": "ff"}


def _kit(tmp_path, bands, tcl, die="s81"):
    (tmp_path/"freeze.json").write_text(json.dumps({"die": die}))
    (tmp_path/"landing_contract.json").write_text(json.dumps({"bands": bands}))
    (tmp_path/"landing_placement.tcl").write_text(tcl)
    return tmp_path


def test_preflight_ring_ff(tmp_path):
    tcl = "set cland_groups {\n  {u_cland_wide {0.0 0.0 10.0 10.0} ring:wide}\n  {u_cland_edge {0.0 0.0 10.0 10.0} ring:edge+ffr}\n}\n"
    e = KP.ring_ff(_kit(tmp_path, _bands(edge=dict(ring_place="ff")), tcl))
    assert len(e) == 1 and "wide (1104 bits) has no ring_place=ff" in e[0]
    ok = _bands(wide=dict(ring_place="ff"), edge=dict(ring_place="ff"))
    e = KP.ring_ff(_kit(tmp_path, ok, tcl))              # plan key present, stale tcl tag
    assert len(e) == 1 and "tag ring:wide has no +ff" in e[0]
    assert KP.ring_ff(_kit(tmp_path, ok, tcl.replace("ring:wide}", "ring:wide@1.8037+ff}"))) == []
    assert KP.ring_ff(_kit(tmp_path, _bands(), tcl, die="qwen_kvsys")) == []      # only S81 kits are judged
    e = KP.ring_ff(_kit(tmp_path, _bands(edge=dict(ring_place="ff")), tcl, die="s81_head"))   # LEP-RINGFF-1: HEAD is judged
    assert len(e) == 1 and "wide (1104 bits) has no ring_place=ff" in e[0]


def test_preflight_ring_ff_no_contract(tmp_path):
    assert KP.ring_ff(tmp_path) == []


def test_fallback_land_defaults_follow_the_die():
    src = (Path(__file__).resolve().parents[1]/"s81_head"/"fallback_land.py").read_text()
    assert 'band_ring = a.band_ring or ("ff" if s81 else "all")' in src
    assert 'c.add_argument("--band-ring", default=None' in src and 'c.add_argument("--band-reserve", default=None' in src


def test_frozen_band_takes_compose_ring_form(monkeypatch):
    # F2s 11-16: band_fixed_um bands (svc) were copied without ring_place and lost +ff under --band-ring ff
    fx = {"rect_um": [0, 0, 10, 10], "width": 1882}
    monkeypatch.setattr(CP, "BAND_RING", "ff")
    b = CP._frozen_band(fx)
    assert b["ring_place"] == "ff" and "ring_place" not in fx and b["rect_um"] == fx["rect_um"]
    assert CP._frozen_band(dict(fx, ring_place="all"))["ring_place"] == "all"
    monkeypatch.setattr(CP, "BAND_RING", "all")
    assert "ring_place" not in CP._frozen_band(fx)
