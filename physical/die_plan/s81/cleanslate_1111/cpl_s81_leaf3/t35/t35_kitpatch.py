#!/usr/bin/env python3
"""apply the t35 v2 plan change to a COPY of the p4 kit (DO_NOT_COUNT probe): bands, tap cap, 2 lane moves, lane rst relays."""
import json, re, sys
K = sys.argv[1]
OLD = {(65.28, 1183.68, 125.348, 1209.6): [6.48, 1183.68, 200.88, 1209.6],
       (126.528, 1183.68, 186.596, 1209.6): [209.52, 1183.68, 403.92, 1209.6],
       (180.36, 1136.16, 189.0, 1183.68): [412.56, 1136.16, 421.2, 1183.68]}
n = [0]
def walk(o):
    if isinstance(o, list):
        if len(o) == 4 and all(isinstance(v, (int, float)) for v in o):
            k = tuple(round(float(v), 4) for v in o)
            if k in OLD:
                n[0] += 1; return list(OLD[k])
        return [walk(v) for v in o]
    if isinstance(o, dict):
        return {k: walk(v) for k, v in o.items()}
    return o
f = f"{K}/landing_contract.json"; d = walk(json.load(open(f))); json.dump(d, open(f, "w"), indent=1)
print("landing_contract rects replaced", n[0])
f = f"{K}/landing_placement.tcl"; s = open(f).read(); m = 0
for o, nw in OLD.items():
    a = "{%.5f %.5f %.5f %.5f}" % o; b = "{%.5f %.5f %.5f %.5f}" % tuple(nw)
    m += s.count(a); s = s.replace(a, b)
open(f, "w").write(s); print("landing_placement rects replaced", m)
f = f"{K}/config.mk"; s = open(f).read(); assert "export OT_TAP_MAX_SINKS = 3000" in s
open(f, "w").write(s.replace("export OT_TAP_MAX_SINKS = 3000", "export OT_TAP_MAX_SINKS = 1500")); print("cap 1500")
f = f"{K}/macro_place.tcl"; s = open(f).read()
for inst, dx in (("u_bound.u_u_vp_g_ln_2_u_l", 192.24 - 198.72), ("u_bound.u_u_vp_g_ln_14_u_l", 183.6 - 190.08)):
    r = re.compile(r"(place_macro -macro_name \{" + re.escape(inst) + r"\} -location \{)([\d.]+) ([\d.]+)\}")
    mm = r.search(s); assert mm
    s = r.sub(lambda m: "%s%.4f %s}" % (m.group(1), float(m.group(2)) + dx, m.group(3)), s, count=1)
    print(inst, mm.group(2), "->", "%.4f" % (float(mm.group(2)) + dx))
open(f, "w").write(s)
f = f"{K}/reset_tree.tcl"; s = open(f).read()
c = s.count("275.544 282.960"); s = s.replace("275.544 282.960", "266.904 282.960"); open(f, "w").write(s)
print("g_ln[14] rst relays moved", c)
