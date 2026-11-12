#!/usr/bin/env python3
"""HBM-VSN-XTAP-2 11-12 d12b = d12 + A/B split (DIE-HBM-100 ruling): types whose type-level latch would pass ~350k
cells (or that have no kit census) get clock.ft_hop_lockup.hops = the cross-port hops whose flop form fails the paper
check (ab_split.py); their tap / latch_frac keys are kept only for listed hops.  Other ops of d12 unchanged.
mk_d12b.py D12_DELTA AB_HOPS_JSON OUT_DELTA"""
import copy, hashlib, json, sys
from pathlib import Path

d12p, hopsp, outp = sys.argv[1:4]
d = json.loads(Path(d12p).read_text())
hops = json.loads(Path(hopsp).read_text())
ops = d["files"]["die_plan.json"]["ops"]
idx = {tuple(p): i for i, (p, op, v) in enumerate(ops)}
tap = copy.deepcopy(ops[idx[("clock", "ft_hop_lockup", "tap")]][2])
frac = copy.deepcopy(ops[idx[("clock", "ft_hop_lockup", "latch_frac")]][2])
dropped = 0
for m in (tap, frac):
    for t in list(m):
        if t not in hops:
            continue
        for s in list(m[t]):
            keep = {k: v for k, v in m[t][s].items() if int(k) in set(hops[t].get(s, []))}
            dropped += len(m[t][s]) - len(keep)
            if keep:
                m[t][s] = keep
            else:
                del m[t][s]
        if not m[t]:
            del m[t]
ops[idx[("clock", "ft_hop_lockup", "tap")]][2] = tap
ops[idx[("clock", "ft_hop_lockup", "latch_frac")]][2] = frac
i = idx[("clock", "ft_hop_lockup", "latch_frac")]
ops.insert(i + 1, [["clock", "ft_hop_lockup", "hops"], "set", hops])
ni = [j for j, (p, op, v) in enumerate(ops) if p == ["clock", "ft_hop_lockup", "note"]][0]
ops[ni][2] += ("  11-12 A/B split (DIE-HBM-100): types whose type-level latch would pass ~350k cells or that have no kit "
               "cell census latch only the hops in ft_hop_lockup.hops (cross-port hops whose flop form fails the paper "
               "check); the others latch every hop.")
d["name"] = "d12b_formAp_ab_1112"
d["source"] = "HBM-VSN-XTAP-2 (DIE-HBM-100 11-12, A/B split ruling)"
Path(outp).write_text(json.dumps(d, indent=1) + "\n")
print("B types", len(hops), "listed hops", sum(len(k) for m in hops.values() for k in m.values()),
      "tap/frac entries dropped", dropped, "delta", hashlib.sha256(Path(outp).read_bytes()).hexdigest()[:12])
