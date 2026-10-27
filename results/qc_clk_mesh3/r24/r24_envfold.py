#!/usr/bin/env python3
"""INFRA-FIRST-QC-R24: signal-environment fold for the QC top clock tree (qc_clk_mesh3 solve --top-edge-corr format).

The qc_clk_mesh3 stage table assumes full M7/M9 planes (upper bound).  The R17/R18 RCX extracted the clock alone
(empty environment, lower bound).  This fold puts the measured environment (clk_env_density.py: die GRT guides +
plan partition reserve at utilisation u) into every top-tree stage:
    stage_env = D0[c] + (seg(L) - D0[c]) * k_net        (k_net = C_env / C_model of the stage driven net, length-weighted M8+M9,
                                                           wire-load part only; intrinsic delay D0 unchanged)
    edge fold: d = sum(stage_env) - sum(seg), k = sum(stage_env) / sum(seg)
Edges -> legal cell chains exactly as solve --geometry legal (copied from results/qc_clk_mesh3/r18/r18_fold.py).
usage: r24_envfold.py ENV_NETS_JSON U OUT_JSON -- <qc_clk_mesh3 solve args>      (UNCHECKED)"""
import json
import sys
from pathlib import Path

env_path, U, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
argv = sys.argv[sys.argv.index("--") + 1:]
import qc_clk_mesh3 as M  # noqa: E402

E = json.loads(Path(env_path).read_text())
nets = E["nets"] if "nets" in E else E
key = f"k_env_u{float(U)}"
by_cell = {}
for n, r in nets.items():
    if not n.startswith("ckm_w_ckt_") or key not in r:
        continue
    idx = int(n[len("ckm_w_ckt_"):].split("_")[0])
    by_cell.setdefault(idx, []).append(r[key])


def fn(a):
    st = M.Stage(a.stage)
    B = M.build(a, st)
    rec = B["rec"]
    xs, ys = [M.r3(x) for x in rec["xs"]], [M.r3(y) for y in rec["ys"]]
    fw = M.RC3[a.fine_w]
    taps = [(M.r3(t["tap"][0]), M.r3(t["tap"][1])) for t in rec["taps"]]
    hs_f = [(y, xs[0], xs[-1]) for y in ys]
    vs_f = [(x, ys[0], ys[-1]) for x in xs]
    fd0 = sorted({(M.r3(n["xy"][0]), M.r3(n["xy"][1])) for ct in B["ctrees"] for n in ct["nodes"] if not n["kids"]})
    N0 = M.mesh(hs_f, vs_f, fd0, taps, fw, (M.RC3[a.stub_w], a.stub_um))
    m0 = M.size(M.voronoi_c(N0), a.fine_m, a.sizing)
    fm = {q: M.decompose(float(m)) for q, m in zip(fd0, m0)}
    cells, lstat = M.legalize(B, fm)
    B["cells"] = cells
    PE = M.phys_edges(B)
    idx = {id(c): i for i, c in enumerate(cells)}
    et = B["et"]["top"]
    corr = {"TT": {}, "FF": {}}
    miss = 0
    ks = []
    for (ns, tag), chain in PE.items():
        if ns != "t":
            continue
        for c in ("TT", "FF"):
            mod = env = 0.0
            for a_, b_, L in chain:
                s = et.st.seg(et.w, et.m, c, L)
                kl = by_cell.get(idx[id(a_)])
                if kl is None:
                    if c == "TT":
                        miss += 1
                    k = 1.0
                else:
                    k = sum(kl) / len(kl)
                    if c == "TT":
                        ks.append(k)
                mod += s
                env += M.D0[c] + (s - M.D0[c]) * k
            corr[c][tag] = dict(d=M.r3(env - mod), k=round(env / mod, 5) if mod else 1.0)
    dd = sorted(v["d"] for v in corr["TT"].values())
    kk = sorted(v["k"] for v in corr["TT"].values())
    summ = dict(edges=len(corr["TT"]), stages_matched=len(ks), stages_unmatched=miss, u_part=float(U),
                TT_d_ps=dict(min=dd[0], med=dd[len(dd) // 2], max=dd[-1]),
                TT_k=dict(min=kk[0], med=kk[len(kk) // 2], max=kk[-1]))
    out.write_text(json.dumps(dict(schema="ot_qc_clk_mesh3_top_edge_corr/1",
                                   basis=f"R24 signal-environment fold: die GRT guide density + partition reserve u={U}, "
                                         f"fd2d C ratio on the wire-load part of each stage (D0 intrinsic kept)",
                                   checked="UNCHECKED", summary=summ, corr=corr)))
    print(json.dumps(summ))
    return 0


M.cmd_solve = fn
sys.exit(M.main(["solve"] + argv))
