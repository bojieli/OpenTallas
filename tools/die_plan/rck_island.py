"""Recovered-clock island of a serdes type (PLAN-READERS-1 11-14, FABLE-PLAN-B6B 6.4, FABLE-SERDES-STRUCT s0 S81 item 1).

Plan type key (opt-in, absent = kit byte-identical):

  partition_types[T].rck_island = {"rect_um": [x0, y0, x1, y1], "clock": "<pad clock name, e.g. io_pma_rck>",
                                   "inst_re": "<regexp on std-cell instance names>", "release_before_dpl": true}

Every std cell whose instance name matches `inst_re` and that is (a) a register in the fan-out of the `clock` port, or (b) a
combinational cell (never a clock buffer / inverter) goes into ONE placement region `rect_um` (an odb dbRegion fence of the
hook serdes_lanes.tcl, cfg key `islands`) for global placement; `release_before_dpl` (default true) removes the fence before
detail placement (serdes_lanes_release.tcl: the HARD-S81-SERDES-1 G3 DPL-0033 class).  The rck root (the pad clock entries of
pad_clock.py) sits at the island; the u_chn hard core and the SRAM sites of the recovered-clock domain are placed inside it.

Plan check (G0, schema.Plan): rect inside the outline with x0 < x1, y0 < y1; `clock` is a pad clock of the type; every hard core /
physical part whose module is a sink_pins module of that pad clock (except the PMA macros ot_s81_pma*, which stay at the PHY
edge) lies fully inside the rect (the island holds u_chn and the SRAMs); no other hard core / physical part overlaps it; it does not overlap a PHY PG domain of the type.
clock.keepouts_um is NOT used: it is the die-clock-cell exclusion (die_clock.py), and on the S81 serdes types it covers the
whole logic area (serdes__t2 [0, 238.76, 2735.76, 1226.88]).

derive(P, tn): the island from the type's OWN pad clock position (S81: the PMA W end), not HEAD's x 1603-2412 (that is the
HEAD hd_serdes pma_rx pin range).  plan_patch(P, tn): the plan data B6c needs (rck_island, the two pad-clock entries, the
u_chn + SRAM shift into the island), as a dict of dotted-path -> value for the plan owner to apply.
"""
import math
import re

# kitH geometry, serdes__t2 (epyc9 hard-s81-serdes-1 kitH / kitH2; FABLE-PLAN-B6B 6.4)
ISLAND_W_UM = 760.0
ISLAND_H_UM = 304.0
PAD_TO_X0_UM = 12.952            # io_pma_rck pad x 257.952 -> island x0 245.0
CHN_OFFSET_UM = (35.8, 40.448)   # u_chn KIT location (origin + track_offset_um) inside the island (t2: 280.8, 680.448 over 245, 640)
EARLY_CHN_PS = 175.0             # FABLE-SERDES-STRUCT: u_chn view needs 174.59 ps of hold
KEYS = {"rect_um", "clock", "inst_re", "release_before_dpl"}
PMA_PREFIX = "ot_s81_pma"         # the PMA macros (u_prx / u_ptx) are the island's source at the PHY edge, never inside it


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _boxes(t, modules=None):
    """[(label, module, x0, y0, x1, y1)] of the type's hard cores and physical parts (type frame, orient never swaps)."""
    out = []
    for c in t.get("hard_cores", []) or []:
        if c.get("origin_um") and c.get("outline_um"):
            (x, y), (w, h) = c["origin_um"], c["outline_um"]
            out.append((c["inst"], c.get("module"), x, y, x + w, y + h))
    for c in t.get("contents", []) or []:
        for p in c.get("physical_parts", []) or []:
            (x, y), (w, h) = p["origin_um"], p["outline_um"]
            out.append((p["physical_inst"], p.get("physical_master"), x, y, x + w, y + h))
    return out


def sink_modules(t, clock):
    """modules named by the sink_pins of the type's pad clock `clock` (the macros of the recovered-clock domain)."""
    for p in (t.get("clock", {}) or {}).get("pad_clock", {}).get("pins", []) or []:
        if p.get("name") == clock:
            return {s["module"] for s in p.get("sink_pins", []) or []}
    return None


