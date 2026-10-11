#!/usr/bin/env python3
"""Per-record SU/SFU census on the production token programs: priced cost (timing.cost), the VM sectors the D1 peer
stages (A/B/C/D spans) and drains (O/R spans) per record, at the record's real descriptors."""
import json, sys, collections
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[1]; ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
from hgi_sim import timing as T, qwen_compiler as QC

def span_secs(d, dyn, L, half=False):
    base, n, m, st, ist = T.eff(d, dyn, L)
    if half: n = (n + 1) // 2
    lo = base; hi = base + max(0, m - 1) * st + max(0, n - 1) * ist
    return (hi >> 3) - (lo >> 3) + 1, (m * n)

def census(recs, pos, name):
    dyn = T.Dyn(pos)
    rows = []
    for k, L, L1 in T.expand(recs, pos):
        r = recs[k]
        if r.unit not in ("SU", "SFU"): continue
        c, g, how = T.cost(r, dyn, L)
        half = r.unit == "SU" and r.sut and r.sut.get("b_half")
        st = dr = 0; regs = []
        for kk, d in r.desc.items():
            if d.space != "VM": 
                regs.append((kk, d.space)); continue
            s, nel = span_secs(d, dyn, L, half and kk in ("B", "D"))
            regs.append((kk, s, nel))
            if kk in ("O", "R"): dr += s
            else: st += s
        rows.append(dict(tag=r.tag, unit=r.unit, cost=c, stage_secs=st, drain_secs=dr, regs=regs))
    return rows

if __name__ == "__main__":
    cfg = json.loads((ROOT / "compiler/models/qwen3-8b/config.json").read_text())
    q = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), 1)
    rows = census(q, 8191, "qwen")
    agg = collections.defaultdict(lambda: [0, 0.0, 0, 0])
    for x in rows:
        a = agg[(x["unit"], x["tag"])]; a[0] += 1; a[1] += x["cost"]; a[2] += x["stage_secs"]; a[3] += x["drain_secs"]
    tot = [0, 0, 0]
    for (u, t), a in agg.items():
        print(f"{u:4s} {t:28s} n={a[0]:3d} cost={a[1]:9.1f} stage_secs={a[2]:7d} drain_secs={a[3]:7d}")
        tot[0] += a[1]; tot[1] += a[2]; tot[2] += a[3]
    print("TOTAL per layer cost", tot)
    for x in rows[:40]: print(x["tag"], x["regs"])
