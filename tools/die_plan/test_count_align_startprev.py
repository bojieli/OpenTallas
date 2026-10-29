"""FLOW-GEN-2 --start-prev (opt-in): deterministic tie-break between start-tree re-plan passes (DIE-HEAD-15: each pass
moved one stage by one node along a repeater chain and flipped near-tie EDGE_FALL picks, gate numbers unchanged)."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_count_align_starttree as TS  # noqa: E402

cap = TS.cap
ROWS = [TS.row("ab", "R0", "R11", 1800.0, 100.0, 100.0), TS.row("ba", "R11", "R0", -1800.0, 100.0, 100.0)]


def ctx(of):
    return TS.ctx_chain(n=12, seg=160.0, ocv_frac=of)


def run(of, prev=None):
    root, edges, info = cap.clock_start_edges(ROWS, ctx(of), prev=prev)
    pref = cap.start_prefer_of(prev) if prev is not None else None
    s, out, regs = cap.plan(copy.deepcopy(ROWS), TS.T, TS.AP, 0.05, start_edges=edges, start_root=root,
                            start_prefer=pref)
    doc = dict(summary=s, regions=regs, crossings=out,
               start_edges=[{k: v for k, v in e.items() if not k.startswith("_")} for e in edges])
    return doc, info


def retimes(doc):
    return sorted(e["dst"] for e in doc["start_edges"] if e["retime"])


def picks(doc):
    return {g["start_from"]["port"]: g["start_from"]["edge"] for g in doc["regions"] if g["start_from"]}


def dump(doc):
    return json.dumps(doc, sort_keys=True, default=str)


def test_default_moves_the_stage_on_a_small_arrival_change():
    # the DIE-HEAD-15 symptom: a few % OCV moves the deepest clean retime node by two levels and flips EDGE_FALL
    a, _ = run(0.14)
    b, _ = run(0.15)
    assert retimes(a) == ["st:h0000000000"] and retimes(b) == ["st:h00000000"]
    assert a["summary"]["start_tree"]["start_fail"] == b["summary"]["start_tree"]["start_fail"] == 0


def test_prev_keeps_a_still_clean_stage_and_edge():
    # pass 1 (more OCV) put the stage on a shallower node; pass 2 (less OCV) would move it deeper by default
    a, _ = run(0.16)
    assert retimes(a) == ["st:h00000000"] and retimes(run(0.14)[0]) == ["st:h0000000000"]
    b, info = run(0.14, prev=a)
    assert retimes(b) == retimes(a) and info["prev_kept"] >= 1
    assert b["summary"]["start_tree"]["start_fail"] == 0
    assert all(e["clean_ok"] for e in b["start_edges"])
    assert picks(b) == picks(a)


def test_prev_is_a_fixed_point():
    a, _ = run(0.14)
    b, _ = run(0.14, prev=a)
    assert dump(b) == dump(a)


def test_prev_falls_back_when_the_kept_stage_is_unclean():
    a, _ = run(0.14)
    bad = copy.deepcopy(a)
    for e in bad["start_edges"]:
        if e["retime"]:
            e["dst"] = "st:h9"          # not a candidate node of this search: ignored, the default choice applies
    b, _ = run(0.15, prev=bad)
    assert retimes(b) == retimes(run(0.15)[0])


def test_prefer_keeps_only_a_tied_edge():
    tie = dict(lo=200.0, hi=250.0, d_ps=225.0)       # rise (dist 200) and fall (dist 166.5) both one value
    assert cap.sync_choice_iv(tie, TS.T, TS.AP)[1] == "rise"
    assert cap.sync_choice_iv(tie, TS.T, TS.AP, prefer="fall")[:2] == (1, "fall")
    near = dict(lo=100.0, hi=200.0, d_ps=150.0)      # rise sees two values: a preferred rise is NOT kept
    assert cap.sync_choice_iv(near, TS.T, TS.AP)[:2] == (1, "fall")
    assert cap.sync_choice_iv(near, TS.T, TS.AP, prefer="rise")[:2] == (1, "fall")


def test_default_byte_identical_without_prev():
    a, _ = run(0.15)
    root, edges, info = cap.clock_start_edges(ROWS, ctx(0.15))
    assert "prev_kept" not in info
    s, out, regs = cap.plan(copy.deepcopy(ROWS), TS.T, TS.AP, 0.05, start_edges=edges, start_root=root)
    assert dump(dict(summary=s, regions=regs, crossings=out)) == dump(
        dict(summary=a["summary"], regions=a["regions"], crossings=a["crossings"]))
    assert cap.sync_choice_iv(dict(lo=100.0, hi=200.0, d_ps=150.0), TS.T, TS.AP) == \
        cap.sync_choice_iv(dict(lo=100.0, hi=200.0, d_ps=150.0), TS.T, TS.AP, prefer=None)
