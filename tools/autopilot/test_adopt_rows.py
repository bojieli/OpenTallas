"""WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1700 item 3): apply keeps every current gen host (replicate + verify or refuse); the wave accounts for adoption rows and alerts."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_reviewed_tree_marker as AM
import kit_wave as KW


def test_apply_replicates_to_the_current_gen_hosts_the_candidate_drops():
    calls = []

    def run(cmd):
        calls.append(cmd)
        return 0, "ok"
    hosts, info = AM.ensure_tree_on_hosts("/t/new", "h" * 64, ["epyc8", "epyc9", "epyc10"], ["epyc9", "epyc8"], "/rt", run=run, link_from="old")
    assert hosts == ["epyc9", "epyc8", "epyc10"] and info                                  # never narrowed: epyc10 stays, after replicate + verify
    assert "replicate /t/new --hosts epyc10 --link-from old" in calls[0] and "hosts /t/new --hosts epyc10 --expect " + "h" * 64 in calls[1]
    assert AM.ensure_tree_on_hosts("/t/new", "h", ["epyc9"], ["epyc9", "epyc8"], "/rt", run=run) == (["epyc9", "epyc8"], [])      # nothing dropped: no work


def test_apply_drops_a_host_whose_replication_or_verification_fails():
    # LATENCY-R 11-18: a host that cannot take the tree is dropped from the die (named DROPPED), not a refusal of the whole apply
    hosts, notes = AM.ensure_tree_on_hosts("/t/n", "h", ["epyc10"], ["epyc9"], "/rt", run=lambda c: (1, "disk full"))
    assert hosts == ["epyc9"] and notes and notes[0].startswith("DROPPED epyc10") and "disk full" in notes[0]
    seq = iter([(0, ""), (1, "hash differs")])
    hosts, notes = AM.ensure_tree_on_hosts("/t/n", "h", ["epyc10"], ["epyc9"], "/rt", run=lambda c: next(seq))
    assert hosts == ["epyc9"] and "hash differs" in notes[0]


class AP:
    DRY = False
    logs, notes = [], []
    log = staticmethod(lambda m: AP.logs.append(m))
    coord_append = staticmethod(lambda rel, line: AP.notes.append(line))


def cfg(src):
    return {"dies": {"qc": {"enabled": True, "src": src, "event": "E2", "owner_lane": "QC-PLAN-R3", "_plan_types": ["t1", "t2", "t3"]}}}


def rows(**kw):
    return {"items": {f"k{i}": dict(die="qc", item=it, event=ev, **extra) for i, (it, ev, extra) in enumerate(kw["r"])}}


def test_adopt_rows_accounting_and_alert_after_two_ticks():
    AP.logs.clear(); AP.notes.clear()
    st = rows(r=[("t1", "E1", {"class": "SUPERSEDED"}), ("t2", "E1", {"class": "SUPERSEDED"}), ("t3", "E1", {})])
    assert KW.adopt_rows_tick(AP, cfg("/k/d1"), st) == {}                                   # first sight is the baseline, not a switch
    assert KW.adopt_rows_tick(AP, cfg("/k/d2"), st) == {} and "tree switched d1 -> d2" in AP.logs[-1]
    out = KW.adopt_rows_tick(AP, cfg("/k/d2"), st)                                          # tick 1: nothing created yet
    assert out["qc"] == (0, 3, ["t1", "t2", "t3"]) and not AP.notes and "0/3 plan types" in AP.logs[-1] and "2 superseded on the old tree" in AP.logs[-1]
    KW.adopt_rows_tick(AP, cfg("/k/d2"), st)                                                # tick 2: alert once
    assert len(AP.notes) == 1 and "NEEDS-LANE [ADOPT-ROWS -> QC-PLAN-R3]" in AP.notes[0] and "t1, t2, t3" in AP.notes[0]
    KW.adopt_rows_tick(AP, cfg("/k/d2"), st)
    assert len(AP.notes) == 1                                                               # never twice
    st["items"]["new1"] = dict(die="qc", item="t1", event="E2")
    st["items"]["new2"] = dict(die="qc", item="t2", event="E2")
    st["items"]["new3"] = dict(die="qc", item="t3", event="E2")
    assert KW.adopt_rows_tick(AP, cfg("/k/d2"), st)["qc"] == (3, 3, [])                     # every type has a current row: done, no more lines
    n = len(AP.logs)
    assert KW.adopt_rows_tick(AP, cfg("/k/d2"), st) == {} and len(AP.logs) == n
