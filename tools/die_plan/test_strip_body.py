"""strip_body.py (FAM-S81-SLICE-R4 11-21): the strip / body sub-tile split key of a partition type -- schema, region rule
(perimeter band minus hard-core / extra keep-out boxes + halo), per-face notches, G0 WARN-only check."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402
import strip_body as SB  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _type(**sb):
    spec = dict(band_um=130, halo_um=5, strip=dict(suffix="__strip", members=["u_cland_*", "u_ft_*"]),
                body=dict(suffix="__body", members=["u_xg*"]), crossing=dict(cycles=0, registered="both_sides"))
    spec.update(sb)
    return {"outline_um": [1000.0, 800.0],
            "hard_cores": [{"inst": "u_c.u_xr", "orient": "R0", "origin_um": [300.0, 50.0], "outline_um": [200.0, 200.0]},
                           {"inst": "u_c.u_cap", "orient": "R90", "origin_um": [20.0, 400.0], "outline_um": [300.0, 100.0]}],
            "strip_body": spec}


def test_notches_follow_the_core_boxes_with_halo():
    r = SB.resolve(_type(), "t")
    s = r["notches"]["S"]
    # u_xr bottom edge 50 - halo 5 = 45 um deep over x 295..505, full band elsewhere
    assert s == [{"from": 0.0, "to": 295.0, "depth": 130.0}, {"from": 295.0, "to": 505.0, "depth": 45.0},
                 {"from": 505.0, "to": 1000.0, "depth": 130.0}]
    # u_cap is R90: 100 x 300 placed at (20, 400) -> W notch depth 15 over y 395..705
    w = r["notches"]["W"]
    assert {"from": 395.0, "to": 705.0, "depth": 15.0} in w
    # its box also reaches 95 um into the N band (y1 705 + 800 - 130 band)
    assert r["notches"]["N"] == [{"from": 0.0, "to": 15.0, "depth": 130.0}, {"from": 15.0, "to": 125.0, "depth": 95.0},
                                 {"from": 125.0, "to": 1000.0, "depth": 130.0}]


def test_strip_area_is_band_minus_cutouts():
    r = SB.resolve(_type(), "t")
    band = 2 * 1000 * 130 + 2 * 130 * (800 - 260)
    cut_s = 210 * (130 - 45)                     # u_xr box inside the S band
    cut_w = (125 - 15) * 310                      # u_cap box (x 15..125, y 395..705) lies inside the W band
    assert abs(r["strip_area_um2"] - (band - cut_s - cut_w)) < 1e-6
    # rectangles are disjoint and inside the outline
    rs = r["strip_rects"]
    assert all(0 <= a < c <= 1000 and 0 <= b < e <= 800 for a, b, c, e in rs)
    assert abs(sum((c - a) * (e - b) for a, b, c, e in rs) - r["strip_area_um2"]) < 1e-6


def test_extra_keepouts_and_per_face_band():
    t = _type(band_um={"S": 130, "W": 40}, faces=["S", "W"], cutouts=dict(hard_cores=False, extra_um=[[600, 30, 700, 300]]))
    r = SB.resolve(t, "t")
    assert set(r["notches"]) == {"S", "W"}
    assert {"from": 595.0, "to": 705.0, "depth": 25.0} in r["notches"]["S"]
    assert [c["name"] for c in r["cutouts"]] == ["extra[0]"]


def test_overlapping_bands_are_refused():
    t = _type(band_um=450)
    try:
        SB.resolve(t, "t")
        raise AssertionError("must refuse")
    except ValueError as ex:
        assert "leave no body" in str(ex)


def test_member_rules():
    t = _type(strip=dict(members=["u_c.*"]))
    errs = SB.member_errors(t, t["strip_body"], "t")
    assert any("hard core u_c.u_xr" in e for e in errs)
    t = _type(strip=dict(members=[]))
    assert any("empty" in e for e in SB.member_errors(t, t["strip_body"], "t"))
    assert SB.member_errors(_type(), _type()["strip_body"], "t") == []


def test_schema_accepts_strip_body_and_refuses_malformed_and_g0_warns_only():
    import check as CK
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["strip_body"] = dict(
        band_um=100, halo_um=5, faces=["S", "N"], strip=dict(suffix="__strip", members=["u_cland_*"]),
        body=dict(suffix="__body"), cutouts=dict(hard_cores=True, extra_um=[[100, 0, 200, 50]], note="sram"),
        crossing=dict(cycles=0, registered="both_sides"), trigger="nontap > 400k", note="split B")
    assert schema.validate(p) == []
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert "strip_body" in on_disk["properties"]["partition_types"]["additionalProperties"]["properties"]
    R, summ = CK.run(copy.deepcopy(p))
    assert not [e for e in R.errors() if e["check"] in ("schema", "strip_body")]
    assert summ["strip_body"] == {"types": 1, "warnings": 0}
    bad = copy.deepcopy(p)
    bad["partition_types"]["mid"]["strip_body"]["faces"] = ["X"]
    assert schema.validate(bad)
    bad = copy.deepcopy(p)
    bad["partition_types"]["mid"]["strip_body"]["cutouts"]["extra_um"] = [[0, 0, 1]]
    assert schema.validate(bad)
    bad = copy.deepcopy(p)
    del bad["partition_types"]["mid"]["strip_body"]["strip"]
    assert schema.validate(bad)
    # a type whose bands swallow it: G0 WARNs (never ERRORs) under check strip_body
    w = copy.deepcopy(p)
    w["partition_types"]["mid"]["strip_body"]["band_um"] = 500
    assert schema.validate(w) == []
    R, summ = CK.run(w)
    assert not [e for e in R.errors() if e["check"] == "strip_body"]
    assert summ["strip_body"]["warnings"] == 1 and any(i["check"] == "strip_body" and i["level"] == "WARN" for i in R.items)
