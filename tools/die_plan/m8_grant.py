#!/usr/bin/env python3
"""M8 leftover grant for partition types (LAYER-BUDGET-1, OWNER 11-11 "grant the leftover M8 for all dies").

The die owns M8/M9 (METHODOLOGY 12.1).  A type may route on M8 inside its footprint, but only on the tracks the die
does not use there.  This module turns the die's M8 use over every placed instance of a type into ONE per-type
track partition in the type frame:

  die tracks  = M8 tracks blocked by the die PG stripes (die_infra.pg_rects over pg_grid: core grid + PHY domains,
                min spacing kept), PLUS the die's reserved tracks: the planned die-top signal share
                (layer_budget.cut_avail["M8"] of the PG-free tracks; schema default 0) and, when a die route is given
                (OpenROAD write_guides of the die clock / reset / die-top GRT or DRT), its M8 demand over the
                footprint (clock nets at their NDR width + spacing, one guard track toward the type),
  type tracks = everything else (the grant).

Tracks are symmetric (schema.ASAP7_LAYERS: offset = pitch / 2, partition origins on the die lattice), so track k of the
type frame is the same die track for R0 / MX / MY / R180 instances; a type with several instances takes the UNION of
their die tracks (the kit is shared).  A track blocked anywhere along the footprint is blocked over its full width
(conservative for partial-width PHY-domain stripes).

Products (all deterministic, sha-stamped):
  grant(P, tn, guides=None) -> dict      the per-type window (layer, pitch, die/type track runs, supply)
  obstruction_tcl(grant, w)              type-kit pdn.tcl lines: one dbObstruction per die track at wire width (the type
                                         routes only on its own tracks; a die track's obstruction covers its wire, so an
                                         adjacent type track keeps the 0.04 um minimum spacing by construction)
  abstract_obs_rects(grant, w)           M8 OBS for the type's abstract = its OWN tracks, one rect per track at wire width,
                                         so the die sees exactly the granted tracks as used and keeps routing / PG on its
                                         own tracks

NARROW SHAPES (HEAD-ROUTE-1 11-12): every emitted M8 rect is one track wide (0.04 um).  ASAP7 M8 SPACINGTABLE needs 0.5 um
beside a shape >= 0.49975 um wide at parallel run >= 1.79975 um, and the tech LEF says USEMINSPACING OBS OFF, so DRT
applies the table to obstructions / macro OBS at their drawn width.  A run of >= 7 tracks emitted as ONE rect (0.60 um for
a PG run of 8) made DRT keep 0.5 um from it: 12 of the 19 granted tracks per 2.16-um period were unusable for long runs
while GRT counted all 19 -> M8 guides DR could not realise (head_rp18_1112: DRT-0255 on hd_turn_a / hd_turn_b /
hd_spn_wshim_rx / hd_spn_wshim_tx, 4.7k-83k DR violations, all on M8).  Die PG stripes themselves keep the
width-dependent spacing (die_infra.pg_spacing: 0.04 below 0.49975 um, 0.5 / 1.0 for the wide PHY stripes).
  fix_abstract_lef(text, grant)          rewrite the LEF M8 OBS of a generated abstract to abstract_obs_rects
  lock_check(grant, P, guides=None)      LOCK: re-derive the die tracks from a later plan / die route; every die track
                                         that falls on a granted type track is a violation (the die event must route
                                         elsewhere, or the type re-signs with a new grant)

CLI:  m8_grant.py report --plan PLAN [--guide G] [--types T ...] [--out TSV]
      m8_grant.py lock   --plan PLAN --grant m8_grant.json [--guide G]
      m8_grant.py fixlef --grant m8_grant.json LEF [LEF ...]
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# schema / die_infra are imported lazily: the kit copy (fixlef after generate_abstract) runs without the plan tools

LAYER = "M8"
# WAVE-RECIPE-1 11-14 (OWNER ruling ~20:00 via COORD: "types may use the REMAINING M8/M9 space; every type kit imports the
# die's pre-routed M8/M9 infra shapes over its outline as routing obstructions"): the same grant on M9, the vertical die
# layer.  Every function takes layer= (default M8, so every M8 caller and every existing m8_grant.json is unchanged);
# on a vertical layer the tracks are x positions across the type width and the die stripes are x bands.
LAYERS = ("M8", "M9")
WIRE_W = 0.040          # ASAP7 M8 / M9 WIDTH
MIN_SP = 0.040          # ASAP7 M8 / M9 SPACING (parallel run, w < 0.5)
WIDE_W = 0.49975        # ASAP7 M8 SPACINGTABLE width row from which a long parallel run needs 0.5 um (see NARROW SHAPES)
SCHEMA = "ot.m8_grant.v1"
CLOCK_NET_RE = re.compile(r"^(ck_|clk|ck\b|.*_clk$|.*clock)")
RESET_NET_RE = re.compile(r"(rst|reset)")
WANT_DIR = {"M8": "H", "M9": "V"}


def _check_layer(layer):
    if layer not in LAYERS:
        raise ValueError(f"grant layer {layer!r}: one of {LAYERS}")
    return layer


def _layer(P, layer=LAYER):
    _check_layer(layer)
    L = P.layers.get(layer)
    if not L or L["dir"] != WANT_DIR[layer]:
        raise ValueError(f"{layer} must be a {'horizontal' if WANT_DIR[layer] == 'H' else 'vertical'} plan layer (ASAP7)")
    return L["pitch_um"], L["offset_um"]


def _horiz(layer):
    return WANT_DIR[_check_layer(layer)] == "H"


def n_tracks(P, tn, layer=LAYER):
    p, off = _layer(P, layer)
    w, h = P.types[tn]["outline_um"]
    ext = h if _horiz(layer) else w
    return int(math.floor((ext - off) / p + 1e-9)) + 1 if ext > off else 0


def track_y(P, k, layer=LAYER):
    """type-frame centre of track k (y on M8, x on M9)"""
    p, off = _layer(P, layer)
    return off + k * p


def instances(P, tn):
    return sorted(n for n, q in P.parts.items() if q.get("type") == tn)


def _type_y(P, part, y):
    return P.to_type(part, (P.rect(part)[0], y))[1]


def _type_c(P, part, c, layer):
    """die coordinate across the tracks (y on M8, x on M9) -> type frame"""
    if _horiz(layer):
        return _type_y(P, part, c)
    return P.to_type(part, (c, P.rect(part)[1]))[0]


def _blocked_by_band(P, tn, lo, hi, pad, layer=LAYER):
    """type-frame track indices whose wire [c-w/2, c+w/2] comes within `pad` of the band [lo, hi]."""
    p, off = _layer(P, layer)
    n = n_tracks(P, tn, layer)
    a = math.ceil((lo - pad - WIRE_W / 2 - off) / p - 1e-9)
    b = math.floor((hi + pad + WIRE_W / 2 - off) / p + 1e-9)
    out = set()
    for k in range(max(0, a), min(n - 1, b) + 1):
        c = off + k * p
        if c + WIRE_W / 2 > lo - pad + 1e-9 and c - WIRE_W / 2 < hi + pad - 1e-9:
            out.add(k)
    return out


def pg_tracks(P, tn, rects=None, layer=LAYER):
    """{k} blocked by die PG stripes of `layer` over any instance of tn (the stripe's width-dependent spacing kept:
    die_infra.pg_spacing of its drawn width at a long parallel run, 0.04 um for the 0.48-um core stripes, 1.0 um beside
    the 12.96-um M9 straps of KV / HEAD / HBM)."""
    import die_infra as DI
    if rects is None:
        rects = [r for r in DI.pg_rects(P, DI.pg_grid(P)) if r[1] == layer]
    hz = _horiz(layer)
    out = set()
    for part in instances(P, tn):
        x0, y0, x1, y1 = P.rect(part)
        for _net, _L, a0, b0, a1, b1 in rects:
            if _L != layer or a1 <= x0 or a0 >= x1 or b1 <= y0 or b0 >= y1:
                continue
            if hz:
                t0, t1 = sorted((_type_c(P, part, max(b0, y0), layer), _type_c(P, part, min(b1, y1), layer)))
                wd = b1 - b0
            else:
                t0, t1 = sorted((_type_c(P, part, max(a0, x0), layer), _type_c(P, part, min(a1, x1), layer)))
                wd = a1 - a0
            out |= _blocked_by_band(P, tn, t0, t1, max(MIN_SP, DI.pg_spacing(wd)), layer)
    return out


def _ndr_tracks(net, ndr):
    import die_infra as DI
    if CLOCK_NET_RE.search(net):
        w, s = DI.NDR[ndr]
        return int(math.ceil((w + 2 * s) / _PITCH_CACHE[0] - 1e-9)) + 1, "clock"   # + 1 guard track toward the type
    if RESET_NET_RE.search(net):
        return 1, "reset"
    return 1, "signal"


_PITCH_CACHE = [0.08]
_IDX = {}


def _m8_index(guides, layer=LAYER):
    """guide boxes of a die route on `layer`, sorted by their low coordinate across the tracks (built once per guides
    object and layer).  Rows: (c0, net, a0, b0, a1, b1, c1)."""
    key = (id(guides), layer)
    if key not in _IDX:
        hz = _horiz(layer)
        rows = sorted(((b0 if hz else a0), net, a0, b0, a1, b1, (b1 if hz else a1)) for net, boxes in guides.items()
                      for L, a0, b0, a1, b1 in boxes if L == layer)
        _IDX.clear()
        _IDX[key] = ([r[0] for r in rows], rows, max((r[6] - r[0] for r in rows), default=0.0))
    return _IDX[key]


def _m8_query(idx, y0, y1):
    import bisect
    ys, rows, hmax = idx
    for r in rows[bisect.bisect_left(ys, y0 - hmax):bisect.bisect_left(ys, y1)]:
        _c0, net, a0, b0, a1, b1, _c1 = r
        yield net, a0, b0, a1, b1


def route_demand(P, tn, guides, ndr="4w", signals=False, layer=LAYER):
    """{(lo, hi) type-frame band: tracks} of the die route's use of `layer` over the instances of tn (max over
    instances, each guide box = one net through the band, clock nets at NDR width + spacing + one guard)."""
    _PITCH_CACHE[0] = _layer(P, layer)[0]
    hz = _horiz(layer)
    per = {}
    kinds = {}
    idx = _m8_index(guides, layer)
    for part in instances(P, tn):
        x0, y0, x1, y1 = P.rect(part)
        nets = {}                    # band -> distinct nets (a net's gcell boxes along one band share its tracks)
        for net, a0, b0, a1, b1 in _m8_query(idx, *((y0, y1) if hz else (x0, x1))):
            if a1 <= x0 or a0 >= x1 or b1 <= y0 or b0 >= y1:
                continue
            lo, hi = (max(b0, y0), min(b1, y1)) if hz else (max(a0, x0), min(a1, x1))
            t0, t1 = sorted((_type_c(P, part, lo, layer), _type_c(P, part, hi, layer)))
            nets.setdefault((round(t0, 4), round(t1, 4)), set()).add(net)
        for key, ns in nets.items():
            v = 0
            for net in ns:
                k, kind = _ndr_tracks(net, ndr)
                if kind == "signal" and not signals:
                    # die-top signals on M8/M9 are the plan's cut_avail share (reserved separately); their guide boxes
                    # without it are GRT via-access augmentation (write_guides), not wires on that layer
                    kinds["signal_skipped"] = kinds.get("signal_skipped", 0) + 1
                    continue
                v += k
                kinds[kind] = kinds.get(kind, 0) + 1
            per[key] = max(per.get(key, 0), v)
    return per, kinds


def _runs(ks):
    out, ks = [], sorted(ks)
    for k in ks:
        if out and k == out[-1][1] + 1:
            out[-1][1] = k
        else:
            out.append([k, k])
    return out


def _pick(free, want, pg, n, shift=0):
    """`want` tracks from `free`, the ones nearest a PG-blocked track first (die tracks hug the stripes: one shielded
    side, type tracks stay in contiguous runs); ties by index.  shift (tracks, default 0): the reference PG tracks are moved by
    this much (r153 fix 4 grant phase: the die tracks then hug the shifted band, so the type tracks do not sit over the M6 pair)."""
    if want <= 0:
        return set()
    pgs = sorted(k + shift for k in pg)

    def dist(k):
        if not pgs:
            return 0
        import bisect
        i = bisect.bisect_left(pgs, k)
        d = min(abs(k - pgs[j]) for j in (i - 1, i) if 0 <= j < len(pgs))
        return d
    return set(sorted(free, key=lambda k: (dist(k), k))[:want])


def grant(P, tn, guides=None, ndr="4w", guide_sha=None, pg_rects=None, layer=LAYER, phase_um=0.0):
    p, off = _layer(P, layer)
    shift = int(round(float(phase_um) / p)) if phase_um else 0
    w, h = P.types[tn]["outline_um"]
    n = n_tracks(P, tn, layer)
    pg = pg_tracks(P, tn, pg_rects, layer)
    free = [k for k in range(n) if k not in pg]
    ca = float((P.layer_budget.get("cut_avail") or {}).get(layer, 0.0))
    die = set(_pick(free, int(math.ceil(ca * len(free) - 1e-9)), pg, n, shift))
    kinds = {}
    route = 0
    if guides:
        dem, kinds = route_demand(P, tn, guides, ndr, layer=layer)
        for (t0, t1), v in sorted(dem.items()):
            band = [k for k in range(n) if t0 - 1e-9 <= off + k * p <= t1 + 1e-9 and k not in pg and k not in die]
            take = set(_pick(band, v, pg | die, n, shift))
            route += len(take)
            die |= take
    blocked = pg | die
    typ = [k for k in range(n) if k not in blocked]
    g = dict(schema=SCHEMA, type=tn, plan=P.name, layer=layer, pitch_um=p, offset_um=off, outline_um=[w, h],
             instances=instances(P, tn), n_tracks=n, pg_tracks=len(pg), die_reserve_tracks=len(die) - route,
             die_route_tracks=route, type_tracks=len(typ), free_frac=round(len(typ) / n, 4) if n else 0.0,
             cut_avail=ca, ndr=ndr, route_kinds=kinds, guide_sha=guide_sha,
             die_runs=_runs(blocked), type_runs=_runs(typ))
    if shift:
        g["phase_um"] = float(phase_um)        # only a shifted grant carries the key (default grants stay byte-identical)
    if not _horiz(layer):
        g["dir"] = "V"               # M8 grants carry no dir key (byte-identical to the v1 grants already in kits)
    g["sha"] = hashlib.sha256(json.dumps({k: v for k, v in g.items() if k != "sha"}, sort_keys=True).encode()).hexdigest()[:16]
    return g


def _track_rects(g, runs):
    """one (x0, y0, x1, y1) per track of `runs` at wire width (NARROW SHAPES: never a merged >= 0.49975-um rect);
    horizontal tracks on M8, vertical on M9 (g["dir"] V)."""
    w, h = g["outline_um"]
    p, off = g["pitch_um"], g["offset_um"]
    vert = g.get("dir") == "V"
    ext = w if vert else h
    out = []
    for k0, k1 in runs:
        for k in range(k0, k1 + 1):
            c0, c1 = max(0.0, off + k * p - WIRE_W / 2), min(ext, off + k * p + WIRE_W / 2)
            if c1 > c0:
                out.append((c0, 0.0, c1, h) if vert else (0.0, c0, w, c1))
    return out


def obstruction_tcl(g):
    """pdn.tcl lines: obstruct every die track on the grant's layer, one wire-width rect per track (NARROW SHAPES)."""
    L =[f"# {g['layer']} GRANT {g['sha']} (tools/die_plan/m8_grant.py): the type routes {g['layer']} only on its {g['type_tracks']} of "
         f"{g['n_tracks']} tracks; die tracks (PG {g['pg_tracks']}, die reserve {g['die_reserve_tracks']}, die route "
         f"{g['die_route_tracks']}) are obstructed",
         "set blk [ord::get_db_block]", "set dbu [$blk getDbUnitsPerMicron]",
         f"set lay [[ord::get_db_tech] findLayer {g['layer']}]"]
    for r in _track_rects(g, g["die_runs"]):
        L.append("odb::dbObstruction_create $blk $lay " + " ".join(f"[expr {{round({v:.4f}*$dbu)}}]" for v in r))
    return "\n".join(L) + "\n"


