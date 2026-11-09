# HBM-CORES-B 11-09 rootg1c_vC5: S-face pins (1074, M5) re-pitched evenly, order kept: x = 0.984 + 0.192*i (M5 grid 0.048, offset 0.024).
import json, os, re, sys
K = sys.argv[1]
P = os.path.join(K, "pins.json")
pins = json.load(open(P))
s = sorted([q for q in pins if q["face"] == "S"], key=lambda q: q["x"])
newx = {}
for i, q in enumerate(s):
    nx = round(0.984 + 0.192 * i, 4)
    name = q["bus"] if q["bit"] is None else "%s[%d]" % (q["bus"], q["bit"])
    newx[name] = nx
    q["x"] = nx
assert max(newx.values()) < 211.68 - 1.0, max(newx.values())
os.remove(P); json.dump(pins, open(P, "w"), indent=1)
T = os.path.join(K, "io.tcl")
lines = open(T).read().split("\n")
n = 0
for k, l in enumerate(lines):
    m = re.match(r"place_pin -pin_name \{([^}]+)\} -layer M5 -location \{([0-9.]+) 0\.0960\}", l)
    if m and m.group(1) in newx:
        lines[k] = l.replace("{%s 0.0960}" % m.group(2), "{%.4f 0.0960}" % newx[m.group(1)])
        n += 1
assert n == len(s), (n, len(s))
os.remove(T); open(T, "w").write("\n".join(lines))
print("S pins re-pitched", n, "x", min(newx.values()), "..", max(newx.values()))
