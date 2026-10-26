import sys, csv, math, re, collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
D = sys.argv[1]; title = sys.argv[2]
cells = [l.rstrip("\n").split("\t") for l in open(D + "/cells.tsv")]
pos = {c[0]: (float(c[2]), float(c[3])) for c in cells}
# 1) enable flops vs their sd rows: we flops = names under g_sd_row[r] (kept qkd_astk_sd_we), sd bits sd[r][k]
sd = collections.defaultdict(list); we = collections.defaultdict(list)
for n, m, x, y in cells:
    k = n.replace("\\", "")
    if not m.startswith("DFF"): continue
    a = re.search(r"g_zn_([0-3])_u_zn[./]sd\[(\d+)\]\[(\d+)\]", k)
    if a: sd[(a[1], int(a[2]))].append((float(x), float(y)))
    b = re.search(r"g_zn_([0-3])_u_zn[./]g_sd_row[\[_](\d+)", k)
    if b: we[(b[1], int(b[2]))].append((float(x), float(y)))
cen = lambda p: (sum(a for a, _ in p) / len(p), sum(b for _, b in p) / len(p))
dist = []
for key, ps in we.items():
    if key not in sd: continue
    cx, cy = cen(sd[key])
    for x, y in ps: dist.append(math.hypot(x - cx, y - cy))
dist.sort()
print(f"ENABLE we_ff {sum(map(len, we.values()))} rows {len(we)} dist_to_row_centroid median {dist[len(dist)//2]:.1f} p90 {dist[int(.9*len(dist))]:.1f} max {dist[-1]:.1f} um" if dist else "ENABLE none found")
# 2) face chains
ch = [l.rstrip("\n").split("\t") for l in open(D + "/chains.tsv")]
cd = sorted(math.hypot(float(c[1]) - float(c[4]), float(c[2]) - float(c[5])) for c in ch)
far = sum(1 for d in cd if d > 10)
print(f"CHAINS cells {len(cd)} median {cd[len(cd)//2]:.2f} max {cd[-1]:.2f} um, >10um {far}" if cd else "CHAINS none")
# 3) ctl start / schedule_age nets
nets = collections.defaultdict(list)
for l in open(D + "/nets.tsv"):
    n, i, t, x, y = l.rstrip("\n").split("\t"); nets[n].append((float(x), float(y)))
for n, ps in sorted(nets.items()):
    xs = [p[0] for p in ps]; ys = [p[1] for p in ps]
    print(f"NET {n} pins {len(ps)} bbox x {min(xs):.0f}-{max(xs):.0f} y {min(ys):.0f}-{max(ys):.0f}")
# render
fig, ax = plt.subplots(figsize=(11, 10.5))
grp = collections.defaultdict(list)
for n, m, x, y in cells:
    k = n.replace("\\", "")
    g = "zn" + re.search(r"g_zn_(\d)", k)[1] if "g_zn_" in k else ("ctl.faces" if "g_tc_faces" in k else ("ctl" if "u_ctl" in k else ("io" if re.match(r"(input|output)\d", k) else "other")))
    grp[g].append((float(x), float(y)))
col = {"other": "0.8", "zn0": "tab:blue", "zn1": "tab:green", "zn2": "tab:purple", "zn3": "tab:olive", "ctl": "tab:orange", "ctl.faces": "tab:cyan", "io": "tab:brown"}
for g in ["other", "zn0", "zn1", "zn2", "zn3", "ctl", "ctl.faces", "io"]:
    ps = grp.get(g, [])
    ax.scatter([p[0] for p in ps], [p[1] for p in ps], s=0.3 if g == "other" else 1.0, c=col[g], label=f"{g} named ({len(ps)})")
for key, ps in we.items():
    ax.scatter([p[0] for p in ps], [p[1] for p in ps], s=4, c="k", marker="x")
for c in ch:
    if math.hypot(float(c[1]) - float(c[4]), float(c[2]) - float(c[5])) > 10:
        ax.plot([float(c[1]), float(c[4])], [float(c[2]), float(c[5])], "r-", lw=0.5)
ax.axhspan(4.32, 38.88, color="0.5", alpha=0.08)
ax.set_xlim(0, 190.08); ax.set_ylim(0, 181.44); ax.set_aspect("equal"); ax.legend(markerscale=20, fontsize=7, loc="upper right")
ax.set_title(title + "  (x = storage-enable FFs, red = face chain cell >10 um from its flop)")
fig.savefig(D + "/place_review.png", dpi=110); print("PNG", D + "/place_review.png")
inb = 0; spans = []
for key, ps in we.items():
    if key not in sd: continue
    xs = [p[0] for p in sd[key]]; ys = [p[1] for p in sd[key]]
    spans.append(max(max(xs) - min(xs), max(ys) - min(ys)))
    for x, y in ps:
        inb += (min(xs) - 2 <= x <= max(xs) + 2 and min(ys) - 2 <= y <= max(ys) + 2)
spans.sort()
print(f"ENABLE inside own sd-row bbox(+2um) {inb}/{sum(map(len, we.values()))}; sd row bbox span median {spans[len(spans)//2]:.1f} um")
