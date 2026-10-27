#!/usr/bin/env python3
"""INFRA-FIRST-QC-R18: model vs RCX on the R17 explicit clock, per top-tree edge and per column tap (A pin).
usage: r18_cmp.py FOLD_DIR STA_DIR BASIS OUT_DIR
  FOLD_DIR/edges.json, taps.json (r18_fold.py); STA_DIR/tree_<C>_<BASIS>.txt (R18 sta.tcl: N / A / T lines)
writes OUT_DIR/cmp_<BASIS>.json (summary + per-tap) and OUT_DIR/top_edge_corr_<BASIS>.json (qc_clk_mesh3 --top-edge-corr)"""
import json
import sys
from pathlib import Path
import statistics as S

fold, sta, basis, out = (Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
out.mkdir(parents=True, exist_ok=True)
E = json.loads((fold / "edges.json").read_text())
edges, parent = E["edges"], E["parent"]
taps = json.loads((fold / "taps.json").read_text())


def rd(p):
    A, Y, T = {}, {}, {}
    for ln in open(p):
        f = ln.split()
        if len(f) != 5:
            continue
        v = (float(f[2]), float(f[3]), float(f[4]))
        if f[0] == "A":
            A[f[1][2:]] = v
        elif f[0] == "N":
            Y[f[1]] = v
        elif f[0] == "T":
            T[f[1]] = v
    return A, Y, T


def q(v):
    v = sorted(v)
    return dict(min=round(v[0], 2), p50=round(S.median(v), 2), max=round(v[-1], 2), spread=round(v[-1] - v[0], 2))


summ, corr, per_tap = {}, {}, {}
for c in ("TT", "FF"):
    A, Y, T = rd(sta / f"tree_{c}_{basis}.txt")
    a = lambda i, k=0: A[f"ckt_{i}_0"][k]
    cc, rat, dl = {}, [], []
    for tag, e in edges.items():
        if e["ns"] != "t":
            continue
        r_ = a(e["cells"][-1]) - a(e["cells"][0])
        m_ = e["model"][c]
        cc[tag[2:]] = dict(d=round(r_ - m_, 3), k=round(r_ / m_, 5) if m_ > 0 else 1.0)
        rat.append(r_ / m_)
        dl.append(r_ - m_)
    corr[c] = cc
    # per tap: model path (sum of model edges root -> leaf) vs RCX A(col_tap) - A(tree root cell)
    mp, rp, ra, ty, tl = [], [], [], [], []
    root_tag = [t for t, p in parent.items() if p is None][0]
    root_cell = None
    for tg, e in edges.items():
        if e["ns"] == "t" and parent.get(tg) == root_tag:
            root_cell = e["cells"][0]
            break
    r0 = a(root_cell)
    for port, t in taps.items():
        tg = "t:" + t["leaf"]
        m_, k = 0.0, tg
        while parent.get(k):
            m_ += edges[k]["model"][c]
            k = parent[k]
        ar = a(t["cell"])
        mp.append(m_)
        rp.append(ar - r0)
        ra.append(ar)
        ty.append(Y[f"ckt_{t['cell']}_0"][0])
        tl.append(float("nan"))
        per_tap.setdefault(port, {})[c] = dict(model_path=round(m_, 2), rcx_A=round(ar, 2), rcx_Y=round(ty[-1], 2),
                                               rcx_port=round(tl[-1], 2), rcx_path=round(ar - r0, 2))
    d = [x - y for x, y in zip(mp, rp)]
    summ[c] = dict(taps=len(mp), model_path_ps=q(mp), rcx_path_ps=q(rp), rcx_colTap_A_ps=q(ra), rcx_colTap_Y_ps=q(ty),
                   root_cell_A_ps=round(r0, 2),
                   model_minus_rcx_ps=q(d), rcx_over_model_path=q([y / x for x, y in zip(mp, rp)]),
                   edge_ratio_rcx_over_model=q(rat), edge_delta_ps=q(dl), edges=len(cc),
                   slew_max_ps=round(max(v[2] for v in list(A.values()) + list(Y.values())), 2))
(out / f"cmp_{basis}.json").write_text(json.dumps(dict(summary=summ, per_tap=per_tap), indent=0))
(out / f"top_edge_corr_{basis}.json").write_text(json.dumps(dict(
    schema="ot_qc_clk_mesh3_top_edge_corr/1", basis=f"R17 routed clock RCX ({basis}), R18 sta.tcl with real tap loads",
    checked="UNCHECKED", corr=corr)))
print(json.dumps(summ, indent=1))
