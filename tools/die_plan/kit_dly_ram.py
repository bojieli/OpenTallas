#!/usr/bin/env python3
"""kit_dly_ram.py -- FIX-KV-PV-MESOFIFO 11-23 (ledger rc128, VIS-KV "pad FIFO" ruling): landing-pad trunks held in SRAM rings
(tools/die_plan/ot_dp_dly_ram.sv) instead of reset-less flop lines.  Kit RTL post-pass at GEN, opt-in per plan type.

Why (measured on the D28 seal bind, 17 kv3_pv* types): 1,247,833 landing-pad flops, 1,111,268 of them in W=1 trunks of
in-lane buses that are 256-bit groups of one depth +- a few cycles (kv3_pv_v6n: i_astk_W owner response 768 b x 46..65
and 256 b x 63..67, i_vport_E_N_vo 256 b x 22..28).  Placed, they form the pad-delay column (VIS-KV pad_delay_column on
19 KV types, rc128 pv_v8 GRT-0228: one ~100 um channel carries the trunk lines, the clock trunk and the stacked taps;
kv3_pv_v6n 87 k sequential cells = 60 % of the kit flops, + 22 k kit_dly_lockup latches).  One ot_sram_1r1w_128x256 holds
256 bits x up to 130 cycles in 95 x 41 um with three registers per bit on the clock tree instead of D.

Same cycles: ot_dp_dly_ram #(.W(n), .D(r)) is cycle-exact to ot_dp_dly #(.W(n), .D(r)) (rtl/test/dp_dly_ram bench), so
every sink keeps its bound depth: bind, bind_latency, LATCHECK and the R8 table are untouched (this pass runs on the kit's
staged copy of the bound RTL, after the bind).  LEC is kit RTL vs netlist, both after this pass; the SRAM is a black box on
both sides.

Form, per in-lane bus b of a selected type (plan partition_types[t].pad_ram = {"min_d": 8, "min_flops": 4096, ...}):
  candidates  W=1 ot_dp_dly / ot_dp_dly_keep statements of the bind marked `landing pad trunk` (tail-split trunk) or
              `landing pad:` (unsplit pad) whose d is an in-boundary bit <b>_q[j] and whose D >= min_d.  Tail copies,
              chained trunk pieces (d = another trunk's q), intra-partition pipes and strap banks are never touched.
  chunks      the bits of b sorted by (D, j), cut into chunks of <= 256 bits; chunk base B = min D of the chunk.
  per chunk   lead L = ceil(pin -> RAM distance / hop_um) reset-less stages per bit (u_pd<L>_ram_<k>_<j>, `landing pad
              trunk` marker, so kit_dly_lockup segments and dly_spread sites them like any trunk), then one
              ot_dp_dly_ram #(.W(n), .D(R)) u_pdram_<k> with R = min(B - L, 130), then per bit the residual D - L - R
              stages under the ORIGINAL instance name and q wire (absent when 0: the RAM slice drives the q wire).
              Taken only when n x R >= min_flops and R >= 4; otherwise the chunk stays as bound.
  placement   each RAM macro (u_bound.u_pdram_<k>.g_b[0].u_m, R0) at the free site nearest to the centroid of the hard cores
              its bits feed (tail-copy `for core <tag>` markers, or the cores reading the pad directly): inside the outline
              (edge margin), clear of hard cores, content macros, earlier RAMs, fixed stations/relay seats and clock taps by `clear_um`, never in a gap
              narrower than the macro + 2 x clear_um (the centre trunk channel stays free).  No site = the chunk stays
              as bound (recorded), never an error.
Outputs: rewritten *_bound.sv, record dly_ram.json, extra macros for gen_phys (type_macros form), extra source files.

Usage: kit_dly_ram.py BOUND.sv --type-json T.json [--pins PINS.json] [--out OUT.sv] [--report R.json]
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kit_zl_lockup import LkError, _close, conns, instances  # noqa: E402

DLY = ("ot_dp_dly", "ot_dp_dly_keep")
TAIL_MARK = "landing pad tail copy for core"
TRUNK_MARK = "landing pad trunk"
PAD_MARK = "landing pad:"
INLANE = re.compile(r"^([A-Za-z_]\w*)_q\[(\d+)\]$")
IDENT = re.compile(r"[A-Za-z_]\w*")
MACRO = "ot_sram_1r1w_128x256_m1_r2c2"
MACRO_DIR = "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2"
MACRO_UM = (94.824, 41.04)
WM, DMAX, DMIN_RAM = 256, 130, 4
DEFAULTS = dict(min_d=8, min_flops=4096, hop_um=300.0, clear_um=10.0, edge_um=10.0, grid_um=4.32, max_macros=16, max_resid=8,
                keepout_um=(), wide_min_d=0)
# KV-PV-CAP 11-23 (wide_min_d > 0): WIDE delay lines too -- a plain multi-bit ot_dp_dly (W > 1, D >= wide_min_d, not a tail copy, not
# a kept line) is the latency padding of a whole bus (kv3_pv_v1n u_d73_vport_E_out_v_lo W 512 D 73 + u_d68_vport_W_out_v_lo: 72k
# flops of the type).  Per line: one lead line (W x L), one ot_dp_dly_ram per 256-bit slice (D R, each its own macro site), and the
# residual (W x D-L-R) under the ORIGINAL instance name and q wire, so the line's consumers, names and cycles stay as bound.
# L / the residual cover the hops source cores -> RAM -> farthest consumer core (hop_um; an end with no placed core counts from the
# farthest outline corner); the RAM sits at the midpoint of the source and consumer centroids.


def cfg_of(t):
    """plan partition_types[t].pad_ram -> config (absent / false -> None)"""
    v = t.get("pad_ram")
    if v is None or v is False:        # an empty object {} means "on, defaults"
        return None
    c = dict(DEFAULTS)
    if isinstance(v, dict):
        unknown = set(v) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"pad_ram: unknown keys {sorted(unknown)}")
        c.update(v)
    return c


def _param(params, key, default=1):
    m = re.search(r"\.%s\(\s*(\d+)\s*\)" % key, params)
    return int(m.group(1)) if m else default


def _norm(s):
    s = s[2:] if s.startswith("u_") else s
    return re.sub(r"_+", "_", s)


def _body(txt):
    mod = re.search(r"\bmodule\s+\w+\s*(#\((?:[^()]|\([^()]*\))*\))?\s*\(", txt)
    if not mod:
        raise LkError("no module header")
    hdr_end = txt.index(";", _close(txt, mod.end() - 1)) + 1
    return hdr_end


def scan(txt):
    """-> (candidates {name: rec}, readers {q wire: set(core tags)}) of a bound module text"""
    hdr = _body(txt)
    body = txt[hdr:]
    insts = instances(body)
    cand, qmap, tails = {}, {}, []
    core_conn = []
    wide, dpin = {}, []
    for mt, params, name, s, e, lp in insts:
        cs = conns(body, lp, e)
        end = body.index(";", e) + 1
        eol = body.find("\n", end)
        rest = body[end:eol if eol >= 0 else len(body)]
        if mt in DLY and "d" in cs:
            dpin.append((name, cs["d"][0], cs.get("q", ("",))[0].strip()))
        if mt == "ot_dp_dly" and _param(params, "W") > 1 and "d" in cs and "q" in cs and IDENT.fullmatch(cs["q"][0].strip()) \
                and TAIL_MARK not in rest:
            wide[name] = dict(mt=mt, W=_param(params, "W"), D=_param(params, "D"), d=cs["d"][0].strip(), q=cs["q"][0].strip(),
                              span=(hdr + s, hdr + end), rest=rest.rstrip(), clk=cs.get("clk", ("clk",))[0].strip())
        if mt in DLY:
            if TAIL_MARK in rest:
                m = re.search(TAIL_MARK + r"\s+([A-Za-z_]\w*)", rest)
                if m and "d" in cs:
                    tails.append((cs["d"][0].strip(), m.group(1)))
                continue
            if _param(params, "W") != 1 or "d" not in cs or "q" not in cs:
                continue
            if TRUNK_MARK not in rest and PAD_MARK not in rest:
                continue
            m = INLANE.match(cs["d"][0].strip())
            q = cs["q"][0].strip()
            if not m or not IDENT.fullmatch(q):
                continue
            cand[name] = dict(mt=mt, D=_param(params, "D"), bus=m.group(1), bit=int(m.group(2)), q=q,
                              span=(hdr + s, hdr + end), rest=rest.rstrip(), clk=cs.get("clk", ("clk",))[0].strip())
            qmap[q] = name
        elif not mt.startswith("ot_dp_"):
            core_conn.append((name, [x[0] for x in cs.values()]))
    readers = {}
    for d, tag in tails:
        w = IDENT.match(d)
        if w and w.group(0) in qmap:
            readers.setdefault(w.group(0), set()).add(tag)
    for name, exprs in core_conn:              # cores reading an unsplit pad directly
        for ex in exprs:
            for w in set(IDENT.findall(ex)):
                if w in qmap:
                    readers.setdefault(w, set()).add(name)
    scan.wide = (wide, core_conn, dpin)
    return cand, readers


def wide_ends(wide, core_conn, dpin):
    """{line: (source core insts, consumer core insts)}: cores on the d idents / on the q ident, one ot_dp_* stage deep"""
    by_id = {}
    for name, exprs in core_conn:
        for ex in exprs:
            for w in set(IDENT.findall(ex)):
                by_id.setdefault(w, set()).add(name)
    rd = {}
    for name, dex, q in dpin:
        for w in set(IDENT.findall(dex)):
            rd.setdefault(w, []).append(q)
    out = {}
    for n, x in wide.items():
        src = set().union(*[by_id.get(w, set()) for w in IDENT.findall(x["d"])] or [set()])
        dst = set(by_id.get(x["q"], set()))
        for q2 in rd.get(x["q"], ()):
            dst |= by_id.get(q2, set())
        out[n] = (sorted(src), sorted(dst))
    return out


def _seat_points(entries):
    for item in entries:
        if not isinstance(item, (tuple, list)):
            continue
        if len(item) >= 2 and all(isinstance(coord, (int, float)) for coord in item[:2]):
            yield item[0], item[1]
        else:
            yield from _seat_points(item)


def _seat_obstacles(t, clock_sites):
    """Coalesce nearby exact seats so search cost depends on occupied regions."""
    groups = [(t.get("relay_sites") or {}).values(), ((x, y) for _, x, y in clock_sites)]
    for row in (*(t.get("internal_stations") or ()), *(t.get("ft_slots") or ())):
        groups.extend((row.get("regs_um") or (), row.get("bit_sites_um") or ()))
    tiles = {}
    for entries in groups:
        for x, y in _seat_points(entries):
            key = int(x // 43.2), int(y // 43.2)
            box = tiles.setdefault(key, [x, y, x, y])
            box[0], box[1] = min(box[0], x), min(box[1], y)
            box[2], box[3] = max(box[2], x), max(box[3], y)
    # Seats can be cell lower-left coordinates, while tap sites are pin centres.
    return [(x0, y0, x1 + 1.404, y1 + 0.27) for x0, y0, x1, y1 in tiles.values()]


def type_geom(t, pins=(), clock_sites=()):
    """obstacles [(x0, y0, x1, y1)] + core centres {norm(inst): (x, y)} + pin centroid per bus, in the type frame"""
    obs, centre = [], {}
    for c in list(t.get("hard_cores", [])) + list(t.get("contents", [])):
        parts = [c] + list(c.get("physical_parts") or [])
        for q in parts:
            if "origin_um" in q and "outline_um" in q:
                x, y = q["origin_um"]
                w, h = q["outline_um"]
                o = q.get("orient", "R0")
                if o in ("R90", "R270", "MXR90", "MYR90"):
                    w, h = h, w
                obs.append((x, y, x + w, y + h))
                if q is c:
                    centre[_norm(c["inst"])] = (x + w / 2, y + h / 2)
    acc = {}
    for port, _bit, _ln, x, y, _f in pins:
        a = acc.setdefault(port, [0.0, 0.0, 0])
        a[0] += x
        a[1] += y
        a[2] += 1
    pin = {k: (v[0] / v[2], v[1] / v[2]) for k, v in acc.items()}
    return dict(outline=tuple(t["outline_um"]), obstacles=obs + _seat_obstacles(t, clock_sites), centre=centre, pins=pin)


def _bus_pin(geom, bus):
    p = geom["pins"]
    for k in (bus, re.sub(r"_p(_\d+)?$", "", bus)):
        if k in p:
            return p[k]
    return None


def _free(box, obs, clear):
    x0, y0, x1, y1 = box
    for a0, b0, a1, b1 in obs:
        if x0 < a1 + clear and a0 - clear < x1 and y0 < b1 + clear and b0 - clear < y1:
            return False
    return True


def site(geom, target, placed, c):
    """origin (x, y) of a free R0 macro site whose centre is nearest (Manhattan) to target, or None"""
    W, H = geom["outline"]
    mw, mh = MACRO_UM
    g, e, cl = c["grid_um"], c["edge_um"], c["clear_um"]
    obs = geom["obstacles"] + placed + [tuple(r) for r in c.get("keepout_um") or ()]
    nx, ny = int((W - 2 * e - mw) / g), int((H - 2 * e - mh) / g)
    if nx < 0 or ny < 0:
        return None
    tx, ty = target
    best = None
    # candidates ordered by distance: scan every grid origin once (a 2160 x 1520 type is ~0.7 M points at 2.16 um; the
    # obstacle test only runs on points that beat the best so far)
    xs = sorted(range(nx + 1), key=lambda i: abs(e + i * g + mw / 2 - tx))
    ys = sorted(range(ny + 1), key=lambda j: abs(e + j * g + mh / 2 - ty))
    for i in xs:
        x = round(e + i * g, 4)
        dx = abs(x + mw / 2 - tx)
        if best and dx >= best[0]:
            break
        for j in ys:
            y = round(e + j * g, 4)
            d = dx + abs(y + mh / 2 - ty)
            if best and d >= best[0]:
                break
            if _free((x, y, x + mw, y + mh), obs, cl):
                best = (d, x, y)
                break
    return None if best is None else (best[1], best[2])


def plan(txt, t, pins=(), c=None, tag="", *, clock_sites=()):
    """-> (chunks [dict], record) without changing txt"""
    c = c or cfg_of(t) or dict(DEFAULTS)
    cand, readers = scan(txt)
    geom = type_geom(t, pins, clock_sites)
    W, H = geom["outline"]
    by_bus = {}
    for n, x in cand.items():
        if x["D"] >= c["min_d"]:
            by_bus.setdefault(x["bus"], []).append(n)
    chunks, skipped, placed = [], [], []
    k = 0
    order = sorted(by_bus, key=lambda b: -sum(cand[n]["D"] for n in by_bus[b]))
    for bus in order:
        names = sorted(by_bus[bus], key=lambda n: (cand[n]["D"], cand[n]["bit"]))
        groups, cur = [], []
        for n in names:
            if cur and (len(cur) == WM or cand[n]["D"] - cand[cur[0]]["D"] > c["max_resid"]):
                groups.append(cur)
                cur = []
            cur.append(n)
        if cur:
            groups.append(cur)
        for ch in groups:
            base = cand[ch[0]]["D"]
            cores = set()
            for n in ch:
                for tg in readers.get(cand[n]["q"], ()):
                    cores.add(_norm(tg))
            pts = [geom["centre"][x] for x in sorted(cores) if x in geom["centre"]]
            target = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else (W / 2, H / 2)
            rec = dict(bus=bus, bits=len(ch), base=base, cores=sorted(cores), target=[round(target[0], 2), round(target[1], 2)])
            if len(chunks) >= c["max_macros"]:
                skipped.append(dict(rec, why="max_macros"))
                continue
            org = site(geom, target, placed, c)
            if org is None:
                skipped.append(dict(rec, why="no free site"))
                continue
            pin = _bus_pin(geom, bus)
            cx, cy = org[0] + MACRO_UM[0] / 2, org[1] + MACRO_UM[1] / 2
            dist = abs(pin[0] - cx) + abs(pin[1] - cy) if pin else (W + H) / 2
            lead = max(0, math.ceil(dist / c["hop_um"]) - 1)    # the in-boundary flop is the first stage of the hop chain
            # trail: the tail copies were sized (bind_pad_tail_split K) from a trunk end at the consumer centroid; a RAM
            # sited away from it gets the missing hops after its output register
            off = abs(target[0] - cx) + abs(target[1] - cy)
            trail = max(0, math.ceil(off / c["hop_um"]) - 1)
            r = min(base - lead - trail, DMAX)
            if r < DMIN_RAM or len(ch) * r < c["min_flops"]:
                skipped.append(dict(rec, why=f"ram depth {r} x {len(ch)} below min_flops / {DMIN_RAM}"))
                continue
            placed.append((org[0], org[1], org[0] + MACRO_UM[0], org[1] + MACRO_UM[1]))
            inst = f"u_pdram_{tag}{k}"
            chunks.append(dict(rec, inst=inst, lead=lead, trail=trail, ram_d=r, names=ch, off_um=round(off, 1), origin_um=[org[0], org[1]],
                               pin=[round(pin[0], 2), round(pin[1], 2)] if pin else None, dist_um=round(dist, 1),
                               physical_inst=f"u_bound.{inst}.g_b[0].u_m",
                               resid=sum(cand[n]["D"] - lead - trail - r for n in ch)))
            k += 1
    wchunks, wskip = [], []
    if c.get("wide_min_d"):
        wide, core_conn, dpin = scan.wide
        ends = wide_ends(wide, core_conn, dpin)

        def cen(insts):
            pts = [geom["centre"][_norm(i)] for i in insts if _norm(i) in geom["centre"]]
            return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None
        for n in sorted((n for n, x in wide.items() if x["D"] >= c["wide_min_d"]), key=lambda n: -wide[n]["W"] * wide[n]["D"]):
            x = wide[n]
            src, dst = (cen(e) for e in ends[n])
            a, b = src or dst or (W / 2, H / 2), dst or src or (W / 2, H / 2)
            target = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            nsl = (x["W"] + WM - 1) // WM
            rec = dict(line=n, W=x["W"], D=x["D"], src=ends[n][0], dst=ends[n][1], target=[round(target[0], 2), round(target[1], 2)])
            if len(chunks) + len(wchunks) + nsl > c["max_macros"]:
                wskip.append(dict(rec, why="max_macros"))
                continue
            orgs, tmp = [], list(placed)
            for _ in range(nsl):
                org = site(geom, target, tmp, c)
                if org is None:
                    break
                orgs.append(org)
                tmp.append((org[0], org[1], org[0] + MACRO_UM[0], org[1] + MACRO_UM[1]))
            if len(orgs) < nsl:
                wskip.append(dict(rec, why="no free site"))
                continue
            # reach (never fewer stages than the hops): lead = RAM -> farthest source core, trail = RAM -> farthest consumer core;
            # an end with no placed core (soft source, port) counts from the farthest outline corner
            def far(cx, cy, insts):
                pts = [geom["centre"][_norm(i)] for i in insts if _norm(i) in geom["centre"]] or [(0, 0), (W, 0), (0, H), (W, H)]
                return max(abs(px - cx) + abs(py - cy) for px, py in pts)
            lead = trail = 0
            for org in orgs:
                cx, cy = org[0] + MACRO_UM[0] / 2, org[1] + MACRO_UM[1] / 2
                lead = max(lead, max(0, math.ceil(far(cx, cy, ends[n][0]) / c["hop_um"]) - 1))
                trail = max(trail, max(0, math.ceil(far(cx, cy, ends[n][1]) / c["hop_um"]) - 1))
            r = min(x["D"] - lead - trail, DMAX)
            if r < DMIN_RAM or x["W"] * r < c["min_flops"]:
                wskip.append(dict(rec, why=f"ram depth {r} x {x['W']} below min_flops / {DMIN_RAM}"))
                continue
            placed[:] = tmp
            for j, org in enumerate(orgs):
                lo, hi = j * WM, min(x["W"], (j + 1) * WM)
                inst = f"u_pdramw_{tag}{k}"
                wchunks.append(dict(rec, kind="wide", inst=inst, slice=[lo, hi], bits=hi - lo, lead=lead, trail=trail, ram_d=r,
                                    resid=x["D"] - lead - r, origin_um=[org[0], org[1]], physical_inst=f"u_bound.{inst}.g_b[0].u_m"))
                k += 1
    chunks = chunks + wchunks
    skipped = skipped + wskip
    stats = dict(candidates=len(cand), candidate_flops=sum(x["D"] for x in cand.values()), chunks=len(chunks),
                 ram_flops=sum(x["bits"] * x["ram_d"] for x in chunks),
                 lead_flops=sum(x["bits"] * (x["lead"] + x["trail"]) for x in chunks if x.get("kind") != "wide"),
                 resid_flops=sum(x["resid"] for x in chunks if x.get("kind") != "wide"), skipped=skipped,
                 wide_lines=len({x["line"] for x in wchunks}), wide_ram_flops=sum(x["bits"] * x["ram_d"] for x in wchunks),
                 wide_lead_flops=sum(x["bits"] * x["lead"] for x in wchunks),
                 wide_resid_flops=sum(x["bits"] * x["resid"] for x in wchunks))
    return chunks, stats, cand


def rewrite(txt, chunks, cand):
    """apply the chunks to txt -> new text (each candidate statement replaced in place, RAMs before endmodule)"""
    if not chunks:
        return txt
    edits, decl, rams = [], [], []
    used = set(re.findall(r"\b[A-Za-z_]\w*\b", txt))
    wide = [ch for ch in chunks if ch.get("kind") == "wide"]
    chunks = [ch for ch in chunks if ch.get("kind") != "wide"]
    if wide:
        scan(txt)
    wl = scan.wide[0] if wide else {}

    def fresh(n):
        if n in used:
            raise LkError(f"name collision: {n}")
        used.add(n)
        return n
    for ch in chunks:
        ins, outs = [], []
        for j, n in enumerate(ch["names"]):
            x = cand[n]
            src = f"{x['bus']}_q[{x['bit']}]"
            if ch["lead"]:
                lw = fresh(f"pd{ch['lead']}_ram_{ch['inst'][2:]}_{j}")
                decl.append(f"    wire [0:0] {lw};")
                rams.append(f"    ot_dp_dly_keep #(.W(1), .D({ch['lead']})) {fresh('u_' + lw)} (.clk({x['clk']}), .d({src}), "
                            f".q({lw}));  // landing pad trunk: kit_dly_ram lead of {n} ({ch['inst']})")
                src = f"{lw}[0]"
            ins.append(src)
            tr = ch["trail"]
            res = x["D"] - ch["lead"] - tr - ch["ram_d"]
            ind = re.match(r"[ \t]*", txt[x["span"][0]:]).group(0)
            after = x["q"]                       # what the RAM slice (or its trail line) finally drives
            if res:
                after = fresh(f"pdr_{ch['inst'][2:]}_{j}")
                decl.append(f"    wire [0:0] {after};")
                new = (f"{ind}{x['mt']} #(.W(1), .D({res})) {n} (.clk({x['clk']}), .d({after}[0]), .q({x['q']}));"
                       f"{x['rest']}  // kit_dly_ram: residual {res} of D {x['D']} after {ch['inst']}")
            else:
                new = (f"{ind}// kit_dly_ram: {n} D {x['D']} = lead {ch['lead']} + {ch['inst']} D {ch['ram_d']}"
                       f" + trail {tr}")
            if tr:
                tw = fresh(f"pdt_{ch['inst'][2:]}_{j}")
                decl.append(f"    wire [0:0] {tw};")
                rams.append(f"    ot_dp_dly_keep #(.W(1), .D({tr})) {fresh('u_pd' + str(tr) + '_ramt_' + ch['inst'][2:] + '_' + str(j))} "
                            f"(.clk({x['clk']}), .d({tw}[0]), .q({after}));  // landing pad trunk: kit_dly_ram trail of {n} ({ch['inst']})")
                outs.append(tw)
            else:
                outs.append(after)
            edits.append((x["span"][0], x["span"][1] + len(x["rest"]), new))
        # MSB first in the concatenations: bit j of the RAM word is chunk bit j
        rams.append(f"    ot_dp_dly_ram #(.W({ch['bits']}), .D({ch['ram_d']})) {fresh(ch['inst'])} (.clk({cand[ch['names'][0]]['clk']}), "
                    f".d({{{', '.join(reversed(ins))}}}), .q({{{', '.join(reversed(outs))}}}));  "
                    f"// kit_dly_ram: {ch['bus']} {ch['bits']} b, pad base {ch['base']} = lead {ch['lead']} + ram {ch['ram_d']} + trail {ch['trail']}")
    lines = {}
    for ch in wide:
        lines.setdefault(ch["line"], []).append(ch)
    for n, chs in lines.items():
        x = wl.get(n)
        if x is None:
            raise LkError(f"kit_dly_ram wide: line {n} not found")
        L, R, W = chs[0]["lead"], chs[0]["ram_d"], x["W"]
        res = x["D"] - L - R
        ind = re.match(r"[ \t]*", txt[x["span"][0]:]).group(0)
        src = x["d"]
        if L:
            lw = fresh(f"{n[2:] if n.startswith('u_') else n}_ramld")
            decl.append(f"    wire [{W - 1}:0] {lw};")
            rams.append(f"    ot_dp_dly #(.W({W}), .D({L})) {fresh('u_' + lw)} (.clk({x['clk']}), .d({src}), .q({lw}));"
                        f"  // kit_dly_ram wide: lead {L} of {n}")
            src = lw
        rq = fresh(f"{n[2:] if n.startswith('u_') else n}_ramq")
        decl.append(f"    wire [{W - 1}:0] {rq};")
        for ch in chs:
            lo, hi = ch["slice"]
            rams.append(f"    ot_dp_dly_ram #(.W({hi - lo}), .D({R})) {fresh(ch['inst'])} (.clk({x['clk']}), .d({src}[{hi - 1}:{lo}]), "
                        f".q({rq}[{hi - 1}:{lo}]));  // kit_dly_ram wide: {n} bits {lo}..{hi - 1} = lead {L} + ram {R} + residual {res}")
        if res:
            new = (f"{ind}{x['mt']} #(.W({W}), .D({res})) {n} (.clk({x['clk']}), .d({rq}), .q({x['q']}));{x['rest']}"
                   f"  // kit_dly_ram wide: residual {res} of D {x['D']}")
        else:
            new = f"{ind}assign {x['q']} = {rq};  // kit_dly_ram wide: {n} D {x['D']} = lead {L} + ram {R}"
        edits.append((x["span"][0], x["span"][1] + len(x["rest"]), new))
    for a, b, new in sorted(edits, reverse=True):
        eol = txt.find("\n", a)
        if eol < 0 or eol < b:
            eol = b
        txt = txt[:a] + new + txt[eol:]
    head = [f"    // kit_dly_ram (FIX-KV-PV-MESOFIFO 11-23): {len(chunks)} landing-pad SRAM rings ot_dp_dly_ram"
            + (f", {len(wide)} wide-line rings (KV-PV-CAP)" if wide else "")] + decl
    hdr = _body(txt)
    txt = txt[:hdr] + "\n" + "\n".join(head) + txt[hdr:]
    txt, n = re.subn(r"(\n\s*endmodule\b)", lambda m: "\n" + "\n".join(rams) + m.group(1), txt, count=1)
    if n != 1:
        raise LkError("no endmodule")
    return txt


def macros_of(chunks):
    """gen_phys type_macros rows for the RAM macros: (inst, module, lef, lib, x, y, orient)"""
    return [(ch["physical_inst"], MACRO, f"{MACRO_DIR}/{MACRO}.lef", f"{MACRO_DIR}/{MACRO}_tt.lib",
             ch["origin_um"][0], ch["origin_um"][1], "R0") for ch in chunks]


def extra_sources():
    """files the rewritten RTL needs: the delay-ring cell (beside this pass: it travels with the rt tools) and the SRAM
    black box (a design-root path: gen_phys resolves it like the macro views)"""
    return [Path(__file__).resolve().parent / "ot_dp_dly_ram.sv"], [f"{MACRO_DIR}/{MACRO}_bb.v"]


def plan_kit(rtl_files, t, pins=(), *, clock_sites=()):
    """gen_phys entry, BEFORE the macro block: {bound file name: (chunks, stats, cand)} of the type's bound RTL"""
    c = cfg_of(t)
    out = {}
    if not c:
        return out
    for f in rtl_files:
        f = Path(f)
        if not f.name.endswith("_bound.sv"):
            continue
        txt = f.read_text()
        if "ot_dp_dly" not in txt:
            continue
        out[f.name] = (txt,) + plan(txt, t, pins, c, clock_sites=clock_sites)
    return out


