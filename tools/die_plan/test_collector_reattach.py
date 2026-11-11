"""DIE-QC-97 REMAP-REATTACH 11-10: collector sources follow a re-picked reset relay; reach misses fail closed."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collector_reattach as CR  # noqa: E402


def _tree(t1_xy):
    # root -> rst_rl_0 (depth 1) -> leaf taps rst_n_t0 / rst_n_t1 (depth 2)
    return {"root": [0.0, 0.0], "depth": 2,
            "relays": [{"q": "rst_rl_0", "d": "rst_root_n", "xy": [200.0, 0.0], "depth": 1},
                       {"q": "rst_n_t0", "d": "rst_rl_0", "xy": [300.0, 100.0], "depth": 2},
                       {"q": "rst_n_t1", "d": "rst_rl_0", "xy": list(t1_xy), "depth": 2}]}


def _lcd(tree, sources):
    return {"collector_tree": tree, "collector_root_node": "rst_root_n", "collector_local_sources": sources,
            "collector_children": []}


def _plan(tree, sources):
    # "other" carries the same (unchanged) tree in every plan of a test
    return {"partition_types": {"ctl": {"clock": {"landing_contract": _lcd(tree, sources)}},
                                "other": {"clock": {"landing_contract": _lcd(_tree([450.0, 0.0]),
                                                                              [dict(SRC[0])])}}}}


SRC = [{"name": "cws1_i", "xy_um": [500.0, 0.0], "tap": 1}]


def test_sources_follow_repicked_relay():
    base = _plan(_tree([450.0, 0.0]), copy.deepcopy(SRC))       # cws1_i 50 um from rst_n_t1
    cand = _plan(_tree([0.0, 900.0]), copy.deepcopy(SRC))       # re-pick moved rst_n_t1 far away; name kept
    # without reattach the stale name is out of reach (the cand21b bind failure)
    assert CR.source_hops(cand["partition_types"]["ctl"]["clock"]["landing_contract"])[0][2] > 405
    rep = CR.reattach_plan(base, cand)
    src = cand["partition_types"]["ctl"]["clock"]["landing_contract"]["collector_local_sources"][0]
    assert src["node"] == "rst_n_t0" and src["tap"] == 0                       # nearest same-depth relay
    assert rep["over"] == {} and rep["reattached"]["ctl"]["added_collector_cycles"] == 0
    assert rep["reattached"]["ctl"]["moved"][0]["old_node"] == "rst_n_t1"
    assert "other" not in rep["reattached"]                                    # unchanged tree untouched


def test_unchanged_plan_byte_identical(tmp_path):
    p = _plan(_tree([450.0, 0.0]), copy.deepcopy(SRC))
    b = tmp_path / "b.json"; b.write_text(json.dumps(p, indent=1) + "\n")
    out, rep = tmp_path / "o.json", tmp_path / "r.json"
    assert CR.main([str(b), str(b), str(out), str(rep)]) == 0
    assert out.read_bytes() == b.read_bytes()


def test_no_relay_in_reach_fails_closed(tmp_path):
    base = _plan(_tree([450.0, 0.0]), copy.deepcopy(SRC))
    far = _tree([0.0, 900.0]); far["relays"][1]["xy"] = [0.0, 1200.0]          # both depth-2 relays out of reach
    cand = _plan(far, copy.deepcopy(SRC))
    b, c = tmp_path / "b.json", tmp_path / "c.json"
    b.write_text(json.dumps(base)); c.write_text(json.dumps(cand))
    out, rep = tmp_path / "o.json", tmp_path / "r.json"
    assert CR.main([str(b), str(c), str(out), str(rep)]) == 1 and not out.exists()


def test_stale_source_on_unchanged_tree_is_reported(tmp_path):
    bad = _plan(_tree([0.0, 900.0]), copy.deepcopy(SRC))
    b = tmp_path / "b.json"; b.write_text(json.dumps(bad))
    out, rep = tmp_path / "o.json", tmp_path / "r.json"
    assert CR.main([str(b), str(b), str(out), str(rep)]) == 1
    assert json.loads(rep.read_text())["over"]["ctl"][0][0] == "cws1_i"


def _side(sources):
    return {"collector": {"types": {"ctl": {"tree": _tree([450.0, 0.0]), "local_sources": sources, "children": []},
                                    "other": {"tree": _tree([450.0, 0.0]), "local_sources": [dict(SRC[0])],
                                              "children": []}}}}


def _files(tmp_path, base, cand, side):
    b, c, si = tmp_path / "b.json", tmp_path / "c.json", tmp_path / "s.json"
    b.write_text(json.dumps(base)); c.write_text(json.dumps(cand)); si.write_text(json.dumps(side, indent=1) + "\n")
    return b, c, si


def test_sidecar_sources_follow(tmp_path):
    # the bind reads the sources from the sidecar: a10 failed on the stale sidecar copy after the plan was fixed
    base = _plan(_tree([450.0, 0.0]), copy.deepcopy(SRC))
    cand = _plan(_tree([0.0, 900.0]), copy.deepcopy(SRC))
    side = _side(copy.deepcopy(SRC))
    b, c, si = _files(tmp_path, base, cand, side)
    out, rep, so = tmp_path / "o.json", tmp_path / "r.json", tmp_path / "so.json"
    assert CR.main([str(b), str(c), str(out), str(rep), "--sidecar", str(si), str(so)]) == 0
    got = json.loads(so.read_text())["collector"]["types"]
    assert got["ctl"]["local_sources"][0]["node"] == "rst_n_t0" and got["ctl"]["local_sources"][0]["tap"] == 0
    assert got["other"] == side["collector"]["types"]["other"]                # untouched type unchanged
    assert json.loads(rep.read_text())["sidecar_changed"] == {"ctl": 2}
    so2 = tmp_path / "so2.json"                                                # no reattach -> byte-identical
    assert CR.main([str(b), str(b), str(out), str(rep), "--sidecar", str(si), str(so2)]) == 0
    assert so2.read_bytes() == si.read_bytes()


def test_sidecar_name_mismatch_fails_closed(tmp_path):
    base = _plan(_tree([450.0, 0.0]), copy.deepcopy(SRC))
    cand = _plan(_tree([0.0, 900.0]), copy.deepcopy(SRC))
    b, c, si = _files(tmp_path, base, cand, _side([dict(SRC[0], name="zz_i")]))
    out, rep, so = tmp_path / "o.json", tmp_path / "r.json", tmp_path / "so.json"
    assert CR.main([str(b), str(c), str(out), str(rep), "--sidecar", str(si), str(so)]) == 1
    assert not out.exists() and not so.exists()


def test_rerooted_collector_keeps_root_site():
    # root = local relay rst_n_t1 (an up-link source); the new tree renames the relay at that site rst_n_t0
    def rooted(tree):
        p = _plan(tree, [{"name": "cws1_i", "xy_um": [300.0, 450.0], "tap": 0}])
        p["partition_types"]["ctl"]["clock"]["landing_contract"]["collector_root_node"] = "rst_n_t1"
        return p
    base = rooted(_tree([450.0, 0.0]))
    nt = _tree([300.0, 100.0]); nt["relays"][1]["xy"] = [455.0, 0.0]          # t0 <-> t1 sites swapped (5 um off)
    cand = rooted(nt)
    rep = CR.reattach_plan(base, cand)
    lc = cand["partition_types"]["ctl"]["clock"]["landing_contract"]
    assert lc["collector_root_node"] == "rst_n_t0"
    assert rep["reattached"]["ctl"]["rerooted"]["shift_um"] == 5.0
    assert lc["collector_local_sources"][0]["node"] == "rst_n_t1"              # source follows its site too
    side = {"collector": {"types": {"ctl": {"local_sources": [{"name": "cws1_i", "tap": 0}], "children": [],
                                            "collector_root_node": "rst_n_t1", "collector_root_xy": [450.0, 0.0]}}}}
    CR.sync_sidecar(cand, side, ["ctl"])
    row = side["collector"]["types"]["ctl"]
    assert row["collector_root_node"] == "rst_n_t0" and row["collector_root_xy"] == [450.0, 0.0]


def test_reroot_out_of_reach_fails():
    base = _plan(_tree([450.0, 0.0]), copy.deepcopy(SRC))
    base["partition_types"]["ctl"]["clock"]["landing_contract"]["collector_root_node"] = "rst_n_t1"
    far = _tree([0.0, 900.0]); far["relays"][1]["xy"] = [0.0, 1200.0]
    cand = _plan(far, copy.deepcopy(SRC))
    cand["partition_types"]["ctl"]["clock"]["landing_contract"]["collector_root_node"] = "rst_n_t1"
    try:
        CR.reattach_plan(base, cand)
    except ValueError as e:
        assert "collector root rst_n_t1" in str(e)
    else:
        raise AssertionError("expected a reach failure")


if __name__ == "__main__":
    import tempfile
    for n, f in sorted(globals().items()):
        if n.startswith("test_"):
            if f.__code__.co_argcount:
                with tempfile.TemporaryDirectory() as d:
                    f(Path(d))
            else:
                f()
            print("PASS", n)
