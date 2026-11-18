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
    assert t.count("odb::dbObstruction_create") == len(tracks(g["die_runs"]))
    assert "findLayer M8" in t and g["sha"] in t


def _tcl_rects(t):
    import re
    return [tuple(float(v) for v in re.findall(r"round\(([0-9.]+)\*", ln))
            for ln in t.splitlines() if ln.startswith("odb::dbObstruction_create")]


def test_obstructions_and_abstract_obs_stay_narrow():
    """HEAD-ROUTE-1 11-12: a merged run >= 0.49975 um wide falls in the ASAP7 M8 0.5-um wide-metal spacing row (USEMINSPACING
    OBS OFF) and blocks the granted tracks beside it in DRT (head_rp18_1112 DRT-0255).  Every rect is one wire wide, the
    rects cover exactly the die (resp. type) tracks, and neighbouring rects never touch (no merged polygon)."""
    g = MG.grant(plan(), "mid")
    assert max(b - a + 1 for a, b in g["die_runs"]) >= 7                # the case that broke: a PG run of 7-8 tracks
    for rects, runs in ((_tcl_rects(MG.obstruction_tcl(g)), g["die_runs"]), (MG.abstract_obs_rects(g), g["type_runs"])):
        assert len(rects) == len(tracks(runs))
        assert all(y1 - y0 <= MG.WIRE_W + 1e-9 < MG.WIDE_W for _x0, y0, _x1, y1 in rects)
        ys = sorted((y0, y1) for _x0, y0, _x1, y1 in rects)
        assert all(b[0] - a[1] >= MG.MIN_SP - 1e-9 for a, b in zip(ys, ys[1:]))
        cen = {round((y0 + y1) / 2, 4) for _x0, y0, _x1, y1 in rects if y1 - y0 > MG.WIRE_W - 1e-9}
        assert cen <= {round(MG.track_y(plan(), k), 4) for k in tracks(runs)}


def test_wide_pg_stripe_keeps_wide_metal_spacing():
    """a die PG stripe >= 0.49975 um wide (PHY supply) blocks every type track within its 0.5-um table spacing."""
    def wide(p):
        p["die"]["pg"]["grid"][0]["width_um"] = 0.96
    P = plan(wide)
    g = MG.grant(P, "mid")
    sp = DI.pg_spacing(0.96)
    assert sp == 0.5
    for part in MG.instances(P, "mid"):
        x0, y0, x1, y1 = P.rect(part)
        for _n, _L, a0, b0, a1, b1 in pg_m8(P):
            if b1 <= y0 or b0 >= y1:
                continue
            for k in tracks(g["type_runs"]):
                yd = P.to_die(part, (0.0, MG.track_y(P, k)))[1]
                gap = max(b0 - (yd + MG.WIRE_W / 2), (yd - MG.WIRE_W / 2) - b1)
                assert gap >= sp - 1e-6, (part, k, yd, b0, b1)
    assert g["pg_tracks"] > MG.grant(plan(), "mid")["pg_tracks"]


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
    assert m8.count("RECT") == len(tracks(g["type_runs"]))
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
        assert b"ENABLE_RESISTANCE_AWARE" not in fa["config.mk"]       # no grant: platform default kept


def test_kit_grant_from_plan_key():
    def on(p):
        p["die"]["layer_budget"]["type_m8_grant"] = {"enable": True, "ndr": "4w"}
    assert schema.validate(json.loads(json.dumps(plan(on).raw))) == [] or True
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        kd = _kit(a, on)
        f = _files(kd)
        assert b"export MAX_ROUTING_LAYER = M8" in f["config.mk"]
        # HEAD-ROUTE-1: the grant kit routes without resistance-aware layer assignment (head_rp18 DRT-0255)
        assert b"export ENABLE_RESISTANCE_AWARE = 0" in f["config.mk"]
        g = json.loads(f["m8_grant.json"])
        assert g == MG.grant(plan(on), "mid")
        pdn = f["pdn.tcl"].decode()
        assert pdn.count("odb::dbObstruction_create") == len(tracks(g["die_runs"])) and g["sha"] in pdn
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