def abstract_obs_rects(g):
    """the type's own (granted) tracks as abstract OBS on the grant's layer, one wire-width rect per track (NARROW SHAPES)."""
    return _track_rects(g, g["type_runs"])


def grants_of(doc):
    """an m8_grant.json document -> [grant, ...]: the M8 grant itself plus its extra_grants (the M9 grant of an M9 kit)"""
    return [doc] + [x for x in (doc.get("extra_grants") or []) if isinstance(x, dict)]


def fix_abstract_lef(text, g):
    """Replace the M8 part of the macro OBS by the granted-track rects (add an OBS block when there is none)."""
    out, i, lines = [], 0, text.splitlines()
    # an OBS section ends with a bare "END"; the macro ends with "END <name>"
    rects = [f"      RECT {a:.3f} {b:.3f} {c:.3f} {d:.3f} ;" for a, b, c, d in abstract_obs_rects(g)]
    new = [f"    LAYER {g['layer']} ;"] + rects if rects else []
    in_obs = done = False
    skip = False
    while i < len(lines):
        s = lines[i].strip()
        if s == "OBS":
            in_obs = True
            out.append(lines[i])
            i += 1
            continue
        if in_obs:
            if s.startswith("LAYER "):
                skip = s.split()[1] == g["layer"]
                if skip:
                    i += 1
                    continue
            elif s == "END":
                out += new
                done = True
                in_obs = skip = False
                out.append(lines[i])
                i += 1
                continue
            if skip:
                i += 1
                continue
        out.append(lines[i])
        i += 1
    if not done:                         # no OBS section: insert one before the macro's END <name>
        for j in range(len(out) - 1, -1, -1):
            m = re.match(r"^END\s+(\S+)\s*$", out[j].strip())
            if m and m.group(1) != "LIBRARY":
                out[j:j] = ["  OBS"] + new + ["  END"]
                break
    return "\n".join(out) + "\n"


