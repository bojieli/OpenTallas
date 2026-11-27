"""C-TAP-REACH tap_cohort_assign: model == regex, singles on true nearest tap, pins kept and checked, safe writes; source mutants are killed."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tap_cohort_assign as T  # noqa: E402

TAPS = [("clk", 0.0, 0.0), ("clk_t1", 400.0, 0.0)]


def S(prefix, n, x, y, sep="/"):
    return [(f"{prefix}{sep}q[{i}]", x + i, y) for i in range(n)]


def check(m):
    # 1 cohorts + singles
    sinks = S("u_ft_a_s0", 4, 10.0, 5.0) + S("u_ft_b_s0", 4, 390.0, 5.0) + [("u_one", 200.0, 0.0)]
    r = m.assign(sinks, TAPS, reach=250, span=300, cap=100)
    assert r["fixed"] == {"u_ft_a_s0": "clk", "u_ft_b_s0": "clk_t1"} and not r["unassigned"], r
    # 2 singles go to their TRUE nearest tap even when that tap is then over span
    sg = [("s0", 10.0, 0.0), ("s1", 290.0, 290.0), ("s2", 11.0, 1.0)]
    r = m.assign(sg, [("clk", 0.0, 0.0)], reach=1000, span=300, cap=100)
    assert r["over_span"] == {"clk": 570.0}, r
    assert m.assign([("s", 10.0, 0.0)], TAPS, 250, 300, 100)["singles"] == {"s": "clk"}
    # 3 unsafe (escaped) keys are not pinnable: their sinks are singles, the regex never carries them
    esc = [("u_a.g\\[0\\].x/q\\[%d\\]" % i, 10.0 + i, 0.0) for i in range(3)] + S("u_ok", 3, 12.0, 0.0)
    r = m.assign(esc, TAPS, reach=250, span=300, cap=100)
    assert list(r["fixed"]) == ["u_ok"] and r["unpinnable"] == 3 and len(r["singles"]) == 3, r
    # 4 flat '.' names have no cohort unit: singles; a '/' key that would swallow a flat descendant is flagged
    flat = [(f"u_h.s0.q{i}", 10.0 + i, 0.0) for i in range(3)]
    r = m.assign(flat, TAPS, 250, 300, 100)
    assert not r["fixed"] and len(r["singles"]) == 3 and not r["swallowed"]
    sw = m.assign(S("u_k", 2, 10.0, 0.0) + [("u_k.flat", 12.0, 0.0)], TAPS, 250, 300, 100)
    assert sw["swallowed"] == ["u_k.flat"], sw
    # 5 reset relays follow their sinks: never pinned
    assert not m.assign(S("u_rrl_3", 3, 10.0, 0.0), TAPS, 250, 300, 100)["fixed"]
    # 5b keys of the plan's own re are cohorts even without a pin
    assert "u_re" in m.assign(S("u_re", 1, 10.0, 0.0), TAPS, 250, 300, 100, re_keys=["u_re"])["members"]
    # 5c over cap verdict
    assert m.assign(S("u_c", 4, 10.0, 0.0), TAPS, 250, 300, 3, pinned={"u_c": "clk"})["over_cap"] == {"clk": 4}
    # 5d longest key wins (what Tcl ARE longest-match does with the same alternation)
    coh, _, _ = m.cohorts_of([("u_a/b/q0", 1, 1), ("u_a/b/q1", 2, 1), ("u_a/q2", 1, 1), ("u_a/q3", 2, 1)], 2, forced=["u_a", "u_a/b"])
    assert len(coh["u_a/b"]) == 2 and len(coh["u_a"]) == 2, coh
    # 6 pinned: kept, checked
    r = m.assign(sinks, TAPS, 250, 300, 100, pinned={"u_ft_a_s0": "clk_t1"})
    assert r["fixed"]["u_ft_a_s0"] == "clk_t1" and r["pinned_bad"], r        # beyond reach of the pinned tap
    r = m.assign(sinks, TAPS, 250, 300, 100, pinned={"u_ft_a_s0": "clk_zz"})
    assert r["pinned_bad"] and "u_ft_a_s0" not in r["fixed"] or r["pinned_bad"][0]["tap"] == "clk_zz", r
    # 7 reach / cap / span
    far = S("u_far", 2, 200.0, 0.0)
    assert m.assign(far, TAPS, reach=150, span=300, cap=100)["unassigned"][0]["cohort"] == "u_far"
    assert m.assign(S("u_c", 4, 10.0, 0.0), TAPS, reach=250, span=300, cap=3)["unassigned"]
    two = S("u_x", 2, 100.0, 0.0) + S("u_y", 2, 200.0, 150.0)
    r = m.assign(two, [("clk", 150.0, 70.0)], reach=250, span=200, cap=100)
    assert r["unassigned"] and r["per_tap"]["clk"]["box_wh"] <= 200, r
    # 8 nearest feasible
    r = m.assign(sinks, TAPS, reach=5000, span=5000, cap=100)
    assert r["fixed"] == {"u_ft_a_s0": "clk", "u_ft_b_s0": "clk_t1"}
    return True


def test_assign_contract():
    assert check(T)


def test_tap_group_write_rules():
    g = T.tap_group_of({}, {"u_new": "clk_t1"})
    assert g["follow_re"] == "" and g["fixed_taps"] == {"u_new": "clk_t1"} and g["re"] == "^(u_new)[/.]"
    old = {"tap_group": {"re": "^(u_old|u_o2)[/.]", "fixed_taps": {"u_old": "clk_t9"}, "note": "n"}}
    g = T.tap_group_of(old, {"u_new": "clk_t1", "u_old": "clk"})
    assert g["fixed_taps"] == {"u_new": "clk_t1", "u_old": "clk_t9"} and "follow_re" not in g
    assert re.match(g["re"], "u_new/q") and re.match(g["re"], "u_o2.x") and not re.match(g["re"], "u_other/q")
    for bad in (({"tap_group": {"re": "(?:^|[/.])(u_ft_x)[/.]"}}, {"k": "clk"}), ({}, {}), ({}, {"bad[0]": "clk"}), ({}, {"k": "9bad"})):
        try:
            T.tap_group_of(*bad)
        except T.Refused:
            continue
        raise AssertionError(f"not refused: {bad}")


def test_next_tap_index_and_sites():
    assert T.next_tap_index([("clk", 0, 0), ("clk_t1", 0, 0), ("clk_t7", 0, 0)]) == 8
    sinks = S("u_f", 3, 900.0, 5.0) + [("u_g0", 905.0, 9.0), ("u_h0", 1500.0, 5.0)]
    r = T.assign(sinks, TAPS, reach=250, span=300, cap=100)
    sites = T.propose_sites(sinks, r["unassigned"] + [dict(cohort="u_g0", sinks=1), dict(cohort="u_h0", sinks=1)], TAPS, 250, lambda x, y, t: (x, y), r["members"])
    assert len(sites) == 2
    taps2 = TAPS + [(f"clk_t{2 + i}", x, y) for i, (x, y) in enumerate(sites)]
    r2 = T.assign(sinks, taps2, reach=250, span=300, cap=100)
    assert not r2["unassigned"] and not r2["single_far"], r2


MUTANTS = [
    ("        return any(abs(x - tx) + abs(y - ty) > reach for x, y, _ in members)", "        return False"),
    ("return b[4] <= cap and (b[1] - b[0]) + (b[3] - b[2]) <= span", "return (b[1] - b[0]) + (b[3] - b[2]) <= span"),
    ("return b[4] <= cap and (b[1] - b[0]) + (b[3] - b[2]) <= span", "return b[4] <= cap"),
    ("n = min(tapxy, key=lambda t: (abs(tapxy[t][0] - x) + abs(tapxy[t][1] - y), tap_order(t)))", "n = max(tapxy, key=lambda t: (abs(tapxy[t][0] - x) + abs(tapxy[t][1] - y), tap_order(t)))"),
    ("        if far(tap, coh[key]):\n            pinned_bad.append(dict(cohort=key, tap=tap, reason=\"a sink is beyond reach of its pinned tap\"))\n", ""),
    ("    swallowed = [i for k, v in coh.items() for _, _, i in v if raw_key(i) != k]", "    swallowed = []"),
    ("not RELAY.fullmatch(k)", "True"),
    ("    forced_keys = list(pinned) + list(re_keys or ())", "    forced_keys = list(pinned)"),
    ("    over_cap = {n: b[4] for n, b in box.items() if b and b[4] > cap}", "    over_cap = {}"),
    ('if a.add_taps and (res["unassigned"] or res["over_span"] or res["single_far"]) and mode != "density":', 'if a.add_taps and res["unassigned"] and mode != "density":'),
    ("        if len(keep) != len(added):", "        if False:"),
    ("tap_order(t)))", "t))"),
    ("        if added and not a.no_freeze:", "        if False:"),
    ("            if rec0.get(\"notes\"):", "            if False:"),
    ("    if split_oversize:\n        excl = set()", "    if False:\n        excl = set()"),
    ("k not in forced_set and k not in excl and box_wh(", "k not in excl and box_wh("),
    ("coh, singles, swallowed = cohorts_of(sinks, min_cohort, forced=[k for k in forced_keys if SAFE.fullmatch(k)], exclude=excl)", "pass"),
    ("        if any(not LITERAL.fullmatch(k) for k in alts):", "        if False:"),
    ("sorted(keys, key=lambda k: (-len(k), k))", "sorted(keys, key=lambda k: (len(k), k))"),
    ("order = sorted(tapxy, key=lambda n: (abs(tapxy[n][0] - cx) + abs(tapxy[n][1] - cy), tap_order(n)))", "order = sorted(tapxy, key=lambda n: (-(abs(tapxy[n][0] - cx) + abs(tapxy[n][1] - cy)), tap_order(n)))"),
    ("        group = {\"follow_re\": \"\"}", "        group = {}"),
    ("        merged.update(old.get(\"fixed_taps\") or {})", "        pass"),
    ("    return (max(n) + 1) if n else len(taps)", "    return len(taps)"),
    ("if \"/\" in inst and SAFE.fullmatch(k) and not RELAY.fullmatch(k) and k not in exclude:", "if \"/\" in inst and not RELAY.fullmatch(k) and k not in exclude:"),
]


def test_mutants_are_killed():
    src = (HERE / "tap_cohort_assign.py").read_text()
    base = type(sys)("base")
    exec(compile(src, "base", "exec"), base.__dict__)
    for fn in (check, _rules_on, _index_on, _main_on, _renum_on, _split_on, _split2_on, _freeze_on, _ffail_on):          # unmutated control: every checker must pass on the real module
        assert fn(base)
    for old, new in MUTANTS:
        assert old in src, old
        mod = type(sys)("mut")
        exec(compile(src.replace(old, new, 1), "mut", "exec"), mod.__dict__)
        killed = False
        for fn in (check, lambda m: _rules_on(m), lambda m: _index_on(m), lambda m: _main_on(m), lambda m: _renum_on(m), lambda m: _split_on(m), lambda m: _split2_on(m), lambda m: _freeze_on(m), lambda m: _ffail_on(m)):
            try:
                fn(mod)
            except Exception:
                killed = True
                break
        assert killed, f"mutant survived: {old[:70]}"


def _rules_on(m):
    old = {"tap_group": {"re": "^(u_old|u_o2)[/.]", "fixed_taps": {"u_old": "clk_t9"}}}
    g = m.tap_group_of(old, {"u_new": "clk_t1", "u_old": "clk"})
    assert g["fixed_taps"]["u_old"] == "clk_t9"
    assert m.tap_group_of({}, {"u_new": "clk_t1"})["follow_re"] == ""
    return True


def _index_on(m):
    assert m.next_tap_index([("clk", 0, 0), ("clk_t7", 0, 0)]) == 8
    return True


def test_overspan_items_pick_far_singles():
    sg = [("s0", 10.0, 0.0), ("s1", 290.0, 290.0), ("s2", 11.0, 1.0)]
    r = T.assign(sg, [("clk", 0.0, 0.0)], reach=1000, span=300, cap=100)
    items = T.overspan_items(sg, [("clk", 0.0, 0.0)], r)
    assert items and items[0]["cohort"] == "s1"
    sites = T.propose_sites(sg, items, [("clk", 0.0, 0.0)], 1000, lambda x, y, t: (x, y))
    r2 = T.assign(sg, [("clk", 0.0, 0.0), ("clk_t1", sites[0][0], sites[0][1])], reach=1000, span=300, cap=100)
    assert not r2["over_span"], r2


# ---- main() end to end: stub schema / tap_split in a --tools dir (the tool imports them from there) ----------------------
STUB_SCHEMA = '''
class Plan:
    def __init__(self, raw, path):
        self.types = raw["partition_types"]
def tap_grid(plan, tn):
    return [(t["name"], t["xy"][0], t["xy"][1]) for t in plan.types[tn]["clock"]["grid_stub"]]
def core_taps(plan, tn):
    return []
def tap_clear(tile, x, y, taken, strict=True):
    return (x, y, 0)
'''
STUB_SPLIT = '''
def type_taps(schema, plan, clock, tn):
    t = [(x["name"], x["xy"][0], x["xy"][1]) for x in clock["taps"]]
    return t, len(t)
def explicit_legalize(tile, x, y, taken):
    return (x, y)
'''


def _run(tmp_path, clock, sinks, extra=()):
    import json
    tools = tmp_path / "tools"
    tools.mkdir(exist_ok=True)
    (tools / "schema.py").write_text(STUB_SCHEMA)
    (tools / "tap_split.py").write_text(STUB_SPLIT)
    (tools / "reach_fix.py").write_text(STUB_RF)
    (tools / "row_normalize.py").write_text(STUB_RN)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"partition_types": {"t": {"clock": clock}}}))
    tsv = tmp_path / "sinks.tsv"
    tsv.write_text("".join(f"clk\t{i}\tDFF\t{x}\t{y}\n" for i, x, y in sinks))
    out, rep = tmp_path / "out.json", tmp_path / "rep.json"
    for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
        sys.modules.pop(m, None)
    rc = T.main([str(plan), "t", str(tsv), "--tools", str(tools), "--out", str(out), "--report", str(rep), *extra])
    for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
        sys.modules.pop(m, None)
    if str(tools) in sys.path:
        sys.path.remove(str(tools))
    return rc, out, (json.loads(rep.read_text()) if rep.exists() else None)


def _clock(**kw):
    return dict({"tap_mode": "explicit", "taps": [{"name": "clk", "xy": [0, 0]}, {"name": "clk_t1", "xy": [400, 0]}]}, **kw)


def test_main_exit0_writes_group_and_follow_re(tmp_path):
    import json
    sinks = S("u_ft_a_s0", 4, 10.0, 5.0) + S("u_ft_b_s0", 4, 390.0, 5.0)
    rc, out, rep = _run(tmp_path, _clock(), sinks)
    assert rc == 0 and rep["unassigned"] == [] and rep["swallowed_sinks"] == 0
    g = json.loads(out.read_text())["partition_types"]["t"]["clock"]["tap_group"]
    assert g["fixed_taps"] == {"u_ft_a_s0": "clk", "u_ft_b_s0": "clk_t1"} and g["follow_re"] == "" and g["re"].startswith("^(")


def test_main_exit2_unassigned_writes_nothing_then_add_taps_fixes(tmp_path):
    sinks = S("u_far", 3, 1500.0, 0.0)
    rc, out, rep = _run(tmp_path, _clock(), sinks)
    assert rc == 2 and not out.exists() and rep["unassigned"][0]["cohort"] == "u_far"
    t2 = tmp_path / "r2"; t2.mkdir()
    rc, out, rep = _run(t2, _clock(), sinks, ["--add-taps", "3"])
    assert rc == 0 and [a["name"] for a in rep["added_taps"]] == ["clk_t2"]


def test_main_exit3_over_cap_and_over_span_and_pinned_bad(tmp_path):
    sinks = S("u_c", 4, 10.0, 0.0)
    rc, out, rep = _run(tmp_path, _clock(tap_group={"re": "^(u_c)[/.]", "fixed_taps": {"u_c": "clk"}}), sinks, ["--cap", "3"])
    assert rc == 3 and not out.exists() and rep["over_cap"] == {"clk": 4}
    t2 = tmp_path / "r2"; t2.mkdir()
    rc, out, rep = _run(t2, _clock(tap_group={"re": "^(u_c)[/.]", "fixed_taps": {"u_c": "clk_t1"}}), sinks)
    assert rc == 3 and rep["pinned_bad"]
    t3 = tmp_path / "r3"; t3.mkdir()
    rc, out, rep = _run(t3, _clock(), [("a", 10.0, 0.0), ("b", 10.0, 200.0), ("c", 150.0, 200.0)], ["--reach", "1000"])
    assert rc == 3 and rep["over_span"]


def test_main_exit4_refusals(tmp_path):
    sinks = S("u_k", 2, 10.0, 0.0) + [("u_k.flat", 12.0, 0.0)]
    rc, out, rep = _run(tmp_path, _clock(), sinks)                                      # regex would swallow a flat descendant
    assert rc == 4 and rep["swallowed_sinks"] == 1 and not out.exists()
    t2 = tmp_path / "r2"; t2.mkdir()
    rc, out, rep = _run(t2, _clock(tap_mode="sinks"), S("u_a", 2, 10.0, 0.0))             # unmodelled tap mode
    assert rc == 4 and rep is None and not out.exists()
    t3 = tmp_path / "r3"; t3.mkdir()
    rc, out, rep = _run(t3, _clock(tap_group={"re": "(?:^|[/.])(u_x)[/.]"}), S("u_a", 2, 10.0, 0.0))   # existing re the model cannot reproduce
    assert rc == 4 and rep is None and not out.exists()
    t4 = tmp_path / "r4"; t4.mkdir()
    rc, out, rep = _run(t4, _clock(), [("solo", 10.0, 0.0)], ["--min-cohort", "2"])     # nothing to pin: no empty group is written
    import json
    assert rc == 0 and "tap_group" not in json.loads(out.read_text())["partition_types"]["t"]["clock"]


def test_main_addtaps_runs_on_overspan_alone_and_refuses_nonliteral_re(tmp_path):
    rc, out, rep = _run(tmp_path, _clock(), [("a", 10.0, 0.0), ("b", 10.0, 200.0), ("c", 150.0, 200.0)], ["--reach", "1000", "--add-taps", "4"])
    assert rc == 0 and rep["added_taps"] and not rep["over_span"], rep
    t2 = tmp_path / "r2"; t2.mkdir()
    rc, out, rep = _run(t2, _clock(tap_group={"re": "^(u_s\\d)[/.]", "fixed_taps": {}}), S("u_a", 2, 10.0, 0.0))
    assert rc == 4 and rep is None and not out.exists()
    t3 = tmp_path / "r3"; t3.mkdir()
    rc, out, rep = _run(t3, _clock(taps=[]), S("u_a", 2, 10.0, 0.0))
    assert rc == 4 and rep is None


def _main_on(m):
    """run the main()-level checks against a mutated module"""
    global T
    keep, T = T, m
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            test_main_addtaps_runs_on_overspan_alone_and_refuses_nonliteral_re(Path(d))
    finally:
        T = keep
    return True


def test_main_renumbers_added_taps_after_dropping_an_empty_one(tmp_path):
    """a legalizer that displaces the first proposed site leaves clk_t2 empty: it is dropped and the survivor renumbered clk_t2 (bind needs consecutive names)"""
    import json
    stub = STUB_SPLIT.replace("def explicit_legalize(tile, x, y, taken):\n    return (x, y)",
                              "CALLS = [0]\ndef explicit_legalize(tile, x, y, taken):\n    CALLS[0] += 1\n    return (x, y + 900.0) if CALLS[0] == 1 else (x, y)")
    tools = tmp_path / "tools"; tools.mkdir()
    (tools / "schema.py").write_text(STUB_SCHEMA); (tools / "tap_split.py").write_text(stub)
    (tools / "reach_fix.py").write_text(STUB_RF); (tools / "row_normalize.py").write_text(STUB_RN)
    plan = tmp_path / "plan.json"; plan.write_text(json.dumps({"partition_types": {"t": {"clock": _clock()}}}))
    tsv = tmp_path / "s.tsv"; tsv.write_text("".join(f"clk\t{i}\tDFF\t{x}\t{y}\n" for i, x, y in [("a", 1500.0, 0.0), ("b", 1501.0, 5.0), ("c", 3000.0, 0.0)]))
    for m in ("schema", "tap_split"):
        sys.modules.pop(m, None)
    rc = T.main([str(plan), "t", str(tsv), "--tools", str(tools), "--out", str(tmp_path / "o.json"), "--report", str(tmp_path / "r.json"), "--add-taps", "4"])
    for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
        sys.modules.pop(m, None)
    taps = [x["name"] for x in json.loads((tmp_path / "o.json").read_text())["partition_types"]["t"]["clock"]["taps"]] if rc == 0 else []
    nums = [int(n[5:]) for n in taps if n.startswith("clk_t")]
    assert rc == 0 and nums == list(range(1, len(nums) + 1)), (rc, taps)


def _renum_on(m):
    global T
    keep, T = T, m
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            test_main_renumbers_added_taps_after_dropping_an_empty_one(Path(d))
    finally:
        T = keep
    return True


def test_oversize_cohort_is_split_and_tie_order_numeric():
    big = [(f"u_big/q{i}", 10.0 + 40 * i, 0.0) for i in range(10)]          # own box 360 > span 300
    taps2 = [("clk", 0.0, 0.0), ("clk_t1", 400.0, 0.0)]
    off = T.assign(big, taps2, reach=250, span=300, cap=100)                 # default off: the cohort stays whole and is unassigned
    assert off["split_cohorts"] == [] and off["unassigned"]
    r = T.assign(big, taps2, reach=250, span=300, cap=100, split_oversize=True)
    assert [c["cohort"] for c in r["split_cohorts"]] == ["u_big"] and "u_big" not in r["fixed"] and len(r["singles"]) == 10
    assert not r["unassigned"]
    rp = T.split_report(r["split_cohorts"], r["singles"])[0]
    assert rp["taps_used"] == 2 and rp["adjacent_pairs_on_different_taps_PROXY"] == 1 and rp["adjacent_pairs"] == 9 and "UNMEASURED" in rp["related_pairs"]
    assert T.assign(big, [("clk", 0.0, 0.0)], 1000, 300, 100, pinned={"u_big": "clk"}, split_oversize=True)["split_cohorts"] == []
    taps = [("clk_t10", 100.0, 0.0), ("clk_t5", -100.0, 0.0)]
    assert T.assign([("s", 0.0, 0.0)], taps, 1000, 300, 100)["singles"] == {"s": "clk_t5"}


def _split_on(m):
    global T
    keep, T = T, m
    try:
        test_oversize_cohort_is_split_and_tie_order_numeric()
    finally:
        T = keep
    return True


def test_split_respects_plan_re_keys_and_recomputes_membership():
    big = [(f"big/q{i}", 10.0 + 40 * i, 0.0) for i in range(10)]
    taps2 = [("clk", 0.0, 0.0), ("clk_t1", 400.0, 0.0)]
    # a key of the plan's own re is never split (CTS would still capture it whole)
    r = T.assign(big, taps2, 250, 300, 100, re_keys=["big"], split_oversize=True)
    assert r["split_cohorts"] == [] and r["unassigned"], r
    # a demoted key whose sinks a shorter key would now capture is refused through `swallowed`, not silently modelled as singles
    sinks = [("a/q0", 10.0, 0.0), ("a/q1", 12.0, 0.0), ("a.b/x", 0.0, 0.0), ("a.b/y", 400.0, 0.0), ("a.b/z", 200.0, 200.0)]
    r = T.assign(sinks, [("clk", 0.0, 0.0), ("clk_t1", 400.0, 0.0)], 1000, 300, 100, pinned={"a": "clk"}, min_cohort=2, split_oversize=True)
    assert sorted(r["swallowed"]) == ["a.b/x", "a.b/y", "a.b/z"], r["swallowed"]


def _split2_on(m):
    global T
    keep, T = T, m
    try:
        test_split_respects_plan_re_keys_and_recomputes_membership()
    finally:
        T = keep
    return True


STUB_RF = '''
def _freeze_reset_consumers(P, tn, t, rec, rnd=0):
    t.setdefault("reset", {})["consumer_sites_um"] = [["clk", 0.0, 0.0]]
    rec["changes"].append(["reset.consumer_sites_um", rnd, 1])
'''
STUB_RN = '''
import contextlib
@contextlib.contextmanager
def in_tree(p):
    yield
'''


def _run_freeze(tmp_path, extra):
    import json
    tools = tmp_path / "tools"; tools.mkdir()
    for n, src in (("schema", STUB_SCHEMA), ("tap_split", STUB_SPLIT), ("reach_fix", STUB_RF), ("row_normalize", STUB_RN)):
        (tools / f"{n}.py").write_text(src)
    plan = tmp_path / "plan.json"; plan.write_text(json.dumps({"partition_types": {"t": {"clock": _clock()}}}))
    tsv = tmp_path / "s.tsv"; tsv.write_text("".join(f"clk\t{i}\tDFF\t{x}\t{y}\n" for i, x, y in S("u_far", 3, 1500.0, 0.0)))
    out, rep = tmp_path / "o.json", tmp_path / "r.json"
    for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
        sys.modules.pop(m, None)
    rc = T.main([str(plan), "t", str(tsv), "--tools", str(tools), "--out", str(out), "--report", str(rep), "--add-taps", "3", *extra])
    for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
        sys.modules.pop(m, None)
    if str(tools) in sys.path:
        sys.path.remove(str(tools))
    return rc, json.loads(out.read_text())["partition_types"]["t"], json.loads(rep.read_text())


def test_main_freezes_reset_consumers_by_default_and_logs_opt_out(tmp_path):
    rc, t, rep = _run_freeze(tmp_path, [])
    assert rc == 0 and t["reset"]["consumer_sites_um"] == [["clk", 0.0, 0.0]] and rep["reset_freeze"]["frozen"] is True
    t2 = tmp_path / "r2"; t2.mkdir()
    rc, t, rep = _run_freeze(t2, ["--no-freeze"])
    assert rc == 0 and "reset" not in t and rep["reset_freeze"] == {"frozen": False, "opted_out": True}


def _freeze_on(m):
    global T
    keep, T = T, m
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            test_main_freezes_reset_consumers_by_default_and_logs_opt_out(Path(d))
    finally:
        T = keep
    return True


def test_main_failed_freeze_exits_5_and_writes_nothing(tmp_path):
    import json
    global STUB_RF
    keep = STUB_RF
    STUB_RF = '''
def _freeze_reset_consumers(P, tn, t, rec, rnd=0):
    rec.setdefault("notes", []).append("reset consumers not frozen: boom")
'''
    try:
        tools = tmp_path / "tools"; tools.mkdir()
        for n, src in (("schema", STUB_SCHEMA), ("tap_split", STUB_SPLIT), ("reach_fix", STUB_RF), ("row_normalize", STUB_RN)):
            (tools / f"{n}.py").write_text(src)
        plan = tmp_path / "plan.json"; plan.write_text(json.dumps({"partition_types": {"t": {"clock": _clock()}}}))
        tsv = tmp_path / "s.tsv"; tsv.write_text("".join(f"clk\t{i}\tDFF\t{x}\t{y}\n" for i, x, y in S("u_far", 3, 1500.0, 0.0)))
        out, rep = tmp_path / "o.json", tmp_path / "r.json"
        for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
            sys.modules.pop(m, None)
        rc = T.main([str(plan), "t", str(tsv), "--tools", str(tools), "--out", str(out), "--report", str(rep), "--add-taps", "3"])
        assert rc == 5 and not out.exists() and json.loads(rep.read_text())["reset_freeze"]["record"]["notes"]
        for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
            sys.modules.pop(m, None)
        (tools / "reach_fix.py").write_text(STUB_RF)
        rc = T.main([str(plan), "t", str(tsv), "--tools", str(tools), "--out", str(out), "--report", str(rep), "--add-taps", "3", "--no-freeze"])
        assert rc == 0 and out.exists()                           # the explicit opt-out still writes
    finally:
        STUB_RF = keep
        for m in ("schema", "tap_split", "reach_fix", "row_normalize"):
            sys.modules.pop(m, None)
        if str(tools) in sys.path:
            sys.path.remove(str(tools))


def _ffail_on(m):
    global T
    keep, T = T, m
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            test_main_failed_freeze_exits_5_and_writes_nothing(Path(d))
    finally:
        T = keep
    return True
