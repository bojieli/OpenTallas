# DIE-QC-18: corr model error = measured subtree arrival change vs model leg-delay change, for each rebuilt leg
import json, re, sys, statistics as st
D, p, g = sys.argv[1:4]
B = json.load(open("%s/trunk_%s_built.json" % (D, p))); N = json.load(open("%s/trunk_%s_built.json" % (D, g)))
G = json.load(open(D + "/" + N["cl"])); r2c = {r.replace("\\", ""): c["name"] for c in G["clusters"] for r in c["regs"]}
CI = N["summary"]["child_ins"]
def arr(t):
    R = {}
    for l in open("%s/arr_%s_TT.txt" % (D, t)):
        q = l.split()
        if not q or q[0] != "S" or q[2].startswith("ICG"): continue
        i = q[1].rsplit("/", 1)[0].replace("\\", "")
        nm = i if q[2] in CI else r2c.get(i)
        if nm: R.setdefault(nm, []).append(float(q[4]))
    return {k: st.mean(v) for k, v in R.items()}
A, Bm = arr(p), arr(g)
def sinks(nd):
    return [nd["name"].replace("\\", "")] if nd["kind"] != "merge" else [s for k in nd["kids"] for s in sinks(k)]
rows = []
def walk(nb, nn):
    if nn["kind"] != "merge": return
    for lb, ln, kb, kn in zip(nb["legs"], nn["legs"], nb["kids"], nn["kids"]):
        if lb["pts"] != ln["pts"]:
            ss = [s for s in sinks(kn) if s in A and s in Bm]
            meas = st.mean(Bm[s] - A[s] for s in ss); mod = ln["d_tt"] - lb["d_tt"]
            rows.append((round(mod, 1), round(meas, 1), len(ss)))
        walk(kb, kn)
walk(B["tree"], N["tree"])
err = [m - x for x, m, _ in rows]
print(D, p, "->", g, "rebuilt legs", len(rows), "model vs measured (model, meas, nsinks):", rows[:8])
print("  error meas-model: mean %.1f  mean|e| %.1f  max|e| %.1f ps; |model| mean %.1f" % (st.mean(err), st.mean(abs(e) for e in err), max(abs(e) for e in err), st.mean(abs(x) for x, _, _ in rows)))
