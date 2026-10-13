#!/usr/bin/env python3
"""[vm8cp] per-net-bit reach audit of the VM8 control plane (25 die-placed tiles, 52 registered die-level hops).

candidate_geometry.py bounds each hop from the two ENDS of the packed pin range of a port.  This tool follows the die
netlist hfd_vm_cp.sv bit by bit and measures, for every net bit, the Manhattan distance from the driver pin to every
load pin (and the HPWL of the whole net), with each pin at

  * the exported LEF pin shape of the kit, when a view exists (repo physical/ref_tile/<kit>/views/<top>/<top>.lef or
    --lef MASTER=PATH), else
  * the generator's own pin plan: the kit's kit.env --pin-region list is parsed by tools/run_abi3_physical.py
    (resolve_floorplan) and turned into Tcl by its io_constraints_tcl -- the very text the route sources -- which is then
    EXECUTED under tclsh with odb / place_pin stubs.  Nothing about bit order or spacing is re-derived here.

Planning evidence only: pin-to-pin Manhattan distance is a LOWER bound of the routed wire (no detour, no layer change,
no track snap of a planned pin; the LEF cross-check below measures the snap).  It is not routed reach and not a closure.

    python3 bit_reach.py                       # candidate origins (candidate_geometry.py), current kits
    python3 bit_reach.py --kit vm_cp_fw0=vm_cp_fw0_m5 --lef vm_cp_rwb=/path/vm_cp_rwb.lef --origin u_rt0=172.8,1373.76
    python3 bit_reach.py --check               # self-check only (exit 1 on any failed check), writes nothing
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CP = Path(__file__).resolve().parent
ROOT = CP.parents[3]
LIMIT_UM, WARN_UM = 500.0, 450.0
# kits the die would place today (relays: the M5 kits in route as loop jobs *-2c31a0533; the rest: the first-round kits,
# being rebuilt on claude/vm8-face-1013 -> rerun with --kit MASTER=NEWKIT)
KIT = {"vm_cp_rb": "vm_cp_rb_cx2", "vm_cp_rt": "vm_cp_rt_cx2", "vm_cp_rt2": "vm_cp_rt2_cx2", "vm_cp_rwa": "vm_cp_rwa_cx2",
       "vm_cp_rwb": "vm_cp_rwb_cx2", "vm_cp_rb2": "vm_cp_rb2_cx", "vm_cp_slice3": "vm_cp_slice3_cx"}
# open-relay origin moves of candidate_geometry.py (commit 07d81243a)
# exported LEFs kept outside a kit's views directory (repo copies of route exports), per master
LEF = {"vm_cp_rwb": "results/physical/vm8_codex_1013/rwb_cx1_collect/vm_cp_rwb.lef"}   # cx1 route 8b38f8b41; cx2 = same pins
CANDIDATE = {"u_rt0": (None, 1373.76), "u_rb3": (None, 224.64)}
TRACKS_PER_UM = {"M6": 1 / 0.064, "M7": 1 / 0.064}     # ASAP7 M6 (horizontal) / M7 (vertical) pitch 64 nm
LOWER_PER_UM = {"M6": 1 / 0.048, "M7": 1 / 0.048}      # + M4 under M6 / M5 under M7 (48 nm), tile-free channel only
CUT_LIMIT = 0.55                                       # owner cut rule: bits per cut <= 0.55-0.60 of the tracks
HALO = 8.64                                            # clearance kept on the pin faces of a moved tile (um)
GRID = 2.16                                            # tile origin / lattice step (um)
EDGE = {"left": "W", "right": "E", "bottom": "S", "top": "N"}


def load(name: str, path: Path):
    sp = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------- RTL
def rtl_ports(master: str) -> dict:
    """{port: (dir, width, scalar)} from the module header of rtl/<master>.sv (the RTL, not the plan table)"""
    text = (CP / "rtl" / f"{master}.sv").read_text()
    head = re.search(r"module\s+%s\s*\((.*?)\);" % re.escape(master), text, re.S).group(1)
    out = {}
    for d, hi, name in re.findall(r"(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)", head):
        out[name] = ("in" if d == "input" else "out", int(hi) + 1 if hi else 1, not hi)
    return out


def parse_top(path: Path):
    """die netlist: wires {net: width}, aliases {alias: net} (the non-mutant `else branch), instances, top ports"""
    wires, alias, insts, top = {}, {}, [], {}
    branch = None
    text = path.read_text()
    head = re.search(r"module\s+hfd_vm_cp\s*\((.*?)\);", text, re.S).group(1)
    for d, hi, names in re.findall(r"(input|output)\s+wire\s*\[(\d+):0\]\s*([\w,\s]+?)(?=,\s*(?:input|output)|$)", head):
        for n in names.replace("\n", " ").split(","):
            if n.strip():
                top[n.strip()] = ("in" if d == "input" else "out", int(hi) + 1)
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("`ifdef"):
            branch = "mut"
        elif s.startswith("`else"):
            branch = "plain"
        elif s.startswith("`endif"):
            branch = None
        m = re.fullmatch(r"wire \[(\d+):0\] (\w+);", s)
        if m:
            wires[m.group(2)] = int(m.group(1)) + 1
        m = re.fullmatch(r"wire \[(\d+):0\] (\w+) = (\w+);", s)
        if m and branch == "plain":
            alias[m.group(2)] = m.group(3)
        m = re.fullmatch(r"(vm_cp_\w+) (u_\w+) \((.*)\);", s)
        if m:
            conn = {}
            for port, net, idx in re.findall(r"\.(\w+)\((\w+)(\[\d+\])?\)", m.group(3)):
                conn[port] = (net, idx)
            insts.append((m.group(2), m.group(1), conn))
    return wires, alias, insts, top


# ------------------------------------------------------------------------------------------------- pins
TCL_STUB = r'''
set ::ot_names {%s}
set ::ot_k 0
foreach n $::ot_names { set ::ot_nm(bt$::ot_k) $n; lappend ::ot_bt bt$::ot_k; incr ::ot_k }
namespace eval ord { proc get_db_block {} { return ot_blk } }
proc ot_blk {method} { return $::ot_bt }
proc unknown {cmd args} {
  if {[info exists ::ot_nm($cmd)]} {
    if {[lindex $args 0] eq "getName"} { return $::ot_nm($cmd) }
    return SIGNAL
  }
  error "bit_reach stub: unknown command $cmd $args"
}
proc set_io_pin_constraint {args} { error "bit_reach: kit uses PPL ordered groups (no deterministic per-bit plan)" }
proc place_pin {args} {
  array set a [lrange $args 0 5]
  puts "PIN\t$a(-pin_name)\t$a(-layer)\t[lindex $a(-location) 0]\t[lindex $a(-location) 1]"
}
'''


def kit_env(kit: str) -> dict:
    """the pin part of physical/ref_tile/<kit>/kit.env: PINS array + exported OT_PIN_* variables"""
    env = {"regions": [], "export": {}}
    for line in (ROOT / "physical/ref_tile" / kit / "kit.env").read_text().splitlines():
        if line.startswith("PINS=("):
            tok = shlex.split(line[len("PINS=("):line.rindex(")")])
            env["regions"] = [tok[i + 1] for i in range(0, len(tok), 2) if tok[i] == "--pin-region"]
        m = re.fullmatch(r"export (OT_PIN_\w+)=(.*)", line)
        if m:
            env["export"][m.group(1)] = shlex.split(m.group(2))[0]
    return env


def plan_pins(kit: str, ports: dict, driver) -> tuple[dict, dict]:
    """{port: {bit: (x, y, layer, face)}} by executing the route's own IO-constraint Tcl; returns (pins, source)"""
    kd = ROOT / "physical/ref_tile" / kit
    fp = json.loads((kd / "floorplan.json").read_text())
    spec = json.loads((kd / "spec.json").read_text())
    if spec.get("io_tcl"):
        raise SystemExit(f"{kit}: spec io_tcl (hand pin file) is not modelled; give --lef")
    env = kit_env(kit)
    resolved = driver.resolve_floorplan(fp["die"], fp["core"], env["regions"], None)
    saved = {k: os.environ.get(k) for k in ("OT_PIN_GROUP_MAX", "OT_PIN_BALANCE_H", "OT_PIN_BALANCE_V")}
    try:
        for k in saved:
            os.environ.pop(k, None)
        os.environ.update(env["export"])
        tcl = driver.io_constraints_tcl(resolved["pin_regions"], True, resolved["die_area_um"])
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    names = []
    for p, (_d, w, scalar) in ports.items():
        names += [p] if scalar else [f"{p}[{b}]" for b in range(w)]
    run = subprocess.run(["tclsh"], input=TCL_STUB % " ".join("{" + n + "}" for n in names) + tcl, text=True,
                         capture_output=True)
    if run.returncode or run.stderr:
        raise SystemExit(f"{kit}: pin plan Tcl failed: {run.stderr[-600:]}")
    face_of = {}
    for r in resolved["pin_regions"]:
        for n in names:
            if re.search(r["regex"], n) or re.search(r["regex"], re.sub(r"\[\d+\]$", "", n)):
                face_of[n] = EDGE[r["edge"]]
    pins = {}
    for line in run.stdout.splitlines():
        _t, name, layer, x, y = line.split("\t")
        m = re.fullmatch(r"(\w+)(?:\[(\d+)\])?", name)
        pins.setdefault(m.group(1), {})[int(m.group(2) or 0)] = (float(x), float(y), layer, face_of[name])
    src = dict(kind="plan", kit=kit, kit_env_sha256=sha(kd / "kit.env"), spec_sha256=sha(kd / "spec.json"),
               floorplan_sha256=sha(kd / "floorplan.json"), die=fp["die"], layer_cap=fp["layer_contract"].get("layer_cap", "M6"),
               pin_env=env["export"])
    return pins, src


def lef_pins(path: Path, top: str) -> tuple[dict, dict]:
    """{port: {bit: (x, y, layer, face)}} from the LEF: the PORT rectangle touching the macro boundary, its centre along
    the face, on the boundary"""
    text = path.read_text()
    w, h = map(float, re.search(r"MACRO %s\b.*?SIZE ([\d.]+) BY ([\d.]+)" % re.escape(top), text, re.S).groups())
    pins = {}
    for name, body in re.findall(r"\n  PIN (\S+)\n(.*?)\n  END \1", text, re.S):
        if re.search(r"USE (POWER|GROUND)", body):
            continue
        best = None
        for layer, rects in re.findall(r"LAYER (\w+) ;((?:\s+RECT [^;]+;)+)", body):
            for r in re.findall(r"RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", rects):
                x0, y0, x1, y1 = map(float, r)
                d = {"W": x0, "E": w - x1, "S": y0, "N": h - y1}
                f = min(d, key=d.get)
                if best is None or d[f] < best[0]:
                    c = ((x0 + x1) / 2, (y0 + y1) / 2)
                    xy = {"W": (0.0, c[1]), "E": (w, c[1]), "S": (c[0], 0.0), "N": (c[0], h)}[f]
                    best = (d[f], xy, layer, f)
        m = re.fullmatch(r"(\w+)(?:\[(\d+)\])?", name)
        pins.setdefault(m.group(1), {})[int(m.group(2) or 0)] = (best[1][0], best[1][1], best[2], best[3])
    return pins, dict(kind="lef", path=str(path.resolve().relative_to(ROOT)) if ROOT in path.resolve().parents else str(path), lef_sha256=sha(path), die=[0, 0, w, h])


def kit_pins(master: str, kit: str, lef: Path | None, ports: dict, driver) -> tuple[dict, dict]:
    top = json.loads((ROOT / "physical/ref_tile" / kit / "spec.json").read_text())["top"]
    assert top == master, (kit, top, master)
    plan, psrc = plan_pins(kit, ports, driver)
    repo_lef = ROOT / "physical/ref_tile" / kit / "views" / top / f"{top}.lef"
    lef = lef or (repo_lef if repo_lef.exists() else None)
    if lef is None:
        return plan, psrc
    pins, src = lef_pins(lef, top)
    src["kit"] = kit
    src["layer_cap"] = psrc["layer_cap"]
    # the LEF is the truth; the plan of the kit named for this master must describe the same pins (same face, and
    # along-face distance within a few tracks), else the LEF belongs to another pin plan
    dev, face_bad, miss = 0.0, 0, 0
    for p, bits in plan.items():
        for b, (x, y, _l, f) in bits.items():
            q = pins.get(p, {}).get(b)
            if q is None:
                miss += 1
                continue
            face_bad += q[3] != f
            dev = max(dev, abs(q[0] - x) + abs(q[1] - y))
    src["plan_vs_lef"] = dict(max_dev_um=round(dev, 4), wrong_face=face_bad, missing_in_lef=miss,
                              plan_kit_env_sha256=psrc["kit_env_sha256"])
    if src["die"][2:] != [float(v) for v in psrc["die"][2:]]:
        src["plan_vs_lef"]["outline_differs"] = [src["die"], psrc["die"]]
    return pins, src


# ------------------------------------------------------------------------------------------------- geometry
def place(inst: dict, pin) -> tuple[float, float]:
    x, y = pin[0], pin[1]
    if inst["orient"] == "MX":
        y = inst["h"] - y
    return inst["x"] + x, inst["y"] + y


def legality(instances: dict, region) -> dict:
    """as candidate_geometry.py (pairwise overlap) plus the region bound of make_vm_cp.py"""
    names = list(instances)
    over, oob = [], []
    for i, a in enumerate(names):
        A = instances[a]
        if A["x"] < -1e-6 or A["y"] < -1e-6 or A["x"] + A["w"] > region[0] + 1e-6 or A["y"] + A["h"] > region[1] + 1e-6:
            oob.append(a)
        for b in names[i + 1:]:
            B = instances[b]
            if (min(A["x"] + A["w"], B["x"] + B["w"]) - max(A["x"], B["x"]) > 1e-6
                    and min(A["y"] + A["h"], B["y"] + B["h"]) - max(A["y"], B["y"]) > 1e-6):
                over.append([a, b])
    return dict(overlap=over, out_of_region=oob)


def build(kits: dict, lefs: dict, origins: dict, driver, plan):
    wires, alias, insts, top = parse_top(CP / "hfd_vm_cp.sv")
    ports, pins, sources, instances = {}, {}, {}, {}
    planned = {i[0]: i for i in plan.INST}
    for inst, master, _conn in insts:
        if master not in ports:
            ports[master] = rtl_ports(master)
            kit = kits.get(master, master)
            pins[master], sources[master] = kit_pins(master, kit, lefs.get(master), ports[master], driver)
        _i, pm, x, y, orient, _c = planned[inst]
        assert pm == master, (inst, pm, master)
        w, h = sources[master]["die"][2:]
        x = plan.VMW - w if x is None else x
        ox, oy = origins.get(inst, (None, None))
        instances[inst] = dict(master=master, kit=sources[master]["kit"], x=x if ox is None else ox,
                               y=y if oy is None else oy, w=w, h=h, orient=orient,
                               moved_from_plan=inst in origins)
    drv, rcv, unconnected, external = {}, {}, [], []
    for inst, master, conn in insts:
        for p, (d, w, _s) in ports[master].items():
            if p == "ck":
                continue
            if p not in conn:
                unconnected.append(f"{inst}.{p}")
                continue
            net = alias.get(conn[p][0], conn[p][0])
            if net in wires:
                (drv if d == "out" else rcv).setdefault(net, []).append((inst, p, w))
            else:
                external.append(dict(pin=f"{inst}.{p}", bits=w, top_port=net))
    return wires, top, ports, pins, sources, instances, drv, rcv, unconnected, external


def measure(wires, pins, instances, drv, rcv):
    hops, nets = [], []
    for net in sorted(wires):
        for di, dp, dw in drv.get(net, []):
            D = instances[di]
            dpin = pins[D["master"]][dp]
            ends = [(ri, rp, rw, pins[instances[ri]["master"]][rp]) for ri, rp, rw in rcv.get(net, [])]
            hp = []
            for ri, rp, rw, rpin in ends:
                rows = []
                for b in range(wires[net]):
                    a, c = place(D, dpin[b]), place(instances[ri], rpin[b])
                    rows.append((abs(a[0] - c[0]) + abs(a[1] - c[1]), b, a, c, dpin[b][2], rpin[b][2]))
                dist = sorted(r[0] for r in rows)
                worst = sorted(rows, key=lambda r: -r[0])[:5]
                hops.append(dict(
                    net=net, frm=f"{di}.{dp}", to=f"{ri}.{rp}", bits=len(rows), driver_bits=dw, load_bits=rw,
                    net_bits=wires[net], faces=dpin[0][3] + ">" + rpin[0][3],
                    max_um=round(dist[-1], 3), min_um=round(dist[0], 3), mean_um=round(sum(dist) / len(dist), 3),
                    p99_um=round(dist[min(len(dist) - 1, int(0.99 * len(dist)))], 3),
                    bits_gt_500=sum(d > LIMIT_UM for d in dist), bits_gt_450=sum(d > WARN_UM for d in dist),
                    worst_bits=[dict(bit=r[1], um=round(r[0], 3), dx_um=round(abs(r[2][0] - r[3][0]), 3),
                                     dy_um=round(abs(r[2][1] - r[3][1]), 3),
                                     driver_xy=[round(v, 3) for v in r[2]], load_xy=[round(v, 3) for v in r[3]],
                                     layers=r[4] + ">" + r[5]) for r in worst],
                    coord_source=[instances[di]["master"], instances[ri]["master"]], _rows=rows))
            if ends:
                for b in range(wires[net]):
                    pts = [place(D, dpin[b])] + [place(instances[ri], rpin[b]) for ri, _p, _w, rpin in ends]
                    hp.append(max(p[0] for p in pts) - min(p[0] for p in pts) + max(p[1] for p in pts) - min(p[1] for p in pts))
                nets.append(dict(net=net, bits=wires[net], loads=len(ends), hpwl_max_um=round(max(hp), 3),
                                 hpwl_mean_um=round(sum(hp) / len(hp), 3), hpwl_bits_gt_500=sum(v > LIMIT_UM for v in hp)))
    return hops, nets


def cuts(hops, instances, sources, region, caps):
    """cheap die-channel cut: every hop bit is one die wire.  A vertical cut line x = c (mid-way between two consecutive
    tile edges) is crossed by the bits whose two pins lie on either side; they cross it on a horizontal layer (M6, 15.6
    tracks/um), somewhere inside the y interval of their two pins (pass no_jog) or inside that interval widened on both
    sides by half the reach the bit has left, (500 - pin distance) / 2 (pass reach_jog: the most a wire may detour and
    still be a 500 um hop).  Free tracks: the cut line outside every tile, plus the M6 above an M5-capped tile (ASSUMED
    free: its own PG is M5; a die M6 strap over it is not subtracted); a tile capped at M6 (or its M7 grid, for the
    horizontal cut lines whose wires are M7) blocks its whole extent.  Hall bound on a 2.16 um lattice: for every window
    of the cut line, bits that must cross INSIDE it / free tracks inside it; demand = the worst window.  Same for
    horizontal cut lines with M7.  Third pass reach_jog_plus_lower_layer_in_gaps: as reach_jog, plus the next lower layer
    of the same direction (M4 under M6, M5 under M7, 20.8 tracks/um) where NO tile lies under the cut line -- only valid if
    the die route is granted those layers in its channels."""
    import numpy as np
    out = []
    for axis, layer, span in ((0, "M6", region[1]), (1, "M7", region[0])):
        tpu = TRACKS_PER_UM[layer]
        edges = sorted({round(v, 3) for i in instances.values()
                        for v in ((i["x"], i["x"] + i["w"]) if axis == 0 else (i["y"], i["y"] + i["h"]))})
        nb = int(span / GRID) + 2
        for e0, e1 in zip(edges, edges[1:]):
            if e1 - e0 < 2.0:
                continue
            c = (e0 + e1) / 2
            lo, hi, slack, by_hop = [], [], [], {}
            for h in hops:
                k = 0
                for d, _b, a, b, _la, _lb in h["_rows"]:
                    if min(a[axis], b[axis]) < c < max(a[axis], b[axis]):
                        k += 1
                        lo.append(min(a[1 - axis], b[1 - axis]))
                        hi.append(max(a[1 - axis], b[1 - axis]))
                        slack.append(max(LIMIT_UM - d, 0.0) / 2)
                if k:
                    by_hop[h["frm"] + ">" + h["to"]] = k
            if not lo:
                continue
            free = np.full(nb, GRID * tpu)
            lower = np.full(nb, GRID * LOWER_PER_UM[layer])
            under = []
            for name, i in instances.items():
                p0, p1 = (i["x"], i["x"] + i["w"]) if axis == 0 else (i["y"], i["y"] + i["h"])
                q0, q1 = (i["y"], i["y"] + i["h"]) if axis == 0 else (i["x"], i["x"] + i["w"])
                if not p0 < c < p1:
                    continue
                cap = caps.get(i["master"], sources[i["master"]].get("layer_cap", "M6"))
                blocks = cap != "M5"
                under.append(dict(inst=name, layer_cap=cap, span_um=[round(q0, 2), round(q1, 2)], blocks=blocks))
                for k in range(int(q0 / GRID), min(nb, int(q1 / GRID) + 1)):
                    cov = max(min(q1, (k + 1) * GRID) - max(q0, k * GRID), 0.0)
                    lower[k] = max(lower[k] - cov * LOWER_PER_UM[layer], 0.0)
                    if blocks:
                        free[k] = max(free[k] - cov * tpu, 0.0)
            row = dict(cut=("x" if axis == 0 else "y") + f"={c:.2f}", wire_layer=layer, bits=len(lo), hops=by_hop,
                       tiles_under=under)
            lo, hi, slack = np.array(lo), np.array(hi), np.array(slack)
            for name, s, fr in (("no_jog", 0.0, free), ("reach_jog", slack, free),
                                ("reach_jog_plus_lower_layer_in_gaps", slack, free + lower)):
                F = np.concatenate([[0.0], np.cumsum(fr)])
                a = np.clip(((lo - s) / GRID).astype(int), 0, nb - 1)
                b = np.clip(((hi + s) / GRID).astype(int), 0, nb - 1)
                cnt = np.zeros((nb, nb))
                np.add.at(cnt, (a, b), 1)
                C = np.cumsum(np.cumsum(cnt[::-1], axis=0)[::-1], axis=1)     # C[u, v] = bits with u <= a and b <= v
                T = F[None, 1:] - F[:-1, None]                                # free tracks in buckets u..v
                with np.errstate(divide="ignore", invalid="ignore"):
                    R = np.where(C > 0, np.where(T > 1e-9, C / np.maximum(T, 1e-9), np.inf), 0.0)
                u, v = np.unravel_index(np.argmax(R), R.shape)
                need = C[u, v] / CUT_LIMIT
                row[name] = dict(demand=None if np.isinf(R[u, v]) else round(float(R[u, v]), 3),
                                 window_um=[round(u * GRID, 2), round((v + 1) * GRID, 2)], bits_in_window=int(C[u, v]),
                                 free_tracks_in_window=int(T[u, v]), over_limit=bool(R[u, v] > CUT_LIMIT),
                                 extra_free_um_for_limit=round(max(need - T[u, v], 0.0) / tpu, 2))
            out.append(row)
    return out


# ------------------------------------------------------------------------------------------------- fixes


def propose(hops, instances, wires, pins, drv, rcv, region, frozen):
    """for each violating hop: (a) the smallest on-grid move of ONE open tile of the hop that brings every hop of that
    tile under the limit with a legal 25-tile assembly, (b) the pin-range shift of one end that does it"""
    def worst_of(inst_set, inst_map):
        w = 0.0
        for net in wires:
            for di, dp, _w in drv.get(net, []):
                for ri, rp, _w2 in rcv.get(net, []):
                    if di not in inst_set and ri not in inst_set:
                        continue
                    dpin, rpin = pins[inst_map[di]["master"]][dp], pins[inst_map[ri]["master"]][rp]
                    for b in {0, wires[net] - 1, wires[net] // 2}:
                        a, c = place(inst_map[di], dpin[b]), place(inst_map[ri], rpin[b])
                        w = max(w, abs(a[0] - c[0]) + abs(a[1] - c[1]))
        return w

    fixes = []
    for h in hops:
        if not h["bits_gt_500"]:
            continue
        di, ri = h["frm"].split(".")[0], h["to"].split(".")[0]
        fix = dict(hop=h["frm"] + ">" + h["to"], max_um=h["max_um"], bits_gt_500=h["bits_gt_500"], moves=[], pin_shift=[])
        for inst in (di, ri):
            if inst in frozen:
                continue
            best = None
            for ax in ("y", "x"):
                for k in range(-120, 121):
                    if not k:
                        continue
                    trial = {n: dict(v) for n, v in instances.items()}
                    trial[inst][ax] = round(instances[inst][ax] + k * GRID, 3)
                    leg = legality(trial, region)
                    if leg["overlap"] or leg["out_of_region"]:
                        continue
                    w = worst_of({inst}, trial)
                    if w <= LIMIT_UM and (best is None or abs(k) < abs(best[0])):
                        best = (k, ax, w)
            if best:
                k, ax, w = best
                fix["moves"].append(dict(inst=inst, axis=ax, frm=instances[inst][ax],
                                         to=round(instances[inst][ax] + k * GRID, 3), delta_um=round(k * GRID, 3),
                                         worst_hop_of_tile_after_um=round(w, 3)))
        # pin shift along the face: the worst bit's excess, applied to the whole range of either port
        wb = h["worst_bits"][0]
        excess = round(h["max_um"] - LIMIT_UM, 3)
        along = "y" if h["faces"][0] in "WE" else "x"
        sign = 1 if wb["load_xy"][1 if along == "y" else 0] > wb["driver_xy"][1 if along == "y" else 0] else -1
        fix["pin_shift"] = [dict(port=h["frm"], kit=instances[di]["kit"], shift_um=round(sign * excess, 3)),
                            dict(port=h["to"], kit=instances[ri]["kit"], shift_um=round(-sign * excess, 3))]
        fix["note"] = "apply ONE entry: a tile move, or one port's pin_ranges [lo, hi] both shifted by shift_um (if the face has room)"
        fixes.append(fix)
    return fixes


def balance(instances, wires, pins, drv, rcv, region, movable, span=60):
    """margin proposal (not a repair): one pass, worst tile first, over the open relay tiles whose longest hop exceeds
    450 um -- move the tile on the 2.16 um lattice to the legal origin (8.64 um halo on its pin faces) that minimises the
    longest hop touching it; keep the move if it gains >= 4.32 um.  Rerun the tool with --origin to audit the set bit by
    bit (reach AND cuts: a move that narrows a channel raises its cut demand)."""
    inst = {n: dict(v) for n, v in instances.items()}

    def worst(name, m):
        w = 0.0
        for net in wires:
            for di, dp, _w in drv.get(net, []):
                for ri, rp, _w2 in rcv.get(net, []):
                    if name not in (di, ri):
                        continue
                    dpin, rpin = pins[m[di]["master"]][dp], pins[m[ri]["master"]][rp]
                    for b in (0, wires[net] - 1):
                        p, q = place(m[di], dpin[b]), place(m[ri], rpin[b])
                        w = max(w, abs(p[0] - q[0]) + abs(p[1] - q[1]))
        return w

    def legal(m, name):
        # a moved tile keeps HALO to every other tile on its pin faces (pins need die access; abutment is only kept
        # where the plan already has it, on faces without pins)
        A = m[name]
        if A["x"] < 0 or A["y"] < 0 or A["x"] + A["w"] > region[0] + 1e-6 or A["y"] + A["h"] > region[1] + 1e-6:
            return False
        faces = {pin[0][3] for pin in pins[A["master"]].values()}
        hx = HALO if faces & {"W", "E"} else 0.0
        hy = HALO if faces & {"N", "S"} else 0.0
        return not any(n != name and min(A["x"] + A["w"] + hx, B["x"] + B["w"]) - max(A["x"] - hx, B["x"]) > 1e-6
                       and min(A["y"] + A["h"] + hy, B["y"] + B["h"]) - max(A["y"] - hy, B["y"]) > 1e-6 for n, B in m.items())

    moves = []
    for name in sorted(movable, key=lambda n: -worst(n, inst)):
        w0 = worst(name, inst)
        if w0 <= WARN_UM:
            continue
        x0, y0 = inst[name]["x"], inst[name]["y"]
        best = (w0, 0.0, 0, 0)
        for kx in range(-span, span + 1):
            for ky in range(-span, span + 1):
                inst[name]["x"], inst[name]["y"] = round(x0 + kx * GRID, 3), round(y0 + ky * GRID, 3)
                if not legal(inst, name):
                    continue
                key = (round(worst(name, inst), 3), (abs(kx) + abs(ky)) * GRID, kx, ky)
                if key < best:
                    best = key
        w1, _d, kx, ky = best
        inst[name]["x"], inst[name]["y"] = x0, y0
        if w0 - w1 >= 2 * GRID:
            inst[name]["x"], inst[name]["y"] = round(x0 + kx * GRID, 3), round(y0 + ky * GRID, 3)
            moves.append(dict(inst=name, frm=[x0, y0], to=[inst[name]["x"], inst[name]["y"]],
                              worst_hop_of_tile_um=[round(w0, 3), w1]))
    final = {n: [v["x"], v["y"]] for n, v in inst.items() if [v["x"], v["y"]] != [instances[n]["x"], instances[n]["y"]]}
    return dict(method=balance.__doc__, moves=moves, origins=final, legality=legality(inst, region),
                rerun="python3 physical/hbm_accel_die_views/vm/cp/bit_reach.py "
                      + " ".join(f"--origin {n}={x},{y}" for n, (x, y) in final.items()) + " --out <file>")


# ------------------------------------------------------------------------------------------------- checks
def self_check(wires, top, ports, pins, sources, instances, drv, rcv, unconnected, external, hops, plan, driver, kits, lefs):
    checks = {}

    def ck(name, ok, detail=None):
        checks[name] = dict(ok=bool(ok), detail=detail)

    ck("instances_25", len(instances) == 25, len(instances))
    ck("kits_19", len(ports) == 19, len(ports))
    ck("hops_52", len(hops) == 52, len(hops))
    bad = [h["net"] for h in hops if not (h["bits"] == h["driver_bits"] == h["load_bits"] == h["net_bits"])]
    ck("hop_bits_equal_rtl_port_widths", not bad, bad)
    ck("every_net_one_driver_and_a_load", all(len(drv.get(n, [])) == 1 and rcv.get(n) for n in wires),
       [n for n in wires if len(drv.get(n, [])) != 1 or not rcv.get(n)])
    ck("no_unconnected_tile_pin", not unconnected, unconnected)
    # every signal pin bit of every kit has exactly one coordinate, on the face the kit spec names, on the boundary
    bad = []
    for m, pp in ports.items():
        spec = json.loads((ROOT / "physical/ref_tile" / sources[m]["kit"] / "spec.json").read_text())
        face = {p: f for f, ps in spec["pins"].items() for p in ps}
        w, h = sources[m]["die"][2:]
        for p, (_d, n, _s) in pp.items():
            got = pins[m].get(p, {})
            if sorted(got) != list(range(n)):
                bad.append(f"{m}.{p}: {len(got)}/{n} bits")
                continue
            for b, (x, y, _l, f) in got.items():
                on = {"W": abs(x) < 1e-6, "E": abs(x - w) < 1e-6, "S": abs(y) < 1e-6, "N": abs(y - h) < 1e-6}[f]
                if f != face[p] or not on or not (0 <= x <= w and 0 <= y <= h):
                    bad.append(f"{m}.{p}[{b}] {f} ({x},{y})")
                    break
    ck("every_pin_bit_placed_on_its_spec_face", not bad, bad[:8])
    # no two pins of a kit share a point on one layer
    bad = []
    for m in pins:
        seen = {}
        for p, bits in pins[m].items():
            for b, (x, y, l, _f) in bits.items():
                k = (round(x, 4), round(y, 4), l)
                if k in seen:
                    bad.append(f"{m}: {p}[{b}] = {seen[k]}")
                seen[k] = f"{p}[{b}]"
    ck("no_coincident_pins", not bad, bad[:8])
    # the plan table of make_vm_cp.py and the die netlist agree (the netlist is what is measured)
    bad = []
    for inst, master, _x, _y, _o, conn in plan.INST:
        for p, net in conn.items():
            want = plan.ports_of(master)[p][:2]
            if tuple(ports[master][p][:2]) != tuple(want):
                bad.append(f"{inst}.{p}")
    ck("rtl_ports_match_plan_table", not bad, bad)
    total = sum(h["bits"] for h in hops)
    ext = sum(e["bits"] for e in external)
    allbits = sum(n for inst in instances.values() for p, (_d, n, _s) in ports[inst["master"]].items() if p != "ck")
    ck("pin_bits_conserved", allbits == 2 * total + ext, dict(tile_pin_bits=allbits, hop_bits=total, external_pin_bits=ext))
    ck("top_ports_all_bound", {e["top_port"] for e in external} == set(top) - {"ck"},
       sorted(set(top) - {"ck"} - {e["top_port"] for e in external}))
    for m, s in sources.items():
        if s["kind"] == "lef":
            v = s["plan_vs_lef"]
            ck(f"lef_matches_plan_{m}", v["max_dev_um"] <= 0.2 and not v["wrong_face"] and not v["missing_in_lef"]
               and "outline_differs" not in v, v)
    # regression: with the generator's nominal origins the audit must find the two known packed-range failures
    # (log 01:35: RT0.wo -> FW2.ph 572.8 um, RB3.eo -> FE1.ph 522.734 um)
    w2 = build(kits, lefs, {}, driver, plan)
    h2, _n = measure(w2[0], w2[3], w2[5], w2[6], w2[7])
    got = {h["frm"] + ">" + h["to"]: h["max_um"] for h in h2 if h["bits_gt_500"]}
    ck("nominal_origins_reproduce_known_failures",
       abs(got.get("u_rt0.wo>u_fw2.ph", 0) - 572.8) < 0.5 and abs(got.get("u_rb3.eo>u_fe1.ph", 0) - 522.734) < 0.5, got)
    return checks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", action="append", default=[], metavar="MASTER=KIT", help="kit directory name under physical/ref_tile")
    ap.add_argument("--lef", action="append", default=[], metavar="MASTER=PATH", help="exported LEF of that master's kit")
    ap.add_argument("--origin", action="append", default=[], metavar="INST=X,Y", help="tile origin override (um)")
    ap.add_argument("--nominal", action="store_true", help="generator origins (drop the candidate_geometry.py moves)")
    ap.add_argument("--layer-cap", action="append", default=[], metavar="MASTER=M5|M6",
                    help="cut analysis: top signal layer of that master (default: the kit floorplan's layer contract)")
    ap.add_argument("--balance", action="store_true", help="also search a margin-balancing origin set for the open relays")
    ap.add_argument("--frozen", default="u_s3", help="comma list of instances a proposed fix may not move (closed views)")
    ap.add_argument("--out", default=str(ROOT / "results/physical/vm8_codex_1013/bit_reach.json"))
    ap.add_argument("--bits-csv", help="also write every bit (hop, bit, um, driver xy, load xy)")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    sys.dont_write_bytecode = True
    driver = load("ot_rap", ROOT / "tools/run_abi3_physical.py")
    plan = load("vm_cp_plan", CP / "make_vm_cp.py")
    kits = {**KIT, **dict(k.split("=", 1) for k in a.kit)}
    lefs = {**{k: ROOT / v for k, v in LEF.items()}, **{k: Path(v) for k, v in (x.split("=", 1) for x in a.lef)}}
    origins = {} if a.nominal else dict(CANDIDATE)
    for o in a.origin:
        k, v = o.split("=")
        origins[k] = tuple(float(t) for t in v.split(","))
    region = [plan.VMW, plan.VMH]
    wires, top, ports, pins, sources, instances, drv, rcv, unconnected, external = build(kits, lefs, origins, driver, plan)
    hops, nets = measure(wires, pins, instances, drv, rcv)
    checks = self_check(wires, top, ports, pins, sources, instances, drv, rcv, unconnected, external, hops, plan, driver,
                        kits, lefs)
    failed = [k for k, v in checks.items() if not v["ok"]]
    leg = legality(instances, region)
    caps = dict(k.split("=", 1) for k in a.layer_cap)
    cut = cuts(hops, instances, sources, region, caps)
    fixes = propose(hops, instances, wires, pins, drv, rcv, region, set(a.frozen.split(",")))
    frozen = set(a.frozen.split(","))
    movable = [n for n, v in instances.items() if n not in frozen
               and re.fullmatch(r"vm_cp_(rb2?|rt2?|rwa|rwb|rwt|re)", v["master"])]
    bal = balance(instances, wires, pins, drv, rcv, region, movable) if a.balance else None
    findings = []
    for c in cut:
        r, l = c["reach_jog"], c["reach_jog_plus_lower_layer_in_gaps"]
        if not r["over_limit"]:
            continue
        w0, w1 = r["window_um"]
        blk = sorted({instances[u["inst"]]["master"] for u in c["tiles_under"]
                      if u["blocks"] and min(u["span_um"][1], w1) > max(u["span_um"][0], w0)})
        findings.append(dict(
            cut=c["cut"], wire_layer=c["wire_layer"], window_um=r["window_um"], bits_in_window=r["bits_in_window"],
            free_tracks=r["free_tracks_in_window"], demand=r["demand"], demand_with_lower_layer_in_gaps=l["demand"],
            options=dict(free_more_um_of_this_layer=r["extra_free_um_for_limit"],
                         rebuild_M5_capped_so_die_tracks_pass_over=blk,
                         grant_lower_layer_in_tile_free_channel="passes" if not l["over_limit"] else "still over",
                         check="rerun with --layer-cap MASTER=M5 / --origin"), hops=c["hops"]))
    if a.bits_csv:
        with open(a.bits_csv, "w") as f:
            f.write("hop,bit,um,dx,dy,driver_x,driver_y,load_x,load_y\n")
            for h in hops:
                for d, b, p, q, _la, _lb in h["_rows"]:
                    f.write(f"{h['frm']}>{h['to']},{b},{d:.3f},{abs(p[0]-q[0]):.3f},{abs(p[1]-q[1]):.3f},{p[0]:.3f},{p[1]:.3f},{q[0]:.3f},{q[1]:.3f}\n")
    for h in hops:
        del h["_rows"]
    hops.sort(key=lambda h: -h["max_um"])
    viol = [h for h in hops if h["bits_gt_500"]]
    result = dict(
        schema="opentallas.vm8.bit_reach.v1", planning_only=True,
        statement="Per-bit pin-to-pin Manhattan distance of every die-level hop of hfd_vm_cp.sv, pins from exported LEFs "
                  "where a view exists and from the route's own IO-constraint Tcl otherwise. A lower bound of the routed "
                  "wire, not routed reach, not a closure.",
        rule=dict(limit_um=LIMIT_UM, warn_um=WARN_UM, basis="SS wire reach 504 um per 833 ps stage"),
        inputs=dict(netlist="physical/hbm_accel_die_views/vm/cp/hfd_vm_cp.sv", netlist_sha256=sha(CP / "hfd_vm_cp.sv"),
                    origins="nominal (make_vm_cp.py INST)" if a.nominal else "candidate_geometry.py moves " + json.dumps(CANDIDATE),
                    origin_overrides=a.origin, kit_per_master={m: sources[m]["kit"] for m in sorted(sources)}),
        region_um=region, instances=instances, legality=leg, coordinate_sources=sources,
        summary=dict(instances=len(instances), kits=len(sources), hops=len(hops), nets=len(nets),
                     hop_bits=sum(h["bits"] for h in hops), worst_um=hops[0]["max_um"],
                     worst_hop=hops[0]["frm"] + ">" + hops[0]["to"],
                     hops_gt_500=len(viol), bits_gt_500=sum(h["bits_gt_500"] for h in hops),
                     hops_gt_450=sum(1 for h in hops if h["bits_gt_450"]), bits_gt_450=sum(h["bits_gt_450"] for h in hops),
                     lef_masters=sorted(m for m, s in sources.items() if s["kind"] == "lef"),
                     plan_masters=sorted(m for m, s in sources.items() if s["kind"] == "plan"),
                     legal=not (leg["overlap"] or leg["out_of_region"]),
                     cuts_over_limit_no_jog=[c["cut"] for c in cut if c["no_jog"]["over_limit"]],
                     cuts_over_limit_reach_jog=[c["cut"] for c in cut if c["reach_jog"]["over_limit"]],
                     cuts_over_limit_with_lower_layer=[c["cut"] for c in cut
                                                       if c["reach_jog_plus_lower_layer_in_gaps"]["over_limit"]],
                     worst_cut_reach_jog=max(((c["reach_jog"]["demand"] or 99.0, c["cut"], c["wire_layer"]) for c in cut)),
                     worst_cut_with_lower_layer=max(((c["reach_jog_plus_lower_layer_in_gaps"]["demand"] or 99.0, c["cut"],
                                                      c["wire_layer"]) for c in cut)), self_check_failed=failed),
        hops=hops, nets=nets, external_pins=external, cuts=dict(
            method=cuts.__doc__, tracks_per_um=TRACKS_PER_UM, limit=CUT_LIMIT, layer_cap_overrides=caps, lines=cut),
        proposed_fixes=fixes, margin_balance=bal, cut_findings=findings, self_check=checks,
        unmeasured=["routed die wire length / detours (no die route exists)", "track snap of planned pins (LEF kits: see "
                    "coordinate_sources[*].plan_vs_lef)", "SS timing of each hop (driver strength, load, M6/M7 RC, clock skew "
                    "between tiles)", "kits being rebuilt (face / fork / root): rerun with --kit / --lef"])
    s = result["summary"]
    print(json.dumps(s, indent=1))
    for h in hops[:10]:
        print(f"  {h['max_um']:8.3f} max {h['mean_um']:8.3f} mean {h['p99_um']:8.3f} p99 {h['bits']:5d} b  >500:{h['bits_gt_500']:5d} "
              f">450:{h['bits_gt_450']:5d}  {h['frm']} > {h['to']}")
    if a.check:
        return 1 if failed else 0
    Path(a.out).write_text(json.dumps(result, indent=1) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
