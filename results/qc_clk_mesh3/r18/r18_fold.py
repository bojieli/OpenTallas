#!/usr/bin/env python3
"""INFRA-FIRST-QC-R18: model side of the model-vs-RCX fold for the d43b explicit clock.
Runs qc_clk_mesh3 build + legalize exactly as `solve --geometry legal` does, then writes
  edges.json   : every top-tree edge (ns 't') -> chain of legal cell indices (= ckt_<idx>_* groups of the export) and
                 the model nominal stage delay per corner (Stage.seg per real pin-to-pin net, as edge_var_phys)
  taps.json    : every column tap (= top leaf, merged level) -> cell idx, port t_g<idx>, real downstream load:
                 first column-tree nets (col 4w, model RC) + child BUF A pins (units x BUF_CIN_FF)
  tap_loads.tcl: set_load per tap port (fF, ASAP7 lib unit)
usage: python3 r18_fold.py OUTDIR -- <qc_clk_mesh3 solve args (same as pipe.sh)>"""
import json
import sys
from pathlib import Path

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:]
import qc_clk_mesh3 as M  # noqa: E402


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
    so = B["site_of"]
    et = B["et"]
    E = {}
    for (ns, tag), chain in PE.items():
        e = et["top"] if ns == "t" else et["col"]
        cs = [idx[id(chain[0][0])]] + [idx[id(b)] for _, b, _ in chain]
        E[f"{ns}:{tag}"] = dict(ns=ns, cells=cs, L=[M.r3(L) for _, _, L in chain], w=e.w, m=e.m,
                                model={c: M.r3(sum(st.seg(e.w, e.m, c, L) for _, _, L in chain)) for c in ("TT", "FF")})
    tby = {n["tag"]: n for n in B["top_nodes"]}
    parent = {f"t:{n['tag']}": (f"t:{n['parent']}" if n.get("parent") else None) for n in B["top_nodes"]}
    T = {}
    col = et["col"]
    for ct in B["ctrees"]:
        r = ct["root"]
        ci = so[("c", r)]
        kids = [n for n in ct["nodes"] if n.get("parent") == r]
        legs, pins = [], 0
        for k in kids:
            ch = PE[("c", k["tag"])]
            legs.append(M.r3(ch[0][2]))
            pins += ch[0][1]["units"]
        leaf = [t for t, n in tby.items() if not n["kids"] and so[("t", t)] == ci]
        cfF = sum(legs) * max(v[1] for v in M.RC3[col.w].values())
        T[f"t_g{ci}"] = dict(cell=ci, leaf=leaf[0] if leaf else None, tap_xy=ct["tap"], legs_um=legs, child_units=pins,
                             wire_fF=M.r3(cfF), pin_fF=M.r3(pins * M.BUF_CIN_FF), load_fF=M.r3(cfF + pins * M.BUF_CIN_FF),
                             site=[M.r3(v) for v in cells[ci]["site"]])
    (out / "edges.json").write_text(json.dumps(dict(edges=E, parent=parent, top_root=B["top_root"] if isinstance(B["top_root"], str) else B["top_root"].get("tag") if isinstance(B["top_root"], dict) else None,
                                                    col_rc=M.RC3[col.w], legal=lstat if isinstance(lstat, dict) else None), indent=0))
    (out / "taps.json").write_text(json.dumps(T, indent=0))
    with open(out / "tap_loads.tcl", "w") as f:
        f.write("# INFRA-FIRST-QC-R18 real column-tree load per tap port (fF): first col 4w legs x model C + child BUF A pins\n")
        for p, v in sorted(T.items()):
            f.write(f"set_load {v['load_fF']} [get_ports {p}]\n")
    L = [v["load_fF"] for v in T.values()]
    print(json.dumps(dict(edges=len(E), taps=len(T), load_fF=dict(min=min(L), max=max(L), med=sorted(L)[len(L) // 2]),
                          col=(col.w, col.m, M.RC3[col.w]))))
    return 0


M.cmd_solve = fn
sys.exit(M.main(["solve"] + argv))
