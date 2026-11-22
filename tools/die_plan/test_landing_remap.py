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


def test_resel_keeps_non_tree_raw_branch_original_and_reports_it(monkeypatch, tmp_path, capsys):
    """FABLE-FIX-KV-HG 11-19 (kv3_hgi_v1 d25d): default --resets resel through the real street_rule.reset_resel; the
    landing-side relay cland_reset_ft0_i named by the last raw-branch stage is not a relay of the OLD tree and must
    stay (it was rewritten to the tap output rst_n_t35), while the tree relays follow their sites."""
    import json
    import types
    import schema
    import reset_tree
    R = lambda q, d, depth, xy: dict(name="u_" + q, q=q, d=d, depth=depth, xy=xy)  # noqa: E731
    trees = {"old": dict(relays=[R("rst_rl_127", "rst_rl_1", 2, [600.0, 557.0]), R("rst_rl_128", "rst_rl_127", 3, [555.0, 557.0]),
                                 R("rst_rl_129", "rst_rl_128", 4, [345.0, 557.0]), R("rst_n_t35", "rst_rl_129", 5, [298.0, 395.0])]),
             "new": dict(relays=[R("rst_rl_124", "rst_rl_1", 2, [600.0, 557.0]), R("rst_rl_125", "rst_rl_124", 3, [555.0, 557.0]),
                                 R("rst_rl_126", "rst_rl_125", 4, [345.0, 557.0]), R("rst_n_t35", "rst_rl_126", 5, [298.0, 395.0])])}
    monkeypatch.setattr(schema, "Plan", lambda raw, path=None: types.SimpleNamespace(tag=raw["tag"]))
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: trees[PP.tag])

    def mk(tag):
        st = [dict(original=q, xy_um=xy) for q, xy in (("rst_rl_128", [554.752, 557.28]), ("rst_rl_129", [345.184, 557.28]),
                                                       ("cland_reset_ft0_i", [298.08, 394.816]))]
        return {"tag": tag, "partition_types": {"T": {"clock": {
            "landing_raw_branches": [dict(name="o", base="rst_rl_127", stages=st, consumers=["origin"])]}}}}
    old, new = mk("old"), mk("new")
    rec = LR.remap_plan(old, new, HERE, tmp_path)
    br = new["partition_types"]["T"]["clock"]["landing_raw_branches"][0]
    assert br["base"] == "rst_rl_124"
    assert [s["original"] for s in br["stages"]] == ["rst_rl_125", "rst_rl_126", "cland_reset_ft0_i"]
    assert rec["resets"][0]["kept"] == [["landing_raw_branches.0.stages.2", "cland_reset_ft0_i"]]
    o, n, out, rc = tmp_path / "o.json", tmp_path / "n.json", tmp_path / "out.json", tmp_path / "rc.json"
    o.write_text(json.dumps(mk("old"))); n.write_text(json.dumps(mk("new")))
    assert LR.main(["landing_remap.py", str(o), str(n), str(out), "--receipt", str(rc)]) == 0
    got = json.loads(out.read_text())["partition_types"]["T"]["clock"]["landing_raw_branches"][0]
    assert got["stages"][-1]["original"] == "cland_reset_ft0_i"
    assert json.loads(rc.read_text())["resets"][0]["kept"] == [["landing_raw_branches.0.stages.2", "cland_reset_ft0_i"]]
    assert "kept T: landing_raw_branches.0.stages.2 = cland_reset_ft0_i" in capsys.readouterr().out



def test_unreferenced_tap_does_not_take_a_needed_nearby_site():
    old = _g(("clk_t112", (1020, 1503), {(1, 1)}),
             ("clk_t130", (1030, 1503), {(2, 2)}))
    new = _g(("clk_t131", (1029, 1503), {(2, 2)}),
             ("clk_t108", (600, 1503), {(3, 3)}))
    assert LR.match_taps(old, new, 305, need={"clk_t112"}) == {
        "clk_t112": ("clk_t131", 9, 0)
    }


