"""DIE-QC-67 PINDUP 11-03: tt_ctlm GRT-0031/GRT-0080 "Invalid pin placement": two landing pins of a type on one site.
12 QC types on plan_qc52 and plan_qc52_ucie1103: cland_fstart_out_<a> / fclk_out_<b> buses 8.64 um apart, and two
children at one seam point (cland_dn_ready_0 / _1)."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as GP  # noqa: E402
import landing_contract as LC  # noqa: E402
import schema as S  # noqa: E402

QC = Path(__file__).resolve().parents[2] / "physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json"
LAYERS = {"M7": {"dir": "V", "pitch_um": 0.064, "offset_um": 0.032}, "M6": {"dir": "H", "pitch_um": 0.064, "offset_um": 0.032}}


def _plan(pins, edge=()):
    t = {"outline_um": [777.6, 518.4], "clock": {"landing_contract": {"pins": pins}, "edge_clocks": list(edge)}}
    return SimpleNamespace(types={"t": t}, layers=LAYERS, layer_budget={"partition_signal_max": "M7"})


def _pin(name, x, y, kind="ctl", d="out"):
    return dict(name=name, dir=d, kind=kind, layer="M7", xy_um=[x, y], epoch=False)


def test_tt_ctlm_pair_separates_along_its_face_and_clock_keeps_site():
    pins = [_pin("cland_fstart_out_cal_descriptor_obs", 20.064, 2.656), _pin("fclk_out_cal_image_ready", 20.064, 2.656, "clock")]
    P = _plan(pins)
    before = copy.deepcopy(P.types)
    t = LC.separate_pins(P, "t")
    assert P.types == before                                 # the input is untouched
    got = {p["name"]: p["xy_um"] for p in t["clock"]["landing_contract"]["pins"]}
    assert got["fclk_out_cal_image_ready"] == [20.064, 2.656]
    x, y = got["cland_fstart_out_cal_descriptor_obs"]
    assert y == pytest.approx(2.656, abs=0.04) and abs(x - 20.064) >= 2.0 and abs(x - 20.064) < 3.0
    assert not LC.overlapping_pins(SimpleNamespace(types={"t": t}, layers=LAYERS), t)


def test_moved_clock_input_takes_its_edge_clock_tap():
    pins = [_pin("fclk_in_cland_dn_0", 611.296, 1173.984, "clock", "in"), _pin("fclk_in_cland_dn_1", 611.296, 1173.984, "clock", "in")]
    edge = [dict(port=p["name"], tap_um=list(p["xy_um"]), period_mult=1) for p in pins]
    P = _plan(pins, edge)
    P.types["t"]["outline_um"] = [613.44, 1339.2]
    t = LC.separate_pins(P, "t")
    got = {p["name"]: p["xy_um"] for p in t["clock"]["landing_contract"]["pins"]}
    assert got["fclk_in_cland_dn_0"] == [611.296, 1173.984] and got["fclk_in_cland_dn_1"] != got["fclk_in_cland_dn_0"]
    assert abs(got["fclk_in_cland_dn_1"][0] - 611.296) < 0.1                  # E face: slides in y
    assert {e["port"]: e["tap_um"] for e in t["clock"]["edge_clocks"]} == got
    assert edge[1]["tap_um"] == [611.296, 1173.984]


def test_slide_skips_sites_already_taken():
    pins = [_pin("a", 20.064, 2.656), _pin("b", 20.064, 2.656), _pin("c", 22.24, 2.656), _pin("d", 17.888, 2.656)]
    t = LC.separate_pins(_plan(pins), "t")
    got = {p["name"]: p["xy_um"] for p in t["clock"]["landing_contract"]["pins"]}
    assert got["a"] == [20.064, 2.656] and got["c"] == [22.24, 2.656] and got["d"] == [17.888, 2.656]
    assert min(abs(got["b"][0] - got[n][0]) for n in "acd") >= 0.12


def test_no_duplicate_returns_none():
    assert LC.separate_pins(_plan([_pin("a", 20.064, 2.656), _pin("b", 24.416, 2.656)]), "t") is None


def test_overlap_on_one_track_is_separated():
    # coll_ucie fclk_out_shr_r_rx / cland_up_fault: same M7 track, 0.128 um apart in y, 0.432-um rectangles
    pins = [_pin("fclk_out_shr_r_rx", 775.456, 1154.976, "clock"), _pin("cland_up_fault", 775.456, 1155.104)]
    P = _plan(pins)
    P.types["t"]["outline_um"] = [777.6, 1468.8]
    t = LC.separate_pins(P, "t")
    got = {p["name"]: p["xy_um"] for p in t["clock"]["landing_contract"]["pins"]}
    assert got["fclk_out_shr_r_rx"] == [775.456, 1154.976] and abs(got["cland_up_fault"][1] - 1154.976) >= 0.472


@pytest.mark.skipif(not QC.is_file(), reason="plan_qc52.json not in this checkout")
def test_plan_qc52_has_no_duplicate_site_and_raw_is_as_read():
    raw = json.loads(QC.read_text())
    keep = json.dumps(raw, sort_keys=True)
    P = S.Plan(raw, str(QC))
    assert json.dumps(P.raw, sort_keys=True) == keep          # plan digests do not move
    assert {tn: LC.overlapping_pins(P, t) for tn, t in P.types.items() if LC.overlapping_pins(P, t)} == {}
    moved = [tn for tn in P.types if P.types[tn] is not raw["partition_types"][tn]]
    assert {"tt_ctlm", "coll_ucie"} <= set(moved) and len(moved) == 13
    for tn in moved:
        for e in P.types[tn]["clock"].get("edge_clocks", []):
            pin = next((p for p in P.types[tn]["clock"]["landing_contract"]["pins"] if p["name"] == e["port"]), None)
            assert pin is None or pin["xy_um"] == e["tap_um"]
    # a separated pin also stays clear of every other pin io.tcl places (clock taps, reset outs, bus pins)
    for tn in moved:
        recs = GP.plan_pin_records(P, tn, GP.type_pins(P, tn))
        recs = recs if isinstance(recs, list) else list(recs.values())
        sites = [(r["layer"], round(r["x"], 4), round(r["y"], 4)) for r in recs]
        assert len(sites) == len(set(sites)), tn
    assert not LC.check(P)["errors"] or LC.check(P)["errors"] == LC.check(S.Plan(json.loads(keep), str(QC)))["errors"]


def test_corner_pin_slides_on_the_face_it_sits_on():
    # DIE-QC-68: KV plan_c kv3_hub_C, y 0.416 from N is inside the edge margin and x 2.144 from W: sliding along N never fits
    pins = [_pin("a", 2.144, 1675.744, "clock", "in"), _pin("b", 2.144, 1675.744, "ctl", "in")]
    P = _plan(pins)
    P.types["t"]["outline_um"] = [2160.0, 1676.16]
    t = LC.separate_pins(P, "t")
    got = {p["name"]: p["xy_um"] for p in t["clock"]["landing_contract"]["pins"]}
    assert got["a"] == [2.144, 1675.744]
    assert got["b"] != got["a"] and got["b"][0] == pytest.approx(2.144, abs=4.0)  # a near free site, same corner
    assert not LC.overlapping_pins(SimpleNamespace(types={"t": t}, layers=LAYERS), t)


def test_full_band_keeps_the_site_and_does_not_raise(capsys):
    pins = [_pin("a", 1.0, 1.0, "clock", "in"), _pin("b", 1.0, 1.0, "ctl", "in")]
    P = _plan(pins)
    P.types["t"]["outline_um"] = [1.2, 1.2]            # no other legal site inside the edge margin
    t = LC.separate_pins(P, "t")
    assert {p["name"]: p["xy_um"] for p in t["clock"]["landing_contract"]["pins"]}["b"] == [1.0, 1.0]
    assert "LANDING_PIN_SITE_FULL t.b" in capsys.readouterr().err