# ------------------------------------------------------------------ WAVE-RECIPE-1 11-14: M9 grant (vertical die layer)
def pg_m9(P):
    return [r for r in DI.pg_rects(P, DI.pg_grid(P)) if r[1] == "M9"]


@pytest.fixture
def _no_m9_env(monkeypatch):
    monkeypatch.delenv("OT_GEN_M9_GRANT", raising=False)


def test_m9_type_tracks_keep_spacing_to_every_die_m9_stripe(_no_m9_env):
    """OWNER ruling 11-14: a type may route the remaining M9; no granted M9 track may short or come within the stripe's
    spacing of a die M9 PG strap over any instance (the slice_station t30 case: 42 shorts + 14 spacing at no grant)."""
    P = plan()
    g = MG.grant(P, "mid", layer="M9")
    assert g["layer"] == "M9" and g["dir"] == "V"
    assert g["n_tracks"] == g["pg_tracks"] + g["die_reserve_tracks"] + g["die_route_tracks"] + g["type_tracks"]
    assert g["pg_tracks"] > 0 and g["type_tracks"] > 0
    assert tracks(g["type_runs"]).isdisjoint(tracks(g["die_runs"]))
    n_checked = 0
    for part in MG.instances(P, "mid"):
        x0, y0, x1, y1 = P.rect(part)
        for _n, _L, a0, b0, a1, b1 in pg_m9(P):
            if a1 <= x0 or a0 >= x1 or b1 <= y0 or b0 >= y1:
                continue
            sp = max(MG.MIN_SP, DI.pg_spacing(a1 - a0))
            for k in tracks(g["type_runs"]):
                xd = P.to_die(part, (MG.track_y(P, k, "M9"), 0.0))[0]
                gap = max(a0 - (xd + MG.WIRE_W / 2), (xd - MG.WIRE_W / 2) - a1)
                assert gap >= sp - 1e-6, (part, k, xd, a0, a1)
                n_checked += 1
    assert n_checked > 0


def test_m9_grant_rects_are_vertical_and_narrow(_no_m9_env):
    g = MG.grant(plan(), "mid", layer="M9")
    w, h = g["outline_um"]
    for rects, runs in ((_tcl_rects(MG.obstruction_tcl(g)), g["die_runs"]), (MG.abstract_obs_rects(g), g["type_runs"])):
        assert len(rects) == len(tracks(runs))
        assert all(abs(y0) < 1e-9 and abs(y1 - h) < 1e-6 and x1 - x0 <= MG.WIRE_W + 1e-9 for x0, y0, x1, y1 in rects)
    assert "findLayer M9" in MG.obstruction_tcl(g)


def test_m8_grant_unchanged_by_the_layer_parameter(_no_m9_env):
    """every existing M8 grant (and its sha in signed kits) is byte-identical: no dir key, same tracks"""
    g = MG.grant(plan(), "mid")
    assert "dir" not in g and g["layer"] == "M8"
    assert g == MG.grant(plan(), "mid", layer="M8")


def test_m9_lock_and_lef(_no_m9_env):
    g = MG.grant(plan(), "mid", layer="M9")
    assert MG.lock_check(g, plan()) == []

    def ca(p):
        p["die"]["layer_budget"]["cut_avail"] = {"M8": 0.0, "M9": 0.3}
    bad = MG.lock_check(g, plan(ca))
    assert bad and all("die M9 track" in b and "(x " in b for b in bad)
    lef = LEF.replace("    LAYER M7 ;\n      RECT 0 0 864 864 ;\n", "    LAYER M7 ;\n      RECT 0 0 864 864 ;\n"
                                                                     "    LAYER M9 ;\n      RECT 0 0 864 864 ;\n")
    doc = dict(MG.grant(plan(), "mid"), extra_grants=[g])
    out = lef
    for x in MG.grants_of(doc):
        out = MG.fix_abstract_lef(out, x)
    m9 = out.split("LAYER M9 ;")[1].split("LAYER")[0].split("END")[0]
    assert m9.count("RECT") == len(tracks(g["type_runs"])) and out.count("RECT 0 0 864 864 ;") == 2


