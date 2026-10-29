"""HBM-CORES-REBAL-10: render a placed lanes__canon kit (dump_placed.py csv) with the --macro-reg-guide boxes and the
WCOPY copy registers coloured by bank, a line from each column's copy-register centroid to its own SRAM centre, and the
distance census (copy flop -> own SRAM bbox, um).   rend_mrg.py placed.csv macro_reg_guide.json out.png [title]"""
import csv, json, sys, collections, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
W, H, B = 760.32, 725.76, 4.0
guides = json.load(open(sys.argv[2]))["guides"] if sys.argv[2] != "none" else []  # REBAL-11: kits without guides
dens = np.zeros((int(H / B) + 1, int(W / B) + 1))
mac, cp = {}, collections.defaultdict(list)
for r in csv.DictReader(open(sys.argv[1])):
    n = r["name"].replace("\\", ""); x, y, w, h = (float(r[k]) for k in ("x", "y", "w", "h"))
    if r["kind"] == "macro":
        mac[n] = (x, y, w, h); continue
    if r["kind"] in ("std", "ff", "buf"):
        dens[int((y + h / 2) / B), int((x + w / 2) / B)] += w * h
    if ".g_wcopy." in n and r["kind"] == "ff":
        cp[n.split(".g_wcopy.")[0]].append((x + w / 2, y + h / 2))
fig, ax = plt.subplots(1, 2, figsize=(20, 10))
im = ax[0].imshow(dens / (B * B), origin="lower", extent=(0, W, 0, H), cmap="viridis", vmax=1.0)
fig.colorbar(im, ax=ax[0], fraction=.04)
ax[0].set_title((sys.argv[4] if len(sys.argv) > 4 else "") + " std-cell density (4 um bins), guides dashed")
ax[1].set_title("WCOPY copy flops by bank (dots) -> own SRAM centre (line); guides dashed")
col = {"u_bank0": "tab:red", "u_bank1": "tab:cyan", "u_bank2": "tab:orange", "u_bank3": "lime"}
rep, worst = [], 0.0
for g in guides:
    pre = g["prefix"].rsplit(".g_wcopy.", 1)[0]; mb = mac.get(pre + ".u_m")
    bank = pre.split(".")[2]; b = g["box_um"]
    for a in ax:
        a.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec=col[bank], lw=1, ls="--"))
    pts = cp.get(pre, [])
    if not mb:
        rep.append((g["name"], pre, len(pts), None, None)); continue
    x0, y0, w, h = mb
    d = [max(x0 - px, 0, px - x0 - w) + max(y0 - py, 0, py - y0 - h) for px, py in pts]
    inbox = sum(1 for px, py in pts if b[0] <= px <= b[2] and b[1] <= py <= b[3])
    worst = max([worst] + d)
    rep.append((g["name"], pre, len(pts), max(d) if d else None, inbox))
    if pts:
        cx, cy = np.mean([p[0] for p in pts]), np.mean([p[1] for p in pts])
        ax[1].scatter([p[0] for p in pts], [p[1] for p in pts], s=4, c=col[bank])
        ax[1].plot([cx, x0 + w / 2], [cy, y0 + h / 2], c=col[bank], lw=1)
for a in ax:
    for n, (x, y, w, h) in mac.items():
        a.add_patch(Rectangle((x, y), w, h, fill=False, ec="white" if a is ax[0] else "black", lw=1.2))
        if a is ax[1]:
            a.text(x + 2, y + 2, (n.split(".")[2][-5:] + "/" + n.split("g_read[")[1][0]) if "g_read[" in n else n.split(".")[-2][-8:], fontsize=6)
    a.set_xlim(0, W); a.set_ylim(0, H)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=70)
tot = sum(r[2] for r in rep)
print(f"MRG_RENDER macros {len(mac)} guides {len(guides)} copy_flops {tot} worst_dist_to_own_sram_um {worst:.1f}")
for r in rep:
    print("MRG", *r)
