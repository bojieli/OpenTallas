#!/usr/bin/env python3
"""INFRASTRUCTURE-FIRST die method (OWNER D-INFRA-FIRST 2026-10-26 01:37 PDT; lanes/INFRA-FIRST.md; METHODOLOGY 11).
One shared tool for every die: power, clock and reset become FIXED pre-routes before die signal routing, so the die
signal GRT sees the exact leftover capacity.  Opt-in; die_trial.py / die_clock_mesh.py default paths are unchanged.

    die_infra.py pg      PLAN --out D [...]                  # (1) PG grid sized from per-region IR (infra_pg.py)
    (2) clock: die_clock_mesh.py build/balance (one mesh per clock region, driver islands = apply_clkmesh_sites.py)
    die_infra.py clockkit PLAN --kit KIT --out KC [--pg D/pg.json]
                                                             # clock-ALONE kit: partitions + pre-route PG, no signals;
                                                             # then die_clock_mesh.py combo MESH --kit KC + post.sh =
                                                             # the skew gate on the pre-routed clock alone (4)
    die_infra.py reset   PLAN --out D                        # (3) die reset wavefront + START hops (reset_tree.wf_plan)
    die_infra.py trim    MESH --offsets J --out MESH2 --plan PLAN
                                                             # (COORD 01:4x) die absorbs tile insertion residuals:
                                                             # per-tap stub trim pads from declared core-latency offsets
    die_infra.py freeze  PLAN --out D --clock MESH --guide G [--pg D/pg.json] [--reset D/reset.json]
                                                             # (4) fixed pre-routes: preroute.json (one geometry list),
                                                             # preroute.def (SPECIALNETS, FIXED), preroute_obs.tcl
                                                             # (their footprints as GRT obstructions), tracks.json
    die_infra.py grt     PLAN --kit KIT --pre D --out G [--m89]
                                                             # (5) die signal GRT (>= 50 iterations) on the leftover
    die_infra.py report  --pre D [--grt G ...] [--clock MESH] [--sites S.json] --out R.json
                                                             # (6) GRT overflow, skew TT/FF, IR, clock power, island
                                                             # area per type, leftover M8/M9

Pre-route geometry model (one list, three consumers):
  PG    die PG stripes (die.pg.grid or the sized pg.json grid), full-die STRIPE shapes on M8 (H) / M9 (V).
  CLOCK mesh straps (special net ck_mesh, as die_clock_mesh combo) + every routed clock net of the clock-alone GRT
        (route_<corner>.guide): each guide box becomes the clock wire along the box's long axis at the box centreline,
        NDR width; its obstruction is the NDR footprint (width + 2 x space).  GRT counts blocked tracks per gcell, so a
        centreline footprint blocks exactly the tracks the routed clock used in that gcell.
  RESET die wavefront hops parent rst_o_<k> -> child arst_n and START start_o_<k> -> start_i (+ die rst_n/start pins
        to the root): L routes, M8 horizontal then M9 vertical, default width (1 track + space).
GRT does not derate special wires (die_clock_mesh combo note), so every pre-route also goes in as an obstruction.
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

DBU = 1000                       # asap7_tech_1x_201209.lef DATABASE MICRONS
HV = {"M8": "H", "M9": "V"}      # die PG / clock / reset layers (ASAP7: M8 horizontal, M9 vertical)
SIG_W, SIG_S = 0.04, 0.04        # default M8/M9 width / spacing (tech LEF)
NDR = {"4w": (0.16, 0.08), "8w": (0.32, 0.08), "2w": (0.08, 0.08)}


def load_plan(path):
    return S.Plan(S.load(path), Path(path))


# ------------------------------------------------------------------------------------------------------------- PG
def pg_grid(P, pg=None):
    """the die PG grid spec (list of die.pg.grid rows): pg.json["grid"] when given, else the plan's."""
    if pg:
        return json.loads(Path(pg).read_text())["grid"]
    return P.die.get("pg", {}).get("grid", [])


def pg_rects(P, grid):
    """[(net, layer, x0, y0, x1, y1)] of every die PG stripe; the same stripe rule as die_trial.pg_stripes, with the
    net of every stripe (VDD/VSS alternate within one pitch) and optional region-limited rows (row["rect_um"])."""
    out = []
    for g in grid:
        L = P.layers.get(g["layer"])
        if not L:
            continue
        nets = g.get("nets", ["VDD", "VSS"]) or ["VDD"]
        k = len(nets)
        x0, y0, x1, y1 = g.get("rect_um") or (0.0, 0.0, P.W, P.H)
        lo, hi = (x0, x1) if L["dir"] == "V" else (y0, y1)
        pos = lo + g["offset_um"]
        while pos < hi:
            for j in range(k):
                c = pos + j * g["pitch_um"] / k
                if c + g["width_um"] / 2 > hi:
                    continue
                a, b = c - g["width_um"] / 2, c + g["width_um"] / 2
                out.append((nets[j], g["layer"]) + ((a, y0, b, y1) if L["dir"] == "V" else (x0, a, x1, b)))
            pos += g["pitch_um"]
    return out