def lock_check(g, P, guides=None, ndr=None):
    """die tracks of the new plan / die route that land on granted type tracks (empty list = PASS)."""
    tn = g["type"]
    layer = g.get("layer") or LAYER
    if tn not in P.types:
        return [f"type {tn} no longer in plan {P.name}"]
    if list(P.types[tn]["outline_um"]) != list(g["outline_um"]):
        return [f"type {tn} outline changed {g['outline_um']} -> {P.types[tn]['outline_um']}"]
    new = grant(P, tn, guides, ndr or g.get("ndr", "4w"), layer=layer)
    typ = {k for a, b in g["type_runs"] for k in range(a, b + 1)}
    die = {k for a, b in new["die_runs"] for k in range(a, b + 1)}
    bad = sorted(typ & die)
    ax = "y" if _horiz(layer) else "x"
    return [f"type {tn}: die {layer} track {k} ({ax} {g['offset_um'] + k * g['pitch_um']:.3f}) is a granted type track"
            for k in bad]


GRANT_KEY = {"M8": "type_m8_grant", "M9": "type_m9_grant"}
GRANT_ENV = {"M8": "OT_GEN_M8_GRANT", "M9": "OT_GEN_M9_GRANT"}


def grant_config(P, layer=LAYER):
    """layer_budget.type_m8_grant / type_m9_grant normalised: None (off) or dict(enable, types, guide, ndr).
    OT_GEN_M8_GRANT=1 / OT_GEN_M9_GRANT=1 at generation turns it on for A/B kits without a plan event."""
    c = P.layer_budget.get(GRANT_KEY[_check_layer(layer)])
    if c is None and os.environ.get(GRANT_ENV[layer]) == "1":
        c = True
    if c is None or c is False:
        return None
    if c is True:
        c = {}
    c = dict(enable=c.get("enable", True), types=c.get("types"), guide=c.get("guide"), ndr=c.get("ndr", "4w"),
             phase_um=float(c.get("phase_um", 0.0)), type_guides=dict(c.get("type_guides") or {}))
    return c if c["enable"] else None


