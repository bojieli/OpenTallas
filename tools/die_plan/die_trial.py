#!/usr/bin/env python3
"""Trial full-chip prototype of a top-down die plan (lane TRIAL-QK, 2026-10-24): the whole die, every partition as
an abstract, long before G4.

    die_trial.py build  PLAN.json --out DIR            # abstracts + die DEF (data) + die clock tree DEF + scripts
    die_trial.py calib  --out DIR                      # repeated-wire hop timing tables (M8 / M9, SS / TT / FF)
    die_trial.py ir     PLAN.json --out DIR [--w-mm2 X] # PDNSim model: die PG on M8/M9 over the partition M7 PG
    die_trial.py report DIR --calib CDIR [--g2 G2.json] # results JSON + markdown + maps from the finished runs

What `build` writes (DIR):
  abstracts/<module>.lef  route-view abstract per partition type: the EXACT plan pins (gen_phys.type_pins, the kit
                 io.tcl rectangles), one station terminal pair (<slot>_s<j>_d / _q, M4) per ft bit per station at the
                 G2 station sites (slot regs_um, else evenly along the in -> out route, g2.part_probe), OBS M1-M3 over
                 the outline and M4..obs_max over the leaf / hard-core blockages (g2.probe_blockages).  M4-M7 above the
                 partition logic and M8/M9 stay open; their share for die traffic is the G0 capacity model
                 (GRT layer adjustment 1 - ft_track_frac on M4-M7, 1 - cut_avail on M8/M9).
  data.def       partitions placed FIXED at plan origin / orient, die IO pins at the die.io / die-edge port windows,
                 one net per register-to-register hop of every lane bit (abutted ports join the two face pins;
                 an ft slot joins S_i -> s0, s_j -> s_j+1, s_last -> S_o), so the die GRT routes every inter-partition
                 and feedthrough wire the partitions will own.
  nets.tsv.gz    per net: kind (abut / ft / io), driver register, capture registers, their partitions and nearest
                 clock taps (die frame), Manhattan length.
  clock.def + clock_tree.json   die clock distribution: the HBM-ARCH B2 MSCTS structured H-tree
                 (physical/die_plan/hbm_arch/clock_htree.py, claude/hbm-arch-1024 c984916b35: seam trunk on M9, mirrored
                 ribs on M8, uniform leaf-driver grid), generalised to this die's outline and tap density; BUFx16f
                 repeaters every <= REP_UM on every branch, one leaf driver per leaf cell, every partition clock tap fed
                 leaf -> mid buffer -> tap root buffer (BUFx24, the partition's tap buffer) with equal stage counts.
  route.tcl / clock.tcl / sta_clock.tcl / run_*.sh   OpenROAD GRT of the data nets and of the clock tree, SPEF of the
                 clock tree, OpenSTA tap arrivals per corner.

Timing model of the die STA (report): a hop's setup / hold slack = the calibrated register-to-register slack of a
repeated wire of the hop's GRT-routed length (calib: DFFHQNx1 -> BUFx12f every 250 um on M8/M9 -> DFFHQNx1, GRT +
estimate_parasitics, OpenSTA TT setup / FF hold (SS informational), T 833.333 ps, uncertainty 60 / 25 ps; the REACH-M89 GRT-validated method) plus
the die clock skew between the capture and launch partitions' taps (clock tree STA, same corner), minus OCV on the
non-common clock path (CPPR via the tree).  Partition-internal insertion is the common latency (250 ps) on both ends
(budget abstract).  FF hold gate (owner 2026-10-24 decision 5) = that hop hold + the receiving kit's contracted
seam-input hold padding (insertion_tol) - die skew; the bare insertion_tol window vs skew is an INFO column.  Clock
gate = related launch/capture tap pair skew (CPPR) <= 80 ps at TT and FF; max-min tap spread is INFO.
"""
import argparse
import gzip
import json
import math
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import g2  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

DBU = 1000
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
TECH_LEF = f"{PLAT}/lef/asap7_tech_1x_201209.lef"
SC_LEF = f"{PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef"
CKBUF = "BUFx16f_ASAP7_75t_R"
TAPBUF = "BUFx24_ASAP7_75t_R"
TAPLOAD = "DFFHQNx2_ASAP7_75t_R"   # tap load stand-in: a clock pin (OpenSTA arrivals are queried on clock pins)
REPBUF = "BUFx12f_ASAP7_75t_R"
FLOP = "DFFHQNx1_ASAP7_75t_R"
REP_UM = 250.0                 # repeater pitch (REACH-M89: BUFx12f 200-300 um slew-legal; owner <= 450)
ORIENT = {"R0": "N", "MX": "FS", "MY": "FN", "R180": "S"}
ST_LAYER = "M4"


def dbu(v):
    return int(round(v * DBU))


def sid(s):
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


# --------------------------------------------------------------------------------------------------- abstracts
def station_sites(P, tn, pins):
    """{slot: {bit: [(x, y) per station]}} in the type frame: slot regs_um, else evenly along the in -> out route of
    each bit (exactly g2.part_probe's station sites, so the die route and the G2 FT probes see the same flops)."""
    t = P.types[tn]
    by_bus = defaultdict(dict)
    for bus, bit, ln, x, y, f in pins:
        by_bus[bus][bit] = (x, y, f)

    def inset(x, y, f):
        d = g2.FLOP_INSET_UM
        return {"E": (x - d, y), "W": (x + d, y), "N": (x, y - d), "S": (x, y + d)}[f]
    out = {}
    for s in t.get("ft_slots", []):
        sn, k = s["name"], int(s.get("stations", 1))
        pi, po = by_bus.get(sn + "_i", {}), by_bus.get(sn + "_o", {})
        res = {}
        for bit in sorted(set(pi) | set(po)):
            x, y, f = pi.get(bit) or po[bit]
            xo, yo, fo = po.get(bit) or pi[bit]
            a, b = inset(x, y, f), inset(xo, yo, fo)
            seg = check.zroute(a, b, f, fo)
            L = check.plen(seg)
            res[bit] = [tuple(s["regs_um"][j]) if s.get("regs_um") else check.point_at(seg, L * j / k) for j in range(k)]
        out[sn] = res
    return out


def type_view(P, tn):
    """pins [(name, dir, layer, rect)] + station table + bus widths of type tn (type frame)."""
    t = P.types[tn]
    pins = gen_phys.type_pins(P, tn)
    dirs = {b["name"]: ("INPUT" if b["dir"] == "in" else "OUTPUT") for b in t.get("buses", [])}
    for sl in t.get("ft_slots", []):
        dirs[sl["name"] + "_i"], dirs[sl["name"] + "_o"] = "INPUT", "OUTPUT"
    rows, xy = [], {}
    for bus, bit, ln, x, y, f in sorted(pins, key=lambda p: (p[0], p[1])):
        lw = gen_phys.LAYER_W.get(ln, 0.04) / 2
        L = gen_phys.PIN_LEN_UM
        r = {"E": (x - L, y - lw, x, y + lw), "W": (x, y - lw, x + L, y + lw),
             "N": (x - lw, y - L, x + lw, y), "S": (x - lw, y, x + lw, y + L)}[f]
        nm = f"{bus}[{bit}]"
        rows.append((nm, dirs.get(bus, "INPUT"), ln, r))
        xy[nm] = (x, y)
    st = station_sites(P, tn, pins)
    hw = gen_phys.LAYER_W[ST_LAYER] / 2
    for sn, bits in sorted(st.items()):
        for bit, sites in sorted(bits.items()):
            for j, (x, y) in enumerate(sites):
                for io, dy in (("d", 0.0), ("q", 0.096)):
                    nm = f"{sn}_s{j}_{io}[{bit}]"
                    yy = y + dy
                    rows.append((nm, "INPUT" if io == "d" else "OUTPUT", ST_LAYER,
                                 (x - 0.096, yy - hw, x + 0.096, yy + hw)))
                    xy[nm] = (x, yy)
    return rows, st, xy


def lef_text(P, tn, rows):
    t = P.types[tn]
    w, h = t["outline_um"]
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {macro_name(tn)}", "  CLASS BLOCK ;",
         "  ORIGIN 0 0 ;", f"  SIZE {w:.4f} BY {h:.4f} ;"]
    for nm, d, ln, r in rows:
        L += [f"  PIN {nm}", f"    DIRECTION {d} ;", "    USE SIGNAL ;", "    PORT", f"      LAYER {ln} ;",
              f"        RECT {r[0]:.4f} {r[1]:.4f} {r[2]:.4f} {r[3]:.4f} ;", "    END", f"  END {nm}"]
    L.append("  OBS")
    for i in (1, 2, 3):
        L += [f"    LAYER M{i} ;", f"      RECT 0 0 {w:.4f} {h:.4f} ;"]
    for c in g2.probe_blockages(t):
        x0, y0 = c["origin_um"]
        x1, y1 = x0 + c["outline_um"][0], y0 + c["outline_um"][1]
        top = int(c.get("obs_max", "M5")[1:])
        for i in range(4, top + 1):
            L += [f"    LAYER M{i} ;", f"      RECT {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;"]
    L += ["  END", f"END {macro_name(tn)}", "END LIBRARY", ""]
    return "\n".join(L)


def macro_name(tn):
    """abstract master per partition TYPE (QC types share modules with different pin tables, e.g. cbf_q00 variants)."""
    return "tq_" + sid(tn)


# --------------------------------------------------------------------------------------------------- data nets
class UF:
    def __init__(self):
        self.p = {}

    def find(self, a):
        p = self.p
        p.setdefault(a, a)
        r = a
        while p[r] != r:
            r = p[r]
        while p[a] != r:
            p[a], a = r, p[a]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def nearest_tap(taps, x, y):
    best = None
    for nm, tx, ty in taps:
        d = abs(tx - x) + abs(ty - y)
        if best is None or d < best[0]:
            best = (d, nm)
    return best[1]


def build_nets(P, views):
    """union-find over (instance, pin) -> nets with their register roles."""
    uf = UF()
    role = {}                     # (inst, pin) -> 'L' launch register | 'C' capture register | 'F' face | 'IO'
    io_pins = {}                  # die pin name -> (layer, x, y, dir)
    for pid, pr in P.ports.items():
        pins = P.port_pins(pid)
        s, d = pr["src"], pr["dst"]
        for bit, ln, c in pins:
            ends = []
            for side, e in (("src", s), ("dst", d)):
                if e["part"] == S.DIE_PART:
                    nm = f"{sid(pid)}[{bit}]"
                    f = pr["face"]
                    x, y = ((P.W if f == "E" else 0.0), c) if f in "EW" else (c, (P.H if f == "N" else 0.0))
                    io_pins[nm] = (ln, x, y, "INPUT" if side == "src" else "OUTPUT", f)
                    key = ("PIN", nm)
                    role[key] = "IO"
                else:
                    key = (e["part"], f"{e['bus']}[{bit}]")
                    b = P.buses(e["part"]).get(e["bus"], {})
                    if b.get("slot"):
                        role[key] = "F"
                    else:
                        role[key] = "L" if side == "src" else "C"
                ends.append(key)
            uf.union(*ends)
    for n, p in P.parts.items():
        st = views[p["type"]]["stations"]
        for sn, bits in st.items():
            for bit, sites in bits.items():
                k = len(sites)
                si, so = (n, f"{sn}_i[{bit}]"), (n, f"{sn}_o[{bit}]")
                uf.union(si, (n, f"{sn}_s0_d[{bit}]"))
                for j in range(k):
                    role[(n, f"{sn}_s{j}_d[{bit}]")] = "C"
                    role[(n, f"{sn}_s{j}_q[{bit}]")] = "L"
                    if j + 1 < k:
                        uf.union((n, f"{sn}_s{j}_q[{bit}]"), (n, f"{sn}_s{j + 1}_d[{bit}]"))
                uf.union((n, f"{sn}_s{k - 1}_q[{bit}]"), so)
    nets = defaultdict(list)
    for key in role:
        nets[uf.find(key)].append(key)
    return list(nets.values()), role, io_pins


