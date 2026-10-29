#!/usr/bin/env python3
"""QC-PG-2: render the SU-window upper deck (S own + bg) for a kit variant, zoom on su8 with bump pads (70 / 37.5 um).
usage: render_k75.py VARIANT_DIR_NAME OUT.png [F_SU8] [BG]   (reads /srv/.../qc-pg-2-1027/kits/<cls>/<variant>, cores.json of qc-pg-map)"""
import csv, re, json, sys
from collections import defaultdict
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
N = "/srv/opentallas-scratch2/claude/qc-pg-2-1027/kits"; MP = "/srv/opentallas-scratch2/claude/qc-pg-map-1027"
v, out = sys.argv[1], sys.argv[2]; f = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0; bg = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5823
x0, y0 = 26352, 9504
def rd(d):
    o = {n: defaultdict(lambda: -1e9) for n in ("VDD", "VSS")}
    for n in o:
        for r in csv.DictReader(open(d + "/ir_%s.csv" % n)):
            x = float(r["Voltage"]); o[n][r["Instance"]] = max(o[n][r["Instance"]], (x if n == "VSS" else 0.7 - x) * 1e3)
    return o
S, U, A, F = [rd(f"{N}/{c}/{v}/psm") for c in ("S", "U8", "A", "F")]
M = np.zeros((69, 69))
for k in S["VDD"]:
    i, j = map(int, re.match(r"u_b(\d+)_(\d+)", k).groups())
    M[j, i] = sum(S[n][k] + (f - 1) * U[n][k] + bg * (A[n][k] + F[n][k]) for n in ("VDD", "VSS"))
fig, ax = plt.subplots(figsize=(8, 7))
im = ax.imshow(M, origin="lower", extent=[0, 2972.16, 0, 2972.16], cmap="inferno", vmin=0, vmax=45)
plt.colorbar(im, label=f"upper colo mV per block (S own, su8 x{f}, bg {bg})")
col = {"qfd_dv_s5_su8_rst3": "cyan", "qfd_dv_s8x_prog": "lime", "qfd_dv_s8x_vmr": "white", "qfd_dv_s8x_crh": "yellow", "qfd_dv_s8x_btab": "magenta"}
for c in json.load(open(MP + "/cores.json"))["cores"]:
    r = c["rect"]
    if r[2] < x0 or r[0] > x0 + 2972 or r[3] < y0 or r[1] > y0 + 2972: continue
    ax.add_patch(Rectangle((r[0] - x0, r[1] - y0), r[2] - r[0], r[3] - r[1], fill=False, ec=col.get(c["module"], "grey"), lw=1))
for m in re.finditer(r"^ot_pad (\S+) \d+ (\S+) (\S+)(?: (\S+))?", open(f"{N}/S/{v}/psm/bumps.tcl").read(), re.M):
    p = float(m[4] or 70); x, y = float(m[2]), float(m[3])
    ax.add_patch(Rectangle((x - p / 2, y - p / 2), p, p, fill=False, ec="deepskyblue" if m[1] == "VDD" else "red", lw=0.8))
ax.set_title(f"QC SU window upper deck M9.672, kit {v}: pads (blue VDD / red VSS; 70-um = 150 lattice, 37.5-um = 75 field)\nsu8 cyan, prog lime, vmr white, crh yellow, btab magenta; max {M.max():.1f} mV", fontsize=8)
ax.set_xlim(1200, 2100); ax.set_ylim(950, 1850); plt.savefig(out, dpi=110)
print("max", M.max())
