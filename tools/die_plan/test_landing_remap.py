"""LANDING-REMAP (HEAD-REMAP-1): relays by (depth, site), density taps by (sink group, site)."""
import copy
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_remap as LR  # noqa: E402
import reset_anchor as RA  # noqa: E402


def _tree(rows):
    return {"relays": [dict(q=q, depth=d, xy=list(xy)) for q, d, xy in rows]}


def _plan(raw_reset, src, mode="density"):
    return {"partition_types": {"T": {"clock": {
        "tap_mode": mode, "tap_radius_um": 200.0,
        "landing_reader_start": {"depth": 2, "branches": {"b": {"stages": [dict(xy_um=[1.0, 1.0], raw_reset=raw_reset)]}}},
        "landing_contract": {"pins": [dict(name="fclk_out_b", kind="clock", source_clock_port=src),
                                      dict(name="fclk_out_c", kind="clock", source_clock_port="clk")]},
        "taps": [dict(name="u_core.clk", kind="core", xy=[1, 1])]}}}}


OLD_T = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_60", 2, (100, 0)), ("rst_rl_61", 2, (0, 100))])
NEW_T = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_59", 2, (0, 100)), ("rst_rl_60", 2, (100, 3)), ("rst_rl_61", 3, (5, 5))])


def _g(*rows):
    return {n: (xy, frozenset(s)) for n, xy, s in rows}


OLD_G = _g(("clk", (0, 0), {(1, 1)}), ("clk_t217", (50, 50), {(2, 2), (3, 3)}), ("clk_t218", (300, 300), {(9, 9), (8, 8)}))
NEW_G = _g(("clk", (0, 0), {(1, 1)}), ("clk_t218", (60, 55), {(2, 2), (3, 3)}), ("clk_t219", (310, 290), {(9, 9), (8, 8), (7, 7)}))


def _run(old, new, **kw):
    kw.setdefault("resets", "anchor")
    kw.setdefault("tree_fn", lambda raw, tn: OLD_T if raw is old else NEW_T)
    kw.setdefault("tol_um", 50.0)
    kw.setdefault("ported_fn", lambda tree: set())
    kw.setdefault("groups_fn", lambda raw, tn: OLD_G if raw is old else NEW_G)
    return LR.remap_plan(old, new, HERE, HERE, **kw)


def test_relay_and_tap_names_follow_identity():
    old, new = _plan("rst_rl_60", "clk_t218"), _plan("rst_rl_60", "clk_t218")
    rec = _run(old, new)
    ck = new["partition_types"]["T"]["clock"]
    assert ck["landing_reader_start"]["branches"]["b"]["stages"][0]["raw_reset"] == "rst_rl_60"   # same depth + site
    assert [p["source_clock_port"] for p in ck["landing_contract"]["pins"]] == ["clk_t219", "clk"]
    assert RA.KEY not in ck                              # transient anchor stripped
    assert rec["taps"][0]["remaps"] == [dict(name="clk_t218", to="clk_t219", moved_um=20, shared_sinks=2)]


def test_relay_renumbered():
    old, new = _plan("rst_rl_61", "clk"), _plan("rst_rl_61", "clk")
    _run(old, new)
    assert new["partition_types"]["T"]["clock"]["landing_reader_start"]["branches"]["b"]["stages"][0]["raw_reset"] == "rst_rl_59"


def test_keep_anchor_and_remapped_plan_is_refused_as_new():
    old, new = _plan("rst_rl_61", "clk_t218"), _plan("rst_rl_61", "clk_t218")
    _run(old, new, keep_anchor=True)
    assert RA.KEY in new["partition_types"]["T"]["clock"]
    with pytest.raises(LR.RemapError):      # remap output must not be fed back as a NEW plan of the same OLD
        _run(old, new)


def test_unchanged_is_byte_identical():
    old, new = _plan("rst_rl_60", "clk_t218"), _plan("rst_rl_60", "clk_t218")
    before = copy.deepcopy(new)
    _run(old, new, tree_fn=lambda raw, tn: OLD_T, groups_fn=lambda raw, tn: OLD_G)
    assert new == before


def test_relay_without_site_fails_closed():
    old, new = _plan("rst_rl_61", "clk"), _plan("rst_rl_61", "clk")
    far = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_70", 2, (900, 900))])
    with pytest.raises(RA.AnchorError):
        _run(old, new, tree_fn=lambda raw, tn: OLD_T if raw is old else far)


def test_tap_without_group_or_site_fails_closed():
    old, new = _plan("rst_rl_60", "clk_t218"), _plan("rst_rl_60", "clk_t218")
    gone = _g(("clk", (0, 0), {(1, 1)}))
    with pytest.raises(LR.RemapError):
        _run(old, new, groups_fn=lambda raw, tn: OLD_G if raw is old else gone)


def test_match_is_injective_and_prefers_shared_sinks_over_distance():
    old = _g(("a", (0, 0), {(1, 1)}), ("b", (10, 0), {(2, 2)}))
    new = _g(("x", (0, 0), {(2, 2)}), ("y", (10, 0), {(1, 1)}))
    m = LR.match_taps(old, new, 50)
    assert (m["a"][0], m["b"][0]) == ("y", "x")


