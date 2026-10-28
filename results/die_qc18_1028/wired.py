# DIE-QC-18: per trunk net wire delay (load A - driver Y, rise col) in two runs; nets with identical driver+load sets
import json, sys
def T(f):
    R = {}
    for l in open(f):
        p = l.split()
        if p and p[0] == "T": R[p[1]] = float(p[2])
    return R
def nets(j):
    d = json.load(open(j)); drv = {}; loads = {}
    for i in d["insts"]:
        drv[i["out_net"]] = i["name"]; loads.setdefault(i["in_net"], []).append(i["name"])
    return drv, loads
Ja, Jb, Fa, Fb = sys.argv[1:5]
da, la = nets(Ja); db, lb = nets(Jb); ta, tb = T(Fa), T(Fb)
same = diff = 0; worst = []
for n, ls in la.items():
    if n not in da or db.get(n) != da[n] or sorted(lb.get(n, [])) != sorted(ls): continue
    for x in ls:
        wa = ta[x + "/A"] - ta[da[n] + "/Y"]; wb = tb[x + "/A"] - tb[db[n] + "/Y"]
        if abs(wa - wb) < 0.01: same += 1
        else: diff += 1; worst.append((round(abs(wa - wb), 2), n, x))
print("trunk wires unchanged-netlist: identical", same, "differ", diff, sorted(worst)[-5:])
