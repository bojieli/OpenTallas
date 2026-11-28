"""QC-CB-C1L: plan_merge3 composes disjoint rows, merges id-keyed lists element-wise, and stops on a same-leaf conflict."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_merge3 as M

B = M.BASE_ANC


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
    rc = M.main([_w(tmp_path, "b.json", _base()), str(out), _w(tmp_path, "a.json", a) + ":A@base", _w(tmp_path, "r.json", b) + ":B@base"])
    assert rc == 0
    hc = json.loads(out.read_text())["partition_types"]["st_a"]["hard_cores"]
    assert hc == [{"inst": "u_c0", "x": 5, "pg_halo_um": 0}, {"inst": "u_c1", "x": 2, "pg_halo_um": 2}]


def test_same_core_different_fields_merge():
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["hard_cores"][0]["x"] = 5
    b["partition_types"]["st_a"]["hard_cores"][0]["pg_halo_um"] = 3
    res, _ = M.merge(_base(), [("A", a, B), ("B", b, B)])
    assert res["partition_types"]["st_a"]["hard_cores"][0] == {"inst": "u_c0", "x": 5, "pg_halo_um": 3}


def test_same_core_same_field_conflicts(tmp_path, capsys):
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["hard_cores"][0]["x"] = 5
    b["partition_types"]["st_a"]["hard_cores"][0]["x"] = 7
    rc = M.main([_w(tmp_path, "b.json", _base()), str(tmp_path / "o.json"), _w(tmp_path, "a.json", a) + ":A@base",
                 _w(tmp_path, "r.json", b) + ":B@base"])
    assert rc == 2
    assert "CONFLICT partition_types/st_a/hard_cores/inst=u_c0/x rows A B" in capsys.readouterr().out


def test_identical_values_merge_and_removal():
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["relay_sites"]["a"] = [3, 4]
    b["partition_types"]["st_a"]["relay_sites"]["a"] = [3, 4]          # same value from two rows: fine
    del b["partition_types"]["st_b"]["clock"]["added_taps"]            # removal is a delta too
    res, rep = M.merge(_base(), [("A", a, B), ("B", b, B)])
    assert res["partition_types"]["st_a"]["relay_sites"]["a"] == [3, 4]
    assert "added_taps" not in res["partition_types"]["st_b"]["clock"]
    assert rep["B"]["n"] == 2


def test_subtree_replace_conflicts():
    a, b = _base(), _base()
    a["partition_types"]["st_b"]["clock"]["added_taps"][0]["site"] = [1, 1]   # edit inside the element
    b["partition_types"]["st_b"]["clock"] = {"tap_mode": "grid"}               # replace the subtree
    try:
        M.merge(_base(), [("A", a, B), ("B", b, B)])
    except M.Conflict as e:
        assert "rows A B" in str(e)
    else:
        raise AssertionError("expected a conflict")


def test_member_change_is_whole_list_and_whole_lists_flag():
    a, b = _base(), _base()
    a["partition_types"]["st_a"]["hard_cores"].append({"inst": "u_c2", "x": 3})   # member added: whole list
    b["partition_types"]["st_a"]["hard_cores"][0]["x"] = 9
    try:
        M.merge(_base(), [("A", a, B), ("B", b, B)])
    except M.Conflict:
        pass
    else:
        raise AssertionError("expected a conflict on a whole-list leaf")
    c, d = _base(), _base()
    c["partition_types"]["st_a"]["hard_cores"][0]["x"] = 5
    d["partition_types"]["st_a"]["hard_cores"][1]["x"] = 6
    try:
        M.merge(_base(), [("C", c, B), ("D", d, B)], keyed=False)
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
        assert M.main([_w(tmp_path, "b.json", _base()), str(o), _w(tmp_path, "a.json", a) + ":A@base"]) == 0
    assert o1.read_bytes() == o2.read_bytes()
    assert list(json.loads(o1.read_text())["partition_types"]["st_a"])[-2:] == ["new_b", "new_a"]


# C-MERGE3-BASE-HIDES-FORK-CONFLICT: the hd_lep0N case.  EAST forked at W11; W11 -> W12f moved the
# strap_ca_k_coll_i3 sites to the x=1058.4 column while EAST kept its r6 seats.  Against BASE=W12f alone the EAST
# value looked like a row-only edit and won silently.
_STRAPS = ("strap_ca_k_coll_i3", "strap_ca_k_lepf_i0", "strap_ca_k_lepk_i0", "strap_ca_k_unit_i0")


def _strap_plan(sites, extra=None):
    t = {"count_straps": [{"name": n, "sites_um": [list(s) for s in sites[n]]} for n in _STRAPS],
         "relay_sites": {"g33": [720.58, 587.25]}}
    t.update(extra or {})
    return {"partition_types": {"hd_lep0N": t}}


def _fork_case():
    w11 = {n: [[1000.0 + i, 900.0]] for i, n in enumerate(_STRAPS)}
    w12f = {n: [[1058.4, 889.92 + i]] for i, n in enumerate(_STRAPS)}
    east = {n: [[978.264 + i, 1006.92]] for i, n in enumerate(_STRAPS)}
    anc = _strap_plan(w11)
    base = _strap_plan(w12f, {"base_only": 1})
    row = _strap_plan(east)
    row["partition_types"]["hd_lep0N"]["relay_sites"]["g33"] = [720.576, 581.85]   # a genuine row-only edit
    return anc, base, row


def test_fork_ancestor_exposes_hidden_strap_conflict(tmp_path, capsys):
    anc, base, row = _fork_case()
    res, _ = M.merge(base, [("EAST", row, B)])            # the old (BASE-only) delta: EAST wins silently
    assert res["partition_types"]["hd_lep0N"]["count_straps"][0]["sites_um"] == [[978.264, 1006.92]]
    rc = M.main([_w(tmp_path, "b.json", base), str(tmp_path / "o.json"),
                 _w(tmp_path, "e.json", row) + ":EAST@" + _w(tmp_path, "w11.json", anc)])
    assert rc == 2
    out = capsys.readouterr().out
    assert out.count("CONFLICT(fork)") == 4 and "relay_sites" not in out
    for n in _STRAPS:
        assert f"CONFLICT(fork) partition_types/hd_lep0N/count_straps/name={n}/sites_um rows BASE EAST" in out


def test_fork_ancestor_keeps_base_only_and_row_only_changes():
    anc, base, row = _fork_case()
    for s in row["partition_types"]["hd_lep0N"]["count_straps"]:     # row resolves the straps to the W12f values
        s["sites_um"] = next(b["sites_um"] for b in base["partition_types"]["hd_lep0N"]["count_straps"]
                             if b["name"] == s["name"])
    res, rep = M.merge(base, [("EAST", row, anc)])
    t = res["partition_types"]["hd_lep0N"]
    assert t["base_only"] == 1                                       # BASE-only change since the fork is kept
    assert t["relay_sites"]["g33"] == [720.576, 581.85]              # row-only change applied
    assert t["count_straps"] == base["partition_types"]["hd_lep0N"]["count_straps"]
    assert rep["EAST"]["fork"] is True


def test_row_without_fork_ancestor_refused(tmp_path, capsys):
    _, base, row = _fork_case()
    rc = M.main([_w(tmp_path, "b.json", base), str(tmp_path / "o.json"), _w(tmp_path, "e.json", row) + ":EAST"])
    assert rc == 3
    assert "REFUSE row" in capsys.readouterr().out


def test_fork_base_replaced_parent_conflicts_not_crash():
    anc = {"t": {"hard_cores": [{"inst": "u0", "x": 1}], "P": {"x": 1}, "Q": {"k": 1}}}
    base = {"t": {"hard_cores": [], "P": 5, "Q": {"k": 1}}}                  # BASE removed u0, retyped P
    row = {"t": {"hard_cores": [{"inst": "u0", "x": 1, "y": 2}], "P": {"x": 1, "y": 2}, "Q": {"k": 1}}}
    try:
        M.merge(base, [("R", row, anc)])
    except M.Conflict as e:
        assert str(e).count("CONFLICT(fork)") == 2 and "t/P/y" in str(e)
    else:
        raise AssertionError("expected CONFLICT(fork)")


def test_fork_conflicts_listed_for_all_rows():
    anc = {"a": 1, "b": 1, "c": 1}
    base = {"a": 2, "b": 2, "c": 1}
    try:
        M.merge(base, [("R1", {"a": 3, "b": 1, "c": 1}, anc), ("R2", {"a": 1, "b": 4, "c": 1}, anc)])
    except M.Conflict as e:
        assert "a rows BASE R1" in str(e) and "b rows BASE R2" in str(e)
    else:
        raise AssertionError("expected CONFLICT(fork)")


def test_refusals_dup_name_wrong_anc_and_2tuple(tmp_path, capsys):
    base = {"a": 1}
    bp, rp = _w(tmp_path, "b.json", base), _w(tmp_path, "r.json", {"a": 2})
    o = str(tmp_path / "o.json")
    assert M.main([bp, o, rp + ":R@base", rp + ":R@base"]) == 3
    assert M.main([bp, o, rp + ":BASE@base"]) == 3
    assert M.main([bp, o, rp + ":R@" + rp]) == 3                       # ANC == row: 0 leaves, wrong ancestor
    assert M.main([bp, o, rp + ":R@" + str(tmp_path / "nope.json")]) == 3
    assert capsys.readouterr().out.count("REFUSE") == 4
    try:
        M.merge(base, [("R", {"a": 2})])
    except ValueError:
        pass
    else:
        raise AssertionError("2-tuple rows must be refused")


def test_dup_id_in_base_list_conflicts():
    anc = {"l": [{"name": "s", "v": 1}]}
    base = {"l": [{"name": "s", "v": 1}, {"name": "s", "v": 9}]}
    try:
        M.merge(base, [("R", {"l": [{"name": "s", "v": 2}]}, anc)])
    except M.Conflict:
        pass
    else:
        raise AssertionError("expected a conflict")


def test_fork_base_adds_sibling_element_merges():
    anc = {"l": [{"name": "s", "v": 1}], "k": 0}
    base = {"l": [{"name": "s", "v": 1}], "k": 5}
    row = {"l": [{"name": "s", "v": 2}], "k": 0}
    res, _ = M.merge(base, [("R", row, anc)])
    assert res == {"l": [{"name": "s", "v": 2}], "k": 5}
