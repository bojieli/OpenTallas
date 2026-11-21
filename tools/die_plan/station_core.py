"""STATION-CORE (FABLE-FIX-QC-SLE-R2 11-21): every station row of a type against every hard-macro box, on the kit's site model.

Why: QC sle_ctl__cla4f6f12f sat at 39-43k flat GRT overflow for ten days.  About 7,000 per-bit station flops were planned
on top of its two hard cores (all hard cores and landing macros block M1-M5), detailed placement moved them onto the core
pin rows, and 4,124 of the registered routes crossed a core on M6-M8 only.  No check saw it:
  * kit_istations.core_chain_geometry_errors / chain_macro_hits ran only on rows with a `core` key;
  * istation_clear tests the regs_um centroid, while the kit sites every bit on its own route from leaf_um.
This census uses the kit's own per-bit model for EVERY row (bus chains with the leaf offset, along_first, channel, core
chains with their starts), the regs_um points of packed / centroid rows, the ft slot regs_um and every plan relay_sites
point; a chain whose station flops all carry plan relay_sites (u_ist_<bus>_<k>.q[b], the explicit per-bit form) is read
from those sites.  Advisory: it reports, it never refuses (the core-chain gate is unchanged).

  rows(t, pins, plan_dir=None) -> [dict(kind, conn, stations, bits, sites, sites_in_macro, routes_crossing, macros)]
  report(P, tn, plan_dir=None) -> rows with a finding;  lines(P, tn) -> one text line per finding
  station_core.py PLAN.json [TYPE_RE]      table for every type (run through ot-run for a whole die)"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parents[1])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TOL_UM = 0.5        # kit_istations.MACRO_TOL_UM: a site / leg may touch a macro box, not enter it by more than this


def boxes_of(t):
    return {c["inst"]: (c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
                        c["origin_um"][1] + c["outline_um"][1])
            for c in t.get("hard_cores", []) if "origin_um" in c and "outline_um" in c}


def in_box(p, box, tol=TOL_UM):
    return box[0] + tol < p[0] < box[2] - tol and box[1] + tol < p[1] < box[3] - tol


def seg_in_box(a, c, box, tol=TOL_UM):
    x0, x1, y0, y1 = min(a[0], c[0]), max(a[0], c[0]), min(a[1], c[1]), max(a[1], c[1])
    bx0, by0, bx1, by1 = box[0] + tol, box[1] + tol, box[2] - tol, box[3] - tol
    return bx0 < bx1 and by0 < by1 and x0 < bx1 and x1 > bx0 and y0 < by1 and y1 > by0


def hop_in_box(a, c, box):
    """a registered hop between two FIRM sites has no planned shape: it crosses the box only when BOTH Manhattan Ls do"""
    k1, k2 = (c[0], a[1]), (a[0], c[1])
    return ((seg_in_box(a, k1, box) or seg_in_box(k1, c, box)) and (seg_in_box(a, k2, box) or seg_in_box(k2, c, box)))


def knee_route(px, py, lx, ly, face, direction, geometry, n, along=False):
    """kit is_knee_site: (route points from the chain start, [station sites]) of one bit; geometry = bbox of the bus starts"""
    import istation_knee as K
    xmin, ymin, xmax, ymax = geometry
    if face in "EW":
        normal, alg, corner = max(abs(xmin - lx), abs(xmax - lx)), max(abs(ymin - ly), abs(ymax - ly)), (lx, py)
    else:
        normal, alg, corner = max(abs(ymin - ly), abs(ymax - ly)), max(abs(xmin - lx), abs(xmax - lx)), (px, ly)
    if along:
        corner = (px, ly) if face in "EW" else (lx, py)
        normal, alg = alg, normal
    if direction == "in":
        first, second, a, b = normal, alg, (px, py), (lx, ly)
    else:
        first, second, a, b = alg, normal, (lx, ly), (px, py)
    edges = n + 1
    _w, split = K.knee(first, second, edges)
    sites = []
    for edge in range(1, n + 1):
        if split > 0 and edge <= split:
            f = edge / split
            sites.append((a[0] + f * (corner[0] - a[0]), a[1] + f * (corner[1] - a[1])))
        else:
            f = (edge - split) / (edges - split) if edges != split else 1.0
            sites.append((corner[0] + f * (b[0] - corner[0]), corner[1] + f * (b[1] - corner[1])))
    return [a, corner, b], sites


def is_landing(c):
    """a clock-landing child macro (its own bus pins sit behind it by construction)"""
    return str(c.get("inst", "")).startswith("cl_") or "cland" in str(c.get("module", ""))


def _pad_relay(rs, bus, k, n, bit):
    """plan relay_sites key of stage k of the packed lane pad u_lpad_<bus> (ot_dp_dly: r[k][bit], the last stage q[bit])"""
    for sep in (".", "/"):
        v = rs.get(f"u_lpad_{bus}{sep}q[{bit}]" if k == n - 1 else f"u_lpad_{bus}{sep}r[{k}][{bit}]")
        if v is not None:
            return (float(v[0]), float(v[1]))
    return None


def _relay(rs, inst, bit, width):
    for sep in (".", "/"):
        v = rs.get(f"{inst}{sep}eq" if bit == width else f"{inst}{sep}q[{bit}]")
        if v is not None:
            return (float(v[0]), float(v[1]))
    return None


def rows(t, pins, plan_dir=None, tn="?"):
    """pins: {bus: {bit: (x, y)}} (gen_phys.type_pins, type frame)"""
    import istation_knee as K
    import istation_channel as IC
    import gen_rtl
    bx = boxes_of(t)
    out = []
    if not bx:
        return out
    buses = {b["name"]: b for b in t.get("buses", [])}
    rs = t.get("relay_sites") or {}
    landing = {c["inst"] for c in t.get("hard_cores", []) if is_landing(c)}

    def hit_names(p):
        return [nm for nm, box in bx.items() if in_box(p, box)]

    for e in t.get("internal_stations", []):
        conn = e.get("conn", "")
        regs = e.get("regs_um") or []
        n = len(regs)
        row = dict(kind="centroid", conn=conn, stations=n, bits=int(e.get("bits", 1)), sites=n, sites_in_macro=0,
                   routes_crossing=0, macros=set())
        b = buses.get(conn[4:]) if conn.startswith("bus:") else None
        per_bit = (b is not None and e.get("bit_route") == "per_bit" and "leaf_um" in e and "face" in b
                   and "bit_sites_um" not in e and pins.get(b["name"]))
        if not per_bit:
            for r in regs:
                h = hit_names(r)
                if h:
                    row["sites_in_macro"] += 1
                    row["macros"].update(h)
            if e.get("core") and e.get("bit_route") == "per_bit":
                row["kind"] = "core_chain"
            out.append(row)
            continue
        bus = b["name"]
        starts = dict(pins[bus])
        W = max(starts)
        keep = None
        offset = 0.0
        if e.get("core"):
            row["kind"] = "core_chain"
            try:
                import kit_istations as KI
                st = KI.chain_starts(tn, t, e, b, None if e.get("start_core") else W, plan_dir, starts)
            except SystemExit:
                st = None
            if st:
                keep = {int(x) for x in e.get("core_bits", [])} | {max(st)}
                starts = st
                W = max(starts)
        else:
            row["kind"] = "bus_chain"
            offset = K.leaf_offset(t, b)
            if b["dir"] == "in":
                # the plan cannot tell whether the bound RTL carries a packed lane-pad receiver (sited at regs_um) or
                # per-bit stations: both models are reported
                row["kind"] = "bus_chain_in"
                row["regs_in_macro"] = sum(1 for r in regs if hit_names(r))
        lx, ly = e["leaf_um"]
        lx += {"W": -offset, "E": offset}.get(b["face"], 0.0)
        ly += {"S": -offset, "N": offset}.get(b["face"], 0.0)
        xs, ys = [p[0] for p in starts.values()], [p[1] for p in starts.values()]
        geo = (min(xs), min(ys), max(xs), max(ys))
        d = b["dir"]
        inst = "u_ist_" + gen_rtl.sv_id(bus)
        chan = IC.entry_channel(e) if e.get("leg_order") == "channel" else None
        own = {"cl_" + bus}                  # an in bus enters through its own landing macro
        nbits = nsites = 0
        for bit, (px, py) in sorted(starts.items()):
            if keep is not None and bit not in keep:
                continue
            nbits += 1
            fixed = [_relay(rs, f"{inst}_{k}", bit, W) for k in range(n)] if not e.get("core") else [None]
            if d == "in" and not e.get("core") and any(f is None for f in fixed):
                fixed = [_pad_relay(rs, gen_rtl.sv_id(bus), k, n, bit) for k in range(n)]
            if n and all(f is not None for f in fixed):       # explicit per-bit FIRM sites (plan relay_sites)
                row["kind"] = "bus_chain_relay_sites"
                sites = fixed
                chain = ([(px, py)] + sites) if d == "in" else (sites + [(px, py)])
                cross = {nm for a, c in zip(chain, chain[1:]) for nm, box in bx.items() if hop_in_box(a, c, box)} - own
            else:
                if chan:
                    pts = IC.path(px, py, lx, ly, b["face"], d, IC.column(chan[0], chan[1], bit, W + 1))
                    L = IC.length(pts)
                    sites = [IC.point_at(pts, L * (k + 1) / (n + 1)) for k in range(n)]
                else:
                    pts, sites = knee_route(px, py, lx, ly, b["face"], d, geo, n, e.get("leg_order") == "along_first")
                cross = {nm for a, c in zip(pts, pts[1:]) for nm, box in bx.items() if seg_in_box(a, c, box)} - own
            for s in sites:
                nsites += 1
                h = hit_names(s)
                if h:
                    row["sites_in_macro"] += 1
                    row["macros"].update(h)
            if cross:
                row["routes_crossing"] += 1
                row["routes_over_cores"] = row.get("routes_over_cores", 0) + bool(cross - landing)
                row["macros"].update(cross)
        row.update(bits=nbits, sites=nsites)
        out.append(row)
    for s in t.get("ft_slots", []):
        regs = s.get("regs_um") or []
        row = dict(kind="ft_slot", conn="ft:" + s["name"], stations=len(regs), bits=int(s.get("width", 1)), sites=len(regs),
                   sites_in_macro=0, routes_crossing=0, macros=set())
        for r in regs:
            h = hit_names(r)
            if h:
                row["sites_in_macro"] += 1
                row["macros"].update(h)
        for a, c in zip(regs, regs[1:]):
            x = {nm for nm, box in bx.items() if hop_in_box(a, c, box)}
            if x:
                row["routes_crossing"] += 1
                row["routes_over_cores"] = row.get("routes_over_cores", 0) + bool(x - landing)
                row["macros"].update(x)
        out.append(row)
    if rs:
        row = dict(kind="relay_sites", conn="relay_sites", stations=0, bits=len(rs), sites=len(rs), sites_in_macro=0,
                   routes_crossing=0, macros=set())
        for k, v in rs.items():
            if re.search(r"(^|[./])u_cland_", k):          # ring flops live inside their landing macro band
                continue
            h = hit_names(v)
            if h:
                row["sites_in_macro"] += 1
                row["macros"].update(h)
        out.append(row)
    for r in out:
        r["macros"] = sorted(r["macros"])
    return out


def type_pins(P, tn):
    import gen_phys
    pins = {}
    for name, bit, _ln, x, y, _f in gen_phys.type_pins(P, tn):
        pins.setdefault(name, {})[int(bit)] = (float(x), float(y))
    return pins


def report(P, tn, plan_dir=None, landing_routes=False):
    """rows with a station site inside a hard macro or a bit route over a hard CORE; a route that only passes a clock-landing
    macro on its way to the pins behind it (M6-M8, short) is listed with landing_routes=True"""
    t = P.types[tn]
    if not t.get("hard_cores") or not (t.get("internal_stations") or t.get("ft_slots") or t.get("relay_sites")):
        return []
    if plan_dir is None and getattr(P, "path", None):
        plan_dir = Path(P.path).resolve().parent
    return [r for r in rows(t, type_pins(P, tn), plan_dir, tn)
            if r["sites_in_macro"] or r.get("routes_over_cores") or (landing_routes and r["routes_crossing"])]


def line(tn, r):
    return (f"type {tn}: {r['kind']} {r['conn']}: {r['sites_in_macro']} of {r['sites']} station sites inside hard macros, "
            f"{r['routes_crossing']} of {r['bits']} bit routes cross a hard macro ({r.get('routes_over_cores', 0)} a hard core; M1-M5 blocked) {r['macros']}"
            + (f"; packed lane-pad form: {r['regs_in_macro']} of {r['stations']} regs_um sites inside" if "regs_in_macro" in r else ""))


def lines(P, tn, plan_dir=None):
    return [line(tn, r) for r in report(P, tn, plan_dir)]


def main(argv):
    import schema as S
    plan = argv[0]
    rx = re.compile(argv[1] if len(argv) > 1 else ".")
    P = S.Plan(json.load(open(plan)), path=plan)
    used = {p["type"] for p in P.parts.values()}
    print("type\tkind\tconn\tstations\tbits\tsites\tsites_in_macro\troutes_crossing\tmacros")
    n = 0
    for tn in sorted(P.types):
        if tn not in used or not rx.search(tn):
            continue
        try:
            rep = report(P, tn)
        except Exception as ex:      # advisory: a type this model cannot read is listed, never fatal
            print(f"{tn}\tERROR\t{type(ex).__name__}: {str(ex)[:120]}")
            continue
        for r in rep:
            n += 1
            print(f"{tn}\t{r['kind']}\t{r['conn']}\t{r['stations']}\t{r['bits']}\t{r['sites']}\t{r['sites_in_macro']}\t"
                  f"{r['routes_crossing']}\t{','.join(r['macros'])}", flush=True)
    print(f"STATION-CORE {plan}: {n} rows with sites in / routes over a hard macro (advisory)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