def die_xy(P, views, key, io_pins):
    if key[0] == "PIN":
        _, x, y, _, _ = io_pins[key[1]]
        return x, y
    n, pin = key
    x, y = views[P.parts[n]["type"]]["xy"][pin]
    return P.to_die(n, (x, y))


def write_data(P, views, out):
    nets, role, io_pins = build_nets(P, views)
    taps_die = {}
    for n, p in P.parts.items():
        taps_die[n] = [(nm, *P.to_die(n, (x, y))) for nm, x, y in gen_phys.clock_pins(P, p["type"])]
    D = [f"VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', f"DESIGN {sid(P.name)}_trial ;",
         f"UNITS DISTANCE MICRONS {DBU} ;", f"DIEAREA ( 0 0 ) ( {dbu(P.W)} {dbu(P.H)} ) ;",
         f"COMPONENTS {len(P.parts)} ;"]
    for n, p in sorted(P.parts.items()):
        m = macro_name(p["type"])
        D.append(f"- {sid(n)} {m} + FIXED ( {dbu(p['origin_um'][0])} {dbu(p['origin_um'][1])} ) "
                 f"{ORIENT[p.get('orient', 'R0')]} ;")
    D.append("END COMPONENTS")
    D.append(f"PINS {len(io_pins)} ;")
    for nm, (ln, x, y, d, f) in sorted(io_pins.items()):
        lw = gen_phys.LAYER_W.get(ln, 0.04) / 2
        L = gen_phys.PIN_LEN_UM
        # pin shape relative to the placement point (on the die edge), pointing into the die
        r = {"E": (-L, -lw, 0, lw), "W": (0, -lw, L, lw), "N": (-lw, -L, lw, 0), "S": (-lw, 0, lw, L)}[f]
        D.append(f"- {nm} + NET {nm} + DIRECTION {d} + USE SIGNAL + LAYER {ln} ( {dbu(r[0])} {dbu(r[1])} ) "
                 f"( {dbu(r[2])} {dbu(r[3])} ) + FIXED ( {dbu(x)} {dbu(y)} ) N ;")
    D.append("END PINS")
    meta = []
    netlines = []
    kinds = defaultdict(int)
    for i, terms in enumerate(sorted(nets, key=lambda ts: sorted(ts)[0])):
        launch = [k for k in terms if role[k] == "L"]
        capture = [k for k in terms if role[k] == "C"]
        io = [k for k in terms if role[k] == "IO"]
        if io:
            nm = io[0][1]
            kind = "io"
        else:
            nm = f"n{i}"
            parts = {k[0] for k in terms}
            kind = "abut" if len(parts) <= 2 and not any(role[k] == "F" for k in terms) else "ft"
        kinds[kind] += 1
        pts = [die_xy(P, views, k, io_pins) for k in terms]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        hpwl = (max(xs) - min(xs)) + (max(ys) - min(ys))
        if len(terms) > 1:
            netlines.append(f"- {nm} " + " ".join(f"( PIN {k[1]} )" if k[0] == "PIN" else f"( {sid(k[0])} {k[1]} )"
                                                  for k in terms) + " ;")

        def reg(k):
            if k[0] == "PIN":
                return f"PIN:{k[1]}"
            x, y = die_xy(P, views, k, io_pins)
            return f"{k[0]}:{k[1]}:{nearest_tap(taps_die[k[0]], x, y)}:{x:.1f}:{y:.1f}"
        meta.append("\t".join([nm, kind, f"{hpwl:.1f}", str(len(terms)), ";".join(reg(k) for k in launch + io[:0]),
                               ";".join(reg(k) for k in capture), ";".join(reg(k) for k in io)]))
    D.append(f"NETS {len(netlines)} ;")
    D += netlines
    D += ["END NETS", "END DESIGN", ""]
    with gzip.open(out / "data.def.gz", "wt") as f:
        f.write("\n".join(D))
    with gzip.open(out / "nets.tsv.gz", "wt") as f:
        f.write("net\tkind\thpwl_um\tterms\tlaunch\tcapture\tio\n" + "\n".join(meta) + "\n")
    tapj = {n: [[nm, round(x, 3), round(y, 3)] for nm, x, y in v] for n, v in taps_die.items()}
    (out / "taps.json").write_text(json.dumps(tapj) + "\n")
    return dict(nets=len(netlines), kinds=dict(kinds), io_pins=len(io_pins))


# ---------------------------------------------------------------------------------------------- PG obstructions
def pg_obstructions(P, layers=None):
    """die PG stripes (die.pg.grid) as obstructions, exactly as g2.die_probe draws them."""
    W, H = P.W, P.H
    out = []
    for g in P.die.get("pg", {}).get("grid", []):
        L = P.layers.get(g["layer"])
        if not L or (layers and g["layer"] not in layers):
            continue
        k = max(1, len(g.get("nets", ["VDD", "VSS"])))
        ext = H if L["dir"] == "V" else W
        span = W if L["dir"] == "V" else H
        pos = g["offset_um"]
        while pos < span:
            for j in range(k):
                c = pos + j * g["pitch_um"] / k
                if c + g["width_um"] / 2 > span:
                    continue
                a, b = c - g["width_um"] / 2, c + g["width_um"] / 2
                r = (a, 0, b, ext) if L["dir"] == "V" else (0, a, ext, b)
                out.append((g["layer"], r))
            pos += g["pitch_um"]
    return out


def write_pg_obs(P, path):
    obs = pg_obstructions(P)
    with open(path, "w") as f:
        f.write("# GENERATED by die_trial.py: die PG stripes (die.pg.grid) as obstructions (GRT capacity)\n")
        for ln, r in obs:
            f.write(f"create_obstruction -region {{{r[0]:.3f} {r[1]:.3f} {r[2]:.3f} {r[3]:.3f}}} -layer {ln}\n")
    return len(obs)


