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
  obstruction_tcl(grant, w)              type-kit pdn.tcl lines: one dbObstruction per run of die tracks (the type routes
                                         only on its own tracks; a die track's obstruction covers its wire, so an
                                         adjacent type track keeps the 0.04 um minimum spacing by construction)
  abstract_obs_rects(grant, w)           M8 OBS for the type's abstract = its OWN tracks (wire extent), so the die sees
                                         exactly the granted tracks as used and keeps routing / PG on its own tracks
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
WIRE_W = 0.040          # ASAP7 M8 WIDTH
MIN_SP = 0.040          # ASAP7 M8 SPACING (parallel run, w < 0.5)
SCHEMA = "ot.m8_grant.v1"
CLOCK_NET_RE = re.compile(r"^(ck_|clk|ck\b|.*_clk$|.*clock)")
RESET_NET_RE = re.compile(r"(rst|reset)")


def _layer(P):
    L = P.layers.get(LAYER)
    if not L or L["dir"] != "H":
        raise ValueError(f"{LAYER} must be a horizontal plan layer (ASAP7)")
    return L["pitch_um"], L["offset_um"]


def n_tracks(P, tn):
    p, off = _layer(P)
    h = P.types[tn]["outline_um"][1]
    return int(math.floor((h - off) / p + 1e-9)) + 1 if h > off else 0


def track_y(P, k):
    p, off = _layer(P)
    return off + k * p


def instances(P, tn):
    return sorted(n for n, q in P.parts.items() if q.get("type") == tn)


def _type_y(P, part, y):
    return P.to_type(part, (P.rect(part)[0], y))[1]


def _blocked_by_band(P, tn, lo, hi, pad):
    """type-frame track indices whose M8 wire [c-w/2, c+w/2] comes within `pad` of the band [lo, hi]."""
    p, off = _layer(P)
    n = n_tracks(P, tn)
    a = math.ceil((lo - pad - WIRE_W / 2 - off) / p - 1e-9)
    b = math.floor((hi + pad + WIRE_W / 2 - off) / p + 1e-9)
    out = set()
    for k in range(max(0, a), min(n - 1, b) + 1):
        c = off + k * p
        if c + WIRE_W / 2 > lo - pad + 1e-9 and c - WIRE_W / 2 < hi + pad - 1e-9:
            out.add(k)
    return out


def pg_tracks(P, tn, rects=None):
    """{k} blocked by die PG M8 stripes over any instance of tn (min spacing kept)."""
    import die_infra as DI
    if rects is None:
        rects = [r for r in DI.pg_rects(P, DI.pg_grid(P)) if r[1] == LAYER]
    out = set()
    for part in instances(P, tn):
        x0, y0, x1, y1 = P.rect(part)
        for _net, _L, a0, b0, a1, b1 in rects:
            if a1 <= x0 or a0 >= x1 or b1 <= y0 or b0 >= y1:
                continue
            t0, t1 = sorted((_type_y(P, part, max(b0, y0)), _type_y(P, part, min(b1, y1))))
            out |= _blocked_by_band(P, tn, t0, t1, MIN_SP)
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


def _m8_index(guides):
    """M8 guide boxes of a die route, sorted by y0 (built once per guides object)."""
    key = id(guides)
    if key not in _IDX:
        rows = sorted((b0, net, a0, a1, b1) for net, boxes in guides.items()
                      for L, a0, b0, a1, b1 in boxes if L == LAYER)
        _IDX.clear()
        _IDX[key] = ([r[0] for r in rows], rows, max((r[4] - r[0] for r in rows), default=0.0))
    return _IDX[key]


def _m8_query(idx, y0, y1):
    import bisect
    ys, rows, hmax = idx
    for r in rows[bisect.bisect_left(ys, y0 - hmax):bisect.bisect_left(ys, y1)]:
        b0, net, a0, a1, b1 = r
        yield net, a0, b0, a1, b1


