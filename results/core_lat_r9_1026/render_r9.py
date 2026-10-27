"""S81-CORE-LAT-R8 GEOM render: placed l0r sinks + the R8 frozen plan (R7 F1 equal-structure 2,2,8,8 H-tree + dedicated
W pin-register strip branch), Manhattan legs coloured by level, strip branch highlighted, drivers at their converted
legal row sites when a slice is given.  usage: GEO(.gz) R8.json OUT.png [SLICE.json]"""
import gzip, json, re, sys, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
geo, rj, out = sys.argv[1:4]; slp = sys.argv[4] if len(sys.argv) > 4 else None
op = gzip.open if geo.endswith(".gz") else open
S = [l.split() for l in op(geo, "rt") if l.startswith("SINK")]
r = json.load(open(rj))[0]
strip_edges = {e["edge"] for e in r["strip"]["l3_edges"]} | {e["edge"] for e in r["strip"]["l4_edges"]}
fig, ax = plt.subplots(figsize=(11, 11))
ax.scatter([float(s[1]) for s in S], [float(s[2]) for s in S], s=0.25, c="0.72", label="%d placed sinks (R6 GPL)" % len(S))
colors = {1: "tab:red", 2: "tab:blue", 3: "tab:green", 4: "tab:orange"}
lv_len = collections.defaultdict(list)
for w in r["wire_paths"]:
    st = w["edge"] in strip_edges
    lv_len[(w["level"], st)].append(sum(w["segs"]))
    for pts in w["paths"]:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], c="magenta" if st else colors[w["level"]],
                lw=1.6 if (w["level"] <= 2 or st) else 0.9, alpha=0.9)
for (lv, st) in sorted(lv_len):
    v = lv_len[(lv, st)]
    ax.plot([], [], c="magenta" if st else colors[lv], lw=2, label="%sL%d edges %d: %.1f-%.1f um" % ("STRIP " if st else "", lv, len(v), min(v), max(v)))
pos = {n[0]: n[2] for n in r["nodes_xy"]}
if slp:
    sl = json.load(open(slp)); pos = {}
    for n in sl["core_tree"]["nodes"]:
        pos[n["name"][6:]] = n["xy_um"]
def strength(m): x = re.search(r"x(\d+)", m); return int(x.group(1)) if x else 1
for kind, mk, c in (("branch", "s", "k"), ("rep", "D", "tab:brown"), ("leaf", "o", "tab:cyan")):
    ns = [n for n in r["nodes_xy"] if n[4] == kind]
    ax.scatter([pos[n[0]][0] for n in ns], [pos[n[0]][1] for n in ns], s=[2 + 1.2 * strength(n[3]) for n in ns], marker=mk, c=c,
               edgecolors="none", label="%s drivers %d (BUFx8..x24)%s" % (kind, len(ns), " at legal row sites" if slp else ""), zorder=3)
ax.plot(*r["entry"], "k*", ms=16, label="centre entry (12.8a)", zorder=4)
ax.set_xlim(-3, 271); ax.set_ylim(-3, 271); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
t, f = r["TT"], r["FF"]; sp = r["leaf_spread_max"]
ax.set_title("dsdv_gunit_l0r R9 %s: %s STRAIGHT legs + strip branch (%d sinks), %s stages/path, d1 (uf3) BUFx8..x24\n"
             "leaf spread max strip %.1f / main %.1f um; PLAN MODEL TT %.1f / w%.1f, FF %.1f / w%.1f (UNCHECKED)"
             % (r["name"], r["splits"], r["strip"]["sinks"], r["stages"], sp["strip"], sp["main"], t["mean"], t["window"], f["mean"], f["window"]), fontsize=9)
fig.savefig(out, dpi=120)
