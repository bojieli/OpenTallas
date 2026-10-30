#!/usr/bin/env python3
"""geom_rules.py -- AUTO-GEOM rule check of a placed / CTS checkpoint (OWNER 2026-10-25 ~20:25).

Owner decision: a part built from a template that already has a visual GEOM PASS may pass on automated rule checks,
with visual review sampled 1 in 5. Owner 2026-10-27 08:02 extends this to new kits on measured absolute
checks (--all-kits); every FAIL requests visual review, and die assemblies stay in their separate review flow.  This module judges the
geom_dump.tcl dump of the replica's 3_place / 4_cts ODB with the rules the visual reviewers already enforce.  Every
threshold below names its source; nothing here is a new gate.  A rule that cannot be evaluated is NA (never PASS by
default for a required rule: a required NA makes the verdict FAIL -> visual review).

    python3 geom_rules.py DUMP.tsv [--json OUT.json] [--template TEMPLATE_auto_geom.json] [--outline WxH]
                                   [--strap-re REGEX] [--title T]

Rules (id: limit -- source):
  outline   : W x H == parent slot (plan outline / template outline) within 0.01 um; aspect <= 2.0 unless the slot
              itself is the visually passed template outline -- METHODOLOGY 1.14 ("outline derived from the parent slot",
              "aspect <= ~2:1"); memory tile-outline-from-parent-slot-1023 (A0 820x907 vs 611x1307 slot)
  fill      : std-cell fill of the free (non-macro) area >= 20 % -- tools/ref_tile/layout_review.py FILL_FREE_FAIL (main
              pre-route gate, TILE-REVIEW 10-23); METHODOLOGY 1.14 (target 40-60 %); GEOM-REVIEW qkd_ahub 12 % FAIL
  empty     : share of macro-free density bins below 5 % density <= 50 % -- layout_review.py EMPTY_FLAG/EMPTY_BIN_DENSITY;
              GEOM-REVIEW qkd_ahub "W/N thirds empty" FAIL
  pin_reg   : every signal pin registered (first flop through pure BUF/INV, a hard-macro pin, or -- COORD 10-29 11:09 /
              GEOM-59 -- a declared landing-ring input: land_slots.json + face_guard.json PASS + exactly D slot flops in the
              pin's comb cone, judged at the farthest slot) and pin->register p90
              <= 30 um -- METHODOLOGY 1.9 (R2 face flops, "pin-to-reg p90 <= 30 um"); layout_review.py PIN_REG_P90_FAIL
              150 um is the hard backstop; clock ports and declared strap_* pins are exempt (METHODOLOGY 1.8 R7 note)
  r2r       : max register->register Manhattan distance (flop centre to flop centre through combinational logic and
              buffers, data and reset pins) <= 405 um -- METHODOLOGY 1.3 / 4.2 (reach 405 per cycle; reset relays every
              <= 405 um); GEOM-REVIEW 10-24 g3k5 FAIL "u_s0->u_t0.c0 905 um"; results/geom_review/s81_head_kits_1025
              hk_ana.py rr_gt405
  pin_density: peak pins in any 10-um face window <= 6 pins/um per layer and face -- METHODOLOGY 5.2; a BUDGET (COORD
              10-27 10:48): an excess is WARN (layer, face, peak, window in the verdict line / GEOM REQ), not FAIL;
              memory tile-review-pin-clustering-1017 (bf_cl_fp 9/um, pegress 10/um partial faces)
  pin_table : pins (name, face, layer, position +-0.05 um) == template pin table up to strap_* pins -- METHODOLOGY 1.5
              (one type = one view; replica shares the lattice) + owner 10-25 template rule ("same pin table up to
              straps")
  macros    : hard macros / hardened children at the template's positions (+-0.01 um, same masters) -- memory
              tile-review-pin-clustering-1017 (macros on the 43.2-um lattice), METHODOLOGY 5.6 (macros on the lattice)
  std_band  : with macros: the largest connected macro-free region holds >= 95 % of the std-cell area (one contiguous
              std-cell band, no cells in slivers between macros) -- memory tile-review-pin-clustering-1017 (NL c1 62k
              cells in slivers, DPL-0033).  The 95 % figure is this tool's reading of "one contiguous band"; it can only
              FAIL a replica towards visual review, never pass something the template did not.
  clock_taps: with >= 2 grid taps (clk|ck, clk_t<i>): no grid tap with 0 sinks and <= 1500 sinks per tap -- METHODOLOGY
              3.3 (~1000-1500 sinks/tap, no taps over empty area); GEOM-REVIEW 10-24 g3k5 FAIL "0..3007 sinks/tap",
              "4 empty N taps", KV hub_Ei vC FAIL "empty taps".  Sinks: actual tree (CTS checkpoint) or the nearest-tap
              split tools/die_plan/clock_taps.tcl applies before CTS (placed checkpoint).
  tap_set   : same tap ports (names, faces) as the template -- template rule (same pin table)
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import json
import hashlib
import math
import re
import sys
from collections import Counter, defaultdict, deque

INF = float("inf")
R2R_MAX = 405.0
PINREG_P90 = 30.0
PINREG_HARD = 150.0
PINREG_DEPTH = 4
FILL_MIN = 0.20
EMPTY_MAX = 0.50
EMPTY_BIN_DENSITY = 0.05
PIN_WIN_MAX = 6.0
TAP_SINKS_MAX = 1500
BAND_MIN = 0.95
ASPECT_MAX = 2.0
POS_TOL = 0.05
OUTLINE_TOL = 0.01
GRID_TAP_RE = re.compile(r"^(clk|ck)(_t\d+)?$")
CLOCK_PIN_RE = re.compile(r"(^|_)(clk|ck)(_[tc]\d+)?(\[\d+\])?$|^clk_|^tile_clk$")
STRAP_RE_DEFAULT = r"^strap_"


def load(path, extra=None):
    die = None
    cells, pins, nets = {}, [], []
    ex = extra if extra is not None else {}
    ex.setdefault("tech", {})
    ex.setdefault("mobs", {})
    ex.setdefault("status", {})
    with open(path) as fh:
        for ln in fh:
            f = ln.rstrip("\n").split("\t")
            t = f[0]
            if t == "R":
                ex["core"] = tuple(map(float, f[1:5]))
            elif t == "T":
                ex["tech"][f[1]] = (f[2], float(f[3]))
            elif t == "O":
                ex["mobs"][f[1]] = set(x for x in f[2:] if x)
            elif t == "I":
                ex.setdefault("macro_ports", {})[f[1]] = dict(v.split(":",1) for v in f[2:])
            elif t == "Q":
                ex["status"][int(f[1])] = f[2]
            elif t == "C":
                cells[int(f[1])] = (f[2], f[3], float(f[4]), float(f[5]), float(f[6]), float(f[7]), f[8] if len(f) > 8 else "")
            elif t == "N":
                nets.append((f[1], f[2], f[3:]))
            elif t == "P":
                pins.append(dict(k=int(f[1]), name=f[2], io=f[3], sig=f[4], layer=f[5], x=float(f[6]), y=float(f[7])))
            elif t == "D":
                die = tuple(map(float, f[1:5]))
    return die, cells, pins, nets


def ctr(c):
    return (c[2] + c[4]) / 2, (c[3] + c[5]) / 2


def q(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * p
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def face_of(x, y, die, tol=2.0):
    X0, Y0, X1, Y1 = die
    if x < X0 + tol:
        return "W"
    if x > X1 - tol:
        return "E"
    if y < Y0 + tol:
        return "S"
    if y > Y1 - tol:
        return "N"
    return "area"


def ref(s):
    """'i12' -> ('i', 12, False); 'i12c' -> ('i', 12, True); 'p3' -> ('p', 3, False); '-' -> None"""
    if s == "-" or not s:
        return None
    if s[0] == "p":
        return ("p", int(s[1:]), False)
    clk = s.endswith("c")
    return ("i", int(s[1:-1] if clk else s[1:]), clk)


class Design:
    def __init__(self, path, memory_libs=(), memory_reach=False):
        self.extra = {}
        self.memory_models = {}
        # COORD 10-29: typed-memory reach is OPT-IN (default off = macros omitted from r2r exactly as before)
        self.memory_reach = bool(memory_reach)
        if memory_libs and self.memory_reach:
            spec=importlib.util.spec_from_file_location("geom_memory", Path(__file__).with_name("geom_memory.py"))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            self.memory_models=module.liberty_models(memory_libs)
        self.die, self.cells, self.pins, raw = load(path, self.extra)
        self.pin_by_k = {p["k"]: p for p in self.pins}
        self.nets = []            # (sig, drv ref, [sink refs])
        self.drives = defaultdict(list)    # cell id -> [net idx]
        self.pin_net = {}          # pin k -> net idx
        self.cell_in = defaultdict(list)   # cell id -> [(net idx, is_clock_pin)]
        for sig, d, ss in raw:
            n = len(self.nets)
            dr = ref(d)
            sk = [ref(s) for s in ss if ref(s)]
            self.nets.append((sig, dr, sk))
            if dr and dr[0] == "i":
                self.drives[dr[1]].append(n)
            elif dr:
                self.pin_net[dr[1]] = n
            for s in sk:
                if s[0] == "p":
                    self.pin_net[s[1]] = n
                else:
                    self.cell_in[s[1]].append((n, s[2]))

    def kind(self, cid):
        c = self.cells.get(cid)
        return c[0] if c else None


# ------------------------------------------------------------------------------------------------ metrics
def area_metrics(D, bins=80):
    X0, Y0, X1, Y1 = D.die
    W, H = X1 - X0, Y1 - Y0
    macros = [c for c in D.cells.values() if c[0] == "M"]
    std = [c for c in D.cells.values() if c[0] in "SBKL"]

    def clip(c):
        return max(0.0, min(c[4], X1) - max(c[2], X0)) * max(0.0, min(c[5], Y1) - max(c[3], Y0))
    marea = sum(clip(c) for c in macros)
    free = max(0.0, W * H - marea)
    sarea = sum((c[4] - c[2]) * (c[5] - c[3]) for c in std)
    bw = max(max(W, H) / bins, 2.0)
    nx, ny = max(1, int(math.ceil(W / bw))), max(1, int(math.ceil(H / bw)))
    grid = [0.0] * (nx * ny)
    for c in std:
        x, y = ctr(c)
        i = min(nx - 1, max(0, int((x - X0) / bw)))
        j = min(ny - 1, max(0, int((y - Y0) / bw)))
        grid[j * nx + i] += (c[4] - c[2]) * (c[5] - c[3])
    cov = [False] * (nx * ny)
    for m in macros:
        for j in range(max(0, int((m[3] - Y0) / bw)), min(ny, int(math.ceil((m[5] - Y0) / bw)))):
            cy = Y0 + (j + .5) * bw
            if not m[3] <= cy <= m[5]:
                continue
            for i in range(max(0, int((m[2] - X0) / bw)), min(nx, int(math.ceil((m[4] - X0) / bw)))):
                if m[2] <= X0 + (i + .5) * bw <= m[4]:
                    cov[j * nx + i] = True
    freeb = emptyb = 0
    usable = [False] * (nx * ny)
    for j in range(ny):
        for i in range(nx):
            k = j * nx + i
            a = (min(X1, X0 + (i + 1) * bw) - (X0 + i * bw)) * (min(Y1, Y0 + (j + 1) * bw) - (Y0 + j * bw))
            if cov[k] or a < 0.25 * bw * bw:
                continue
            usable[k] = True
            freeb += 1
            if grid[k] / a < EMPTY_BIN_DENSITY:
                emptyb += 1
    # largest 4-connected macro-free component and its share of the std-cell area
    comp = [-1] * (nx * ny)
    best = 0.0
    tot = sum(grid[k] for k in range(nx * ny) if usable[k]) or 0.0
    for s in range(nx * ny):
        if not usable[s] or comp[s] >= 0:
            continue
        comp[s] = s
        dq, acc = deque([s]), 0.0
        while dq:
            k = dq.popleft()
            acc += grid[k]
            i, j = k % nx, k // nx
            for ii, jj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= ii < nx and 0 <= jj < ny:
                    kk = jj * nx + ii
                    if usable[kk] and comp[kk] < 0:
                        comp[kk] = s
                        dq.append(kk)
        best = max(best, acc)
    return dict(outline=[round(W, 4), round(H, 4)], aspect=round(max(W, H) / max(1e-9, min(W, H)), 3),
                macros=len(macros), macro_area_pct=round(100 * marea / max(1e-9, W * H), 2),
                std_cells=len(std), ff=sum(1 for c in std if c[0] == "S"),
                fill_of_free=round(sarea / free, 4) if free > 1 and std else None,
                empty_area=round(emptyb / freeb, 4) if freeb and std else None,
                band_share=round(best / tot, 4) if tot > 0 else None, density_bin_um=round(bw, 3),
                macro_list=sorted([c[1], round(c[2] - X0, 3), round(c[3] - Y0, 3)] for c in macros))


def pin_metrics(D, strap_re):
    X0, Y0, X1, Y1 = D.die
    W, H = X1 - X0, Y1 - Y0
    faces, pos, table = Counter(), defaultdict(list), []
    for p in D.pins:
        if p["sig"] in ("POWER", "GROUND"):
            continue
        f = face_of(p["x"], p["y"], D.die)
        p["face"] = f
        faces[f] += 1
        pos[f].append(p["x"] if f in "NS" else p["y"])
        if not strap_re.search(p["name"]):
            table.append([p["name"], f, p["layer"], round(p["x"] - X0, 3), round(p["y"] - Y0, 3)])
    peak = {}
    for f, v in pos.items():
        if f == "area":
            continue
        v.sort()
        j = best = 0
        for i in range(len(v)):
            while v[i] - v[j] > 10.0:
                j += 1
            best = max(best, i - j + 1)
        peak[f] = round(best / 10.0, 2)
    lpos = defaultdict(list)
    for p in D.pins:
        if p["sig"] in ("POWER", "GROUND") or p.get("face", "area") == "area":
            continue
        lpos[(p["face"], p["layer"])].append(p["x"] if p["face"] in "NS" else p["y"])
    lpeak, lwin = {}, {}
    for fl, v in lpos.items():
        v.sort()
        j = best = bj = 0
        for i in range(len(v)):
            while v[i] - v[j] > 10.0:
                j += 1
            if i - j + 1 > best:
                best, bj = i - j + 1, j
        key = f"{fl[0]}/{fl[1]}"
        lpeak[key] = round(best / 10.0, 2)
        if v:                                         # the peak 10-um window, die-relative, along the face axis
            o = X0 if fl[0] in "NS" else Y0
            lwin[key] = ["x" if fl[0] in "NS" else "y", round(v[bj] - o, 2), round(v[bj] - o + 10.0, 2)]
    flen = {"N": W, "S": W, "E": H, "W": H}
    span = {f: round((max(v) - min(v)) / flen[f], 3) for f, v in pos.items() if f != "area" and v and flen[f] > 0}
    return dict(pins_per_face=dict(faces), pin_peak_per_um_10um=peak, pin_peak_layer=lpeak, pin_peak_layer_win=lwin,
                pin_peak_layer_max=max(lpeak.values()) if lpeak else 0.0, face_span=span, pin_table=sorted(table))


def declared_infra_arcs(D, interface, declaration):
    """12.2a1 die-owned scalar clock/reset pass-throughs, never a name exemption.

    ft_ports.v1 and ft_interface_model.v1 define DIE ownership and scalar ports.
    Verify their shared digest, explicit roles/directions/endpoints, and the
    checkpoint's pure-buffer connectivity and non-inverting truth table. Keep
    all accepted/rejected arc records; characterization and die STA stay required.
    """
    result = dict(owner="die", width=1, arcs=[], pins=[], errors=[])
    try:
        if declaration.get("schema") != "opentallas.ft_ports.v1" or interface.get("schema") != "opentallas.ft_interface_model.v1":
            raise ValueError("missing typed declaration/interface schema")
        if declaration.get("owner", "die") != "die" or interface.get("owner", "die") != "die":
            raise ValueError("feedthrough owner must be die")
        ports, arcs = declaration["ports"], declaration["arcs"]
        body = dict(ports=sorted(ports,key=lambda p:p["name"]),arcs=sorted(arcs,key=lambda a:(a["source"],a["sink"])))
        digest = hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if declaration.get("sha256") != digest or interface.get("ft_sha256") != digest:
            raise ValueError("declaration/interface digest mismatch")
        declared = {p["name"]:p for p in ports}
        if len(declared) != len(ports) or not arcs:
            raise ValueError("duplicate ports or empty arcs")
        for n,p in declared.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n) or type(p.get("width",1)) is not int or p.get("width",1) != 1:
                raise ValueError("only explicitly scalar canonical FT ports supported")
        ends = [a[k] for a in arcs for k in ("source","sink")]
        if len(set(ends)) != len(ends) or set(ends) != set(declared):
            raise ValueError("arc endpoints are not one-to-one declared port pairs")
        model = interface["arcs"]
        identity = lambda a:(a["source"],a["sink"],a["kind"])
        if len(model) != len(arcs) or set(map(identity,model)) != set(map(identity,arcs)):
            raise ValueError("interface/declaration arc inventory mismatch")
        for a in arcs+model:
            if (a["kind"] not in ("clock","reset") or a.get("owner","die") != "die"
                or type(a.get("width",1)) is not int or a.get("width",1) != 1):
                raise ValueError("invalid explicit infrastructure role/owner/width")
    except (KeyError,TypeError,ValueError,AttributeError) as e:
        result["errors"].append(str(e)); return result
    actual = {p["name"]:p for p in D.pins}
    accepted = set()
    for a in arcs:
        timed = next(x for x in model if identity(x) == identity(a))
        rec = dict(source=a["source"],sink=a["sink"],role=a["kind"],owner="die",width=1,status="FAIL",
                   timing_status=interface.get("status"),tt_ps=timed.get("tt_ps"),ff_ps=timed.get("ff_ps"))
        try:
            src,dst = actual[a["source"]],actual[a["sink"]]
            if (declared[a["source"]]["direction"] != "INPUT" or declared[a["sink"]]["direction"] != "OUTPUT"
                or src["io"] != "INPUT" or dst["io"] != "OUTPUT"):
                raise ValueError("endpoint direction mismatch")
            start = D.pin_net.get(src["k"])
            if start is None or D.nets[start][1] != ("p",src["k"],False):
                raise ValueError("source is not the actual input driver")
            todo, seen, hits, buffers = [(start,0)], {}, [], set()
            while todo:
                net,parity = todo.pop()
                if net in seen:
                    # A pure single-input BUF/INV network cannot reconverge to
                    # itself without a cycle; never bless an ambiguous graph.
                    raise ValueError("cycle/repeated net in infrastructure cone")
                seen[net] = parity
                sinks = D.nets[net][2]
                if not sinks: raise ValueError("disconnected infrastructure cone")
                for s in sinks:
                    if s[0] == "p":
                        if s[1] != dst["k"]: raise ValueError("extra endpoint fanout")
                        hits.append(parity)
                    elif D.kind(s[1]) == "B":
                        cid = s[1]; inputs = D.cell_in[cid]; outputs = D.drives[cid]
                        if len(inputs) != 1 or len(outputs) != 1:
                            raise ValueError("ambiguous buffer input/output")
                        master = D.cells[cid][1]
                        if not master.startswith(("BUF","INV","HB")):
                            raise ValueError("untyped buffer function")
                        buffers.add(cid)
                        todo.append((outputs[0],parity ^ int(master.startswith("INV"))))
                    else:
                        raise ValueError("ordinary data/sequential/logic fanout")
            if not hits or any(hits): raise ValueError("endpoint is not non-inverting pass-through equivalent")
            rec.update(status="PASS",buffers=len(buffers),nets=len(seen),equivalence="y=x for both binary inputs")
            accepted.update((a["source"],a["sink"]))
        except (KeyError,TypeError,ValueError) as e:
            rec["why"] = str(e)
        result["arcs"].append(rec)
    result["pins"] = sorted(accepted)
    return result


LAND_CONE_DEPTH = 6      # comb cells pin -> landing slot D pin: face_guard land_mux_depth <= 2 plus placement buffers


def _bus_of(name):
    return name.split("[", 1)[0] if re.fullmatch(r"[^\[\]]+(\[\d+\])?", name) else None


def land_ring_captures(D, land, guard):
    """Declared landing ring = registered capture (COORD 2026-10-29 11:09, GEOM-59; config of the pin_reg rule).
    land: kit land_slots.json, guard: kit face_guard.json.  Only with face_guard verdict PASS (it proves on the
    netlist that every bit of a declared slot bus loads exactly D slot-flop D pins through the write mux), and only
    per pin where the CHECKPOINT agrees: the input pin's forward combinational cone (<= LAND_CONE_DEPTH B/L cells)
    reaches exactly D sequential data pins and nothing else (no output pin, macro, clock pin or clock cell), and the
    face_guard-named capture flop of that bit, when it names one, is among them.  The pin is then judged at the
    distance to its FARTHEST slot flop (GEOM-59), so pin_reg_p90/max still judge the placement.  ring_start /
    origin_start inputs and undeclared buses get nothing.  face_guard clock_exports (sdc create_generated_clock
    -divide_by 1 forwarded clock outputs) are returned as kit-declared clock pins.  Missing / invalid metadata grants
    no exemption and is recorded in errors."""
    res = dict(caps={}, clock_exports=[], errors=[], rejected=[], buses=[])
    if not isinstance(land, dict) or not (str(land.get("schema", "")).startswith("land_slots/")
                                         or land.get("schema") == "opentallas.land_slots.v1") \
            or not isinstance(land.get("buses"), dict):
        res["errors"].append("land_slots: want {schema: land_slots/N or opentallas.land_slots.v1, buses: {...}}")
        return res
    if not isinstance(guard, dict) or guard.get("verdict") != "PASS" or not isinstance(guard.get("flops", {}), dict):
        res["errors"].append(f"face_guard verdict {guard.get('verdict') if isinstance(guard, dict) else None} (want PASS)")
        return res
    buses = {}
    for b, v in land["buses"].items():
        d = v.get("D") if isinstance(v, dict) and v.get("form") not in ("ring_start", "origin_start") else v
        if isinstance(d, int) and not isinstance(d, bool) and d >= 2:
            buses[b] = d
        elif not (isinstance(v, dict) and v.get("form") in ("ring_start", "origin_start")):
            res["errors"].append(f"land_slots bus {b}: spec {v} has no D >= 2")
    res["buses"] = sorted(buses)
    named = {k: v.replace("\\", "") for k, v in guard.get("flops", {}).items() if isinstance(v, str)}
    for p in D.pins:
        b = _bus_of(p["name"])
        if p["io"] != "INPUT" or b not in buses:
            continue
        n = D.pin_net.get(p["k"])
        flops, leak, front, seen, depth = set(), None, [n], {n}, 0
        while front and leak is None and n is not None:
            nf = []
            for nn in front:
                for s in D.nets[nn][2]:
                    k = D.kind(s[1]) if s[0] == "i" else "P"
                    if s[0] != "i" or s[2] or k in ("M", "K", None):
                        leak = f"reaches {k or 'unknown'}{' clock pin' if s[0] == 'i' and s[2] else ''}"
                    elif k == "S":
                        flops.add(s[1])
                    elif depth >= LAND_CONE_DEPTH:
                        leak = f"cone deeper than {LAND_CONE_DEPTH} cells"
                    else:
                        for on in D.drives.get(s[1], []):
                            if on not in seen:
                                seen.add(on)
                                nf.append(on)
            front, depth = nf, depth + 1
        names = {D.cells[c][6].replace("\\", "") for c in flops}
        if n is None:
            leak = "no net"
        elif leak is None and len(flops) != buses[b]:
            leak = f"{len(flops)} slot flops (declared D {buses[b]})"
        elif leak is None and p["name"] in named and named[p["name"]] not in names:
            leak = f"face_guard flop {named[p['name']]} not in cone"
        if leak:
            res["rejected"].append(f"{p['name']}: {leak}")
        else:
            res["caps"][p["name"]] = sorted(flops)
    ex = guard.get("clock_exports", {})
    if isinstance(ex, dict):
        outs = {p["name"] for p in D.pins if p["io"] == "OUTPUT"}
        names = {p["name"] for p in D.pins}
        accepted = set()
        for t in ex:
            if t in outs:
                accepted.add(t)
            elif t + "[0]" in outs:
                # A width-one bound RTL port [0:0] becomes BTerm <port>[0].
                # Keep the face_guard clock proof; resolve only a singleton
                # actual bit inventory, never a slice of a wider output bus.
                bits = {n for n in names if re.fullmatch(re.escape(t) + r"\[\d+\]", n)}
                if bits == {t + "[0]"}:
                    accepted.add(t + "[0]")
        res["clock_exports"] = sorted(accepted)
    return res


def pin_reg_metrics(D, strap_re, clock_pins=frozenset(), land=None):
    """pin -> first directional register through pure BUF/INV; visited nets bound cycles, not buffer count.
    land: {input pin: [slot flop ids]} of land_ring_captures (declared ring; judged at the farthest slot)."""
    land = land or {}
    dist, unreg, macro, exempt = [], [], 0, 0
    worst = []
    for p in D.pins:
        if p["sig"] in ("POWER", "GROUND"):
            continue
        if (p["sig"] == "CLOCK" or p["name"] in clock_pins or CLOCK_PIN_RE.search(p["name"])
                or strap_re.search(p["name"])):
            exempt += 1
            continue
        n = D.pin_net.get(p["k"])
        if n is None:
            unreg.append(p["name"] + "(no net)")
            continue
        best, hit_m = INF, False
        if p["io"] == "INPUT" and p["name"] in land:
            best = max(abs(x - p["x"]) + abs(y - p["y"]) for x, y in (ctr(D.cells[c]) for c in land[p["name"]]))
        elif p["io"] == "OUTPUT":
            cur, seen = n, set()
            while cur not in seen:
                seen.add(cur)
                dr = D.nets[cur][1]
                if not dr or dr[0] != "i":
                    break
                k = D.kind(dr[1])
                if k == "S":
                    x, y = ctr(D.cells[dr[1]])
                    best = abs(x - p["x"]) + abs(y - p["y"])
                    break
                if k == "M":
                    hit_m = True
                    break
                if k != "B" or not D.cell_in.get(dr[1]):
                    break
                inputs = [nn for nn, clock in D.cell_in[dr[1]] if not clock]
                if len(inputs) != 1:
                    break
                cur = inputs[0]
        else:
            front, seen = [n], {n}
            while front and best == INF and not hit_m:
                nf = []
                for nn in front:
                    for s in D.nets[nn][2]:
                        if s[0] != "i" or s[2]:
                            continue
                        k = D.kind(s[1])
                        if k == "S":
                            x, y = ctr(D.cells[s[1]])
                            best = min(best, abs(x - p["x"]) + abs(y - p["y"]))
                        elif k == "M":
                            hit_m = True
                        elif k == "B":
                            for on in D.drives.get(s[1], []):
                                if on not in seen:
                                    seen.add(on)
                                    nf.append(on)
                front = nf
        if best < INF:
            dist.append(best)
            worst.append((best, p["name"]))
        elif hit_m:
            macro += 1
        else:
            unreg.append(p["name"])
    worst.sort(reverse=True)
    return dict(pins_registered=len(dist), pins_to_macro=macro, pins_exempt=exempt, pins_unregistered=len(unreg),
                pins_land_ring=sum(1 for p in D.pins if p["io"] == "INPUT" and p["name"] in land),
                unregistered_sample=unreg[:8], pin_reg_p50=None if not dist else round(q(dist, .5), 2),
                pin_reg_p90=None if not dist else round(q(dist, .9), 2),
                pin_reg_max=None if not dist else round(max(dist), 2), pin_reg_worst=[f"{d:.1f} {n}" for d, n in worst[:5]])


def r2r_metrics(D):
    """max Manhattan launch-flop -> capture-flop distance over every combinational path (data + reset pins, clock pins
    excluded), exact: per node keep min/max of u = x + y and v = x - y over the launching flops (Manhattan distance =
    max(|du|, |dv|)), propagated in topological order through the combinational cells."""
    memories=set(); unknown=[]
    for cid,c in D.cells.items():
        if not getattr(D,'memory_reach',False):break
        if c[0]!='M':continue
        model=getattr(D,'memory_models',{}).get(c[1])
        if model is None:unknown.append(c[1]+': missing actual Liberty model');continue
        if model['kind']=='nonmemory':continue
        if model['kind']!='synchronous_memory':unknown.append(c[1]+': '+','.join(model.get('errors',[])));continue
        physical=D.extra.get('macro_ports',{}).get(c[1])
        expected={p:'INPUT' for p in model['captures']+model['clocks']}
        expected.update({p:'OUTPUT' for p in model['launches']})
        if physical!=expected:unknown.append(c[1]+': missing/mismatched actual master port inventory');continue
        memories.add(cid)
    seq={cid for cid,c in D.cells.items() if c[0]=='S'}|memories
    def bounds(cid):
        c=D.cells[cid]
        if cid in memories:return c[2]+c[3],c[4]+c[5],c[2]-c[5],c[4]-c[3]
        x,y=ctr(c);return x+y,x+y,x-y,x-y
    comb = {cid for cid, c in D.cells.items() if c[0] in "BLK"}
    # per comb cell: [umin, umax, vmin, vmax, src_umin, src_umax, src_vmin, src_vmax]
    st = {}
    indeg = Counter()
    succ = defaultdict(list)          # comb cell -> comb cells it feeds (data pins)
    for cid in comb:
        for n in D.drives.get(cid, []):
            for s in D.nets[n][2]:
                if s[0] == "i" and not s[2] and s[1] in comb:
                    succ[cid].append(s[1])
                    indeg[s[1]] += 1

    def merge(dst, u0, u1, v0, v1, a, b, c_, d_):
        e = st.get(dst)
        if e is None:
            st[dst] = [u0, u1, v0, v1, a, b, c_, d_]
            return
        if u0 < e[0]:
            e[0], e[4] = u0, a
        if u1 > e[1]:
            e[1], e[5] = u1, b
        if v0 < e[2]:
            e[2], e[6] = v0, c_
        if v1 > e[3]:
            e[3], e[7] = v1, d_
    caps = defaultdict(list)          # capture flop -> [(umin, umax, vmin, vmax, srcs...)]
    for cid, c in D.cells.items():
        if cid not in seq:
            continue
        u0,u1,v0,v1=bounds(cid)
        for n in D.drives.get(cid, []):
            for s in D.nets[n][2]:
                if s[0] != "i" or s[2]:
                    continue
                k = D.kind(s[1])
                if s[1] in seq:
                    caps[s[1]].append((u0,u1,v0,v1,cid,cid,cid,cid))
                elif s[1] in comb:
                    merge(s[1],u0,u1,v0,v1,cid,cid,cid,cid)
    dq = deque(cid for cid in comb if indeg[cid] == 0)
    done = 0
    while dq:
        cid = dq.popleft()
        done += 1
        e = st.get(cid)
        for n in D.drives.get(cid, []):
            for s in D.nets[n][2]:
                if s[0] != "i" or s[2]:
                    continue
                if e is not None:
                    if s[1] in seq:
                        caps[s[1]].append(tuple(e))
                    elif s[1] in comb:
                        merge(s[1], *e)
        for t in succ.get(cid, []):
            indeg[t] -= 1
            if indeg[t] == 0:
                dq.append(t)
    loops = len(comb) - done
    best, arg, n_gt = 0.0, None, 0
    for cap, lst in caps.items():
        u0,u1,v0,v1=bounds(cap)
        mx, src = 0.0, None
        for e in lst:
            for val, s in ((u1-e[0],e[4]),(e[1]-u0,e[5]),(v1-e[2],e[6]),(e[3]-v0,e[7])):
                if val > mx:
                    mx, src = val, s
        if mx > R2R_MAX:
            n_gt += 1
        if mx > best:
            best, arg = mx, (src, cap)
    name = lambda i: D.cells[i][6] if i in D.cells else str(i)
    return dict(r2r_memory_instances=len(memories),r2r_incomplete_macros=sorted(set(unknown)),r2r_max=round(best, 2), r2r_captures_gt405=n_gt, r2r_captures=len(caps), comb_loop_cells=loops,
                r2r_worst=None if not arg else f"{name(arg[0])} -> {name(arg[1])}")


def clock_metrics(D):
    """clock sinks (seq / macro clock pins) traced up through buffers / clock cells to the input port that roots them.
    Taps = input ports that root clock sinks (or carry sig CLOCK / a clk name); grid taps = clk|ck, clk_t<i>.  Sinks
    per tap: actual tree (CTS checkpoint) or, when every sink still hangs on one root while >= 2 grid taps exist (placed
    checkpoint, before tools/die_plan/clock_taps.tcl), the nearest-tap split that hook applies.  Tree shape (INFO, and
    compared with the template): clock cells, levels root -> sink (max, spread), sinks per leaf driver, clock-net HPWL."""
    sinks = []
    for cid, c in D.cells.items():
        if c[0] not in "SM":
            continue
        for n, is_clk in D.cell_in.get(cid, []):
            if is_clk:
                sinks.append((cid, n))
    memo = {}                                          # net -> (root pin k | None, depth in cells)
    clk_nets, clk_cells = set(), set()

    def trace(n):
        path, cur, r, base = [], n, None, 0
        while len(path) < 64:
            if cur in memo:
                r, base = memo[cur][0], memo[cur][1] + 1
                break
            path.append(cur)
            dr = D.nets[cur][1]
            if dr is None:
                break
            if dr[0] == "p":
                r = dr[1]
                break
            k = D.kind(dr[1])
            ins = D.cell_in.get(dr[1], [])
            if k not in ("B", "K") or not ins:
                break
            clk_cells.add(dr[1])
            ck = [x for x, c in ins if c]
            cur = ck[0] if ck else ins[0][0]
        for i, pnet in enumerate(reversed(path)):
            memo[pnet] = (r, base + i)
            clk_nets.add(pnet)
        return memo[n]
    roots, depth_of = {}, {}
    for cid, n in sinks:
        r, d = trace(n)
        roots[cid] = r
        depth_of[cid] = d
    rooted = {r for r in roots.values() if r is not None}
    taps = {p["k"]: p for p in D.pins if p["io"] == "INPUT" and (p["k"] in rooted or p["sig"] == "CLOCK" or
                                                                 GRID_TAP_RE.match(p["name"]))}
    grid = {k for k, p in taps.items() if GRID_TAP_RE.match(p["name"])}
    cnt = Counter(r for r in roots.values() if r is not None)
    mode = "tree"
    if len(grid) >= 2 and len({r for r in cnt if r in grid}) <= 1 and sum(cnt.values()) > 0:
        mode = "nearest"
        new = Counter({k: 0 for k in grid})
        for cid, r in roots.items():
            if r is None:
                continue
            if r not in grid:
                new[r] += 1
                continue
            x, y = ctr(D.cells[cid])
            new[min(grid, key=lambda k: abs(taps[k]["x"] - x) + abs(taps[k]["y"] - y))] += 1
        cnt = new
    gvals = [cnt.get(k, 0) for k in grid]
    # tree shape
    leaf = Counter()
    for cid, n in sinks:
        dr = D.nets[n][1]
        if dr and dr[0] == "i":
            leaf[dr[1]] += 1
    hp = []
    for n in clk_nets:
        pts = []
        sig, dr, sk = D.nets[n]
        for e in ([dr] if dr else []) + sk:
            if e[0] == "p":
                p = D.pin_by_k.get(e[1])
                if p:
                    pts.append((p["x"], p["y"]))
            elif e[1] in D.cells:
                pts.append(ctr(D.cells[e[1]]))
        if len(pts) >= 2:
            xs, ys = [a for a, _ in pts], [b for _, b in pts]
            hp.append(max(xs) - min(xs) + max(ys) - min(ys))
    depths = [depth_of[c] for c, _ in sinks if roots.get(c) is not None]
    lv = list(leaf.values())
    return dict(taps=len(taps), grid_taps=len(grid), tap_mode=mode, clock_sinks=len(sinks),
                unrooted_sinks=sum(1 for r in roots.values() if r is None),
                grid_tap_sinks_min=min(gvals) if gvals else None, grid_tap_sinks_max=max(gvals) if gvals else None,
                grid_taps_empty=sorted(taps[k]["name"] for k in grid if cnt.get(k, 0) == 0),
                tap_sinks={taps[k]["name"]: cnt.get(k, 0) for k in taps},
                tap_set=sorted([taps[k]["name"], face_of(taps[k]["x"], taps[k]["y"], D.die)] for k in taps),
                clock_cells=len(clk_cells), clock_depth_max=max(depths) if depths else None,
                clock_depth_spread=(max(depths) - min(depths)) if depths else None,
                leaf_sinks_p90=None if not lv else round(q(lv, .9), 1), leaf_sinks_max=max(lv) if lv else None,
                clock_net_hpwl_max=round(max(hp), 2) if hp else None,
                clock_net_hpwl_p90=round(q(hp, .9), 2) if hp else None,
                stage="cts" if clk_cells else "placed")


# ------------------------------------------------------------------------------------------------ GEOM-AUTO-2 metrics
# (OWNER 2026-10-27: AUTO GEOM PASS for all core kits on measured checks.)  Every limit names the review that set it.
FILL_LO = 0.15            # GEOM-AUTO-2 fill band: < 0.15 or > 0.75 flags (owner 10-27 lane brief; METHODOLOGY 1.14 40-60 %)
FILL_HI = 0.75
FILL_MACRO_DOMINATED = 50.0   # macro area % above which low fill is INFO (GEOM-REVIEW-24 pslice_c5 cond (4): 3.7 % at 55 %)
MACRO_LATTICE = 4.32      # GEOM-REVIEW-24 pslice_c5 "stacks on the 4.32 lattice"; ASAP7 16 rows x 80 sites
SITE_X, ROW_Y = 0.054, 0.270
DEMAND_HARD = 1.0         # estimated demand above the derated capacity itself
DEMAND_MAX = 0.6          # METHODOLOGY 5.2 / 12.7b corridor tracks <= 0.6; GEOM-REVIEW-24 pslice cond (1) channel <= 0.6
TRACK_DERATE = 0.75       # GEOM-REVIEW-24/-25 "M3+M5 derated ~36/um", "M2+M4 derated ~35 tracks/um"
CUT_STEP = 5.0
DEMAND_WIN = 10.0
CLK_REACH_MAX = 200.0     # METHODOLOGY 12.8b "longest entry-to-sink distance exceeds ~200 um" -> restructure
CLK_REACH_TOL = 1.10      # "~200": 10 % reading of the approximate limit (220 um) before FAIL
PARTIAL_FACE_PINS = 64    # tile-review-pin-clustering-1017 (bf_cl_fp 1170 pins on partial W/S, pegress ~200 of 302 um)
PARTIAL_FACE_OCC = 0.5
PARTIAL_FACE_DENS = 4.0
GRT_ITER_MIN = 50         # memory hbm-overflow-core-ceiling-1026: judge GRT only at >= 50 iterations


def _layer_idx(name):
    m = re.match(r"^M(\d+)$", name or "")
    return int(m.group(1)) if m else None


def macro_metrics(D):
    """0 std cells on macros; macro origins on the placement grid and the 4.32-um macro lattice"""
    X0, Y0, X1, Y1 = D.die
    macros = [c for c in D.cells.values() if c[0] == "M"]
    out = dict(cells_on_macros=0, cells_on_macros_sample=[], macro_off_grid=0, macro_off_lattice=0,
               macro_lattice_resid_max=None)
    if not macros:
        return out
    B = 20.0
    buck = defaultdict(list)
    for mi, m in enumerate(macros):
        for i in range(int((m[2] - X0) // B), int((m[4] - X0) // B) + 1):
            for j in range(int((m[3] - Y0) // B), int((m[5] - Y0) // B) + 1):
                buck[(i, j)].append(mi)
    bad = []
    for cid, c in D.cells.items():
        if c[0] == "M":
            continue
        x, y = ctr(c)
        for mi in buck.get((int((x - X0) // B), int((y - Y0) // B)), ()):
            m = macros[mi]
            ox = min(c[4], m[4]) - max(c[2], m[2])
            oy = min(c[5], m[5]) - max(c[3], m[3])
            if ox > 0.005 and oy > 0.005:
                bad.append(c[6])
                break
    def res(v, g):
        r = v % g
        return min(r, g - r)
    lat = []
    grid_bad = 0
    cx0, cy0 = (D.extra.get("core") or (X0, Y0))[:2]
    for m in macros:
        dx, dy = m[2] - cx0, m[3] - cy0
        if res(dx, SITE_X) > 0.002 or res(dy, ROW_Y) > 0.002:
            grid_bad += 1
        lat.append(max(res(dx, MACRO_LATTICE), res(dy, MACRO_LATTICE)))
    out.update(cells_on_macros=len(bad), cells_on_macros_sample=bad[:5], macro_off_grid=grid_bad,
               macro_off_lattice=sum(1 for r in lat if r > 0.01), macro_lattice_resid_max=round(max(lat), 4))
    return out


def _net_boxes(D, skip_clock=True):
    """signal-net bounding boxes from cell centres / top pins: [(x0, y0, x1, y1)]"""
    out = []
    for sig, dr, sk in D.nets:
        if skip_clock and sig == "CLOCK":
            continue
        xs, ys, mac = [], [], []
        for e in ([dr] if dr else []) + sk:
            if e[0] == "p":
                p = D.pin_by_k.get(e[1])
                if p:
                    xs.append(p["x"]); ys.append(p["y"])
            elif e[1] in D.cells:
                c = D.cells[e[1]]
                if c[0] == "M":
                    mac.append(c)
                    continue
                x, y = ctr(c)
                xs.append(x); ys.append(y)
        if mac:
            # macro pins sit on the macro boundary: project onto the edge nearest the net's other points
            gx = sum(xs) / len(xs) if xs else None
            gy = sum(ys) / len(ys) if ys else None
            for c in mac:
                if gx is None:
                    gx, gy = ctr(c)
                px, py = min(max(gx, c[2]), c[4]), min(max(gy, c[3]), c[5])
                if c[2] < px < c[4] and c[3] < py < c[5]:
                    dl, dr_, db, dt = px - c[2], c[4] - px, py - c[3], c[5] - py
                    k = min(dl, dr_, db, dt)
                    px = c[2] if k == dl else c[4] if k == dr_ else px
                    py = c[3] if k == db else c[5] if k == dt else py
                xs.append(px); ys.append(py)
        if len(xs) >= 2:
            out.append((min(xs), min(ys), max(xs), max(ys)))
    return out


def demand_metrics(D, max_layer="M5", min_layer="M2"):
    """macro-aware cut demand (GEOM-REVIEW-24 ep/pslice method, generalised): on cut lines every CUT_STEP um, every
    signal net whose bounding box straddles the cut crosses it at least once; that crossing is spread over the net's
    span in proportion to the routing capacity there (tracks/um of the layers of that direction in [min, max] layer that
    the local macro master does not obstruct, x TRACK_DERATE).  Utilisation of a window = crossings / capacity.
      channel_*: windows on cuts that pass macros, outside macros (inter-macro channels, edge strips)
      col_v:     per-column vertical demand: every DEMAND_WIN-wide column on every horizontal cut
      detour_*:  net-cut crossings with no capacity inside the net's span, moved to the nearest free tracks (INFO)
      blocked_*: crossings on a cut line with zero capacity everywhere (no legal crossing at all)"""
    import numpy as np
    X0, Y0, X1, Y1 = D.die
    tech = D.extra.get("tech") or {}
    mobs = D.extra.get("mobs") or {}
    lo, hi = _layer_idx(min_layer) or 2, _layer_idx(max_layer) or 5
    lay = {d: [(n, p) for n, (dd, p) in tech.items() if dd.upper().startswith(d) and lo <= (_layer_idx(n) or 0) <= hi]
           for d in ("V", "H")}
    if not tech or not lay["V"] or not lay["H"]:
        return dict(demand_note="no tech layers in dump")
    macros = [c for c in D.cells.values() if c[0] == "M"]
    boxes = _net_boxes(D)
    if not boxes:
        return dict(demand_note="no signal nets")
    bx = np.array(boxes)
    res = {}
    step = 1.0
    for d in ("V", "H"):     # V: vertical tracks crossing horizontal cuts y = c (spread along x)
        layers = lay[d]
        full = sum(TRACK_DERATE / p for _, p in layers)
        a0, a1 = (X0, X1) if d == "V" else (Y0, Y1)
        b0, b1 = (Y0, Y1) if d == "V" else (X0, X1)
        nb = max(1, int(math.ceil((a1 - a0) / step)))
        lo_a, hi_a = (bx[:, 0], bx[:, 2]) if d == "V" else (bx[:, 1], bx[:, 3])
        lo_b, hi_b = (bx[:, 1], bx[:, 3]) if d == "V" else (bx[:, 0], bx[:, 2])
        ia0 = np.clip(((lo_a - a0) / step).astype(int), 0, nb - 1)
        ia1 = np.clip(((hi_a - a0) / step).astype(int), 0, nb - 1)
        win = max(1, int(round(DEMAND_WIN / step)))
        col_best, ch_best, blocked, detour = (0.0, None), (0.0, None), 0, 0
        for c in np.arange(b0 + CUT_STEP / 2, b1, CUT_STEP):
            cap = np.full(nb, full * step)
            inm = np.zeros(nb, bool)
            for m in macros:
                mb0, mb1, ma0, ma1 = (m[3], m[5], m[2], m[4]) if d == "V" else (m[2], m[4], m[3], m[5])
                if not (mb0 < c < mb1):
                    continue
                ob = mobs.get(m[1], set())
                keep = sum(TRACK_DERATE / p for n, p in layers if n not in ob) if ob else 0.0
                j0, j1 = int(max(0, (ma0 - a0) / step)), int(min(nb, math.ceil((ma1 - a0) / step)))
                cap[j0:j1] = np.minimum(cap[j0:j1], keep * step)
                inm[j0:j1] = True
            sel = (lo_b < c) & (hi_b > c)
            if not sel.any():
                continue
            cs = np.concatenate([[0.0], np.cumsum(cap)])
            s0, s1 = ia0[sel], ia1[sel]
            T = cs[s1 + 1] - cs[s0]
            z = T <= 1e-9
            if z.any():
                # no capacity inside the net's span (e.g. W band <-> E face across an SRAM column under an M5
                # ceiling): the route detours to the nearest free track on either side; that detour demand lands there
                fr = cap > 1e-12
                idx = np.arange(nb)
                prv = np.maximum.accumulate(np.where(fr, idx, -1))
                nxt = np.minimum.accumulate(np.where(fr, idx, nb)[::-1])[::-1]
                p0, p1 = prv[s0[z]], nxt[s1[z]]
                s0 = s0.copy(); s1 = s1.copy()
                s0[z] = np.where(p0 >= 0, p0, s0[z])
                s1[z] = np.where(p1 < nb, p1, s1[z])
                detour += int(z.sum())
                T = cs[s1 + 1] - cs[s0]
                z = T <= 1e-9
            blocked += int(z.sum())
            w = np.where(z, 0.0, 1.0 / np.maximum(T, 1e-9))
            diff = np.zeros(nb + 1)
            np.add.at(diff, s0, w)
            np.add.at(diff, s1 + 1, -w)
            u = np.cumsum(diff)[:nb] * cap        # crossings per bin
            # windows: fixed columns for the column metric; free runs (channels) on cuts that pass macros
            if d == "V":
                cu = np.concatenate([[0.0], np.cumsum(u)])
                for j in range(0, nb, win):
                    k = min(nb, j + win)
                    cc = cs[k] - cs[j]
                    if cc > 0:
                        r = (cu[k] - cu[j]) / cc
                        if r > col_best[0]:
                            col_best = (float(r), (round(a0 + j * step, 1), round(float(c), 1)))
            if inm.any():
                j = 0
                cu = np.concatenate([[0.0], np.cumsum(u)])
                while j < nb:
                    if inm[j]:
                        j += 1
                        continue
                    k = j
                    while k < nb and not inm[k]:
                        k += 1
                    # split a long free run into DEMAND_WIN windows; a narrow channel is one window
                    for jj in range(j, k, max(win, 1)):
                        kk = min(k, jj + win)
                        cc = cs[kk] - cs[jj]
                        if cc > 0:
                            r = (cu[kk] - cu[jj]) / cc
                            if r > ch_best[0]:
                                ch_best = (float(r), (round(a0 + jj * step, 1), round(a0 + kk * step, 1), round(float(c), 1)))
                    j = k
                # macro spans: demand that the spread put over a (partially) open macro
                j = 0
                while j < nb:
                    if not inm[j]:
                        j += 1
                        continue
                    k = j
                    while k < nb and inm[k]:
                        k += 1
                    cc = cs[k] - cs[j]
                    if cc > 0:
                        r = (cu[k] - cu[j]) / cc
                        if r > ch_best[0]:
                            ch_best = (float(r), (round(a0 + j * step, 1), round(a0 + k * step, 1), round(float(c), 1)))
                    j = k
        key = "v" if d == "V" else "h"
        res[f"channel_{key}_max"] = round(ch_best[0], 3) if ch_best[1] else None
        res[f"channel_{key}_at"] = ch_best[1]
        res[f"blocked_{key}"] = blocked
        res[f"detour_{key}"] = detour
        if d == "V":
            res["col_v_max"] = round(col_best[0], 3)
            res["col_v_at"] = col_best[1]
        res[f"tracks_{key}_per_um"] = round(full, 2)
    res["demand_layers"] = f"{min_layer}-{max_layer}"
    return res


def clock_entry_metrics(D, ck):
    """clock entry: the input port rooting the most sinks; inside a macro outline -> FAIL (GEOM-REVIEW-24
    vm_calendar_f20 'clock entry island ON the SRAM').  Reach = max over clocked flops of the Manhattan distance to the
    nearest entry point (the port, plus pre-placed FIRM/LOCKED clock cells = in-core islands, METHODOLOGY 12.8b).
    That nearest point need not be the sink's own driver, so two INFO measures are added (GEOM-REVIEW-46 10-28, node
    a0k3: reach 13.66 while 79 sinks sit >100 um from their own leaf): clock_leaf_reach_max = max sink distance to the
    cell / port that drives its clock pin, and clock_entry_sink_max = max distance from the root port to a sink."""
    ts = ck.get("tap_sinks") or {}
    if not ts or not any(ts.values()):
        return dict(clock_entry=None)
    root = max(ts, key=lambda k: ts[k])
    roots = [x for x in D.pins if ts.get(x["name"], 0) > 0]
    p = next((x for x in roots if x["name"] == root), None)
    if p is None:
        return dict(clock_entry=None)
    # every clock root port with sinks: an entry inside a macro outline fails (vm_calendar_f20 'clk' at the SRAM)
    on_macro = [f"{x['name']}@{c[6]}" for x in roots for c in D.cells.values()
                if c[0] == "M" and c[2] < x["x"] < c[4] and c[3] < x["y"] < c[5]]
    pts = [(x["x"], x["y"]) for x in roots if ts.get(x["name"], 0) >= 0.05 * ts[root]]
    st = D.extra.get("status") or {}
    clk_fixed = 0
    for cid, s in st.items():
        c = D.cells.get(cid)
        if c and c[0] in "KB" and s in ("FIRM", "LOCKED", "COVER") and any(
                D.nets[n][0] == "CLOCK" or ck_net(D, n) for n in D.drives.get(cid, [])):
            pts.append(ctr(c))
            clk_fixed += 1
    sinks, leaf, ent = [], (0.0, None, None), (0.0, None)
    for cid, c in D.cells.items():
        cn = [n for n, isc in D.cell_in.get(cid, []) if isc]
        if c[0] == "S" and cn:
            sx, sy = ctr(c)
            sinks.append((sx, sy))
            dd = abs(sx - p["x"]) + abs(sy - p["y"])
            if dd > ent[0]:
                ent = (dd, (round(sx, 1), round(sy, 1)))
            dr = D.nets[cn[0]][1]
            if dr is None:
                continue
            if dr[0] == "i":
                dc = D.cells.get(dr[1])
                if dc is None:
                    continue
                dxy = ctr(dc)
            else:
                pp = D.pin_by_k.get(dr[1])
                if pp is None:
                    continue
                dxy = (pp["x"], pp["y"])
            dd = abs(sx - dxy[0]) + abs(sy - dxy[1])
            if dd > leaf[0]:
                leaf = (dd, (round(sx, 1), round(sy, 1)), (round(dxy[0], 1), round(dxy[1], 1)))
    reach, far = 0.0, None
    if sinks:
        import numpy as np
        S = np.array(sinks)
        E = np.array(pts)
        best = np.full(len(S), np.inf)
        for i in range(0, len(E), 256):
            e = E[i:i + 256]
            dd = np.abs(S[:, None, 0] - e[None, :, 0]) + np.abs(S[:, None, 1] - e[None, :, 1])
            best = np.minimum(best, dd.min(axis=1))
        k = int(best.argmax())
        reach, far = float(best[k]), (round(float(S[k][0]), 1), round(float(S[k][1]), 1))
    return dict(clock_entry=root, clock_entry_xy=[round(p["x"], 3), round(p["y"], 3)], clock_entry_on_macro=len(on_macro),
                clock_entry_macro=on_macro[:2], clock_islands_fixed=clk_fixed, clock_reach_max=round(reach, 2),
                clock_reach_far=far, clock_leaf_reach_max=round(leaf[0], 2), clock_leaf_reach_far=leaf[1],
                clock_leaf_reach_driver=leaf[2], clock_entry_sink_max=round(ent[0], 2), clock_entry_sink_far=ent[1])


def ck_net(D, n):
    """net n reaches a clock pin of a seq/macro (one level)"""
    return any(s[0] == "i" and s[2] for s in D.nets[n][2])


def relay_metrics(D):
    """pass-through flops (single data input fed through <= PINREG_DEPTH buffers by one flop) form relay chains.
    A chain is COLLAPSED when its stages are stacked: a hop > 405 um inside the chain while the stages are within
    reach of each other elsewhere (memory gpl-collapses-relay-chains-1022: 1-level mm-long relay paths = GPL stacked
    the stages).  balance = longest hop / (chain span / hops)."""
    src = {}
    for cid, c in D.cells.items():
        if c[0] != "S":
            continue
        ins = [n for n, isc in D.cell_in.get(cid, []) if not isc]
        if len(ins) != 1:
            continue
        cur, depth, prev = ins[0], 0, None
        while depth <= PINREG_DEPTH:
            dr = D.nets[cur][1]
            if not dr or dr[0] != "i":
                break
            k = D.kind(dr[1])
            if k == "S":
                prev = dr[1]
                break
            if k != "B" or not D.cell_in.get(dr[1]):
                break
            cur = D.cell_in[dr[1]][0][0]
            depth += 1
        if prev is not None and prev != cid:
            src[cid] = prev
    if not src:
        return dict(relay_chains=0, relay_collapsed=0, relay_balance_max=None, relay_worst=None)
    has_succ = set(src.values())
    heads = [c for c in src if c not in has_succ]     # chain ends
    n_ch, collapsed, bal_max, worst = 0, 0, 0.0, None
    for t in heads:
        chain, cur, seen = [t], t, {t}
        while cur in src and src[cur] not in seen and len(chain) < 4096:
            cur = src[cur]
            chain.append(cur)
            seen.add(cur)
        if len(chain) < 3:
            continue
        n_ch += 1
        pts = [ctr(D.cells[c]) for c in chain]
        hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
        span = abs(pts[0][0] - pts[-1][0]) + abs(pts[0][1] - pts[-1][1])
        mh = max(hops)
        if mh > R2R_MAX:
            collapsed += 1
        if span > R2R_MAX:
            bal = mh / (span / len(hops))
            if bal > bal_max:
                bal_max, worst = bal, f"{D.cells[chain[-1]][6]} -> {D.cells[chain[0]][6]} {len(hops)} hops span {span:.0f} max hop {mh:.0f}"
    return dict(relay_chains=n_ch, relay_collapsed=collapsed, relay_balance_max=round(bal_max, 2) if worst else None,
                relay_worst=worst)


def partial_face_metrics(D, pm):
    """a face with >= PARTIAL_FACE_PINS pins whose pins occupy < PARTIAL_FACE_OCC of the face's 10-um windows while
    those windows average >= PARTIAL_FACE_DENS pins/um (tile-review-pin-clustering-1017)"""
    X0, Y0, X1, Y1 = D.die
    flen = {"N": X1 - X0, "S": X1 - X0, "E": Y1 - Y0, "W": Y1 - Y0}
    pos = defaultdict(list)
    for p in D.pins:
        if p["sig"] in ("POWER", "GROUND"):
            continue
        f = face_of(p["x"], p["y"], D.die)
        if f != "area":
            pos[f].append(p["x"] - X0 if f in "NS" else p["y"] - Y0)
    worst, bad = None, []
    for f, v in pos.items():
        nw = max(1, int(math.ceil(flen[f] / 10.0)))
        occ = len({min(nw - 1, int(x // 10.0)) for x in v})
        frac = occ / nw
        dens = len(v) / (occ * 10.0)
        if worst is None or frac < worst[1]:
            worst = (f, round(frac, 3), round(dens, 2), len(v))
        if len(v) >= PARTIAL_FACE_PINS and frac < PARTIAL_FACE_OCC and dens >= PARTIAL_FACE_DENS:
            bad.append(f"{f}:{len(v)} pins on {frac:.0%} of face at {dens:.1f}/um")
    return dict(partial_faces=len(bad), partial_face_detail=bad, partial_face_worst=worst)


def grt_metrics(path):
    """final congestion report of geom_grt.tcl (or an equivalent >= 50-iteration probe log)"""
    if not path:
        return dict(grt_overflow=None, grt_note="GRT not run")
    try:
        txt = open(path, errors="replace").read()
    except OSError:
        return dict(grt_overflow=None, grt_note=f"no GRT log {path}")
    its = [int(x) for x in re.findall(r"Start extra iteration (\d+)/", txt)]
    m = re.findall(r"Final congestion report:(.*?)Total\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", txt, re.S)
    per = {}
    if m:
        for ln in m[-1][0].splitlines():
            mm = re.match(r"^(M\d+)\s+\d+\s+\d+\s+([\d.]+)%\s+\d+\s*/\s*\d+\s*/\s*(\d+)", ln.strip())
            if mm:
                per[mm.group(1)] = [float(mm.group(2)), int(mm.group(3))]
    if not m:
        why = "GRT did not finish" if "OT_GRT_DONE" not in txt else "no congestion report"
        return dict(grt_overflow=None, grt_note=why, grt_iterations=max(its) if its else 0)
    ov = int(m[-1][3])
    return dict(grt_overflow=ov, grt_iterations=max(its) if its else 0, grt_layers=per,
                grt_note=("converged" if ov == 0 else "overflow"))


# ------------------------------------------------------------------------------------------------ rules
TOL_REL = 0.02            # replica vs template: numerical noise of a re-place of identical inputs (not a design margin)
TOL_CLOCK = 0.10          # clock-tree shape vs the template's tree (CTS is less repeatable than placement)


def pin_window_excess(m):
    """[(face/layer, peak, axis, lo, hi)] for every layer-face whose peak 10-um window exceeds PIN_WIN_MAX, worst first"""
    win = m.get("pin_peak_layer_win") or {}
    out = [(k, v) + tuple(win.get(k) or ("?", None, None)) for k, v in (m.get("pin_peak_layer") or {}).items()
           if v > PIN_WIN_MAX]
    return sorted(out, key=lambda e: (-e[1], e[0]))


def pin_density_rule(m, add):
    src = "METHODOLOGY 5.2 per layer+face BUDGET (COORD 10-27 10:48); route (pin-access DRC / GRT0) decides"
    ex = pin_window_excess(m)
    if m.get("pin_peak_layer") is None:
        add("pin_density", "NA", None, f"<={PIN_WIN_MAX}", src, "not measurable")
    elif ex:
        add("pin_density", "WARN", m.get("pin_peak_layer_max"), f"<={PIN_WIN_MAX} budget", src,
            "; ".join(f"{k} {v}/um at {a} {lo}-{hi}" for k, v, a, lo, hi in ex))
    else:
        add("pin_density", "PASS", m.get("pin_peak_layer_max"), f"<={PIN_WIN_MAX}", src,
            f"per layer {m.get('pin_peak_layer')}")


def judge(m, template=None, outline=None, all_kits=False):
    """[rule dicts], verdict.  Absolute limit first; with a template (the visually passed part), a value outside the
    absolute limit still passes ONLY when the template carried the same violation through its visual PASS and the
    replica is not worse than the template (TOL_REL) -- the layout_review.py principle that a GEOM-REVIEW PASS for the
    reviewed content excuses low fill / far pin registers, narrowed to 'no worse than what the reviewer saw'."""
    R = []
    t = template["metrics"] if template else None
    if all_kits and template:
        raise ValueError("all-kits uses absolute measured limits, never template exceptions")

    def add(rule, status, value, limit, src, detail=""):
        R.append(dict(rule=rule, status=status, value=value, limit=limit, source=src, detail=detail))

    def lim(rule, key, limit, src, higher_bad=True, detail="", absent_ok=False):
        v = m.get(key)
        if v is None:
            add(rule, "INFO" if absent_ok else "NA", v, limit, src, detail or "not measurable")
            return
        ok = v <= limit if higher_bad else v >= limit
        if ok:
            add(rule, "PASS", v, f"{'<=' if higher_bad else '>='}{limit}", src, detail)
            return
        tv = t.get(key) if t else None
        if tv is not None and not (tv <= limit if higher_bad else tv >= limit):
            worse = v > tv * (1 + TOL_REL) + 1e-6 if higher_bad else v < tv * (1 - TOL_REL) - 1e-6
            if not worse:
                add(rule, "PASS", v, f"template {tv} (visually passed with it)", src, "template-accepted; " + detail)
                return
            detail = f"worse than template {tv}; " + detail
        add(rule, "FAIL", v, f"{'<=' if higher_bad else '>='}{limit}", src, detail)
    if m.get("stage") not in ("placed", "cts"):
        add("checkpoint", "NA", m.get("stage"), "3_place or 4_cts", "AUTO-GEOM scope (pre-route review points only)")
    W, H = m["outline"]
    slot = outline or (t["outline"] if t else None)
    if slot:
        ok = abs(W - slot[0]) <= OUTLINE_TOL and abs(H - slot[1]) <= OUTLINE_TOL
        add("outline", "PASS" if ok else "FAIL", f"{W}x{H}", f"=={slot[0]}x{slot[1]}",
            "METHODOLOGY 1.14; tile-outline-from-parent-slot-1023")
    else:
        add("outline", "NA", f"{W}x{H}", "slot", "METHODOLOGY 1.14", "no parent slot / template outline given")
    lim("aspect", "aspect", ASPECT_MAX, "METHODOLOGY 1.14 aspect <= ~2:1")
    fsrc = "GEOM-AUTO-2 band <0.15 / >0.75 (owner 10-27); METHODOLOGY 1.14 target 40-60 %"
    if m.get("fill_of_free") is not None and m["fill_of_free"] < FILL_LO and m.get("macro_area_pct", 0) >= FILL_MACRO_DOMINATED:
        add("fill", "INFO", m["fill_of_free"], f">={FILL_LO}", fsrc,
            f"macro-dominated ({m['macro_area_pct']} % macro area; GEOM-REVIEW-24 pslice_c5 cond (4))")
    else:
        lim("fill", "fill_of_free", FILL_LO, fsrc, higher_bad=False)
    lim("fill_hi", "fill_of_free", FILL_HI, fsrc)
    if (m.get("empty_area") or 0) > EMPTY_MAX and m.get("macro_area_pct", 0) >= FILL_MACRO_DOMINATED:
        add("empty", "INFO", m["empty_area"], f"<={EMPTY_MAX}", "layout_review.py EMPTY_FLAG (bins < 5 %)",
            f"macro-dominated ({m['macro_area_pct']} % macro area), judged by fill/channel demand")
    else:
        lim("empty", "empty_area", EMPTY_MAX, "layout_review.py EMPTY_FLAG (bins < 5 %)")
    lim("pin_reg_p90", "pin_reg_p90", PINREG_P90, "METHODOLOGY 1.9 (R2 p90 <= 30)", detail=", ".join(m["pin_reg_worst"][:2]))
    lim("pin_reg_max", "pin_reg_max", PINREG_HARD, "layout_review.py PIN_REG_P90_FAIL 150 (backstop)")
    lim("pin_unreg", "pins_unregistered", 0, "METHODOLOGY 1.9 register every partition pin",
        detail=", ".join(m["unregistered_sample"][:4]))
    if m.get("r2r_incomplete_macros"):
        add("r2r","NA",None,f"<={R2R_MAX}","METHODOLOGY 1.3/4.2 complete sequential reach",'; '.join(m['r2r_incomplete_macros'][:4]))
    elif m["r2r_captures"]:
        lim("r2r", "r2r_max", R2R_MAX, "METHODOLOGY 1.3/4.2 reach 405",
            detail=f"{m['r2r_captures_gt405']} captures > 405; worst {m['r2r_worst']}")
        lim("r2r_count", "r2r_captures_gt405", 0, "METHODOLOGY 1.3 (count of captures > 405 um)")
    else:
        add("r2r", "NA", None, f"<={R2R_MAX}", "METHODOLOGY 1.3", "no register-to-register path found")
    pk = m["pin_peak_per_um_10um"]
    m["_pin_peak"] = max(pk.values()) if pk else 0.0
    if t is not None and "_pin_peak" not in t:
        tp = t.get("pin_peak_per_um_10um") or {}
        t["_pin_peak"] = max(tp.values()) if tp else 0.0
    # METHODOLOGY 5.2 "<= 6 pins/um per 10-um window" (per layer and per face) is a BUDGET (COORD 10-27 10:48 GEOM-AUTO-2
    # ruling, 10:4x PIN-DENSITY): an excess is a WARN naming layer, face, peak and window; the measured route (pin-access
    # DRC / GRT0 at >= 50 it, already a required rule) decides.  The combined-face reading stays INFO.
    pin_density_rule(m, add)
    if m["_pin_peak"] > PIN_WIN_MAX and m.get("pin_peak_layer_max", 0) <= PIN_WIN_MAX:
        add("pin_density_face", "INFO", m["_pin_peak"], f"<={PIN_WIN_MAX} combined (OWNER scope open)",
            "METHODOLOGY 5.2 combined-face reading", str(pk))
    if m["macros"]:
        lim("std_band", "band_share", BAND_MIN, "tile-review-pin-clustering-1017 (one contiguous std-cell band)",
            higher_bad=False)
    if m["macros"]:
        lim("cells_on_macros", "cells_on_macros", 0, "GEOM-REVIEW-24 pslice_c5 cond (2) 0 std cells on macros",
            detail=", ".join(m.get("cells_on_macros_sample") or [])[:160])
        # METHODOLOGY 5.6 names no lattice pitch; visually passed parts (pslice_c5: y pitch 41.31) are off any common
        # lattice, and a wrong lattice diagnosis must not override measured facts (tile-review-pin-clustering-1017).
        add("macro_lattice", "INFO", f"{m.get('macro_off_grid')} off site/row grid, {m.get('macro_off_lattice')} off "
            f"{MACRO_LATTICE}", "reported", "METHODOLOGY 5.6 (no pitch defined)",
            f"max {MACRO_LATTICE} residual {m.get('macro_lattice_resid_max')}")
    lim("partial_face", "partial_faces", 0, "tile-review-pin-clustering-1017 (pins on partial faces)",
        detail="; ".join(m.get("partial_face_detail") or []))
    if m.get("relay_chains"):
        lim("relay_collapse", "relay_collapsed", 0, "gpl-collapses-relay-chains-1022 (stacked relay stages)",
            detail=str(m.get("relay_worst")))
    dsrc = "METHODOLOGY 5.2/12.7b tracks <= 0.6; GEOM-REVIEW-24 ep/pslice channel demand"
    if m.get("demand_layers"):
        # The cut estimate is a pre-route model: > 1.0 (demand above the derated capacity) FAILs; above the 0.6 plan
        # budget it is a WARN when the >= 50-iteration GRT measured 0 overflow (measured facts are not overridden by a
        # model, tile-review-pin-clustering-1017), and a FAIL when GRT is missing or overflowed.
        grt_ok = m.get("grt_overflow") == 0
        for key, nm, src in (("channel_h_max", "channel_h", dsrc), ("channel_v_max", "channel_v", dsrc),
                             ("col_v_max", "col_v", "per-column vertical demand; GEOM-REVIEW-24 hub_Ei spine")):
            v = m.get(key)
            if v is None:
                continue
            at = f"at {m.get(key.replace('_max', '_at'))} ({m['demand_layers']}, est.)"
            if v <= DEMAND_MAX:
                add(nm, "PASS", v, f"<={DEMAND_MAX}", src, at)
            elif v <= DEMAND_HARD and grt_ok:
                add(nm, "WARN", v, f"<={DEMAND_MAX} plan budget", src, at + "; GRT 0 overflow")
            else:
                add(nm, "FAIL", v, f"<={DEMAND_MAX} (hard {DEMAND_HARD}, GRT {m.get('grt_overflow')})", src, at)
        for key in ("blocked_h", "blocked_v"):
            lim(key, key, 0, "GEOM-REVIEW-24 ep: nets with no legal crossing (capacity 0 under the layer ceiling)")
        add("detour", "INFO", f"h {m.get('detour_h')} v {m.get('detour_v')}", "info",
            "net-cut crossings detoured around macros (counted into channel demand)")
    else:
        add("demand", "NA", None, f"<={DEMAND_MAX}", dsrc, m.get("demand_note", "not measured"))
    if m.get("clock_entry"):
        lim("clock_on_macro", "clock_entry_on_macro", 0, "GEOM-REVIEW-24 vm_calendar_f20 (entry ON the SRAM)",
            detail=f"{m['clock_entry']} at {m['clock_entry_xy']} {m.get('clock_entry_macro')}")
        lim("clock_reach", "clock_reach_max", round(CLK_REACH_MAX * CLK_REACH_TOL, 1),
            "METHODOLOGY 12.8b entry-to-sink ~<=200 um (sink to NEAREST entry: port or pre-placed clock cell)",
            detail=f"sink farthest from its nearest entry {m.get('clock_reach_far')}, "
            f"{m.get('clock_islands_fixed')} pre-placed clock cells")
        if m.get("clock_leaf_reach_max") is not None:
            add("clock_leaf_reach", "INFO", m["clock_leaf_reach_max"], "info",
                "sink to its OWN clock driver (leaf cell or port), GEOM-REVIEW-46",
                f"sink {m.get('clock_leaf_reach_far')} driver {m.get('clock_leaf_reach_driver')}")
            add("clock_entry_sink", "INFO", m.get("clock_entry_sink_max"), "info",
                "root port to farthest clock sink", f"sink {m.get('clock_entry_sink_far')}")
    else:
        add("clock_entry", "NA", None, "clock root port", "METHODOLOGY 12.8a", "no clock entry found")
    if m.get("grt_overflow") is None:
        add("grt", "NA", None, "0 overflow", "OWNER 10-26 GRT0 at >= 50 iterations", m.get("grt_note", ""))
    else:
        lim("grt", "grt_overflow", 0, "OWNER 10-26 GRT0 at >= 50 iterations (hbm-overflow-core-ceiling-1026)",
            detail=f"{m.get('grt_iterations')} it, {m.get('grt_layers')}")
    if m["grid_taps"] >= 2:
        m["_empty_taps"] = len(m["grid_taps_empty"])
        if t is not None:
            t["_empty_taps"] = len(t.get("grid_taps_empty") or [])
        lim("clock_tap_empty", "_empty_taps", 0, "METHODOLOGY 3.3 (no empty taps); GEOM-REVIEW g3k5 / hub_Ei vC",
            detail=",".join(m["grid_taps_empty"][:6]))
        lim("clock_tap_sinks", "grid_tap_sinks_max", TAP_SINKS_MAX, "METHODOLOGY 3.3 (~1000-1500 sinks/tap); g3k5 3007",
            detail=f"{m['grid_taps']} taps {m['grid_tap_sinks_min']}..{m['grid_tap_sinks_max']} ({m['tap_mode']})")
    else:
        add("clock_taps", "INFO", f"{m['grid_taps']} grid taps, {m['clock_sinks']} sinks", "n/a (< 2 grid taps)",
            "METHODOLOGY 3.3")
    if m["unrooted_sinks"]:
        lim("clock_unrooted", "unrooted_sinks", 0, "METHODOLOGY 6.3 (no unclocked registers)")
    if t is not None:
        add("pin_table", "PASS" if _close_table(m["pin_table"], t["pin_table"]) else "FAIL", len(m["pin_table"]),
            f"== template ({len(t['pin_table'])})", "owner 10-25 template rule; METHODOLOGY 1.5",
            _table_diff(m["pin_table"], t["pin_table"]))
        add("macros", "PASS" if _close_macros(m["macro_list"], t["macro_list"]) else "FAIL", m["macros"],
            f"== template ({t['macros']})", "tile-review-pin-clustering-1017; METHODOLOGY 5.6")
        add("tap_set", "PASS" if m["tap_set"] == t["tap_set"] else "FAIL", m["taps"], f"== template ({t['taps']})",
            "owner 10-25 template rule")
        add("stage", "PASS" if m.get("stage") == t.get("stage") else "FAIL", m.get("stage"), f"== template ({t.get('stage')})",
            "a CTS checkpoint is compared with a reviewed CTS checkpoint (GEOM-REVIEW post-CTS reviews)")
        if m.get("stage") == "cts" and t.get("stage") == "cts":
            for key in ("clock_depth_max", "clock_depth_spread", "leaf_sinks_max", "leaf_sinks_p90", "clock_net_hpwl_max",
                        "clock_net_hpwl_p90", "clock_cells"):
                v, tv = m.get(key), t.get(key)
                if v is None or tv is None:
                    add("clk_" + key, "NA", v, f"template {tv}", "GEOM-REVIEW post-CTS reviews (tree shape)")
                    continue
                ok = v <= tv * (1 + TOL_CLOCK) + 1 if key != "clock_cells" else abs(v - tv) <= tv * TOL_CLOCK + 1
                add("clk_" + key, "PASS" if ok else "FAIL", v, f"template {tv} +{int(TOL_CLOCK * 100)}%",
                    "GEOM-REVIEW E5-CTS01 / ASTK3 FAIL (tap loads, trunk legs, branch length)")
    elif all_kits:
        # Template equality is a replica rule, not a requirement to invent a template for a new
        # kit.  Registration/density, macro-band continuity and root reach are measured above.
        add("interface", "INFO", len(m["pin_table"]), "kit pin contract", "OWNER 2026-10-27 08:02",
            "new kit: parent interface checks stay in shared preflight; no replica equality asserted")
        lim("comb_loops", "comb_loop_cells", 0, "complete r2r reach census (acyclic combinational graph)")
        lim("clock_rooted", "unrooted_sinks", 0, "all sequential sinks trace to a clock input")
        lim("clock_sinks", "clock_sinks", 1, "measured clock topology required", higher_bad=False)
        if not m["pin_table"]:
            add("pins", "NA", 0, ">0", "measured pin registration required")
    else:
        for r in ("pin_table", "macros", "tap_set", "stage"):
            add(r, "NA", "", "template", "owner 10-25 template rule", "no template metrics")
    req_fail = [r for r in R if r["status"] in ("FAIL", "NA")]
    return R, ("FAIL" if req_fail else "PASS")


def reasons(rules):
    """short FAIL / NA reason list for the GEOM REQ line"""
    return [f"{r['rule']} {r['value'] if not isinstance(r['value'], dict) else ''} vs {r['limit']}".strip()
            for r in rules if r["status"] in ("FAIL", "NA")]


def _close_table(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x[:3] != y[:3] or abs(x[3] - y[3]) > POS_TOL or abs(x[4] - y[4]) > POS_TOL:
            return False
    return True


def _table_diff(a, b):
    na, nb = {x[0]: x for x in a}, {x[0]: x for x in b}
    only_a, only_b = sorted(set(na) - set(nb)), sorted(set(nb) - set(na))
    moved = [n for n in set(na) & set(nb) if na[n][1:3] != nb[n][1:3] or abs(na[n][3] - nb[n][3]) > POS_TOL
             or abs(na[n][4] - nb[n][4]) > POS_TOL]
    if not (only_a or only_b or moved):
        return ""
    return f"extra {only_a[:3]} missing {only_b[:3]} moved {sorted(moved)[:3]} ({len(only_a)}/{len(only_b)}/{len(moved)})"


def _close_macros(a, b):
    if len(a) != len(b):
        return False
    return all(x[0] == y[0] and abs(x[1] - y[1]) <= OUTLINE_TOL and abs(x[2] - y[2]) <= OUTLINE_TOL for x, y in zip(a, b))


def stage_of_odb(name):
    """checkpoint stage from the ORFS file name: AUTO-GEOM judges only the pre-route review points (3_place / 4_cts);
    GRT / routed checkpoints carry timing verdicts (GEOM-REVIEW 13:52 elemB_if2e 5_1_grt FAIL on clock timing)"""
    b = (name or "").rsplit("/", 1)[-1]
    return "placed" if b.startswith("3_place") else "cts" if b.startswith("4_cts") else "other" if b else ""


def metrics(path, strap_re=STRAP_RE_DEFAULT, odb="", max_layer="M5", grt_log=None, memory_libs=(), memory_reach=False, ft_interface=None, ft_ports=None,
            land_slots=None, face_guard=None):
    D = Design(path, memory_libs, memory_reach)
    sr = re.compile(strap_re)
    m = area_metrics(D)
    m.update(pin_metrics(D, sr))
    ck = clock_metrics(D)
    infra_pins = frozenset()
    if ft_interface or ft_ports:
        try:
            infra = declared_infra_arcs(D, json.loads(Path(ft_interface).read_text()), json.loads(Path(ft_ports).read_text()))
        except (OSError,TypeError,ValueError) as e:
            infra = dict(owner="die",width=1,arcs=[],pins=[],errors=[str(e)])
        m["die_owned_infra"] = infra
        infra_pins = frozenset(infra["pins"])
    caps, ring_clocks = {}, frozenset()
    if land_slots or face_guard:
        try:
            lr = land_ring_captures(D, json.loads(Path(land_slots).read_text()), json.loads(Path(face_guard).read_text()))
        except (OSError, TypeError, ValueError, AttributeError) as e:
            lr = dict(caps={}, clock_exports=[], errors=[str(e)], rejected=[], buses=[])
        caps, ring_clocks = lr["caps"], frozenset(lr["clock_exports"])
        m["land_ring"] = dict(buses=lr["buses"], pins=len(caps), clock_exports=lr["clock_exports"], errors=lr["errors"],
                              rejected=len(lr["rejected"]), rejected_sample=lr["rejected"][:8])
    m.update(pin_reg_metrics(D, sr, frozenset(ck["tap_sinks"]) | infra_pins | ring_clocks, caps))
    m.update(r2r_metrics(D))
    m.update(ck)
    m.update(macro_metrics(D))
    m.update(partial_face_metrics(D, m))
    m.update(relay_metrics(D))
    m.update(demand_metrics(D, max_layer or "M5"))
    m.update(clock_entry_metrics(D, ck))
    m.update(grt_metrics(grt_log))
    st = stage_of_odb(odb)
    if st:
        m["stage"] = st
    return m


def verdict_line(verdict, rules, title=""):
    short = {"PASS": "ok", "FAIL": "FAIL", "NA": "NA", "INFO": "info", "WARN": "WARN"}
    order = {"FAIL": 0, "NA": 0, "WARN": 1, "PASS": 2}
    parts = [f"{r['rule']}={short[r['status']]}({r['value'] if not isinstance(r['value'], dict) else max(r['value'].values() or [0])})"
             for r in sorted((r for r in rules if r["status"] != "INFO"), key=lambda r: order[r["status"]])]
    warn = "; ".join(f"{r['rule']} {r['value']}: {r['detail']}" for r in rules if r["status"] == "WARN")
    return (f"AUTO-GEOM {verdict}" + (f" {title}" if title else "") + (f" WARN[{warn}]" if warn else "") + " "
            + " ".join(parts))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dump")
    ap.add_argument("--json")
    ap.add_argument("--memory-lib",action="append",default=[],help="Actual kit Liberty model(s); used only with --memory-reach")
    ap.add_argument("--memory-reach", action="store_true", help="opt-in (COORD 10-29, default off): typed synchronous memories become r2r endpoints; missing/unproven macro models make r2r NA")
    ap.add_argument("--all-kits", action="store_true", help="owner 10-27: independent absolute checks without a template")
    ap.add_argument("--template", help="the template checkpoint's auto_geom.json (metrics of the visually passed part)")
    ap.add_argument("--outline", help="parent slot WxH (um)")
    ap.add_argument("--outline-self", action="store_true", help="no slot known: use the checkpoint's own outline (INFO)")
    ap.add_argument("--strap-re", default=STRAP_RE_DEFAULT)
    ap.add_argument("--title", default="")
    ap.add_argument("--odb", default="", help="checkpoint file name (stage: 3_place / 4_cts)")
    ap.add_argument("--max-layer", default="M5", help="kit MAX_ROUTING_LAYER (channel / column capacity)")
    ap.add_argument("--grt-log", default=None, help="geom_grt.tcl log (>= 50 congestion iterations)")
    ap.add_argument("--ft-interface", help="typed die-owned clock/reset interface model")
    ap.add_argument("--ft-ports", help="matching hash-checked scalar FT declaration")
    ap.add_argument("--land-slots", help="kit land_slots.json: declared landing ring (with --face-guard PASS) = registered capture")
    ap.add_argument("--face-guard", help="kit face_guard.json (verdict PASS) matching --land-slots")
    a = ap.parse_args(argv)
    m = metrics(a.dump, a.strap_re, a.odb, a.max_layer, a.grt_log, a.memory_lib, a.memory_reach, a.ft_interface, a.ft_ports,
                a.land_slots, a.face_guard)
    tmpl = json.load(open(a.template)) if a.template else None
    outline = [float(x) for x in a.outline.lower().split("x")] if a.outline else (m["outline"] if a.outline_self else None)
    rules, verdict = judge(m, tmpl, outline, a.all_kits)
    line = verdict_line(verdict, rules, a.title)
    out = dict(schema="opentallas.auto_geom.v2", dump=a.dump, verdict=verdict, line=line, rules=rules, metrics=m,
               reasons=reasons(rules), warns=[r["rule"] for r in rules if r["status"] == "WARN"],
               warn_detail=[f"{r['rule']} {r['value']}: {r['detail']}" for r in rules if r["status"] == "WARN"])
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)
    print("AP_AUTO_GEOM " + line)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
