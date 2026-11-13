"""QC-REGION-1 region_form.py sta (built-clock K re-derivation follow-on delta): the START form of the re-derivation is
the sidecar's.  s28 built proof: a data START tree re-planned on the STA hull turned 195/312 sync-ambiguous tree edges
into 5-9 cycles of path ambiguity on 117 crossings whose own interval fits DEPTH 4 (count_align_plan's own
test_data_tree_accumulates_ambiguity_clock_tree_does_not proves the clock START tree removes that mode)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_align_plan as CAP  # noqa: E402
import count_frame as CF  # noqa: E402
import locality as LO  # noqa: E402
import region_form as RF  # noqa: E402

T = 833.0


def fixture(tmp, start_tree):
    plan = dict(partitions=[dict(name="a", type="t"), dict(name="b", type="t")],
                ports=[dict(id="ab", src=dict(part="a", bus="o"), dst=dict(part="b", bus="i"), width=8)],
                lanes=[dict(id="L", ports=["ab"])], latency=dict(lanes={}),
                clock=dict(spine=dict(topology="link_htree"),
                           landing_network=dict(data_cycles_per_crossing="count_aligned",
                                                count_aligned_cycles=dict(ab=2))))
    fr = CF.Frame("wall_aligned", dict(a=0, b=1), dict(a="a", b="b"), "plan_of_record/feed.json", "f" * 64, "e" * 64)
    side = dict(ports=[dict(port="ab", lane="L", src="a", dst="b", src_region="a", dst_region="b", width=8,
                            added_cycles=2)],
                count_aligned=dict(ports=dict(ab=dict(K=1, depth=4, sched_lat=2, tree=False)), frame=fr.meta(),
                                   **({"start_tree": start_tree} if start_tree else {})))
    pp, sp = tmp / "plan.json", tmp / "side.json"
    pp.write_text(json.dumps(plan))
    sp.write_text(json.dumps(side))
    return pp, sp, fr


@pytest.fixture
def stubs(monkeypatch):
    seen = {}
    r = dict(port="ab", src="a", dst="b", d_ps=T + 100.0, p_up_ps=50.0, p_dn_ps=50.0, unshared_a_ps=100.0,
             unshared_b_ps=100.0, margin_ps=0.0)
    monkeypatch.setattr(LO, "load_plan", lambda p: dict(period=T))
    monkeypatch.setattr(LO, "score", lambda D, reg, v, f: dict(crossings=[]))
    monkeypatch.setattr(LO, "cap_corner_rows", lambda R: dict(TT=[dict(r)], FF=[dict(r)]))
    monkeypatch.setattr(RF, "validate_errs", lambda raw: set())
    monkeypatch.setattr(RF, "lane_table", lambda raw, lids: {})          # no latency table in the fixture

    def cap_main(argv):
        seen["argv"] = list(argv)
        out = argv[argv.index("--out") + 1]
        Path(out).write_text(json.dumps(dict(summary=dict(worst_margin_lo_ps=200.0, worst_margin_hi_ps=210.0),
                                             crossings=[dict(port="ab", depth=4, lat_cycles=3, frame_shift=1,
                                                             margin_lo_ps=200.0, margin_hi_ps=210.0)])))
        return 0
    monkeypatch.setattr(CAP, "main", cap_main)
    return seen


def run(tmp, start_tree, stubs, monkeypatch):
    pp, sp, fr = fixture(tmp, start_tree)
    monkeypatch.setattr(CF, "load", lambda plan, path=None, base=None: fr)
    return RF.sta(pp, tmp / "out.json", sp, tmp / "side_out.json", tmp / "proof")


def test_clock_start_sidecar_is_rederived_on_the_clock_start_tree(tmp_path, stubs, monkeypatch):
    rep = run(tmp_path, "clock", stubs, monkeypatch)
    a = stubs["argv"]
    assert a[a.index("--start-tree") + 1] == "clock"                 # never a data START tree on a clock sidecar
    assert "--sta-proof" in a and a[a.index("--sta-plan") + 1] == str(tmp_path / "plan.json")   # frame from the plan
    p = rep["ports"][0]
    assert (p["old"], p["new"], p["K_old"], p["K_new"]) == (2, 3, 1, 2)   # K absorbs, origins kept, same frame
    s = json.loads((tmp_path / "side_out.json").read_text())
    assert s["count_aligned"]["ports"]["ab"]["sched_lat"] == 3 and s["ports"][0]["added_cycles"] == 3
    assert s["count_aligned"]["start_tree"] == "clock" and s["count_aligned"]["frame"]["frame"] == "wall_aligned"
    out = json.loads((tmp_path / "out.json").read_text())
    assert out["clock"]["landing_network"]["count_aligned_cycles"]["ab"] == 3
    assert not rep["post_check"]


def test_data_start_sidecar_keeps_the_data_start_tree(tmp_path, stubs, monkeypatch):
    run(tmp_path, None, stubs, monkeypatch)
    a = stubs["argv"]
    assert a[a.index("--start-tree") + 1] == "data"


def test_unknown_start_form_and_wrong_frame_conflict(tmp_path, stubs, monkeypatch):
    with pytest.raises(RF.Conflict, match="start_tree"):
        run(tmp_path, "mesh", stubs, monkeypatch)
    pp, sp, fr = fixture(tmp_path, "clock")
    other = CF.Frame("wall_aligned", dict(a=0, b=1), dict(a="a", b="b"), "x", "0" * 64, "e" * 64)
    monkeypatch.setattr(CF, "load", lambda plan, path=None, base=None: other)
    with pytest.raises(RF.Conflict, match="count frame"):
        RF.sta(pp, tmp_path / "o.json", sp, tmp_path / "so.json", tmp_path / "proof")


def test_fail_on_built_clock_is_a_post_check_failure(tmp_path, stubs, monkeypatch):
    def cap_fail(argv):
        Path(argv[argv.index("--out") + 1]).write_text(json.dumps(dict(summary={}, crossings=[dict(
            port="ab", depth=None, lat_cycles=None, path_ambiguous_cycles=5)])))
        return 1
    monkeypatch.setattr(CAP, "main", cap_fail)
    rep = run(tmp_path, "clock", stubs, monkeypatch)
    assert rep["summary"]["fail"] == 1 and rep["post_check"] and "FAIL the CA ring" in rep["post_check"][0]


def test_clock_start_retimes_by_default_and_can_be_turned_off(tmp_path, stubs, monkeypatch):
    rep = run(tmp_path, "clock", stubs, monkeypatch)
    a = stubs["argv"]
    assert "--start-retime-up" in a and "--start-lift" in a and "--depth16-allow" not in a
    assert rep["summary"]["start_retime"] == ["--start-retime-up", "--start-lift"]
    pp, sp, fr = fixture(tmp_path, "clock")
    RF.sta(pp, tmp_path / "o2.json", sp, tmp_path / "s2.json", tmp_path / "proof", start_retime=False)
    assert "--start-retime-up" not in stubs["argv"] and "--start-lift" not in stubs["argv"]
    run(tmp_path, None, stubs, monkeypatch)                          # data START: retime needs a clock START tree
    assert "--start-retime-up" not in stubs["argv"]
