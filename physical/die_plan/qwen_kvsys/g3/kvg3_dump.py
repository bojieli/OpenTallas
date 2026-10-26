# KV-G3: dump a placed/CTS/routed ODB for geometry review (openroad -python -exit; env ODB, OUT)
import json
import os
import odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ["ODB"])
blk = db.getChip().getBlock()
dbu = blk.getDbUnitsPerMicron()
die = blk.getDieArea()
insts = []
for i in blk.getInsts():
    m = i.getMaster()
    mn = m.getName()
    bb = i.getBBox()
    if mn.startswith(("TAPCELL", "FILLER", "DECAP")):
        cls = "phys"
    elif m.isBlock():
        cls = "macro"
    elif mn.startswith(("DFF", "ASYNC_DFF", "SDF", "DHL", "DLL", "ICG")):
        cls = "ff"
    elif mn.startswith(("BUF", "INV", "HB", "CKINV")):
        cls = "buf"
    else:
        cls = "logic"
    ck = ""
    if cls == "ff":
        for it in i.getITerms():
            if it.getMTerm().getSigType() == "CLOCK" or it.getMTerm().getName() == "CLK":
                n = it.getNet()
                ck = n.getName() if n else ""
    insts.append([i.getName(), mn, cls, round(bb.xMin() / dbu, 3), round(bb.yMin() / dbu, 3),
                  round(bb.xMax() / dbu, 3), round(bb.yMax() / dbu, 3), ck])
pins = []
for bt in blk.getBTerms():
    for bp in bt.getBPins():
        for b in bp.getBoxes():
            pins.append([bt.getName(), b.getTechLayer().getName(), round((b.xMin() + b.xMax()) / 2 / dbu, 3),
                         round((b.yMin() + b.yMax()) / 2 / dbu, 3)])
            break
        break
# reg->reg / pin->reg / reg->pin hop distances: follow nets through buffers / inverters / logic (max 6 cells deep)
def loc(i):
    bb = i.getBBox()
    return ((bb.xMin() + bb.xMax()) / 2 / dbu, (bb.yMin() + bb.yMax()) / 2 / dbu)
def isff(i):
    return i.getMaster().getName().startswith(("DFF", "ASYNC_DFF", "SDF", "DHL", "DLL"))
def sinks(net, depth=0, seen=None):
    """registers / output ports reached from net through combinational cells"""
    seen = seen if seen is not None else set()
    out = []
    if net is None or net.getId() in seen or depth > 6 or net.getSigType() in ("CLOCK", "POWER", "GROUND"):
        return out
    seen.add(net.getId())
    for it in net.getITerms():
        if not it.isInputSignal():
            continue
        i = it.getInst()
        if isff(i):
            if it.getMTerm().getName() == "D":
                out.append(("ff", i))
        elif i.getMaster().isBlock():
            out.append(("macro", i))
        else:
            for o in i.getITerms():
                if o.isOutputSignal():
                    out += sinks(o.getNet(), depth + 1, seen)
    for bt in net.getBTerms():
        if bt.getIoType() == "OUTPUT":
            out.append(("port", bt))
    return out
def bt_xy(bt):
    for bp in bt.getBPins():
        b = bp.getBBox()
        return ((b.xMin() + b.xMax()) / 2 / dbu, (b.yMin() + b.yMax()) / 2 / dbu)
    return None
hops = {"ff_ff": [], "pin_ff": [], "ff_pin": []}
for i in blk.getInsts():
    if not isff(i):
        continue
    a = loc(i)
    for it in i.getITerms():
        if it.isOutputSignal() and it.getNet() is not None:
            for k, s in sinks(it.getNet()):
                if k == "ff":
                    b = loc(s); hops["ff_ff"].append([round(abs(a[0]-b[0]) + abs(a[1]-b[1]), 1), i.getName(), s.getName(), a, b])
                elif k == "port":
                    b = bt_xy(s)
                    if b: hops["ff_pin"].append([round(abs(a[0]-b[0]) + abs(a[1]-b[1]), 1), i.getName(), s.getName(), a, b])
for bt in blk.getBTerms():
    if bt.getIoType() != "INPUT" or bt.getNet() is None or bt.getNet().getSigType() == "CLOCK":
        continue
    a = bt_xy(bt)
    if not a:
        continue
    for k, s in sinks(bt.getNet()):
        if k == "ff":
            b = loc(s); hops["pin_ff"].append([round(abs(a[0]-b[0]) + abs(a[1]-b[1]), 1), bt.getName(), s.getName(), a, b])
json.dump(dict(hops=hops, die=[die.xMin() / dbu, die.yMin() / dbu, die.xMax() / dbu, die.yMax() / dbu], insts=insts, pins=pins),
          open(os.environ["OUT"], "w"))
print("KVG3_DUMP", len(insts), len(pins))