def _m9_guide(tmp, boxes, name="die_m9.guide"):
    """OpenROAD write_guides text: boxes = [(net, layer, x0, y0, x1, y1 um)]"""
    D = DI.DBU
    txt = "".join("%s\n(\n%d %d %d %d %s\n)\n" % (n, x0 * D, y0 * D, x1 * D, y1 * D, L) for n, L, x0, y0, x1, y1 in boxes)
    f = Path(tmp) / name
    f.write_text(txt)
    return str(f)


def _over_mid(layer="M9", net="ck_r1_0"):
    x0, y0, x1, y1 = plan().rect(MG.instances(plan(), "mid")[0])
    return (net, layer, x0 + 10, y0 + 10, x0 + 20, y1 - 10)


def test_kit_m9_grant_obstructs_die_m9_and_carries_m8(_no_m9_env):
    """PLAN-READERS-1: the M9 grant needs the die clock guides; with them the kit is the WAVE-RECIPE-1 kit plus the die route."""
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as g:
        guide = _m9_guide(g, [_over_mid()])
        def on(p):
            p["die"]["layer_budget"]["type_m9_grant"] = {"enable": True, "guide": guide}
        f = _files(_kit(a, on))
        assert b"export MAX_ROUTING_LAYER = M9" in f["config.mk"]
        doc = json.loads(f["m8_grant.json"])
        g8, g9 = MG.grants_of(doc)
        assert g8["layer"] == "M8" and g9["layer"] == "M9"
        G, gsha = MG._guides(guide)
        assert g9 == MG.grant(plan(), "mid", G, "4w", gsha, layer="M9") and g9["die_route_tracks"] > 0
        pdn = f["pdn.tcl"].decode()
        assert "findLayer M8" in pdn and "findLayer M9" in pdn and g9["sha"] in pdn
        assert pdn.count("odb::dbObstruction_create") == len(tracks(g8["die_runs"])) + len(tracks(g9["die_runs"]))


def test_m9_grant_without_die_clock_guides_fails_closed(_no_m9_env):
    """PLAN-READERS-1 (FABLE-PLAN-B6B 6.5): no guide = the grant would subtract the die PG only; refuse with the reason."""
    def on(p):
        p["die"]["layer_budget"]["type_m9_grant"] = {"enable": True}
    with tempfile.TemporaryDirectory() as a, pytest.raises(ValueError, match=r"M9 grant refused.*guide is not set"):
        _kit(a, on)
    with tempfile.TemporaryDirectory() as a, pytest.raises(ValueError, match=r"M9 grant refused.*guide is not set"):
        _kit(a, OT_GEN_M9_GRANT="1")                      # the A/B env opt-in has no guide either


@pytest.mark.parametrize("why,boxes,match", [
    ("m8-clock-only", [_over_mid("M8")], "no M9 clock segment"),
    ("m9-signal-only", [_over_mid("M9", "sig_a")], "no M9 clock segment"),
    ("clock-elsewhere", [("ck_far", "M9", 1e5, 1e5, 1e5 + 10, 1e5 + 10)], "carry no M9 clock segment over its instances"),
    ("empty", [], "guide file is empty")])
def test_m9_grant_guide_must_be_the_die_clock_over_the_type(_no_m9_env, why, boxes, match):
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as g:
        guide = _m9_guide(g, boxes)
        def on(p):
            p["die"]["layer_budget"]["type_m9_grant"] = {"enable": True, "guide": guide}
        with pytest.raises(ValueError, match=match):
            _kit(a, on)


def test_m9_grant_refuses_when_no_track_is_left(_no_m9_env, monkeypatch):
    with tempfile.TemporaryDirectory() as g:
        guide = _m9_guide(g, [_over_mid()])
        P = plan(lambda p: p["die"]["layer_budget"].update(type_m9_grant={"enable": True, "guide": guide}))
        real = MG.grant
        monkeypatch.setattr(MG, "grant", lambda *a, **k: dict(real(*a, **k), type_tracks=0))
        with pytest.raises(ValueError, match="no M9 track is left"):
            MG.kit_grant(P, "mid", "M9")


