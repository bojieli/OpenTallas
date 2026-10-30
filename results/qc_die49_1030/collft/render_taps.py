"""DIE-QC-49/collft: coll_ft__cla4a25d77 taps / landing bands / reset relays, plan_qc49 vs plan_qc50."""
import sys, json
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
T = "coll_ft__cla4a25d77"
fig, axs = plt.subplots(1, 2, figsize=(14, 9))
for ax, pp, lab in zip(axs, sys.argv[1:3], ("plan_qc49", "plan_qc50")):
    t = json.load(open(pp))["partition_types"][T]; ck = t["clock"]; lc = ck["landing_contract"]; w, h = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1))
    for k, b in lc["bands"].items():
        x0, y0, x1, y1 = b["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, color="tab:orange", alpha=.5)); ax.text(x0, y1+4, k, fontsize=6)
    for r in lc["collector_tree"]["relays"]:
        x, y = r["xy"]; ax.add_patch(Rectangle((x-2.16, y-2.16), 4.32, 4.32, color="tab:green", alpha=.8))
    taps = [(x["name"], *x["xy"]) for x in ck["taps"]] if ck.get("tap_mode") == "explicit" else [("clk",196.56,165.6),("clk_t1",589.68,165.6),("clk_t2",196.56,496.8),("clk_t3",589.68,496.8),("clk_t4",196.56,828.0),("clk_t5",589.68,828.0)]
    for n, x, y in taps:
        ax.plot(x, y, "b^", ms=7); ax.text(x+6, y+6, n, fontsize=8, color="b")
    for p in lc["pins"]:
        if p["kind"] == "clock" and p["dir"] == "out": ax.plot(*p["xy_um"], "rs", ms=4); ax.text(p["xy_um"][0], p["xy_um"][1]-14, p["name"][9:]+"<-"+p["source_clock_tap"], fontsize=5, color="r")
    ax.set_xlim(-10, w+10); ax.set_ylim(-20, h+20); ax.set_aspect("equal"); ax.set_title(f"{lab} {T}: taps(blue) bands(orange) relays(green) fclk_out(red)", fontsize=8)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=130)
