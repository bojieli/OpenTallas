"""placed_hops_or.py -- PRECHECK-1119 placed-hop scan, OpenROAD side.  Runs INSIDE the ORFS container:

    openroad -python -exit placed_hops_or.py        (env OT_ODB=<3_place.odb>, OT_OUT=<result.json>)

At each capture endpoint the combinational DAG yields the longest accumulated wire path for each
launch clock edge. The straight Manhattan distance between the launch and capture endpoints is
compared with the full-cycle limit or the half-cycle limit for opposite edges.
Clock nets (nets reaching a register clock pin) are skipped.  Also dumps every register's location (in-tap skew).
Registers are recognised by master name (ASAP7 DFF* / ASYNC_DFF* / DHL* / DLL* / SDF*); ICG* is clock logic.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import odb  # noqa: F401  (OpenROAD python)
from openroad import Design, Tech

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
from long_leg_census import HALF_UM, clock_inverter_drivers, longest_launches_by_edge, pin_centroid

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
falling_regs = set()
clock_driver_cache = {}
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
        falling = m.getName().upper().startswith(("DFFL", "ASYNC_DFFL", "DLL"))
        for it in inst.getITerms():
            if CLKPIN.match(it.getMTerm().getName()):
                net = it.getNet()
                if net is not None and clock_inverter_drivers(net, clock_driver_cache):
                    falling = not falling
        if falling:
            falling_regs.add(n)
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

def macro_pin_loc(it):
    inst = it.getInst()
    m = inst.getMaster()
    try:
        rects = [(r.xMin() / dbu, r.yMin() / dbu, r.xMax() / dbu, r.yMax() / dbu)
                 for pin in it.getMTerm().getMPins() for r in pin.getGeometry()]
        if rects:
            bb = inst.getBBox()
            return pin_centroid(rects, str(inst.getOrient()), (bb.xMin() / dbu, bb.yMin() / dbu),
                                (m.getWidth() / dbu, m.getHeight() / dbu))
    except (AttributeError, KeyError, RuntimeError) as e:
        log("macro pin geometry unavailable", inst.getName(), it.getMTerm().getName(), str(e)[:80])
    ok, x, y = it.getAvgXY()
    return (x / dbu, y / dbu) if ok else loc[inst.getName()]


# per net: driver (inst name or port), sinks [(inst or port, pin)]
pinloc = {}         # (net, macro inst, pin) -> pin centre
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
        pin = it.getMTerm().getName()
        if kind[n] == "macro":
            pinloc[(nn, n, pin)] = macro_pin_loc(it)
        if it.isOutputSignal():
            d = ("i", n, pin)
        elif it.isInputSignal():
            sinks.append((n, pin))
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
    return pinloc.get((net, d[1], d[2]), loc[d[1]])


def dname(d):
    return ("port:" + d[1]) if d[0] == "p" else d[1]


# Longest inferred data path per launch edge in Kahn order over combinational instances.
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


def source_paths(driver, net):
    instance = driver[1]
    if driver[0] == "i":
        if kind[instance] == "comb":
            return A.get(instance, ())
        if kind[instance] == "tie":
            return ()
    xy = dloc(driver, net)
    falling = driver[0] == "i" and instance in falling_regs
    return ((0.0, dname(driver), xy, falling),) if xy else ()


def fanin_paths(instance):
    for net in fanin[instance]:
        driver = nets[net][0]
        paths = source_paths(driver, net)
        if paths:
            yield dloc(driver, net), paths


ready = [c for c, k in indeg.items() if k == 0]
done = 0
while ready:
    c = ready.pop()
    done += 1
    cl = loc[c]
    A[c] = longest_launches_by_edge(fanin_paths(c), cl) or ((0.0, c, cl, False),)
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
    paths = source_paths(d, nn)
    if not paths:
        continue
    cl = s[2] if isinstance(s, tuple) else pinloc.get((nn, s, pin), loc[s])
    if cl is None:
        continue
    dl = dloc(d, nn)
    distance = abs(dl[0] - cl[0]) + abs(dl[1] - cl[1])
    capture = ("port:" + s[1]) if isinstance(s, tuple) else s
    capture_falling = capture in falling_regs
    for path_length, launch, launch_xy, falling in paths:
        accumulated = path_length + distance
        straight = abs(launch_xy[0] - cl[0]) + abs(launch_xy[1] - cl[1])
        opposite_edges = falling != capture_falling
        limit = min(reach, HALF_UM) if opposite_edges else reach
        if straight > limit * 0.9:
            legs.append([round(straight, 1), round(accumulated, 1), launch, capture, pin,
                         [round(launch_xy[0], 1), round(launch_xy[1], 1)], [round(cl[0], 1), round(cl[1], 1)], opposite_edges])
legs.sort(key=lambda r: -r[0])
die = block.getDieArea()
json.dump(dict(scan_version=3, odb=os.environ["OT_ODB"], design=block.getName(), die_um=[die.xMax() / dbu, die.yMax() / dbu], reach=reach,
               n_regs=len(regs), n_captures=len(caps), legs=legs[:200000],
               regs=[[round(loc[r][0], 2), round(loc[r][1], 2)] for r in regs],
               macros=[[round(v, 2) for v in r] for r in macros]),
          open(os.environ["OT_OUT"], "w"))
log("legs >= 0.9 reach", len(legs), "written", os.environ["OT_OUT"])
