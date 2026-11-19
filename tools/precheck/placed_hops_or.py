"""placed_hops_or.py -- PRECHECK-1119 placed-hop scan, OpenROAD side.  Runs INSIDE the ORFS container:

    openroad -python -exit placed_hops_or.py        (env OT_ODB=<3_place.odb>, OT_OUT=<result.json>)

Every register-to-register leg of a placed netlist, declared or not: a longest-wire dynamic programme over the
combinational DAG (A(cell) = max over its input nets of A(driver) + |driver - cell|, registers / macros / ports start at
0 and carry their location).  At each capture pin (register data / reset inputs, macro inputs, output ports) the leg is
the launch -> capture pair of the longest-wire path; its straight Manhattan distance is what CBC reach (405 um) bounds.
Clock nets (nets reaching a register clock pin) are skipped.  Also dumps every register's location (in-tap skew).
Registers are recognised by master name (ASAP7 DFF* / ASYNC_DFF* / DHL* / DLL* / SDF*); ICG* is clock logic.
"""
import json
import os
import re
import time

import odb  # noqa: F401  (OpenROAD python)
from openroad import Design, Tech

T0 = time.time()
SEQ = re.compile(r"^(ASYNC_DFF|DFF|DHL|DLL|SDF|SDFH|SDFL)", re.I)
CLKPIN = re.compile(r"^(CLK|CK|CLKN|GCLK|clk)$")


def log(*a):
    print("[placed_hops %6.1fs]" % (time.time() - T0), *a, flush=True)


tech = Tech()
design = Design(tech)
design.evalTclString("read_db %s" % os.environ["OT_ODB"])
block = design.getBlock()
dbu = float(block.getDbUnitsPerMicron())
reach = float(os.environ.get("OT_REACH_UM", "405"))
log("read", os.environ["OT_ODB"], "insts", len(block.getInsts()))


def centre(inst):
    b = inst.getBBox()
    return ((b.xMin() + b.xMax()) / 2.0 / dbu, (b.yMin() + b.yMax()) / 2.0 / dbu)


kind = {}       # inst name -> 'reg' | 'macro' | 'comb' | 'tie'
loc = {}
regs = []
macros = []
for inst in block.getInsts():
    m = inst.getMaster()
    n = inst.getName()
    if m.getType() in ("CORE_TIE", "CORE_WELLTAP", "CORE_ANTENNACELL", "CORE_SPACER", "ENDCAP", "ENDCAP_PRE") or m.getName().startswith(("TAP", "FILL", "DECAP", "TIE")):
        continue
    loc[n] = centre(inst)
    if m.isBlock():
        kind[n] = "macro"
        b = inst.getBBox()
        macros.append([b.xMin() / dbu, b.yMin() / dbu, b.xMax() / dbu, b.yMax() / dbu])
    elif m.getName().upper().startswith(("TIEHI", "TIELO")):
        kind[n] = "tie"
    elif SEQ.match(m.getName()):
        kind[n] = "reg"
        regs.append(n)
    else:
        kind[n] = "comb"

# clock nets: any net touching a register clock pin, and the nets of ICG / clock buffers feeding them are left as data
# (their sinks are clock pins, so no data capture is counted on them)
clock_nets = set()
for net in block.getNets():
    st = net.getSigType()
    if st in ("POWER", "GROUND"):
        clock_nets.add(net.getName())
        continue
    if st == "CLOCK":
        clock_nets.add(net.getName())
        continue
    for it in net.getITerms():
        n = it.getInst().getName()
        if kind.get(n) == "reg" and CLKPIN.match(it.getMTerm().getName()):
            clock_nets.add(net.getName())
            break
log("clock/power nets", len(clock_nets))