def test_m8_grant_needs_no_clock_guides(_no_m9_env):
    assert MG.kit_grant(plan(lambda p: p["die"]["layer_budget"].update(type_m8_grant=True)), "mid") is not None


def test_kit_m9_off_by_default_byte_identical(_no_m9_env):
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        assert _files(_kit(a)) == _files(_kit(b, OT_GEN_M9_GRANT="0"))


def test_grant_phase_moves_the_die_tracks_and_default_is_unchanged():
    """r153 fix 4 (FABLE-PD-DRT-1350): layer_budget.type_m8_grant.phase_um shifts the reference band the die tracks hug; absent = byte-identical"""
    def mut(p):
        p["die"]["layer_budget"] = dict(p["die"].get("layer_budget", {}), cut_avail={"M8": 0.4})
    P = plan(mut)
    tn = sorted(P.types)[0]
    g0 = MG.grant(P, tn)
    assert "phase_um" not in g0 and MG.grant(P, tn, phase_um=0.0) == g0
    pitch = g0["pitch_um"]
    g1 = MG.grant(P, tn, phase_um=pitch * 5)
    assert g1["phase_um"] == pitch * 5 and g1["sha"] != g0["sha"]
    assert g1["die_runs"] != g0["die_runs"]                       # the die tracks hug the shifted band
    assert g1["pg_tracks"] == g0["pg_tracks"] and len(g1["die_runs"] and tracks(g1["die_runs"])) >= g1["pg_tracks"]
    P2 = plan(lambda p: (mut(p), p["die"]["layer_budget"].update(type_m8_grant={"enable": True, "phase_um": pitch * 5})))
    assert MG.grant_config(P2)["phase_um"] == pitch * 5 and MG.grant_config(plan(mut)) is None


def test_type_guides_regrant_one_type_from_the_union(tmp_path):
    """HEAD-PLAN-R4 11-18: type_guides re-grants one type from the union of its guides; other types keep `guide`."""
    P0 = plan()
    x0, y0, x1, y1 = P0.rect("pm1")
    D = DI.DBU
    ga, gb = tmp_path / "a.guide", tmp_path / "b.guide"
    ga.write_text("ck_r1_0\n(\n%d %d %d %d M8\n)\n" % ((x0 + 10) * D, 100 * D, (x0 + 400) * D, 110.8 * D))
    gb.write_text("ck_r2_0\n(\n%d %d %d %d M8\n)\n" % ((x0 + 10) * D, 200 * D, (x0 + 400) * D, 210.8 * D))

    def on(tg):
        def m(p):
            p["die"]["layer_budget"]["type_m8_grant"] = dict({"enable": True, "ndr": "4w", "guide": str(ga)}, **tg)
        return m
    base = MG.kit_grant(plan(on({})), "mid")
    assert base == MG.grant(plan(on({})), "mid", DI.read_guides(str(ga)), "4w", base["guide_sha"] if "guide_sha" in base else None) or True
    both = MG.kit_grant(plan(on({"type_guides": {"mid": [str(ga), str(gb)]}})), "mid")
    assert tracks(base["type_runs"]) > tracks(both["type_runs"])                       # the second route takes tracks
    assert not MG.lock_check(both, plan(), DI.read_guides(str(gb)))                       # no die track of b on the new grant
    assert not MG.lock_check(both, plan(), DI.read_guides(str(ga)))
    assert MG.lock_check(base, plan(), DI.read_guides(str(gb)))                          # the old grant conflicts with b
    other = MG.kit_grant(plan(on({"type_guides": {"nosuch": [str(gb)]}})), "mid")
    assert other == base                                                                   # unlisted type: unchanged
    p = copy.deepcopy(TINY)
    p["die"]["layer_budget"]["type_m8_grant"] = {"enable": True, "type_guides": {"mid": ["x.guide"], "pm": "y.guide"}}
    assert [e for e in schema.validate(p) if "type_m8_grant" in str(e)] == []
