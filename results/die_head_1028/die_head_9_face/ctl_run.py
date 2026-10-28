import sys, json, glob, os
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-head-9-face/tools/die_plan")
import face_guard as F
out = {}
for f in sorted(glob.glob("/srv/opentallas-scratch2/claude/die-head-8/face/nc/*.v")):
    n = os.path.basename(f)[:-2]
    v = open(f).read()
    for form in ("hold_mux", "icg"):
        land = {"d": {"D": 4, "form": form}}
        g = F.guard(v, top="top", clocks=["fclk", "clk"], land=land)
        out[f"{n}/{form}"] = dict(verdict=g["verdict"], fails=g["fail_counts"], why={k: x[:1] for k, x in g["fails"].items()}, mux=g.get("land_mux_bits"), depth=g.get("land_mux_depth"))
        print(n, form, g["verdict"], g["fail_counts"], {k: x[:1] for k, x in g["fails"].items()})
json.dump(out, open("controls_hold_mux.json", "w"), indent=1)
