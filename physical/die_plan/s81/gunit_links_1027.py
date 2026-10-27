#!/usr/bin/env python3
"""S81-CORES-R24 gunit link census: pin-to-pin Manhattan per net bit between gunit hard cores, from the gunit RTL
instance port maps (plain-net connections) and the plan pin tables (core-local pin coordinates + plan origins).
usage: glinks.py RTL PLANDIR [--move inst=x,y ...] [--json OUT]"""
import json, re, sys, collections
rtl, B = sys.argv[1], sys.argv[2]
moves = {}
for a in sys.argv[3:]:
    if "=" in a and not a.startswith("--"):
        k, v = a.split("="); moves[k] = [float(t) for t in v.split(",")]
out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
src = open(rtl).read()
src = re.sub(r"//[^\n]*", "", src)
d = json.load(open(B + "/die_plan.json"))
pt = d["partition_types"]["gunit__t1"]
cores = {c["inst"].split(".")[-1]: c for c in pt["hard_cores"]}
conn = collections.defaultdict(list)   # net -> [(inst, port)]
for inst in cores:
    m = re.search(r"\b" + inst + r"\s*\((.*?)\);", src, re.S)
    if not m:
        print("no inst", inst); continue
    for pm in re.finditer(r"\.(\w+)\s*\(\s*([A-Za-z_]\w*)\s*\)", m.group(1)):
        port, net = pm.groups()
        if net in ("clk", "rst_n"):
            continue
        conn[net].append((inst, port))
pins = {}
for inst, c in cores.items():
    o = moves.get(inst, c["origin_um"])
    t = json.load(open(B + "/inputs/core_pins/%s.json" % c["module"]))["pins"]
    for p in t:
        m = re.match(r"^(\w+)(?:\[(\d+)\])?$", p["name"])
        pins[(inst, m.group(1), m.group(2))] = (o[0] + p["x"], o[1] + p["y"])
res = collections.defaultdict(list)
for net, ends in conn.items():
    if len(ends) != 2:
        continue
    (ia, pa), (ib, pb) = ends
    ka = {k[2]: v for k, v in pins.items() if k[0] == ia and k[1] == pa}
    kb = {k[2]: v for k, v in pins.items() if k[0] == ib and k[1] == pb}
    for bit in ka:
        if bit in kb:
            (x1, y1), (x2, y2) = ka[bit], kb[bit]
            res[tuple(sorted((ia, ib)))].append((abs(x1 - x2) + abs(y1 - y2), f"{ia}.{pa}[{bit}]->{ib}.{pb}"))
summ = {}
for k in sorted(res):
    v = sorted(res[k])
    n405 = sum(1 for l, _ in v if l > 405)
    summ["%s-%s" % k] = dict(bits=len(v), min=round(v[0][0], 2), max=round(v[-1][0], 2), gt405=n405, worst=v[-1][1])
    print("%-14s bits %5d  min %7.2f  max %7.2f  >405 %5d  worst %s" % ("%s-%s" % k, len(v), v[0][0], v[-1][0], n405, v[-1][1]))
if out:
    json.dump(dict(moves=moves, bundles=summ), open(out, "w"), indent=1)
# partition S-face bus legs (pin -> nearest point of its bus window at y=0; vi_s leg from its FIRM station reg at x 432.819)
BUS = {"vi_s": ("xtier_i0", None, 432.819), "vo_s": ("xtier_o0", [1508.16, 1568.228], None),
       "vi_n": ("xtier_i1", [1630.656, 1690.724], None), "vo_n": ("xtier_o1", [1569.408, 1629.476], None),
       "cw_d": ("unit_i0", [1449.024, 1506.972], None), "cw_a": ("unit_i0", [1449.024, 1506.972], None),
       "cw_v": ("unit_i0", [1449.024, 1506.972], None)}
owner = {"vi_s": "u_l3", "vo_s": "u_l3", "vi_n": "u_l5", "vo_n": "u_l5", "cw_d": "u_l2", "cw_a": "u_l2", "cw_v": "u_l2"}
bl = collections.defaultdict(list)
for (inst, port, bit), (x, y) in pins.items():
    if owner.get(port) != inst:
        continue
    bus, win, st = BUS[port]
    if st is not None:
        l = abs(x - st) + y
    else:
        l = max(0.0, win[0] - x, x - win[1]) + y
    bl[bus].append(l)
for b, v in sorted(bl.items()):
    print("bus %-9s bits %4d max %7.2f >405 %4d" % (b, len(v), max(v), sum(1 for l in v if l > 405)))
