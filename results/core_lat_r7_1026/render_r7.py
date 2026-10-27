"""S81-CORE-LAT-R7 GEOM render: placed l0r sinks + the R7 frozen plan (equal-structure 2,2,8,8 H-tree, NDR M4/M5 trunk,
12.8 d1 plan-sized drivers): Manhattan legs as planned maze paths coloured by level, drivers sized by drive strength,
per-level edge length (all edges of a level equal by structure). usage: GEO R7.json NAME OUT.png"""
import json, re, sys, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
geo, rj, name, out = sys.argv[1:5]
S = [l.split() for l in open(geo) if l.startswith("SINK")]
r = [x for x in json.load(open(rj)) if x["name"] == name][0]
fig, ax = plt.subplots(figsize=(11, 11))
ax.scatter([float(s[1]) for s in S], [float(s[2]) for s in S], s=0.25, c="0.72", label="%d placed sinks (GPL)" % len(S))
colors = {1: "tab:red", 2: "tab:blue", 3: "tab:green", 4: "tab:orange", 5: "tab:purple"}
lv_len = collections.defaultdict(list)
for w in r["wire_paths"]:
    lv_len[w["level"]].append(sum(w["segs"]))
    for pts in w["paths"]:
        ax.plot([p[0] for p in pts], [p[1] for p in pts], c=colors[w["level"]], lw=1.6 if w["level"] <= 2 else 0.9, alpha=0.9)
for lv in sorted(lv_len):
    v = lv_len[lv]; ax.plot([], [], c=colors[lv], lw=2, label="L%d edges %d: %.1f-%.1f um (%s)" % (lv, len(v), min(v), max(v), "equal by detour+rep" if max(v) - min(v) < 2.5 else "natural length, d1-sized"))
def strength(m): x = re.search(r"x(\d+)", m); return int(x.group(1)) if x else 1
for kind, mk, c in (("branch", "s", "k"), ("rep", "D", "tab:brown"), ("leaf", "o", "tab:cyan")):
    ns = [n for n in r["nodes_xy"] if n[4] == kind]
    ax.scatter([n[2][0] for n in ns], [n[2][1] for n in ns], s=[2 + 1.2 * strength(n[3]) for n in ns], marker=mk, c=c,
               edgecolors="none", label="%s drivers %d (BUFx4f..x24, marker ~ size)" % (kind, len(ns)), zorder=3)
ax.plot(*r["entry"], "k*", ms=16, label="centre entry (12.8a)", zorder=4)
ax.set_xlim(-3, 271); ax.set_ylim(-3, 271); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
t, f = r["TT"], r["FF"]
ax.set_title("dsdv_gunit_l0r R7 %s: %s, %d stages/path, NDR2W M4/M5 trunk, d1 sizing\nPLAN MODEL TT %.1f / w%.1f, FF %.1f / w%.1f (UNCHECKED)"
             % (name, r["splits"], r["stages"][0], t["mean"], t["window"], f["mean"], f["window"]), fontsize=9)
fig.savefig(out, dpi=120)
