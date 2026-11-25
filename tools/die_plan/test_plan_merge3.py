"""QC-CB-C1L: plan_merge3 composes disjoint rows, merges id-keyed lists element-wise, and stops on a same-leaf conflict."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_merge3 as M


def _base():
    return {"partition_types": {"st_a": {"hard_cores": [{"inst": "u_c0", "x": 1, "pg_halo_um": 0},
                                                        {"inst": "u_c1", "x": 2}],
                                         "relay_sites": {"a": [1, 2]}},
                                "st_b": {"clock": {"added_taps": [{"name": "t1"}]}}},
            "lanes": [1, 2]}


def _w(tmp, name, obj):
    p = tmp / name
    p.write_text(json.dumps(obj))
    return str(p)


def test_different_cores_merge(tmp_path):
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["hard_cores"][0]["x"] = 5          # row A: core u_c0
    b["partition_types"]["st_a"]["hard_cores"][1]["pg_halo_um"] = 2  # row B: core u_c1 (new key)
    out = tmp_path / "o.json"
    rc = M.main([_w(tmp_path, "b.json", _base()), str(out), _w(tmp_path, "a.json", a) + ":A", _w(tmp_path, "r.json", b) + ":B"])
    assert rc == 0
    hc = json.loads(out.read_text())["partition_types"]["st_a"]["hard_cores"]
    assert hc == [{"inst": "u_c0", "x": 5, "pg_halo_um": 0}, {"inst": "u_c1", "x": 2, "pg_halo_um": 2}]


def test_same_core_different_fields_merge():
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["hard_cores"][0]["x"] = 5
    b["partition_types"]["st_a"]["hard_cores"][0]["pg_halo_um"] = 3
    res, _ = M.merge(_base(), [("A", a), ("B", b)])
    assert res["partition_types"]["st_a"]["hard_cores"][0] == {"inst": "u_c0", "x": 5, "pg_halo_um": 3}


def test_same_core_same_field_conflicts(tmp_path, capsys):
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["hard_cores"][0]["x"] = 5
    b["partition_types"]["st_a"]["hard_cores"][0]["x"] = 7
    rc = M.main([_w(tmp_path, "b.json", _base()), str(tmp_path / "o.json"), _w(tmp_path, "a.json", a) + ":A",
                 _w(tmp_path, "r.json", b) + ":B"])
    assert rc == 2
    assert "CONFLICT partition_types/st_a/hard_cores/inst=u_c0/x rows A B" in capsys.readouterr().out


def test_identical_values_merge_and_removal():
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["relay_sites"]["a"] = [3, 4]
    b["partition_types"]["st_a"]["relay_sites"]["a"] = [3, 4]          # same value from two rows: fine
    del b["partition_types"]["st_b"]["clock"]["added_taps"]            # removal is a delta too
    res, rep = M.merge(_base(), [("A", a), ("B", b)])
    assert res["partition_types"]["st_a"]["relay_sites"]["a"] == [3, 4]
    assert "added_taps" not in res["partition_types"]["st_b"]["clock"]
    assert rep["B"]["n"] == 2


def test_subtree_replace_conflicts():
    a, b = _base(), _base()
    a["partition_types"]["st_b"]["clock"]["added_taps"][0]["site"] = [1, 1]   # edit inside the element
    b["partition_types"]["st_b"]["clock"] = {"tap_mode": "grid"}               # replace the subtree
    try:
        M.merge(_base(), [("A", a), ("B", b)])
    except M.Conflict as e:
        assert "rows A B" in str(e)
    else:
        raise AssertionError("expected a conflict")


def test_member_change_is_whole_list_and_whole_lists_flag():
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["hard_cores"].append({"inst": "u_c2", "x": 3})   # member added: whole list
    b["partition_types"]["st_a"]["hard_cores"][0]["x"] = 9
    try:
        M.merge(_base(), [("A", a), ("B", b)])
    except M.Conflict:
        pass
    else:
        raise AssertionError("expected a conflict on a whole-list leaf")
    c, d = _base(), _base()
    c["partition_types"]["st_a"]["hard_cores"][0]["x"] = 5
    d["partition_types"]["st_a"]["hard_cores"][1]["x"] = 6
    try:
        M.merge(_base(), [("C", c), ("D", d)], keyed=False)
    except M.Conflict:
        pass
    else:
        raise AssertionError("--whole-lists keeps lists as one leaf")


def test_output_key_order_reproducible(tmp_path):
    a = _base()
    a["partition_types"]["st_a"]["new_b"] = 1
    a["partition_types"]["st_a"]["new_a"] = 2
    o1, o2 = tmp_path / "1.json", tmp_path / "2.json"
    for o in (o1, o2):
        assert M.main([_w(tmp_path, "b.json", _base()), str(o), _w(tmp_path, "a.json", a) + ":A"]) == 0
    assert o1.read_bytes() == o2.read_bytes()
    assert list(json.loads(o1.read_text())["partition_types"]["st_a"])[-2:] == ["new_b", "new_a"]