def check(P, tn):
    """[error strings] of the type's rck_island (see the module note); [] when the key is absent or valid."""
    t = P.types[tn]
    r = t.get("rck_island")
    if r is None:
        return []
    e = []
    if not isinstance(r, dict) or not {"rect_um", "clock", "inst_re"} <= set(r) or set(r) - KEYS:
        return [f"type {tn}: rck_island needs rect_um, clock, inst_re (optional release_before_dpl) and nothing else"]
    rect = r["rect_um"]
    if not (isinstance(rect, list) and len(rect) == 4 and all(_num(v) for v in rect) and rect[0] < rect[2] and rect[1] < rect[3]):
        return [f"type {tn}: rck_island.rect_um must be [x0, y0, x1, y1] with x0 < x1, y0 < y1"]
    if "release_before_dpl" in r and not isinstance(r["release_before_dpl"], bool):
        e.append(f"type {tn}: rck_island.release_before_dpl must be a boolean")
    try:
        re.compile(r["inst_re"])
    except (re.error, TypeError):
        e.append(f"type {tn}: rck_island.inst_re is not a regular expression")
    if not isinstance(r["inst_re"], str) or not r["inst_re"] or any(c in r["inst_re"] for c in "{}\n\\"):
        e.append(f"type {tn}: rck_island.inst_re must be a nonempty single-line regexp without braces or backslashes")
    w, h = t["outline_um"]
    x0, y0, x1, y1 = rect
    if x0 < 0 or y0 < 0 or x1 > w + 1e-9 or y1 > h + 1e-9:
        e.append(f"type {tn}: rck_island {rect} is outside the outline {w} x {h}")
    mods = sink_modules(t, r["clock"])
    if mods is None:
        return e + [f"type {tn}: rck_island.clock {r['clock']!r} is not a pad_clock pin of the type"]
    held = 0
    for lab, mod, a, b, c, d in _boxes(t):
        inside = a >= x0 - 1e-6 and b >= y0 - 1e-6 and c <= x1 + 1e-6 and d <= y1 + 1e-6
        hit = a < x1 - 1e-6 and c > x0 + 1e-6 and b < y1 - 1e-6 and d > y0 + 1e-6
        if mod in mods and not str(mod).startswith(PMA_PREFIX):
            held += 1
            if not inside:
                e.append(f"type {tn}: rck_island {rect} must hold {lab} ({mod}, a {r['clock']} sink macro) at [{a:g}, {b:g}, {c:g}, {d:g}]")
        elif hit:
            e.append(f"type {tn}: rck_island {rect} overlaps {lab} ({mod}), which is not a {r['clock']} sink macro")
    if not held:
        e.append(f"type {tn}: rck_island.clock {r['clock']!r} has no sink macro (hard core / physical part) in the type to hold")
    try:
        import gen_phys
        for d in gen_phys.phy_pg_domains(P, tn):
            a, b, c, dd = d[3]
            if a < x1 and c > x0 and b < y1 and dd > y0:
                e.append(f"type {tn}: rck_island {rect} overlaps PHY PG domain {d[0]} {[a, b, c, dd]}")
    except ValueError as exc:      # S81-PHYPG-1 11-15: a PG domain error (straddling macro, core macro in the region) is a check error
        e.append(f"type {tn}: {exc}")
    except KeyError:
        pass
    return e


def island(P, tn):
    """the validated rck_island of the type, or None; ValueError (all errors) when invalid."""
    errs = check(P, tn)
    if errs:
        raise ValueError("; ".join(errs))
    r = P.types[tn].get("rck_island")
    return None if r is None else dict(r, release_before_dpl=r.get("release_before_dpl", True))


