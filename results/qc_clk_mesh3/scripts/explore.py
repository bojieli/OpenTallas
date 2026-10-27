import sys, json, collections
sys.path.insert(0, "/w/die_plan")
import qc_clk_mesh3 as M
ap = M.argparse.ArgumentParser(); M.add_common(ap)
a = ap.parse_args("--r2 inputs/r2_plan_w.json --stage inputs/stage_table.json --no-spine --top-w 16w --top-m 2 --top-reach 450".split())
st = M.Stage(a.stage); B = M.build(a, st)
P = B["P"]
k0 = next(iter(P.parts)); print("part keys", k0, {k: v for k, v in P.parts[k0].items() if k not in ("pins",)} if isinstance(P.parts[k0], dict) else P.parts[k0])
bt = collections.defaultdict(list)
for n in P.parts:
    bt[P.parts[n]["type"]].append((n, P.rect(n), P.parts[n].get("orient")))
print("types", len(bt), "parts", len(P.parts), "W H", P.W, P.H)
for t, L in sorted(bt.items(), key=lambda kv: -len(kv[1]))[:12]:
    ws = {round(r[2]-r[0],3) for _, r, _ in L}; hs = {round(r[3]-r[1],3) for _, r, _ in L}
    print(t, len(L), "w", ws, "h", hs, "orient", collections.Counter(o for *_, o in L), "x0", sorted({round(r[0],2) for _, r, _ in L})[:8], "y0", sorted({round(r[1],2) for _, r, _ in L})[:8])
ys = sorted({round(P.rect(n)[1], 2) for n in P.parts}); xs = sorted({round(P.rect(n)[0], 2) for n in P.parts})
print("distinct y0", len(ys), ys[:40]); print("distinct x0", len(xs), xs[:60])
print("gaps", B["gaps"]); print("cols", B["cols"])
print("cores", len(B["cores"]), B["cores"][:3])