def route_demand(P, tn, guides, ndr="4w", signals=False):
    """{(y_lo, y_hi) type-frame band: tracks} of the die route's M8 use over the instances of tn (max over instances,
    each guide box = one net through the band, clock nets at NDR width + spacing + one guard)."""
    _PITCH_CACHE[0] = _layer(P)[0]
    per = {}
    kinds = {}
    idx = _m8_index(guides)
    for part in instances(P, tn):
        x0, y0, x1, y1 = P.rect(part)
        nets = {}                    # band -> distinct nets (a net's gcell boxes along one band share its tracks)
        for net, a0, b0, a1, b1 in _m8_query(idx, y0, y1):
            if a1 <= x0 or a0 >= x1 or b1 <= y0 or b0 >= y1:
                continue
            t0, t1 = sorted((_type_y(P, part, max(b0, y0)), _type_y(P, part, min(b1, y1))))
            nets.setdefault((round(t0, 4), round(t1, 4)), set()).add(net)
        for key, ns in nets.items():
            v = 0
            for net in ns:
                k, kind = _ndr_tracks(net, ndr)
                if kind == "signal" and not signals:
                    # die-top signals on M8 are the plan's cut_avail share (reserved separately); their M8 guide boxes
                    # without it are GRT via-access augmentation (write_guides), not M8 wires
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


def _pick(free, want, pg, n):
    """`want` tracks from `free`, the ones nearest a PG-blocked track first (die tracks hug the stripes: one shielded
    side, type tracks stay in contiguous runs); ties by index."""
    if want <= 0:
        return set()
    pgs = sorted(pg)

    def dist(k):
        if not pgs:
            return 0
        import bisect
        i = bisect.bisect_left(pgs, k)
        d = min(abs(k - pgs[j]) for j in (i - 1, i) if 0 <= j < len(pgs))
        return d
    return set(sorted(free, key=lambda k: (dist(k), k))[:want])


def grant(P, tn, guides=None, ndr="4w", guide_sha=None, pg_rects=None):
    p, off = _layer(P)
    w, h = P.types[tn]["outline_um"]
    n = n_tracks(P, tn)
    pg = pg_tracks(P, tn, pg_rects)
    free = [k for k in range(n) if k not in pg]
    ca = float((P.layer_budget.get("cut_avail") or {}).get(LAYER, 0.0))
    die = set(_pick(free, int(math.ceil(ca * len(free) - 1e-9)), pg, n))
    kinds = {}
    route = 0
    if guides:
        dem, kinds = route_demand(P, tn, guides, ndr)
        for (t0, t1), v in sorted(dem.items()):
            band = [k for k in range(n) if t0 - 1e-9 <= off + k * p <= t1 + 1e-9 and k not in pg and k not in die]
            take = set(_pick(band, v, pg | die, n))
            route += len(take)
            die |= take
    blocked = pg | die
    typ = [k for k in range(n) if k not in blocked]
    g = dict(schema=SCHEMA, type=tn, plan=P.name, layer=LAYER, pitch_um=p, offset_um=off, outline_um=[w, h],
             instances=instances(P, tn), n_tracks=n, pg_tracks=len(pg), die_reserve_tracks=len(die) - route,
             die_route_tracks=route, type_tracks=len(typ), free_frac=round(len(typ) / n, 4) if n else 0.0,
             cut_avail=ca, ndr=ndr, route_kinds=kinds, guide_sha=guide_sha,
             die_runs=_runs(blocked), type_runs=_runs(typ))
    g["sha"] = hashlib.sha256(json.dumps({k: v for k, v in g.items() if k != "sha"}, sort_keys=True).encode()).hexdigest()[:16]
    return g