def m9_clock_refusal(tn, why):
    return (f"type {tn}: M9 grant refused (fail closed, PLAN-READERS-1): {why}.  S81 die M9 use is the clock spine + PG and every "
            "type tap pin sits on M9 (clock.layer M9): name the die route guides that carry the die clock "
            "(layer_budget.type_m9_grant.guide, OpenROAD write_guides of the die clock route), or do not grant M9")


def check_m9_clock(P, tn, G, g, ndr="4w"):
    """PLAN-READERS-1 11-14: precondition of every M9 grant.  The die route guides `G` must be the die clock route and must
    agree with this grant: (1) at least one die clock net holds an M9 guide box (else the file is not the clock route);
    (2) a type whose taps are on M9 (clock.layer M9) sees die M9 clock guides over at least one placed instance (else the
    guides do not cover its clock entries: the grant would route over the spine legs); (3) tracks remain for the type.
    ValueError with the reason otherwise."""
    if not G:
        raise ValueError(m9_clock_refusal(tn, "the die route guide file is empty"))
    if not any(L == "M9" and CLOCK_NET_RE.search(net) for net, boxes in G.items() for L, *_ in boxes):
        raise ValueError(m9_clock_refusal(tn, "the die route guides hold no M9 clock segment (not the die clock route)"))
    ck = P.types[tn].get("clock", {}) or {}
    if ck.get("layer") == "M9":
        _dem, kinds = route_demand(P, tn, G, ndr, layer="M9")
        if not kinds.get("clock"):
            raise ValueError(m9_clock_refusal(tn, f"the type's clock taps are on M9 but the die guides carry no M9 clock segment over "
                                                  f"its instances {instances(P, tn)}"))
    if g["type_tracks"] <= 0:
        raise ValueError(m9_clock_refusal(tn, "no M9 track is left for the type after the die PG, reserve and clock route"))