# per net: driver (inst name or port), sinks [(inst or port, pin)]
drv_of = {}
pinloc = {}         # (net, macro inst) -> pin centre (a macro end of a leg sits at its pin, not the macro centre)
fanin = {}          # comb inst -> [nets]
caps = []           # (net, capture inst/port, pin)
nets = {}
for net in block.getNets():
    nn = net.getName()
    if nn in clock_nets:
        continue
    d = None
    sinks = []
    for it in net.getITerms():
        n = it.getInst().getName()
        if n not in kind:
            continue
        if kind[n] == "macro":
            try:
                b = it.getBBox()
                pinloc[(nn, n)] = ((b.xMin() + b.xMax()) / 2.0 / dbu, (b.yMin() + b.yMax()) / 2.0 / dbu)
            except Exception:  # noqa: BLE001
                pass
        if it.isOutputSignal():
            d = ("i", n)
        elif it.isInputSignal():
            sinks.append((n, it.getMTerm().getName()))
    for bt in net.getBTerms():
        ok, x, y = bt.getFirstPinLocation()
        p = ("p", bt.getName(), (x / dbu, y / dbu) if ok else None)
        if bt.getIoType() == "INPUT":
            d = p
        else:
            sinks.append((p, None))
    if d is None:
        continue
    nets[nn] = (d, sinks)
    for s, pin in sinks:
        if isinstance(s, tuple):
            caps.append((nn, s, pin))
        elif kind[s] == "comb":
            fanin.setdefault(s, []).append(nn)
        else:
            caps.append((nn, s, pin))
log("nets", len(nets), "comb with fanin", len(fanin), "captures", len(caps))


def dloc(d, net=None):
    if d[0] == "p":
        return d[2]
    return pinloc.get((net, d[1]), loc[d[1]])


def dname(d):
    return ("port:" + d[1]) if d[0] == "p" else d[1]


# A[inst] = (acc wire um, launch name, launch loc); Kahn order over comb insts
out_nets = {}
for nn, (d, sinks) in nets.items():
    if d[0] == "i" and kind[d[1]] == "comb":
        out_nets.setdefault(d[1], []).append(nn)
indeg = {c: 0 for c in fanin}
for c, ins in fanin.items():
    for nn in ins:
        d = nets[nn][0]
        if d[0] == "i" and kind[d[1]] == "comb" and d[1] in indeg:
            indeg[c] += 1
A = {}


def src_val(d, net=None):
    if d[0] == "i" and kind[d[1]] == "comb":
        return A.get(d[1])
    if d[0] == "i" and kind[d[1]] == "tie":
        return None                                   # constants are not launches
    l = dloc(d, net)
    return (0.0, dname(d), l) if l else None


ready = [c for c, k in indeg.items() if k == 0]
done = 0
while ready:
    c = ready.pop()
    done += 1
    best = None
    cl = loc[c]
    for nn in fanin[c]:
        d = nets[nn][0]
        v = src_val(d, nn)
        if v is None:
            continue
        dl = dloc(d, nn) if not (d[0] == "i" and kind[d[1]] == "comb") else loc[d[1]]
        acc = v[0] + abs(dl[0] - cl[0]) + abs(dl[1] - cl[1])
        if best is None or acc > best[0]:
            best = (acc, v[1], v[2])
    A[c] = best or (0.0, c, cl)
    for nn in out_nets.get(c, ()):
        for s, _pin in nets[nn][1]:
            if not isinstance(s, tuple) and s in indeg:
                indeg[s] -= 1
                if indeg[s] == 0:
                    ready.append(s)
log("comb ordered", done, "of", len(fanin), "(rest in loops)")

legs = []
for nn, s, pin in caps:
    d = nets[nn][0]
    v = src_val(d, nn)
    if v is None:
        continue
    cl = s[2] if isinstance(s, tuple) else pinloc.get((nn, s), loc[s])
    if cl is None:
        continue
    dl = dloc(d, nn) if not (d[0] == "i" and kind[d[1]] == "comb") else loc[d[1]]
    acc = v[0] + abs(dl[0] - cl[0]) + abs(dl[1] - cl[1])
    straight = abs(v[2][0] - cl[0]) + abs(v[2][1] - cl[1])
    if straight > reach * 0.9:
        legs.append([round(straight, 1), round(acc, 1), v[1], ("port:" + s[1]) if isinstance(s, tuple) else s, pin,
                     [round(v[2][0], 1), round(v[2][1], 1)], [round(cl[0], 1), round(cl[1], 1)]])
legs.sort(key=lambda r: -r[0])
die = block.getDieArea()
json.dump(dict(odb=os.environ["OT_ODB"], design=block.getName(), die_um=[die.xMax() / dbu, die.yMax() / dbu], reach=reach,
               n_regs=len(regs), n_captures=len(caps), legs=legs[:200000],
               regs=[[round(loc[r][0], 2), round(loc[r][1], 2)] for r in regs],
               macros=[[round(v, 2) for v in r] for r in macros]),
          open(os.environ["OT_OUT"], "w"))
log("legs >= 0.9 reach", len(legs), "written", os.environ["OT_OUT"])
