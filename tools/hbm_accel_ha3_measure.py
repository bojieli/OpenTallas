#!/usr/bin/env python3
"""HA3: per-collective critical-path cycles from the +TRACE logs of tools/hbm_accel_ha3_run.py (Qwen reduced system).

For every layer kernel (4 per decode step) and die, on the die's critical path (the LAST SM of the die):
  AR_o  last SM's o-proj tensor-core result (TCDONE #2)  ->  last SM's gate/up TCWAIT (#3): the all-reduce of the
        attention output, the residual add, the post-attention rmsnorm and the gate/up x staging
  AR_d  last SM's down-proj result (TCDONE #4)  ->  last SM's kernel DONE: the all-reduce of the MLP output, the
        residual add and the X store
The non-collective work inside both sections is the same instruction sequence in every program mode, so the
difference between modes is the collective + epilogue change.

    python3 tools/hbm_accel_ha3_measure.py --log base=A.log --log cut=C.log ... --out measured.json
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
from pathlib import Path


def sections(path):
    ev = {}
    steps = []
    for line in Path(path).read_text().splitlines():
        if line.startswith("CT ") and len(line.split()) >= 5:
            f = line.split()
            ev.setdefault((int(f[2][1:]), int(f[3][1:])), []).append((int(f[1]), f[4]))
        m = re.match(r"STEP (\d+) .*\(step (\d+) clk_sm", line)
        if m:
            steps.append(int(m.group(2)))
    # split each SM's events into kernels (LAUNCH .. DONE)
    kern = {}
    for k, es in ev.items():
        cur = None
        out = []
        for c, e in es:
            if e == "LAUNCH":
                cur = [(c, e)]
            elif cur is not None:
                cur.append((c, e))
                if e == "DONE":
                    out.append(cur)
                    cur = None
        kern[k] = out
    nk = min(len(v) for v in kern.values())
    ar_o, ar_d = [], []
    parts = {}
    for d in (0, 1):
        sms = [k for k in kern if k[0] == d]
        for i in range(nk):
            ks = [kern[k][i] for k in sms]
            tcd = [[c for c, e in kk if e == "TCDONE"] for kk in ks]
            tcw = [[c for c, e in kk if e == "TCWAIT"] for kk in ks]
            if any(len(t) != 4 for t in tcd):
                continue                                # embed / head kernels
            ar_o.append(max(t[2] for t in tcw) - max(t[1] for t in tcd))
            done = [kk[-1][0] for kk in ks]
            ar_d.append(max(done) - max(t[3] for t in tcd))
            for nm, lo, hi in (("ar_o", max(t[1] for t in tcd), max(t[2] for t in tcw)),
                               ("ar_d", max(t[3] for t in tcd), max(done))):
                bw, cw = [], []
                for kk in ks:
                    b = c = 0
                    t_bar = t_req = None
                    for cy, e in kk:
                        if not (lo <= cy <= hi):
                            continue
                        if e == "BAR":
                            t_bar = cy
                        elif e == "BARREL" and t_bar is not None:
                            b += cy - t_bar
                        elif e == "REQ":
                            t_req = cy
                        elif e == "RSP" and t_req is not None:
                            c += cy - t_req
                    bw.append(b)
                    cw.append(c)
                parts.setdefault(nm + "_barrier_wait", []).append(max(bw))
                parts.setdefault(nm + "_collective_wait", []).append(max(cw))
    return dict(n_layer_kernels_x_dies=len(ar_o), ar_o_mean=st.mean(ar_o), ar_o_median=st.median(ar_o),
                ar_o_min=min(ar_o), ar_o_max=max(ar_o), ar_d_mean=st.mean(ar_d), ar_d_median=st.median(ar_d),
                ar_d_min=min(ar_d), ar_d_max=max(ar_d), step_cycles=steps, total_step_cycles=sum(steps),
                breakdown_mean={k: round(st.mean(v), 1) for k, v in parts.items()},
                breakdown_note="max over the die's SMs, inside the section: cycles waiting at BAR (arrive->release) "
                               "and in a collective (issue->response)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", required=True, help="mode=path")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = {m: sections(p) for m, p in (x.split("=", 1) for x in a.log)}
    if "base" in res:
        b = res["base"]
        for m, r in res.items():
            r["saved_vs_base"] = dict(ar_o=round(b["ar_o_mean"] - r["ar_o_mean"], 1),
                                      ar_d=round(b["ar_d_mean"] - r["ar_d_mean"], 1),
                                      per_layer=round(b["ar_o_mean"] + b["ar_d_mean"] - r["ar_o_mean"] - r["ar_d_mean"], 1),
                                      total_step_cycles=b["total_step_cycles"] - r["total_step_cycles"])
    txt = json.dumps(res, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n")
    print(json.dumps({m: {k: v for k, v in r.items() if k != "step_cycles"} for m, r in res.items()}, indent=1))


if __name__ == "__main__":
    main()
