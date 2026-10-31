#!/usr/bin/env python3
"""ot-clk region MESH form (CLK-TOOL-6, OWNER 12.17(2) one clock tool): config-driven region clock mesh builder.

A region mesh = an equal-leg pre-mesh driver tree (balanced BY CONSTRUCTION, no detours) feeding mesh drivers that sit
under vertical straps on the region's glue tap columns; horizontal straps run along the tap rows; one special net
(the mesh) joins all drivers and tap loads.  Early (off-mesh) taps named by a prefix get their own equal-leg branch from
the region root port.  Hard-core rects of the partition type own the lower layers and placement.

Every die quirk is a key of the config section region.mesh (no defaults: a missing key is a ConfigError, so a build
can never silently take another die's numbers).  The builder writes, per region:
  pilot.json (geom/cells/nets; the schema and file names of the earlier per-die mesh pilot, so its trials replay)
  pilot.def, run.tcl, run_ff.tcl, run.sh   (OpenROAD region run: GRT -> GRT-RC STA dump -> DRT -> RCX -> FF dump)
and `rec` turns a routed trial into the explicit_mesh_signoff rec (shared MC basis, tools/die_plan).

Topology (generic within these bounds, fail-closed otherwise): 2^k glue columns (k=2 wired: root R -> A{L,R} at the
column-pair midpoints -> B{i} at each column on the middle tap row), then per column a vertical binary tree whose leg
lengths are config multiples of the driver pitch (first level carries a repeater P at mid-leg): C (2p, rep at p) ->
D (p) -> mesh drivers M (p/2); 2^3 = 8 drivers per column.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

REQUIRED = ("cols", "rows", "driver_pitch_um", "adjust", "trunk_offset_um", "early_tap_prefix", "driver_master",
            "load_master", "cell_w", "site_name", "site_w", "row_h", "dbu", "pg_pitch", "pg_w", "strap_w", "strap_layers",
            "core_layers", "window_layers", "window", "core_keepout", "core_pin_load_dx", "ndr", "period_ps",
            "routing", "run", "rec")


class MeshConfigError(Exception):
    pass


def params(cfg_mesh):
    if not isinstance(cfg_mesh, dict):
        raise MeshConfigError("region.mesh section missing")
    if cfg_mesh.get("topology", "quad4") == "grid":
        return grid_params(cfg_mesh)
    if cfg_mesh.get("topology", "quad4") != "quad4":
        raise MeshConfigError(f"region.mesh.topology={cfg_mesh['topology']!r}: only quad4 / grid are wired")
    miss = [k for k in REQUIRED if k not in cfg_mesh]
    if miss:
        raise MeshConfigError(f"region.mesh missing keys {miss} (no defaults: every die value is explicit)")
    m = dict(cfg_mesh)
    if m["cols"] != 4:
        raise MeshConfigError(f"region.mesh.cols={m['cols']}: only the 4-column (k=2) trunk is wired")
    for k in (m["driver_master"], m["load_master"]):
        if k not in m["cell_w"]:
            raise MeshConfigError(f"region.mesh.cell_w has no width for {k}")
    return m


def snap_gap(v, pitch):
    """centre of the nearest PG gap (PG stripe centres at pitch*k in the partition frame)"""
    return round((math.floor(v / pitch) * pitch + pitch / 2), 4)


def part_geom(plan, part, m_orient_my=False):
    P = json.load(open(plan))
    pa = {p["name"]: p for p in P["partitions"]}[part]
    T = P["partition_types"][pa["type"]]
    W, H = T["outline_um"]
    cores = []
    for c in T["contents"]:
        if "outline_um" in c and "origin_um" in c:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            if pa["orient"] == "MX":
                y = H - y - h
            elif pa["orient"] == "MY" and m_orient_my:
                x = W - x - w
            elif pa["orient"] != "R0":
                raise MeshConfigError(f"orient {pa['orient']} not handled")
            cores.append(dict(inst=c["inst"], rect=[round(x, 4), round(y, 4), round(x + w, 4), round(y + h, 4)]))
    return pa, T, W, H, cores


def in_core(x, y, cores, m=0.0):
    return any(r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m for r in (c["rect"] for c in cores))


def build(plan, tree_json, part, out, m):
    m = params(m)
    if m.get("topology", "quad4") == "grid":
        return build_grid(plan, tree_json, part, out, m)
    pitch, adjust, pre = float(m["driver_pitch_um"]), m["adjust"], m["early_tap_prefix"]
    DRV, LOAD = m["driver_master"], m["load_master"]
    pa, T, W, H, cores = part_geom(plan, part)
    ox, oy = pa["origin_um"]
    tj = json.load(open(tree_json))
    taps = [t for t in tj["taps"] if t["part"] == part]
    glue = [dict(t, lx=round(t["xy"][0] - ox, 4), ly=round(t["xy"][1] - oy, 4)) for t in taps if not t["tap"].startswith(pre)]
    core = [dict(t, lx=round(t["xy"][0] - ox, 4), ly=round(t["xy"][1] - oy, 4)) for t in taps if t["tap"].startswith(pre)]
    rows = sorted({g["ly"] for g in glue})
    ymid = rows[len(rows) // 2]
    cols = sorted({g["lx"] for g in glue if g["ly"] != ymid})
    if len(cols) != m["cols"] or len(rows) != m["rows"]:
        raise MeshConfigError(f"{part}: {len(cols)} glue columns x {len(rows)} tap rows, config says "
                              f"{m['cols']} x {m['rows']}: {cols} {rows}")
    rx = (cols[1] + cols[2]) / 2
    cells, nets = {}, {}
    ko = m["core_keepout"]

    def cell(name, x, y, master=DRV):
        if in_core(x, y, cores, ko):
            raise MeshConfigError(f"{name} at ({x:.1f},{y:.1f}) lands on a hard core")
        cells[name] = dict(master=master, x=x, y=y)

    def net(name, drv, loads, kind="tree"):
        nets[name] = dict(drv=drv, loads=loads, kind=kind)
    cell("R", rx, ymid)
    net("n_root", "port:root", ["R"])
    A = {"L": (cols[0] + cols[1]) / 2, "R": (cols[2] + cols[3]) / 2}
    for s, x in A.items():
        cell(f"A{s}", x, ymid)
    net("n_R", "R", ["AL", "AR"])
    for i, x in enumerate(cols):
        cell(f"B{i}", x, ymid)
    net("n_AL", "AL", ["B0", "B1"]); net("n_AR", "AR", ["B2", "B3"])
    drivers = []
    off = float(m["trunk_offset_um"])
    for i, x in enumerate(cols):
        xs = x + (off if i in (0, 2) else -off)       # keep the trunk cells inside the glue strip/channel
        for sgn, s in ((1, "u"), (-1, "d")):
            cell(f"P{i}{s}", xs, ymid + sgn * pitch)        # repeater on the 2p leg
            cell(f"C{i}{s}", x, ymid + sgn * 2 * pitch)
            Cn = f"C{i}{s}"
            for sg2, s2 in ((1, "u"), (-1, "d")):
                Dn = f"D{i}{s}{s2}"
                cell(Dn, xs, ymid + sgn * 2 * pitch + sg2 * pitch)
                ds = []
                for sg3, s3 in ((1, "u"), (-1, "d")):
                    dn = f"M{i}{s}{s2}{s3}"
                    cell(dn, x, ymid + sgn * 2 * pitch + sg2 * pitch + sg3 * pitch / 2)
                    drivers.append(dn); ds.append(dn)
                net(f"n_{Dn}", Dn, ds)
            net(f"n_{Cn}", Cn, [f"D{i}{s}u", f"D{i}{s}d"])
            net(f"n_P{i}{s}", f"P{i}{s}", [Cn])
        net(f"n_B{i}", f"B{i}", [f"P{i}u", f"P{i}d"])
    # early (off-mesh) tap branch, equal legs by construction: E0 at the y midpoint of the two early-tap rows (fed from
    # the region root port), repeaters Q at the leg midpoints, E1 at each early-tap row
    ey = sorted({c["ly"] for c in core})
    if len(ey) != 2:
        raise MeshConfigError(f"{part}: early taps on {len(ey)} rows, the early branch needs exactly 2: {ey}")
    em = (ey[0] + ey[1]) / 2
    cell("E0", rx, em)
    net("n_root", "port:root", ["R", "E0"])
    qs = []
    dx_in, dx_out = m["core_pin_load_dx"]
    for j, y in enumerate(ey):
        cell(f"Q{j}", rx + off, (em + y) / 2); qs.append(f"Q{j}")
        cell(f"E1_{j}", rx, y)
        net(f"n_Q{j}", f"Q{j}", [f"E1_{j}"])
        loads = []
        for c in core:
            if c["ly"] == y:
                n = "L_" + c["tap"]
                x = c["lx"]       # the core clock pin is on the core edge: its load cell sits just outside, in the channel
                for r in (q["rect"] for q in cores):
                    if r[0] - dx_in <= x <= r[2] + dx_in and r[1] <= c["ly"] <= r[3]:
                        x = r[2] + dx_in if abs(x - r[2]) < abs(x - r[0]) else r[0] - dx_out
                cell(n, x, c["ly"], LOAD); loads.append(n)
        net(f"n_E1_{j}", f"E1_{j}", loads)
    net("n_E0", "E0", qs)
    # mesh
    pg = float(m["pg_pitch"])
    vx = {i: snap_gap(x, pg) for i, x in enumerate(cols)}
    hy = {y: snap_gap(y, pg) for y in rows}
    ylo = min(min(rows), min(cells[d]["y"] for d in drivers)) - 2
    yhi = max(max(rows), max(cells[d]["y"] for d in drivers)) + 2
    xlo, xhi = min(vx.values()), max(vx.values())
    mesh_loads = []
    for g in glue:
        n = "L_" + g["tap"]; cell(n, g["lx"], g["ly"], LOAD); mesh_loads.append(n)
    for d in drivers:      # put the driver centre under its strap
        i = int(d[1]); cells[d]["x"] = vx[i]
    net("ck_mesh", drivers, mesh_loads, kind="mesh")
    wid, SW, RH = m["cell_w"], m["site_w"], m["row_h"]
    for c in cells.values():          # centre -> lower-left on the site grid; legalize overlaps (shift right)
        c["x"] = round(round((c["x"] - wid[c["master"]] / 2) / SW) * SW, 4)
        c["y"] = round(round((c["y"]) / RH) * RH, 4)
    occ = {}
    for n in sorted(cells):
        c = cells[n]
        while any(abs(c["y"] - o["y"]) < 1e-6 and c["x"] < o["x"] + wid[o["master"]] and o["x"] < c["x"] + wid[c["master"]]
                  for o in occ.values()):
            c["x"] = round(c["x"] + SW * 2, 4)
        if in_core(c["x"], c["y"], cores, 0.0) or in_core(c["x"] + wid[c["master"]], c["y"], cores, 0.0):
            raise MeshConfigError(f"{n} legalized onto a hard core")
        occ[n] = c
    geom = dict(part=part, origin=[ox, oy], W=W, H=H, cores=cores, cols=cols, rows=rows, ymid=ymid, root=[rx, ymid],
                vx=[vx[i] for i in range(4)], hy=[hy[y] for y in rows], y_span=[ylo, yhi], x_span=[xlo, xhi],
                drivers=drivers, mesh_loads=mesh_loads, glue_taps=[g["port"] for g in glue],
                core_taps=[c["port"] for c in core], adjust=adjust, driver_pitch_um=pitch,
                tap_xy={("L_" + g["tap"]): [g["lx"], g["ly"]] for g in glue + core})
    o = Path(out); o.mkdir(parents=True, exist_ok=True)
    json.dump(dict(geom=geom, cells=cells, nets=nets), open(o / "pilot.json", "w"), indent=1)
    write_def(o, geom, cells, nets, m)
    write_tcl(o, geom, m)
    return dict(part=part, cells=len(cells), drivers=len(drivers), nets=len(nets), cols=cols, rows=rows, root=geom["root"])


# ------------------------------------------------------------------------------------------------- grid topology
GRID_REQUIRED = ("grid", "adjust", "driver_master", "load_master", "cell_w", "site_name", "site_w", "row_h", "dbu",
                 "pg_pitch", "pg_w", "strap_w", "strap_layers", "core_layers", "window_layers", "window", "core_keepout",
                 "ndr", "period_ps", "routing", "run", "rec")
GRID_KEYS = ("v_straps", "h_straps", "drivers_per_col", "rep_max_um", "legal_step_um", "legal_max_um", "root", "early")


def grid_params(cfg_mesh):
    """region.mesh.topology: grid (opt-in; the quad4 form and its bytes are untouched).  A uniform strap grid over the
    whole partition: grid.v_straps vertical straps (strap_layers.v) x grid.h_straps horizontal straps (strap_layers.h),
    grid.drivers_per_col drivers under every vertical strap, fed by a zero-skew merge tree (pre-mesh, Manhattan legs on the
    strap layers over the hard cores, merge/repeater cells slid off the cores onto the nearest glue site, repeaters every
    <= grid.rep_max_um).  Taps need not sit on a lattice: each tap gets its mesh load cell on the nearest off-core point of
    a horizontal strap; the load->tap stub length is reported (it is the root net of the tap's local tree)."""
    miss = [k for k in GRID_REQUIRED if k not in cfg_mesh]
    if miss:
        raise MeshConfigError(f"region.mesh missing keys {miss} (no defaults: every die value is explicit)")
    m = dict(cfg_mesh)
    g = m["grid"]
    if not isinstance(g, dict):
        raise MeshConfigError("region.mesh.grid must be a mapping")
    miss = [k for k in GRID_KEYS if k not in g]
    if miss:
        raise MeshConfigError(f"region.mesh.grid missing keys {miss}")
    for k in ("v_straps", "h_straps", "drivers_per_col"):
        if int(g[k]) < 1:
            raise MeshConfigError(f"region.mesh.grid.{k} must be >= 1")
    if int(g["drivers_per_col"]) % 2:
        raise MeshConfigError("region.mesh.grid.drivers_per_col must be even (leaf nodes drive driver pairs)")
    if g["root"] not in ("plan_entry", "centre"):
        raise MeshConfigError("region.mesh.grid.root must be plan_entry or centre")
    if g["early"] != "none":
        raise MeshConfigError("region.mesh.grid.early: only 'none' is wired (every tap on the mesh)")
    for k in (m["driver_master"], m["load_master"]):
        if k not in m["cell_w"]:
            raise MeshConfigError(f"region.mesh.cell_w has no width for {k}")
    return m


def legal_pt(x, y, cores, W, H, ko, step, maxd):
    """nearest off-core point (centre) on rings of radius step, 2*step, ... (angles every 5 deg, deterministic)"""
    if not in_core(x, y, cores, ko) and 0 < x < W and 0 < y < H:
        return round(x, 4), round(y, 4), 0.0
    d = step
    while d <= maxd + 1e-9:
        for a in range(0, 360, 5):
            xx, yy = x + d * math.cos(math.radians(a)), y + d * math.sin(math.radians(a))
            if 0 < xx < W and 0 < yy < H and not in_core(xx, yy, cores, ko):
                return round(xx, 4), round(yy, 4), round(abs(xx - x) + abs(yy - y), 4)
        d += step
    raise MeshConfigError(f"no glue site within {maxd} um of ({x:.1f},{y:.1f})")


def lpath(a, b, t):
    """point at Manhattan distance t from a along the x-first L route a -> b"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if t <= abs(dx):
        return (a[0] + math.copysign(t, dx) if dx else a[0], a[1])
    t2 = min(t - abs(dx), abs(dy))
    return (b[0], a[1] + math.copysign(t2, dy) if dy else a[1])


def manh(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def plan_entry(T, pa, W, H):
    x, y = T["clock"]["tap_um"]
    if pa["orient"] == "MX":
        y = H - y
    elif pa["orient"] == "MY":
        x = W - x
    return x, y


def build_grid(plan, tree_json, part, out, m):
    G = m["grid"]
    DRV, LOAD = m["driver_master"], m["load_master"]
    pa, T, W, H, cores = part_geom(plan, part, m_orient_my=True)
    ox, oy = pa["origin_um"]
    step, maxd, rep = float(G["legal_step_um"]), float(G["legal_max_um"]), float(G["rep_max_um"])
    # a cell centre is legal when its widest master + row snap stays off every core (+ core_keepout)
    ko = float(m["core_keepout"]) + max(m["cell_w"].values()) + float(m["row_h"])
    tj = json.load(open(tree_json))
    taps = [dict(t, lx=round(t["xy"][0] - ox, 4), ly=round(t["xy"][1] - oy, 4)) for t in tj["taps"] if t["part"] == part]
    if not taps:
        raise MeshConfigError(f"{part}: no taps in {tree_json}")
    pg = float(m["pg_pitch"])
    nv, nh, nd = int(G["v_straps"]), int(G["h_straps"]), int(G["drivers_per_col"])
    vx = [snap_gap((i + 0.5) * W / nv, pg) for i in range(nv)]
    hy = [snap_gap((j + 0.5) * H / nh, pg) for j in range(nh)]
    cells, nets, slides, snake = {}, {}, {}, {}

    def put(name, x, y, master=DRV):
        lx, ly, s = legal_pt(x, y, cores, W, H, ko, step, maxd)
        cells[name] = dict(master=master, x=lx, y=ly)
        if s:
            slides[name] = s
        return (lx, ly)
    drivers, anchor = [], {}
    for i, x in enumerate(vx):
        for k in range(nd):
            n = f"M{i}_{k}"
            ay = round((k + 0.5) * H / nd, 4)
            put(n, x, ay)
            anchor[n] = [x, ay]
            drivers.append(n)
    # zero-skew merge tree over the drivers (bisect the longer side of the driver index box; leaves = driver pairs)
    cnt = [0]

    def merge(a, b):
        D = manh(a["p"], b["p"])
        e = min(max((D + b["T"] - a["T"]) / 2.0, 0.0), D)
        x, y = lpath(a["p"], b["p"], e)
        cnt[0] += 1
        n = f"N{cnt[0]}"
        p = put(n, x, y)
        la, lb = manh(p, a["p"]) + a["T"], manh(p, b["p"]) + b["T"]
        Tm = max(la, lb)
        sk = a["n"] if la < lb else b["n"]
        if abs(la - lb) > 1e-6:
            snake[sk] = round(abs(la - lb), 4)
        return dict(n=n, p=p, T=Tm, kids=[a, b])

    def tree(i0, i1, k0, k1):
        if i1 - i0 == 1 and k1 - k0 == 2:
            a, b = (dict(n=f"M{i0}_{k}", p=(cells[f"M{i0}_{k}"]["x"], cells[f"M{i0}_{k}"]["y"]), T=0.0, kids=[])
                    for k in (k0, k0 + 1))
            return merge(a, b)
        if (i1 - i0) >= (k1 - k0) / 2 and i1 - i0 > 1:
            im = (i0 + i1) // 2
            return merge(tree(i0, im, k0, k1), tree(im, i1, k0, k1))
        km = k0 + 2 * ((k1 - k0) // 4) if (k1 - k0) >= 4 else k0 + 2
        return merge(tree(i0, i1, k0, km), tree(i0, i1, km, k1))
    top = tree(0, nv, 0, nd)
    if G["root"] == "plan_entry":
        rx, ry = plan_entry(T, pa, W, H)
    else:
        rx, ry = W / 2, H / 2
    root = put("R", rx, ry)
    reps = [0]

    def wire(parent_name, ppos, kid):
        """parent -> kid leg with repeaters every <= rep along the x-first L route"""
        L = manh(ppos, kid["p"])
        k = max(0, math.ceil(L / rep - 1e-9) - 1)
        prev = parent_name
        for j in range(1, k + 1):
            x, y = lpath(ppos, kid["p"], L * j / (k + 1))
            reps[0] += 1
            n = f"P{reps[0]}"
            put(n, x, y)
            nets.setdefault(f"n_{prev}", dict(drv=prev, loads=[], kind="tree"))["loads"].append(n)
            prev = n
        nets.setdefault(f"n_{prev}", dict(drv=prev, loads=[], kind="tree"))["loads"].append(kid["n"])

    def emit(node):
        for kid in node["kids"]:
            wire(node["n"], node["p"], kid)
            emit(kid)
    nets["n_root"] = dict(drv="port:root", loads=["R"], kind="tree")
    wire("R", root, top)
    emit(top)
    # taps: load cell on the nearest off-core point of a horizontal strap
    loads, tap_node, tap_xy, stub = [], {}, {}, {}
    for t in sorted(taps, key=lambda t: t["port"]):
        n = "L_" + t["tap"]
        best = None
        for y in sorted(hy, key=lambda v: abs(v - t["ly"]))[:2]:
            d = 0.0
            while d <= maxd:
                hit = None
                for x in (t["lx"] - d, t["lx"] + d):
                    if 0 < x < W and not in_core(x, y, cores, ko):
                        hit = x
                        break
                if hit is not None:
                    c = abs(hit - t["lx"]) + abs(y - t["ly"])
                    if best is None or c < best[0]:
                        best = (c, hit, y)
                    break
                d += step
        if best is None:
            raise MeshConfigError(f"{t['tap']}: no off-core strap point within {maxd} um")
        c, x, y = best
        cells[n] = dict(master=LOAD, x=round(x, 4), y=round(y, 4))
        loads.append(n)
        tap_node[n] = [round(x, 4), y]
        tap_xy[n] = [t["lx"], t["ly"]]
        stub[n] = round(c, 4)
    wid, SW, RH = m["cell_w"], m["site_w"], m["row_h"]
    for c in cells.values():          # centre -> lower-left on the site grid; legalize overlaps (shift right)
        c["x"] = round(round((c["x"] - wid[c["master"]] / 2) / SW) * SW, 4)
        c["y"] = round(round(c["y"] / RH) * RH, 4)
    occ = []
    for n in sorted(cells):
        c = cells[n]
        while any(abs(c["y"] - o["y"]) < 1e-6 and c["x"] < o["x"] + wid[o["master"]] and o["x"] < c["x"] + wid[c["master"]]
                  for o in occ):
            c["x"] = round(c["x"] + SW * 2, 4)
        if in_core(c["x"], c["y"], cores, 0.0) or in_core(c["x"] + wid[c["master"]], c["y"], cores, 0.0):
            raise MeshConfigError(f"{n} legalized onto a hard core")
        occ.append(c)
    _mesh_net("ck_mesh", nets, drivers, loads)
    dpin = {}
    for d in drivers:
        c = cells[d]
        cx = round(c["x"] + wid[DRV] / 2, 4)
        if d in slides:
            dpin[d] = [cx, round(c["y"] + m["rec"]["driver_pin_dy"], 4)]
        else:
            dpin[d] = [anchor[d][0], round(c["y"] + m["rec"]["driver_pin_dy"], 4)]
            anchor[d] = list(dpin[d])
    ys = [anchor[d][1] for d in drivers] + hy
    geom = dict(part=part, topology="grid", origin=[ox, oy], W=W, H=H, cores=cores, root=list(root), vx=vx, hy=hy,
                rows=hy, y_span=[round(max(0.5, min(ys) - 2), 4), round(min(H - 0.5, max(ys) + 2), 4)],
                x_span=[vx[0], vx[-1]], drivers=drivers, mesh_loads=loads, glue_taps=[t["port"] for t in taps],
                core_taps=[], adjust=m["adjust"], tap_xy=tap_xy, tap_node=tap_node, drv_anchor=anchor, drv_pin=dpin,
                load_stub_um=stub, slides=slides, snake_um=snake, path_um=round(top["T"] + manh(root, top["p"]), 4))
    o = Path(out); o.mkdir(parents=True, exist_ok=True)
    json.dump(dict(geom=geom, cells=cells, nets=nets), open(o / "pilot.json", "w"), indent=1)
    write_def(o, geom, cells, nets, m)
    write_tcl(o, geom, m)
    sv = sorted(slides.values())
    return dict(part=part, topology="grid", cells=len(cells), drivers=len(drivers), loads=len(loads), nets=len(nets),
                repeaters=reps[0], merges=cnt[0], slid=len(sv), slide_max=sv[-1] if sv else 0.0,
                snake_mm=round(sum(snake.values()) / 1e3, 3), path_um=geom["path_um"],
                stub_max=max(stub.values()), stub_mean=round(sum(stub.values()) / len(stub), 2), root=geom["root"])


def _mesh_net(name, nets, drv, loads):
    nets[name] = dict(drv=drv, loads=loads, kind="mesh")


def strap_keepout(g, m):
    """opt-in region.mesh.strap_keepout_um (COORD 10-29 mesh keep-out form; absent or 0 = no blockage, old bytes): a
    routing blockage band of that width on the strap layer along both sides of every mesh strap (vertical straps on the
    v layer over y_span, horizontal straps on the h layer over x_span).  The straps are the special net ck_mesh; the band
    keeps every routed net (tree legs and any die signal) >= the band from the strap even when GRT demotes a clock NDR
    to the default rule under congestion (GRT-0273 soft NDR; 10-29 routed-clip failure: a leg shorted onto a strap)."""
    k = float(m.get("strap_keepout_um") or 0)
    if k < 0:
        raise MeshConfigError("region.mesh.strap_keepout_um must be >= 0")
    if not k:
        return []
    u = lambda v: int(round(v * m["dbu"]))
    hl, vl = m["strap_layers"]["h"], m["strap_layers"]["v"]
    h = float(m["strap_w"]) / 2
    (y0, y1), (x0, x1) = g["y_span"], g["x_span"]
    out = []
    for x in g["vx"]:
        for a, b in ((x - h - k, x - h), (x + h, x + h + k)):
            out.append(f"- LAYER {vl} RECT ( {u(a)} {u(y0)} ) ( {u(b)} {u(y1)} ) ;")
    for y in g["hy"]:
        for a, b in ((y - h - k, y - h), (y + h, y + h + k)):
            out.append(f"- LAYER {hl} RECT ( {u(x0)} {u(a)} ) ( {u(x1)} {u(b)} ) ;")
    return out


def write_def(o, g, cells, nets, m):
    W, H = g["W"], g["H"]
    DBU, RH, SW, PG = m["dbu"], m["row_h"], m["site_w"], float(m["pg_pitch"])
    hl, vl = m["strap_layers"]["h"], m["strap_layers"]["v"]
    via = m["strap_layers"]["via"]
    u = lambda v: int(round(v * DBU))
    L = ["VERSION 5.8 ;", "DIVIDERCHAR \"/\" ;", "BUSBITCHARS \"[]\" ;", "DESIGN pilot ;", f"UNITS DISTANCE MICRONS {DBU} ;",
         f"DIEAREA ( 0 0 ) ( {u(W)} {u(H)} ) ;"]
    nrow, nsite = int(H / RH), int(W / SW)
    for r in range(nrow):
        L.append(f"ROW ROW_{r} {m['site_name']} 0 {u(r * RH)} {'N' if r % 2 == 0 else 'FS'} DO {nsite} BY 1 STEP {u(SW)} 0 ;")
    L.append(f"COMPONENTS {len(cells)} ;")
    for n, c in sorted(cells.items()):
        r = int(round(c["y"] / RH))
        L.append(f"- {n} {c['master']} + FIXED ( {u(c['x'])} {u(c['y'])} ) {'N' if r % 2 == 0 else 'FS'} ;")
    L.append("END COMPONENTS")
    rx, ry = g["root"]
    L += ["PINS 1 ;", f"- root + NET n_root + DIRECTION INPUT + USE CLOCK + LAYER {vl} ( -40 -40 ) ( 40 40 ) + FIXED ( {u(snap_gap(rx, PG) + 0.04)} {u(ry)} ) N ;",
          "END PINS"]
    blk = []
    for c in g["cores"]:              # hard cores own the core layers and placement
        x0, y0, x1, y1 = (u(v) for v in c["rect"])
        for lay in m["core_layers"]:
            blk.append(f"- LAYER {lay} RECT ( {x0} {y0} ) ( {x1} {y1} ) ;")
        blk.append(f"- PLACEMENT RECT ( {x0} {y0} ) ( {x1} {y1} ) ;")
    # die clock on the strap layers only (12.1a): window layers blocked everywhere except a pin-access window around
    # each clock cell (y-slabs between windows, x-gaps inside a slab)
    wx0, wy0, wx1, wy1 = m["window"]
    win = sorted((u(c["x"] + wx0), u(c["y"] + wy0), u(c["x"] + wx1), u(c["y"] + wy1)) for c in cells.values())
    ys = sorted({0, u(H)} | {w[1] for w in win} | {w[3] for w in win})
    for ya, yb in zip(ys, ys[1:]):
        xs = sorted((w[0], w[2]) for w in win if w[1] < yb and w[3] > ya)
        free, x = [], 0
        for a, b in xs:
            if a > x:
                free.append((x, a))
            x = max(x, b)
        if x < u(W):
            free.append((x, u(W)))
        for xa, xb in free:
            for lay in m["window_layers"]:
                blk.append(f"- LAYER {lay} RECT ( {xa} {ya} ) ( {xb} {yb} ) ;")
    blk += strap_keepout(g, m)
    L += [f"BLOCKAGES {len(blk)} ;"] + blk + ["END BLOCKAGES"]
    pg = {"VDD": [], "VSS": []}       # special nets: PG stripes on the strap layers (alternate VDD/VSS) + mesh
    k = 0
    while k * PG <= H:
        y = k * PG
        if 0 < y < H:
            pg["VDD" if k % 2 else "VSS"].append(f"NEW {hl} {u(m['pg_w'][hl])} + SHAPE STRIPE ( 0 {u(y)} ) ( {u(W)} {u(y)} )")
        k += 1
    k = 0
    while k * PG <= W:
        x = k * PG
        if 0 < x < W:
            pg["VDD" if k % 2 else "VSS"].append(f"NEW {vl} {u(m['pg_w'][vl])} + SHAPE STRIPE ( {u(x)} 0 ) ( {u(x)} {u(H)} )")
        k += 1
    sn = []
    for nn, segs in pg.items():
        segs[0] = segs[0].replace("NEW ", "", 1)
        sn.append(f"- {nn} + ROUTED " + "\n    ".join(segs) + f" + USE {'POWER' if nn == 'VDD' else 'GROUND'} ;")
    mn = nets["ck_mesh"]
    conn = " ".join(f"( {d} Y )" for d in mn["drv"]) + " " + " ".join(f"( {l} A )" for l in mn["loads"])
    ms = []
    y0, y1 = g["y_span"]
    sw = m["strap_w"]
    for x in g["vx"]:
        ms.append(f"{vl} {u(sw)} + SHAPE STRIPE ( {u(x)} {u(y0)} ) ( {u(x)} {u(y1)} )")
    x0, x1 = g["x_span"]
    for y in g["hy"]:
        ms.append(f"{hl} {u(sw)} + SHAPE STRIPE ( {u(x0)} {u(y)} ) ( {u(x1)} {u(y)} )")
        for x in g["vx"]:
            ms.append(f"{hl} 0 + SHAPE STRIPE ( {u(x)} {u(y)} ) {via}")
    sn.append(f"- ck_mesh {conn} + ROUTED " + "\n    NEW ".join(ms) + " + USE CLOCK ;")
    L += [f"SPECIALNETS {len(sn)} ;"] + sn + ["END SPECIALNETS"]
    reg = [(n, v) for n, v in nets.items() if v["kind"] == "tree"]
    L.append(f"NETS {len(reg)} ;")
    for n, v in reg:
        d = "( PIN root )" if v["drv"] == "port:root" else f"( {v['drv']} Y )"
        L.append(f"- {n} {d} " + " ".join(f"( {l} A )" for l in v["loads"]) + " + USE CLOCK ;")
    L += ["END NETS", "END DESIGN"]
    (o / "pilot.def").write_text("\n".join(L) + "\n")


TCL = r"""
set t0 [clock seconds]
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob $::env(LIBDIR)/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_def /o/pilot.def
source $P/openRoad/make_tracks.tcl
create_clock -name dck -period @PERIOD@ [get_ports root]
set_routing_layers -signal @SIGNAL@ -clock @CLOCK@
@ADJ_LINES@
# die clock on @HL@/@VL@ only (12.1a: M1-M7 belong to the partition/cores); M2-M7 only for the pin stacks
foreach L {@BLOCKED@} { set_global_routing_layer_adjustment $L @BLOCKED_ADJ@ }
create_ndr -name @NDR@ -width {@NDR_W@} -spacing {@NDR_S@}
foreach n [get_nets n_*] { assign_ndr -ndr @NDR@ -net [get_full_name $n] }
global_route -congestion_iterations @GRT_IT@ -allow_congestion -verbose
write_guides /o/route.guide
proc dump {tag corner} {
  set fh [open /o/tree_${tag}_${corner}.txt w]
  foreach c [get_cells *] {
    set n [get_full_name $c]
    if {[string match L_* $n]} { set pins {A} } else { set pins {A Y} }
    foreach pn $pins {
      set p [get_pins $n/$pn]
      puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
    }
  }
  close $fh
}
@EDGES_PROC@proc timing {} {
  create_clock -name vclk -period @PERIOD@
  set_driving_cell -lib_cell @DRV@ -pin Y [get_ports root]
  set_input_delay 0 -clock vclk [get_ports root]
  foreach c [get_cells M*] { set_disable_timing $c }
}
source $P/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
timing
dump grt TT
@EDGES_GRT@puts "OT_T grt [expr {[clock seconds]-$t0}]"
detailed_route -output_drc /o/drc.rpt -verbose 0
puts "OT_T drt [expr {[clock seconds]-$t0}]"
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $P/rcx_patterns.rules
write_spef /o/drt.spef
dump drt TT
@EDGES_DRT@write_db /o/drt.odb
write_def /o/drt.def
puts "OT_DONE [expr {[clock seconds]-$t0}]"
"""

TCL_FF = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $::env(LIBDIR)/*RVT_FF_nldm*.lib*] { read_liberty $f }
read_db /o/drt.odb
read_spef /o/drt.spef
create_clock -name vclk -period @PERIOD@
set_driving_cell -lib_cell @DRV@ -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
foreach c [get_cells M*] { set_disable_timing $c }
set fh [open /o/tree_drt_FF.txt w]
foreach c [get_cells *] {
  set n [get_full_name $c]
  if {[string match L_* $n]} { set pins {A} } else { set pins {A Y} }
  foreach pn $pins {
    set p [get_pins $n/$pn]
    puts $fh "$pn $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
  }
}
close $fh
@EDGES_PROC@@EDGES_FF@puts OT_FF_DONE
"""

# opt-in (region.mesh.edges: both): both-edge readout of every tree cell input in the shared OT_EDGES v1 format
# ('T port rise_late rise_early slew', 'F port fall_late fall_early slew'), so 'ot_clk duty' prices the pre-mesh tree
# on measured fall edges (the BUFx24-only tree low-phase question, clock-duty-distortion 10-28).  Off by default.
EDGES_PROC = r"""proc edges {tag corner} {
  set fh [open /o/edges_${tag}_${corner}.txt w]
  puts $fh "# OT_EDGES v1 region mesh tree inputs (rise: T, fall: F)"
  foreach c [get_cells *] {
    set n [get_full_name $c]
    set p [get_pins $n/A]
    puts $fh "T $n [get_property $p arrival_max_rise] [get_property $p arrival_min_rise] [get_property $p slew_max_rise]"
    puts $fh "F $n [get_property $p arrival_max_fall] [get_property $p arrival_min_fall] [get_property $p slew_max_fall]"
  }
  close $fh
}
"""


def _tcl(text, g, m):
    r = m["routing"]
    hl, vl = m["strap_layers"]["h"], m["strap_layers"]["v"]
    nd = m["ndr"]
    both = m.get("edges", "rise") == "both"
    if m.get("edges", "rise") not in ("rise", "both"):
        raise MeshConfigError("region.mesh.edges must be rise or both")
    rep = {"@PERIOD@": _num(m["period_ps"]), "@SIGNAL@": r["signal"], "@CLOCK@": r["clock"], "@HL@": hl, "@VL@": vl,
           "@ADJ_LINES@": "\n".join(f"set_global_routing_layer_adjustment {L} $::env(ADJ)" for L in r["adjust_layers"]),
           "@BLOCKED@": " ".join(r["blocked_layers"]), "@BLOCKED_ADJ@": _num(r["blocked_adjust"]),
           "@NDR@": nd["name"], "@NDR_W@": " ".join(f"{L} {_num(nd['width'])}" for L in nd["layers"]),
           "@NDR_S@": " ".join(f"{L} {_num(nd['spacing'])}" for L in nd["layers"]), "@GRT_IT@": str(r["grt_iterations"]),
           "@DRV@": m["driver_master"], "@EDGES_PROC@": EDGES_PROC if both else "",
           "@EDGES_GRT@": "edges grt TT\n" if both else "", "@EDGES_DRT@": "edges drt TT\n" if both else "",
           "@EDGES_FF@": "edges drt FF\n" if both else ""}
    for k, v in rep.items():
        text = text.replace(k, v)
    if "@" in text.replace("$::env", ""):
        raise MeshConfigError("unfilled TCL placeholder")
    return text


def _num(v):
    return str(v)


def write_tcl(o, g, m):
    run = m["run"]
    (o / "run.tcl").write_text(_tcl(TCL, g, m))
    (o / "run_ff.tcl").write_text(_tcl(TCL_FF, g, m))
    (o / "run.sh").write_text(f"""#!/bin/bash
O=$(cd $(dirname $0) && pwd)
docker run --rm --name {run['name_prefix']}-$(basename $O)-$$ --memory={run['memory']} --memory-swap={run['memory']} --cpus={run['cpus']} -e ADJ={g['adjust']} -e LIBDIR={run['libdir']} -v $O:/o {run['image']} bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -no_init -threads {run['threads']} -exit /o/run.tcl > /o/run.log 2>&1; rc=$?; echo "EXIT $rc" >> /o/run.log
[ $rc = 0 ] && {{ openroad -no_init -exit /o/run_ff.tcl > /o/run_ff.log 2>&1; echo "EXIT $?" >> /o/run_ff.log; }}
chown -R {_uid()} /o'
""")


def _uid():
    import os
    return f"{os.getuid()}:{os.getgid()}"


# ------------------------------------------------------------------------------------------------- sign-off record
def read_tree(p):
    t = defaultdict(dict)
    for ln in open(p):
        f = ln.split()
        if len(f) < 5:
            continue
        try:
            v = tuple(float(x) for x in f[2:5])
        except ValueError:
            continue
        t[f[1]][f[0]] = v
    return t


def graph(g, m):
    """explicit conductor graph: vertical straps split at every horizontal crossing + driver point; horizontal straps
    split at every vertical crossing + tap point; one via edge at each crossing."""
    hl, vl = m["strap_layers"]["h"], m["strap_layers"]["v"]
    y0, y1 = g["y_span"]
    x0, x1 = g["x_span"]
    drv_pts = defaultdict(set)
    E = []
    for d, (x, y) in (g.get("drv_anchor") or g["drv_xy"]).items():
        drv_pts[x].add(y)
        if g.get("drv_anchor") and [x, y] != list(g["drv_xy"][d]):      # grid: driver slid off a core -> stub to strap
            E.append([[vl, g["drv_xy"][d][0], g["drv_xy"][d][1]], [vl, x, y]])
    tap_pts = defaultdict(set)
    for t, (x, y) in g["tap_node"].items():
        tap_pts[y].add(x)
    for x in g["vx"]:
        ys = sorted({y0, y1} | set(g["hy"]) | drv_pts[x])
        E += [[[vl, x, a], [vl, x, b]] for a, b in zip(ys, ys[1:])]
    for y in g["hy"]:
        xs = sorted({x0, x1} | set(g["vx"]) | tap_pts[y])
        E += [[[hl, a, y], [hl, b, y]] for a, b in zip(xs, xs[1:])]
        E += [[[hl, x, y], [vl, x, y]] for x in g["vx"]]
    return dict(edges=E)


def rec(trial, stage, m, mesh_rc):
    """routed trial -> explicit_mesh_signoff rec (mult-1 drivers), the shared MC basis.  mesh_rc = EMS.mesh_rc."""
    m = params(m)
    T = Path(trial)
    J = json.load(open(T / "pilot.json"))
    g, cells, nets = J["geom"], J["cells"], J["nets"]
    tr = {c: read_tree(T / f"tree_{stage}_{c}.txt") for c in ("TT", "FF") if (T / f"tree_{stage}_{c}.txt").exists()}
    warn = None
    if "FF" not in tr:
        tr["FF"] = tr["TT"]
        warn = f"no FF arrivals for {stage} -> FF = TT (labelled)"
    parent = {}
    for n, v in nets.items():
        if v["kind"] != "tree" or n == "n_E0" or n.startswith(("n_E1", "n_Q")):
            continue
        for l in v["loads"]:
            if l == "E0":
                continue
            parent[l] = None if v["drv"] == "port:root" else v["drv"]
    depth = {}

    def dep(c):
        if c not in depth:
            depth[c] = 1 if parent[c] is None else dep(parent[c]) + 1
        return depth[c]
    hyrow = dict(zip(g["rows"], g["hy"]))
    vl = m["strap_layers"]["v"]
    hl = m["strap_layers"]["h"]
    grid = g.get("topology") == "grid"
    if grid:      # driver pins / strap anchors / tap strap points were fixed by build_grid
        g["drv_xy"] = g["drv_pin"]
    else:
        g["drv_xy"] = {}
        for d in g["drivers"]:
            i = int(d[1])
            g["drv_xy"][d] = [g["vx"][i], round(cells[d]["y"] + m["rec"]["driver_pin_dy"], 4)]
        g["tap_node"] = {}
        for l in g["mesh_loads"]:
            x, y = g["tap_xy"][l]
            g["tap_node"][l] = [x, hyrow[y]]
    G = graph(g, m)
    segs, rcm = mesh_rc(G, m["rec"]["ndr"], m["rec"]["rc"])
    nodes = []
    for c in sorted(parent, key=lambda c: (dep(c), c)):
        drv = c in g["drivers"]
        pin = "A" if drv else "Y"
        arr = {}
        for k, t in tr.items():
            v = t[c][pin]
            arr[k] = dict(late=v[0], early=v[1], slew=v[2])
        p = parent[c]
        leg = abs(cells[c]["x"] - cells[p]["x"]) + abs(cells[c]["y"] - cells[p]["y"]) if p else 0.0
        nodes.append(dict(tag=c, parent=p, depth=dep(c), driver=drv, mult=1, xy=[cells[c]["x"], cells[c]["y"]], arr=arr,
                          anchor=[vl, g["drv_xy"][c][0], g["drv_xy"][c][1]] if drv else None, units=[c], leg_um=max(leg, 1.0)))
    key = lambda p: f"{p[0]}:{float(p[1]):.4f}:{float(p[2]):.4f}"
    lf = m["rec"]["tap_load_ff"]
    taps = [dict(port=l, part=g["part"], kind="published_grid_clock", endpoint_port=l, node=key([hl] + g["tap_node"][l]),
                 xy=g["tap_node"][l], pin_xy=g["tap_xy"][l], jog_um=abs(g["tap_xy"][l][1] - g["tap_node"][l][1]),
                 stub_um=0.0, load_ff=lf) for l in g["mesh_loads"]]
    if grid:      # the load cell sits on the strap (jog 0); its stub to the tap is the tap's local-tree root net (INFO)
        for t in taps:
            t["jog_um"], t["pin_xy"], t["tap_stub_um"] = 0.0, g["tap_node"][t["port"]], g["load_stub_um"][t["port"]]
    root = [n for n in nodes if n["parent"] is None][0]
    out = dict(schema="opentallas.explicit_mesh_rec.v1", source=str(T.resolve()), ndr=m["rec"]["ndr"], rc=rcm, nodes=nodes,
               segs=segs, taps=taps, root_xy=root["xy"], root=root["tag"], tap_load_ff={"published_grid_clock": lf},
               graph=dict(edges=len(G["edges"]), components=1), stage=stage, checked="UNCHECKED")
    (T / f"rec_{stage}.json").write_text(json.dumps(out))
    return out, warn