def apply_kit(rtl_dir, planned):
    """gen_phys entry, AFTER staging: rewrite each staged bound file (must be byte-identical to the planned source)."""
    rec = {}
    for name, (src, chunks, stats, cand) in planned.items():
        f = Path(rtl_dir) / name
        if f.read_text() != src:
            raise LkError(f"kit_dly_ram: staged {name} differs from the planned source")
        if chunks:
            tmp = f.with_name(f.name + ".dram_tmp")
            tmp.write_text(rewrite(src, chunks, cand))
            tmp.replace(f)
        rec[name] = dict(stats, rams=[{k: v for k, v in ch.items() if k != "names"} for ch in chunks])
    return rec


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        raise SystemExit(__doc__)

    def opt(k, d=None):
        return argv[argv.index(k) + 1] if k in argv else d
    src = Path(argv[0])
    t = json.loads(Path(opt("--type-json")).read_text())
    pins = [tuple(p) for p in json.loads(Path(opt("--pins")).read_text())] if opt("--pins") else []
    txt = src.read_text()
    chunks, stats, cand = plan(txt, t, pins, cfg_of(t) or dict(DEFAULTS))
    if opt("--out"):
        Path(opt("--out")).write_text(rewrite(txt, chunks, cand))
    rep = dict(stats, rams=[{k: v for k, v in ch.items() if k != "names"} for ch in chunks])
    if opt("--report"):
        Path(opt("--report")).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("rams", "skipped")} | dict(skipped=len(stats["skipped"]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
