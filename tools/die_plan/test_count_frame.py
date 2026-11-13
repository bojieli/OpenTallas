"""QC-REGION-1 COUNT FRAME (count_frame.py) and its readers: count_align_plan, count_align_bind, clock_landings,
lane_asbuilt_latency."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landings as CL  # noqa: E402
import count_align_bind as CB  # noqa: E402
import count_align_plan as CAP  # noqa: E402
import count_frame as CF  # noqa: E402
import lane_asbuilt_latency as LA  # noqa: E402

T = 833.0
PR = dict(a1="a", a2="a", b="b", c1="c", c2="c", c3="c")
OFF = dict(a=0, b=3, c=7)          # whole-cycle leaf offsets of a link-fed regional clock
EDGES = [("a1", "b"), ("b", "c1"), ("c2", "a2"), ("a2", "c3"), ("c3", "b"), ("b", "a2"), ("c1", "a1"), ("a2", "b"),
         ("b", "c2")]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def die(tmp, feed=True):
    """a die plan dir: plan_of_record/{feed,regions,plan}.json; feed=False = an old plan (no clock.spine.feed)"""
    por = tmp / "plan_of_record"
    por.mkdir(parents=True, exist_ok=True)
    (por / "feed_t.json").write_text(json.dumps(dict(frame="wall_aligned", frame_offset=OFF, root="a")))
    (por / "regions_t.json").write_text(json.dumps(dict(part_region=PR)))
    sp = dict(topology="htree")
    if feed:
        sp = dict(topology="link_htree",
                  region_map=dict(path="plan_of_record/regions_t.json", sha256=_sha(por / "regions_t.json")[:16]),
                  feed=dict(path="plan_of_record/feed_t.json", sha256=_sha(por / "feed_t.json")[:16], root="a",
                            form="fwd", frame="wall_aligned"))
    plan = dict(clock=dict(spine=sp), partitions=[dict(name=p, type="t") for p in PR], partition_types=dict(t={}))
    pp = por / ("zz_feed.json" if feed else "zz_old.json")
    pp.write_text(json.dumps(plan))
    return plan, pp


def rows():
    """OCV rows of the link feed: d = dst clock - src clock carries the whole-cycle leaf offsets"""
    ph = dict(a=40.0, b=300.0, c=-250.0)
    out = []
    for u, v in EDGES:
        ru, rv = PR[u], PR[v]
        d = (OFF[rv] - OFF[ru]) * T + ph[rv] - ph[ru]
        out.append(dict(port=f"{u}_{v}", src=ru, dst=rv, d_ps=d, p_up_ps=60, p_dn_ps=60, unshared_a_ps=1000.0,
                        unshared_b_ps=1000.0, margin_ps=0.0))
    return out


def parts():
    return {f"{u}_{v}": (u, v) for u, v in EDGES}


def plan_doc(frame):
    s, out, regs = CAP.plan(rows(), T, T / 8, 0.05, 26.5, 0)
    s.update(period_ps=T, aperture_ps=T / 8, sync_aperture_ps=26.5, pad=0)
    CAP.apply_frame(s, out, frame)
    return CB.plan_doc(s, out, regs)


def table(b):
    return dict(regions=[], ports=[dict(port=p, src=c["src_part"], dst=c["dst_part"], src_region=c["src"],
                                        dst_region=c["dst"], width=8, lane="L" + p) for p, c in b["ports"].items()])


def bind_dir(tmp, t, frame):
    """the slice of a bind output lane_asbuilt_latency reads for the landing cycles"""
    bd = tmp / "bind"
    (bd / "rtl").mkdir(parents=True, exist_ok=True)
    (bd / "rtl" / "t_bound_top.sv").write_text("module t_bound_top;\nendmodule\n")
    (bd / "bind_latency.json").write_text(json.dumps(dict(buses=[])))
    man = dict(lane_added_cycles=CB.lane_cycles(t))
    if frame is not None:
        man["count_frame"] = frame.meta()
    (bd / "bind_clock_landings.json").write_text(json.dumps(man))
    return bd


def test_frame_round_trip(tmp_path):
    plan, pp = die(tmp_path)
    fr = CF.load(plan, pp)
    assert fr.name == "wall_aligned" and fr.feed_path == "plan_of_record/feed_t.json"
    assert {p: fr.f(p) for p in PR} == {p: OFF[r] for p, r in PR.items()}
    assert fr.f("c") == 7 and fr.f("st:h0001") == 0 and fr.shift("a1", "c2") == 7
    with pytest.raises(CF.FrameError):
        fr.f("zz")
    back = CF.from_meta(json.loads(json.dumps(fr.meta(offsets=True))))
    assert all(back.f(p) == fr.f(p) for p in list(PR) + list(OFF))
    assert CF.same(fr.meta(), fr) and CF.same(back.meta(), fr)
    for s, d in EDGES:
        assert CF.edge_lat(CF.wall_lat(2, fr, s, d), fr, s, d) == 2
    # the frame files are pinned by sha: a changed feed is refused
    (pp.parent / "feed_t.json").write_text(json.dumps(dict(frame="wall_aligned", frame_offset=dict(OFF, c=8))))
    with pytest.raises(CF.FrameError, match="sha"):
        CF.load(plan, pp)


def test_landed_lane_end_to_end_both_frames(tmp_path):
    plan, pp = die(tmp_path)
    fr = CF.load(plan, pp)
    # edge-index frame (no frame applied) and wall-aligned frame, same rows / same physics
    be = CB.bind(plan_doc(None), parts=parts())
    bw = CB.bind(plan_doc(fr), parts=parts())
    ve, vw = CB.verify(be, 400), CB.verify(bw, 400)
    assert not ve["identity_and_loop_errors"] and not vw["identity_and_loop_errors"], vw
    assert ve["sim_window_violations"] == 0 and vw["sim_window_violations"] == 0
    assert vw["sim_min_margin_low_ps"] == ve["sim_min_margin_low_ps"]
    for p, c in bw["ports"].items():
        s, d = c["src_part"], c["dst_part"]
        assert c["K"] == be["ports"][p]["K"]                                    # RTL K: the frame relabels the count
        assert c["sched_lat"] == be["ports"][p]["sched_lat"] + fr.shift(s, d)   # schedule: whole cycles out of d
    assert min(c["sched_lat"] for c in be["ports"].values()) <= 0                # edge frame: not a latency
    assert min(c["sched_lat"] for c in bw["ports"].values()) >= 1
    # a wrong frame shift on one crossing is caught by the identity and the loops
    q = next(p for p, c in bw["ports"].items() if not c["tree"] and fr.shift(c["src_part"], c["dst_part"]))
    bad = json.loads(json.dumps({k: v for k, v in bw.items() if k != "_frame_obj"}))
    bad["ports"][q]["sched_lat"] = be["ports"][q]["sched_lat"]
    assert any(e.startswith("identity " + q) for e in CB.verify(bad, 50)["identity_and_loop_errors"])
    # the lane: sidecar (annotate_table) -> clock_landings pricing -> bind manifest -> lane_asbuilt_latency
    lane, pid = "L" + q, q
    tw = CB.annotate_table(table(bw), bw)
    assert tw["count_aligned"]["frame"]["feed_sha256"] == fr.feed_sha[:16]
    CF.check_same(tw["count_aligned"].get("frame"), CF.load(plan, pp), "sidecar")       # Landings guard
    assert CL.ca_cycles(tw["count_aligned"], pid) == bw["ports"][pid]["sched_lat"]
    _, _, _, _, land, _ = LA.load_bind_dir(bind_dir(tmp_path, tw, fr), plan, pp)
    assert land(lane) == bw["ports"][pid]["sched_lat"] == be["ports"][pid]["sched_lat"] + fr.shift(*parts()[pid])
    # the edge-frame sidecar / bind output under the feed plan: refused by every reader
    te = CB.annotate_table(table(be), be)
    with pytest.raises(CF.FrameError):
        CF.check_same(te["count_aligned"].get("frame"), fr, "sidecar")
    with pytest.raises(SystemExit, match="count frame"):
        LA.load_bind_dir(bind_dir(tmp_path, te, None), plan, pp)
    # count_align_bind refuses a plan doc whose lat_cycles are not edge + shift
    pw = plan_doc(fr)
    pw["crossings"][0]["lat_cycles"] += 1
    with pytest.raises(CB.BindError, match="frame"):
        CB.bind(pw)


def test_old_plan_regression(tmp_path):
    plan, pp = die(tmp_path, feed=False)
    assert CF.load(plan, pp) is None and CF.load_path(pp) is None
    s, out, regs = CAP.plan(rows(), T, T / 8, 0.05, 26.5, 0)
    before = json.dumps([s, out, regs], sort_keys=True, default=str)
    CAP.apply_frame(s, out, CF.load(plan, pp))
    assert json.dumps([s, out, regs], sort_keys=True, default=str) == before        # no-op
    b = CB.bind(plan_doc(None), parts=parts())
    assert "frame" not in b
    t = CB.annotate_table(table(b), b)
    assert "frame" not in t["count_aligned"]
    CF.check_same(t["count_aligned"].get("frame"), None, "sidecar")
    _, _, _, _, land, _ = LA.load_bind_dir(bind_dir(tmp_path, t, None), plan, pp)
    assert all(land("L" + p) == c["sched_lat"] for p, c in b["ports"].items())
    # a frame-carrying sidecar under an old plan is refused (no silent mix)
    plan_f, pp_f = die(tmp_path / "f")
    tw = CB.annotate_table(table(CB.bind(plan_doc(CF.load(plan_f, pp_f)), parts=parts())), CB.bind(
        plan_doc(CF.load(plan_f, pp_f)), parts=parts()))
    with pytest.raises(CF.FrameError):
        CF.check_same(tw["count_aligned"].get("frame"), None, "sidecar")


def test_implicit_frame_source_missing_is_a_no_op(tmp_path):
    """--sta-plan / --plan-die that is not on disk (planner_cli tests): no frame, legacy output; an explicit
    --frame-plan that is missing is an error"""
    assert CF.load_optional(None) is None and CF.load_optional(tmp_path / "nope.json") is None
    (tmp_path / "bad.json").write_text("{not json")
    assert CF.load_optional(tmp_path / "bad.json") is None
    with pytest.raises(OSError):
        CF.load_path(tmp_path / "nope.json")
    plan, pp = die(tmp_path)
    assert CF.load_optional(pp).feed_sha == CF.load_path(pp).feed_sha       # a real feed plan still loads
    s, out, regs = CAP.plan(rows(), T, T / 8, 0.05, 26.5, 0)
    before = json.dumps([s, out], sort_keys=True, default=str)
    CAP.apply_frame(s, out, CF.load_optional(tmp_path / "nope.json"))
    assert json.dumps([s, out], sort_keys=True, default=str) == before


def test_cli_without_frame_plan_on_missing_sta_plan_is_byte_identical(tmp_path):
    """count_align_plan.main: no --frame-plan + a --sta-plan path that does not exist never touches the frame"""
    fi = tmp_path / "in.json"
    rs = rows()
    fi.write_text(json.dumps(dict(corners=dict(TT=dict(all=rs), FF=dict(all=rs)))))
    a = ["--corner", "TT,FF", "--period", str(T), "--wander-frac", "0.05"]
    CAP.main([str(fi)] + a + ["--out", str(tmp_path / "o1.json")])
    import unittest.mock as um
    with um.patch.object(CAP, "sta_rows_hull", lambda rows, args: dict(missing=0)):
        CAP.main([str(fi)] + a + ["--sta-proof", str(tmp_path / "noproof"), "--sta-plan", str(tmp_path / "none.json"),
                                  "--out", str(tmp_path / "o2.json")])
    d1, d2 = json.loads((tmp_path / "o1.json").read_text()), json.loads((tmp_path / "o2.json").read_text())
    d2["summary"].pop("sta_interval", None)
    assert "frame" not in d2["summary"] and d1["crossings"] == d2["crossings"]
    with pytest.raises((OSError, SystemExit)):
        CAP.main([str(fi)] + a + ["--frame-plan", str(tmp_path / "none.json"), "--out", str(tmp_path / "o3.json")])