def test_does_not_rewrite_added_tap_declarations():
    old, new = _plan("rst_rl_60", "clk_t218"), _plan("rst_rl_60", "clk_t218")
    ck = new["partition_types"]["T"]["clock"]
    ck["added_taps"] = [{"name": "clk_t218", "xy": [1, 1]}, {"name": "clk_t777", "xy": [2, 2]}]
    _run(old, new)
    assert [r["name"] for r in ck["added_taps"]] == ["clk_t218", "clk_t777"]
    assert ck["landing_contract"]["pins"][0]["source_clock_port"] == "clk_t219"


def _anchored(raw_reset, tree):
    pl = _plan(raw_reset, "clk")
    ck = pl["partition_types"]["T"]["clock"]
    ck[RA.KEY] = RA.record(pl["partition_types"]["T"], tree, HERE, 50.0)
    return pl


def test_anchor_rerecorded_when_resel_renames_relay():
    """RESET-ANCHOR-REMAP (TAP-GRID-R5 11-22): the tap rows renumber the relay tree, reset_resel renames rst_rl_60 ->
    rst_rl_59; the anchor still listed rst_rl_60 and the bind failed RESET_ANCHOR.  Now re-recorded on the NEW tree."""
    old, new = _anchored("rst_rl_60", OLD_T), _anchored("rst_rl_60", OLD_T)

    def rename(o, n, names, d):
        n["partition_types"]["T"]["clock"]["landing_reader_start"]["branches"]["b"]["stages"][0]["raw_reset"] = "rst_rl_59"
        return {"T": dict(exports=[], raw=[["rst_rl_60", "rst_rl_59"]], skipped=[])}
    rec = LR.remap_plan(old, new, HERE, HERE, resets="resel", resel_fn=rename, keep_xy=False,
                        tree_fn=lambda raw, tn: OLD_T if raw is old else NEW_T)
    a = new["partition_types"]["T"]["clock"][RA.KEY]
    assert rec["anchors"] == ["T"] and set(a["relays"]) == {"rst_rl_59"}
    assert a["relays"]["rst_rl_59"] == dict(depth=2, xy=[0.0, 100.0]) and a["tol_um"] == 50.0
    # the bind-side check accepts it: every referenced name is carried, at the NEW tree site
    RA.resolve("T", new["partition_types"]["T"], NEW_T, HERE, lambda tree: set())


def test_anchor_untouched_when_names_unchanged():
    old, new = _anchored("rst_rl_60", OLD_T), _anchored("rst_rl_60", OLD_T)
    before = copy.deepcopy(new["partition_types"]["T"]["clock"][RA.KEY])
    rec = LR.remap_plan(old, new, HERE, HERE, resets="resel", resel_fn=lambda *a: {"T": dict(exports=[], raw=[], skipped=[])},
                        tree_fn=lambda raw, tn: OLD_T if raw is old else NEW_T)
    assert rec["anchors"] == [] and new["partition_types"]["T"]["clock"][RA.KEY] == before


def test_anchor_mode_does_not_restore_a_stale_anchor():
    """anchor mode used to put the OLD anchor back after renaming (rst_rl_61 depth 2 -> rst_rl_59)."""
    old, new = _anchored("rst_rl_61", OLD_T), _anchored("rst_rl_61", OLD_T)
    _run(old, new)
    ck = new["partition_types"]["T"]["clock"]
    assert ck["landing_reader_start"]["branches"]["b"]["stages"][0]["raw_reset"] == "rst_rl_59"
    assert set(ck[RA.KEY]["relays"]) == {"rst_rl_59"}


def test_identity_pass_keeps_authoritative_anchored_source():
    old = _plan("rst_rl_60", "clk")
    new = copy.deepcopy(old)
    path = "clock/landing_reader_start/branches/b/stages/0/raw_reset"

    def identity(raw, tn):
        if raw is old:
            return {"rst_rl_60": ("old_tree_with_reused_name",)}
        return {"rst_rl_60": ("anchored_site",), "rst_rl_59": ("old_tree_with_reused_name",)}

    assert LR.identity_remap(old, new, ["T"], identity, preserve_paths={"T": {path}}) == []
    changed = LR.identity_remap(old, new, ["T"], identity)
    assert changed[0]["new"] == "rst_rl_59"