# --------------------------------------------------------------------------------------------------- clock tree
def htree_geom(W, H, nrib, nx, ny):
    """HBM-ARCH B2 MSCTS H-tree (hbm_arch/clock_htree.py build(), c984916b35), parameterised: trunk = balanced binary
    tree along the vertical seam x = W/2 (M9) to nrib rib nodes; at every rib node one W and one E rib (M8), each a
    balanced H-tree over its half-die band ending in nx x ny leaf drivers.  -> (segs, leaves); seg = (x0, y0, x1, y1,
    level, layer), drawn parent -> child."""
    segs, leaves = [], []

    def seg(a, b, lev):
        (x0, y0), (x1, y1) = a, b
        segs.append((round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3), lev, "M9" if x0 == x1 else "M8"))
    xc = W / 2.0

    def trunk(y, half, lev, n):
        if n == 1:
            return [y]
        out = []
        for s in (-1, 1):
            y2 = y + s * half / 2.0
            seg((xc, y), (xc, y2), lev)
            out += trunk(y2, half / 2.0, lev + 1, n // 2)
        return out
    ribs = trunk(H / 2.0, H / 2.0, 1, nrib)
    lev0 = 1 + (nrib.bit_length() - 1)

    def htree(cx, cy, w, h, nx_, ny_, lev):
        if nx_ == 1 and ny_ == 1:
            leaves.append((round(cx, 3), round(cy, 3)))
            return
        if nx_ >= ny_ and nx_ > 1:
            for s in (-1, 1):
                x2 = cx + s * w / 4.0
                seg((cx, cy), (x2, cy), lev)
                htree(x2, cy, w / 2.0, h, nx_ // 2, ny_, lev + 1)
        else:
            for s in (-1, 1):
                y2 = cy + s * h / 4.0
                seg((cx, cy), (cx, y2), lev)
                htree(cx, y2, w, h / 2.0, nx_, ny_ // 2, lev + 1)
    bh = H / nrib
    for y in ribs:
        for side in (-1, 1):
            tx = xc + side * W / 4.0
            seg((xc, y), (tx, y), lev0)
            htree(tx, y, W / 2.0, bh, nx, ny, lev0 + 1)
    return segs, leaves


def pow2_at_least(v):
    return 1 << max(0, math.ceil(math.log2(max(1.0, v))))


def build_clock(P, out, leaf_um=None):
    """die clock tree netlist (DEF, std cells only) + tree topology for CPPR."""
    W, H = P.W, P.H
    ntap = sum(len(gen_phys.clock_pins(P, p["type"])) for p in P.parts.values())
    # leaf cell ~ one tap-grid cell: ~ as many leaf drivers as partition taps (power-of-two H-tree counts, rounded down)
    pitch = leaf_um or max(float(P.budgets.get("tap_pitch_um", 400.0)), math.sqrt(W * H / max(1, ntap)))
    # leaf cell <= the tap pitch (power-of-two counts rounded UP): every tap within ~half a pitch of its leaf driver,
    # so the leaf -> tap legs (not balanced by delay padding here) stay short and nearly equal
    nx = pow2_at_least(W / 2 / pitch)
    nband = pow2_at_least(H / pitch)
    nrib = min(16, nband)
    ny = max(1, nband // nrib)
    segs, leaves = htree_geom(W, H, nrib, nx, ny)
    cx, cy = W / 2.0, H / 2.0
    root_pin = {n: (x, y) for n, L, x, y in gen_phys.die_root_pins(P)}["clk"]
    comps, nets = [], []          # comps: (name, cell, x, y); nets: (name, driver (inst, pin) | PIN, [(inst, pin)])
    node_of = {}                  # point -> buffer instance at that tree node
    parent = {}                   # instance -> parent instance (clock tree topology incl. repeaters)

    def clampx(x):
        return min(max(x, 1.0), W - 2.0)

    def clampy(y):
        return min(max(y, 1.0), H - 2.0)

    def add_buf(name, x, y, cell=CKBUF):
        comps.append((name, cell, clampx(x), clampy(y)))
        return name

    def chain(src, a, b, tag, end_cell=CKBUF, end_name=None):
        """buffered wire from instance src (at point a) to a new buffer at b: repeaters every <= REP_UM."""
        L = abs(a[0] - b[0]) + abs(a[1] - b[1])
        k = max(1, math.ceil(L / REP_UM - 1e-9))
        prev = src
        for j in range(1, k + 1):
            f = j / k
            # L-shaped: x first, then y (H-tree legs are straight; local legs are short)
            t = f * L
            dx = abs(b[0] - a[0])
            if t <= dx:
                x, y = a[0] + math.copysign(t, b[0] - a[0]), a[1]
            else:
                x, y = b[0], a[1] + math.copysign(t - dx, b[1] - a[1])
            last = j == k
            nm = end_name if (last and end_name) else f"{tag}_r{j}"
            add_buf(nm, x, y, end_cell if last else CKBUF)
            nets.append((f"ck_{nm}", (prev, "Y"), [(nm, "A")]))
            parent[nm] = prev
            prev = nm
        return prev
    # root: die clk pin -> buffered stub -> tree centre node
    first = add_buf("ck_root", *root_pin)
    nets.append(("clk", ("PIN", "clk"), [(first, "A")]))
    parent[first] = None
    node_of[(round(cx, 3), round(cy, 3))] = chain(first, root_pin, (cx, cy), "ck_stub", end_name="ck_c")
    nseg = 0
    for (x0, y0, x1, y1, lev, ln) in segs:          # segs are emitted parent before child
        src = node_of[(x0, y0)]
        nseg += 1
        node_of[(x1, y1)] = chain(src, (x0, y0), (x1, y1), f"ck_l{lev}_{nseg}", end_name=f"ck_n{nseg}")
    leaf_inst = {lf: node_of[lf] for lf in leaves}
    # taps -> nearest leaf; leaf -> mid buffer -> tap root buffer (equal stage count)
    taps = []
    for n, p in sorted(P.parts.items()):
        for nm, x, y in gen_phys.clock_pins(P, p["type"]) + gen_phys.core_tap_pins(P, p["type"]):
            taps.append((n, nm, *P.to_die(n, (x, y))))
    import bisect
    lx = sorted(set(l[0] for l in leaves))
    ly = sorted(set(l[1] for l in leaves))

    def near(v, arr):
        i = bisect.bisect_left(arr, v)
        c = [arr[j] for j in (i - 1, i) if 0 <= j < len(arr)]
        return min(c, key=lambda a: abs(a - v))
    tap_rows = []
    for k, (n, nm, x, y) in enumerate(taps):
        lf = (near(x, lx), near(y, ly))
        src = leaf_inst[lf]
        mid = ((lf[0] + x) / 2, (lf[1] + y) / 2)
        tb = f"tap_{sid(n)}__{nm}"
        mb = add_buf(f"ckm_{k}", *mid)
        nets.append((f"ck_ckm_{k}", (src, "Y"), [(mb, "A")]))
        parent[mb] = src
        add_buf(tb, x, y, TAPLOAD)
        nets.append((f"ck_{tb}", (mb, "Y"), [(tb, "CLK")]))
        parent[tb] = mb
        tap_rows.append(dict(part=n, tap=nm, x=round(x, 3), y=round(y, 3), inst=tb, leaf=src,
                             leaf_um=round(abs(lf[0] - x) + abs(lf[1] - y), 1)))
    # merge nets with the same driver (a node buffer drives its two children + local mids from one output)
    by_drv = defaultdict(list)
    for nm, drv, loads in nets:
        by_drv[drv].extend(loads)
    D = ["VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', f"DESIGN {sid(P.name)}_clock ;",
         f"UNITS DISTANCE MICRONS {DBU} ;", f"DIEAREA ( 0 0 ) ( {dbu(W)} {dbu(H)} ) ;",
         f"COMPONENTS {len(comps)} ;"]
    for nm, cell, x, y in comps:
        D.append(f"- {nm} {cell} + PLACED ( {dbu(x)} {dbu(y)} ) N ;")
    D += ["END COMPONENTS", "PINS 1 ;",
          f"- clk + NET clk + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -20 -160 ) ( 20 160 ) "
          f"+ FIXED ( {dbu(gen_phys.pg_free(P, 'M9', root_pin[0]))} {dbu(root_pin[1])} ) N ;", "END PINS"]
    D.append(f"NETS {len(by_drv)} ;")
    for drv, loads in by_drv.items():
        nm = "clk" if drv[0] == "PIN" else f"ck_{drv[0]}"
        t0 = "( PIN clk )" if drv[0] == "PIN" else f"( {drv[0]} {drv[1]} )"
        D.append(f"- {nm} {t0} " + " ".join(f"( {a} {b} )" for a, b in loads) + " + USE CLOCK ;")
    D += ["END NETS", "END DESIGN", ""]
    (out / "clock.def").write_text("\n".join(D))
    ncell = defaultdict(int)
    for _, c, _, _ in comps:
        ncell[c] += 1
    tree = dict(params=dict(nrib=nrib, nx=nx, ny=ny, leaves=len(leaves), rep_um=REP_UM, leaf_pitch_um=pitch,
                            centre=[cx, cy], root_pin=list(root_pin)),
                cells=dict(ncell), segments=[list(s) for s in segs], taps=tap_rows, parent=parent,
                wire_um=round(sum(abs(s[0] - s[2]) + abs(s[1] - s[3]) for s in segs), 1),
                local_um=round(sum(t["leaf_um"] for t in tap_rows), 1))
    (out / "clock_tree.json").write_text(json.dumps(tree) + "\n")
    return tree


# --------------------------------------------------------------------------------------------------- scripts
def grt_adjust(P, mode="g0"):
    """GRT layer adjustments: the G0 capacity model (partition ft layers M4-M7 at ft_track_frac, die layers at
    cut_avail) -- 'g0'; or over-the-top only (M8/M9 at cut_avail, M4-M7 closed except pin access) -- 'ott'."""
    ftf = 0.25
    cut = P.layer_budget.get("cut_avail", {"M8": 0.6, "M9": 0.6})
    adj = {}
    for L in ("M4", "M5", "M6", "M7"):
        adj[L] = round(1.0 - ftf, 3) if mode == "g0" else 0.95
    for L in ("M8", "M9"):
        adj[L] = round(1.0 - float(cut.get(L, 0.6)), 3)
    return adj


def route_tcl(P, lefs, mode="g0"):
    adj = grt_adjust(P, mode)
    t = [f"# GENERATED by tools/die_plan/die_trial.py: die GRT of every inter-partition / ft hop, die {P.name}, "
         f"capacity model {mode}",
         f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}"]
    t += [f"read_lef /work/abstracts/{x}" for x in lefs]
    t += ["set t0 [clock seconds]",
          "read_def /work/data.def",
          "puts \"OT_T_READ [expr {[clock seconds]-$t0}]\"",
          "source /work/make_tracks.tcl",
          "source /work/pg_obs.tcl",
          "set_routing_layers -signal M4-M9"]
    t += [f"set_global_routing_layer_adjustment {L} {v:g}" for L, v in adj.items()]
    t += ["global_route -congestion_iterations 30 -allow_congestion -verbose "
          f"-congestion_report_file /work/grt_{mode}_congestion.rpt",
          "puts \"OT_T_GRT [expr {[clock seconds]-$t0}]\"",
          f"report_wire_length -net [get_nets *] -global_route -file /work/grt_{mode}_wl.csv",
          "puts \"OT_T_WL [expr {[clock seconds]-$t0}]\"",
          f"if {{[catch {{gui::dump_heatmap Routing /work/grt_{mode}_heatmap.csv}} e]}} {{ puts \"OT_HEATMAP_FAIL $e\" }}",
          "puts \"OT_T_DONE [expr {[clock seconds]-$t0}]\"",
          "puts OT_DONE"]
    return "\n".join(t) + "\n"


def clock_tcl(P):
    t = [f"# GENERATED by tools/die_plan/die_trial.py: die clock tree GRT (M8/M9; M2-M7 closed, pins lifted by vias, "
         "REACH-M89 grt_case) + SPEF for the tap-arrival STA",
         f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}",
         f"foreach f [glob {PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{ read_liberty $f }}",
         "set t0 [clock seconds]",
         "read_def /work/clock.def",
         "source /work/make_tracks.tcl",
         "source /work/pg_obs.tcl",
         "set_routing_layers -signal M2-M9 -clock M2-M9"]
    t += [f"set_global_routing_layer_adjustment M{i} 1.0" for i in range(2, 8)]
    t += ["global_route -congestion_iterations 30 -allow_congestion -verbose "
          "-congestion_report_file /work/clock_congestion.rpt",
          "puts \"OT_T_GRT [expr {[clock seconds]-$t0}]\"",
          f"source {PLAT}/setRC.tcl",
          "estimate_parasitics -global_routing -spef_file /work/clock.spef",
          "write_verilog /work/clock.v",
          "report_wire_length -net [get_nets *] -global_route -file /work/clock_wl.csv",
          "puts OT_DONE"]
    return "\n".join(t) + "\n"


def sta_clock_tcl(P):
    return f"""# GENERATED by tools/die_plan/die_trial.py: die clock tree tap arrivals (env CORNER, OUT)
set L {PLAT}/lib/NLDM
foreach f [glob $L/*RVT_$::env(CORNER)_nldm*.lib*] {{ read_liberty $f }}
read_verilog /work/clock.v
link_design {sid(P.name)}_clock
read_spef /work/clock.spef
create_clock -name clk -period {P.die['period_ps']:.4f} [get_ports clk]
set_propagated_clock [all_clocks]
# (a pin arrival query before the first search segfaults OpenSTA: run one report first)
report_checks -path_delay max -format end
set fh [open $::env(OUT) w]
foreach p [concat [get_pins */A] [get_pins tap_*/CLK]] {{
  puts $fh "[get_full_name $p] [get_property $p arrival_max_rise]"
}}
close $fh
report_check_types -max_slew -max_capacitance -violators
puts OT_DONE
"""


RUN = r"""#!/bin/bash
# GENERATED by tools/die_plan/die_trial.py.  run_<what>.sh [MEM_GB] [CPUS]   (heavy: launch through ot-run)
set -uo pipefail
D=$(cd $(dirname $0) && pwd); MEM=${1:-%(mem)d}; CPUS=${2:-%(cpus)d}
IMAGE=${OT_ORFS_IMAGE:-%(image)s}
DK=docker; docker info >/dev/null 2>&1 || DK="sudo docker"
echo "image $IMAGE $($DK image inspect --format '{{.Id}}' $IMAGE)" > $D/image_%(what)s.txt
$DK run --rm --name trialqk-%(what)s-$$ --cpus=$CPUS --memory=${MEM}g --memory-swap=${MEM}g -v $D:/work -w /work \
  -e HUID=$(id -u) -e HGID=$(id -g) $IMAGE bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; RC=0; %(body)s chown -R \$HUID:\$HGID /work; exit \$RC"
rc=$?; echo "run_%(what)s exit $rc" >> $D/image_%(what)s.txt; exit $rc
"""


def write_run(out, what, body, mem, cpus):
    p = out / f"run_{what}.sh"
    p.write_text(RUN % dict(mem=mem, cpus=cpus, image=IMAGE, what=what, body=body))
    p.chmod(0o755)


def die_tracks_tcl(P, coarse=0.64):
    """plan tracks on M4-M9; M1-M3 (inside the partitions, never die routing) coarse so the GRT gcell stays die-sized
    (the GRT tile follows the lowest layers' pitch; g2.die_probe does the same)."""
    lines = ["# GENERATED by die_trial.py: plan tracks M4-M9 (symmetric), M1-M3 coarse (GRT gcell size)"]
    for n in ("M9", "M8", "M7", "M6", "M5", "M4"):
        L = P.layers.get(n)
        lines.append(f"make_tracks {n} -x_offset {L['offset_um']:g} -x_pitch {L['pitch_um']:g} "
                     f"-y_offset {L['offset_um']:g} -y_pitch {L['pitch_um']:g}")
    for n in ("M3", "M2", "M1"):
        lines.append(f"make_tracks {n} -x_offset {coarse / 2:g} -x_pitch {coarse:g} -y_offset {coarse / 2:g} "
                     f"-y_pitch {coarse:g}")
    return "\n".join(lines) + "\n"


def cmd_build(a):
    raw = S.load(a.plan)
    P = S.Plan(raw)
    out = Path(a.out)
    if a.clock_only:
        tree = build_clock(P, out)
        info = json.loads((out / "build.json").read_text())
        info["clock"] = dict(tree["params"], cells=tree["cells"], taps=len(tree["taps"]), htree_wire_um=tree["wire_um"],
                             local_wire_um=tree["local_um"])
        (out / "build.json").write_text(json.dumps(info, indent=1) + "\n")
        print(json.dumps(info["clock"]))
        return
    (out / "abstracts").mkdir(parents=True, exist_ok=True)
    views, lefs = {}, []
    npins = 0
    for tn, t in sorted(P.types.items()):
        if not any(p["type"] == tn for p in P.parts.values()):
            continue
        rows, st, xy = type_view(P, tn)
        views[tn] = dict(stations=st, xy=xy)
        f = f"{macro_name(tn)}.lef"
        (out / "abstracts" / f).write_text(lef_text(P, tn, rows))
        lefs.append(f)
        npins += len(rows)
    info = dict(plan=str(Path(a.plan).resolve()), die=P.name, outline_um=[P.W, P.H], parts=len(P.parts),
                types=len(views), abstract_pins=npins)
    info["data"] = write_data(P, views, out)
    info["pg_obstructions"] = write_pg_obs(P, out / "pg_obs.tcl")
    (out / "make_tracks.tcl").write_text(die_tracks_tcl(P))
    tree = build_clock(P, out)
    info["clock"] = dict(tree["params"], cells=tree["cells"], taps=len(tree["taps"]), htree_wire_um=tree["wire_um"],
                         local_wire_um=tree["local_um"])
    for mode in ("g0", "ott"):
        (out / f"route_{mode}.tcl").write_text(route_tcl(P, lefs, mode))
        write_run(out, f"route_{mode}", f"gunzip -kf /work/data.def.gz; /usr/bin/time -v openroad -threads $CPUS -exit "
                  f"/work/route_{mode}.tcl > /work/route_{mode}.log 2>&1; RC=\\$?; echo EXIT \\$RC >> /work/route_{mode}.log;",
                  a.mem, a.cpus)
    (out / "clock.tcl").write_text(clock_tcl(P))
    (out / "sta_clock.tcl").write_text(sta_clock_tcl(P))
    write_run(out, "clock", "/usr/bin/time -v openroad -threads $CPUS -exit /work/clock.tcl > /work/clock.log 2>&1; "
              "RC=\\$?; echo EXIT \\$RC >> /work/clock.log; for c in TT FF SS; do CORNER=\\$c OUT=/work/clock_arr_\\$c.txt "
              "sta -no_splash -exit /work/sta_clock.tcl > /work/sta_clock_\\$c.log 2>&1 || RC=1; done;", 64, 8)
    import hashlib
    info["plan_sha256"] = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    (out / "build.json").write_text(json.dumps(info, indent=1) + "\n")
    print(json.dumps(info, indent=1))


# --------------------------------------------------------------------------------------------------- calibration
CAL_L = [2, 25, 50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600,
         1800, 2000, 2400]


def cmd_calib(a):
    """repeated-wire register-to-register hops: DFF -> BUFx12f every REP_UM -> DFF, straight on M8 (H) and M9 (V)."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    comps, nets = [], []
    W, H = 3000.0, 3000.0
    rows = []
    for li, (ln, horiz) in enumerate((("M8", True), ("M9", False))):
        for k, L in enumerate(CAL_L):
            tag = f"{ln}_{L}"
            p0 = (100.0, 100.0 + k * 40.0) if horiz else (1200.0 + k * 40.0, 300.0)
            def at(t):
                return (p0[0] + t, p0[1]) if horiz else (p0[0], p0[1] + t)
            nrep = max(0, math.ceil(L / REP_UM - 1e-9) - 1)
            comps.append((f"l_{tag}", FLOP, *at(0)))
            comps.append((f"c_{tag}", FLOP, *at(L)))
            prev = (f"l_{tag}", "QN")
            for j in range(1, nrep + 1):
                b = f"r_{tag}_{j}"
                comps.append((b, REPBUF, *at(L * j / (nrep + 1))))
                nets.append((f"w_{tag}_{j}", prev, [(b, "A")]))
                prev = (b, "Y")
            nets.append((f"w_{tag}_e", prev, [(f"c_{tag}", "D")]))
            nets.append((f"fb_{tag}", (f"c_{tag}", "QN"), [(f"l_{tag}", "D")]))   # keep both flops' D driven
            rows.append(dict(tag=tag, layer=ln, L=L, reps=nrep))
    D = ["VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', "DESIGN calib ;",
         f"UNITS DISTANCE MICRONS {DBU} ;", f"DIEAREA ( 0 0 ) ( {dbu(W)} {dbu(H)} ) ;", f"COMPONENTS {len(comps)} ;"]
    D += [f"- {n} {c} + PLACED ( {dbu(x)} {dbu(y)} ) N ;" for n, c, x, y in comps]
    D += ["END COMPONENTS", "PINS 1 ;", f"- clk + NET clk + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -20 -160 ) "
          f"( 20 160 ) + FIXED ( {dbu(1500)} {dbu(5)} ) N ;", "END PINS"]
    flops = [n for n, c, _, _ in comps if c == FLOP]
    D.append(f"NETS {len(nets) + 1} ;")
    D.append("- clk ( PIN clk ) " + " ".join(f"( {f} CLK )" for f in flops) + " + USE CLOCK ;")
    for n, drv, loads in nets:
        D.append(f"- {n} ( {drv[0]} {drv[1]} ) " + " ".join(f"( {x} {y} )" for x, y in loads) + " ;")
    D += ["END NETS", "END DESIGN", ""]
    (out / "calib.def").write_text("\n".join(D))
    (out / "calib.json").write_text(json.dumps(rows, indent=0) + "\n")
    tcl = [f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}",
           f"foreach f [glob {PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{ read_liberty $f }}",
           "read_def /work/calib.def", "source /work/make_tracks.tcl", "set_routing_layers -signal M2-M9"]
    tcl += [f"set_global_routing_layer_adjustment M{i} 1.0" for i in range(2, 8)]
    tcl += ["global_route -allow_congestion -verbose", f"source {PLAT}/setRC.tcl",
            "estimate_parasitics -global_routing -spef_file /work/calib.spef", "write_verilog /work/calib.v",
            "report_wire_length -net [get_nets w_*] -global_route -file /work/calib_wl.csv", "puts OT_DONE"]
    (out / "calib.tcl").write_text("\n".join(tcl) + "\n")
    sta = f"""set L {PLAT}/lib/NLDM
foreach f [glob $L/*RVT_$::env(CORNER)_nldm*.lib*] {{ read_liberty $f }}
read_verilog /work/calib.v
link_design calib
read_spef /work/calib.spef
create_clock -name clk -period 833.333 [get_ports clk]
set_clock_uncertainty 60 -setup [all_clocks]
set_clock_uncertainty 25 -hold [all_clocks]
report_checks -path_delay max -format end
report_checks -path_delay max -group_path_count 1000 -endpoint_path_count 1 -format end > $::env(OUT).max
report_checks -path_delay min -group_path_count 1000 -endpoint_path_count 1 -format end > $::env(OUT).min
puts OT_DONE
"""
    (out / "sta_calib.tcl").write_text(sta)
    P = S.Plan(json.loads((HERE / "examples" / "tiny_plan.json").read_text()))
    (out / "make_tracks.tcl").write_text(die_tracks_tcl(P))
    write_run(out, "calib", "openroad -exit /work/calib.tcl > /work/calib.log 2>&1 || RC=1; for c in TT FF SS; do "
              "CORNER=\\$c OUT=/work/calib_\\$c.txt sta -no_splash -exit /work/sta_calib.tcl > /work/sta_calib_\\$c.log "
              "2>&1 || RC=1; done;", 16, 4)
    print(out)



# --------------------------------------------------------------------------------------------------- report
SETUP_C, HOLD_C = "TT", "FF"   # release policy: TT setup / FF hold (60 / 25 ps); SS is informational only, never gates
OCV = 0.05          # flat clock OCV derate on the non-common (post-CPPR) tree path, TT / FF / SS (ASSUMED, stated)
CAL_MARGIN = 0.76 / 0.6315   # REACH-M89 calibration of the repeated-wire delay (planning-constant margin)
END_RE = re.compile(r"^(c_(M\d)_(\d+))/D \S+\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)")


def load_calib(cdir):
    """{corner: {layer: [(L, setup_slack, hold_slack, arrival)]}} from the calib run (report_checks -format end)."""
    out = {}
    for c in ("SS", "TT", "FF"):
        tab = defaultdict(dict)
        for dly in ("max", "min"):
            f = Path(cdir) / f"calib_{c}.txt.{dly}"
            for ln in f.read_text().splitlines():
                m = END_RE.match(ln.strip())
                if m:
                    L = int(m.group(3))
                    req, arr, sl = float(m.group(4)), float(m.group(5)), float(m.group(6))
                    tab[(m.group(2), L)][dly] = (sl, arr)
        rows = defaultdict(list)
        for (ln, L), v in sorted(tab.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            if "max" in v and "min" in v:
                rows[ln].append((L, v["max"][0], v["min"][0], v["max"][1]))
        out[c] = dict(rows)
    return out


def interp(rows, L, col):
    """linear interpolation in the calib table (column col), extrapolated linearly past the last point."""
    if L <= rows[0][0]:
        return rows[0][col]
    for a, b in zip(rows, rows[1:]):
        if L <= b[0]:
            f = (L - a[0]) / (b[0] - a[0])
            return a[col] + f * (b[col] - a[col])
    a, b = rows[-2], rows[-1]
    return b[col] + (L - b[0]) * (b[col] - a[col]) / (b[0] - a[0])


def hop_setup(cal, corner, L, calibrated=False):
    """worst of M8 / M9 register-to-register setup slack of a repeated hop of length L (ps)."""
    v = []
    for ln, rows in cal[corner].items():
        s = interp(rows, L, 1)
        if calibrated:
            s -= (CAL_MARGIN - 1.0) * (interp(rows, L, 3) - rows[0][3])
        v.append(s)
    return min(v)


def hop_hold(cal, corner, L):
    return min(interp(rows, L, 2) for rows in cal[corner].values())


def load_arrivals(bdir):
    arr = {}
    for c in ("TT", "FF", "SS"):
        f = Path(bdir) / f"clock_arr_{c}.txt"
        d = {}
        if f.is_file():
            for ln in f.read_text().splitlines():
                p = ln.split()
                if len(p) >= 2 and p[1] not in ("NA", ""):
                    try:
                        d[p[0].rsplit("/", 1)[0]] = float(p[1])
                    except ValueError:
                        pass
        arr[c] = d
    return arr


def read_wl(path):
    wl = {}
    if Path(path).is_file():
        with open(path) as f:
            for ln in f:
                p = ln.split()
                if len(p) >= 3 and p[0] == "grt:":
                    wl[p[1]] = float(p[2])
    return wl


def parse_reg(s):
    p = s.split(":")
    return dict(part=p[0], pin=p[1], tap=p[2], x=float(p[3]), y=float(p[4]))


def cmd_report(a):
    B = Path(a.dir)
    info = json.loads((B / "build.json").read_text())
    raw = S.load(info["plan"]) if not a.plan else S.load(a.plan)
    P = S.Plan(raw)
    res = dict(schema="opentallas.die_trial.v1", die=P.name, plan=info["plan"], plan_sha256=info["plan_sha256"],
               build=info, period_ps=P.die["period_ps"], unc_setup_ps=60.0, unc_hold_ps=25.0,
               common_latency_ps=P.clock.get("common_latency_ps", P.clock["insertion_ps"]),
               seam_skew_rule_ps=P.clock.get("neighbour_skew_ps", 80), insertion_tol_ps=P.clock["insertion_tol_ps"])
    # ---------------- route
    rt = {}
    for mode in ("g0", "ott"):
        lg = B / f"route_{mode}.log"
        if not lg.is_file():
            continue
        txt = lg.read_text(errors="replace")
        r = g2.parse_grt(txt)
        m = re.findall(r"OT_T_GRT (\d+)", txt)
        r["grt_seconds"] = int(m[-1]) if m else None
        m = re.findall(r"Maximum resident set size \(kbytes\): (\d+)", txt)
        r["peak_rss_gb"] = round(int(m[-1]) / 1048576, 1) if m else None
        r["windows"] = worst_windows(P, B / f"grt_{mode}_heatmap.csv", a.window)
        r["overflow_by_part"] = overflow_by_part(P, B / f"grt_{mode}_congestion.rpt")
        rt[mode] = r
    res["route"] = rt
    # ---------------- clock
    tree = json.loads((B / "clock_tree.json").read_text())
    arr = load_arrivals(B)
    parent = tree["parent"]
    tapinst = {(t["part"], t["tap"]): t["inst"] for t in tree["taps"]}

    def anc(i):
        out = []
        while i is not None:
            out.append(i)
            i = parent.get(i)
        return out
    anc_cache = {}

    def ancestors(i):
        if i not in anc_cache:
            anc_cache[i] = anc(i)
        return anc_cache[i]

    def common(i, j):
        sa = set(ancestors(i))
        for k in ancestors(j):
            if k in sa:
                return k
        return None
    ck = dict(params=tree["params"], cells=tree["cells"], htree_wire_um=tree["wire_um"], local_wire_um=tree["local_um"],
              corners={})
    for c, d in arr.items():
        ta = [d[t["inst"]] for t in tree["taps"] if t["inst"] in d]
        if ta:
            ck["corners"][c] = dict(taps=len(ta), insertion_min_ps=round(min(ta), 1), insertion_max_ps=round(max(ta), 1),
                                    insertion_mean_ps=round(sum(ta) / len(ta), 1), global_skew_ps=round(max(ta) - min(ta), 1))
    clog = B / "clock.log"
    if clog.is_file():
        ct = g2.parse_grt(clog.read_text(errors="replace"))
        ck["grt_overflow"] = ct.get("total_overflow")
        ck["grt_wirelength_um"] = ct.get("wirelength_um")
    for c in ("TT", "FF", "SS"):
        lg = B / f"sta_clock_{c}.log"
        if lg.is_file():
            t = lg.read_text(errors="replace")
            m = re.search(r"max slew.*?\n(.*?)(?:\n\n|\Z)", t, re.S)
            ck.setdefault("slew_cap_violations", {})[c] = len(re.findall(r"\(VIOLATED\)", t))
    res["clock"] = ck
    # ---------------- hops
    cal = load_calib(a.calib)
    wl = read_wl(B / "grt_g0_wl.csv")
    hop_rows = []
    pair_skew = {}
    with gzip.open(B / "nets.tsv.gz", "rt") as f:
        next(f)
        for ln in f:
            nm, kind, hpwl, nt, launch, capture, io = ln.rstrip("\n").split("\t")
            if kind == "io" or not launch or not capture:
                continue
            L0 = parse_reg(launch.split(";")[0])
            for cs in capture.split(";"):
                C0 = parse_reg(cs)
                Lr = wl.get(nm, 0.0)
                Lm = abs(L0["x"] - C0["x"]) + abs(L0["y"] - C0["y"])
                Lh = max(Lr if capture.count(";") == 0 else Lm * 1.1, Lm)
                hop_rows.append((nm, kind, L0, C0, Lh, Lr))
    tap_t = lambda r: tapinst.get((r["part"], r["tap"]))
    seam = defaultdict(lambda: dict(n=0))
    worst = {}
    stats = defaultdict(lambda: defaultdict(int))
    hist_len = defaultdict(int)
    neg_rows = []
    for nm, kind, L0, C0, Lh, Lr in hop_rows:
        ti, tj = tap_t(L0), tap_t(C0)
        sk = {}
        for c in ("TT", "FF", "SS"):
            d = arr.get(c, {})
            if ti in d and tj in d:
                cm = common(ti, tj)
                cv = d.get(cm, min(d[ti], d[tj])) if cm else 0.0
                ocv = OCV * ((d[ti] - cv) + (d[tj] - cv))
                sk[c] = (d[tj] - d[ti], ocv)
        if SETUP_C not in sk or HOLD_C not in sk:
            stats[kind]["no_clock"] += 1
            continue
        s_setup = hop_setup(cal, SETUP_C, Lh) + sk[SETUP_C][0] - sk[SETUP_C][1]
        s_setup_cal = hop_setup(cal, SETUP_C, Lh, True) + sk[SETUP_C][0] - sk[SETUP_C][1]
        s_hold = hop_hold(cal, HOLD_C, Lh) - sk[HOLD_C][0] - sk[HOLD_C][1]
        # INFO: kit insertion window (gen_phys.hold_in_min_ps = -insertion_tol, no clk->q / wire credit) vs die skew
        s_hold_b = res["insertion_tol_ps"] - sk[HOLD_C][0] - sk[HOLD_C][1]
        # GATE (owner 2026-10-24 decision 5: FF hold STA with the real trees decides, insertion_tol is guidance):
        # FF hold slack of the hop = calibrated flop -> repeated wire -> flop FF hold (clk->q + wire - t_hold - 25 ps
        # uncertainty) + the receiving kit's contracted seam-input hold padding (kits close FF hold with a min input
        # delay of -insertion_tol, gen_phys.hold_in_min_ps) - the die tree's capture-minus-launch tap skew
        s_hold_g = hop_hold(cal, HOLD_C, Lh) + res["insertion_tol_ps"] - sk[HOLD_C][0] - sk[HOLD_C][1]
        st = stats[kind]
        st["hops"] += 1
        st["setup_neg"] += s_setup < 0
        st["setup_cal_neg"] += s_setup_cal < 0
        st["hold_neg"] += s_hold < 0
        st["hold_budget_neg"] += s_hold_b < 0
        st["hold_gate_neg"] += s_hold_g < 0
        st["hold_gate_nom_neg"] += s_hold_g + sk[HOLD_C][1] < 0
        st["setup_nom_neg"] += s_setup + sk[SETUP_C][1] < 0             # nominal: no clock OCV
        st["hold_budget_nom_neg"] += s_hold_b + sk[HOLD_C][1] < 0
        st["hold_nom_neg"] += s_hold + sk[HOLD_C][1] < 0
        st["setup_lt_tol"] += s_setup < 2 * res["insertion_tol_ps"]
        st["hold_lt_tol"] += s_hold < 2 * res["insertion_tol_ps"]
        hist_len[int(Lh // 250) * 250] += 1
        for key, val in (("setup", s_setup), ("setup_cal", s_setup_cal), ("hold", s_hold), ("hold_budget", s_hold_b),
                         ("setup_nom", s_setup + sk[SETUP_C][1]), ("hold_gate_nom", s_hold_g + sk[HOLD_C][1])):
            k2 = (kind, key)
            if k2 not in worst or val < worst[k2][0]:
                worst[k2] = (val, nm, L0["part"], L0["pin"], C0["part"], C0["pin"], round(Lh, 1), round(Lr, 1),
                             {c: [round(v[0], 1), round(v[1], 1)] for c, v in sk.items()})
        g_setup, g_hold = s_setup + sk[SETUP_C][1], s_hold_g + sk[HOLD_C][1]      # gate values (nominal clock)
        if g_setup < 0 or g_hold < 0:
            neg_rows.append((round(g_setup, 1), round(g_hold, 1), kind, nm, L0["part"], L0["pin"], C0["part"],
                             C0["pin"], round(Lh, 1)))
        pk = (L0["part"], L0["tap"], C0["part"], C0["tap"])
        if L0["part"] != C0["part"] and pk not in pair_skew:
            pair_skew[pk] = {c: round(abs(v[0]) + v[1], 1) for c, v in sk.items()} | \
                            {c + "_nom": round(abs(v[0]), 1) for c, v in sk.items()}
        g = (L0["part"], C0["part"])
        e = seam[g]
        e["n"] += 1
        e["setup"] = min(e.get("setup", 1e9), round(s_setup, 1))
        e["setup_cal"] = min(e.get("setup_cal", 1e9), round(s_setup_cal, 1))
        e["hold"] = min(e.get("hold", 1e9), round(s_hold, 1))
        e["hold_budget"] = min(e.get("hold_budget", 1e9), round(s_hold_b, 1))
        e["hold_gate_nom"] = min(e.get("hold_gate_nom", 1e9), round(s_hold_g + sk[HOLD_C][1], 1))
        e["setup_nom"] = min(e.get("setup_nom", 1e9), round(s_setup + sk[SETUP_C][1], 1))
        e["max_len_um"] = max(e.get("max_len_um", 0), round(Lh, 1))
    res["sta"] = dict(model="calibrated repeated-hop table (calib) + die clock tree skew with CPPR, OCV "
                            f"{OCV:.0%} non-common; {SETUP_C} setup / {HOLD_C} hold (SS informational only); setup_cal = wire delay x {CAL_MARGIN:.3f} (REACH-M89)",
                      stats={k: dict(v) for k, v in stats.items()},
                      worst={f"{k[0]}.{k[1]}": dict(slack_ps=round(v[0], 1), net=v[1], launch=f"{v[2]}/{v[3]}",
                                                   capture=f"{v[4]}/{v[5]}", len_um=v[6], grt_len_um=v[7],
                                                   skew_ocv_ps=v[8]) for k, v in worst.items()},
                      hop_len_hist_250um=dict(sorted(hist_len.items())),
                      calib_reach_um={c: {ln: reach_of(rows) for ln, rows in cal[c].items()} for c in cal})
    # OWNER 2026-10-24 decisions 3 + 5: gate = hop STA TT setup / FF hold with 60 / 25 ps uncertainty on the die
    # tree (nominal arrivals; CPPR via the common tree node) + related launch/capture pair skew (CPPR) <= 80 ps at TT
    # and FF.  INFO only: margined slack (OCV / xtalk / IR), the kit insertion_tol hold window, the bare (unpadded)
    # flop-wire-flop hold and the global max-min tap spread.
    tot = lambda key: sum(v.get(key, 0) for v in stats.values())
    res["gate"] = dict(rule="hop STA TT setup / FF hold (60/25 ps, kit seam hold padding per contract) on the die "
                            "tree + related launch/capture pair skew with CPPR <= 80 ps at TT and FF; OCV, "
                            "insertion_tol window, bare hold and max-min spread are INFO",
                       setup_neg=tot("setup_nom_neg"), hold_neg=tot("hold_gate_nom_neg"),
                       info_hold_window_neg=tot("hold_budget_nom_neg"),
                       info_bare_hold_neg=tot("hold_nom_neg"),
                       info_ocv=dict(ocv=OCV, setup_neg=tot("setup_neg"), hold_neg=tot("hold_gate_neg"),
                                     hold_window_neg=tot("hold_budget_neg"), bare_hold_neg=tot("hold_neg")))
    sk_vals = defaultdict(list)
    for v in pair_skew.values():
        for c, x in v.items():
            sk_vals[c].append(x)
    # pair_skew: one entry per related (launch partition tap, capture partition tap) pair of a seam; "<C>_nom" is the
    # nominal |capture - launch| arrival (CPPR exact: the common tree path cancels), "<C>" adds the OCV INFO term
    res["seam_skew"] = {c: dict(pairs=len(v), max_ps=max(v), p99_ps=sorted(v)[int(0.99 * (len(v) - 1))],
                                over_80=sum(x > res["seam_skew_rule_ps"] for x in v)) for c, v in sk_vals.items() if v}
    res["pair_skew"] = {c: res["seam_skew"][c + "_nom"] for c in ("TT", "FF", "SS") if c + "_nom" in res["seam_skew"]}
    for c in ("TT", "FF"):
        k = res["pair_skew"].get(c)
        if k:
            res["gate"][f"pair_skew_over_80_{c}"] = k["over_80"]
            res["gate"][f"pair_skew_max_{c}_ps"] = k["max_ps"]
    res["gate"]["info_spread_ps"] = {c: v["global_skew_ps"] for c, v in ck["corners"].items()}
    g = res["gate"]
    g["verdict"] = "PASS" if not (g["setup_neg"] or g["hold_neg"] or
                                  any(v for k, v in g.items() if k.startswith("pair_skew_over_80"))) else "FAIL"
    g["note"] = "budget/abstract trial: hop = calibrated repeated wire, partitions at 250 ps common latency; not signoff"
    wp = sorted(pair_skew.items(), key=lambda kv: -max(kv[1].get("TT_nom", 0), kv[1].get("FF_nom", 0)))[:20]
    res["seam_skew_worst"] = [dict(launch=f"{k[0]}/{k[1]}", capture=f"{k[2]}/{k[3]}", **v) for k, v in wp]
    res["seams_worst"] = [dict(src=g[0], dst=g[1], **e) for g, e in sorted(seam.items(), key=lambda kv: kv[1]["setup"])[:40]]
    res["seams_worst_hold"] = [dict(src=g[0], dst=g[1], **e) for g, e in sorted(seam.items(), key=lambda kv: kv[1]["hold_gate_nom"])[:20]]
    neg_rows.sort()
    with gzip.open(B / "hops_negative.tsv.gz", "wt") as f:
        f.write(f"setup_{SETUP_C}_nom\thold_{HOLD_C}_gate_nom\tkind\tnet\tlaunch_part\tlaunch_pin\tcapture_part\tcapture_pin\tlen_um\n")
        for r in neg_rows:
            f.write("\t".join(map(str, r)) + "\n")
    # ---------------- G2 comparison
    if a.g2 and Path(a.g2).is_file():
        res["g2_compare"] = g2_compare(P, json.loads(Path(a.g2).read_text()), rt.get("g0", {}))
    # ---------------- IR
    irj = (Path(a.ir_dir) if a.ir_dir else B.parent / (B.name + "_ir")) / "ir.json"
    if irj.is_file():
        res["ir"] = json.loads(irj.read_text())
    out = Path(a.out) if a.out else B
    out.mkdir(parents=True, exist_ok=True)
    (out / "die_trial.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("route", "clock", "seam_skew") if k in res}, indent=1)[:4000])
    print(json.dumps(res["sta"]["stats"], indent=1))
    return res


def reach_of(rows):
    """first L where the setup slack crosses 0 (raw table)."""
    for a, b in zip(rows, rows[1:]):
        if a[1] >= 0 > b[1]:
            return round(a[0] + (b[0] - a[0]) * a[1] / (a[1] - b[1]), 1)
    return None


def worst_windows(P, csv, win):
    """aggregate the GRT routing heatmap (gcell usage %, all layers incl. blocked capacity) into win x win um windows;
    -> top windows with the partition under their centre + the die-wide empty-gcell baseline."""
    if not Path(csv).is_file():
        return None
    agg = defaultdict(lambda: [0.0, 0])
    mx = []
    vals = []
    with open(csv) as f:
        next(f)
        for ln in f:
            x0, y0, x1, y1, v = ln.split(",")
            x0, y0, v = float(x0), float(y0), float(v)
            k = (int(x0 // win), int(y0 // win))
            agg[k][0] += v
            agg[k][1] += 1
            vals.append(v)
            mx.append((v, x0, y0))
    vals.sort()
    base = vals[len(vals) // 10]
    rects = [(n, P.rect(n)) for n in P.parts]

    def part_at(x, y):
        for n, (a, b, c, d) in rects:
            if a <= x < c and b <= y < d:
                return n
        return None
    w = sorted(((s / n, k) for k, (s, n) in agg.items()), reverse=True)[:15]
    mx.sort(reverse=True)
    return dict(window_um=win, gcell_p10_pct=round(base, 2), gcell_p50_pct=round(vals[len(vals) // 2], 2),
                gcell_p99_pct=round(vals[int(0.99 * (len(vals) - 1))], 2), gcell_max_pct=round(vals[-1], 2),
                gcells_ge_100=sum(v >= 100 for v in vals),
                top_windows=[dict(x_um=k[0] * win, y_um=k[1] * win, mean_pct=round(v, 2),
                                  part=part_at(k[0] * win + win / 2, k[1] * win + win / 2)) for v, k in w],
                top_gcells=[dict(x_um=x, y_um=y, pct=round(v, 1), part=part_at(x, y)) for v, x, y in mx[:10]])


def overflow_by_part(P, rpt):
    """GRT congestion report (overflowing gcells) -> count per partition and per layer."""
    if not Path(rpt).is_file():
        return None
    txt = Path(rpt).read_text(errors="replace")
    by_part, by_layer = defaultdict(int), defaultdict(int)
    rects = [(n, P.rect(n)) for n in P.parts]
    n = 0
    # this GRT build writes "violation type: <Horizontal|Vertical> congestion ... bbox = (..) - (..) on Layer -"
    for m in re.finditer(r"violation type: (\w+)[^\n]*\n(?:[^\n]*\n)*?\s*bbox = \(\s*([-\d.]+),\s*([-\d.]+)\s*\)\s*-\s*"
                         r"\(\s*([-\d.]+),\s*([-\d.]+)\s*\) on Layer (\S+)", txt):
        x = (float(m.group(2)) + float(m.group(4))) / 2
        y = (float(m.group(3)) + float(m.group(5))) / 2
        n += 1
        by_layer[m.group(6) if m.group(6) != "-" else m.group(1)] += 1
        for nm, (a, b, c, d) in rects:
            if a <= x < c and b <= y < d:
                by_part[nm] += 1
                break
    return dict(entries=n, by_layer=dict(by_layer),
                top_parts=sorted(by_part.items(), key=lambda kv: -kv[1])[:20])


def g2_compare(P, g2r, rt):
    """G2 FT probes (partition-type congestion in isolation) vs the die route over the same types' instances."""
    out = {}
    wins = (rt.get("windows") or {}).get("top_windows", [])
    ovf = dict((rt.get("overflow_by_part") or {}).get("top_parts", []))
    for k, v in g2r.get("probes", {}).items():
        lay = {l: x["usage_pct"] for l, x in v.get("layers", {}).items() if x.get("resource")}
        row = dict(g2_overflow=v.get("total_overflow"), g2_max_layer_pct=max(lay.values()) if lay else None)
        if k.startswith("part_"):
            tn = k[5:]
            inst = [n for n, p in P.parts.items() if p["type"] == tn]
            row["instances"] = len(inst)
            row["die_overflow_gcells"] = sum(ovf.get(n, 0) for n in inst)
            row["die_top_windows"] = sum(1 for w in wins if w["part"] in inst)
        out[k] = row
    return out



# --------------------------------------------------------------------------------------------------- IR (PDNSim)
TECH_JSON = HERE.parent.parent / "configs" / "hardware" / "technology.json"
ASAP7_RC = [("M1", 7.04175e-02, 0.018), ("M2", 2.97127e-02, 0.018), ("M3", 3.12870e-02, 0.018),
            ("M4", 1.80365e-02, 0.024), ("M5", 1.89935e-02, 0.024), ("M6", 1.18796e-02, 0.032),
            ("M7", 1.25096e-02, 0.032), ("M8", 8.44765e-03, 0.04), ("M9", 8.89556e-03, 0.04)]   # setRC.tcl kOhm/um
ASAP7_VIA_R = [("V1", 1.72e-2), ("V2", 1.72e-2), ("V3", 1.72e-2), ("V4", 1.18e-2), ("V5", 1.18e-2), ("V6", 8.2e-3),
               ("V7", 8.2e-3), ("V8", 6.3e-3), ("V9", 6.3e-3)]                                  # setRC.tcl kOhm/cut
IR_K = 4           # PG coarsening: width x K, pitch x K (same metal fraction = same sheet conductance per layer)
VDD_V = 0.7


def part_power(P, raw, plan_dir):
    """{partition: W} ESTIMATE: clock network (technology.json clock_energy_j_per_mm2_per_cycle x f) + logic leakage
    (static_leakage_w_per_mm2.logic) over the partition area, + switching = the die clock power redistributed by the
    partition's share of the die's estimated cells (cells.py) -- datapath-heavy partitions run hotter."""
    import cells as C
    t = json.loads(TECH_JSON.read_text())["power"]
    ck = t["clock_energy_j_per_mm2_per_cycle"]["value"] * 1e12 / P.die["period_ps"]       # W / mm2
    lk = t["static_leakage_w_per_mm2"]["logic"]["value"]
    est, _ = C.estimate(raw, plan_dir=plan_dir)
    cell = {}
    for n, p in P.parts.items():
        e = est.get(p["type"])
        cell[n] = (e[0] if isinstance(e, (list, tuple)) else (e.get("cells") if isinstance(e, dict) else e)) or 0
    area = {n: (lambda r: (r[2] - r[0]) * (r[3] - r[1]) / 1e6)(P.rect(n)) for n in P.parts}
    A, N = sum(area.values()), max(1, sum(cell.values()))
    pw = {n: area[n] * (ck + lk) + ck * A * cell[n] / N for n in P.parts}
    return pw, dict(clock_w_mm2=round(ck, 4), leak_w_mm2=lk, switching="die clock power x cell share",
                    total_w=round(sum(pw.values()), 1), area_mm2=round(A, 1), cells=N)


def cmd_ir(a):
    raw = S.load(a.plan)
    P = S.Plan(raw)
    out = Path(a.out)
    (out / "lef").mkdir(parents=True, exist_ok=True)
    pw, basis = part_power(P, raw, Path(a.plan).resolve().parent)
    if a.w_mm2:
        sc = a.w_mm2 * basis["area_mm2"] / basis["total_w"]
        pw = {n: v * sc for n, v in pw.items()}
        basis.update(scaled_to_w_mm2=a.w_mm2, total_w=round(sum(pw.values()), 1))
    K = IR_K
    # the load: power tiles (2 x 2 coarse PG pitches) over every partition, each a small macro with its own M7 VDD /
    # VSS stripe pair (the partition M7 PG, coarsened), current = the partition's power density x tile area
    # (PSM attaches an instance's current at one point: one macro per partition would be a point load).
    tile = a.tile_pitches * 8.64 * K
    NLV = 64
    dens = {n: pw[n] / ((lambda r: (r[2] - r[0]) * (r[3] - r[1]))(P.rect(n))) for n in P.parts}   # W / um2
    dmax = max(dens.values())
    lvl = {n: max(1, round(NLV * d / dmax)) for n, d in dens.items()}
    tiles = []
    rects = sorted((n, P.rect(n)) for n in P.parts)
    for i in range(int(P.W // tile)):
        for j in range(int(P.H // tile)):
            cx, cy = (i + 0.5) * tile, (j + 0.5) * tile
            for n, (x0, y0, x1, y1) in rects:
                if x0 <= cx < x1 and y0 <= cy < y1:
                    tiles.append((f"t_{i}_{j}", lvl[n], i * tile, j * tile))
                    break
    # scale the level power so that every partition's total is exact on average over the die
    want = sum(pw.values())
    got = sum(dmax * lv / NLV * tile * tile for _, lv, _, _ in tiles)
    fix = want / got if got else 1.0
    R = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    L = ['library (trial_ir) {', '  delay_model : table_lookup ;', '  time_unit : "1ps" ;', '  voltage_unit : "1V" ;',
         '  current_unit : "1mA" ;', '  leakage_power_unit : "1mW" ;', '  capacitive_load_unit (1, ff) ;',
         '  pulling_resistance_unit : "1kohm" ;', f'  nom_voltage : {VDD_V} ;',
         f'  voltage_map (VDD, {VDD_V}) ;', '  voltage_map (VSS, 0) ;']
    for lv in sorted({t[1] for t in tiles}):
        m = f"irtile_{lv}"
        R += [f"MACRO {m}", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;", f"  SIZE {tile:.4f} BY {tile:.4f} ;"]
        for net, j in (("VDD", 0), ("VSS", 1)):
            wid = 0.288 * K
            R += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {'POWER' if net == 'VDD' else 'GROUND'} ;", "    PORT"]
            for c in (tile / 8 + j * tile / 4, 5 * tile / 8 + j * tile / 4):     # = the die M7 stripes (below)
                R += ["      LAYER M7 ;", f"        RECT {c:.4f} 0 {c + wid:.4f} {tile:.4f} ;"]
            R += ["    END", f"  END {net}"]
        R += [f"END {m}"]
        mw = dmax * lv / NLV * tile * tile * fix * 1e3
        L += [f'  cell ({m}) {{', '    area : 1 ;', f'    cell_leakage_power : {mw:.6f} ;',
              '    pg_pin (VDD) { voltage_name : VDD ; pg_type : primary_power ; }',
              '    pg_pin (VSS) { voltage_name : VSS ; pg_type : primary_ground ; }', '  }']
    R += ["END LIBRARY", ""]
    L.append('}')
    (out / "lef" / "irtiles.lef").write_text("\n".join(R))
    lefs = ["irtiles.lef"]
    (out / "trial_ir.lib").write_text("\n".join(L) + "\n")
    D = ["VERSION 5.8 ;", 'DIVIDERCHAR "/" ;', 'BUSBITCHARS "[]" ;', f"DESIGN {sid(P.name)}_ir ;",
         f"UNITS DISTANCE MICRONS {DBU} ;", f"DIEAREA ( 0 0 ) ( {dbu(P.W)} {dbu(P.H)} ) ;",
         f"COMPONENTS {len(tiles)} ;"]
    for nm, lv, x, y in tiles:
        D.append(f"- {nm} irtile_{lv} + FIXED ( {dbu(x)} {dbu(y)} ) N ;")
    D += ["END COMPONENTS", "END DESIGN", ""]
    (out / "ir.def").write_text("\n".join(D))
    basis.update(tiles=len(tiles), tile_um=tile, levels=NLV, tile_power_fix=round(fix, 4))
    g = P.die.get("pg", {}).get("grid") or []
    pdn = ["add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power",
           "add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground", "global_connect",
           "set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}",
           "define_pdn_grid -name {top} -voltage_domains {CORE}"]
    for st in g:
        k = max(1, len(st.get("nets", ["VDD", "VSS"])))
        pitch = st["pitch_um"] * K
        wid = st["width_um"] * K
        pdn.append(f"add_pdn_stripe -grid {{top}} -layer {{{st['layer']}}} -width {{{wid:g}}} "
                   f"-spacing {{{pitch / k - wid:g}}} -pitch {{{pitch:g}}} -offset {{{st['offset_um'] * K:g}}}")
    pdn.append("add_pdn_connect -grid {top} -layers {M8 M9}")
    # load tiles: their M7 pins (the partition M7 PG, coarsened) strapped to the die M8 grid
    pdn += ["define_pdn_grid -name {parts} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {0 0 0 0} "
            "-default", "add_pdn_connect -grid {parts} -layers {M7 M8}"]
    (out / "pdn.tcl").write_text("\n".join(pdn) + "\n")
    tcl = [f"read_lef {TECH_LEF}", f"read_lef {SC_LEF}"] + [f"read_lef /work/lef/{x}" for x in lefs] + \
          ["read_liberty /work/trial_ir.lib", "read_def /work/ir.def", "source /work/make_tracks.tcl",
           "set t0 [clock seconds]", "source /work/pdn.tcl", "pdngen", "puts \"OT_T_PDN [expr {[clock seconds]-$t0}]\"", "write_db /work/ir_pdn.odb",
           "foreach n {VDD VSS} { if {[catch {check_power_grid -net $n -error_file /work/pg_$n.rpt} e]} "
           "{ puts \"OT_PG_CHECK_FAIL $n $e\" } else { puts \"OT_PG_CHECK_OK $n\" } }",
           f"source {PLAT}/setRC.tcl",
           # the ASAP7 tech LEF has no RESISTANCE: give PSM the setRC.tcl values as Ohm / square (kOhm/um x min width
           # x 1000) and Ohm / cut, the same RC estimate_parasitics uses
           ] + [f"[[ord::get_db_tech] findLayer {ln}] setResistance {r * w * 1000:.6g}" for ln, r, w in ASAP7_RC] + \
          [f"[[ord::get_db_tech] findLayer {v}] setResistance {r * 1000:.6g}" for v, r in ASAP7_VIA_R] + [
           f"set_pdnsim_net_voltage -net VDD -voltage {VDD_V}", "set_pdnsim_net_voltage -net VSS -voltage 0",
           "report_power",
           # C4 bumps: a.bump_um area array, VDD / VSS checkerboard (-source_type BUMPS of this build drops its sources
           # on the die's left edge only: explicit source files instead)
           "foreach n {VDD VSS} { if {[catch {analyze_power_grid -net $n -vsrc /work/bumps_$n.vsrc -error_file /work/psm_$n.rpt "
           "-voltage_file /work/psm_$n.csv} e]} { puts \"OT_PSM_FAIL $n $e\" } else { puts \"OT_PSM_OK $n\" } }",
           "puts \"OT_T_PSM [expr {[clock seconds]-$t0}]\"", "puts OT_DONE"]
    (out / "ir.tcl").write_text("\n".join(tcl) + "\n")
    b = a.bump_um
    nb = {"VDD": 0, "VSS": 0}
    for net, par, v in (("VDD", 0, VDD_V), ("VSS", 1, 0.0)):
        rows = []
        for i in range(int(P.W // b)):
            for j in range(int(P.H // b)):
                if (i + j) % 2 == par:
                    rows.append(f"{(i + 0.5) * b:.3f},{(j + 0.5) * b:.3f},{b / 5:g},{v:g}")
        nb[net] = len(rows)
        (out / f"bumps_{net}.vsrc").write_text("\n".join(rows) + "\n")
    (out / "make_tracks.tcl").write_text(die_tracks_tcl(P))
    write_run(out, "ir", "/usr/bin/time -v openroad -threads $CPUS -exit /work/ir.tcl > /work/ir.log 2>&1; "
              "RC=\\$?; echo EXIT \\$RC >> /work/ir.log;", 128, 16)
    (out / "ir_power.json").write_text(json.dumps(dict(basis=basis, parts={n: round(v, 4) for n, v in pw.items()},
                                                       coarsen=IR_K, tile_um=tile, ntiles=len(tiles), vdd_v=VDD_V, bump_um=a.bump_um,
                                                       bumps=nb, bump_pattern="VDD/VSS checkerboard"), indent=1) + "\n")
    print(json.dumps(basis))


def ir_summary(d, P=None):
    """PDNSim results: worst / mean IR per net, per partition worst, from ir.log + psm_<net>.csv."""
    d = Path(d)
    txt = (d / "ir.log").read_text(errors="replace") if (d / "ir.log").is_file() else ""
    res = dict(log={})
    for net in ("VDD", "VSS"):
        m = re.search(r"Net\s*:\s*" + net + r".*?Worstcase voltage\s*:\s*([-\d.e]+)\s*V.*?Average voltage\s*:\s*([-\d.e]+)"
                      r"\s*V.*?Average IR drop\s*:\s*([-\d.e]+)\s*V.*?Worstcase IR drop\s*:\s*([-\d.e]+)\s*V", txt, re.S)
        if m:
            res[net] = dict(worst_v=float(m.group(1)), avg_v=float(m.group(2)), avg_ir_mv=round(float(m.group(3)) * 1e3, 2),
                            worst_ir_mv=round(float(m.group(4)) * 1e3, 2))
    res["pg_check"] = re.findall(r"OT_PG_CHECK_(\w+) (\w+)", txt)
    res["psm"] = re.findall(r"OT_PSM_(\w+) (\w+)", txt)
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", txt)
    res["peak_rss_gb"] = round(int(m.group(1)) / 1048576, 1) if m else None
    m = re.search(r"OT_T_PSM (\d+)", txt)
    res["psm_seconds"] = int(m.group(1)) if m else None
    m = re.findall(r"^EXIT (\d+)", txt, re.M)
    res["exit"] = int(m[-1]) if m else None
    if P is not None:
        # per-partition worst drop from the per-tile PSM voltages (tile origin -> partition)
        rects = sorted((n, P.rect(n)) for n in P.parts)
        per = defaultdict(dict)
        for net in ("VDD", "VSS"):
            f = d / f"psm_{net}.csv"
            if not f.is_file():
                continue
            with open(f) as fh:
                next(fh)
                for ln in fh:
                    q = ln.split(",")
                    x, y, v = float(q[3]), float(q[4]), float(q[5])
                    drop = (VDD_V - v if net == "VDD" else v) * 1e3
                    for n, (x0, y0, x1, y1) in rects:
                        if x0 <= x < x1 and y0 <= y < y1:
                            per[n][net] = max(per[n].get(net, 0.0), drop)
                            break
        tot = {n: round(v.get("VDD", 0) + v.get("VSS", 0), 1) for n, v in per.items()}
        res["worst_parts_mv"] = [dict(part=n, vdd=round(per[n].get("VDD", 0), 1), vss=round(per[n].get("VSS", 0), 1),
                                      total=t) for n, t in sorted(tot.items(), key=lambda kv: -kv[1])[:20]]
        res["parts_over_5pct_total"] = sum(t > 0.05 * VDD_V * 1e3 for t in tot.values())
        res["parts"] = len(tot)
    return res



# --------------------------------------------------------------------------------------------------- render
def _base(P, ax, label=True, fs=4):
    from matplotlib.patches import Rectangle
    import matplotlib.cm as cm
    types = sorted(P.types)
    import matplotlib
    cmap = matplotlib.colormaps["tab20"]
    for n, p in P.parts.items():
        x0, y0, x1, y1 = P.rect(n)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=True, fc=cmap(types.index(p["type"]) % 20),
                               alpha=0.25, ec="#555", lw=0.4))
        if label:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, n, ha="center", va="center", fontsize=fs, color="#333")
    ax.set_xlim(-100, P.W + 100)
    ax.set_ylim(-100, P.H + 100)
    ax.set_aspect("equal")


def _fig(P, w=14):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(w, w * P.H / P.W + 0.8))
    return plt, fig, ax


def cmd_render(a):
    """die review images: floorplan + ft lane bundles + die IO; clock tree (TT arrival); congestion; IR; hop slack."""
    B = Path(a.dir)
    info = json.loads((B / "build.json").read_text())
    P = S.Plan(S.load(info["plan"]))
    out = Path(a.out or B / "png")
    out.mkdir(parents=True, exist_ok=True)
    from matplotlib.patches import Rectangle
    import matplotlib.colors as mc
    made = []
    # 1. floorplan + bundles (one line per (launch part, capture part) of ft hops, width ~ bits) + die io windows
    plt, fig, ax = _fig(P)
    _base(P, ax)
    bund = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0.0, 0.0])
    with gzip.open(B / "nets.tsv.gz", "rt") as f:
        next(f)
        for ln in f:
            nm, kind, hpwl, nt, launch, capture, io = ln.rstrip("\n").split("\t")
            if kind != "ft" or not launch or not capture:
                continue
            L0 = parse_reg(launch.split(";")[0])
            C0 = parse_reg(capture.split(";")[0])
            b = bund[(L0["part"], C0["part"])]
            b[0] += 1
            b[1] += L0["x"]; b[2] += L0["y"]; b[3] += C0["x"]; b[4] += C0["y"]
            b[5] = max(b[5], float(hpwl))
    mxb = max([v[0] for v in bund.values()] or [1])
    for (lp, cp), v in bund.items():
        n = v[0]
        xs, ys, xe, ye = v[1] / n, v[2] / n, v[3] / n, v[4] / n
        col = "#c0392b" if v[5] > 900 else ("#e67e22" if v[5] > 600 else "#2c3e50")
        ax.plot([xs, xe], [ys, ye], color=col, lw=0.3 + 4 * n / mxb, alpha=0.7)
    dio = Path(info["plan"]).parent / "die_io.json"
    if dio.is_file():
        for w in json.loads(dio.read_text()):
            x0, y0, x1, y1 = w["rect_um"]
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="m", hatch="//", lw=0.8))
    ax.plot([], [], color="#c0392b", lw=2, label="ft hop bundle, max hop > 900 um")
    ax.plot([], [], color="#e67e22", lw=2, label="600-900 um")
    ax.plot([], [], color="#2c3e50", lw=2, label="<= 600 um")
    ax.legend(loc="upper right", fontsize=7)
    ax.set_title(f"{P.name}: partitions + feedthrough hop bundles (line width ~ bits, {sum(v[0] for v in bund.values())} "
                 "ft hops) + die IO windows (magenta)", fontsize=9)
    fig.savefig(out / "floorplan_lanes.png", dpi=a.dpi, bbox_inches="tight")
    plt.close(fig)
    made.append("floorplan_lanes.png")
    # 2. clock tree coloured by --corner (TT) arrival at the segment's child node + taps
    tree = json.loads((B / "clock_tree.json").read_text())
    arr = load_arrivals(B)
    d = arr.get(a.corner, {})
    if d:
        plt, fig, ax = _fig(P)
        _base(P, ax, label=False)
        ta = [d.get(t["inst"]) for t in tree["taps"]]
        ta = [x for x in ta if x is not None]
        norm = mc.Normalize(min(ta), max(ta))
        import matplotlib.cm as cm
        for (x0, y0, x1, y1, lev, lnm) in tree["segments"]:
            ax.plot([x0, x1], [y0, y1], color="#1f5fbf" if lnm == "M9" else "#c0392b",
                    lw=max(0.3, 2.5 - 0.25 * lev), alpha=0.8)
        sc = ax.scatter([t["x"] for t in tree["taps"] if t["inst"] in d], [t["y"] for t in tree["taps"] if t["inst"] in d],
                        c=[d[t["inst"]] for t in tree["taps"] if t["inst"] in d], s=4, cmap="viridis", norm=norm, zorder=5)
        fig.colorbar(sc, ax=ax, fraction=0.03, label=f"tap insertion {a.corner} (ps)")
        ax.set_title(f"{P.name}: die clock H-tree (M8 red / M9 blue) + partition taps coloured by {a.corner} insertion "
                     f"({min(ta):.0f}-{max(ta):.0f} ps)", fontsize=9)
        fig.savefig(out / "clock_tree.png", dpi=a.dpi, bbox_inches="tight")
        plt.close(fig)
        made.append("clock_tree.png")
    # 3. congestion heatmap
    hm = B / "grt_g0_heatmap.csv"
    if hm.is_file():
        import numpy as np
        rows = np.loadtxt(hm, delimiter=",", skiprows=1)
        g = rows[0, 2] - rows[0, 0]
        nx, ny = int(round(P.W / g)) + 1, int(round(P.H / g)) + 1
        img = np.full((ny, nx), np.nan)
        ix = np.clip((rows[:, 0] / g).astype(int), 0, nx - 1)
        iy = np.clip((rows[:, 1] / g).astype(int), 0, ny - 1)
        img[iy, ix] = rows[:, 4]
        # every gcell carries the reserved (PG / adjustment) baseline: show the excess over the median, max-pooled
        # over k x k gcells so isolated hot gcells stay visible at die scale; partitions as outlines only
        k = 5
        base = np.nanmedian(img)
        ny2, nx2 = ny // k, nx // k
        pool = np.nanmax(img[:ny2 * k, :nx2 * k].reshape(ny2, k, nx2, k), axis=(1, 3)) - base
        pool = np.ma.masked_less(pool, 2.0)
        plt, fig, ax = _fig(P)
        ax.set_facecolor("#f4f4f4")
        im = ax.imshow(pool, origin="lower", extent=(0, nx2 * k * g, 0, ny2 * k * g), cmap="inferno_r",
                       vmin=0, vmax=max(30.0, 100.0 - base, float(pool.max())), interpolation="nearest", zorder=2)
        for n in P.parts:
            x0, y0, x1, y1 = P.rect(n)
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.3, ec="#3060a0", zorder=3))
        ax.set_xlim(0, P.W); ax.set_ylim(0, P.H)
        hot = np.argwhere(img > 100.0)
        if len(hot):
            ax.scatter((hot[:, 1] + 0.5) * g, (hot[:, 0] + 0.5) * g, s=6, c="cyan", marker="x", zorder=4,
                       label=f"{len(hot)} gcells > 100 %")
            ax.legend(loc="upper right", fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.03,
                     label=f"GRT usage above the median gcell ({base:.0f} % = reserved baseline), max over {k * g:.0f} um")
        ax.set_title(f"{P.name}: die GRT congestion (G0 capacity model: M4-M7 at 25 %, M8/M9 at cut_avail)", fontsize=9)
        fig.savefig(out / "congestion.png", dpi=a.dpi, bbox_inches="tight")
        plt.close(fig)
        made.append("congestion.png")
    # 3b. no heatmap (WL / heatmap dump not finished): overflowing gcells from the GRT congestion report
    rpt = B / "grt_g0_congestion.rpt"
    if not hm.is_file() and rpt.is_file():
        pts = []
        txt = rpt.read_text(errors="replace")
        for m in re.finditer(r"violation type: (\w+)[^\n]*\n(?:[^\n]*\n)*?\s*comment: [^\n]*congestion:(\d+)\s*\n"
                             r"\s*bbox = \(\s*([-\d.]+),\s*([-\d.]+)\s*\)\s*-\s*\(\s*([-\d.]+),\s*([-\d.]+)", txt):
            pts.append(((float(m.group(3)) + float(m.group(5))) / 2, (float(m.group(4)) + float(m.group(6))) / 2,
                        m.group(1), int(m.group(2))))
        if pts:
            plt, fig, ax = _fig(P)
            _base(P, ax, label=False)
            for kind, col in (("Horizontal", "#d62728"), ("Vertical", "#1f77b4")):
                q = [p for p in pts if p[2] == kind]
                if q:
                    ax.scatter([p[0] for p in q], [p[1] for p in q], s=[2 + 0.4 * p[3] for p in q], c=col, alpha=0.6,
                               marker="s", zorder=4, label=f"{kind} overflow gcells: {len(q)} (sum {sum(p[3] for p in q)})")
            ax.legend(loc="upper right", fontsize=7)
            ax.set_title(f"{P.name}: die GRT overflowing gcells from the congestion report (marker ~ overflow tracks)",
                         fontsize=9)
            fig.savefig(out / "congestion_overflow.png", dpi=a.dpi, bbox_inches="tight")
            plt.close(fig)
            made.append("congestion_overflow.png")
    # 4. IR map
    irc = (Path(a.ir_dir) if a.ir_dir else B.parent / (B.name + "_ir")) / "psm_VDD.csv"
    if irc.is_file():
        import numpy as np
        xs, ys, vs = [], [], []
        with open(irc) as f:
            next(f)
            for ln in f:
                p = ln.split(",")
                xs.append(float(p[3])); ys.append(float(p[4])); vs.append(float(p[5]))
        plt, fig, ax = _fig(P)
        drop = (VDD_V - np.array(vs)) * 1e3
        xs, ys = np.array(xs), np.array(ys)
        ux = np.unique(xs)
        t = float(np.median(np.diff(ux))) if len(ux) > 1 else 100.0
        nx, ny = int(P.W // t) + 1, int(P.H // t) + 1
        img = np.full((ny, nx), np.nan)
        ix = np.clip((xs // t).astype(int), 0, nx - 1)
        iy = np.clip((ys // t).astype(int), 0, ny - 1)
        img[iy, ix] = np.fmax(img[iy, ix], drop) if False else drop
        sc = ax.imshow(img, origin="lower", extent=(0, nx * t, 0, ny * t), cmap="magma_r", interpolation="nearest",
                       vmin=0, vmax=float(np.nanmax(img)), zorder=2)
        for n in P.parts:
            x0, y0, x1, y1 = P.rect(n)
            ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.3, ec="#20a0ff", zorder=3))
        ax.set_xlim(0, P.W); ax.set_ylim(0, P.H)
        fig.colorbar(sc, ax=ax, fraction=0.03, label="static VDD IR drop (mV)")
        ax.set_title(f"{P.name}: PDNSim static VDD drop, die M8/M9 grid over partition M7 (coarsened x{IR_K}), "
                     f"worst {drop.max():.1f} mV", fontsize=9)
        fig.savefig(out / "ir_vdd.png", dpi=a.dpi, bbox_inches="tight")
        plt.close(fig)
        made.append("ir_vdd.png")
    # 5. negative-slack hops
    neg = B / "hops_negative.tsv.gz"
    if neg.is_file():
        tapj = json.loads((B / "taps.json").read_text())
        plt, fig, ax = _fig(P)
        _base(P, ax, label=False)
        cnt = defaultdict(int)
        with gzip.open(neg, "rt") as f:
            next(f)
            for ln in f:
                r = ln.rstrip("\n").split("\t")
                cnt[(r[4], r[6], "S" if float(r[0]) < 0 else "H")] += 1
        for (lp, cp, k), n in cnt.items():
            a0, a1 = P.rect(lp), P.rect(cp)
            ax.plot([(a0[0] + a0[2]) / 2, (a1[0] + a1[2]) / 2], [(a0[1] + a0[3]) / 2, (a1[1] + a1[3]) / 2],
                    color="r" if k == "S" else "b", lw=0.5 + 3 * math.log10(1 + n) / 4, alpha=0.7)
        ax.plot([], [], color="r", label=f"setup {SETUP_C} < 0 (partition pair)")
        ax.plot([], [], color="b", label=f"hold {HOLD_C} < 0 (gate: kit seam padding, nominal tree)")
        ax.legend(loc="upper right", fontsize=7)
        ax.set_title(f"{P.name}: partition pairs with negative die-STA hops (line width ~ log count)", fontsize=9)
        fig.savefig(out / "sta_negative.png", dpi=a.dpi, bbox_inches="tight")
        plt.close(fig)
        made.append("sta_negative.png")
    print("\n".join(str(out / m) for m in made))


# --------------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("plan")
    b.add_argument("--out", required=True)
    b.add_argument("--mem", type=int, default=256)
    b.add_argument("--cpus", type=int, default=16)
    b.add_argument("--clock-only", action="store_true", help="rebuild only the die clock tree (clock.def / json)")
    c = sub.add_parser("calib")
    c.add_argument("--out", required=True)
    r = sub.add_parser("report")
    r.add_argument("dir")
    r.add_argument("--calib", required=True)
    r.add_argument("--plan")
    r.add_argument("--g2")
    r.add_argument("--out")
    r.add_argument("--window", type=float, default=250.0)
    r.add_argument("--ir-dir", help="finished ir run dir with ir.json (default DIR_ir)")
    i = sub.add_parser("ir")
    i.add_argument("plan")
    i.add_argument("--out", required=True)
    i.add_argument("--w-mm2", type=float)
    i.add_argument("--bump-um", type=float, default=150.0)
    i.add_argument("--tile-pitches", type=int, default=2,
                   help="power tile = N coarse PG pitches (8.64 um x IR_K); larger -> fewer pdngen instance grids")
    q = sub.add_parser("irsum", help="summarise a finished ir run dir -> DIR/ir.json")
    q.add_argument("dir")
    q.add_argument("plan")
    v = sub.add_parser("render")
    v.add_argument("dir")
    v.add_argument("--out")
    v.add_argument("--corner", default="TT")
    v.add_argument("--ir-dir", help="finished ir run dir (default DIR_ir)")
    v.add_argument("--dpi", type=int, default=110)
    a = ap.parse_args(argv)
    if a.cmd == "render":
        cmd_render(a)
    elif a.cmd == "ir":
        cmd_ir(a)
    elif a.cmd == "irsum":
        r = ir_summary(a.dir, S.Plan(S.load(a.plan)))
        r["power"] = json.loads((Path(a.dir) / "ir_power.json").read_text()) if (Path(a.dir) / "ir_power.json").is_file() else None
        (Path(a.dir) / "ir.json").write_text(json.dumps(r, indent=1) + "\n")
        print(json.dumps({k: v for k, v in r.items() if k not in ("worst_parts_mv", "power")}))
    elif a.cmd == "report":
        cmd_report(a)
    elif a.cmd == "build":
        cmd_build(a)
    elif a.cmd == "calib":
        cmd_calib(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
