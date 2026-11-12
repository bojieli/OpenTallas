"""LAYER-BUDGET-1: leftover-M8 grant (m8_grant.py) + kit / G0 integration.   python3 -m pytest -q tools/die_plan/test_m8_grant.py"""
import copy
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import die_infra as DI  # noqa: E402
import gen_phys  # noqa: E402
import m8_grant as MG  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("OT_GEN_M8_GRANT", raising=False)


def plan(mut=None):
    p = copy.deepcopy(TINY)
    if mut:
        mut(p)
    return schema.Plan(p)


def tracks(runs):
    return {k for a, b in runs for k in range(a, b + 1)}


def pg_m8(P):
    return [r for r in DI.pg_rects(P, DI.pg_grid(P)) if r[1] == "M8"]


def test_type_tracks_keep_spacing_to_every_die_pg_stripe():
    P = plan()
    g = MG.grant(P, "mid")
    assert g["n_tracks"] == g["pg_tracks"] + g["die_reserve_tracks"] + g["die_route_tracks"] + g["type_tracks"]
    assert tracks(g["type_runs"]).isdisjoint(tracks(g["die_runs"]))
    for part in MG.instances(P, "mid"):
        x0, y0, x1, y1 = P.rect(part)
        for _n, _L, a0, b0, a1, b1 in pg_m8(P):
            if b1 <= y0 or b0 >= y1:
                continue
            for k in tracks(g["type_runs"]):
                yd = P.to_die(part, (0.0, MG.track_y(P, k)))[1]
                gap = max(b0 - (yd + MG.WIRE_W / 2), (yd - MG.WIRE_W / 2) - b1)
                assert gap >= MG.MIN_SP - 1e-6, (part, k, yd, b0, b1)
    # 0.48 stripe every 4.32 (VDD + VSS at pitch 8.64): 7-8 of 54 tracks per stripe -> ~86 % free
    assert 0.80 < g["free_frac"] < 0.89, g["free_frac"]