def exports(P, tn):
    """config.mk lines (OT_RCK_ISLAND*), [] when the key is absent."""
    r = island(P, tn)
    if r is None:
        return []
    x0, y0, x1, y1 = r["rect_um"]
    return ["export OT_RCK_ISLAND = 1", f"export OT_RCK_ISLAND_RECT_UM = {x0:g},{y0:g},{x1:g},{y1:g}",
            f"export OT_RCK_ISLAND_CLOCK = {r['clock']}", f"export OT_RCK_ISLAND_RELEASE = {int(r['release_before_dpl'])}"]


def cfg_tcl(P, tn):
    """the kit's serdes_lanes_cfg.tcl (dict sl_cfg read by serdes_lanes.tcl): one island, no lane chains / blockages."""
    r = island(P, tn)
    x0, y0, x1, y1 = r["rect_um"]
    return ("# GENERATED by tools/die_plan/gen.py phys (plan type key rck_island, PLAN-READERS-1).  Do not edit.\n"
            "set sl_cfg {\n  blocks {}\n  chains {}\n"
            f"  release_regions_before_dpl {int(r['release_before_dpl'])}\n"
            "  islands {\n"
            f"    {{rck_isl {x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f} {r['clock']} {{{r['inst_re']}}}}}\n"
            "  }\n}\n")


def derive(P, tn, width=ISLAND_W_UM, height=ISLAND_H_UM, band_gap_um=3.16):
    """island rect [x0, y0, x1, y1] anchored at the type's own recovered-clock pad x, directly under the rck_band top
    (the lower edge of the PHY PG region holding the receiver macro, gen_phys.rck_band_exports) minus band_gap_um
    (S81 serdes__t2: measured band top 947.16 -> island top 944; smoke PLAN-READERS-1).  Raises ValueError when it does not fit the outline."""
    import gen_phys
    t = P.types[tn]
    pads = [p for p in t["clock"]["pad_clock"]["pins"] if p["dir"] == "in"]
    if len(pads) != 1:
        raise ValueError(f"type {tn}: expected exactly one input pad clock, got {len(pads)}")
    px = pads[0]["xy_um"][0]
    top = float([x for x in gen_phys.rck_band_exports(P, tn) if "BAND_TOP" in x][0].split("=")[1])
    x0, y1 = round(px - PAD_TO_X0_UM, 3), round(top - band_gap_um, 3)
    rect = [x0, round(y1 - height, 3), round(x0 + width, 3), y1]
    w, h = t["outline_um"]
    if rect[0] < 0 or rect[1] < 0 or rect[2] > w:
        raise ValueError(f"type {tn}: island {rect} does not fit the outline {w} x {h}")
    return rect


def trunk(a, b, max_hop=400.0):
    """stations of an L-shaped trunk a -> corner (a.x, b.y) -> b, every hop <= max_hop (12.1e: 405 um); endpoints excluded."""
    corner = [a[0], b[1]]
    pts = []
    for p, q in ((list(a), corner), (corner, list(b))):
        d = abs(p[0] - q[0]) + abs(p[1] - q[1])
        n = max(1, math.ceil(d / max_hop - 1e-9))
        pts += [[round(p[0] + (q[0] - p[0]) * i / n, 3), round(p[1] + (q[1] - p[1]) * i / n, 3)] for i in range(1, n + 1)]
    pts = [p for i, p in enumerate(pts) if (i == len(pts) - 1 or p != pts[i + 1])]
    return [p for p in pts[:-1] if p != list(a)]


def domain_patch(P, tn):
    """{die domain name: die rect_um} of the die-rect shrink that keeps the PHY PG domains at the PHY floor.  NOT part of plan_patch
    any more (S81-PHYPG-1 11-15, FABLE-TRIAGE-S81 7.3): the shrink is the 41-error G0 path.  The island stays on the core supply by
    declared membership instead: type key phy_pg_macros (gen_phys.phy_pg_domains) lists the PMA macros, so u_chn and the SRAMs moved
    into the island are never PHY macros and the 14 die rects stay as they are.  Kept as an analysis helper (what the shrink would be)."""
    import gen_phys
    out = {}
    doms = {d["name"]: d for d in P.die.get("pg", {}).get("domains", []) or []}
    for inst in sorted(n for n, p in P.parts.items() if p["type"] == tn):
        a = P.rect(inst)
        for name, _p, _g, rt, _m in gen_phys.phy_pg_domains(P, tn):
            for dn, d in doms.items():
                b = d["rect_um"]
                if b[0] < a[2] and b[2] > a[0] and b[1] < a[3] and b[3] > a[1]:
                    u, v = P.to_die(inst, rt[:2]), P.to_die(inst, rt[2:])
                    out[dn] = [round(min(u[0], v[0]), 3), round(min(u[1], v[1]), 3), round(max(u[0], v[0]), 3), round(max(u[1], v[1]), 3)]
    return out


