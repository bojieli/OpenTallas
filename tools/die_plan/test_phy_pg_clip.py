"""S81-TYPES-6 11-07 (COORD 23:0x (2) choice (a), class PHY-REGION-CLOCK-ENTRY): PHY PG region + hard blockage
clipped to the PHY macro bounding box grown by phy_pg_clip_um (opt-in type key)."""
import json
from pathlib import Path

import gen_phys as G
import schema as S

HERE = Path(__file__).parent
PLAN = HERE.parents[1] / "physical/die_plan/s81/plan_h2_2249.json"


def _plan(clip=None, notch=None, south=None, big=True):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    q = dict(lef="m.lef", lib="m_tt.lib", outline_um=[8.64, 2.16], orient="MX")
    c = dict(inst="u_phy", module="logical_phy", status="rework", origin_um=[17.28, 25.92], outline_um=[8.64, 8.64],
             physical_parts=[dict(q, physical_inst="u_bound.u_core.u_ptx", physical_master="txm", origin_um=[17.28, 32.4]),
                             dict(q, physical_inst="u_bound.u_core.u_prx", physical_master="rxm", origin_um=[17.28, 28.08])])
    t = raw["partition_types"]["src"]
    t["contents"] = [c]
    for k, v in (("phy_pg_clip_um", clip), ("phy_pg_west_notch_um", notch), ("phy_pg_south_notch_um", south)):
        if v is not None:
            t[k] = v
    p = S.Plan(raw)
    n = next(n for n, r in p.parts.items() if r["type"] == "src")
    a, b = p.to_die(n, (4.32, 4.32)), p.to_die(n, (38.88, 34.56))   # domain spans far beyond the macros
    raw["die"]["pg"] = {"domains": [dict(name="phy", nets=["VDDPHY", "VSS"],
                                         rect_um=[min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])])]}
    return S.Plan(raw)


def test_key_absent_region_unchanged():
    r = G.phy_pg_domains(_plan(), "src")[0][3]
    assert r == [4.32, 4.32, 38.88, 34.56], r


def test_clip_all_four_sides():
    r = G.phy_pg_domains(_plan(clip=1.0), "src")[0][3]
    # macros: x 17.28-25.92, y 28.08-34.56 (two stacked 8.64 x 2.16 parts); +1 um, snapped outward to site / row
    assert r[0] <= 16.28 and r[0] > 16.28 - G.PHY_PG_NOTCH_SITE_UM, r
    assert r[1] <= 27.08 and r[1] > 27.08 - G.PHY_PG_NOTCH_ROW_UM, r
    assert r[2] >= 26.92 and r[2] < 26.92 + G.PHY_PG_NOTCH_SITE_UM, r
    assert r[3] == 34.56, r           # never grows past the die domain rect
    for v in r:
        assert v == round(v, 4)


def test_clip_composes_with_notch_tighter_wins():
    r = G.phy_pg_domains(_plan(clip=10.0, notch=0.5, south=0.5), "src")[0][3]
    assert 16.78 - G.PHY_PG_NOTCH_SITE_UM < r[0] <= 16.78, r     # notch 0.5 is tighter than clip 10 on W
    assert 27.58 - G.PHY_PG_NOTCH_ROW_UM < r[1] <= 27.58, r
    assert 35.92 <= r[2] < 35.92 + G.PHY_PG_NOTCH_SITE_UM, r     # clip 10 on E (domain reaches 38.88)


def test_region_still_covers_every_macro():
    for clip in (0.0, 0.3, 10.0):
        r = G.phy_pg_domains(_plan(clip=clip), "src")[0][3]
        assert r[0] <= 17.28 and r[1] <= 28.08 and r[2] >= 25.92 and r[3] >= 34.56, (clip, r)


def test_schema_accepts_key():
    raw = _plan(clip=10.0).raw
    assert not [e for e in S.validate(raw) if "phy_pg_clip_um" in e]


def test_all_s81_serdes_types_carry_the_clip():
    P = S.Plan(json.loads(PLAN.read_text()))
    serdes = sorted(t for t in P.types if t.startswith("serdes__"))
    assert len(serdes) == 11
    for tn in serdes:
        t = P.types[tn]
        assert t["phy_pg_clip_um"] == 10.0, tn
        dom = G.phy_pg_domains(P, tn)
        assert len(dom) == 1, tn
        boxes = []
        for c in t["contents"]:
            for q in c.get("physical_parts", []):
                if q["physical_inst"] in dom[0][4]:
                    w, h = q["outline_um"]
                    boxes.append((q["origin_um"][0], q["origin_um"][1], q["origin_um"][0] + w, q["origin_um"][1] + h))
        x1 = max(b[2] for b in boxes)
        r = dom[0][3]
        assert x1 + 10.0 <= r[2] < x1 + 10.0 + G.PHY_PG_NOTCH_SITE_UM or r[2] == t["outline_um"][0], (tn, r, x1)
        assert r[1] <= min(b[1] for b in boxes) and r[0] <= min(b[0] for b in boxes), tn
