import sys, json, collections
sys.path.insert(0, "/w/die_plan")
import qc_clk_mesh3 as M
ap = M.argparse.ArgumentParser(); M.add_common(ap)
a = ap.parse_args(("--r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --no-spine --top-w 16w --top-m 2 --top-reach 450 " + " ".join(sys.argv[1:])).split())
st = M.Stage(a.stage); B = M.build(a, st)
I = B["islands"]; top = B["et"]["top"]
cells, ls = M.legalize(B); B["cells"] = cells
PE = M.phys_edges(B)
by = {n["tag"]: n for n in B["top_nodes"]}
rows = []
for n in B["top_nodes"]:
    if not n.get("parent"): continue
    p = by[n["parent"]]["xy"]; q = n["xy"]
    hor = abs(p[1]-q[1]) < 1e-6
    if I and (hor or abs(p[0]-q[0])<1e-6):
        ax = "x" if hor else "y"; i = 0 if hor else 1
        dm = I.chain_delay(top, "TT", ax, p[1-i], p[i], q[i], n["nseg"])
    else:
        dm = top.delay(n["leg"], "TT", n["nseg"])
    dl = sum(top.st.seg(top.w, top.m, "TT", L) for _, _, L in PE[("t", n["tag"])])
    Ls = [round(L,1) for _, _, L in PE[("t", n["tag"])]]
    rows.append((dl-dm, n["tag"], hor, n["nseg"], round(n["leg"],1), max(Ls), Ls[:6]))
rows.sort(key=lambda r: -abs(r[0]))
print("edges", len(rows), "abs diff >5ps", sum(1 for r in rows if abs(r[0])>5), "max", rows[0][:6])
for r in rows[:15]: print([round(r[0],1)] + list(r[1:]))

E = {r[1]: r for r in rows}
dm_e = {}
for n in B["top_nodes"]:
    if not n.get("parent"): continue
    p = by[n["parent"]]["xy"]; q = n["xy"]; hor = abs(p[1]-q[1]) < 1e-6
    ax = "x" if hor else "y"; i = 0 if hor else 1
    dm_e[n["tag"]] = I.chain_delay(top, "TT", ax, p[1-i], p[i], q[i], n["nseg"]) if (hor or abs(p[0]-q[0])<1e-6) else top.delay(n["leg"], "TT", n["nseg"])
tp, _ = M.paths(B["top_nodes"])
res = []
for leaf, ch in tp.items():
    m = sum(dm_e[e["tag"]] for e in ch); l = sum(dm_e[e["tag"]] + E[e["tag"]][0] for e in ch)
    res.append((leaf, by[leaf]["xy"], m, l, [e["tag"] for e in ch][-3:]))
ms = [r[2] for r in res]; lsx = [r[3] for r in res]
print("model spread", round(max(ms)-min(ms),2), "legal spread", round(max(lsx)-min(lsx),2))
import statistics
rowsd = collections.defaultdict(list)
for r in res: rowsd[r[0][:3]].append(r[3])
print("per-row legal mean/spread", {k: (round(statistics.mean(v)-min(lsx),1), round(max(v)-min(v),1)) for k, v in sorted(rowsd.items())})
res.sort(key=lambda r: r[3])
print("earliest", [(r[0], r[1], round(r[3]-r[2],1)) for r in res[:3]]); print("latest", [(r[0], r[1], round(r[3]-r[2],1)) for r in res[-3:]])