def plan_patch(P, tn, rect=None, rck_buf_cell=None):
    """the B6c plan data for one serdes type: {"rck_island": ..., "core_moves": {inst: new origin}, "sram_moves": {...},
    "entries": [rck_isl, rck_chn], "shift_um": (dx, dy)}.  u_chn goes to rect origin + CHN_OFFSET_UM (kit location), keeping its
    orientation and shape; every physical part of a rck sink module moves by the same vector (t2: (-583.2, +587.52)).
    rck_isl takes every other sink macro of the pad clock (at the island's NW corner), rck_chn takes u_chn alone (a buffer
    just west of the core, on the row at the clk pin height) with min_early_ps = EARLY_CHN_PS.  Trunks are L-shaped from the
    pad, hops <= 400 um.  The entry positions are a proposal: the plan owner moves them to free rows."""
    t = P.types[tn]
    rect = rect or derive(P, tn)
    clk = [p for p in t["clock"]["pad_clock"]["pins"] if p["dir"] == "in"][0]
    mods = sink_modules(t, clk["name"])
    chn = [c for c in t["hard_cores"] if c["module"] in mods]
    if len(chn) != 1:
        raise ValueError(f"type {tn}: expected one u_chn hard core among the pad clock sinks, got {[c['inst'] for c in chn]}")
    ox, oy = chn[0]["origin_um"]
    tox, toy = chn[0].get("track_offset_um") or (0.0, 0.0)       # the kit places the core at origin + track_offset_um
    nx, ny = round(rect[0] + CHN_OFFSET_UM[0] - tox, 3), round(rect[1] + CHN_OFFSET_UM[1] - toy, 3)
    dx, dy = round(nx - ox, 3), round(ny - oy, 3)
    parts = {p["physical_inst"]: [round(p["origin_um"][0] + dx, 3), round(p["origin_um"][1] + dy, 3)]
             for c in t.get("contents", []) for p in c.get("physical_parts", []) or [] if p.get("physical_master") in mods and str(p.get("physical_master")).startswith("ot_sram")}
    pad = clk["xy_um"]
    ci = [round(rect[0] + 12.0, 3), round(rect[3] - 12.0, 3)]
    w, h = chn[0]["outline_um"]
    cc = [round(nx + tox - 4.32, 3), round(ny + toy + h / 2.0, 3)]
    ent = [dict(name="rck_isl", xy_um=ci, stations_um=trunk(pad, ci), cell=rck_buf_cell, region_um=[list(rect)],
                sink_pins=[s for s in clk["sink_pins"] if s["module"] != chn[0]["module"]], evidence="FABLE_SERDES_STRUCT_s0_1"),
           dict(name="rck_chn", xy_um=cc, stations_um=trunk(pad, cc), cell=rck_buf_cell,
                region_um=[[round(cc[0] - 1.08, 3), round(cc[1] - 0.27, 3), round(cc[0] + 1.08, 3), round(cc[1] + 0.27, 3)]],
                sink_pins=[s for s in clk["sink_pins"] if s["module"] == chn[0]["module"]],
                evidence="FABLE_SERDES_STRUCT_s0_2", min_early_ps=EARLY_CHN_PS)]
    return dict(rck_island=dict(rect_um=list(rect), clock=clk["name"], inst_re="u_core[.](u_dec|u_rxf|u_lrx)", release_before_dpl=True),
                core_moves={chn[0]["inst"]: [nx, ny]}, sram_moves=parts, shift_um=(dx, dy), entries=ent)
