"""STN-REPRICE 11-24: a station-adding row is re-priced in the same op set; law-table guard; STNPRICE count line."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stn_reprice as SR  # noqa: E402

ROW = """import json, sys
raw = json.load(open(sys.argv[1]))
raw["partition_types"]["a"]["internal_stations"][0]["regs_um"].append([9, 9])
json.dump(raw, open(sys.argv[2], "w"), indent=1)
"""


def _plan(fixed=2, regs_a=1):
    return {"partitions": [{"name": "pa", "type": "a"}, {"name": "pb", "type": "b"}],
            "ports": [{"id": "p1", "src": {"part": "pa", "bus": "o"}, "dst": {"part": "pb", "bus": "i"}}],
            "lanes": [{"id": "L1", "ports": ["p1"], "fixed_cycles": fixed}],
            "latency": {"lanes": {"L1": {"fixed": fixed, "cycles": fixed + 2, "natural": fixed}}},
            "partition_types": {"a": {"internal_stations": [{"conn": "bus:o", "regs_um": [[0, 0]] * regs_a}]},
                                "b": {"internal_stations": [{"conn": "bus:i", "regs_um": [[1, 1]]}]}}}


def _setup(tmp_path):
    (tmp_path / "row.py").write_text(ROW)
    (tmp_path / "base.json").write_text(json.dumps(_plan()))
    return tmp_path


def test_wrap_reprices_added_station_idempotent(tmp_path):
    _setup(tmp_path)
    a = ["wrap", "--", str(tmp_path / "row.py"), str(tmp_path / "base.json"), str(tmp_path / "out.json")]
    assert SR.main(a) == 0
    L = json.loads((tmp_path / "out.json").read_text())
    assert L["lanes"][0]["fixed_cycles"] == 3 and L["latency"]["lanes"]["L1"] == {"fixed": 3, "cycles": 5, "natural": 3}
    # a second pass over its own output (no further depth change vs the new base) changes nothing
    (tmp_path / "out2.json").write_text((tmp_path / "out.json").read_text())
    raw = json.loads((tmp_path / "out.json").read_text())
    assert SR.reprice_raw(raw, json.loads((tmp_path / "out.json").read_text())) == {}


def test_unpriced_lane_is_counted_priced_is_not():
    bad, n = SR.stnprice_lanes(_plan(fixed=2))
    assert n == 1 and bad == []                       # depth 1 + 1 == fixed 2
    assert SR.stnprice_lanes(_plan(fixed=3, regs_a=2))[0] == []
    assert len(SR.stnprice_lanes(_plan(fixed=5))[0]) == 1


def _with_table(tmp_path, regen=False):
    base = _plan()
    (tmp_path / "base.json").write_text(json.dumps(base))
    new = _plan(fixed=3, regs_a=2)
    new["asbuilt"] = {"land_r8": "pv_col.json"}
    (tmp_path / "new.json").write_text(json.dumps(new))
    (tmp_path / "pv_col.json").write_text(json.dumps({"members": [{"lane": "L1"}]}))
    if regen:
        d = tmp_path / "regen"
        d.mkdir()
        (d / "pv_col.json").write_text(json.dumps({"members": [{"lane": "L1", "x": 1}]}))
        return [str(d / "pv_col.json")]
    return []


def test_law_guard_reports_and_strict_refuses_unless_regen(tmp_path):
    _with_table(tmp_path)
    h = SR.law_hits(tmp_path / "new.json", tmp_path / "base.json")
    assert list(h.values()) == [["L1"]]
    assert SR._law_lines(h, False)[0].startswith("WARN STNREPRICE-LAW") and SR._law_lines(h, True)[0].startswith("FAIL")
    assert SR.main(["check", str(tmp_path / "new.json"), "--baseline-plan", str(tmp_path / "base.json")]) == 0
    assert SR.main(["check", str(tmp_path / "new.json"), "--baseline-plan", str(tmp_path / "base.json"), "--strict"]) == 3
    regen = _with_table(tmp_path, regen=True)
    assert SR.law_hits(tmp_path / "new.json", tmp_path / "base.json", regen=regen) == {}


def test_wrap_strict_refuses_law_member(tmp_path):
    _setup(tmp_path)
    (tmp_path / "pv_col.json").write_text(json.dumps({"members": [{"lane": "L1"}]}))
    base = _plan()
    base["asbuilt"] = {"land_r8": "pv_col.json"}
    (tmp_path / "base.json").write_text(json.dumps(base))
    a = ["wrap", "--strict", "--", str(tmp_path / "row.py"), str(tmp_path / "base.json"), str(tmp_path / "out.json")]
    assert SR.main(a) == 3
    assert (tmp_path / "out.json.refused").is_file() and not (tmp_path / "out.json").exists()


def test_pre_line_is_report_only(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(_plan(fixed=9)))
    out = SR.check_stnprice(str(p))
    assert len(out) == 1 and out[0].startswith("LIST STNPRICE 1 of 1")


def test_baseline_station_growth_without_fixed_delta_is_reported(tmp_path):
    base = tmp_path / "base.json"
    candidate = tmp_path / "candidate.json"
    base.write_text(json.dumps(_plan(fixed=21, regs_a=11)))
    candidate.write_text(json.dumps(_plan(fixed=21, regs_a=12)))

    assert SR.G.istcyc_lanes(json.loads(candidate.read_text()), json.loads(base.read_text())) == []
    assert SR.check_stnprice(candidate, baseline=base)[1] == (
        "WARN ADV-IST-PRICE STATION-DELTA lane L1: lane-end stations 12 -> 13, "
        "fixed_cycles 21 -> 21; 1 added cycle(s) lack a fixed price"
    )

    candidate.write_text(json.dumps(_plan(fixed=22, regs_a=12)))
    assert len(SR.check_stnprice(candidate, baseline=base)) == 1

    candidate.write_text(json.dumps(_plan(fixed=21, regs_a=11)))
    assert len(SR.check_stnprice(candidate, baseline=base)) == 1


def test_upstream_reach_flags_member_fed_by_moved_lane(tmp_path):
    base = _plan()
    new = _plan(fixed=3, regs_a=2)
    for d in (base, new):
        d["partitions"].append({"name": "pc", "type": "c"})
        d["ports"].append({"id": "p2", "src": {"part": "pb", "bus": "o2"}, "dst": {"part": "pc", "bus": "i2"}})
        d["lanes"].append({"id": "L2", "ports": ["p2"], "fixed_cycles": 0})
        d["partition_types"]["c"] = {}
    new["asbuilt"] = {"land_r8": "t.json"}
    (tmp_path / "t.json").write_text(json.dumps({"members": [{"lane": "L2"}]}))
    (tmp_path / "base.json").write_text(json.dumps(base))
    (tmp_path / "new.json").write_text(json.dumps(new))
    assert SR.law_hits(tmp_path / "new.json", tmp_path / "base.json") == {}
    assert list(SR.law_hits(tmp_path / "new.json", tmp_path / "base.json", upstream=1).values()) == [["L2"]]