# BOUND-TREE (FABLE-FIX-S81-J8-TAPROWS 11-22): the bound depth + site of an OLD name, not a rebuild of the OLD plan
BOUND_T = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_60", 2, (100, 0))])                       # what the bind of record emitted
REBUILT_OLD_T = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_60", 3, (5, 5)), ("rst_rl_62", 2, (100, 0))])   # today's tools reuse the name
NEW_BT = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_60", 3, (5, 5)), ("rst_rl_70", 2, (100, 3))])


def _bound_run(old, new, **kw):
    return LR.remap_plan(old, new, HERE, HERE, resets="anchor", tol_um=50.0, ported_fn=lambda tree: set(),
                         tree_fn=lambda raw, tn: REBUILT_OLD_T if raw is old else NEW_BT, groups_fn=lambda raw, tn: {}, **kw)


def _raw(pl):
    return pl["partition_types"]["T"]["clock"]["landing_reader_start"]["branches"]["b"]["stages"][0]["raw_reset"]


def test_anchor_mode_reads_the_bound_anchor_not_a_rebuilt_old_tree():
    """S81 J8 tap rows: the rebuilt OLD tree still has rst_rl_60, at depth 3; the NEW tree has it there too, so the name was
    kept and pointed at a relay of the wrong depth (bind EMIT 'release edge would move').  The bound anchor says depth 2 @ (100, 0)."""
    old, new = _anchored("rst_rl_60", BOUND_T), _anchored("rst_rl_60", BOUND_T)
    rec = _bound_run(old, new)
    assert _raw(new) == "rst_rl_70" and rec["old_tree"] == {"T": "anchor"}
    a = new["partition_types"]["T"]["clock"][RA.KEY]
    assert a["relays"] == {"rst_rl_70": dict(depth=2, xy=[100.0, 3.0])}        # re-recorded on the NEW tree
    RA.resolve("T", new["partition_types"]["T"], NEW_BT, HERE, lambda tree: set())
    old2, new2 = _anchored("rst_rl_60", BOUND_T), _anchored("rst_rl_60", BOUND_T)
    rec2 = _bound_run(old2, new2, bound_old=False)                             # the old behaviour: stale name kept
    assert _raw(new2) == "rst_rl_60" and rec2["old_tree"] == {"T": "rebuilt"}


def test_anchor_mode_reads_the_bound_rtl_first(tmp_path):
    """no anchor in the OLD plan: the bound body of the bind of record gives the depth + site (reset_tree.rtl_lines comments)"""
    (tmp_path / "s81p_T.sv").write_text(
        "  ot_dp_rrelay u_rst_rl_0 (.clk(clk), .d(rst_n), .q(rst_rl_0));  // depth 1 @ (0.0, 0.0)\n"
        "  ot_dp_rrelay u_rst_rl_60 (.clk(clk), .d(rst_rl_0), .q(rst_rl_60));  // depth 2 @ (100.0, 0.0)\n")
    old, new = _plan("rst_rl_60", "clk"), _plan("rst_rl_60", "clk")
    rec = _bound_run(old, new, bound_rtl=tmp_path)
    assert _raw(new) == "rst_rl_70" and rec["old_tree"] == {"T": "bound_rtl"}
    assert LR.bound_old_tree("T", old["partition_types"]["T"], tmp_path)[0] == "bound_rtl"


def test_bound_old_tree_never_mixes_a_partial_source(tmp_path):
    """a bound body or an anchor that lacks one referenced name is not used: the caller falls back to the rebuilt tree"""
    (tmp_path / "T.sv").write_text("  ot_dp_rrelay u_a (.clk(clk), .d(rst_n), .q(rst_rl_0));  // depth 1 @ (0.0, 0.0)\n")
    old = _anchored("rst_rl_60", BOUND_T)
    old["partition_types"]["T"]["clock"]["landing_reader_start"]["branches"]["b"]["stages"].append(dict(xy_um=[2.0, 2.0], raw_reset="rst_rl_62"))
    assert LR.bound_old_tree("T", old["partition_types"]["T"], tmp_path) is None
    assert LR.bound_old_tree("T", {"clock": {}}) is None
