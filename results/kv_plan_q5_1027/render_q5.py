"""render the q5 core deltas: qkd_ahub zh macro drops (ck[1]/ck[2] islands) and qkd_hr_phy_pad centre clock/reset entry."""
import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pd, out = sys.argv[1:3]
fig, ax = plt.subplots(1, 2, figsize=(16, 8))
S = json.load(open(f"{pd}/cores/qkd_ahub_slice_r26q5.json"))["slice"]
pins = {p["name"]: p for p in json.load(open(f"{pd}/cores/qkd_ahub_pins_r26q5.json"))["pins"]}
a = ax[0]; a.add_patch(Rectangle((0, 0), 604.8, 440.64, fill=False, lw=1.5))
for b in S["hard_children_boxes_um"]:
    a.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc="#ddd", ec="k"))
for i in S["core_tree"]["islands"]:
    c = i["centre_um"]; a.add_patch(Rectangle((c[0] - 4.32, c[1] - 4.32), 8.64, 8.64, fc="orange", ec="none", alpha=.7))
e = S["entry"]["xy_um"]; a.plot(*e, "bs", ms=8, label="ck[0] entry (q4)")
for m in S["macro_entries"]:
    r = m["island_um"]; a.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="red", ec="k"))
    a.plot(*m["pin_xy_um"], "r*", ms=12)
    for s in S["macro_sinks"]["sinks"]:
        if s["inst"] in m["sinks"]:
            a.plot([m["pin_xy_um"][0], s["pin_um"][0]], [m["pin_xy_um"][1], s["pin_um"][1]], "r-", lw=2)
            a.plot(*s["pin_um"], "go", ms=6)
    a.annotate(f"{m['pin']} TT {m['insertion_ps']['tt']}", m["pin_xy_um"], xytext=(10, 10), textcoords="offset points", color="r")
for s in S["macro_sinks"]["sinks"]:
    a.annotate(s["inst"].split(".")[0], s["pin_um"], fontsize=7)
a.set_aspect("equal"); a.set_title("qkd_ahub q5: zh pair macro drops (red) / islands orange / macros grey"); a.legend(loc="center right")
d = json.load(open(f"{pd}/cores/qkd_hr_phy_pad_pins_r26q5.json"))
a = ax[1]; a.add_patch(Rectangle((0, 0), 86.4, 95.04, fill=False, lw=1.5))
for p in d["pins"]:
    c = "r" if p["name"] in ("ck_phy[0]", "rst_n[0]") else ("b" if p["layer"] == "M5" else "g")
    a.plot(p["x"], p["y"], ".", color=c, ms=3 if c != "r" else 10)
a.annotate("ck_phy[0] / rst_n[0] centre entry", (43.224, 47.52), xytext=(5, 8), textcoords="offset points", color="r")
a.set_xlim(-3, 90); a.set_ylim(-3, 98); a.set_aspect("equal"); a.set_title("qkd_hr_phy_pad q5 pins (M5 blue, M4 green)")
plt.tight_layout(); plt.savefig(out, dpi=110)
