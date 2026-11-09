#!/usr/bin/env python3
"""DIE-QC-93 vR8a: x remap of the vR7 hand homes to the vR8a macro map. Piecewise-linear between macro edges (edges map
exactly; y unchanged). romleaf col0 flips MY->R0 (pins east->west): its pin-side homes east of col0 (g_col[0] names in the
old central channel) are mirrored to the same distance WEST of the new col0 west edge. Writes *.pre_vR8a backups."""
import re, sys, shutil
from pathlib import Path
K = Path(sys.argv[1])
TOP = [(4.32, 4.32), (25.92, 46.656), (73.44, 94.176), (86.4, 107.136), (201.744, 222.48), (299.856, 299.856),
       (453.6, 453.6)]
BOT = [(4.32, 4.32), (9.288, 49.032), (182.088, 221.832), (261.408, 266.592), (434.208, 439.392), (453.6, 453.6)]
YSPLIT = 564.48
C0W = 49.032
def fx(x, y, name=""):
    if y < YSPLIT and ("g_col\\[0\\]" in name or "g_col[0]" in name) and 182.088 <= x <= 261.408:
        return max(4.6, C0W - (x - 182.088))
    bp = TOP if y >= YSPLIT else BOT
    if x <= bp[0][0]: return x
    for (a, A), (b, B) in zip(bp, bp[1:]):
        if x <= b: return A + (x - a) * (B - A) / (b - a)
    return x
n = {}
p = K / "nk_graph_homes.tsv"; shutil.copy(p, str(p) + ".pre_vR8a")
out = []
for line in p.read_text().splitlines():
    f = line.split("\t")
    if len(f) >= 3:
        try:
            x, y = float(f[1]), float(f[2]); nx = fx(x, y, f[0]); f[1] = f"{nx:.3f}"; n["homes"] = n.get("homes", 0) + 1
            if y < YSPLIT and ("g_col\\[0\\]" in f[0] or "g_col[0]" in f[0]) and 182.088 <= x <= 261.408: n["col0_mirrored"] = n.get("col0_mirrored", 0) + 1
        except ValueError: pass
    out.append("\t".join(f))
p.write_text("\n".join(out) + "\n")
p = K / "vr7/plan.tcl"; shutil.copy(p, str(p) + ".pre_vR8a"); t = p.read_text()
def rh(m):
    x, y = int(m.group(2)), int(m.group(3)); n["plan_rh"] = n.get("plan_rh", 0) + 1
    return f"{m.group(1)}{int(round(fx(x / 1000, y / 1000) * 1000))} {y}"
p.write_text(re.sub(r"^(ot_rh \{[^}]*\} )(\d+) (\d+)$", rh, t, flags=re.M))
p = K / "vr7/control_home.tcl"; shutil.copy(p, str(p) + ".pre_vR8a"); t = p.read_text()
assert t.count("235000 + (") == 1 and t.count("235000+") == 1
t = t.replace("235000 + (", "235000 + (").replace("235000+", "235000+")   # top central channel unchanged around x 235..263
t, k = re.subn(r"(\$_DFF_PN0_\} )79000 ", lambda m: m.group(1) + str(int(round(fx(79.0, 800.0) * 1000))) + " ", t)
assert k == 4; n["nv_f2_x"] = int(round(fx(79.0, 800.0) * 1000))
p.write_text(t)
print(n)
