"""pytest: REF-SITE resolves name / index references to xy (QC sle_sc_v3 seam index crossing the tap count)."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_site as RS  # noqa: E402


def _grid(n, far=None):
    g = [("clk", 0.0, 0.0)] + [(f"clk_t{i}", 10.0 * i, 0.0) for i in range(1, n)]
    if far is not None:
        g[far] = (g[far][0], 1184.0, 0.0)
    return g


def _plan(node="rst_n_t4"):
    return {"partition_types": {"A": {"clock": {"landing_contract": {
        "collector_children": [{"name": "c0", "node": node, "status_pins_xy_um": [[5.0, 0.0], [6.0, 0.0]]}],
        "collector_tree": {"relays": [{"q": "rst_n_t1", "xy": [0, 0], "d": "rst_root_n"}]}},
        "landing_raw_branches": [{"name": "b", "stages": [{"original": "rst_n_t1", "xy_um": [3000.0, 0.0]}]}]}}}}


def _with_grid(monkeypatch, n, far=None):
    monkeypatch.setitem(sys.modules, "schema", types.SimpleNamespace(tap_grid=lambda P, tn: _grid(n, far)))


def test_index_refs_skip_collector_tree_and_label_by_name():
    refs = RS.index_refs(_plan()["partition_types"]["A"])
    paths = sorted(p for p, *_ in refs)
    assert paths == [".clock.landing_contract.collector_children[c0].node", ".clock.landing_raw_branches[b].stages[0].original"]


def test_seam_index_then_tap_after_tap_count_grows(monkeypatch):
    raw = _plan()
    _with_grid(monkeypatch, 4)                       # 4 taps: index 4 = seam output 0 (unsited)
    old, n0 = RS.type_refs(None, raw, "A")
    k = ".clock.landing_contract.collector_children[c0].node"
    assert n0 == 4 and old[k][0] == "seam"
    _with_grid(monkeypatch, 6, far=4)                # 6 taps: index 4 is now clock tap 4, 1184 um away
    new, n1 = RS.type_refs(None, raw, "A")
    assert new[k][0] == "reset" and new[k][2] == (1184.0, 0.0)
    rr = RS.reach_rows(new, 405.0)
    assert [r[0] for r in rr] == [k] and rr[0][2] > 1100       # transport stage (3000 um, by design) is not a REACH row
    mv, kind = RS.moved_rows(new, old)
    assert kind and kind[0][0] == k and kind[0][3] == "reset" and kind[0][4] > 1100


def test_moved_site_and_same_site(monkeypatch):
    raw = _plan("rst_n_t2")
    _with_grid(monkeypatch, 4)
    a, _ = RS.type_refs(None, raw, "A")
    _with_grid(monkeypatch, 4, far=2)
    b, _ = RS.type_refs(None, raw, "A")
    mv, kind = RS.moved_rows(b, a)
    assert [m[0] for m in mv] == [".clock.landing_contract.collector_children[c0].node"] and not kind
    assert RS.moved_rows(a, a) == ([], [])


def test_adv_ref_site_never_raises():
    import adv_ref_site as A
    assert A.findings(None, "p")[0].startswith("WARN ADV-REF-SITE")


_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata")


def _fixture(name):
    import json
    with open(os.path.join(_DATA, name)) as f:
        return json.load(f)


def _site(grid, name):
    return next((x, y) for n, x, y in grid if n == name)


def test_kv_a5t3_seam_index_rekeyed_by_site_on_compose():
    """KV A5t3 vs D29 (COORD 11-24): hub_Ei 89 -> 99 taps kept rst_n_t97 (seam output 8, now clock tap 97, 2053 um away);
    pv_v1n 150 -> 320 kept rst_n_t151 (seam output 1).  reindex re-keys them to n_new + j; a stage on a real tap follows its site."""
    import copy
    fx = _fixture("refsite_kv_a5t3.json")
    for tn, seam_old, seam_new in (("kv3_hub_Ei", "rst_n_t97", "rst_n_t107"), ("kv3_pv_v1n", "rst_n_t151", "rst_n_t321")):
        v = fx[tn]
        old, new = [tuple(g) for g in v["old"]], [tuple(g) for g in v["new"]]
        t = copy.deepcopy(v["type"])
        before = {p: val for p, val, *_ in RS.index_refs(t)}
        ch = RS.reindex_type(t, old, new)
        after = {p: val for p, val, *_ in RS.index_refs(t)}
        seam = [p for p, val in before.items() if val == seam_old]
        assert seam and all(after[p] == seam_new for p in seam)
        ctl = [p for p in before if "ctl_" in p]
        assert ctl
        for p in ctl:
            i = int(before[p].split("_t")[-1])
            o = next((x, y) for n, x, y in old if RS.tap_index(n) == i)
            j = int(after[p].split("_t")[-1])
            nxy = next((x, y) for n, x, y in new if RS.tap_index(n) == j)
            best = min(abs(x - o[0]) + abs(y - o[1]) for n, x, y in new)
            assert abs(nxy[0] - o[0]) + abs(nxy[1] - o[1]) == best          # re-keyed to the new tap nearest its old site
        assert len(ch) >= len(seam)


def test_qc_c1g_sle_sc_v3_stale_seam_index_is_reach_and_reindexes(monkeypatch):
    """QC C1g sle_sc_v3 (FABLE-RC-QC 02:49): collector_children node rst_n_t69 was seam output 0 with 69 taps; at 73 taps it is
    clock tap 69, 1184 um from its monitors (-241 ps).  REACH flags it with no baseline; a compose re-key from the 69-tap set
    (taps 69..72 appended) moves it to the seam output rst_n_t73."""
    import copy
    v = _fixture("refsite_qc_c1g_sc3.json")["sle_sc_v3"]
    grid = [tuple(g) for g in v["grid"]]
    monkeypatch.setitem(sys.modules, "schema", types.SimpleNamespace(tap_grid=lambda P, tn: grid))
    raw = {"partition_types": {"sle_sc_v3": copy.deepcopy(v["type"])}}
    refs, n = RS.type_refs(None, raw, "sle_sc_v3")
    rr = RS.reach_rows(refs, 405.0)
    assert n == 73 and len(rr) == 2 and all(r[1] == "rst_n_t69" and 1150 < r[2] < 1220 for r in rr)
    t = copy.deepcopy(v["type"])
    old = [g for g in grid if RS.tap_index(g[0]) is None or RS.tap_index(g[0]) < 69]
    RS.reindex_type(t, old, grid)
    assert [c["node"] for c in t["clock"]["landing_contract"]["collector_children"]] == ["rst_n_t73", "rst_n_t73"]


def test_cli_runs_under_isolated_mode():
    """python3 -I drops the script folder from sys.path (KV-ALLFIX 25a62dbff7): both CLIs must still import their siblings."""
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    for script, args in (("ref_site.py", ["reindex", "--help"]), ("ref_site.py", ["--help"]), ("tap_site.py", ["--help"])):
        r = subprocess.run([sys.executable, "-I", os.path.join(here, script)] + args, cwd="/", capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, (script, r.stderr[-400:])