def cmd_pg(a):
    import infra_pg
    P = load_plan(a.plan)
    r = infra_pg.size_grid(P, Path(a.plan).resolve().parent, ir_budget_frac=a.ir_budget_frac, vdd=a.vdd,
                           phy_w_per_macro=a.phy_w, core_w_mm2=a.core_w_mm2)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pg.json").write_text(json.dumps(r, indent=1) + "\n")
    print(json.dumps({k: r[k] for k in ("grid", "tracks")}, indent=1))
    return 0


# ---------------------------------------------------------------------------------------------------------- reset
def reset_wires(P):
    """die reset wavefront + START hops as (net, kind, (x0, y0), (x1, y1)) in the die frame (reset_tree.wf_plan)."""
    import gen_phys
    import reset_tree as RT
    W = RT.wf_plan(P)
    rp = {n: (x, y) for n, _L, x, y in gen_phys.die_root_pins(P)}
    T = W["types"]
    ST = (W.get("start") or {}).get("types", {})
    out = []
    for p, r in W["parts"].items():
        tn = r["type"]
        if tn in T:
            dst = P.to_die(p, T[tn]["in_um"])
        else:                                   # hard leaf: its reset tap is its IN (the type's reset pin)
            dst = tuple(RT.part_reset_pin(P, p))       # already in the die frame
        if r["parent"] is None:
            src = rp.get(RT.die_reset_port(P)) or rp.get("rst_n")
            out.append(("rst_n", "reset", tuple(src), tuple(dst)))
            if tn in ST and "start" in rp:
                out.append(("start", "start", tuple(rp["start"]), tuple(P.to_die(p, ST[tn]["in_um"]))))
            continue
        q = r["parent"]
        k = int(r["source"].rsplit("_", 1)[1])
        o = T[P.parts[q]["type"]]["outs"][k]
        out.append(("rstw_" + re.sub(r"\W", "_", r["source"]), "reset", tuple(P.to_die(q, (o[1], o[2]))), tuple(dst)))
        if tn in ST and P.parts[q]["type"] in ST:
            so = ST[P.parts[q]["type"]]["outs"]
            if k < len(so):
                src = r["source"].replace(".rst_o_", ".start_o_")
                out.append(("stw_" + re.sub(r"\W", "_", src), "start", tuple(P.to_die(q, (so[k][1], so[k][2]))),
                            tuple(P.to_die(p, ST[tn]["in_um"]))))
    return W, out


def l_rects(a, b, w):
    """L route a -> b: M8 horizontal at a.y, then M9 vertical at b.x; [(layer, x0, y0, x1, y1)] wire rects."""
    (x0, y0), (x1, y1) = a, b
    h = w / 2
    r = []
    if abs(x1 - x0) > 1e-6:
        r.append(("M8", min(x0, x1), y0 - h, max(x0, x1), y0 + h))
    if abs(y1 - y0) > 1e-6:
        r.append(("M9", x1 - h, min(y0, y1), x1 + h, max(y0, y1)))
    return r


