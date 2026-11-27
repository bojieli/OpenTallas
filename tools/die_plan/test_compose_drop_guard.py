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


def test_pre_findings_level_is_caller_choice():
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
    cd = lambda fs: [x for x in fs if x.split()[1:2] == ["COMPOSEDROP"]]  # noqa: E731 - not the LIST PRE-TIME line
    monkeypatch.setenv("OT_TREE_PRECHECK", "off")
    f = cd(P.check(str(tmp_path), pb, baseline=pa, skip=others))
    assert f and all(x.startswith("FAIL COMPOSEDROP") for x in f)      # P-COMPOSE-DROP 11-27: blocking by default
    assert any("landing_relay_start_copy" in x for x in f)
    monkeypatch.setenv("OT_COMPOSE_DROP", "warn")
    assert all(x.startswith("WARN COMPOSEDROP") for x in cd(P.check(str(tmp_path), pb, baseline=pa, skip=others)))
    monkeypatch.delenv("OT_COMPOSE_DROP")
    assert not cd(P.check(str(tmp_path), pb, skip=others))      # no baseline: not run
    monkeypatch.setenv("OT_COMPOSE_DROP", "fail")
    assert [x for x in cd(P.check(str(tmp_path), pb, baseline=pa, skip=others)) if x.startswith("FAIL ")]
    dl = tmp_path / "drops.txt"
    dl.write_text("partition_types.st_a.landing_relay_start_copy # intended\n")
    monkeypatch.setenv("OT_COMPOSE_DROP_LIST", str(dl))
    assert not cd(P.check(str(tmp_path), pb, baseline=pa, skip=others))


# QC-GUARD-SIDECAR: the bind reads collector tap fields from the launch sidecar, kit gen / landing_place from the plan.
def _sc_plan():
    p = _plan()
    p["partition_types"]["st_a"]["clock"]["landing_contract"] = {
        "collector_root_node": "rst_root_n",
        "collector_local_sources": [{"name": "cws1_i", "tap": 5, "node": "rst_n_t5", "xy_um": [0, 1]},
                                    {"name": "x_st_b_i", "tap": 7, "xy_um": [3, 4]}],
        "collector_children": [{"index": 0, "node": "rst_n_t9", "tap": 9, "xy_um": [8, 8]}]}
    return p


def _sidecar_of(plan):
    types = {}
    for tn, t in plan["partition_types"].items():
        lc = (t.get("clock") or {}).get("landing_contract")
        if lc:
            types[tn] = {"collector_root_node": lc["collector_root_node"], "tree": {"relays": []},
                         "local_sources": copy.deepcopy(lc["collector_local_sources"]),
                         "children": copy.deepcopy(lc["collector_children"])}
    return {"schema": "t", "collector": {"types": types}}


