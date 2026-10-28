"""DIE-QC-16: OCV-inclusive spread of the A0 nl trunk (routed q3), approved clock AOCV table (g 0.21 %/mm), hold
convention (late + early, same region -> no droop), CPPR at the pair's LCA in the planned trunk tree.
Per sink: routed arrival range (cluster regs min..max; child = pin + contract).  Pair branch below the LCA = planned
leg delays (d_tt/d_ff, stage counts n) + the sink's downstream (cluster local tree; the child's own insertion is its
signed view's and is not charged here).  usage: nl_ocv.py trunk.json cl.json arr_TT arr_FF table.json clk_aocv_dir"""
import json, sys, itertools
tr, cl, aT, aF, tab, tdir = sys.argv[1:7]
sys.path.insert(0, tdir); import clk_aocv as A
T = A.load(tab); tr = json.load(open(tr)); cl = json.load(open(cl))
CI = {k: tuple(v) for k, v in tr["summary"]["child_ins"].items()}
U = lambda x: x.replace("\\", "")
reg2cl = {U(r): c["name"] for c in cl["clusters"] for r in c["regs"]}
paths = {}
def walk(n, path):
    kids = n.get("kids", [])
    legs = n.get("legs", [None] * len(kids))
    for i, k in enumerate(kids):
        lg = legs[i] if i < len(legs) else None
        p2 = path + [(id(n), lg)]
        if k["kind"] == "merge":
            walk(k, p2)
        else:
            paths[U(k["name"])] = (p2, k)
walk(tr["tree"], [])
out = {}
for C, ci, ap in (("TT", 0, aT), ("FF", 1, aF)):
    key = "d_tt" if C == "TT" else "d_ff"; sh = T["classes"]["A"][C]["cell_share"]
    rng = {}
    for l in open(ap):
        p = l.split()
        if p[0] != "S" or p[2].startswith("ICG"): continue
        if p[2] in CI:
            nm = U(p[1].rsplit("/", 1)[0]); v = float(p[4]) + CI[p[2]][ci]
        else:
            nm = reg2cl.get(U(p[1].rsplit("/", 1)[0])); v = float(p[4])
            if nm is None: continue
        lo, hi = rng.get(nm, (1e9, -1e9)); rng[nm] = (min(lo, v), max(hi, v))
    names = [n for n in rng if n in paths]
    miss = [n for n in rng if n not in paths]
    def branch(n, lca_depth):
        p, k = paths[n]; d = 0.0; st = 0; xs = []
        for _, lg in p[lca_depth:]:
            if lg: d += lg[key]; st += lg["n"]; xs += lg["pts"]
        if k["kind"] == "cluster": d += k[C.lower()]
        return dict(cell_ps=d * sh, net_ps=d * (1 - sh), stages={"A": max(st, 1)}), xs
    worst = (-1e9, None); nom = max(v[1] for v in rng.values()) - min(v[0] for v in rng.values())
    for a, b in itertools.permutations(names, 2):
        pa, pb = paths[a][0], paths[b][0]; dpt = 0
        while dpt < min(len(pa), len(pb)) and pa[dpt][0] == pb[dpt][0] and pa[dpt][1] is pb[dpt][1]: dpt += 1
        ba, xa = branch(a, dpt); bb, xb = branch(b, dpt)
        xy = xa + xb + [paths[a][1].get("p", [0, 0]), paths[b][1].get("p", [0, 0])]
        diag = (max(x for x, _ in xy) - min(x for x, _ in xy)) + (max(y for _, y in xy) - min(y for _, y in xy))
        pes = A.branch_pessimism(T, C, ba, bb, diag, True, "hold")
        s = rng[b][1] - rng[a][0] + pes        # capture b late, launch a early
        if s > worst[0]: worst = (s, (a, b, round(rng[b][1] - rng[a][0], 1), round(pes, 1)))
    out[C] = dict(nominal_spread=round(nom, 1), ocv_inclusive_spread=round(worst[0], 1), worst_pair=worst[1],
                  sinks=len(names), unmapped=miss[:5])
print(json.dumps(out, indent=1))
