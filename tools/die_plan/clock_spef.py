#!/usr/bin/env python3
"""FABLE-DIE-QC-R S4q9m: exact-length RC of the die clock tree as SPEF (read_spef in the combo proof instead of
estimate_parasitics -global_routing).  The GRT estimate snaps every pin to its 10.8-um gcell: two copies of one region tree whose
partitions are not a whole number of gcells apart get different wire on EVERY net (measured: same placed tree, same guides, +21 %
wire cap, 108 ps on a 1.1-ns local path), so same-type instances can never have the same tap offsets in that readout.
Model (ASAP7 setRC.tcl values): each net = single-trunk rectilinear tree from the placed cell sites: M8 trunk along the driver's y
over the x span of its pins, M9 branch per pin column, via stack M1..M8 (91.6 ohm) / M1..M9 (97.9 ohm) at every cell pin, V8 at a
trunk-branch corner; tap ports are M9 pins.  Valid only with the chain's GRT: overflow 0 and no clock net longer than its placed
length + 2 gcells (bin/detour.py).
usage: clock_spef.py CTREE_V TREE_JSON OUT_SPEF [--prefix ck_] [--design die_combo]"""
import json, re, sys, argparse
ap = argparse.ArgumentParser(); [ap.add_argument(x) for x in ("ctree", "tree", "out")]
ap.add_argument("--prefix", default="ck_"); ap.add_argument("--design", default="die_combo")
ap.add_argument("--pin-escape-um", type=float, default=0.0)   # M9 wire in series with every cell pin stack (pin access / track jog)
a = ap.parse_args()
R8, C8, R9, C9 = 8.44765e-3, 1.03962e-1, 8.89556e-3, 9.28446e-2      # kohm/um, fF/um
VIA = [0.0172, 0.0172, 0.0172, 0.0118, 0.0118, 0.0082, 0.0082, 0.0063]  # V1..V8 kohm
S8, S9, V8 = sum(VIA[:7]), sum(VIA), VIA[7]
t = json.load(open(a.tree)); site = t["sites"]
pxy = {x["port"]: x["xy"] for x in t["taps"]}
root = next(n for n in t["nodes"].values() if n["parent"] is None); pxy["root"] = [root["x"], root["y"]]
drv, snk = {}, {}            # net -> (kind, name, pin) ; net -> [(kind, name, pin)]
for l in open(a.ctree):
    s = l.strip()
    m = re.match(r"(\w+)\s+(\w+)\s*\(\.A\((\w+)\), \.Y\((\w+)\)\);", s)
    if m:
        _, c, i, o = m.groups(); drv[o] = ("I", c, "Y"); snk.setdefault(i, []).append(("I", c, "A")); continue
    m = re.match(r"assign\s+(\w+)\s*=\s*(\w+)\s*;", s)
    if m: snk.setdefault(m.group(2), []).append(("P", m.group(1), None))
P = a.prefix
def xy(p): return pxy[p[1]] if p[0] == "P" else site[p[1]]
def nm(p): return p[1] if p[0] == "P" else f"{P}{p[1]}:{p[2]}"
LE = a.pin_escape_um
EPS = 0.02
with open(a.out, "w") as f:
    f.write(f'*SPEF "IEEE 1481-1998"\n*DESIGN "{a.design}"\n*DATE "x"\n*VENDOR "opentallas"\n*PROGRAM "clock_spef"\n*VERSION "1"\n*DESIGN_FLOW "x"\n'
            '*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 PS\n*C_UNIT 1 FF\n*R_UNIT 1 KOHM\n*L_UNIT 1 HENRY\n\n')
    nn = 0; wl = 0.0
    for net, sinks in snk.items():
        d = drv.get(net)
        if d is None:
            if net != "root": raise SystemExit(f"undriven net {net}")
            continue                    # the root port net: ideal driver, first cell sits on the root pin
        N = net if net in pxy else P + net
        xd, yd = xy(d)
        cap, res, k = {}, [], [0]
        def node():
            k[0] += 1; n = f"{N}:{k[0]}"; cap[n] = 0.0; return n
        def pin(n, p, r):
            """stack (+ escape wire) between tree node n and pin p"""
            if p[0] == "I" and LE > 0:
                cap[n] += C9 * LE / 2; e = node(); cap[e] += C9 * LE / 2
                res.append((n, e, R9 * LE)); n = e
            res.append((n, nm(p), r))
        def wire(u, v, L, r, c):
            cap[u] += c * L / 2; cap[v] += c * L / 2; res.append((u, v, max(r * L, 1e-6)))
        cols = {}
        for p in sinks:
            x, y = xy(p); kx = next((q for q in cols if abs(q - x) < EPS), None)
            if kx is None: kx = x; cols[kx] = []
            cols[kx].append((y, p))
        xs = sorted(set(list(cols) + [next((q for q in cols if abs(q - xd) < EPS), xd)]))
        trunk = len(xs) > 1
        tn = {x: node() for x in xs}                       # trunk node per column (M8 when a trunk exists)
        x0 = next(q for q in xs if abs(q - xd) < EPS)
        for u, v in zip(xs, xs[1:]): wire(tn[u], tn[v], v - u, R8, C8); wl += v - u
        pin(tn[x0], d, S8 if trunk else S9)                 # driver stack: to the M8 trunk, or straight to its M9 column
        for x, pl in cols.items():
            for side in (1, -1):
                ch = sorted((p for p in pl if side * (p[0] - yd) > EPS), key=lambda p: side * p[0])
                prev, py, first = tn[x], yd, True
                for y, p in ch:
                    n = node()
                    if first and trunk: v8 = node(); res.append((prev, v8, V8)); prev = v8
                    first = False
                    wire(prev, n, abs(y - py), R9, C9); wl += abs(y - py)
                    pin(n, p, 1e-6 if p[0] == "P" else S9); prev, py = n, y
            for y, p in pl:
                if abs(y - yd) <= EPS:                        # on the trunk row: M8 pin stack / V8 up to an M9 port
                    pin(tn[x], p, (S8 if trunk else S9) if p[0] == "I" else (V8 if trunk else 1e-6))
        f.write(f"*D_NET {N} {sum(cap.values()):.5f}\n*CONN\n*I {nm(d)} O\n")
        for p in sinks: f.write(f"*P {p[1]} O\n" if p[0] == "P" else f"*I {nm(p)} I\n")
        f.write("*CAP\n"); [f.write(f"{i} {n} {c:.6f}\n") for i, (n, c) in enumerate(cap.items(), 1) if c > 0]
        f.write("*RES\n"); [f.write(f"{i} {u} {v} {r:.7f}\n") for i, (u, v, r) in enumerate(res, 1)]
        f.write("*END\n\n"); nn += 1
print("nets", nn, "wire_um", round(wl, 1))
