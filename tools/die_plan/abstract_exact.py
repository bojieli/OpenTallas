#!/usr/bin/env python3
"""ABSTRACT-EXACT (11-25, COORD; generalises KV-PC-ABSTRACT kvpc_exact_m45 to every die): routing-layer OBS of a hard-core
view from the REAL metal of its signed routed DB instead of one blanket rect per layer.

Cause (census lanes/ABSTRACT-CENSUS.tsv, 190 of 282 hard-core views on S81/HEAD/QC/KV): ORFS do-generate_abstract
(scripts/generate_abstract.tcl: write_abstract_lef -bloat_occupied_layers) writes ONE OBS rect per occupied layer, so M4/M5
read 94-100 % blocked while the real metal there is 2-40 % (median M4 10-14 %, M5 22 %).  The parent router then has no
M4/M5 over any hard core and detours around it (GRT overflow in the kits that hold them).

Form (COORD guardrails 11-25): only routing layers M4-M6 whose OBS is BLANKET (>= 80 % of the macro) while the real metal
is < 40 % are replaced; M1-M3 stay blanket.  The replacement is the -bloat_factor 0 export of the SAME signed ODB, every
shape GROWN by max(min spacing, merge gap / 2) per side (gaps < 2 x track pitch close, so no unusable slivers) and clipped
to the macro outline, the union merged, and the zone within --pin-clear-um of every signal pin on that layer cut back so
pin access stays open.  PG pins stay PIN; PG strap metal is metal, so it stays OBS (grown).  PINs, SIZE, FOREIGN and every
other layer are byte-identical (abstract_detail check).

  python3 -I abstract_exact.py form --base signed.lef --detail exact_b0.lef --out new.lef [--receipt r.json] [--layers auto|M4,M5]
  python3 -I abstract_exact.py census --lef view.lef [--detail exact_b0.lef]      per-layer OBS % (and metal % with --detail)
  python3 -I abstract_exact.py tcl --odb 6_final.odb --out exact_b0.lef           OpenROAD Tcl of the exact export
PRECHECK: plan_gate_pre ABSTRACT-BLANKET-OBS (report-only WARN) calls findings(plan, tree) for every bound hard-core view.
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_detail as A  # noqa: E402
import kvpc_exact_m45 as K  # noqa: E402

ROUTING = ("M4", "M5", "M6")        # layers this form may replace (M1-M3 stay blanket, COORD guardrail 1)
# ASAP7 (asap7_tech_1x_201209.lef): track pitch / min spacing per routing layer, um
PITCH = {"M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}
MIN_SPACE = {"M4": 0.024, "M5": 0.024, "M6": 0.032, "M7": 0.032}
BLANKET_OBS_PCT = 80.0
SPARSE_METAL_PCT = 40.0
EXPECTED_PROBLEM = K.EXPECTED_PROBLEM
_RECT = re.compile(r"^\s*RECT\s+(?:MASK\s+\d+\s+)?(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;")


def _nm(v):
    return int(round(float(v) * 1000))


def layer_rects(path, want_pins=True):
    """-> (W, H, {layer: [obs rect nm]}, {layer: [pin rect nm]} (all pins, PG included)); streams big files"""
    W = H = None
    obs, pins, in_obs, in_pin, lay = {}, {}, False, False, None
    with open(path) as fh:
        for ln in fh:
            s = ln.strip()
            if W is None:
                m = re.match(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", s)
                if m:
                    W, H = float(m.group(1)), float(m.group(2))
            if s == "OBS":
                in_obs, in_pin, lay = True, False, None
                continue
            if s.startswith("PIN "):
                in_pin, lay = True, None
                continue
            if in_obs and s == "END":
                in_obs = False
                continue
            m = re.match(r"LAYER\s+(\S+)", s)
            if m:
                lay = m.group(1)
                continue
            m = _RECT.match(ln)
            if m and lay:
                r = tuple(_nm(v) for v in m.groups())
                if in_obs:
                    obs.setdefault(lay, []).append(r)
                elif in_pin and want_pins:
                    pins.setdefault(lay, []).append(r)
    return W, H, obs, pins


def union_area_um2(rects):
    return K._area(K.union_minus(rects, []))


def coverage(path, layers=ROUTING, with_pins=False):
    """{layer: (pct of macro area, rect count)} of OBS (plus pins when with_pins: the real-metal figure of an exact export)"""
    W, H, obs, pins = layer_rects(path, want_pins=with_pins)
    out = {}
    for L in layers:
        rs = obs.get(L, []) + (pins.get(L, []) if with_pins else [])
        out[L] = (round(100.0 * union_area_um2(rs) / (W * H), 2) if rs else 0.0, len(obs.get(L, [])))
    return out


def blanket_layers(base, detail=None, layers=ROUTING):
    """layers of `base` whose OBS covers >= BLANKET_OBS_PCT of the macro; with an exact `detail`, only those whose real metal
    is < SPARSE_METAL_PCT (the census rule).  -> {layer: {obs_pct, rects, metal_pct}}"""
    cov = coverage(base, layers)
    met = coverage(detail, layers, with_pins=True) if detail else {}
    out = {}
    for L in layers:
        o, n = cov[L]
        if o < BLANKET_OBS_PCT:
            continue
        m = met.get(L, (None,))[0]
        if m is not None and m >= SPARSE_METAL_PCT:
            continue
        out[L] = dict(obs_pct=o, rects=n, metal_pct=m)
    return out


MIN_WIDTH = {"M4": 0.024, "M5": 0.024, "M6": 0.032, "M7": 0.032}

# STALE-OBS 11-25 (hd_host_e merged-GDS DRC): a bound view whose OBS on a NON-blanket layer came from another build of the
# core hides real metal of the signed DB (he_epc: bound M6 OBS 20397 rects from another layout; a 78 um M6 signal wire of
# the signed DB 16 nm from the parent VSS strap was in no OBS -> 232 M6/M7 PG + 61 signal NEW markers).  A layer is STALE
# when real metal of the exact export of the signed ODB lies outside the base OBS+PIN; it is replaced like a blanket layer.
# M7 is included: the parent routes and grids M7 over cores (COORD 05:4x named M5-M7); M1-M3 stay blanket (guardrail 1).
STALE_LAYERS = ROUTING + ("M7",)
STALE_UNCOVERED_PCT = 0.5     # % of exact metal rects that touch no base OBS/PIN rect


def _binned(rects, cell=2000):
    idx = {}
    for i, r in enumerate(rects):
        for bx in range(r[0] // cell, r[2] // cell + 1):
            for by in range(r[1] // cell, r[3] // cell + 1):
                idx.setdefault((bx, by), []).append(i)
    return idx, cell


def uncovered(have, metal):
    """rects of `metal` that touch no rect of `have` (nm tuples)"""
    idx, cell = _binned(have)
    miss = []
    for r in metal:
        cand = set()
        for bx in range(r[0] // cell, r[2] // cell + 1):
            for by in range(r[1] // cell, r[3] // cell + 1):
                cand.update(idx.get((bx, by), ()))
        if not any(have[i][0] < r[2] and have[i][2] > r[0] and have[i][1] < r[3] and have[i][3] > r[1] for i in cand):
            miss.append(r)
    return miss


def stale_layers(base, detail, layers=STALE_LAYERS, pct=STALE_UNCOVERED_PCT):
    """layers where > pct % of the exact metal rects (detail OBS+PIN) touch no base OBS/PIN rect
    -> {layer: {uncovered, metal_rects, uncovered_pct, example_nm}}"""
    _, _, bo, bp = layer_rects(base)
    _, _, do, dp = layer_rects(detail)
    out = {}
    for L in layers:
        metal = do.get(L, []) + dp.get(L, [])
        if not metal:
            continue
        miss = uncovered(bo.get(L, []) + bp.get(L, []), metal)
        up = 100.0 * len(miss) / len(metal)
        if up > pct:
            out[L] = dict(uncovered=len(miss), metal_rects=len(metal), uncovered_pct=round(up, 2), example_nm=list(miss[0]))
    return out


# PIN-EOL 11-25 (COORD, S81 col_h9_r2: 358 constant M5 Lef58EolKeepOut DRT marks = 179 pins of dsfd_qbank_S/N, dsfd_node_NNfd,
# n25): a signal pin sliver whose own wire continues as OBS (or OBS grown up to it) puts an OBS line end inside the EOL
# keep-out of the pin end, which DRT can never clear.  v4: the pin's own same-layer wire is merged into the pin shape
# (abstract_detail.merge_pin_wires, exact metal only), and the grown OBS is cut back EOL_CLEAR from every signal pin shape;
# real foreign metal inside that band stays OBS at min spacing (never exposed).  ASAP7 LEF58_EOLKEEPOUT forward extension
# M4/M5 0.048 (tech LEF), M6/M7 one pitch.
EOL_CLEAR = {"M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}


def _grow(rs, g, Wn, Hn):
    return [(max(0, r[0] - g), max(0, r[1] - g), min(Wn, r[2] + g), min(Hn, r[3] + g)) for r in rs]


def pin_eol_findings(path, layers=STALE_LAYERS):
    """signal pin shapes whose own-wire OBS stub ends less than EOL_CLEAR past the pin line end, or with a separate OBS rect
    inside EOL_CLEAR beyond a line end (the DRT Lef58EolKeepOut class; a long own wire past the pin is fine)
    -> {layer: {"pins": n pin names, "shapes": n, "example": [pin, rect nm, obs rect nm]}}"""
    lines, _, obs, _, (W, H) = K._parse(Path(path).read_text())
    big = W * H * 1e6 / 2           # a blanket rect (> half the macro) is the blanket form, not a stub
    obs = {L: [q for q in rs if (q[2] - q[0]) * (q[3] - q[1]) <= big] for L, rs in obs.items()}
    names, cur, sig, lay, shapes = {}, None, False, None, []
    for ln in lines:
        s = ln.strip()
        if s == "OBS":
            break
        m = re.match(r"PIN\s+(\S+)", s)
        if m:
            cur, sig = m.group(1), False
        elif s.startswith("USE "):
            sig = s.rstrip(" ;").split()[1] == "SIGNAL"
        m = re.match(r"LAYER\s+(\w+)", s)
        if m:
            lay = m.group(1)
        m = _RECT.match(ln)
        if m and cur and sig and lay in layers:
            shapes.append((cur, lay, tuple(_nm(v) for v in m.groups())))
    out = {}
    idx = {L: _binned(obs.get(L, [])) for L in layers}
    for pin, L, r in shapes:
        e = _nm(EOL_CLEAR[L])
        horiz = (r[2] - r[0]) >= (r[3] - r[1])
        # touching box, plus the two line-end extension boxes
        zones = [r]
        if horiz:
            zones += [(r[0] - e, r[1], r[0], r[3]), (r[2], r[1], r[2] + e, r[3])]
        else:
            zones += [(r[0], r[1] - e, r[2], r[1]), (r[0], r[3], r[2], r[3] + e)]
        ix, cell = idx[L]
        rs = obs.get(L, [])
        cand = set()
        for z in zones:
            for bx in range(z[0] // cell, z[2] // cell + 1):
                for by in range(z[1] // cell, z[3] // cell + 1):
                    cand.update(ix.get((bx, by), ()))
        a0, a1 = (0, 2) if horiz else (1, 3)          # long axis
        n0, n1 = (1, 3) if horiz else (0, 2)          # narrow axis
        hit, ext = None, {0: 0, 1: 0}
        for i in cand:
            q = rs[i]
            touch = q[0] <= r[2] and q[2] >= r[0] and q[1] <= r[3] and q[3] >= r[1]
            if touch:
                if q[n0] < r[n1] and q[n1] > r[n0]:   # own wire continuing along the pin's track
                    ext[0] = max(ext[0], r[a0] - q[a0])
                    ext[1] = max(ext[1], q[a1] - r[a1])
                continue
            for z in zones[1:]:                       # foreign / separate OBS inside the line-end keep-out
                if q[0] < z[2] and q[2] > z[0] and q[1] < z[3] and q[3] > z[1]:
                    hit = q
        # an own-wire OBS stub that ends less than the keep-out past the pin end (col_h9_r2: pin to 0.084, OBS to 0.131)
        for end in (0, 1):
            if 0 < ext[end] < e and hit is None:
                hit = ["stub", end, ext[end]]
        if hit:
            d = out.setdefault(L, {"pins": set(), "shapes": 0, "example": [pin, list(r), list(hit)]})
            d["pins"].add(pin)
            d["shapes"] += 1
    return {L: dict(pins=len(d["pins"]), shapes=d["shapes"], example=d["example"]) for L, d in out.items()}


def regrow(lef_in, lef_out, layers, extra=None):
    """v3 (Fable 11-25, = KV-PC-ABSTRACT v3): grow each OBS rect of `layers` by max(min spacing, pitch) (= merge gap 2 x pitch / 2),
    clip to the outline, merge, cut ONLY each signal pin's own shape (foreign metal and its spacing stay OBS), regrow slivers
    below the layer min width in place (never over a pin, never outside the macro) -> lef_out; -> per-layer stats"""
    text = Path(lef_in).read_text()
    lines, obs_start, obs, sig_pins, (W, H) = K._parse(text)
    Wn, Hn = _nm(W), _nm(H)
    keep, lay, end = lines[:obs_start + 1], None, None
    for j in range(obs_start + 1, len(lines)):
        s = lines[j].strip()
        m = re.match(r"LAYER\s+(\w+)", s)
        if m:
            lay = m.group(1)
        if s == "END" and lines[j].startswith("  END"):
            end = j
            break
        if lay in layers:
            continue
        keep.append(lines[j])
    blocks, stats = [], {}
    for L in layers:
        g = _nm(max(MIN_SPACE.get(L, 0.024), PITCH.get(L, 0.048)))
        old = obs.get(L, []) + list((extra or {}).get(L, []))
        grown = [(max(0, r[0] - g), max(0, r[1] - g), min(Wn, r[2] + g), min(Hn, r[3] + g)) for r in old]
        clear = list(sig_pins.get(L, []))
        # PIN-EOL: grown OBS stops EOL_CLEAR short of every signal pin shape; real foreign metal inside that band stays OBS
        # at its exact (signed, DRC-clean) geometry: never exposed, never grown into the pin's line-end keep-out
        zone = _grow(clear, _nm(EOL_CLEAR.get(L, 0.048)), Wn, Hn)
        real = list(old)
        # slivers regrow only outside the keep-out band; one that cannot grow is dropped, and the exact foreign metal is put
        # back afterwards so a dropped piece never exposes real metal (overlapping OBS rects are fine in a LEF)
        res, sl = K.fix_slivers(K.union_minus(K.union_minus(grown, zone) + real, clear), zone, _nm(MIN_WIDTH.get(L, 0.024)), (0, 0, Wn, Hn))
        res = sorted(set(res) | {r for r in real if not any(c[0] <= r[0] and c[1] <= r[1] and c[2] >= r[2] and c[3] >= r[3]
                                                            for c in clear)})
        if res:
            blocks.append(f"    LAYER {L} ;")
            blocks += [f"     RECT  {a / 1000:.3f} {b / 1000:.3f} {c / 1000:.3f} {d / 1000:.3f} ;" for a, b, c, d in res]
        stats[L] = dict(grow_um=g / 1000, exact_rects=len(old), rects=len(res),
                        exact_area_pct=round(100 * K._area(K.union_minus(old, [])) / (W * H), 2),
                        blocked_pct=round(100 * K._area(K.union_minus(res, [])) / (W * H), 2), **sl)
    Path(lef_out).write_text("\n".join(keep + blocks + lines[end:]))
    return stats


def form(base, detail, out, receipt=None, layers="auto"):
    """splice exact OBS of the blanket or stale routing layers (M4-M7), regrow, check -> rc (0 ok, 1 nothing to do, 2 refused)"""
    base, detail, out = Path(base), Path(detail), Path(out)
    st = {}
    if layers == "auto":
        bl = blanket_layers(base, detail)
        st = stale_layers(base, detail)
        st.update({L: dict(pin_eol=v) for L, v in pin_eol_findings(base).items() if L not in st})   # PIN-EOL in the bound view
        sel = [L for L in STALE_LAYERS if L in bl or L in st]
    else:
        bl = {}
        sel = [L for L in layers.split(",") if L]
    rec = dict(schema="opentallas.abstract_exact.v4", base=str(base), base_sha256=A._sha(str(base)), detail=str(detail),
               detail_sha256=A._sha(str(detail)), layers=sel, blanket=bl, stale=st, obs_before=coverage(base, STALE_LAYERS))
    if not sel:
        rec["verdict"] = "NOTHING-TO-DO"
        if receipt:
            Path(receipt).write_text(json.dumps(rec, indent=1))
        return 1
    tmp = out.with_name(out.name + ".exact.tmp")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = A.main(["splice", "--base", str(base), "--detail", str(detail), "--layers", ",".join(sel), "--bloat-factor", "0",
                     "--out", str(tmp)])
    sp = json.loads(buf.getvalue() or "{}")
    problems = [p for p in sp.get("problems", []) if p != EXPECTED_PROBLEM]
    rec["splice"] = {k: sp.get(k) for k in ("rects", "pin_clear", "pg_pin_layers", "problems")}
    if rc not in (0, 1) or problems:
        rec["verdict"] = "REFUSED"
        rec["problems"] = problems or ["splice rc %s" % rc]
        if tmp.exists():
            tmp.unlink()
        if receipt:
            Path(receipt).write_text(json.dumps(rec, indent=1))
        return 2
    # PIN-EOL: the pin's own same-layer wire (exact metal, touching the pin) becomes pin shape before the OBS is grown
    with open(tmp) as fh:
        lns = fh.readlines()
    lns, rec["pin_wire_merge"] = A.merge_pin_wires(lns, set(sel))
    tmp.write_text("".join(lns))
    # PIN-METAL 11-25: exact BTerm metal the bound pins do not cover (a bound view whose pin shapes differ from the signed DB,
    # e.g. LL*/hcpost/elemA/B) is real metal of that net: it becomes OBS so no foreign wire is routed onto it
    _, _, _, xp0 = layer_rects(detail)
    _, _, _, bp0 = layer_rects(tmp)
    extra = {L: K.union_minus(xp0.get(L, []), bp0.get(L, [])) for L in sel}
    rec["pin_metal_to_obs"] = {L: len(v) for L, v in extra.items() if v}
    rec["regrow"] = regrow(tmp, out, sel, extra)
    tmp.unlink()
    # the check compares against the base with the same merged pin rects (only RECT lines added inside PIN sections)
    bh, bb, bt = A._split(base.read_text().splitlines(keepends=True))
    nh, _, _ = A._split(Path(out).read_text().splitlines(keepends=True))
    added = list(nh)
    for ln in bh:
        if ln in added:
            added.remove(ln)
    pins_ok = all(_RECT.match(ln) for ln in added) and [ln for ln in nh if not _RECT.match(ln)] == \
        [ln for ln in bh if not _RECT.match(ln)]
    base_pm = out.with_name(out.name + ".basepm.tmp")
    base_pm.write_text("".join(nh + (bb or []) + bt))
    with contextlib.redirect_stdout(io.StringIO()):
        crc = A.main(["check", "--base", str(base_pm), "--new", str(out), "--layers", ",".join(sel)])
    base_pm.unlink()
    if not pins_ok:
        crc = 2
    # every exact metal rect of a replaced layer is still OBS or PIN (the keep-out cut and sliver drops never expose metal)
    _, _, xo, xp = layer_rects(detail)
    _, _, no, np_ = layer_rects(out)
    exposed = {L: round(K._area(K.union_minus(xo.get(L, []) + xp.get(L, []), no.get(L, []) + np_.get(L, []))), 6)
               for L in sel}
    rec["real_metal_exposed_um2"] = {L: v for L, v in exposed.items() if v}
    if rec["real_metal_exposed_um2"]:
        crc = 2
    rec["pin_rects_added"] = len(added)
    acc = A.access_report(Path(out).read_text().split("\n"))
    rec.update(check_ok=crc == 0, obs_after=coverage(out, STALE_LAYERS), lef_bytes_before=base.stat().st_size,
               lef_bytes_after=out.stat().st_size, obs_rects_before=sum(1 for ln in open(base) if _RECT.match(ln)),
               obs_rects_after=sum(1 for ln in open(out) if _RECT.match(ln)),
               pins_without_access=sorted(p for p, e in acc["pins"].items() if not e["ok"]),
               pin_eol=pin_eol_findings(out),
               out_sha256=A._sha(str(out)), verdict="OK" if crc == 0 else "CHECK-FAIL")
    if receipt:
        Path(receipt).write_text(json.dumps(rec, indent=1))
    return 0 if crc == 0 else 2


# --------------------------------------------------------------------------- PRECHECK ABSTRACT-BLANKET-OBS (report-only)
LEVEL = "WARN"          # r703: a new check is report-only until COORD rules otherwise


def _hard_core_lefs(raw):
    seen = {}

    def walk(o, t):
        if isinstance(o, dict):
            lef = o.get("lef")
            if isinstance(lef, str) and lef.endswith(".lef"):
                seen.setdefault(lef, set()).add(t)
            for k, v in o.items():
                if k != "lef":
                    walk(v, t)
        elif isinstance(o, list):
            for v in o:
                walk(v, t)
    for t, d in (raw.get("partition_types") or {}).items():
        walk((d or {}).get("hard_cores"), t)
    return seen


def findings(raw, tree, max_list=40):
    """one WARN line per bound hard-core view whose M4-M6 OBS is BLANKET (>= 80 % with <= 4 rects: the
    -bloat_occupied_layers signature), plus one LIST line.  Generated memory macros are skipped.  Never a FAIL."""
    die = raw.get("die", "?")
    out, n, flagged = [], 0, 0
    for lef, types in sorted(_hard_core_lefs(raw).items()):
        if "asap7_memory_macros" in lef or os.path.basename(lef).endswith("_phy.lef"):
            continue
        p = lef if os.path.isabs(lef) else os.path.join(tree or ".", lef)
        if not os.path.isfile(p):
            continue
        n += 1
        try:
            cov = coverage(p)
        except Exception as e:  # noqa: BLE001
            out.append(f"{LEVEL} ABSTRACT-BLANKET-OBS {die}/{os.path.basename(lef)}: not read ({type(e).__name__})")
            continue
        bl = {L: c for L, c in cov.items() if c[0] >= BLANKET_OBS_PCT and c[1] <= 4}
        if not bl:
            continue
        flagged += 1
        if flagged <= max_list:
            ly = ", ".join(f"{L} {c[0]:.0f}%/{c[1]} rect" for L, c in sorted(bl.items()))
            out.append(f"{LEVEL} ABSTRACT-BLANKET-OBS {die}/{os.path.basename(lef)[:-4]}: {ly} (one-rect blanket OBS, "
                       f"write_abstract_lef -bloat_occupied_layers; {len(types)} type(s) e.g. {sorted(types)[0]}); "
                       f"report-only: re-export with tools/die_plan/abstract_exact.py form (exact routing-layer OBS)")
    out.append(f"LIST ABSTRACT-BLANKET-OBS die {die} hard-core views {n} blanket {flagged}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("form")
    f.add_argument("--base", required=True)
    f.add_argument("--detail", required=True)
    f.add_argument("--out", required=True)
    f.add_argument("--receipt")
    f.add_argument("--layers", default="auto")
    c = sub.add_parser("census")
    c.add_argument("--lef", required=True)
    c.add_argument("--detail")
    e = sub.add_parser("pin-eol", help="census: signal pins with OBS inside the line-end keep-out (Lef58EolKeepOut class)")
    e.add_argument("lefs", nargs="+")
    t = sub.add_parser("tcl")
    t.add_argument("--odb", required=True)
    t.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "form":
        return form(a.base, a.detail, a.out, a.receipt, a.layers)
    if a.cmd == "pin-eol":
        for f in a.lefs:
            try:
                print(json.dumps(dict(lef=f, sha256=A._sha(f), pin_eol=pin_eol_findings(f))))
            except Exception as ex:          # a census row per file, never a crash
                print(json.dumps(dict(lef=f, error=repr(ex))))
        return 0
    if a.cmd == "census":
        res = dict(obs=coverage(a.lef, ("M1", "M2", "M3") + ROUTING + ("M7",)))
        if a.detail:
            res["metal"] = coverage(a.detail, ("M1", "M2", "M3") + ROUTING + ("M7",), with_pins=True)
            res["blanket"] = blanket_layers(a.lef, a.detail)
        print(json.dumps(res))
        return 0
    print("read_db %s\nwrite_abstract_lef -bloat_factor 0 %s" % (a.odb, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
