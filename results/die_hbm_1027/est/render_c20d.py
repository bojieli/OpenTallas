import json, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D = sys.argv[1]; raw = json.load(open(D + "/die_plan.json")); T = raw["partition_types"]
parts = {p["name"]: p for p in raw["partitions"]}
# (a) root tkm field
t = T["root"]; fig, ax = plt.subplots(1, 2, figsize=(16, 9))
a = ax[0]
for c in t["hard_cores"]:
    x, y = c["origin_um"]; w, h = c["outline_um"]
    if x < 1700 and 2300 < y < 4600:
        a.add_patch(Rectangle((x, y), w, h, fc="#ddd", ec="k", lw=.5)); a.text(x + w / 2, y + h / 2, c["inst"].replace("u_tkm_SW_", ""), fontsize=6, ha="center")
for b in t["clock"]["branch_buffers"]:
    if "tkmclk" not in b["name"]: continue
    a.plot(*b["xy"], "bs", ms=5)
    for r in b.get("leg_repeaters") or []:
        a.plot(*r["xy"], "r^", ms=5)
for tp in t["clock"]["taps"]:
    if "tkm_SW" in tp["name"]: a.plot(*tp["xy"], "g.", ms=6)
a.set_xlim(150, 1700); a.set_ylim(2300, 4600); a.set_aspect("equal"); a.set_title("C20d root tkm field: blue=branch buf, red=leg repeater (gap columns), green=tile tap")
# (b) NE_b101 N / NE_hub S face windows
a = ax[1]; p = parts["NE_b101"]; tb = T[p["type"]]; x0, y0 = p["origin_um"]; W, H = tb["outline_um"]
a.add_patch(Rectangle((x0, y0), W, H, fc="#eef", ec="b")); a.text(x0 + 10, y0 + H - 60, "NE_b101", fontsize=8)
a.add_patch(Rectangle((x0 - 100, y0 + H), W + 200, 300, fc="#efe", ec="g")); a.text(x0 + 10, y0 + H + 250, "NE_hub (S face)", fontsize=8)
col = {"L12m_1": "r", "L74m_0": "m"}
for pid, c in col.items():
    w = next(q for q in raw["ports"] if q["id"] == pid)["window_um"]
    a.add_patch(Rectangle((w[0], y0 + H - 20), w[1] - w[0], 40, fc=c, alpha=.6)); a.text(w[0], y0 + H + 30 + (60 if c == "m" else 0), f"{pid} {w[0]:.1f}-{w[1]:.1f}", fontsize=8, color=c)
s = next(s for s in tb["ft_slots"] if s["name"] == "L12x1")
for q in s["regs_um"]:
    a.plot(x0 + W - q[0], y0 + q[1], "ko")
a.set_xlim(x0 - 120, x0 + W + 120); a.set_ylim(y0 + H - 900, y0 + H + 320); a.set_aspect("equal"); a.set_title("C20d NE_b101 N face: L12m_1 (red) and L74m_0 (magenta) windows; black = L12m stations (MY)")
plt.tight_layout(); plt.savefig(D + "/c20d_fixes.png", dpi=110)
