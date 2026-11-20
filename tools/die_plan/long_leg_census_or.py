"""long_leg_census_or.py -- LONG-LEG-0040 census scan, OpenROAD side (derived from precheck/placed_hops_or.py; adds the capture net, the endpoint kinds and masters).  Runs INSIDE the ORFS container:

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
import time

import sys
sys.path.insert(0, "/s")
import long_leg_census as LLC  # noqa: E402  (pure helpers, same mount)
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


mast = {}
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
    mast[n] = m.getName()
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


def pin_centre(it, n):
    """centre of the ACTUAL pin shapes of a macro / hard-core iterm (COORD 11-19: the instance / core bounding box put legs at the core
    centre, hd_lep0N coll_i3 467 um vs 861 um real): area-weighted centroid of the LEF pin geometry placed with the instance orientation
    (pure maths in long_leg_census.pin_centroid, unit-tested with an off-centre pin)"""
    try:
        inst = it.getInst()
        m = inst.getMaster()
        bb = inst.getBBox()
        rects = [(bx.xMin() / dbu, bx.yMin() / dbu, bx.xMax() / dbu, bx.yMax() / dbu) for mp in it.getMTerm().getMPins() for bx in mp.getGeometry()]
        if rects:
            return LLC.pin_centroid(rects, str(inst.getOrient()), (bb.xMin() / dbu, bb.yMin() / dbu), (m.getWidth() / dbu, m.getHeight() / dbu))
    except Exception as e:  # noqa: BLE001
        log("pin geometry failed", n, repr(e)[:80])
    ok, x, y = it.getAvgXY()
    return (x / dbu, y / dbu) if ok else loc[n]


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

# capture edge per register (COORD 11-19: a negedge face has half a cycle): DFFL* / DLL* masters, or a CLK pin driven by an inverter
neg = set()
clock_driver_cache = {}
for rn in regs:
    mn = mast[rn].upper()
    inv = mn.startswith(("DFFL", "ASYNC_DFFL", "DLL"))
    inst = block.findInst(rn)
    if inst is not None:
        for it in inst.getITerms():
            if CLKPIN.match(it.getMTerm().getName()):
                net = it.getNet()
                if net is not None and LLC.clock_inverter_drivers(net, clock_driver_cache) % 2:
                    inv = not inv
    if inv:
        neg.add(rn)
log("negedge registers", len(neg))


NETLEN = os.environ.get("OT_NETLEN") == "1"      # routed DB: wire length of the leg's last net (slack census)


def net_len(nn):
    try:
        w = block.findNet(nn).getWire()
        if w is None:
            return -1.0
        for m in ("getLength", "length"):
            if hasattr(w, m):
                return round(getattr(w, m)() / dbu, 1)
    except Exception:  # noqa: BLE001
        pass
    return -1.0


# per net: driver (inst name or port), sinks [(inst or port, pin)]
drv_of = {}
pinloc = {}         # (net, macro instance, terminal) -> placed pin centre
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
            pinloc[(nn, n, pin)] = pin_centre(it, n)
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
    falling = driver[0] == "i" and instance in neg
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
    A[c] = LLC.longest_launches_by_edge(fanin_paths(c), cl) or ((0.0, c, cl, False),)
    for nn in out_nets.get(c, ()):
        for s, _pin in nets[nn][1]:
            if not isinstance(s, tuple) and s in indeg:
                indeg[s] -= 1
                if indeg[s] == 0:
                    ready.append(s)
log("comb ordered", done, "of", len(fanin), "(rest in loops)")

def kmaster(n):
    if n.startswith("port:"):
        return "port"
    return kind.get(n, "?") + ":" + mast.get(n, "?")


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
    capture_falling = capture in neg
    for path_length, launch, launch_xy, falling in paths:
        accumulated = path_length + distance
        straight = abs(launch_xy[0] - cl[0]) + abs(launch_xy[1] - cl[1])
        opposite_edges = falling != capture_falling
        legacy_xy = loc.get(launch, launch_xy)
        legacy_capture = loc[s] if isinstance(s, str) else cl
        legacy = abs(legacy_xy[0] - legacy_capture[0]) + abs(legacy_xy[1] - legacy_capture[1])
        limit = min(LLC.HALF_UM, reach) if opposite_edges else reach
        if straight > limit or legacy > limit:
            legs.append([round(straight, 1), round(accumulated, 1), launch, capture, pin,
                         [round(launch_xy[0], 1), round(launch_xy[1], 1)], [round(cl[0], 1), round(cl[1], 1)], nn,
                         kmaster(launch), kmaster(capture), round(legacy, 1), "n" if falling else "p",
                         "n" if capture_falling else "p", round(path_length, 1), net_len(nn) if NETLEN else -1.0])
legs.sort(key=lambda r: -r[0])
die = block.getDieArea()
json.dump(dict(odb=os.environ["OT_ODB"], design=block.getName(), die_um=[die.xMax() / dbu, die.yMax() / dbu], reach=reach,
               n_regs=len(regs), n_captures=len(caps), legs=legs[:200000],
                              macros=[[round(v, 2) for v in r] for r in macros]),
          open(os.environ["OT_OUT"], "w"))
log("legs > reach", len(legs), "written", os.environ["OT_OUT"])
