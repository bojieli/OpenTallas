"""COMPOSE-GUARD-1124: compose_drop_guard refuses silent drops / reverts / lost private rows (QC C1k lost r10 + start_copy)."""
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_drop_guard as G


def _plan():
    return {
        "clock": {"tap_offset": {"per_port_ps": {"st_a": {"p0": 1.0}, "st_b": {"p0": 2.0}}}},
        "latency": {"lanes": {"sl_E0": {"cycles": 2}}},
        "partition_types": {
            "st_a": {"landing_relay_start_copy": True, "relay_sites": {"u_r/q[0]": [1, 2], "u_r/q[1]": [3, 4]},
                     "internal_stations": [{"conn": "bus:a", "n": 1}, {"conn": "bus:flt_o", "n": 2}],
                     "clock": {"taps": [[0, 0], [1, 1]]}},
            "st_b": {"landing_relay_start_copy": True, "relay_sites": {}},
        },
    }


def _w(tmp, name, obj):
    p = tmp / name
    p.write_text(json.dumps(obj))
    return str(p)


def test_identical_passes(tmp_path, capsys):
    p = _plan()
    assert G.main([_w(tmp_path, "a.json", p), _w(tmp_path, "b.json", p)]) == 0
    assert "PASS 0 silent" in capsys.readouterr().out


def test_changed_value_is_not_a_drop(tmp_path):
    a, b = _plan(), _plan()
    b["partition_types"]["st_a"]["relay_sites"]["u_r/q[0]"] = [9, 9]
    b["latency"]["lanes"]["sl_E0"]["cycles"] = 4
    assert G.main([_w(tmp_path, "a.json", a), _w(tmp_path, "b.json", b)]) == 0


def test_dropped_key_and_list_element_refused(tmp_path, capsys):
    a, b = _plan(), _plan()
    del b["partition_types"]["st_a"]["landing_relay_start_copy"]
    b["partition_types"]["st_a"]["internal_stations"].pop()            # identity-keyed list element (conn)
    del b["partition_types"]["st_a"]["relay_sites"]["u_r/q[1]"]
    assert G.main([_w(tmp_path, "a.json", a), _w(tmp_path, "b.json", b)]) == 1
    out = capsys.readouterr().out
    assert "partition_types.st_a.landing_relay_start_copy" in out
    assert "internal_stations[conn=bus:flt_o]" in out
    assert "relay_sites.u_r/q[1]" in out
    assert "REFUSED 3 silent" in out


def test_null_counts_as_drop_and_whole_type_is_one_line():
    a, b = _plan(), _plan()
    b["partition_types"]["st_a"]["landing_relay_start_copy"] = None
    del b["partition_types"]["st_b"]
    found = G.guard(a, b)
    assert sorted(p for _, p, _, _ in found) == ["partition_types.st_a.landing_relay_start_copy", "partition_types.st_b"]


def test_drop_list_names_intended(tmp_path, capsys):
    a, b = _plan(), _plan()
    b["partition_types"]["st_a"]["relay_sites"] = {"u_new/q[0]": [5, 5]}     # a re-key: old keys go, new ones come
    dl = tmp_path / "drops.txt"
    dl.write_text("# re-key row 1d3b\npartition_types.st_a.relay_sites.* # SEAT-MATCH re-key\n")
    assert G.main([_w(tmp_path, "a.json", a), _w(tmp_path, "b.json", b), "--drop-list", str(dl)]) == 0
    out = capsys.readouterr().out
    assert "INTENDED DROP partition_types.st_a.relay_sites x2" in out


def test_drop_list_kind_prefix_only_matches_that_kind():
    pats = G.load_drop_list_lines(["REVERT partition_types.st_a.*"])
    assert G.intended("REVERT", "partition_types.st_a.clock.taps", pats)
    assert not G.intended("DROP", "partition_types.st_a.clock.taps", pats)