def test_sidecar_in_sync_passes(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("OT_COMPOSE_DROP", "fail")
    p = _sc_plan()
    pp, sp = _w(tmp_path, "p.json", p), _w(tmp_path, "s.json", _sidecar_of(p))
    assert G.main([pp, pp, "--sidecar", sp, "--prev-sidecar", sp]) == 0
    out = capsys.readouterr().out
    assert "SIDECAR PASS" in out and "PASS 0 silent" in out
    assert G.sidecar_mismatches(p, _sidecar_of(p)) == []


def test_tap_changed_only_in_plan_flagged(tmp_path, capsys, monkeypatch):
    p = _sc_plan()
    s = _sidecar_of(p)
    lc = p["partition_types"]["st_a"]["clock"]["landing_contract"]
    lc["collector_local_sources"][0].update(tap=84, node="rst_n_t84")     # plan-only retap (the sidecar keeps t5)
    lc["collector_children"][0]["tap"] = 11
    mm = G.sidecar_mismatches(p, s)
    assert mm == [("partition_types.st_a.clock.landing_contract.collector_local_sources[name=cws1_i].node", "rst_n_t84", "rst_n_t5")]
    lc["collector_local_sources"][1]["tap"] = 70                          # tap-only row: its effective node moves too
    raw = G.Counter()
    mm = G.sidecar_mismatches(p, s, raw)
    assert len(mm) == 2 and mm[1][1:] == ("rst_n_t70", "rst_n_t7")
    assert raw == {"local_sources.node": 1, "local_sources.tap": 2, "children.tap": 1}   # child tap beside its node: raw only
    pp, sp = _w(tmp_path, "p.json", p), _w(tmp_path, "s.json", s)
    monkeypatch.delenv("OT_COMPOSE_DROP", raising=False)
    assert G.main([pp, pp, "--sidecar", sp, "--sidecar-max", "1"]) == 0              # WARN by default
    out = capsys.readouterr().out
    assert "WARN SIDECAR-MISMATCH 2 collector reset nodes" in out and "source_node 2" in out and "raw node/tap field diffs 4" in out
    assert "collector_local_sources[name=cws1_i].node" in out and "... 1 more" in out
    monkeypatch.setenv("OT_COMPOSE_DROP", "fail")
    assert G.main([pp, pp, "--sidecar", sp]) == 1
    out = capsys.readouterr().out
    assert "FAIL SIDECAR-MISMATCH 2" in out and "REFUSED 0 silent losses" in out
    dl = tmp_path / "d.txt"
    dl.write_text("SIDECAR-MISMATCH partition_types.st_a.* # intended\n")
    assert G.main([pp, pp, "--sidecar", sp, "--drop-list", str(dl)]) == 0


def test_sidecar_row_change_lost_in_compose_flagged(tmp_path, capsys):
    base = _sc_plan()
    sbase = _sidecar_of(base)
    srow = copy.deepcopy(sbase)                                               # the row retaps cws1_i in plan AND sidecar
    srow["collector"]["types"]["st_a"]["local_sources"][0].update(tap=84, node="rst_n_t84")
    row = copy.deepcopy(base)
    row["partition_types"]["st_a"]["clock"]["landing_contract"]["collector_local_sources"][0].update(tap=84, node="rst_n_t84")
    snew = copy.deepcopy(sbase)                                               # compose merged the plan only
    del snew["collector"]["types"]["st_a"]["local_sources"][1]                # ... and lost a sidecar entry
    pn, sn = _w(tmp_path, "new.json", row), _w(tmp_path, "snew.json", snew)
    args = [pn, pn, "--sidecar", sn, "--prev-sidecar", _w(tmp_path, "sprev.json", srow),
            "--sidecar-row", "srctap=%s:%s" % (_w(tmp_path, "sb.json", sbase), _w(tmp_path, "sr.json", srow))]
    assert G.main(args) == 1
    out = capsys.readouterr().out
    assert "ROW-LOST sidecar:collector.types.st_a" in out and "(sidecar row srctap)" in out
    assert "DROP sidecar:collector.types.st_a" in out and "local_sources[name=x_st_b_i]" in out
    assert "SIDECAR-MISMATCH 2 collector reset nodes" in out                 # the retapped node, and the absent row
    assert "source_node 1" in out and "source_row_one_side 1" in out
    good = _w(tmp_path, "sgood.json", srow)
    assert G.main([pn, pn, "--sidecar", good, "--prev-sidecar", good,
                   "--sidecar-row", "srctap=%s:%s" % (_w(tmp_path, "sb2.json", sbase), good)]) == 0


def test_sidecar_usage_errors_rc2(tmp_path):
    p = _w(tmp_path, "p.json", _sc_plan())
    assert G.main([p, p, "--prev-sidecar", p]) == 2                           # needs --sidecar
    assert G.main([p, p, "--sidecar", p]) == 2                                # a plan is not a sidecar


def test_plan_key_and_sibling_file_name_intended_drops(tmp_path):
    a, b = _plan(), _plan()
    del b["partition_types"]["st_a"]["landing_relay_start_copy"]
    assert G.findings_for_pre(a, b, level="FAIL")
    b["compose_drop_list"] = ["partition_types.st_a.landing_relay_start_copy # intended"]
    assert G.findings_for_pre(a, b, level="FAIL") == []
    del b["compose_drop_list"]
    pb = _w(tmp_path, "plan.json", b)
    (tmp_path / "plan.json.drop_list").write_text("partition_types.st_a.landing_relay_start_copy  # intended\n")
    assert G.findings_for_pre(a, b, level="FAIL", plan_path=pb) == []


def test_emit_drop_list_names_only_intended(tmp_path):
    a, b = _plan(), _plan()
    del b["partition_types"]["st_a"]["landing_relay_start_copy"]
    text, named, unnamed = G.emit_drop_list(a, b)
    assert not named and unnamed and text.startswith("#UNNAMED DROP ")
    assert G.load_drop_list_lines(text.splitlines()) == []            # an unnamed drop never reads as intended
    text, named, unnamed = G.emit_drop_list(a, b, G.load_drop_list_lines(["partition_types.st_a.landing_relay_start_copy"]))
    assert named and not unnamed and text.startswith("DROP ")
    assert G.load_drop_list_lines(text.splitlines())                  # the emitted list names it
