#!/usr/bin/env python3
"""TOKg 10-23: checks of the coll_images.py transport (compiler calendar) retiming.  No simulator.

  PYTHONPATH=tools python3 tools/hbm_layer_vehicle/test_coll_transport.py [--transport t.json] [--codex-retiming r.json
      --tb tb_slice.sv]

1. transport None == the GEN2 schedule (byte-identical events).
2. With a profile: every gather edge moves by launch_edges (ring outputs, VM / fault checks), each far-end drive by
   launch_edges - ingress_edges[port]; host-ingress programme + configured check + VM preload unchanged; values same.
3. Mutants: B-CCW ingress omitted -> exactly the 33 hcollb_SE__ccw_o drives move +20 (the causal negative that FAILS
   in the slice); launch 47 instead of 48 -> every check moves; both differ from the profile output.
4. --codex-retiming: the tool's retiming of DS L0 rec2 equals the hand-built, slice-validated corrected_rec2 change set.
5. A launch lane trailing the calendar launch by more than the 96-edge grant margin is refused (format_open).
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import numpy as np  # noqa: E402

from hbm_layer_vehicle import coll_images as CI  # noqa: E402

FIX = TOOLS.parent / "results/rtl/hbm_ds_layer_tput_1018/fixtures/L00"
R18H5 = dict(schema="opentallas.hbm_coll_transport.v1", launch_edges=48, calendar_launch_edges=24,
             ingress_edges={"hb_coll_NW__pr_cw_o": 6, "hb_coll_SE__pr_ccw_o": 18, "hcollb_NW__cw_o": 4,
                            "hcollb_SE__ccw_o": 20})


def rec(i_rec, fix):
    meta, z, recs = CI.load_fixture_records(fix)
    for x in recs:
        pr = x.get("priced") or []
        if x["op"] == "COLL.ALL_GATHER" and pr and int(pr[0]["i"]) == i_rec:
            return np.asarray(z[x["outputs"]["O"]["array"]], np.uint32)
    raise KeyError(i_rec)


def evs(g):
    return g["events"] + g["chk_vm"] + g["chk_ring"] + g["chk_misc"]


def deltas(a, b):
    """Counter of ((kind, port class), cycle delta) pairing identical events in order."""
    key = lambda e: (e["k"], e.get("port", "M"), e.get("val"), e.get("sector"))
    qa, qb = {}, {}
    for e in a:
        qa.setdefault(key(e), []).append(e["cyc"])
    for e in b:
        qb.setdefault(key(e), []).append(e["cyc"])
    assert qa.keys() == qb.keys() and all(len(qa[k]) == len(qb[k]) for k in qa), "event sets differ beyond timing"
    out = Counter()
    for k in qa:
        for c0, c1 in zip(sorted(qa[k]), sorted(qb[k])):
            if c1 != c0:
                out[((k[0], "vm" if k[1].startswith("vm:") else k[1]), c1 - c0)] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transport", type=Path)
    ap.add_argument("--fixtures", type=Path, default=FIX)
    ap.add_argument("--record", type=int, default=2)
    ap.add_argument("--vm-rt", type=int, default=95)
    ap.add_argument("--codex-retiming", type=Path)
    ap.add_argument("--tb", type=Path)
    a = ap.parse_args()
    T = json.loads(a.transport.read_text()) if a.transport else R18H5
    O = rec(a.record, a.fixtures)
    base = CI.gather_record(O, a.record, vm_rt=a.vm_rt)
    assert base["status"] == "emitted"
    # 1
    assert evs(CI.gather_record(O, a.record, vm_rt=a.vm_rt, transport=None)) == evs(base)
    # 2
    g = CI.gather_record(O, a.record, vm_rt=a.vm_rt, transport=T)
    d = deltas(evs(base), evs(g))
    Ls, ing = T["launch_edges"], T["ingress_edges"]
    for ((k, p), dl), n in d.items():
        if k == "D":
            assert p in ing and dl == Ls - ing[p], (p, dl)
        else:
            assert dl == Ls and p != "hcollgi_SW__configured", (p, dl)
    moved = Counter()
    for ((k, p), _), n in d.items():
        moved[p] += n
    assert moved["vm"] == len(base["chk_vm"]) and all(moved[p] for p in CI.OUT_PORTS.values())
    assert not any(e["src"].startswith("image:") and e["k"] == "D" for e in evs(base)
                   if (e["k"], e.get("port")) in {(k, p) for (k, p), _ in d}), "host programme moved"
    print(f"retime OK: launch {Ls}, drives {dict((p, Ls - v) for p, v in ing.items())}, "
          f"{sum(n for ((k, _), _), n in d.items() if k == 'C')} checks +{Ls}")
    # 3
    Tm = copy.deepcopy(T)
    Tm["ingress_edges"]["hcollb_SE__ccw_o"] = 0
    dm = deltas(evs(g), evs(CI.gather_record(O, a.record, vm_rt=a.vm_rt, transport=Tm)))
    assert set(dm) == {(("D", "hcollb_SE__ccw_o"), ing["hcollb_SE__ccw_o"])}, dm
    T2 = copy.deepcopy(T)
    T2["launch_edges"] = Ls - 1
    d2 = deltas(evs(g), evs(CI.gather_record(O, a.record, vm_rt=a.vm_rt, transport=T2)))
    assert sum(n for ((k, _), _), n in d2.items() if k == "C") == sum(n for ((k, _), _), n in d.items() if k == "C")
    print(f"mutants OK: omit B-CCW -> {sum(dm.values())} drives +{ing['hcollb_SE__ccw_o']}; launch-1 -> all checks -1")
    # 4
    if a.codex_retiming:
        tb = a.tb.read_text()
        inp = {int(i): n for i, n in re.findall(r"^\s+(\d+): (\w+) <= v\[", tb, re.M)}
        out = {int(i): n for i, n in re.findall(r"^\s+(\d+): sample\[.*?\] = (\w+);", tb, re.M)}
        ch = json.loads(a.codex_retiming.read_text())["changes"]
        want = Counter(((("D", inp[c["port"]]) if c["kind"] == 1 else
                         ("C", out.get(c["port"], "vm"))), c["new"] - c["old"])
                       for c in ch)
        # the slice TB compares VM words through vm_* sample ports; fold those into "vm"
        want = Counter({((k, "vm" if (k == "C" and p not in CI.OUT_PORTS.values() and "fault" not in p) else p), dl): n
                        for ((k, p), dl), n in want.items()})
        assert want == d, (sorted(want.items()), sorted(d.items()))
        print(f"codex corrected_rec2 retiming: IDENTICAL ({sum(d.values())} moved events)")
    # 5
    T3 = copy.deepcopy(T)
    T3["calendar_launch_edges"] = Ls - 97
    assert CI.gather_record(O, a.record, vm_rt=a.vm_rt, transport=T3)["status"] == "format_open"
    print("TEST_COLL_TRANSPORT PASS")


if __name__ == "__main__":
    main()
