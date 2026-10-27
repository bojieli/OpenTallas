#!/usr/bin/env python3
"""QC-SU-PROG-L1 option (a') (COORD 16:xx, GEOM-REVIEW-6): replace the gate's entry->island L1 chains by a GEOMETRY H-TREE.

entry -> TW / TE trunk nodes along the entry SRAM gap row (mirrored about the entry x: equal length), TE/TW -> islands
N/S in the free SRAM gap rows (equal dy, su_tree_uf_ht.ht_points) and the E-face island along the entry row (same dy).
Every leg is a straight Manhattan run whose length is computed from the geometry before the build; repeaters at the equal
cuts of each level (same count on every edge of a level -> equal stage count on every path).  E vertical legs run at
x = xE >= E SRAM clock-pin column + 4.32.  Then the L2/L3 part of the gate's spec is kept as is, cells are sized
(option (c), su_branch_size, 12.8 d1) and the result is predicted + gated by uf_phys (phys_gate, guard band).
Checks (L1 part, replacing G4/G5 for L1): every new node in the core rows, outside every macro ROW halo / SRAM clock-pin
column / island rect; every leg clear of every macro + 2.2 um halo; every E vertical leg x >= pin column edge + 4 um.
usage: ht_l1.py GATE.json GEO LIBDIR OUTPREFIX [--seg UM]   PLAN MODEL, UNCHECKED.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phys_gate as PG  # noqa: E402
import su_branch_size as SB  # noqa: E402

ROW_HALO, HALO, CORE_EPS = 4.32, 2.2, 1e-6
REP, BIG = "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R"


def main():
    gate_p, geo, libdir, pre = sys.argv[1:5]
    SEG = float(sys.argv[sys.argv.index("--seg") + 1]) if "--seg" in sys.argv else 50.0
    g = json.loads(Path(gate_p).read_text())
    spec_p, asb_p = g["asbuilt"]["spec"], g["asbuilt"]["json"]
    core, macros = None, []
    for ln in open(geo):
        f = ln.split()
        if f and f[0] == "CORE":
            core = list(map(float, f[1:5]))
        if f and f[0] == "MACRO":
            macros.append(list(map(float, f[3:7])))
        if f and f[0] == "PIN" and f[1] == "ck":
            entry = (float(f[2]), float(f[3]))
    pincols = g["gates"]["G5_sram_structure"]["pin_columns_um"]
    isl_rects = [i["rect_um"] for i in g["gates"]["G2_island_rows"]["islands"]]
    xcol = max(q[2] for q in pincols)
    t = Path(spec_p).read_text()
    head, rest = t.split("set ot_ms_tree {", 1)
    blk, tail = rest.split("\n}", 1)
    rows = [ln for ln in blk.split("\n") if ln.strip()]
    nodes = {}
    for ln in rows:
        m = re.match(r"\s*\{(\S+) (\S+) ([\d.]+) ([\d.]+) (\S+)\}$", ln)
        nodes[m.group(1)] = [m.group(2), float(m.group(3)), float(m.group(4)), m.group(5)]
    isl = {n: v for n, v in nodes.items() if re.fullmatch(r"Q\d+", n)}
    l1rep = [n for n in nodes if re.fullmatch(r"Q\d+_r\d+", n)]
    gy = entry[1]
    xE = min(v[1] for v in isl.values() if v[1] > entry[0])     # N/S gap islands sit at the trunk x; an E-face island lies further E
    xW = 2 * entry[0] - xE
    # assign each island to its trunk side and leg; leg = (trunk, island) L path: vertical at trunk x, then horizontal
    legs = {}
    for n, v in isl.items():
        side = "TE" if v[1] > entry[0] else "TW"
        legs[n] = side
    tr = {"TE": (round(xE, 3), round(gy, 3)), "TW": (round(xW, 3), round(gy, 3))}
    L0 = {s: abs(p[0] - entry[0]) + abs(p[1] - entry[1]) for s, p in tr.items()}
    L1 = {n: abs(isl[n][1] - tr[s][0]) + abs(isl[n][2] - tr[s][1]) for n, s in legs.items()}
    K0 = max(1, math.ceil(max(L0.values()) / SEG))
    K1 = max(1, math.ceil(max(L1.values()) / SEG))
    new = []          # (name, par, x, y, cell)
    for s, p in tr.items():
        prev = "root"
        for j in range(1, K0):
            x = entry[0] + (p[0] - entry[0]) * j / K0
            new.append((f"{s}_r{j - 1}", prev, round(x, 3), round(gy, 3), REP))
            prev = f"{s}_r{j - 1}"
        new.append((s, prev, p[0], p[1], BIG))
    for n, s in legs.items():
        p, q = tr[s], (isl[n][1], isl[n][2])
        # L path p -> (p.x, q.y) -> q ; cut points along it
        pts = [p, (p[0], q[1]), q]
        tot = L1[n]
        prev = s
        for j in range(1, K1):
            d = tot * j / K1
            a = abs(pts[1][1] - pts[0][1])
            if d <= a:
                x, y = p[0], p[1] + math.copysign(d, q[1] - p[1])
            else:
                x, y = p[0] + math.copysign(d - a, q[0] - p[0]), q[1]
            new.append((f"{n}_h{j - 1}", prev, round(x, 3), round(y, 3), REP))
            prev = f"{n}_h{j - 1}"
        isl[n][0] = prev
    # ---- checks (L1 part)
    def in_rowhalo(x, y):
        return any(r[0] - ROW_HALO < x < r[2] + ROW_HALO and r[1] - ROW_HALO < y < r[3] + ROW_HALO for r in macros)

    def in_pc(x, y):
        return any(q[0] <= x <= q[2] and q[1] <= y <= q[3] for q in pincols)

    bad_nodes = [dict(node=a, xy=[x, y]) for a, _, x, y, _ in new
                 if not (core[0] <= x <= core[2] and core[1] <= y <= core[3]) or in_rowhalo(x, y) or in_pc(x, y)
                 or any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for R in isl_rects)]
    pos = {"root": entry, **{a: (x, y) for a, _, x, y, _ in new}, **{n: (v[1], v[2]) for n, v in isl.items()}}
    segs = [(pos[a], pos[p_]) for a, p_, *_ in new] + [(pos[n], pos[isl[n][0]]) for n in isl]

    def seg_hits(a, b):
        out = []
        # L-shaped legs: vertical first (at the driver x), then horizontal
        pts = [b, (b[0], a[1]), a] if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6 else [b, a]
        for u, v in zip(pts, pts[1:]):
            x0, x1, y0, y1 = min(u[0], v[0]), max(u[0], v[0]), min(u[1], v[1]), max(u[1], v[1])
            for r in macros:
                if x0 < r[2] + HALO and x1 > r[0] - HALO and y0 < r[3] + HALO and y1 > r[1] - HALO:
                    out.append(r)
            if abs(u[0] - v[0]) < 1e-6 and u[0] > entry[0] and u[0] < xcol + 4.0 and y1 - y0 > 1e-6:
                out.append(["vertical E leg within 4 um of the pin column", u[0]])
        return out
    bad_legs = [dict(a=a, b=b, hits=h) for a, b in segs for h in [seg_hits(a, b)] if h]
    # ---- new spec + seg json
    keep = [ln for ln in rows if re.match(r"\s*\{(\S+) ", ln).group(1) not in l1rep]
    out_rows = [f" {{{a} {p_} {x:.3f} {y:.3f} {c}}}" for a, p_, x, y, c in new]
    for ln in keep:
        m = re.match(r"\s*\{(\S+) (\S+) ([\d.]+) ([\d.]+) (\S+)\}$", ln)
        if m.group(1) in isl:
            v = isl[m.group(1)]
            ln = f" {{{m.group(1)} {v[0]} {m.group(3)} {m.group(4)} {m.group(5)}}}"
        out_rows.append(ln)
    spec_o = pre + ".tcl"
    Path(spec_o).write_text("# QC-SU-PROG-L1 option (a') geometry H-tree L1 (ht_l1.py) on " + Path(spec_p).name + "\n" + head +
                            "set ot_ms_tree {\n" + "\n".join(out_rows) + "\n}" + tail)
    A = json.loads(Path(asb_p).read_text())
    seg = {k_: v for k_, v in A["seg_um"].items() if k_ not in l1rep and k_ not in isl}
    for a, p_, x, y, _ in new:
        seg[a] = round(abs(x - pos[p_][0]) + abs(y - pos[p_][1]), 3)
    for n in isl:
        seg[n] = round(abs(isl[n][1] - pos[isl[n][0]][0]) + abs(isl[n][2] - pos[isl[n][0]][1]), 3)
    A["seg_um"] = seg
    asb_o = pre + ".seg.json"
    Path(asb_o).write_text(json.dumps(A))
    sz = SB.size(spec_o, asb_o, geo, libdir)
    spec_s = pre + ".sized.tcl"
    SB.write_spec(spec_o, sz["cells"], spec_s, "QC-SU-PROG-L1 per-branch sizing (12.8 d1, uf_phys) of " + Path(spec_o).name)
    ph = PG.predict_file(spec_s, asb_o, geo, libdir, extra_inputs=[gate_p, spec_p, asb_p, __file__])
    other = {k_: v["verdict"] for k_, v in g["gates"].items() if k_ in ("G1_macro_orient", "G2_island_rows", "G3_cell_rows")}
    g4 = g["gates"]["G4_detour_sites"]
    g4_l23 = [e for e in g4["edges"] if e["level"] != "L1" and not e["ok"]]
    g5 = g["gates"]["G5_sram_structure"]
    g5_bad = [x for x in g5["nodes_in_pin_column"] if not re.fullmatch(r"Q\d+_r\d+", x["node"])] + \
             [x for x in g5["legs_across_sram"] if not re.fullmatch(r"Q\d+", x["edge"])]
    rep = dict(scope="QC-SU-PROG-L1 option (a') geometry H-tree L1 + (c) sizing; uf_phys gate; PLAN MODEL, UNCHECKED",
               gate_json=gate_p, gate_json_sha256=PG.sha(gate_p), trunk=tr, trunk_len_um={k_: round(v, 2) for k_, v in L0.items()},
               leg_len_um={k_: round(v, 2) for k_, v in L1.items()}, repeaters=dict(L1a=K0 - 1, L1b=K1 - 1), seg_um=SEG,
               xcol_E=xcol, xE=xE, xW=xW, new_nodes=new,
               checks=dict(L1_nodes_bad=bad_nodes, L1_legs_bad=bad_legs, G1_G3=other,
                           G4_L2_L3_fail=[e["edge"] for e in g4_l23], G5_L2_L3_bad=g5_bad),
               sizing={k_: v for k_, v in sz.items() if k_ != "cells"}, spec=spec_s, spec_sha256=PG.sha(spec_s),
               seg_json=asb_o, phys=ph)
    ok = (not bad_nodes and not bad_legs and all(v == "PASS" for v in other.values()) and not g4_l23 and not g5_bad)
    rep["structure_verdict"] = "PASS" if ok else "FAIL"
    rep["verdict"] = "PASS" if ok and ph["gate"]["verdict"] == "PASS" else "FAIL"
    rep["provenance"] = dict(argv=[sys.executable] + list(sys.argv), sha256={p: PG.sha(p) for p in (gate_p, geo, spec_p, asb_p, __file__)})
    Path(pre + ".ht.json").write_text(json.dumps(rep, indent=1))
    print("HT_L1", pre, "trunk", rep["trunk_len_um"], "legs", rep["leg_len_um"], "reps", rep["repeaters"], "struct", rep["structure_verdict"],
          "bad", len(bad_nodes), len(bad_legs), len(g4_l23), len(g5_bad))
    print(" ", PG.line(ph), "VERDICT", rep["verdict"])


if __name__ == "__main__":
    main()