def obstruction_tcl(g):
    """pdn.tcl lines: obstruct every run of die tracks on M8 (wire extent of the run)."""
    w = g["outline_um"][0]
    p, off = g["pitch_um"], g["offset_um"]
    L = [f"# M8 GRANT {g['sha']} (tools/die_plan/m8_grant.py): the type routes M8 only on its {g['type_tracks']} of "
         f"{g['n_tracks']} tracks; die tracks (PG {g['pg_tracks']}, die reserve {g['die_reserve_tracks']}, die route "
         f"{g['die_route_tracks']}) are obstructed",
         "set blk [ord::get_db_block]", "set dbu [$blk getDbUnitsPerMicron]",
         f"set lay [[ord::get_db_tech] findLayer {g['layer']}]"]
    h = g["outline_um"][1]
    for k0, k1 in g["die_runs"]:
        y0 = max(0.0, off + k0 * p - WIRE_W / 2)
        y1 = min(h, off + k1 * p + WIRE_W / 2)
        L.append("odb::dbObstruction_create $blk $lay " + " ".join(
            f"[expr {{round({v:.4f}*$dbu)}}]" for v in (0.0, y0, w, y1)))
    return "\n".join(L) + "\n"


def abstract_obs_rects(g):
    w, h = g["outline_um"]
    p, off = g["pitch_um"], g["offset_um"]
    return [(0.0, max(0.0, off + k0 * p - WIRE_W / 2), w, min(h, off + k1 * p + WIRE_W / 2)) for k0, k1 in g["type_runs"]]


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
    if tn not in P.types:
        return [f"type {tn} no longer in plan {P.name}"]
    if list(P.types[tn]["outline_um"]) != list(g["outline_um"]):
        return [f"type {tn} outline changed {g['outline_um']} -> {P.types[tn]['outline_um']}"]
    new = grant(P, tn, guides, ndr or g.get("ndr", "4w"))
    typ = {k for a, b in g["type_runs"] for k in range(a, b + 1)}
    die = {k for a, b in new["die_runs"] for k in range(a, b + 1)}
    bad = sorted(typ & die)
    return [f"type {tn}: die M8 track {k} (y {g['offset_um'] + k * g['pitch_um']:.3f}) is a granted type track"
            for k in bad]


def grant_config(P):
    """layer_budget.type_m8_grant normalised: None (off) or dict(enable, types, guide, ndr).  OT_GEN_M8_GRANT=1 at
    generation turns it on for A/B kits without a plan event."""
    c = P.layer_budget.get("type_m8_grant")
    if c is None and os.environ.get("OT_GEN_M8_GRANT") == "1":
        c = True
    if c is None or c is False:
        return None
    if c is True:
        c = {}
    c = dict(enable=c.get("enable", True), types=c.get("types"), guide=c.get("guide"), ndr=c.get("ndr", "4w"))
    return c if c["enable"] else None


def kit_grant(P, tn):
    """the grant a type kit carries, or None (grant off, type not selected, ceiling already >= M8, not placed)."""
    c = grant_config(P)
    if c is None or (c["types"] is not None and tn not in c["types"]):
        return None
    if int(P.layer_budget["partition_signal_max"][1:]) >= int(LAYER[1:]) or not instances(P, tn):
        return None
    G, gsha = None, None
    if c["guide"]:
        gp = Path(c["guide"])
        if not gp.is_absolute() and P.path:
            gp = Path(P.path).resolve().parent / gp
        if not gp.is_file():
            raise FileNotFoundError(f"type {tn}: layer_budget.type_m8_grant.guide {gp} missing")
        G, gsha = _guides(str(gp))
    return grant(P, tn, G, c["ndr"], gsha)


def check_lock(P, R, lock, guide=None):
    """G0 hook (check.py --m8-grant-lock): ERROR [m8_grant_lock] per die track on a signed type's granted track."""
    files = sorted(Path(lock).glob("*.json")) if Path(lock).is_dir() else [Path(lock)]
    G, _ = _guides(guide)
    n = bad = 0
    for f in files:
        g = json.loads(f.read_text())
        if g.get("schema") != SCHEMA:
            continue
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
        g = json.loads(Path(a.grant).read_text())
        for f in a.lef:
            Path(f).write_text(fix_abstract_lef(Path(f).read_text(), g))
            print(f"M8GRANT fixlef {f} {g['sha']} type_runs {len(g['type_runs'])}")
        return 0
    import schema as S
    P = S.Plan(S.load(a.plan), Path(a.plan))
    G, gsha = _guides(a.guide)
    if a.cmd == "lock":
        bad = []
        for f in a.grant:
            bad += lock_check(json.loads(Path(f).read_text()), P, G)
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