def kit_grant(P, tn, layer=LAYER, force=False):
    """the grant a type kit carries on `layer`, or None (grant off, type not selected, ceiling already >= layer, not
    placed).  force=True: the M8 grant an M9 kit needs (an M9 route reaches M9 only through M8, so M8 must be obstructed
    on the die tracks too) even when the M8 grant itself is off; it then takes the M9 grant's guide / ndr."""
    c = grant_config(P, layer)
    if c is None and force:
        c = grant_config(P, "M9") or dict(enable=True, types=None, guide=None, ndr="4w")
        c = dict(c, types=None)
    if c is None or (c["types"] is not None and tn not in c["types"]):
        return None
    if int(P.layer_budget["partition_signal_max"][1:]) >= int(layer[1:]) or not instances(P, tn):
        return None
    if layer == "M9" and not c["guide"]:
        raise ValueError(m9_clock_refusal(tn, "layer_budget.type_m9_grant.guide is not set (no die route guides to prove the M9 "
                                              "clock use; without them the grant subtracts the die PG straps only)"))
    G, gsha = None, None
    # HEAD-PLAN-R4 11-18 (COORD, M8 lock of the HEAD die clock): type_guides {type: [guide, ...]} re-grants ONE type from the UNION
    # of its own die route guides (e.g. the frozen route + the new die clock route) while every other type keeps `guide`, so an
    # open type clears its lock conflicts without touching a signed type's grant.  Absent = unchanged.
    names = (c.get("type_guides") or {}).get(tn) or ([c["guide"]] if c["guide"] else [])
    if isinstance(names, str):
        names = [names]
    for name in names:
        gp = Path(name)
        if not gp.is_absolute() and P.path:
            gp = Path(P.path).resolve().parent / gp
        if not gp.is_file():
            raise FileNotFoundError(f"type {tn}: layer_budget.{GRANT_KEY[layer]} guide {gp} missing")
        Gi, si = _guides(str(gp))
        if G is None:
            G, gsha = Gi, si
        else:
            G = {n: list(G.get(n, [])) + list(Gi.get(n, [])) for n in set(G) | set(Gi)}
            gsha = gsha + "+" + si
    g = grant(P, tn, G, c["ndr"], gsha, layer=layer, phase_um=c.get("phase_um", 0.0))
    if layer == "M9":
        check_m9_clock(P, tn, G, g, c["ndr"])
    return g