def test_explicit_taps_types_are_skipped():
    old, new = _plan("rst_rl_60", "clk_t218", "explicit"), _plan("rst_rl_60", "clk_t218", "explicit")
    rec = _run(old, new)
    assert new["partition_types"]["T"]["clock"]["landing_contract"]["pins"][0]["source_clock_port"] == "clk_t218"
    assert rec["skipped"]


def test_tap_definitions_are_not_references():
    t = _plan("rst_rl_60", "clk_t218")["partition_types"]["T"]
    t["clock"]["taps"].append(dict(name="clk_t5", xy=[1, 2]))
    assert [(c[k]) for c, k in LR.tap_refs(t)] == ["clk_t218"]


def test_resel_mode_delegates_every_type_and_rewrites_taps():
    old, new = _plan("rst_rl_60", "clk_t218"), _plan("rst_rl_60", "clk_t218")
    calls = []

    def fake(o, n, names, d):
        calls.append(names)
        return {"T": dict(exports=[["rst_start_raw_0", "u_rrl_1", "u_rrl_2"]], raw=[], skipped=[])}
    rec = LR.remap_plan(old, new, HERE, HERE, resets="resel", resel_fn=fake,
                        groups_fn=lambda raw, tn: OLD_G if raw is old else NEW_G)
    assert calls == [["T"]] and rec["resets"][0]["exports"]
    assert new["partition_types"]["T"]["clock"]["landing_contract"]["pins"][0]["source_clock_port"] == "clk_t219"


def test_resel_error_fails_closed():
    old, new = _plan("rst_rl_60", "clk"), _plan("rst_rl_60", "clk")
    with pytest.raises(LR.RemapError):
        LR.remap_plan(old, new, HERE, HERE, resets="resel", resel_fn=lambda *a: {"T": dict(error="plan load: x")})


def test_adopt_by_key_takes_old_names_for_same_port_pin_stage_local():
    def t(inst, net, src, raw, loc):
        return {"reset_start_raw_exports": [dict(port="rst_start_raw_0", instance=inst, net=net, xy_um=[1, 1])],
                "clock": {"landing_contract": {"pins": [dict(name="p0", source_instance=src, source_copy_from_net=net)]},
                          "landing_reader_start": {"branches": {"b": {"stages": [dict(raw_reset=raw)]}}},
                          "landing_local_resets": [dict(name="l0", raw=loc)]}}
    old, new = t("u_rrl_316", "rst_rl_316", "u_rrl_316", "rst_rl_60", "rst_rl_7"), t("u_rrl_301", "rst_rl_301", "u_rrl_301", "rst_rl_61", "rst_rl_8")
    ad = LR.adopt_by_key(old, new)
    assert new == old and len(ad) == 6
    assert LR.adopt_by_key(old, new) == []


def test_unreferenced_taps_may_vanish():
    old = _g(("a", (0, 0), {(1, 1)}), ("b", (900, 900), {(5, 5)}))
    new = _g(("x", (0, 0), {(1, 1)}))
    with pytest.raises(LR.RemapError):
        LR.match_taps(old, new, 50)
    assert LR.match_taps(old, new, 50, need={"a"}) == {"a": ("x", 0, 1)}


def test_resel_keeps_pin_sites_and_fails_closed_on_far_relay():
    def mk():
        return {"partition_types": {"T": {"reset_start_raw_exports": [dict(port="p0", instance="a", net="n", xy_um=[0.0, 0.0])],
                                          "clock": {"landing_contract": {"pins": [dict(name="p0", xy_um=[1.0, 1.0])]}}}}}
    def moving(o, n, names, d):
        e = n["partition_types"]["T"]
        e["reset_start_raw_exports"][0].update(instance="b", xy_um=[300.0, 0.0])
        e["clock"]["landing_contract"]["pins"][0]["xy_um"] = [301.0, 1.0]
        return {"T": dict(exports=[["p0", "a", "b"]], raw=[], skipped=[])}
    old, new = mk(), mk()
    LR.remap_plan(old, new, HERE, HERE, resets="resel", resel_fn=moving)
    t = new["partition_types"]["T"]
    # export row xy_um = relay site of the rebuilt tree (HEAD-99: 41 stale rows in G0 rp21z20); the landing pin stays put
    assert t["reset_start_raw_exports"][0]["xy_um"] == [300.0, 0.0] and t["reset_start_raw_exports"][0]["instance"] == "b"
    assert t["clock"]["landing_contract"]["pins"][0]["xy_um"] == [1.0, 1.0]
    with pytest.raises(LR.RemapError):
        LR.remap_plan(mk(), mk(), HERE, HERE, resets="resel", resel_fn=moving, max_um=100.0)
    moved = mk()
    LR.remap_plan(mk(), moved, HERE, HERE, resets="resel", resel_fn=moving, keep_xy=False)
    assert moved["partition_types"]["T"]["reset_start_raw_exports"][0]["xy_um"] == [300.0, 0.0]
