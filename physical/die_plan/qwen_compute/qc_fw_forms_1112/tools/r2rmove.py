"""TOOLS GEOM_TSV MOVES_JSON OUT_TSV -> geom.tsv with flops moved ({"u_bin_x_sc_i/q[43]": [x, y], ...}, keys = relay_sites
form) + r2r census of the moved geometry (captures > 405 listed), so a plan relay_sites edit is checked on the measured
netlist before the build"""
import sys, json, re
sys.path.insert(0, sys.argv[1] + "/autopilot")
import geom_rules as G
moves = json.load(open(sys.argv[3]))
want = {}
for k, xy in moves.items():
    inst, pin = k.split("/")
    m = re.fullmatch(r"(\w+)\[(\d+)\]", pin)
    want[(inst, m.group(1), m.group(2)) if m else (inst, pin, None)] = xy
hit = 0
with open(sys.argv[2]) as f, open(sys.argv[4], "w") as o:
    for line in f:
        c = line.rstrip("\n").split("\t")
        if c[0] == "C" and "DFF" in c[3]:
            m = re.search(r"\.(u_\w+)/(\w+?)(?:\\?\[(\d+)\\?\])?\$_", c[8])
            if m and (m.group(1), m.group(2), m.group(3)) in want:
                x, y = want[(m.group(1), m.group(2), m.group(3))]
                w, h = float(c[6]) - float(c[4]), float(c[7]) - float(c[5])
                c[4:8] = [f"{x - w / 2:.4f}", f"{y - h / 2:.4f}", f"{x + w / 2:.4f}", f"{y + h / 2:.4f}"]
                line = "\t".join(c) + "\n"; hit += 1
        o.write(line)
print("moved", hit, "of", len(want))
D = G.Design(sys.argv[4]); pairs = []
m = G.r2r_metrics(D, capture_pairs=pairs)
print("r2r_gt405", m["r2r_captures_gt405"], "max", m["r2r_max"])
for p in sorted(pairs, key=lambda p: -p["distance_um"]):
    print(round(p["distance_um"]), p["launch"][:48], [round(a) for a in p["launch_xy"]], p["capture"][:48], [round(a) for a in p["capture_xy"]])