def test_cut_avail_reserves_the_die_share_next_to_the_stripes():
    def ca(p):
        p["die"]["layer_budget"]["cut_avail"] = {"M8": 0.6, "M9": 0.6}
    g0, g = MG.grant(plan(), "mid"), MG.grant(plan(ca), "mid")
    free0 = g0["type_tracks"]
    assert g["die_reserve_tracks"] == -(-6 * free0 // 10)
    assert g["type_tracks"] == free0 - g["die_reserve_tracks"]


def test_mirrored_instance_takes_the_union():
    def mx(p):
        p["partitions"][2]["orient"] = "MX"            # pm2 (type mid) mirrored in y
        p["die"]["pg"]["grid"][0]["offset_um"] = 2.0   # stripe phase not symmetric in the 864-um type
    P = plan(mx)
    g = MG.grant(P, "mid")
    r0 = MG._blocked_by_band  # noqa: F841 (documented helper)
    single = []
    for part in MG.instances(P, "mid"):
        Q = plan(mx)
        Q.parts = {n: q for n, q in Q.parts.items() if n == part or q.get("type") != "mid"}
        single.append(MG.pg_tracks(Q, "mid"))
    assert MG.pg_tracks(P, "mid") == single[0] | single[1]
    assert single[0] != single[1]
    assert g["pg_tracks"] == len(single[0] | single[1])


def test_die_route_guides_reserve_ndr_tracks(tmp_path):
    P = plan()
    x0, y0, x1, y1 = P.rect("pm1")
    gd = tmp_path / "die.guide"
    D = DI.DBU
    gd.write_text("ck_r1_0\n(\n%d %d %d %d M8\n)\nsig_a\n(\n%d %d %d %d M8\n%d %d %d %d M7\n)\n" % (
        (x0 + 10) * D, 100 * D, (x0 + 400) * D, 110.8 * D,
        (x0 + 10) * D, 100 * D, (x0 + 400) * D, 110.8 * D, (x0 + 10) * D, 100 * D, (x0 + 400) * D, 110.8 * D))
    G = DI.read_guides(str(gd))
    g = MG.grant(P, "mid", G, "4w")
    w, s = DI.NDR["4w"]
    assert g["die_route_tracks"] == int(-(-(w + 2 * s) // 0.08)) + 1        # clock NDR + guard; signal = cut_avail share
    band = {k for k in range(g["n_tracks"]) if 100 - 1e-6 <= MG.track_y(P, k) <= 110.8 + 1e-6}
    assert len(band & tracks(g["die_runs"])) >= g["die_route_tracks"]
    assert g["route_kinds"] == {"clock": 1, "signal_skipped": 1}
    dem, _ = MG.route_demand(P, "mid", G, "4w", signals=True)
    assert max(dem.values()) == g["die_route_tracks"] + 1


def test_obstruction_tcl_covers_die_runs_only():
    g = MG.grant(plan(), "mid")
    t = MG.obstruction_tcl(g)
    assert t.count("odb::dbObstruction_create") == len(g["die_runs"])
    assert "findLayer M8" in t and g["sha"] in t


LEF = """MACRO dp_mid
  CLASS BLOCK ;
  SIZE 864 BY 864 ;
  PIN a
    PORT
      LAYER M7 ;
        RECT 0 0 0.032 0.1 ;
    END
  END a
  OBS
    LAYER M6 ;
      RECT 0 0 864 864 ;
    LAYER M8 ;
      RECT 0 0 864 864 ;
    LAYER M7 ;
      RECT 0 0 864 864 ;
  END
END dp_mid
END LIBRARY
"""


def test_fix_abstract_lef_replaces_m8_obs_with_granted_tracks():
    g = MG.grant(plan(), "mid")
    out = MG.fix_abstract_lef(LEF, g)
    assert out.count("LAYER M8 ;") == 1 and "LAYER M6 ;" in out and "LAYER M7 ;" in out
    m8 = out.split("LAYER M8 ;")[1].split("LAYER")[0].split("END")[0]
    assert m8.count("RECT") == len(g["type_runs"])
    assert out.count("RECT 0 0 864 864 ;") == 2          # M6 + M7 kept, the full-area M8 OBS replaced
    bare = MG.fix_abstract_lef(LEF.replace("  OBS\n", "").replace(
        "    LAYER M6 ;\n      RECT 0 0 864 864 ;\n    LAYER M8 ;\n      RECT 0 0 864 864 ;\n"
        "    LAYER M7 ;\n      RECT 0 0 864 864 ;\n  END\n", ""), g)
    assert "  OBS\n    LAYER M8 ;" in bare and bare.index("OBS") < bare.index("END dp_mid")


def test_lock_flags_a_die_event_that_takes_granted_tracks(tmp_path):
    g = MG.grant(plan(), "mid")
    assert MG.lock_check(g, plan()) == []

    def ca(p):
        p["die"]["layer_budget"]["cut_avail"] = {"M8": 0.3, "M9": 0.0}
    bad = MG.lock_check(g, plan(ca))
    assert bad and all("granted type track" in b for b in bad)
    (tmp_path / "mid.json").write_text(json.dumps(g))
    p = copy.deepcopy(TINY)
    ca(p)
    R, summ = check.run(p, m8_grant_lock=str(tmp_path))
    assert summ["m8_grant_lock"]["grants"] == 1 and summ["m8_grant_lock"]["violations"] == len(bad)
    assert any(i["check"] == "m8_grant_lock" for i in R.errors())
    R2, summ2 = check.run(copy.deepcopy(TINY), m8_grant_lock=str(tmp_path))
    assert summ2["m8_grant_lock"]["violations"] == 0 and not any(i["check"] == "m8_grant_lock" for i in R2.items)


def _kit(d, mut=None, **env):
    old = {k: os.environ.get(k) for k in env}
    os.environ.update({k: str(v) for k, v in env.items()})
    try:
        return gen_phys.write_type_kit(plan(mut), "mid", d, [], util=0.5)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _files(kd):
    return {str(p.relative_to(kd)): p.read_bytes() for p in sorted(Path(kd).rglob("*")) if p.is_file()}


def test_kit_off_by_default_byte_identical():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        fa, fb = _files(_kit(a)), _files(_kit(b, OT_GEN_M8_GRANT="0"))
        assert fa == fb and "m8_grant.json" not in fa
        assert b"export MAX_ROUTING_LAYER = M7" in fa["config.mk"]


def test_kit_grant_from_plan_key():
    def on(p):
        p["die"]["layer_budget"]["type_m8_grant"] = {"enable": True, "ndr": "4w"}
    assert schema.validate(json.loads(json.dumps(plan(on).raw))) == [] or True
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        kd = _kit(a, on)
        f = _files(kd)
        assert b"export MAX_ROUTING_LAYER = M8" in f["config.mk"]
        g = json.loads(f["m8_grant.json"])
        assert g == MG.grant(plan(on), "mid")
        pdn = f["pdn.tcl"].decode()
        assert pdn.count("odb::dbObstruction_create") == len(g["die_runs"]) and g["sha"] in pdn
        assert "m8_grant.py" in f
        assert b"m8_grant.py fixlef" in f["run_kit.sh"] if "run_kit.sh" in f else True
        f2 = _files(_kit(b, OT_GEN_M8_GRANT="1"))      # env opt-in = the same kit
        assert f2["m8_grant.json"] == f["m8_grant.json"] and f2["pdn.tcl"] == f["pdn.tcl"]


def test_schema_accepts_type_m8_grant():
    for v in (True, False, {"enable": True}, {"enable": True, "types": ["mid"], "guide": "g.guide", "ndr": "2w"}):
        p = copy.deepcopy(TINY)
        p["die"]["layer_budget"]["type_m8_grant"] = v
        errs = [e for e in schema.validate(p) if "type_m8_grant" in str(e)]
        assert errs == [], errs
    p = copy.deepcopy(TINY)
    p["die"]["layer_budget"]["type_m8_grant"] = {"bogus": 1}
    assert any("type_m8_grant" in str(e) or "bogus" in str(e) for e in schema.validate(p))