def check_lock(P, R, lock, guide=None):
    """G0 hook (check.py --m8-grant-lock): ERROR [m8_grant_lock] per die track on a signed type's granted track."""
    files = sorted(Path(lock).glob("*.json")) if Path(lock).is_dir() else [Path(lock)]
    G, _ = _guides(guide)
    n = bad = 0
    for f in files:
        doc = json.loads(f.read_text())
        if doc.get("schema") != SCHEMA:
            continue
        for g in grants_of(doc):                 # + the M9 grant of an M9 kit
            n += 1
            for msg in lock_check(g, P, G):
                bad += 1
                if bad <= 40:
                    R.err("m8_grant_lock", f"{msg} (grant {g['sha']} {f.name}): route the die elsewhere or re-sign the type")
    return dict(grants=n, violations=bad)


def _guides(path):
    if not path:
        return None, None
    import die_infra as DI
    return DI.read_guides(path), hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def report(P, types=None, guides=None, gsha=None, ndr="4w"):
    import die_infra as DI
    rects = [r for r in DI.pg_rects(P, DI.pg_grid(P)) if r[1] == LAYER]
    rows = []
    for tn in sorted(types or P.types):
        if not instances(P, tn):
            continue
        g = grant(P, tn, guides, ndr, gsha, pg_rects=rects)
        w, h = g["outline_um"]
        rows.append((tn, len(g["instances"]), w * h * len(g["instances"]), g))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("--plan", required=True)
    r.add_argument("--guide")
    r.add_argument("--ndr", default="4w")
    r.add_argument("--types", nargs="*")
    r.add_argument("--out")
    lk = sub.add_parser("lock")
    lk.add_argument("--plan", required=True)
    lk.add_argument("--grant", required=True, nargs="+")
    lk.add_argument("--guide")
    fx = sub.add_parser("fixlef")
    fx.add_argument("--grant", required=True)
    fx.add_argument("lef", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "fixlef":
        doc = json.loads(Path(a.grant).read_text())
        for f in a.lef:
            for g in grants_of(doc):          # the M8 grant, then the M9 grant of an M9 kit (extra_grants)
                Path(f).write_text(fix_abstract_lef(Path(f).read_text(), g))
                print(f"M8GRANT fixlef {f} {g.get('layer', LAYER)} {g['sha']} type_runs {len(g['type_runs'])}")
        return 0
    import schema as S
    P = S.Plan(S.load(a.plan), Path(a.plan))
    G, gsha = _guides(a.guide)
    if a.cmd == "lock":
        bad = []
        for f in a.grant:
            for g in grants_of(json.loads(Path(f).read_text())):
                bad += lock_check(g, P, G)
        for b in bad:
            print("M8GRANT LOCK FAIL", b)
        print("M8GRANT LOCK", "PASS" if not bad else f"FAIL {len(bad)}")
        return 1 if bad else 0
    rows = report(P, a.types, G, gsha, a.ndr)
    hdr = "type\tn_inst\tn_tracks\tpg\tdie_reserve\tdie_route\ttype_tracks\tfree_frac\tgrant_sha"
    lines = [hdr] + [f"{tn}\t{ni}\t{g['n_tracks']}\t{g['pg_tracks']}\t{g['die_reserve_tracks']}\t"
                     f"{g['die_route_tracks']}\t{g['type_tracks']}\t{g['free_frac']:.4f}\t{g['sha']}"
                     for tn, ni, area, g in rows]
    tot = sum(area for _, _, area, _ in rows)
    fw = sum(area * g["free_frac"] for _, _, area, g in rows) / tot if tot else 0.0
    summ = (f"# die {P.name}: {len(rows)} placed types, area-weighted M8 type share {fw:.4f}, "
            f"cut_avail {float((P.layer_budget.get('cut_avail') or {}).get(LAYER, 0.0)):g}, guide {gsha}")
    text = "\n".join(lines + [summ]) + "\n"
    if a.out:
        Path(a.out).write_text(text)
    print(summ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