def test_revert_to_older_value_needs_history(tmp_path, capsys):
    old, prev = _plan(), _plan()
    prev["partition_types"]["st_a"]["clock"]["taps"] = [[0, 0], [5, 5]]      # a row in PREV moved a tap
    new = copy.deepcopy(old)                                                  # compose from the stale base
    args = [_w(tmp_path, "prev.json", prev), _w(tmp_path, "new.json", new)]
    assert G.main(args) == 0                                                  # value change alone: not a drop
    assert G.main(args + ["--history", _w(tmp_path, "old.json", old)]) == 1
    out = capsys.readouterr().out
    assert "REVERT partition_types.st_a.clock" in out and "taps" in out


def test_private_row_lost(tmp_path, capsys):
    base, new = _plan(), _plan()
    row = copy.deepcopy(base)
    row["partition_types"]["st_a"]["clock"]["taps"] = [[0, 0], [7, 7]]
    row["clock"]["tap_offset"]["per_port_ps"]["st_a"]["p9"] = 3.0
    args = [_w(tmp_path, "prev.json", new), _w(tmp_path, "new.json", new),
            "--row", "r10=%s:%s" % (_w(tmp_path, "base.json", base), _w(tmp_path, "row.json", row))]
    assert G.main(args) == 1
    out = capsys.readouterr().out
    assert "ROW-LOST partition_types.st_a.clock" in out and "(row r10)" in out
    assert "ROW-DROP clock.tap_offset" in out
    carried = copy.deepcopy(row)
    args[1] = _w(tmp_path, "new2.json", carried)
    args[0] = _w(tmp_path, "prev2.json", carried)
    assert G.main(args) == 0


def test_row_replaced_later_is_not_lost():
    base = _plan()
    row = copy.deepcopy(base)
    row["latency"]["lanes"]["sl_E0"]["cycles"] = 3
    new = copy.deepcopy(base)
    new["latency"]["lanes"]["sl_E0"]["cycles"] = 4                         # a later row set a third value
    assert G.row_check(base, row, new) == []


def test_bad_input_rc2(tmp_path):
    assert G.main([str(tmp_path / "missing.json"), str(tmp_path / "missing2.json")]) == 2
    p = _w(tmp_path, "a.json", _plan())
    assert G.main([p, p, "--row", "broken"]) == 2


def test_pre_findings_are_warn_by_default():
    a, b = _plan(), _plan()
    del b["partition_types"]["st_a"]["landing_relay_start_copy"]
    lines = G.findings_for_pre(a, b)
    assert lines and all(x.startswith("WARN COMPOSEDROP") for x in lines)
    assert G.findings_for_pre(a, a) == []
    assert G.findings_for_pre(a, b, level="FAIL")[0].startswith("FAIL COMPOSEDROP")


def test_plan_gate_pre_composedrop_class(tmp_path, monkeypatch):
    import plan_gate_pre as P
    assert "COMPOSEDROP" in P.CLASSES
    a, b = _plan(), _plan()
    del b["partition_types"]["st_a"]["landing_relay_start_copy"]
    pa, pb = _w(tmp_path, "base.json", a), _w(tmp_path, "plan.json", b)
    others = [c for c in P.CLASSES if c != "COMPOSEDROP"] + ["TAPOFF", "STARTSETTLE"]
    monkeypatch.setenv("OT_TREE_PRECHECK", "off")
    f = [x for x in P.check(str(tmp_path), pb, baseline=pa, skip=others) if "COMPOSEDROP" in x]
    assert f and all(x.startswith("WARN COMPOSEDROP") for x in f)
    assert any("landing_relay_start_copy" in x for x in f)
    assert not [x for x in P.check(str(tmp_path), pb, skip=others) if "COMPOSEDROP" in x]      # no baseline: not run
    monkeypatch.setenv("OT_COMPOSE_DROP", "fail")
    assert [x for x in P.check(str(tmp_path), pb, baseline=pa, skip=others) if x.startswith("FAIL COMPOSEDROP")]
    dl = tmp_path / "drops.txt"
    dl.write_text("partition_types.st_a.landing_relay_start_copy # intended\n")
    monkeypatch.setenv("OT_COMPOSE_DROP_LIST", str(dl))
    assert not [x for x in P.check(str(tmp_path), pb, baseline=pa, skip=others) if "COMPOSEDROP" in x]
