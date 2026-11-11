# DS85-HEHOT probe 3 (DO_NOT_COUNT): classify nets in he overflow gcells + H crossing demand over each he
import os, odb, collections, json
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"])
b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
he = {i.getName(): i for i in b.getInsts() if i.getMaster().getName().endswith("_gb_he")}
hw = {i.getName(): i for i in b.getInsts() if i.getMaster().getName().endswith("_gb_hw")}
def pts(net):
    p = []
    for it in net.getITerms():
        ok, x, y = it.getAvgXY()
        if not ok: bb = it.getInst().getBBox(); x, y = (bb.xMin()+bb.xMax())//2, (bb.yMin()+bb.yMax())//2
        p.append((x/u, y/u, it.getInst()))
    for bt in net.getBTerms():
        bb = bt.getBBox(); p.append(((bb.xMin()+bb.xMax())/2/u, (bb.yMin()+bb.yMax())/2/u, None))
    return p
names = [l.strip() for l in open("/w/he11_nets.txt") if l.strip()]
I = he["u_bound.u_u_e11_u_e"]; ib = I.getBBox(); B = (ib.xMin()/u, ib.yMin()/u, ib.xMax()/u, ib.yMax()/u)
cls = collections.Counter(); drv = collections.Counter(); ends = collections.Counter(); ex = []
def side(x, y):
    if x < B[0]: return "W"
    if x > B[2]: return "E"
    if y < B[1]: return "S"
    if y > B[3]: return "N"
    return "in"
for nm in names:
    n = b.findNet(nm)
    if n is None: cls["missing"] += 1; continue
    p = pts(n)
    onhe = any(q[2] is not None and q[2].getName() in he for q in p)
    onhw = any(q[2] is not None and q[2].getName() in hw for q in p)
    sides = "".join(sorted(set(side(x, y) for x, y, _ in p)))
    cls[("he_pin" if onhe else "") + ("hw_pin" if onhw else "") + "|" + sides] += 1
    for x, y, inst in p:
        if inst is not None: drv[inst.getMaster().getName()[:28]] += 1
    if len(ex) < 8: ex.append((nm, [(round(x,1), round(y,1), (i.getName()[-30:] if i else "BT")) for x, y, i in p][:4]))
print("he11 overflow nets", len(names)); print("class (pins|sides)", cls.most_common(20)); print("pin masters", drv.most_common(15))
for e in ex: print(" ex", e)
# global H crossing demand: for each he/hw, nets whose pins exist both west and east of the core x-span and
# whose pin y-span overlaps the core y-span (must cross it or detour N/S), and nets with a pin on the core
res = {}
allc = {**{k: ("he", v) for k, v in he.items()}, **{k: ("hw", v) for k, v in hw.items()}}
nets = [n for n in b.getNets() if not n.isSpecial() and n.getSigType() not in ("POWER", "GROUND")]
P = {n.getName(): pts(n) for n in nets}
for cn, (t, ci) in allc.items():
    cb = ci.getBBox(); X0, Y0, X1, Y1 = cb.xMin()/u, cb.yMin()/u, cb.xMax()/u, cb.yMax()/u
    cross = 0; cross_in_y = 0; pin = 0; pinEW = collections.Counter()
    for nm, p in P.items():
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        if not p: continue
        if any(q[2] is ci for q in p):
            pin += 1
            for x, y, i in p:
                if i is not ci: pinEW[side_c(x, y) if False else ("W" if x < X0 else "E" if x > X1 else "S" if y < Y0 else "N" if y > Y1 else "in")] += 1
            continue
        if min(xs) < X0 and max(xs) > X1 and min(ys) < Y1 and max(ys) > Y0:
            cross += 1
            if min(ys) >= Y0 and max(ys) <= Y1: cross_in_y += 1
    res[cn] = dict(type=t, bbox=[X0, Y0, X1, Y1], nets_with_pin=pin, pin_partner_sides=dict(pinEW), bbox_spans_EW=cross, EW_within_core_y=cross_in_y)
    print(cn, res[cn])
json.dump(res, open("/o/probe3.json", "w"), indent=1)
