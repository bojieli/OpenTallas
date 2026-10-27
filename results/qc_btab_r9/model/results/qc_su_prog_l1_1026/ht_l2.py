#!/usr/bin/env python3
"""QC-SU-PROG-L2 (COORD RULING QC-SU-PROG-L1 (4), GEOM-REVIEW-6 16:39 PASS-COND): 3-LEVEL GEOMETRY H-TREE for prog.

Level 1 (unchanged, ht_l1.py H5, GEOM-6 L1 PASS): entry -> TW/TE trunk nodes along the y 135 gap (112.31 um each, mirrored)
  -> N/S legs to the gap-row islands Q0..Q3 + the E-face island Q4 (55-57 um).
Level 2 (NEW, this tool): every island branches to SUB-ISLANDS at ONE leg length D2 (equal for every sub-island of the die,
  within LEN_TOL 2.16 um), the sub-island count per island = ceil(B nodes / 2) (load shared by count, GEOM-6 (2));
  each sub-island is an 8.64 um island rect on the 4.32 PG lattice (G2 rules), outside every SRAM ROW halo, every SRAM
  clock-pin column + CLR clearance, every other island rect.  The site set and the B -> sub-island assignment are chosen
  from geometry only: exhaustive partition of the island's B nodes into the sub-island groups, each group's site = the legal
  rect at leg length D2 minimising the group's max sub-island -> B maze length (then the sum).
Level 3: sub-island -> B node (the gate's B sites, membership frozen), straight shortest legal path, the same repeater count on
  every edge (equal cuts of each edge's own path, chain-pinned).  Level 4: B -> leaf driver (gate's leaves, frozen membership),
  straight.  Unequal L3/L4 lengths are balanced ONLY by plan-computed per-branch sizing (12.8 d1, su_branch_size), never by
  trims.
ROUTING: every tree leg below L1 is a MAZE path on a grid that blocks every macro + 2.2 um halo AND every SRAM clock-pin
  column widened by CLR (>= 4 um, default 4.32) on both sides -> 0 SRAM crossings and >= CLR clearance by construction.
  Every tree node (sub-island, repeater, B, leaf driver) is additionally kept out of the 4.32 macro ROW halo; B / leaf sites
  inside the clearance band are re-sited to the nearest legal cell (their leaf nets to the sinks inside the column are the
  sinks' own nets and are exempt).  CHECKS on EVERY leg incl. the L1 L-paths (leg_clearance(): no leg point inside
  [col.x0 - CLR, col.x1 + CLR] x [col.y0, col.y1] of any column, no point inside a macro), on every node, plus a SHORTCUT
  check: the unconstrained maze (macros only) may not be shorter than the planned leg by > LEN_TOL (else the router could cut
  through the clearance band).
usage: ht_l2.py HTL1.ht.json OUTPREFIX LIBDIR [--d2 UM] [--seg UM] [--clr UM]
PLAN MODEL, UNCHECKED.
"""
import collections
import hashlib
import itertools
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
G = 0.54
HALO, ROW_HALO, LAT, ISL, LEN_TOL = 2.2, 4.32, 4.32, 8.64, 2.16
REP = "BUFx16f_ASAP7_75t_R"
BIG = "BUFx24_ASAP7_75t_R"


