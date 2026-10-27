import sys, re, statistics as st
def load(fn):
    d = {}
    for l in open(fn):
        if l.startswith("#"): continue
        f = l.split("\t"); m = re.fullmatch(r"ot_ms_(Q\w+?)_clk", f[1])
        if m: d.setdefault(m.group(1), []).append(float(f[2]))
    return {k: (st.mean(v), len(v), max(v) - min(v)) for k, v in d.items()}
g, r = load(sys.argv[1]), load(sys.argv[2])
rows = sorted(((r[k][0] - g[k][0], k, g[k][0], r[k][0], r[k][2]) for k in g), reverse=True)
for x in rows[:12]: print("%-8s grt %.1f rcx %.1f delta %+.1f intra-leaf-spread %.1f" % (x[1], x[2], x[3], x[0], x[4]))
print("...")
for x in rows[-5:]: print("%-8s grt %.1f rcx %.1f delta %+.1f intra-leaf-spread %.1f" % (x[1], x[2], x[3], x[0], x[4]))
ds = [x[0] for x in rows]; print("delta mean %.1f sd %.1f" % (st.mean(ds), st.pstdev(ds)))