def cmd_reset(a):
    P = load_plan(a.plan)
    W, wires = reset_wires(P)
    rows = [dict(net=n, kind=k, a=[round(v, 4) for v in s], b=[round(v, 4) for v in d],
                 len_um=round(abs(s[0] - d[0]) + abs(s[1] - d[1]), 2)) for n, k, s, d in wires]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = dict(root=W["root"], max_release=W["max_release"], max_die_hop_um=W["max_die_hop_um"],
               hop_um=W["hop_um"], long_hops=W["long_hops"], unreachable=W["unreachable"], nets=len(rows),
               wire_mm=round(sum(r["len_um"] for r in rows) / 1e3, 3), wires=rows)
    (out / "reset.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "wires"}, indent=1))
    return 0


# ---------------------------------------------------------------------------------------------------------- clock
def read_guides(path):
    """OpenROAD write_guides -> {net: [(layer, x0, y0, x1, y1) um]}."""
    G, cur, box = {}, None, None
    for line in open(path):
        s = line.strip()
        if not s:
            continue
        if s == "(":
            box = []
            continue
        if s == ")":
            G[cur] = box
            cur, box = None, None
            continue
        if box is None:
            cur = s
            continue
        f = s.split()
        if len(f) >= 5:
            box.append((f[4], int(f[0]) / DBU, int(f[1]) / DBU, int(f[2]) / DBU, int(f[3]) / DBU))
    return G


def guide_wire(layer, x0, y0, x1, y1, w):
    """the clock wire a guide box stands for: along the box's long axis (the layer's preferred axis when the box is
    a single gcell), at the box centreline, width w."""
    dx, dy = x1 - x0, y1 - y0
    horiz = dx > dy + 1e-6 or (abs(dx - dy) <= 1e-6 and HV.get(layer, "H") == "H")
    h = w / 2
    if horiz:
        yc = (y0 + y1) / 2
        return (x0 + dy / 2, yc - h, x1 - dy / 2, yc + h) if dx > dy else ((x0 + x1) / 2 - h, yc - h, (x0 + x1) / 2 + h, yc + h)
    xc = (x0 + x1) / 2
    return (xc - h, y0 + dx / 2, xc + h, y1 - dx / 2) if dy > dx else (xc - h, (y0 + y1) / 2 - h, xc + h, (y0 + y1) / 2 + h)


def clock_rects(mesh_dir, guide, layers=("M8", "M9")):
    """[(net, layer, x0, y0, x1, y1, width)] of the clock pre-route: mesh straps + routed clock nets (guides)."""
    d = Path(mesh_dir)
    M = json.loads((d / "mesh.json").read_text())
    w, _s = NDR[M["meta"].get("ndr", "4w")]
    xs, ys = M["xs"], M["ys"]
    h = w / 2
    out = [("ck_mesh", "M8", xs[0] - h, y - h, xs[-1] + h, y + h, w) for y in ys]
    out += [("ck_mesh", "M9", x - h, ys[0] - h, x + h, ys[-1] + h, w) for x in xs]
    nets = set((d / "clock_nets.txt").read_text().split()) if (d / "clock_nets.txt").exists() else None
    G = read_guides(guide) if guide else {}
    for n, boxes in G.items():
        if nets is not None and n not in nets:
            continue
        for L, x0, y0, x1, y1 in boxes:
            if L not in layers:
                continue
            out.append((n, L) + guide_wire(L, x0, y0, x1, y1, w) + (w,))
    return M, out


# ----------------------------------------------------------------------------------------------------------- trim
def trim_pads(offsets, quantum_ps, reserve=None):
    """COORD 01:4x (the die absorbs residuals): tap t whose tile's measured insertion exceeds plan by off[t] ps must
    get its clock off[t] earlier than the others; a mesh can only ADD delay below the strap, so every other tap gets
    k = round((off_max - off[t]) / quantum) trim pads after its stub buffer.  -> ({tap: k}, {tap: residual ps})."""
    if not offsets:
        return {}, {}
    if reserve is not None:
        # reserve mode: every stub carries `reserve` nominal trim pads (planned latency), so a tile may be faster OR
        # slower than plan: k = reserve - round(off / q), clamped to [0, 2 reserve]; residual = what is not absorbed.
        k = {t: min(2 * reserve, max(0, reserve - int(round(v / quantum_ps)))) for t, v in offsets.items()}
        res = {t: round(-(v + (k[t] - reserve) * quantum_ps), 3) for t, v in offsets.items()}
        return k, res
    top = max(offsets.values())
    k = {t: max(0, int(round((top - v) / quantum_ps))) for t, v in offsets.items()}
    res = {t: round((top - v) - k[t] * quantum_ps, 3) for t, v in offsets.items()}
    return k, res


def cmd_trim(a):
    import die_clock_mesh as DCM
    src, out = Path(a.dir), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    M = json.loads((src / "mesh.json").read_text())
    cells = json.loads((src / "place.json").read_text())
    data = json.loads((src / "nets.json").read_text())
    nets, ports = data["nets"], [tuple(p) for p in data["ports"]]
    raw = json.loads(Path(a.offsets).read_text())
    by_part = defaultdict(list)
    for t in M["taps"]:
        by_part[t["part"]].append(t["port"])
    off = {}
    for key, v in raw.items():                  # key = tap port, "part.tap" or "part" (all its taps)
        if key in by_part:
            for p in by_part[key]:
                off[p] = float(v)
        else:
            m_ = [t["port"] for t in M["taps"] if t["port"] == key or f"{t['part']}.{t['tap']}" == key]
            if not m_:
                raise SystemExit(f"die_infra trim: offset key {key} matches no tap")
            for p in m_:
                off[p] = float(v)
    for t in M["taps"]:
        off.setdefault(t["port"], 0.0)
    q = a.quantum_ps if a.quantum_ps else DCM.pad_delay(a.corner, a.libdir)
    K, res = trim_pads(off, q, a.reserve)
    by_load = {}
    for n in nets:
        for ld in n["loads"]:
            by_load[ld] = n
    added = 0
    for t in M["taps"]:
        k = K.get(t["port"], 0)
        if k <= 0:
            continue
        n = by_load["port:" + t["port"]]           # the net that drives the tap port (stub or split repeater)
        x, y = cells[n["drv"]]["x"], cells[n["drv"]]["y"]
        chain = []
        for i in range(k):
            nm = f"ckm_t_{added}"
            added += 1
            cells[nm] = dict(x=round(x + DCM.BUF_W * (i + 1), 4), y=round(y + 2 * DCM.ROW_Y, 4), kind="pad",
                             level=99, trim_of=t["port"])
            chain.append(nm)
        n["loads"] = [chain[0] if ld == "port:" + t["port"] else ld for ld in n["loads"]]
        for u, w in zip(chain, chain[1:]):
            nets.append(dict(name=f"ckm_w_{u}", drv=u, loads=[w], level=99))
        nets.append(dict(name=f"ckm_w_{chain[-1]}", drv=chain[-1], loads=["port:" + t["port"]], level=99))
    for n in nets:                               # undo write_verilog's port renaming before re-writing
        if n["name"].startswith("t_") and not any(ld == "port:" + n["name"] for ld in n["loads"]):
            n["name"] = f"ckm_w_{n['drv']}"
    ren = DCM.write_verilog(cells, nets, ports, out / "ctree.v")
    for n in nets:
        n["name"] = ren.get(n["name"], n["name"])
    M["meta"]["cells"] = len(cells)
    M["meta"]["trim"] = dict(src=str(src), offsets=str(a.offsets), quantum_ps=round(q, 3), pads=added, reserve=a.reserve,
                             unabsorbed=sorted([t, r] for t, r in res.items() if abs(r) > q / 2 + 1e-6),
                             max_residual_ps=max([abs(v) for v in res.values()] or [0.0]))
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
    (out / "tap_offsets.json").write_text(json.dumps(off, indent=0) + "\n")
    print(json.dumps(M["meta"]["trim"]))
    return 0


# --------------------------------------------------------------------------------------------------------- freeze
def footprint(layer, r, w, s):
    """obstruction of a wire rect: the wire plus spacing on both sides across the wire (its NDR footprint)."""
    x0, y0, x1, y1 = r
    horiz = (x1 - x0) >= (y1 - y0)
    return (x0, y0 - s, x1, y1 + s) if horiz else (x0 - s, y0, x1 + s, y1)


def track_use(P, rects, layers=("M8", "M9"), g=10.8):
    """fraction of each layer's track capacity taken by rects [(cls, layer, x0, y0, x1, y1)], counted the way GRT
    counts it (blocked tracks per gcell, capped at the gcell's tracks) -> {layer: {cls: frac, "all": frac}}."""
    import numpy as np
    nx, ny = int(math.ceil(P.W / g)), int(math.ceil(P.H / g))
    out = {}
    for L in layers:
        pitch = P.layers[L]["pitch_um"]
        horiz = P.layers[L]["dir"] == "H"
        cap = g / pitch
        tot = None
        res = {}
        bycls = defaultdict(list)
        for c, l_, *r in rects:
            if l_ == L:
                bycls[c].append(r)
        for c, rs in sorted(bycls.items()):
            A = np.zeros((ny, nx) if horiz else (nx, ny), dtype=np.float32)
            for x0, y0, x1, y1 in rs:
                # along = the preferred axis (H: x), across = the track axis (H: y)
                al0, al1, ac0, ac1 = (x0, x1, y0, y1) if horiz else (y0, y1, x0, x1)
                tr = max(1.0, math.ceil((ac1 - ac0) / pitch - 1e-6))
                j0 = int(max(0, (ac0 + ac1) / 2 // g))
                i0, i1 = int(max(0, al0 // g)), int(min(A.shape[1] - 1, max(0, (al1 - 1e-6) // g)))
                if j0 >= A.shape[0]:
                    continue
                A[j0, i0:i1 + 1] += tr
            A = np.minimum(A, cap)
            res[c] = float(A.sum() / (A.size * cap))
            tot = A if tot is None else np.minimum(tot + A, cap)
        res["all"] = float(tot.sum() / (tot.size * cap)) if tot is not None else 0.0
        out[L] = {k: round(v, 5) for k, v in res.items()}
    return out


def write_def(P, path, shapes):
    """preroute.def: DIEAREA + SPECIALNETS (every pre-route FIXED, rect shapes as width paths)."""
    by = defaultdict(list)
    use = {}
    for net, cls, L, x0, y0, x1, y1, shape in shapes:
        by[net].append((L, x0, y0, x1, y1, shape))
        use[net] = {"pg": "POWER" if net == "VDD" else "GROUND", "clock": "CLOCK", "reset": "RESET",
                    "start": "SIGNAL"}[cls] if cls != "pg" or net in ("VDD", "VSS") else "POWER"

    def u(v):
        return int(round(v * DBU))
    with open(path, "w") as f:
        f.write(f"VERSION 5.8 ;\nDIVIDERCHAR \"/\" ;\nBUSBITCHARS \"[]\" ;\nDESIGN {P.name}_preroute ;\n"
                f"UNITS DISTANCE MICRONS {DBU} ;\nDIEAREA ( 0 0 ) ( {u(P.W)} {u(P.H)} ) ;\n"
                f"SPECIALNETS {len(by)} ;\n")
        for net in sorted(by):
            f.write(f"- {net}\n")
            first = True
            for L, x0, y0, x1, y1, shape in by[net]:
                horiz = (x1 - x0) >= (y1 - y0)
                w = (y1 - y0) if horiz else (x1 - x0)
                a = (u(x0), u((y0 + y1) / 2)) if horiz else (u((x0 + x1) / 2), u(y0))
                b = (u(x1), a[1]) if horiz else (a[0], u(y1))
                f.write(f"  {'+ FIXED' if first else 'NEW'} {L} {u(w)} + SHAPE {shape} ( {a[0]} {a[1]} ) "
                        f"( {b[0]} {b[1]} )\n")
                first = False
            f.write(f"  + USE {use[net]} ;\n")
        f.write("END SPECIALNETS\nEND DESIGN\n")


def cmd_freeze(a):
    P = load_plan(a.plan)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    shapes, obs, cls_rects = [], [], []
    for net, L, x0, y0, x1, y1 in pg_rects(P, pg_grid(P, a.pg)):
        shapes.append((net, "pg", L, x0, y0, x1, y1, "STRIPE"))
        obs.append((L, x0, y0, x1, y1))
        cls_rects.append(("pg", L, x0 - SIG_S, y0, x1 + SIG_S, y1) if HV[L] == "V" else ("pg", L, x0, y0 - SIG_S, x1, y1 + SIG_S))
    meta = {}
    if a.clock:
        M, crs = clock_rects(a.clock, a.guide)
        _w, s = NDR[M["meta"].get("ndr", "4w")]
        meta["clock"] = dict(dir=str(a.clock), guide=str(a.guide), ndr=M["meta"].get("ndr"), rects=len(crs),
                             nets=len({r[0] for r in crs}))
        for net, L, x0, y0, x1, y1, w in crs:
            shapes.append((net, "clock", L, x0, y0, x1, y1, "STRIPE" if net == "ck_mesh" else "IOWIRE"))
            fp = footprint(L, (x0, y0, x1, y1), w, s)
            obs.append((L,) + fp)
            cls_rects.append(("clock", L) + fp)
    if a.reset:
        R = json.loads(Path(a.reset).read_text())
        meta["reset"] = dict(file=str(a.reset), nets=R["nets"], wire_mm=R["wire_mm"])
        for row in R["wires"]:
            for L, x0, y0, x1, y1 in l_rects(tuple(row["a"]), tuple(row["b"]), SIG_W):
                shapes.append((row["net"], row["kind"], L, x0, y0, x1, y1, "IOWIRE"))
                fp = footprint(L, (x0, y0, x1, y1), SIG_W, SIG_S)
                obs.append((L,) + fp)
                cls_rects.append(("reset", L) + fp)
    write_def(P, out / "preroute.def", shapes)
    with open(out / "preroute_obs.tcl", "w") as f:
        f.write(f"# GENERATED by tools/die_plan/die_infra.py freeze: fixed pre-route footprints ({len(obs)} rects)\n")
        for L, x0, y0, x1, y1 in obs:
            f.write(f"create_obstruction -region {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} -layer {L}\n")
    tracks = track_use(P, cls_rects)
    rep = dict(plan=str(a.plan), pg=str(a.pg) if a.pg else "plan die.pg.grid", pg_file=str(Path(a.pg).resolve()) if a.pg else None, shapes=len(shapes), obstructions=len(obs),
               tracks_taken=tracks, **meta)
    (out / "preroute.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------------- kits/GRT
def base_obs(P, pg=None):
    """die_trial obs WITHOUT the old die H-tree reservation: PG stripes (sized grid when given) + band share stripes."""
    import die_trial as DT
    _bl, regs = DT.band_region_adjust(P, 0.75)
    L = [f"create_obstruction -region {{{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}}} -layer {l}"
         for _n, l, x0, y0, x1, y1 in pg_rects(P, pg_grid(P, pg))]
    L += [f"create_obstruction -region {{{a:.3f} {b:.3f} {c:.3f} {d:.3f}}} -layer {l}"
          for l, a, b, c, d in DT.band_share_obs(P, regs)]
    return "\n".join(L) + "\n"


def strip_route(v, keep_reset=False):
    """route.v with every die signal connection removed (clock-alone kit) or only the legacy reset spine removed."""
    if keep_reset:
        return v
    return re.sub(r"\(\s*\.arst_n\(rst_n\)[^;]*\);", "();", v)


def cmd_clockkit(a):
    P = load_plan(a.plan)
    kit, out = Path(a.kit).resolve(), Path(a.out)
    (out / "grt").mkdir(parents=True, exist_ok=True)
    ab = out / "abstracts"
    if not ab.exists():
        ab.symlink_to((kit / "abstracts").resolve())
    for f in ("grt.tcl", "tracks.tcl"):
        (out / "grt" / f).write_text((kit / "grt" / f).read_text())
    (out / "grt" / "obs.tcl").write_text(base_obs(P, a.pg))
    v = (kit / "grt" / "route.v").read_text()
    (out / "grt" / "route.v").write_text(strip_route(v))
    (out / "kit.json").write_text(json.dumps(dict(base_kit=str(kit), pg=str(a.pg) if a.pg else None,
                                                  note="die_infra clockkit: partitions + PG + bands, no signal nets"),
                                             indent=1) + "\n")
    print("clock-alone kit", out)
    return 0


def cmd_grt(a):
    P = load_plan(a.plan)
    kit, pre, out = Path(a.kit).resolve(), Path(a.pre).resolve(), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pg = a.pg or json.loads((pre / "preroute.json").read_text()).get("pg_file")
    (out / "obs_base.tcl").write_text(base_obs(P, pg))
    v = (kit / "grt" / "route.v").read_text()
    # the reset is a pre-route now: drop the legacy reset spine (.arst_n(rst_n) on every partition)
    (out / "route.v").write_text(re.sub(r"\.arst_n\(rst_n\),?\s*", "", v).replace(", )", ")"))
    t = (kit / "grt" / "grt.tcl").read_text()
    t = t.replace("read_verilog /work/grt/route.v", "read_verilog /out/route.v")
    t = t.replace("source /work/grt/obs.tcl", "source /out/obs_base.tcl\nsource /pre/preroute_obs.tcl")
    if a.m89:
        t = t.replace("set_routing_layers -signal M4-M7", "set_routing_layers -signal M4-M9")
        t = t.replace("global_route ", "set_global_routing_layer_adjustment M8 0\nset_global_routing_layer_adjustment "
                                       "M9 0\nglobal_route ", 1)
    t = re.sub(r"-congestion_iterations \d+", f"-congestion_iterations {a.iterations}", t)
    t = t.replace("/work/grt/congestion.rpt", "/out/congestion.rpt").replace("/work/grt/route.guide", "/out/route.guide")
    (out / "grt.tcl").write_text(t)
    (out / "run_grt.sh").write_text(f"""#!/bin/bash
# GENERATED by die_infra.py grt: die signal GRT on the leftover of the fixed pre-routes (launch via ot-run --mem {a.mem})
D=$(cd $(dirname $0) && pwd); K={kit}; PRE={pre}
docker run --rm --name dinfra-grt-$(basename $D)-$$ --cpus=${{CPUS:-16}} --memory=${{MEM:-{a.mem}}}g --memory-swap=${{MEM:-{a.mem}}}g \\
  -v $K:/work:ro -v $(readlink -f $K/abstracts):/work/abstracts:ro -v $PRE:/pre:ro -v $D:/out openroad/orfs:latest \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 16 -exit /out/grt.tcl > /out/grt.log 2>&1; echo EXIT \\$? >> /out/grt.log; chown -R $(id -u):$(id -g) /out"
""")
    (out / "run_grt.sh").chmod(0o755)
    print("grt written", out / "grt.tcl")
    return 0


# --------------------------------------------------------------------------------------------------------- report
def parse_grt(log):
    """per-layer resource / demand / usage / overflow of the final GRT congestion report + total overflow."""
    rows, tot = {}, None
    txt = Path(log).read_text(errors="replace")
    blk = txt[txt.rfind("Final congestion report"):] if "Final congestion report" in txt else txt
    for m in re.finditer(r"^\s*(M\d+)\s+(-?\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", blk, re.M):
        rows[m.group(1)] = dict(resource=int(m.group(2)), demand=int(m.group(3)), usage_pct=float(m.group(4)),
                                overflow=int(m.group(7)))
    m = re.search(r"^\s*Total\s+(-?\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", blk, re.M)
    if m:
        tot = int(m.group(6))
    return dict(layers=rows, total_overflow=tot if tot is not None else sum(r["overflow"] for r in rows.values()),
                exit=(re.findall(r"EXIT (\d+)", txt) or [None])[-1])


def cmd_report(a):
    rep = {}
    pre = json.loads((Path(a.pre) / "preroute.json").read_text())
    rep["tracks_taken"] = pre["tracks_taken"]
    rep["leftover_M8_M9"] = {L: round(1 - v["all"], 4) for L, v in pre["tracks_taken"].items()}
    for g in a.grt or []:
        rep.setdefault("grt", {})[str(g)] = parse_grt(Path(g) / "grt.log")
    if a.clock:
        cr = json.loads((Path(a.clock) / "clock_report.json").read_text())
        rep["clock"] = {c: {k: r[k] for k in ("related_pair_max_ps", "verdict", "pairs_over_80", "seam_max_ps",
                                             "intra_max_ps", "insertion_ps", "tap_slew_max_ps", "clock_wire_power_W")
                            if k in r} for c, r in cr["corners"].items()}
    if a.pg:
        pg = json.loads(Path(a.pg).read_text())
        rep["pg"] = {k: pg.get(k) for k in ("grid", "tracks", "regions", "psm")}
    if a.sites:
        rep["islands"] = json.loads(Path(a.sites).read_text()).get("types_summary") or \
            json.loads(Path(a.sites).read_text())
    Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1)[:4000])
    return 0


# --------------------------------------------------------------------------------------------------------- render
def cmd_render(a):
    """the frozen pre-routes from preroute.def: partitions (grey), hard cores / keep-outs (light), PG (VDD orange /
    VSS brown, thin), clock (mesh straps blue, routed clock nets red), reset (green) / START (purple).  --window
    x0,y0,x1,y1 crops a zoom (PG stripes are 4 um apart, so only a zoom shows them one by one)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Rectangle
    import die_clock as DC
    P = load_plan(a.plan)
    win = [float(v) for v in a.window.split(",")] if a.window else [0, 0, P.W, P.H]
    ww, wh = win[2] - win[0], win[3] - win[1]
    sc = max(ww, wh) / 18.0
    fig, ax = plt.subplots(figsize=(ww / sc, wh / sc), dpi=a.dpi)

    def inwin(r):
        return r[2] >= win[0] and r[0] <= win[2] and r[3] >= win[1] and r[1] <= win[3]
    for n in P.parts:
        r = P.rect(n)
        if inwin(r):
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, lw=0.25, ec="0.55"))
            if a.window:
                ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, n, fontsize=4, color="0.4", ha="center")
    for r in DC.keepouts(P):
        if inwin(r):
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="0.88", ec="none"))
    col = {"VDD": "tab:orange", "VSS": "saddlebrown", "ck_mesh": "tab:blue"}
    polys = defaultdict(list)
    net, use = None, None
    pend = []
    for line in open(Path(a.pre) / "preroute.def"):
        m_ = re.match(r"- (\S+)", line)
        if m_:
            net, pend = m_.group(1), []
            continue
        m_ = re.search(r"(?:FIXED|NEW) (M\d) (\d+) \+ SHAPE \w+ \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", line)
        if m_:
            L, w, x0, y0, x1, y1 = m_.group(1), int(m_.group(2)) / DBU, *(int(v) / DBU for v in m_.groups()[2:])
            h = w / 2                                  # edges (linewidths) keep thin wires visible
            r = (min(x0, x1) - (h if x0 == x1 else 0), min(y0, y1) - (h if y0 == y1 else 0),
                 max(x0, x1) + (h if x0 == x1 else 0), max(y0, y1) + (h if y0 == y1 else 0))
            pend.append(r)
            continue
        m_ = re.search(r"\+ USE (\w+)", line)
        if m_ and net:
            use = m_.group(1)
            key = net if net in col else {"CLOCK": "clock", "RESET": "reset"}.get(use, "start" if net.startswith(
                ("stw_", "start")) else "other")
            if key in ("VDD", "VSS") and not a.window and not a.pg_full:
                pend = pend[::max(1, int(len(pend) / 300))]   # die view: a sample of the stripes (they are ~4 um apart)
            polys[key] += [[(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])] for r in pend if inwin(r)]
            net = None
    col.update(clock="tab:red", reset="tab:green", start="tab:purple", other="k")
    lw = {"VDD": 0.15, "VSS": 0.15, "ck_mesh": 0.4, "clock": 0.6, "reset": 0.8, "start": 0.5, "other": 0.3}
    for k in ("VDD", "VSS", "ck_mesh", "clock", "start", "reset", "other"):
        if polys.get(k):
            ax.add_collection(PolyCollection(polys[k], facecolors=col[k], edgecolors=col[k], linewidths=lw[k],
                                             alpha=0.5 if k in ("VDD", "VSS") else 0.9, label=f"{k} ({len(polys[k])})"))
    rep = json.loads((Path(a.pre) / "preroute.json").read_text())
    tt = rep["tracks_taken"]
    ax.set_xlim(win[0], win[2])
    ax.set_ylim(win[1], win[3])
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=5)
    ax.set_title(f"{P.name} infra-first fixed pre-routes: M8 taken {tt['M8']['all']:.1%} "
                 f"({', '.join(f'{k} {v:.1%}' for k, v in tt['M8'].items() if k != 'all')}), M9 taken "
                 f"{tt['M9']['all']:.1%} ({', '.join(f'{k} {v:.1%}' for k, v in tt['M9'].items() if k != 'all')})"
                 + (f"  window {win}" if a.window else ""), fontsize=6)
    out = a.out or str(Path(a.pre) / ("preroute_zoom.png" if a.window else "preroute.png"))
    fig.savefig(out, bbox_inches="tight")
    print(out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pg")
    p.add_argument("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--ir-budget-frac", type=float, default=0.05)
    p.add_argument("--vdd", type=float, default=0.7)
    p.add_argument("--phy-w", type=float, default=4.37)
    p.add_argument("--core-w-mm2", type=float)
    r = sub.add_parser("reset")
    r.add_argument("plan")
    r.add_argument("--out", required=True)
    k = sub.add_parser("clockkit")
    k.add_argument("plan")
    k.add_argument("--kit", required=True)
    k.add_argument("--out", required=True)
    k.add_argument("--pg")
    t = sub.add_parser("trim")
    t.add_argument("dir")
    t.add_argument("--offsets", required=True, help="JSON {tap port | part.tap | part: measured - planned insertion ps}")
    t.add_argument("--out", required=True)
    t.add_argument("--plan")
    t.add_argument("--corner", default="TT")
    t.add_argument("--quantum-ps", type=float, help="trim pad delay (default: BUFx24 pad delay from the liberty)")
    t.add_argument("--reserve", type=int, help="nominal trim pads per stub (tiles may be faster or slower than plan)")
    t.add_argument("--libdir", default=str(Path("~/.cache/opentallas/asap7_nldm").expanduser()))
    f = sub.add_parser("freeze")
    f.add_argument("plan")
    f.add_argument("--out", required=True)
    f.add_argument("--pg")
    f.add_argument("--clock")
    f.add_argument("--guide")
    f.add_argument("--reset")
    g = sub.add_parser("grt")
    g.add_argument("plan")
    g.add_argument("--kit", required=True)
    g.add_argument("--pre", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--pg")
    g.add_argument("--m89", action="store_true", help="signals may also use the leftover M8/M9 (FT-M89-PROBE)")
    g.add_argument("--iterations", type=int, default=50)
    g.add_argument("--mem", type=int, default=256)
    q = sub.add_parser("report")
    q.add_argument("--pre", required=True)
    q.add_argument("--grt", action="append")
    q.add_argument("--clock")
    q.add_argument("--pg")
    q.add_argument("--sites")
    q.add_argument("--out", required=True)
    v = sub.add_parser("render")
    v.add_argument("plan")
    v.add_argument("--pre", required=True)
    v.add_argument("--window", help="x0,y0,x1,y1 um zoom")
    v.add_argument("--out")
    v.add_argument("--dpi", type=int, default=200)
    v.add_argument("--pg-full", action="store_true")
    a = ap.parse_args(argv)
    return dict(pg=cmd_pg, reset=cmd_reset, clockkit=cmd_clockkit, trim=cmd_trim, freeze=cmd_freeze, grt=cmd_grt,
                report=cmd_report, render=cmd_render)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