def sha(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    except OSError:
        return None


def leg_clearance(path, pincols, macros, clr):
    """violations of a leg polyline (list of points, consecutive points axis-aligned): points sampled every 0.27 um.
    A violation = a sample inside a macro rect (crossing an SRAM) or inside a pin column widened by clr in x."""
    bad = []
    for u, v in zip(path, path[1:]):
        n = max(1, int(round((abs(u[0] - v[0]) + abs(u[1] - v[1])) / 0.27)))
        for i in range(n + 1):
            x, y = u[0] + (v[0] - u[0]) * i / n, u[1] + (v[1] - u[1]) * i / n
            for r in macros:
                if r[0] < x < r[2] and r[1] < y < r[3]:
                    bad.append(("across_sram", round(x, 3), round(y, 3)))
                    break
            for q in pincols:
                if q[0] - clr < x < q[2] + clr and q[1] < y < q[3]:
                    bad.append(("pin_column_clearance", round(x, 3), round(y, 3)))
                    break
    return bad


def lpath(a, b):
    """ht_l1 L1 leg drawn as an L: vertical at the driver x first, then horizontal (ht_l1.seg_hits convention)."""
    if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6:
        return [a, (a[0], b[1]), b]
    return [a, b]


class Maze:
    def __init__(self, core, macros, pincols, clr, island_rects=()):
        self.core = core
        self.NX, self.NY = int((core[2] - core[0]) / G), int((core[3] - core[1]) / G)
        self.W = self.NY + 1
        n = (self.NX + 1) * self.W
        self.blk0 = bytearray(n)   # macros + halo (what the router sees)
        self.blk = bytearray(n)    # + clearance band (planned legs)
        self.blkN = bytearray(n)   # + row halo (nodes)
        for i in range(self.NX + 1):
            x = core[0] + i * G
            for j in range(self.NY + 1):
                y = core[1] + j * G
                k = i * self.W + j
                if any(r[0] - HALO < x < r[2] + HALO and r[1] - HALO < y < r[3] + HALO for r in macros):
                    self.blk0[k] = self.blk[k] = self.blkN[k] = 1
                    continue
                if any(q[0] - clr <= x <= q[2] + clr and q[1] <= y <= q[3] for q in pincols):
                    self.blk[k] = self.blkN[k] = 1
                    continue
                if any(r[0] - ROW_HALO < x < r[2] + ROW_HALO and r[1] - ROW_HALO < y < r[3] + ROW_HALO for r in macros):
                    self.blkN[k] = 1
                if any(R[0] <= x <= R[2] and R[1] <= y <= R[3] for R in island_rects):
                    self.blkN[k] = 1
        self._b = {}

    def cell(self, p):
        return (min(self.NX, max(0, round((p[0] - self.core[0]) / G))), min(self.NY, max(0, round((p[1] - self.core[1]) / G))))

    def xy(self, c):
        return (round(self.core[0] + c[0] * G, 3), round(self.core[1] + c[1] * G, 3))

    def legal_node(self, p):
        i, j = self.cell(p)
        if not self.blkN[i * self.W + j]:
            return (i, j)
        for r in range(1, 400):
            best = None
            for di in range(-r, r + 1):
                for dj in (r - abs(di), -(r - abs(di))):
                    a, b = i + di, j + dj
                    if 0 <= a <= self.NX and 0 <= b <= self.NY and not self.blkN[a * self.W + b]:
                        if best is None or (abs(di), a, b) < best[0]:
                            best = ((abs(di), a, b), (a, b))
            if best:
                return best[1]

    def bfs(self, c, which="blk"):
        key = (c, which)
        if key in self._b:
            return self._b[key]
        B = getattr(self, which)
        D = [-1] * ((self.NX + 1) * self.W)
        P = [-1] * ((self.NX + 1) * self.W)
        s = c[0] * self.W + c[1]
        D[s] = 0
        q = collections.deque([s])
        W = self.W
        while q:
            u = q.popleft()
            i, j = divmod(u, W)
            for v, ok in ((u + W, i < self.NX), (u - W, i > 0), (u + 1, j < self.NY), (u - 1, j > 0)):
                if ok and D[v] < 0 and not B[v]:
                    D[v] = D[u] + 1
                    P[v] = u
                    q.append(v)
        self._b[key] = (D, P)
        return D, P

    def dist(self, a, b, which="blk"):
        d = self.bfs(a, which)[0][b[0] * self.W + b[1]]
        return d * G if d >= 0 else None

    def path(self, a, b):
        """shortest planned path a -> b (cells), preferring few bends (BFS parent walk from b back to a)."""
        D, P = self.bfs(a, "blk")
        k = b[0] * self.W + b[1]
        assert D[k] >= 0, ("unreachable", a, b)
        out = [k]
        while out[-1] != a[0] * self.W + a[1]:
            out.append(P[out[-1]])
        return [divmod(u, self.W) for u in reversed(out)]


def simplify(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if len(out) >= 2 and (out[-2][0] == out[-1][0] == p[0] or out[-2][1] == out[-1][1] == p[1]):
            out[-1] = p
        else:
            out.append(p)
    return out


def main():
    htj, pre, libdir = sys.argv[1:4]
    D2 = float(sys.argv[sys.argv.index("--d2") + 1]) if "--d2" in sys.argv else 55.0
    SEG = float(sys.argv[sys.argv.index("--seg") + 1]) if "--seg" in sys.argv else 50.0
    CLR = float(sys.argv[sys.argv.index("--clr") + 1]) if "--clr" in sys.argv else 4.32
    H = json.loads(Path(htj).read_text())
    base = str(Path(htj).parent / (Path(H["spec"]).name.replace(".sized.tcl", ".tcl")))
    seg_in = str(Path(htj).parent / Path(H["seg_json"]).name)
    gate_p = str(Path(htj).parent / Path(H["gate_json"]).name)
    g = json.loads(Path(gate_p).read_text())
    geo = g["geo"]
    macros = []
    for ln in open(geo):
        f = ln.split()
        if f and f[0] == "CORE":
            core = list(map(float, f[1:5]))
        if f and f[0] == "MACRO":
            macros.append(list(map(float, f[3:7])))
        if f and f[0] == "PIN" and f[1] == "ck":
            entry = (float(f[2]), float(f[3]))
    pincols = g["gates"]["G5_sram_structure"]["pin_columns_um"]
    qrects = [i["rect_um"] for i in g["gates"]["G2_island_rows"]["islands"]]
    M = Maze(core, macros, pincols, CLR, qrects)
    t = Path(base).read_text()
    head, rest = t.split("set ot_ms_tree {", 1)
    blk, tail = rest.split("\n}", 1)
    nodes = collections.OrderedDict()
    for ln in blk.split("\n"):
        m = re.match(r"\s*\{(\S+) (\S+) ([\d.]+) ([\d.]+) (\S+)\}$", ln)
        if m:
            nodes[m.group(1)] = [m.group(2), float(m.group(3)), float(m.group(4)), m.group(5)]
    lhead, lrest = tail.split("set ot_ms_leaves {", 1)
    lblk, ltail = lrest.split("\n}\nset ot_ms_macros", 1)
    leaves = collections.OrderedDict()
    for ln in lblk.strip("\n").split("\n"):
        m = re.match(r"(\s*\{)(\S+) (\S+) \{([\d.]+) ([\d.]+)\}(.*)$", ln)
        leaves[m.group(2)] = dict(par=m.group(3), xy=(float(m.group(4)), float(m.group(5))), rest=m.group(6), pre=m.group(1))
    l1 = {n: v for n, v in nodes.items() if re.fullmatch(r"T[EW](_r\d+)?|Q\d+(_h\d+)?", n)}
    isl = sorted((n for n in nodes if re.fullmatch(r"Q\d+", n)), key=lambda s: int(s[1:]))
    Bn = [n for n in nodes if re.fullmatch(r"Q\d+B\d+", n)]
    pos = {"root": entry, **{n: (v[1], v[2]) for n, v in nodes.items()}}
    # ---- re-site B / leaf drivers that sit in the clearance band / node keepout (nearest legal cell)
    moved = {}
    Bc = {}
    for b in Bn:
        c = M.legal_node(pos[b])
        Bc[b] = c
        if M.xy(c) != (round(pos[b][0], 3), round(pos[b][1], 3)) and math.dist(M.xy(c), pos[b]) > 0.3:
            moved[b] = [list(pos[b]), list(M.xy(c))]
    Lc = {}
    for n, v in leaves.items():
        c = M.legal_node(v["xy"])
        Lc[n] = c
        if math.dist(M.xy(c), v["xy"]) > 0.3:
            moved[n] = [list(v["xy"]), list(M.xy(c))]
    Qc = {q: M.cell(pos[q]) for q in isl}
    # ---- sub-island candidate rects (G2 rules + clearance), leg length D2 +- LEN_TOL from their island
    l1pts = [entry] + [(v[1], v[2]) for n, v in nodes.items() if re.fullmatch(r"T[EW](_r\d+)?|Q\d+_h\d+", n)]
    cand = []
    for a in range(int(core[0] / LAT), int(core[2] / LAT) + 1):
        for b in range(int(core[1] / LAT), int(core[3] / LAT) + 1):
            R = [round(a * LAT, 3), round(b * LAT, 3), round(a * LAT + ISL, 3), round(b * LAT + ISL, 3)]
            if R[0] < core[0] - 1e-6 or R[1] < core[1] - 1e-6 or R[2] > core[2] + 1e-6 or R[3] > core[3] + 1e-6:
                continue
            if any(R[0] < r[2] + ROW_HALO and R[2] > r[0] - ROW_HALO and R[1] < r[3] + ROW_HALO and R[3] > r[1] - ROW_HALO for r in macros):
                continue
            if any(R[0] < q[2] + CLR and R[2] > q[0] - CLR and R[1] < q[3] and R[3] > q[1] for q in pincols):
                continue
            if any(R[0] < Q[2] and R[2] > Q[0] and R[1] < Q[3] and R[3] > Q[1] for Q in qrects):
                continue
            if any(R[0] - ROW_HALO < p_[0] < R[2] + ROW_HALO and R[1] - ROW_HALO < p_[1] < R[3] + ROW_HALO for p_ in l1pts):
                continue                         # not on / beside an L1 trunk node, trunk repeater or the entry
            c = M.cell(((R[0] + R[2]) / 2, (R[1] + R[3]) / 2))
            if M.blk[c[0] * M.W + c[1]]:
                continue
            cand.append((R, c))
    kids = collections.defaultdict(list)
    for b in Bn:
        q = "Q" + b[1:].split("B")[0]
        kids[q].append(b)
    for b in Bn:
        M.bfs(Bc[b])
    plan_s, taken = {}, []

    def overl(R, S):
        return R[0] < S[2] and R[2] > S[0] and R[1] < S[3] and R[3] > S[1]
    for q in isl:
        bs = kids[q]
        ns = max(1, math.ceil(len(bs) / 2))
        cq = [(R, c, M.dist(Qc[q], c)) for R, c in cand if not any(overl(R, T) for T in taken)]
        cq = [x for x in cq if x[2] is not None and abs(x[2] - D2) <= LEN_TOL]
        best = None
        # exhaustive set partitions of bs into ns non-empty groups
        for lab in itertools.product(range(ns), repeat=len(bs)):
            if set(lab) != set(range(ns)) or any(lab[i] > max(lab[:i] + (-1,)) + 1 for i in range(len(lab))):
                continue
            grp = [[bs[i] for i in range(len(bs)) if lab[i] == k] for k in range(ns)]
            sites, sc, ok = [], [], True
            for gr in grp:
                bb = None
                for R, c, d in cq:
                    if any(overl(R, s_[0]) for s_ in sites):
                        continue
                    ds = [M.dist(c, Bc[b]) for b in gr]
                    if None in ds:
                        continue
                    v = (max(ds), sum(ds))
                    if bb is None or v < bb[0]:
                        bb = (v, R, c, d)
                if bb is None:
                    ok = False
                    break
                sites.append((bb[1], bb[2], bb[3], gr))
                sc.append(bb[0])
            if not ok:
                continue
            v = (max(s_[0] for s_ in sc), sum(s_[1] for s_ in sc))
            if best is None or v < best[0]:
                best = (v, sites)
        for k, (R, c, d, gr) in enumerate(best[1]):
            plan_s[f"{q}S{k}"] = dict(island=q, rect=R, cell=c, xy=M.xy(c), leg_um=round(d, 3), B=gr)
            taken.append(R)
    # ---- levels: L2 island->S, L3 S->B, L4 B->leaf; paths on the clearance maze; K repeaters per level (equal count)
    Bpar = {b: s for s, v in plan_s.items() for b in v["B"]}
    edges = {"L2": [(v["island"], s, Qc[v["island"]], v["cell"]) for s, v in plan_s.items()],
             "L3": [(Bpar[b], b, plan_s[Bpar[b]]["cell"], Bc[b]) for b in Bn],
             "L4": [(v["par"], n, Bc[v["par"]], Lc[n]) for n, v in leaves.items()]}
    new_nodes = collections.OrderedDict()   # name -> (par, x, y, cell)
    seg, legs, short_bad, rep_shift = {}, {}, [], []
    levK, levT = {}, {}
    for lev, E in edges.items():
        lens = [M.dist(a, b) for _, _, a, b in E]
        levT[lev] = (round(min(lens), 2), round(max(lens), 2))
        K = max(1, math.ceil(max(lens) / SEG))
        levK[lev] = K
        for (pa, ch, a, b), L in zip(E, lens):
            pth = M.path(a, b)
            prev, prevc = pa, a
            for j in range(1, K):
                idx = round(len(pth) * j / K)
                # nearest node-legal cell along the path to the equal cut
                # chain-pinned repeater: a node-legal cell ON SOME SHORTEST legal path a -> b (dist(a,c)+dist(c,b) = L)
                # whose distance from a is nearest the equal cut j*L/K (search radius 12 grid cells around the path cell)
                cut = L * j / K
                pc = pth[idx]
                Da, Db = M.bfs(a)[0], M.bfs(b)[0]
                best_c = None
                for di in range(-12, 13):
                    for dj in range(-12 + abs(di), 13 - abs(di)):
                        cc = (pc[0] + di, pc[1] + dj)
                        if not (0 <= cc[0] <= M.NX and 0 <= cc[1] <= M.NY):
                            continue
                        kk = cc[0] * M.W + cc[1]
                        if M.blkN[kk] or Da[kk] < 0 or Db[kk] < 0 or Da[kk] + Db[kk] != Da[b[0] * M.W + b[1]]:
                            continue
                        v = (abs(Da[kk] * G - cut), abs(di) + abs(dj))
                        if best_c is None or v < best_c[0]:
                            best_c = (v, cc)
                if best_c is None:      # fallback: nearest node-legal cell along the path
                    ii = next(i for i in sorted(range(len(pth)), key=lambda i: abs(i - idx)) if not M.blkN[pth[i][0] * M.W + pth[i][1]])
                    best_c = ((abs(ii - idx) * G, 0), pth[ii])
                rep_shift.append(round(best_c[0][0], 2))
                nm = f"{ch}_s{j - 1}"
                x, y = M.xy(best_c[1])
                new_nodes[nm] = (prev, x, y, REP)
                seg[nm] = round(M.dist(prevc, best_c[1]), 3)
                prev, prevc = nm, best_c[1]
            seg[ch] = round(M.dist(prevc, b), 3)
            legs[ch] = [list(p) for p in simplify([M.xy(c) for c in pth])]
            if lev != "L4" or True:
                d0 = M.dist(a, b, "blk0")
                if d0 is not None and d0 < L - LEN_TOL:
                    short_bad.append(dict(edge=f"{pa}->{ch}", planned_um=round(L, 2), router_shortest_um=round(d0, 2)))
            if lev == "L2":
                plan_s[ch]["par_last"] = prev
            elif lev == "L3":
                nodes[ch] = [prev, *M.xy(b), nodes[ch][3]]
            else:
                leaves[ch]["par"] = prev
                leaves[ch]["xy"] = M.xy(b)
    # ---- assemble spec: L1 nodes kept, S nodes, chain repeaters, B nodes (re-parented), leaves
    rows = [(n, *l1[n]) for n in l1]
    for s, v in plan_s.items():
        pass
    out_rows = [f" {{{n} {p} {x:.3f} {y:.3f} {c}}}" for n, p, x, y, c in rows]
    order = []
    for s, v in plan_s.items():
        for nm, (p, x, y, c) in new_nodes.items():
            if nm.startswith(s + "_s"):
                order.append((nm, p, x, y, c))
        order.append((s, v["par_last"], *v["xy"], BIG))
    for b in Bn:
        for nm, (p, x, y, c) in new_nodes.items():
            if nm.startswith(b + "_s"):
                order.append((nm, p, x, y, c))
        order.append((b, nodes[b][0], nodes[b][1], nodes[b][2], nodes[b][3]))
    for n in leaves:
        for nm, (p, x, y, c) in new_nodes.items():
            if nm.startswith(n + "_s"):
                order.append((nm, p, x, y, c))
    out_rows += [f" {{{n} {p} {x:.3f} {y:.3f} {c}}}" for n, p, x, y, c in order]
    lrows = [f"{v['pre']}{n} {v['par']} {{{v['xy'][0]:.3f} {v['xy'][1]:.3f}}}{v['rest']}" for n, v in leaves.items()]
    spec_o = pre + ".tcl"
    Path(spec_o).write_text("# QC-SU-PROG-L2 3-level geometry H-tree (ht_l2.py: island -> sub-islands at D2 %.2f um, maze legs with "
                            "%.2f um pin-column clearance) on %s\n" % (D2, CLR, Path(base).name) + head + "set ot_ms_tree {\n" +
                            "\n".join(out_rows) + "\n}" + lhead + "set ot_ms_leaves {\n" + "\n".join(lrows) + "\n}\nset ot_ms_macros" + ltail)
    A = json.loads(Path(seg_in).read_text())
    s0 = {k: v for k, v in A["seg_um"].items() if k in l1}
    for s, v in plan_s.items():
        pass
    s0.update(seg)
    A["seg_um"] = s0
    seg_o = pre + ".seg.json"
    Path(seg_o).write_text(json.dumps(A))
    # ---- checks
    l1legs = {n: lpath(pos[v[0]], (v[1], v[2])) for n, v in l1.items()}
    clr_bad = {}
    for n, pth in list(l1legs.items()) + list(legs.items()):
        b = leg_clearance([tuple(p) for p in pth], pincols, macros, CLR - 1e-6)
        if b:
            clr_bad[n] = b[:3] + [f"... {len(b)} samples"]
    all_nodes = [(n, (x, y)) for n, p, x, y, c in rows + order] + [(n, v["xy"]) for n, v in leaves.items()]

    def node_bad(p):
        why = []
        if not (core[0] <= p[0] <= core[2] and core[1] <= p[1] <= core[3]):
            why.append("outside core")
        if any(r[0] - ROW_HALO < p[0] < r[2] + ROW_HALO and r[1] - ROW_HALO < p[1] < r[3] + ROW_HALO for r in macros):
            why.append("macro row halo")
        if any(q[0] - CLR + G < p[0] < q[2] + CLR - G and q[1] < p[1] < q[3] for q in pincols):
            why.append("pin column / clearance")
        return why
    nbad = {n: w for n, p in all_nodes for w in [node_bad(p)] if w}
    srect = [v["rect"] for v in plan_s.values()]
    g2_bad = [s for s, v in plan_s.items() if any(overl(v["rect"], T) for T in qrects) or
              sum(overl(v["rect"], T) for T in srect) > 1]
    l2len = [v["leg_um"] for v in plan_s.values()]
    eq_ok = max(l2len) - min(l2len) <= LEN_TOL
    # chain gate: consecutive placed cells' shortest legal distances = equal cuts (+- 2.16 shift)
    chain_bad = []
    for lev, E in edges.items():
        K = levK[lev]
        for pa, ch, a, b in E:
            L = M.dist(a, b)
            names = [nm for nm in new_nodes if nm.startswith(ch + "_s")]
            tot = sum(seg[nm] for nm in names) + seg[ch]
            if abs(tot - L) > LEN_TOL:
                chain_bad.append(dict(edge=ch, planned=round(L, 2), sum_segments=round(tot, 2)))
            for j, nm in enumerate(names):
                cut = L * (j + 1) / K
                got = sum(seg[x] for x in names[:j + 1])
                if abs(got - cut) > LEN_TOL:
                    chain_bad.append(dict(edge=ch, rep=nm, cut=round(cut, 2), at=round(got, 2)))
    structure = dict(
        G1_macro_orient=g["gates"]["G1_macro_orient"]["verdict"],
        G2_island_rows=dict(verdict="PASS" if not g2_bad and g["gates"]["G2_island_rows"]["verdict"] == "PASS" else "FAIL",
                            sub_islands_bad=g2_bad, n_sub_islands=len(plan_s)),
        G3_cell_rows=dict(verdict="PASS" if not nbad else "FAIL", bad=nbad, n_nodes=len(all_nodes)),
        G4_lengths=dict(verdict="PASS" if eq_ok and not short_bad else "FAIL", L2_equal_leg_um=[min(l2len), max(l2len)],
                        L2_tol=LEN_TOL, level_len_um=levT, segments_per_edge=levK, router_shortcut=short_bad,
                        note="L2 equal by construction (H level); L3/L4 straight shortest legal paths, sizing balances"),
        G5_sram_structure=dict(verdict="PASS" if not clr_bad and not any("pin column" in " ".join(w) for w in nbad.values()) else "FAIL",
                               leg_violations=clr_bad, legs_checked=len(l1legs) + len(legs), clearance_um=CLR,
                               rule="every leg (L1 L-paths + every maze leg) >= CLR off every SRAM clock-pin column, no point in a macro"),
        chain=dict(verdict="PASS" if not chain_bad else "FAIL", bad=chain_bad, max_rep_shift_um=max(rep_shift) if rep_shift else 0.0))
    sverdict = "PASS" if all((v if isinstance(v, str) else v["verdict"]) == "PASS" for v in structure.values()) else "FAIL"
    # ---- sizing + gate (refit model via OT_PHYS_FIT)
    import phys_gate as PG
    import su_branch_size as SB
    sz = SB.size(spec_o, seg_o, geo, libdir)
    spec_s = pre + ".sized.tcl"
    SB.write_spec(spec_o, sz["cells"], spec_s, "QC-SU-PROG-L2 per-branch sizing (12.8 d1, uf_phys refit) of " + Path(spec_o).name)
    ph = PG.predict_file(spec_s, seg_o, geo, libdir, extra_inputs=[htj, base, seg_in, gate_p, __file__])
    rep = dict(scope="QC-SU-PROG-L2 3-level geometry H-tree + plan-computed sizing; uf_phys refit gate; PLAN MODEL, UNCHECKED",
               inputs=dict(htl1=htj, base_spec=base, seg_json=seg_in, gate_json=gate_p, geo=geo),
               D2_um=D2, seg_um=SEG, clearance_um=CLR, sub_islands={s: {k: v[k] for k in ("island", "rect", "xy", "leg_um", "B")}
                                                                  for s, v in plan_s.items()},
               moved_nodes=moved, legs=legs, l1_legs={n: [list(p) for p in v] for n, v in l1legs.items()},
               structure=structure, structure_verdict=sverdict,
               sizing={k: v for k, v in sz.items() if k != "cells"}, spec=spec_s, spec_sha256=sha(spec_s), seg_json=seg_o,
               seg_sha256=sha(seg_o), phys=ph,
               provenance=dict(argv=[sys.executable] + list(sys.argv), sha256={p: sha(p) for p in (htj, base, seg_in, gate_p, geo, __file__)}))
    rep["verdict"] = "PASS" if sverdict == "PASS" and ph["gate"]["verdict"] == "PASS" else "FAIL"
    Path(pre + ".ht2.json").write_text(json.dumps(rep, indent=1))
    print("HT_L2", pre, "D2", D2, "subs", {s: (v["xy"], v["leg_um"], v["B"]) for s, v in plan_s.items()})
    print("  levels", levT, "K", levK, "moved", len(moved), "struct", sverdict,
          {k: (v if isinstance(v, str) else v["verdict"]) for k, v in structure.items()})
    print(" ", PG.line(ph), "VERDICT", rep["verdict"])


if __name__ == "__main__":
    main()
