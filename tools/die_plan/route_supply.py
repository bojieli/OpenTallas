#!/usr/bin/env python3
"""PLAN-ROUTE-1: plan-time routing supply-versus-demand check per partition type (ADVISORY, never a gate).

    route_supply.py PLAN [--die NAME] [--repo ROOT] [--types T1,T2|--match RE] [--out DIR] [--bin 10.8]
                         [--derate M6=0.31,...] [--core-conns PATH] [--calib JSON]

OWNER 11-03 "targets, not gates": the check only reports; it never fails kit generation.  Exit code is 0 unless
the plan cannot be read.  Its rows feed plan events (wider street, channel between macro rows, reshaped outline,
landing-ring form, layer reassignment).

WHAT IT READS (all from the plan and files the plan names; no kit, no netlist):
  type outline_um; hard_cores (origin_um, outline_um, orient, lef, pins_file); buses (face, window_um, width);
  ft_slots (in/out face, width, regs_um, bit_sites_um); internal_stations (from_um, regs_um, to_um, bits);
  clock.landing_contract.bands (rect_um, width, padded_data_storage_flops); core_conns.json(.gz) from the plan dir, the
  --ref-dirs (newest first) and <die>/, merged per type (first file listing a type wins).

SUPPLY (tracks per bin per layer, signal layers M2-M7, METHODOLOGY 12.1a: tiles never use M8/M9):
  tracks_L(bin) = bin_um / pitch_L x (1 - derate_L) x (1 - obs_L(bin))
  pitch: effective (drawn minus PG/rail blockage), MEASURED from GRT-0053 Original Resources of macro-free kits:
         M2 0.0419, M3 0.0371, M4 0.048, M5 0.0503, M6 0.074, M7 0.0681 um; M2/M4/M6 H, M3/M5/M7 V (ASAP7).
  derate_L = the flow's own GRT reduction, MEASURED from the kit GRT-0053 table (S81 leaf t15 a8: M2 29.14, M3 25.73,
           M4 25.68, M5 25.99, M6 31.18, M7 32.39 %); --derate overrides (e.g. M7=0.8787 reproduces the old QC
           conservative-kit cut).
  obs_L(bin) = share of the bin under a hard core whose LEF has OBS on layer L (LEF OBS rect area / macro area,
           capped at 1).  A LEF that blocks every layer M1..M7 with one full rect is a plan TEMPLATE (S81 *_tpl.lef);
           the built core view obstructs only up to its ceiling, so OBS is capped at --core-ceiling (default M5,
           METHODOLOGY 12.1a new-tile default; measured: every kit macro LEF in S81 leaf t15 a8 obstructs M1-M5,
           the 512x128 SRAM M1-M4).
  Over a macro that blocks M1-M5 the only horizontal layer is M6 and the only vertical one is M7.

DEMAND (track-um per bin per direction, RUDY: each net puts its bbox half-perimeter wire uniformly over its bbox;
the horizontal share is w / (w h) per um^2, the vertical one h / (w h)):
  core nets      one 2-pin net per core pin bit: from the pin (pins_file, orient applied) to the partner the plan
                 names in core_conns.json (core:B -> the B pins whose bus names core:A, else B's pin centroid;
                 bus:X -> the type bus window; face:F -> the middle of face F).  Without core_conns the partner is
                 the pin-weighted centroid of all OTHER hard cores ("fallback", flagged in the row).
  bus / ft bits  every ft slot bit: face entry -> station sites -> exit, one net per hop; every internal_station
                 bit: from -> regs -> to.
  landing rings  every clock.landing_contract band: the ring storage spreads over
                 A = max(band area, flops x ring_um2_per_flop) grown from the band away from its face; the ring
                 puts ring_tracks_per_bit x width tracks across every cut of that area in both directions
                 (calibrated on KV hgi_v3 u_cland_ft27: ~5,000 of 6,224 H tracks at x=120 for 1,056 bits).
  glue pins      a core pin whose bus core_conns does not route to another core / type bus goes to the type's glue
                 logic: a local escape net glue_um out of the nearest core face.
  cell wiring    background: cell_fill x supply on M2-M5 of every bin that is not under a macro.
RATIO: demand / supply per direction, after a box filter of --window bins (the router detours locally), by region
  class: core (bin centre under a hard core), mem (under an SRAM/ROM macro, reported separately), street (between two hard cores within --street-um on opposite sides),
  face (within --face-um of the outline), open.  Per type the worst region gives: ratio, direction, layer (the layer
  that carries most of the supply there), hot bins (> 1), and the cheapest plan-level fix class.
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

import numpy as np

SCHEMA = "opentallas.route_supply.v1"
LAYERS = ["M2", "M3", "M4", "M5", "M6", "M7"]
# OpenROAD GRT macro-obstruction rules (build 26Q3-1510-g6cb3f2b704 in openroad/orfs:asap7lock, src/grt/src/
# GlobalRouter.cpp; PLAN-ROUTE-1 11-10, verified on the DIE-QC-97 NK H-channel arms A/B/C):
#  * transition layers (default via = first tech via per bottom layer, no OR_DEFAULT in ASAP7; via enclosure on the
#    layer / track pitch > 0.8): VIA23 0.028/0.039 no; VIA34 .034/.036, VIA45 .046/.048, VIA56 .054/.048,
#    VIA67 .054/.064, VIA78 .054/.064 yes -> M3..M7 lose 50% capacity over a macro OBS on the layer below
#    (adjustTransitionLayers, l.2158; adjustTileSet floor(cap*0.5), l.2177)
#  * per macro, the max routing layer (M7) inherits every OBS of the layer below (layerIsBlocked l.5513) and a layer
#    between two obstructed layers is blocked where they overlap (extendObstructions l.5557)
GRT_TRANSITION = ("M3", "M4", "M5", "M6", "M7")
GRT_MAX_LAYER = "M7"
GRT_GCELL_UM = 0.57    # MEASURED gcell of the ASAP7 tile runs (GRT-PATCH-1 11-10, t15: perimeter ring 2 x 0.57 um)
# GRT-CALIB-1 11-11 (COORD ruling "GRT calibration"): calibrated feasibility model, opt-in (--calib-1111), checked
# against 925 completed kit GRTs of 11-07..11-12 (230 types with a model row). The defaults stay byte-identical.
#  (1) verdict FAIL when the worst region p99 (any track region, dens_A excluded) > CALIB_FAIL_P99, or the soft-cell
#      density dens_A >= FLAG_AT["dens"]: the measured GRT fail detector (p99 > 1: recall 78%, precision 75%);
#  (2) over a hard core (kind core) the only signal supply is M6 (H) / M7 (V): M2-M5 are blocked over the whole
#      macro area whatever share the view's OBS rects cover (--over-macro-m67), with the transition halving of the
#      active --grt-halving mode (edge_outline for new builds under --calib-1111);
#  (3) the full-line cut is not a feasibility input (check.py --full-cut band keeps it as a die-band WARN).
CALIB_FAIL_P99 = 1.0
CALIB_HALVING = "edge_outline"
# GRT-CALIB-2 11-12: per-macro hot spot (--macro-hotspot local, region mhot_H/V). Calibrated on the same corpus:
# the 6 S81 macro-dense misses of --calib-1111 (col_h10_r2 x3, col_h9_r0_p4 x2, dsdv_slice_lepw_mus_LP__t2) read
# 0.93-1.10 as the ratio of windowed sums (demand/supply) over the macro; every GRT-PASS type that --calib-1111 calls
# OK reads <= 0.927. FAIL above 1.0 (demand > supply, the same physical line as CALIB_FAIL_P99, not a fitted value):
# it catches col_h10_r2 x3 (missed 11 -> 8, 0 new false alarms). 0.93 would catch all 6 but has no margin.
CALIB_HOTSPOT_FAIL = 1.0



def station_bits(t, s):
    """Bits carried by one internal_stations chain. An explicit "bits" wins. A face-bus chain (conn bus:X) without one
    carries the whole bus: the kit pads every bit of X through the chain's register sites (u_lpad_X.r[k][*]), and
    station_face_dedupe removes X as a separate face net, so falling back to 1 bit hid the bus from the model."""
    if s.get("bits") is not None:
        return s["bits"]
    cn = str(s.get("conn", ""))
    if cn.startswith("bus:"):
        name = cn[4:].split("|", 1)[0]
        for b in t.get("buses") or []:
            if isinstance(b, dict) and b.get("name") == name and b.get("width"):
                return int(b["width"])
    return 1

def grt_halving_weight(g, mrects, pins, k_gcells, gcell_um=GRT_GCELL_UM):
    """GRT-PATCH-1 'edge_outline' image (OT_GRT_TRANSITION_MODE=edge_outline, grtT3 sha256:2d12164ad3f6): a stock-halved
    tile stays halved only within K gcells of the macro INSTANCE bbox boundary or within K of a macro SIGNAL pin (PG
    excluded; pins_file pins are signal pins). Returns, per bin, the fraction of the macro area under it that is still halved (1 = stock
    image, everywhere under the OBS)."""
    # rim = bbox tiles first..first+K (GRT-PATCH-1: interior from first+K+1), the first tile ~half covered
    d = (k_gcells + 0.5) * gcell_um
    w = np.zeros((g.ny, g.nx))
    b = g.b
    for (x0, y0, x1, y1, h) in mrects:
        (c, _), = coverage(g, [(x0, y0, x1, y1, h)])
        ix0, iy0, ix1, iy1 = x0 + d, y0 + d, x1 - d, y1 - d
        inner = coverage(g, [(ix0, iy0, ix1, iy1, h)])[0][0] if ix1 > ix0 and iy1 > iy0 else np.zeros_like(c)
        band = c - inner
        if ix1 > ix0 and iy1 > iy0:
            for (_, px, py) in pins.get(h["inst"], []):
                if ix0 < px < ix1 and iy0 < py < iy1:      # interior pin: its own K-gcell square is halved
                    e = d                                # Chebyshev K around the pin's own tile (+ its half tile)
                    sq = coverage(g, [(max(px - e, ix0), max(py - e, iy0), min(px + e, ix1), min(py + e, iy1), h)])
                    band = band + sq[0][0]
        frac = np.where(c > 1e-9, np.clip(band / np.maximum(c, 1e-9), 0, 1), 0.0)
        w = np.maximum(w, frac)
    return w


def grt_halving_weight_obs(g, cov, mrects, pins, k_gcells, macro_obs, notes, gcell_um=None):
    """GRT-PATCH-1 'edge' image (OT_GRT_TRANSITION_MODE=edge): a stock-halved tile stays halved within K gcells
    (Chebyshev) of the union boundary of the layer-below macro OBS tiles, or within K of any macro pin (PG included)
    on L-1/L/L+1. The share comes from the view's OBS and pin shapes rasterised on the gcell grid (edge_share) and is
    spread evenly over the macro. A view without shapes (template, obs_max, ceiling) is one solid block: edge_outline
    with its signal pins (PG straps unknown, so this under-halves), noted."""
    out = {L: np.zeros((g.ny, g.nx)) for L in LAYERS}
    outline_w = None
    nfb = 0
    for (c, h), r in zip(cov, mrects):
        bd = macro_band(h["inst"], k_gcells, gcell_um)
        if bd is None:
            nfb += 1
            if outline_w is None:
                outline_w = grt_halving_weight(g, mrects, pins, k_gcells)
            for L in LAYERS:
                out[L] = np.maximum(out[L], np.where(c > 1e-9, outline_w, 0.0))
            continue
        for L in LAYERS:
            out[L] = np.maximum(out[L], np.where(c > 1e-9, bd.get(L, 0.0), 0.0))
    if nfb:
        notes.append(f"grt edge: {nfb} macro views without shapes taken as solid (= edge_outline)")
    return out


GRT_HALVING_MODES = ("full", "edge", "edge_outline", "none", "off")


def grt_halving_types(items):
    """['TYPE=MODE', ...] -> {TYPE: MODE} (GRT-PATCH-1 per-row arm); a bad item raises"""
    out = {}
    for it in items or []:
        t, sep, m = str(it).partition("=")
        if not sep or not t or m not in GRT_HALVING_MODES:
            raise ValueError(f"--grt-halving-type {it!r}: TYPE=MODE with MODE in {GRT_HALVING_MODES}")
        out[t] = m
    return out


def grt_macro_rules(obs):
    """macro OBS extension as findInstancesObstructions applies it (bottom-up, in place)."""
    for i in range(1, len(LAYERS) - 1):
        lo, mid, hi = LAYERS[i - 1], LAYERS[i], LAYERS[i + 1]
        obs[mid] = np.maximum(obs[mid], np.minimum(obs[lo], obs[hi]))
    top = GRT_MAX_LAYER
    below = LAYERS[LAYERS.index(top) - 1]
    obs[top] = np.maximum(obs[top], obs[below])
# Effective track pitch = drawn pitch after PG / rail blockage, MEASURED as the GRT-0053 "Original Resources" ratio
# to M4 on macro-free kits (S81 slice_station__t46 / t24 / t49, HEAD hd_spn, HBM q_spt1: identical to 3 digits),
# with M4 at its drawn 0.048 um (drawn: M2/M3 0.036, M4/M5 0.048, M6/M7 0.064).
PITCH = {"M2": 0.0419, "M3": 0.0371, "M4": 0.048, "M5": 0.0503, "M6": 0.074, "M7": 0.0681}
DIRN = {"M2": "H", "M3": "V", "M4": "H", "M5": "V", "M6": "H", "M7": "V"}
# MEASURED: GRT-0053 "Resource Reduction" of S81 ot_s81sl_leaf__t15 a8 (flow default; same on every S81 GRT table
# DIE-S81-85 read 11-10).
DERATE = {"M2": 0.2914, "M3": 0.2573, "M4": 0.2568, "M5": 0.2599, "M6": 0.3118, "M7": 0.3239}
DEFAULTS = dict(
    bin_um=10.8,               # master_plan.py corridor gcell
    window=3,                  # box filter, bins (router detour)
    core_ceiling="M5",         # 12.1a new-tile default ceiling; measured kit LEFs M1-M5
    cell_fill=0.25,            # background cell wiring share of M2-M5 outside macros (calibrated, see --calib)
    ring_tracks_per_bit=2.5,   # calibrated: signed S81 stations (1,104-bit rings) <= ~1; KV ft27 squeezed street measured 4.7
    ring_um2_per_flop=10.0,    # calibrated on signed stations; KV ft27 squeezed: ~232 x 104 um for 5,440 flops (4.4)
    street_um=60.0,
    face_um=21.6,
    hot=1.0,
    glue_um=21.6,
    cell_um2=0.1,              # mean placed std-cell area for the fill ESTIMATE (ASAP7, ~0.09-0.12 um2)
    detour_um=97.2,
    margin_bins=9,   # bins beside a macro run pooled with it = the detour window (97.2 um); 2 over-weighted V along hard-core columns
)
FIX = {
    ("core", "H"): "horizontal channel between hard-core rows (only M6 runs H over an M1-M5 hard core)",
    ("core", "V"): "layer reassignment / vertical channel (only M7 runs V over an M1-M5 hard core)",
    ("mem", "H"): "horizontal channel beside the SRAM/ROM macro column (macro blocks M1-M4/M5; M6 only H)",
    ("mem", "V"): "vertical channel beside the SRAM/ROM macros / layer reassignment",
    ("mstreet", "H"): "wider street / channel beside the SRAM/ROM macros",
    ("mstreet", "V"): "wider street / channel beside the SRAM/ROM macros",
    ("street", "H"): "wider street (H) between hard cores",
    ("street", "V"): "wider street (V) between hard cores",
    ("face", "H"): "landing ring form / spread face pins (reshape outline along the face)",
    ("face", "V"): "landing ring form / spread face pins (reshape outline along the face)",
    ("open", "H"): "narrower/reshaped outline or lower cell density (open-area demand)",
    ("open", "V"): "narrower/reshaped outline or lower cell density (open-area demand)",
    ("ring", "H"): "landing ring form (stacked / y-column ring, or split the landing)",
    ("ring", "V"): "landing ring form (stacked / y-column ring, or split the landing)",
    ("dens", "A"): "cell density: grow / reshape the outline or split the type (cells per soft um2 above the GRT-pass limit)",
}


# ----------------------------------------------------------------------------------------------------------- inputs
_LEF_CACHE = {}


def lef_obs(path):
    """{layer: covered fraction of the macro} from a LEF OBS section (M1..M9), or None if unreadable."""
    key = str(path)
    if key in _LEF_CACHE:
        return _LEF_CACHE[key]
    out = None
    try:
        txt = Path(path).read_text(errors="replace")
    except OSError:
        txt = None
    if txt is not None:
        out = {}
        m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt)
        area = float(m.group(1)) * float(m.group(2)) if m else None
        i = txt.find("\n  OBS")
        if i < 0:
            i = txt.find("OBS")
        sec = txt[i:txt.find("END", i + 4)] if i >= 0 else ""
        cur = None
        acc = defaultdict(float)
        for ln in sec.splitlines():
            mm = re.match(r"\s*LAYER\s+(\S+)", ln)
            if mm:
                cur = mm.group(1)
                continue
            mm = re.match(r"\s*RECT\s+(?:MASK\s+\d+\s+)?([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", ln)
            if mm and cur:
                x0, y0, x1, y1 = map(float, mm.groups())
                acc[cur] += abs(x1 - x0) * abs(y1 - y0)
        for L, a in acc.items():
            if re.fullmatch(r"M\d", L) and area:
                out[L] = min(1.0, a / area)
    _LEF_CACHE[key] = out
    return out


_EDGE_CACHE = {}
def _dilate(m, k):
    """Chebyshev dilation by k tiles (separable running max)."""
    out = m.copy()
    for _ in range(k):
        t = out.copy()
        t[1:, :] |= out[:-1, :]
        t[:-1, :] |= out[1:, :]
        out = t
    o2 = out.copy()
    for _ in range(k):
        t = o2.copy()
        t[:, 1:] |= o2[:, :-1]
        t[:, :-1] |= o2[:, 1:]
        o2 = t
    return o2


def lef_shapes(txt, macro=None):
    """(W, H, obs {layer: [rects]}, pins {layer: [(rect, is_pg)]}) of one MACRO."""
    if macro:
        m = re.search(r"MACRO\s+" + re.escape(macro) + r"\b(.*?)\nEND\s+" + re.escape(macro), txt, re.S)
        if m:
            txt = m.group(1)
    sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt)
    if not sz:
        return None
    W, H = float(sz.group(1)), float(sz.group(2))
    obs, pins = {}, {}
    rect = r"\s*RECT\s+(?:MASK\s+\d+\s+)?([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)"
    for pm in re.finditer(r"\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1", txt, re.S):
        body = pm.group(2)
        pg = bool(re.search(r"USE\s+(POWER|GROUND)", body))
        cur = None
        for ln in body.splitlines():
            mm = re.match(r"\s*LAYER\s+(\S+)", ln)
            if mm:
                cur = mm.group(1)
                continue
            mm = re.match(rect, ln)
            if mm and cur:
                pins.setdefault(cur, []).append((tuple(map(float, mm.groups())), pg))
    i = txt.find("\n  OBS")
    if i < 0:
        i = txt.find("OBS")
    if i >= 0:
        cur = None
        for ln in txt[i:].splitlines():
            mm = re.match(r"\s*LAYER\s+(\S+)", ln)
            if mm:
                cur = mm.group(1)
                continue
            mm = re.match(rect, ln)
            if mm and cur:
                obs.setdefault(cur, []).append(tuple(map(float, mm.groups())))
            if re.match(r"\s*END\s*$", ln):
                break
    return W, H, obs, pins


def edge_share(shapes, ks, g, layers=("M2", "M3", "M4", "M5", "M6", "M7")):
    """{K: {B: share}}: of the gcell tiles under the layer-B macro OBS (B = the layer below a transition layer L),
    the share still halved by GRT-PATCH-1 'edge' (OT_GRT_TRANSITION_MODE=edge): within K tiles (Chebyshev) of the
    union boundary of the B OBS tiles, or within K of any macro pin (PG included) on B, L or L+1."""
    W, H, obs, pins = shapes
    nx, ny = max(1, int(np.ceil(W / g))), max(1, int(np.ceil(H / g)))

    def raster(rs):
        m = np.zeros((ny, nx), bool)
        for (x0, y0, x1, y1) in rs:
            a, b = sorted((x0, x1)), sorted((y0, y1))
            i0, i1 = max(0, int(a[0] // g)), min(nx, int(np.ceil(a[1] / g)))
            j0, j1 = max(0, int(b[0] // g)), min(ny, int(np.ceil(b[1] / g)))
            if i1 > i0 and j1 > j0:
                m[j0:j1, i0:i1] = True
        return m

    names = ["M1"] + list(layers) + ["M8"]
    out = {str(k): {} for k in ks}
    for B in layers[:-1]:
        ob = raster(obs.get(B, []))
        n = ob.sum()
        if not n:
            continue
        L = names[names.index(B) + 1]
        Lp = names[names.index(B) + 2]
        pm = raster([r for Ly in (B, L, Lp) for (r, _) in pins.get(Ly, [])])
        pad = np.pad(~ob, 1, constant_values=True)
        for k in ks:
            near_free = _dilate(pad, k)[1:-1, 1:-1]
            halved = ob & (near_free | _dilate(pm, k))
            out[str(k)][B] = round(float(halved.sum() / n), 4)
    return out


def lef_edge_share(path, k_gcells, gcell_um):
    """{B: share} of edge_share for one LEF (first MACRO), cached; None if unreadable."""
    key = (str(path), k_gcells, gcell_um)
    if key not in _EDGE_CACHE:
        try:
            sh = lef_shapes(Path(path).read_text(errors="replace"))
        except OSError:
            sh = None
        _EDGE_CACHE[key] = edge_share(sh, (k_gcells,), gcell_um)[str(k_gcells)] if sh else None
    return _EDGE_CACHE[key]


_SIGNED_CACHE = {}


def signed_view_lefs(die_dir):
    """{module: lef} for repo core views that carry a SIGNED signoff.json next to the LEF (die_dir/cores/**)."""
    key = str(die_dir)
    if key in _SIGNED_CACHE:
        return _SIGNED_CACHE[key]
    out = {}
    root = Path(die_dir) / "cores"
    if root.is_dir():
        for so in root.rglob("signoff.json"):
            try:
                txt = so.read_text(errors="replace")
            except OSError:
                continue
            if "SIGNED" not in txt and '"signed": true' not in txt.lower():
                continue
            for lef in so.parent.glob("*.lef"):
                out.setdefault(lef.stem.replace("_tpl", ""), str(lef))
    _SIGNED_CACHE[key] = out
    return out


_VIEW_SRC = {}   # inst -> ("lef", path) | ("kit", kit_views entry): where the OBS rects of the chosen view live


def macro_band(inst, k_gcells, gcell_um=None):
    """{B: share of the layer-B OBS tiles still halved under GRT-PATCH-1 'edge'} of the view macro_view chose for
    inst, or None (no shapes known: a solid block, whose only OBS boundary is its outline)."""
    gcell_um = gcell_um or GRT_GCELL_UM
    v = _VIEW_SRC.get(inst)
    if not v:
        return None
    if v[0] == "lef":
        return lef_edge_share(v[1], k_gcells, gcell_um)
    kb = (v[1].get("edge_share") or {}).get(str(k_gcells))
    return {L: float(f) for L, f in kb.items()} if kb is not None else None


def macro_view(h, die_dir, repo, cfg):
    """(obs {layer: frac}, kind core|mem, source, provisional) for one hard core / macro.

    Order: (1) cfg views table (signed-view measurements, route_supply_views.json / --views), (2) a SIGNED repo core
    view LEF, (3) the plan's lef (a TEMPLATE that blocks M1-M7 whole is capped at the core ceiling: the built view
    obstructs only its own routing ceiling), (4) obs_max, (5) the ceiling.  kind = mem when nothing above M4 is
    blocked (generated SRAM/ROM: M1-M4 only), else core -- from the LEF, never from the name."""
    mod = h.get("module", "")
    cap = int(cfg["core_ceiling"][1:])
    v = (cfg.get("views") or {}).get(mod)
    obs, src = None, None
    if v:
        if v.get("lef"):
            obs = lef_obs(find_ref(v["lef"], repo))
            if obs is not None:
                _VIEW_SRC[h["inst"]] = ("lef", find_ref(v["lef"], repo))
        if obs is None and v.get("obs_top"):
            top = int(v["obs_top"][1:])
            obs = {f"M{k}": float(v.get("coverage", 1.0)) for k in range(1, top + 1)}
        src = "views:" + str(v.get("src", "table"))
    if obs is None:
        sl = signed_view_lefs(die_dir).get(mod)
        if sl:
            obs = lef_obs(sl)
            src = "signed-repo"
            _VIEW_SRC[h["inst"]] = ("lef", sl)
    kv = None
    kvt = cfg.get("kit_views") or {}
    stem = Path(str(h.get("lef") or "")).stem
    for key in (mod, stem):
        if key and key in kvt:
            kv = kvt[key]
            break
    if obs is None and h.get("lef"):
        obs = lef_obs(find_ref(h["lef"], repo))
        if obs is not None:
            src = "plan-lef"
            _VIEW_SRC[h["inst"]] = ("lef", find_ref(h["lef"], repo))
            if all(obs.get(f"M{k}", 0) > 0.99 for k in range(1, 8)):
                _VIEW_SRC.pop(h["inst"], None)          # template: solid block, its outline is the OBS edge
                if kv:
                    obs, src = None, None          # whole-block template: the kit's real view LEF wins
                else:
                    # the plan's own obs_max for this core is its ceiling (T51 native split children: M7), else
                    # the 12.1a default
                    tc = cap
                    if h.get("obs_max") and cfg.get("template_cap_obs_max", True):
                        tc = min(int(str(h["obs_max"])[1:]), 9)
                    obs = {L: f for L, f in obs.items() if int(L[1:]) <= tc}
                    src = "plan-template(capped M%d%s)" % (tc, " obs_max" if tc != cap else "")
    if obs is None and kv:
        # repo LEF missing (or a template): the macro LEF the kit hands to GRT (route_supply_kit_views.json)
        obs = {L: float(f) for L, f in kv["obs"].items()}
        src = "kit-lef"
        _VIEW_SRC[h["inst"]] = ("kit", kv)
    if obs is None and h.get("obs_max"):
        top = min(int(str(h["obs_max"])[1:]), 9)
        obs = {f"M{k}": 1.0 for k in range(1, top + 1)}
        src = "plan-obs_max"
    if obs is None:
        obs = {f"M{k}": 1.0 for k in range(1, cap + 1)}
        src = "assumed(ceiling M%d)" % cap
    top = max([int(L[1:]) for L, f in obs.items() if f > 0.5] or [0])
    kind = "mem" if 0 < top <= 4 else "core"
    return obs, kind, src, not src.startswith(("views:", "signed"))


def orient_pt(h, x, y):
    w, hh = h["outline_um"]
    o = h.get("orient", "R0")
    X = w - x if o in ("MY", "R180") else x
    Y = hh - y if o in ("MX", "R180") else y
    return h["origin_um"][0] + X, h["origin_um"][1] + Y


REF_DIRS = []      # plan dir + --ref-dirs: plan-relative pins_file / lef references


def read_json(p):
    p = Path(p)
    if p.suffix == ".gz":
        with gzip.open(p, "rt") as f:
            return json.load(f)
    return json.loads(p.read_text())


def find_ref(rel, repo):
    for d in REF_DIRS + [repo]:
        c = Path(d) / rel
        if c.is_file():
            return c
    return Path(repo) / rel


def _pin_iter(d):
    """(name, (x, y)) from the pin-table shapes in use: {pins: [{name, x, y} | {name, xy_um}]}, [..], {name: [x, y]}."""
    pins = d.get("pins", d) if isinstance(d, dict) else d
    if isinstance(pins, dict):
        for k, v in pins.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2 and all(isinstance(a, (int, float)) for a in v[:2]):
                yield k, v
            elif isinstance(v, dict):
                xy = v.get("xy_um") or v.get("xy") or ([v["x"], v["y"]] if "x" in v and "y" in v else None)
                if xy:
                    yield k, xy
        return
    for p in pins or []:
        if not isinstance(p, dict) or "name" not in p:
            continue
        xy = p.get("xy_um") or p.get("xy") or ([p["x"], p["y"]] if "x" in p and "y" in p else None)
        if xy and len(xy) >= 2:
            yield p["name"], xy


def core_pins(h, die_dir, repo):
    """[(bus, x, y)] in the type frame."""
    pf = h.get("pins_file")
    cands = []
    if pf:
        cands = [Path(d) / pf for d in REF_DIRS] + [die_dir / pf, repo / pf]
    for c in cands:
        if c.is_file():
            try:
                d = read_json(c)
            except (OSError, ValueError):
                continue
            out = []
            for name, xy in _pin_iter(d):
                bus = re.sub(r"\[\d+\]$", "", name)
                out.append((bus,) + orient_pt(h, float(xy[0]), float(xy[1])))
            return out
    return []


def escape(x, y, rect, L):
    """point L um outside the core face nearest to pin (x, y)."""
    x0, y0, x1, y1 = rect
    d = {"W": x - x0, "E": x1 - x, "S": y - y0, "N": y1 - y}
    f = min(d, key=d.get)
    return {"W": (x0 - L, y), "E": (x1 + L, y), "S": (x, y0 - L), "N": (x, y1 + L)}[f]


def face_point(W, H, face, window=None):
    lo, hi = (window or (None, None))[:2] if window else (None, None)
    if face in ("N", "S"):
        x = (lo + hi) / 2 if lo is not None else W / 2
        return (x, H if face == "N" else 0.0)
    y = (lo + hi) / 2 if lo is not None else H / 2
    return (W if face == "E" else 0.0, y)


def face_bit_point(W, H, win, rank):
    """point of one bit on a face window: rank = (fraction along the window, bits)."""
    face, (lo, hi) = win
    f = rank[0]
    a = lo + f * (hi - lo)
    if face in ("N", "S"):
        return (a, H if face == "N" else 0.0)
    return (W if face == "E" else 0.0, a)


SKIP = set(filter(None, os.environ.get("ROUTE_SUPPLY_SKIP", "").split(",")))


# ----------------------------------------------------------------------------------------------------------- model
class Grid:
    def __init__(self, W, H, b):
        self.W, self.H, self.b = W, H, b
        self.nx, self.ny = max(1, int(math.ceil(W / b))), max(1, int(math.ceil(H / b)))
        self.dH = np.zeros((self.ny + 1, self.nx + 1))   # difference arrays (density per um^2)
        self.dV = np.zeros((self.ny + 1, self.nx + 1))
        self.wl = 0.0
        self.cur = None      # demand category being added (ablation: env ROUTE_SUPPLY_SKIP=glue,core,ft,station,ring)
        self.rec = None      # FEAS-AUDIT-1 / S81-PLANMODEL-1: list of (cat, label, x0, x1, y0, y1, n) when not None
        self.label = None

    def _rect(self, d, x0, y0, x1, y1, dens):
        b = self.b
        i0, i1 = int(np.clip(x0 // b, 0, self.nx - 1)), int(np.clip(x1 // b, 0, self.nx - 1)) + 1
        j0, j1 = int(np.clip(y0 // b, 0, self.ny - 1)), int(np.clip(y1 // b, 0, self.ny - 1)) + 1
        d[j0, i0] += dens
        d[j0, i1] -= dens
        d[j1, i0] -= dens
        d[j1, i1] += dens

    def net(self, pts, n=1.0, span=0.0):
        """RUDY: n nets with these terminals.  span > 0: the box is at least span um wide across a long thin
        net (the router places a bundle of buffered relay wires anywhere within its detour, not on one line)."""
        if self.cur in SKIP:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        w, h = max(x1 - x0, self.b), max(y1 - y0, self.b)   # a net shorter than a bin still fills that bin
        if span > 0:
            if w < span:
                x0 -= (span - w) / 2
                w = span
            if h < span:
                y0 -= (span - h) / 2
                h = span
        x1, y1 = x0 + w, y0 + h
        # H wire length (x1-x0 actual) spread over w x h; per um^2 = (actual w)/(w h)
        aw, ah = max(xs) - min(xs), max(ys) - min(ys)
        if aw > 0:
            self._rect(self.dH, x0, y0, x1 - 1e-9, y1 - 1e-9, n * aw / (w * h))
        if ah > 0:
            self._rect(self.dV, x0, y0, x1 - 1e-9, y1 - 1e-9, n * ah / (w * h))
        self.wl += n * (aw + ah)
        if self.rec is not None and self.cur != "glue":
            self.rec.append((self.cur, self.label, min(xs), max(xs), min(ys), max(ys), n))

    def area_density(self, rect, dens_h, dens_v):
        if self.cur in SKIP:
            return
        x0, y0, x1, y1 = rect
        self._rect(self.dH, x0, y0, x1 - 1e-9, y1 - 1e-9, dens_h)
        self._rect(self.dV, x0, y0, x1 - 1e-9, y1 - 1e-9, dens_v)

    def demand(self):
        """track-um per bin -> tracks per bin (divide by bin length along the direction = b)."""
        a = self.b * self.b
        DH = np.cumsum(np.cumsum(self.dH, 0), 1)[: self.ny, : self.nx] * a / self.b
        DV = np.cumsum(np.cumsum(self.dV, 0), 1)[: self.ny, : self.nx] * a / self.b
        return DH, DV


def macro_rects(t):
    out = []
    for h in t.get("hard_cores", []) or []:
        ox, oy = h["origin_um"]
        w, hh = h["outline_um"]
        out.append((ox, oy, ox + w, oy + hh, h))
    return out


def coverage(grid, rects):
    """per-bin covered fraction for each rect list entry -> list of arrays (sparse via slices)."""
    b = grid.b
    xs = np.arange(grid.nx) * b
    ys = np.arange(grid.ny) * b
    res = []
    for (x0, y0, x1, y1, h) in rects:
        cx = np.clip(np.minimum(xs + b, x1) - np.maximum(xs, x0), 0, None) / b
        cy = np.clip(np.minimum(ys + b, y1) - np.maximum(ys, y0), 0, None) / b
        res.append((np.outer(cy, cx), h))
    return res


def run_pool(D, S, occ, axis, k, m):
    """ratio pooled over each contiguous macro run along `axis` (+ m bins each side), k bins wide across it."""
    if axis == 1:
        return run_pool(D.T, S.T, occ.T, 0, k, m).T
    ny, nx = D.shape
    Dk = box(D, k, 1)
    Sk = box(S, k, 1)
    out = np.zeros_like(D)
    for i in range(nx):
        col = occ[:, i]
        if not col.any():
            continue
        j = 0
        while j < ny:
            if not col[j]:
                j += 1
                continue
            j1 = j
            while j1 < ny and col[j1]:
                j1 += 1
            a, z = max(0, j - m), min(ny, j1 + m)
            out[j:j1, i] = Dk[a:z, i].sum() / max(Sk[a:z, i].sum(), 1e-6)
            j = j1
    return out


def box(a, k, ky=None):
    """mean over a (ky rows x k cols) window, edge-padded."""
    ky = k if ky is None else ky
    if k <= 1 and ky <= 1:
        return a
    px, py = k // 2, ky // 2
    s = np.pad(a, ((py, ky - 1 - py), (px, k - 1 - px)), mode="edge")
    c = np.cumsum(np.cumsum(s, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[ky:, k:] - c[:-ky, k:] - c[ky:, :-k] + c[:-ky, :-k])[: a.shape[0], : a.shape[1]] / (k * ky)


def _nearest_on_rect(p, r):
    x0, y0, x1, y1 = r
    x = min(max(p[0], x0), x1)
    y = min(max(p[1], y0), y1)
    if x0 < x < x1 and y0 < y < y1:           # inside: to the nearest edge
        d = {(x0, y): x - x0, (x1, y): x1 - x, (x, y0): y - y0, (x, y1): y1 - y}
        return min(d, key=d.get)
    return (x, y)


def _seam_pts(r, q, frac):
    """the hop from core r to core q: facing edges, at fraction `frac` along their overlap (bits spread over the seam,
    each at its own row/column), else the nearest corners."""
    ax0, ay0, ax1, ay1 = r
    bx0, by0, bx1, by1 = q
    lo, hi = max(ay0, by0), min(ay1, by1)
    if hi > lo and (ax1 <= bx0 or bx1 <= ax0):
        y = lo + frac * (hi - lo)
        return ((ax1, y), (bx0, y)) if ax1 <= bx0 else ((ax0, y), (bx1, y))
    lo, hi = max(ax0, bx0), min(ax1, bx1)
    if hi > lo and (ay1 <= by0 or by1 <= ay0):
        x = lo + frac * (hi - lo)
        return ((x, ay1), (x, by0)) if ay1 <= by0 else ((x, ay0), (x, by1))
    c = (min(max((bx0 + bx1) / 2, ax0), ax1), min(max((by0 + by1) / 2, ay0), ay1))
    return c, _nearest_on_rect(c, q)


def _gap(r, q):
    return max(0.0, q[0] - r[2], r[0] - q[2]) + max(0.0, q[1] - r[3], r[1] - q[3])


def ft_core_internal(g, W, H, f, wbits, rects, bundles=16):
    """parent wire of a feed-through slot carried inside hard cores (stations_in), per bit bundle spread over the
    face windows: in face -> nearest core, core -> next core across their seam (spread along it), last core -> out
    face. The slot's own wires over the cores are child-internal (CPL-S81-STN t51)."""
    nb = max(1, min(bundles, wbits))
    fi, fo = f.get("in_face", "W"), f.get("out_face", "E")
    wi = f.get("in_window_um") or ([0, H] if fi in ("W", "E") else [0, W])
    wo = f.get("out_window_um") or ([0, H] if fo in ("W", "E") else [0, W])
    for j in range(nb):
        n = wbits / nb
        fr = (j + 0.5) / nb
        a = face_bit_point(W, H, (fi, tuple(wi[:2])), (fr, nb))
        z = face_bit_point(W, H, (fo, tuple(wo[:2])), (fr, nb))
        # enter the core nearest the in point, leave from the core nearest the out point, hopping core to core
        # (nearest gap first) only until that last core is reached; stations_in cores off that path add nothing
        cur = min(rects, key=lambda q: _gap((a[0], a[1], a[0], a[1]), q))
        last = min(rects, key=lambda q: _gap((z[0], z[1], z[0], z[1]), q))
        left = [q for q in rects if q != cur]
        e = _nearest_on_rect(a, cur)
        if e != a:
            g.net([a, e], n=n)
        while cur != last and left:
            nxt = last if _gap(cur, last) <= min(_gap(cur, q) for q in left) else min(left, key=lambda q: _gap(cur, q))
            left.remove(nxt)
            p, q = _seam_pts(cur, nxt, fr)
            if p != q:
                g.net([p, q], n=n)
            cur = nxt
        x = _nearest_on_rect(z, cur)
        if x != z:
            g.net([x, z], n=n)


def analyze_type(name, t, die_dir, repo, conns, cfg):
    W, H = map(float, t["outline_um"])
    b = cfg["bin_um"]
    g = Grid(W, H, b)
    if cfg.get("record_nets"):
        g.rec = []
    notes = []
    if cfg.get("fanout", True) and (_UNREAL.get(name) or {}).get("phantom"):
        # S81-PLANMODEL-1: plan stations whose class has bound depth 0 (s81_leaf_conns.py) are wires, not registers
        t, nd_, nb_, nu_ = drop_phantoms(name, t, _UNREAL)
        notes.append(f"UNREALISED {nd_} plan station(s) / {nb_} b: bound depth 0, not counted as register hops"
                     + (f", {nu_} rows unmatched" if nu_ else ""))
    mrects = macro_rects(t)
    cov = coverage(g, mrects)
    # ---------------- supply
    obs = {L: np.zeros((g.ny, g.nx)) for L in LAYERS}
    macro_cov = np.zeros((g.ny, g.nx))
    mem_cov = np.zeros((g.ny, g.nx))
    obs_src = defaultdict(int)
    macro_obs = {}
    _VIEW_SRC.clear()
    h_kind = {}
    provisional = set()
    for (c, h) in cov:
        o, kind, src, prov = macro_view(h, die_dir, repo, cfg)
        macro_obs[h["inst"]] = o
        obs_src[src] += 1
        h_kind[h["inst"]] = kind
        sm = cfg.get("signed_modules")
        if kind == "core" and (prov if sm is None else h.get("module") not in sm):
            provisional.add(h.get("module", "?"))
        for L in LAYERS:
            if o.get(L):
                obs[L] = np.maximum(obs[L], c * o[L])
        if cfg.get("over_macro_m67") and kind == "core":
            # GRT-CALIB-1 (2): over a hard core only M6/M7 carry signals (kit views block M1-M5 over the macro)
            for L in ("M2", "M3", "M4", "M5"):
                obs[L] = np.maximum(obs[L], c)
        macro_cov = np.maximum(macro_cov, c)
        if kind == "mem":
            mem_cov = np.maximum(mem_cov, c)
    if cfg.get("grt_rules", True):
        grt_macro_rules(obs)
    pins = {}
    for (_, _, _, _, h) in mrects:
        pins[h["inst"]] = core_pins(h, die_dir, repo)
    mode = cfg.get("grt_halving", "full")
    # GRT-PATCH-1 11-11 (OWNER 01:1x, opt-in): rows on the halving-off parallel arm (kit item_env
    # OT_GRT_TRANSITION_MODE=<mode>) get that mode here, so their plan flags use the router's capacity model.
    # --grt-halving-type TYPE=MODE; "off" is the router env name of "none".  Absent = the global --grt-halving.
    mode = (cfg.get("grt_halving_types") or {}).get(name, mode)
    mode = "none" if mode == "off" else mode
    K = cfg.get("grt_edge_gcells", 2)
    halve_w = {L: 1.0 for L in LAYERS}
    if mode == "none":
        halve_w = {L: 0.0 for L in LAYERS}
    elif mode == "edge_outline":
        w = grt_halving_weight(g, mrects, pins, K)
        halve_w = {L: w for L in LAYERS}
    elif mode == "edge":
        halve_w = grt_halving_weight_obs(g, cov, mrects, pins, K, macro_obs, notes)
    sup = {}
    for L in LAYERS:
        sup[L] = b / PITCH[L] * (1 - cfg["derate"][L]) * (1 - np.clip(obs[L], 0, 1))
        if cfg.get("grt_rules", True) and L in GRT_TRANSITION:
            # fat-via transition layer: OpenROAD halves L's capacity over every gcell under a MACRO OBS on L-1
            # (GlobalRouter::adjustTransitionLayers / adjustTileSet, floor(cap * 0.5))
            below = LAYERS[LAYERS.index(L) - 1] if LAYERS.index(L) > 0 else None
            if below:
                sup[L] = sup[L] * (1 - 0.5 * np.clip(obs[below], 0, 1) * halve_w[below])
    supH = sup["M2"] + sup["M4"] + sup["M6"]
    supV = sup["M3"] + sup["M5"] + sup["M7"]
    # ---------------- demand
    npins = sum(len(v) for v in pins.values())
    if npins == 0 and mrects:
        notes.append("no core pin files found")
    bus_pt = {}
    bus_win = {}
    bus_dir = defaultdict(list)          # "in"/"out" -> face bus names (stale bus names fall back to these)
    for bu in t.get("buses", []) or []:
        if bu.get("face"):
            bus_dir[str(bu.get("dir", ""))].append(bu["name"])
            bus_pt[bu["name"]] = face_point(W, H, bu["face"], bu.get("window_um"))
            if bu.get("window_um") and cfg.get("face_spread", True):
                bus_win[bu["name"]] = (bu["face"], tuple(bu["window_um"][:2]))
    cc_key = next((k for k in (name, re.sub(r"__cl[0-9a-f]{8}.*$", "", name), re.sub(r"__.*$", "", name))
                   if conns.get(k)), None)
    cc = conns.get(cc_key) if cc_key else None
    model = "core_conns" if cc else ("fallback" if npins else "none")
    cen = {}
    for inst, pl in pins.items():
        if pl:
            cen[inst] = (sum(p[1] for p in pl) / len(pl), sum(p[2] for p in pl) / len(pl))
        else:
            for (x0, y0, x1, y1, h) in mrects:
                if h["inst"] == inst:
                    cen[inst] = ((x0 + x1) / 2, (y0 + y1) / 2)
    bus_cen = {}
    for inst, pl in pins.items():
        acc = defaultdict(list)
        for bus, x, y in pl:
            acc[bus].append((x, y))
        bus_cen[inst] = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in acc.items()}
    unresolved = 0
    stale_bus = 0
    nglue = 0
    unchecked = 0          # pins of cores whose core_conns entry is empty {}: no partner known, not scored
    # links carried by internal_stations (launch core:A.bus -> capture B): not counted again as a direct core net
    st_pairs = set()
    st_rev = defaultdict(set)
    for s_ in t.get("internal_stations", []) or []:
        la = str(s_.get("launch", ""))
        if la.startswith("core:"):
            ab = la[5:]
            A, _, bus_ = ab.rpartition(".")
            B = str(s_.get("capture", "")).split(".")
            Bi = ".".join(B[:-1]) if B[-1] and str(s_.get("capture", "")).rsplit(".", 1)[0] in cen else str(
                s_.get("capture", ""))
            st_pairs.add((A, bus_, Bi))
            # the capture end lists A as its destination on some input bus
            for bb, dd in ((cc or {}).get(Bi, {}) or {}).items():
                if _names_core(dd, A):
                    st_rev[(Bi, bb)].add((A, Bi))
    # face buses carried by an internal_stations chain (conn bus:X, one end a core pin of inst): the chain is the
    # wire from that core to the face, so the core pin's bus:X destination is not a second face net (FEAS-AUDIT-1)
    st_face = set()
    if cfg.get("station_face_dedupe", True):
        for s_ in t.get("internal_stations", []) or []:
            cn = str(s_.get("conn", ""))
            if not cn.startswith("bus:"):
                continue
            for end in (s_.get("launch", ""), s_.get("capture", "")):
                e_ = str(end)
                e_ = e_[5:] if e_.startswith("core:") else e_
                hit = [c_ for c_ in cen if e_ == c_ or e_.startswith(c_ + ".")]
                if hit:
                    st_face.add((max(hit, key=len), cn[4:]))
    carried = 0
    rect_of = {h["inst"]: (x0, y0, x1, y1) for (x0, y0, x1, y1, h) in mrects}
    # S81-PLANMODEL-1: ports named by a fan-out net are drawn by that net only (not as glue escapes / core_conns nets)
    fan_nets = [n_ for n_ in (_FANOUT.get(name) or _FANOUT.get(cc_key) or []) if cfg.get("fanout", True)]
    fan_claim = {(i_, p_) for n_ in fan_nets for i_, p_ in n_["pins"]}
    fan_claimed = 0
    g.cur = "core"
    # face pin band: the bits of a face bus land spread over its window, in the order of the core pins that drive
    # them (no crossing), not at one point
    face_rank = {}
    if cc and bus_win:
        groups = defaultdict(list)
        for inst, pl in pins.items():
            ci = cc.get(inst, {}) if pl else {}
            for bus, x, y in pl:
                for d in ci.get(bus) or []:
                    k, _, v = str(d).partition(":")
                    if k == "bus" and v in bus_win:
                        groups[v].append((inst, bus, x, y))
        for v, lst in groups.items():
            along = 0 if bus_win[v][0] in ("N", "S") else 1
            order = sorted(range(len(lst)), key=lambda i: lst[i][2 + along])
            for r_, i in enumerate(order):
                inst, bus, x, y = lst[i]
                face_rank[(inst, bus, v, x, y)] = ((r_ + 0.5) / len(lst), len(lst))
    for inst, pl in pins.items():
        if not pl:
            continue
        if fan_claim:
            n0_ = len(pl)
            pl = [q_ for q_ in pl if (inst, q_[0]) not in fan_claim]
            fan_claimed += n0_ - len(pl)
            if not pl:
                continue
        if cc:
            ci = cc.get(inst, {})
            if inst in cc and not ci and cfg.get("empty_conns_unchecked", True):
                # empty entry: the netlist trace found no wiring partner, which says nothing about where the
                # pins go (glue, parent logic, faces). UNCHECKED, not scored as local escapes
                unchecked += len(pl)
                continue
            for bus, x, y in pl:
                dl = [d_ for d_ in (ci.get(bus) or []) if d_ != "glue"]
                if st_face:
                    n0 = len(dl)
                    dl = [d_ for d_ in dl if not (str(d_).startswith("bus:") and (inst, str(d_)[4:]) in st_face)]
                    if len(dl) < n0:
                        carried += 1
                        if not dl:
                            continue            # routed by its internal_stations chain to the face
                if not dl:
                    # pin to type glue logic (not core-to-core): a local escape net from the pin out of the
                    # core face, cfg glue_um long (the glue cells sit next to the core)
                    g.cur = "glue"
                    g.net([(x, y), escape(x, y, rect_of[inst], cfg["glue_um"])])
                    g.cur = "core"
                    nglue += 1
                    continue
                pts = [(x, y)]
                two_sided = True
                had_face = False
                for d in dl:
                    k, _, v = str(d).partition(":")
                    if k == "bus" and v in bus_win:
                        had_face = True
                        fp = face_bit_point(W, H, bus_win[v], face_rank.get((inst, bus, v, x, y), (0.5, 1)))
                        pts.append(fp)
                        dl = [dd for dd in dl if dd != d]
                        break
                for d in dl:
                    k, _, v = str(d).partition(":")
                    if k == "core" and v not in cen and v.rpartition(".")[0] in cen:
                        v = v.rpartition(".")[0]    # core_conns_from_bind form core:<inst>.<port>
                    if k == "core" and v in cen:
                        if (inst, bus, v) in st_pairs or (v, inst) in st_rev.get((inst, bus), ()):
                            continue            # this link is routed by its internal_stations chain
                        mate = [bb for bb, dd in (cc.get(v, {}) or {}).items() if _names_core(dd, inst)]
                        two_sided &= bool(mate)
                        pts.append(bus_cen[v][mate[0]] if mate and mate[0] in bus_cen.get(v, {}) else cen[v])
                    elif k == "bus" and v in bus_pt:
                        pts.append(bus_pt[v])
                    elif k == "bus" and cfg.get("stale_bus_nearest", True) and v[-2:] in ("_i", "_o") \
                            and bus_dir.get({"_i": "in", "_o": "out"}[v[-2:]]):
                        # bus name not in this plan (core_conns older than a lane renumbering): the nearest face
                        # bus of the same direction (ESTIMATE, counted)
                        cand = bus_dir[{"_i": "in", "_o": "out"}[v[-2:]]]
                        pts.append(min((bus_pt[c_] for c_ in cand), key=lambda q: abs(q[0] - x) + abs(q[1] - y)))
                        stale_bus += 1
                    elif k == "face" and v in "NSEW":
                        pts.append(face_point(W, H, v))
                    elif k == "tap":
                        continue                # clock entry: the clock tree, not a signal net
                    else:
                        unresolved += 1
                if len(pts) > 1:
                    g.label = ("core", inst, bus, tuple(d_ for d_ in (ci.get(bus) or []) if d_ != "glue"))
                    # core_conns lists a core-to-core link at BOTH ends: count each end half
                    w_ = 0.5 if two_sided and not had_face and all(not str(d).startswith(("bus:", "face:")) for d in dl) \
                        else 1.0
                    if cfg.get("pin_escape", False) and len(pts) == 2:
                        # pin band: a core pin leaves its face along the face normal, so a 2-pin link is an L whose
                        # first leg runs at the pin's own row (W/E face -> H leg at pin y, N/S -> V leg at pin x)
                        (px_, py_), (qx_, qy_) = pts
                        x0r, y0r, x1r, y1r = rect_of[inst]
                        dd_ = {"W": px_ - x0r, "E": x1r - px_, "S": py_ - y0r, "N": y1r - py_}
                        if min(dd_, key=dd_.get) in ("W", "E"):
                            mid = (qx_, py_)
                        else:
                            mid = (px_, qy_)
                        g.net([pts[0], mid], n=w_)
                        g.net([mid, pts[1]], n=w_)
                    else:
                        g.net(pts, n=w_)
        else:
            others = [(cen[k], len(pins[k])) for k in pins if k != inst and pins[k]]
            if not others:
                continue
            tw = sum(n for _, n in others)
            px = sum(c[0] * n for c, n in others) / tw
            py = sum(c[1] * n for c, n in others) / tw
            for bus, x, y in pl:
                g.net([(x, y), (px, py)])
    fan_bits = 0
    if fan_nets:
        port_cen = {}
        for inst_, bc_ in bus_cen.items():
            for bus_, c_ in bc_.items():
                port_cen[(inst_, bus_)] = c_
        for n_ in fan_nets:
            pts_ = [port_cen[(i_, p_)] for i_, p_ in n_["pins"] if (i_, p_) in port_cen]
            go_ = [port_cen[(i_, p_)] for i_, p_ in n_.get("glue_of", []) if (i_, p_) in port_cen]
            if go_:
                pts_.append((sum(q[0] for q in go_) / len(go_), sum(q[1] for q in go_) / len(go_)))
            if len(pts_) > 1:
                g.label = ("core", n_["name"], n_["kind"], ())
                g.net(pts_, n=n_["bits"])
                fan_bits += n_["bits"]
        notes.append(f"PLANMODEL {len(fan_nets)} fan-out nets / {fan_bits} b replace {fan_claimed} core pins "
                     f"(s81_leaf_conns.py, from the leaf RTL)")
    if unresolved:
        notes.append(f"{unresolved} core_conns destinations not placed in the type")
    if unchecked:
        notes.append(f"{unchecked} core pins UNCHECKED (core_conns entry empty: partners unknown, not scored)")
    if stale_bus:
        notes.append(f"{stale_bus} core_conns bus destinations not in the plan, taken to the nearest same-direction "
                     f"face bus (ESTIMATE)")
    # ft slots
    g.cur = "ft"
    ft_bits = 0
    ft_internal = 0
    ft_internal_slots = set()
    rect_by_name = {}
    for (x0, y0, x1, y1, h) in mrects:
        for k_ in (h.get("inst"), h.get("module")):
            if k_:
                rect_by_name[k_] = (x0, y0, x1, y1)
    for f in t.get("ft_slots", []) or []:
        wbits = int(f.get("width", 1))
        g.label = ("ft", str(f.get("name", "")), wbits)
        si_ = [rect_by_name[n_] for n_ in (f.get("stations_in") or []) if n_ in rect_by_name]
        if si_ and cfg.get("ft_core_internal", True):
            # the slot's stations and wires live inside these hard cores (stations_in): parent wire is only
            # face -> first core, core -> core across the street/seam, last core -> face, each along the slot line
            ft_core_internal(g, W, H, f, wbits, si_)
            ft_internal += wbits
            ft_bits += wbits
            ft_internal_slots.add(str(f.get("name", "")))
            continue
        regs = [tuple(r) for r in (f.get("regs_um") or [])]
        sites = f.get("bit_sites_um") or []
        chain = []
        if sites and isinstance(sites[0], list) and sites[0] and isinstance(sites[0][0], list):
            for si, s in enumerate(sites):
                pts = [tuple(p[:2]) for p in s]
                ref = regs[si + 1] if si + 1 < len(regs) else None
                if ref:
                    cx = sum(p[0] for p in pts) / len(pts)
                    cy = sum(p[1] for p in pts) / len(pts)
                    if abs(cy - ref[0]) + abs(cx - ref[1]) < abs(cx - ref[0]) + abs(cy - ref[1]):
                        pts = [(p[1], p[0]) for p in pts]   # sites stored (y, x) in this plan
                chain.append(pts)
        start = regs[0] if regs else face_point(W, H, f.get("in_face", "W"),
                                                    f.get("in_window_um"))
        end = face_point(W, H, f.get("out_face", "E"), f.get("out_window_um"))
        prev = None
        for st in chain:
            n = len(st)
            if prev is None:
                for p in st[: wbits]:
                    g.net([start, p])
            else:
                m = min(len(prev), n)
                for i in range(m):
                    g.net([prev[i], st[i]])
            prev = st
        if prev is None:
            pts = [start] + [r for r in regs[1:]] + [end]
            for a, c in zip(pts, pts[1:]):
                g.net([a, c], n=wbits)
        else:
            for p in prev[: wbits]:
                g.net([p, end])
        ft_bits += wbits
    st_bits = 0
    g.cur = "station"
    # stations that share a launch pin are ONE driver net to all their first registers (a broadcast bus to 16
    # lanes is a 17-pin net, not 16 two-pin nets); later hops are per link
    fan = defaultdict(list)
    for s in t.get("internal_stations", []) or []:
        pts = [tuple(s["from_um"])] + [tuple(r) for r in s.get("regs_um", [])] + [tuple(s["to_um"])]
        nb = station_bits(t, s)
        fan[(str(s.get("launch")), tuple(round(v, 1) for v in s["from_um"]))].append((pts, nb))
        st_bits += nb
    sp = cfg["detour_um"] if cfg.get("station_spread", False) else 0.0
    for (_la, _), lst in fan.items():
        bits = max(n for _, n in lst)
        g.label = ("st", _la, bits)
        g.net([lst[0][0][0]] + [p[1] for p, _ in lst], n=bits, span=sp)
        for pts, n in lst:
            for a, c in zip(pts[1:], pts[2:]):
                g.net([a, c], n=n, span=sp)
    # landing rings
    g.cur = "ring"
    ring_cells = np.zeros((g.ny, g.nx), dtype=bool)
    lc = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
    ring_bits = 0
    ring_internal = 0
    for bn, bd in lc.items():
        r = bd.get("rect_um")
        if not r:
            continue
        if re.sub(r"_[io]$", "", str(bn)) in ft_internal_slots:
            # landing band of a core-internal ft slot: its storage sits with the slot's stations inside the child
            ring_internal += 1
            continue
        x0, y0, x1, y1 = map(float, r)
        flops = float(bd.get("padded_data_storage_flops") or bd.get("live_data_storage_flops") or 0)
        bits = float(bd.get("width") or 0)
        need = max((x1 - x0) * (y1 - y0), flops * cfg["ring_um2_per_flop"])
        # the placer spreads the ring storage around its band into free (non-macro) area: grow the band one bin
        # per side in turn, skipping a side whose new strip is mostly macro or outside the outline, until the free
        # area holds the ring (KV hgi_v3 ft27: squeezed between e0/e2 it ran ~232 um along the street)
        occm = macro_cov > 0.5

        def free_area(r):
            a0, b0 = int(max(0, r[0]) // b), int(max(0, r[1]) // b)
            a1, b1 = int(math.ceil(min(W, r[2]) / b)), int(math.ceil(min(H, r[3]) / b))
            return float((~occm[b0:b1, a0:a1]).sum()) * b * b

        rr = [x0, y0, x1, y1]
        for _ in range(2000):
            if free_area(rr) >= need:
                break
            best_c = None
            for side in (0, 1, 2, 3):
                cand = list(rr)
                cand[side] += -b if side < 2 else b
                cand = [max(0.0, cand[0]), max(0.0, cand[1]), min(W, cand[2]), min(H, cand[3])]
                if cand == rr:
                    continue
                strip = free_area(cand) - free_area(rr)
                area_add = (cand[2] - cand[0]) * (cand[3] - cand[1]) - (rr[2] - rr[0]) * (rr[3] - rr[1])
                if area_add <= 0 or strip < 0.5 * area_add:
                    continue
                w_, h_ = cand[2] - cand[0], cand[3] - cand[1]
                asp = max(w_, h_) / max(min(w_, h_), 1e-6)     # the placer keeps the ring compact
                if best_c is None or asp < best_c[0]:
                    best_c = (asp, cand)
            if best_c is None:
                break
            rr = best_c[1]
        x0, y0, x1, y1 = rr
        hgt, wid = max(y1 - y0, b), max(x1 - x0, b)
        # ring_tracks_per_bit x bits wires cross every cut of the ring area, spread over the cut length
        g.area_density((x0, y0, x1, y1), cfg["ring_tracks_per_bit"] * bits / hgt,
                       cfg["ring_tracks_per_bit"] * bits / wid)
        i0, i1 = int(x0 // b), int(math.ceil(x1 / b))
        j0, j1 = int(y0 // b), int(math.ceil(y1 / b))
        ring_cells[j0:j1, i0:i1] = True
        ring_bits += bits
    DH, DV = g.demand()
    g.cur = "cell"
    # background cell wiring outside macros
    bgH = cfg["cell_fill"] * (sup["M2"] + sup["M4"]) * (1 - macro_cov)
    bgV = cfg["cell_fill"] * (sup["M3"] + sup["M5"]) * (1 - macro_cov)
    DH = DH + bgH
    DV = DV + bgV
    k = cfg["window"]
    # anisotropic detour window: H traffic over a macro may shift up/down to a gap within detour_um, so the H
    # ratio is pooled over (detour bins tall x window wide); V the transpose
    kd = max(1, int(round(cfg["detour_um"] / b)) | 1)
    rH = box(DH, k, kd) / np.maximum(box(supH, k, kd), 1e-6)
    rV = box(DV, kd, k) / np.maximum(box(supV, kd, k), 1e-6)
    # over a macro the cut that matters is ACROSS the whole blockage: an H wire over a macro may move anywhere
    # along the macro run's height (plus margin_bins of free rows above/below) to cross it, so over macro bins the
    # H ratio is pooled over the full macro run in that column (V: the run in that row)
    occb = macro_cov > 0.5
    # GRT-CALIB-2: local (unpooled) demand / supply windows for --macro-hotspot local (ratio of sums per macro)
    hot_loc = ((box(DH, k, kd), box(supH, k, kd)), (box(DV, kd, k), box(supV, kd, k))) if cfg.get("macro_hotspot") else None
    rH = np.where(occb, run_pool(DH, supH, occb, 0, k, cfg["margin_bins"]), rH)
    rV = np.where(occb, run_pool(DV, supV, occb, 1, k, cfg["margin_bins"]), rV)
    # porous-abstract what-if (OWNER idea 11-10): signed cores with low cell fill leave most of M4/M5 inside their
    # outline empty while the abstract blocks it.  need_free = the share of the blocked M4 (H) / M5 (V) over hard
    # cores that would have to be free for the core-region p99 ratio to reach 1 (routing supply only: type cells
    # still may not sit inside a core outline, 12.2a1).
    kd_ = max(1, int(round(cfg["detour_um"] / b)) | 1)
    core_only = (macro_cov > 0.5) & ~(mem_cov > 0.5)
    porous = {}
    for d, D, S, L, kx, ky in (("H", DH, supH, "M4", k, kd_), ("V", DV, supV, "M5", kd_, k)):
        extra = b / PITCH[L] * (1 - cfg["derate"][L]) * np.clip(obs[L], 0, 1) * (macro_cov > 0.5)
        if not core_only.any():
            continue
        bd = box(D, kx, ky)

        def p99(f):
            return float(np.percentile((bd / np.maximum(box(S + f * extra, kx, ky), 1e-6))[core_only], 99))
        p0, p1 = p99(0.0), p99(1.0)
        if p0 < 1.0:
            need = 0.0
        elif p1 >= 1.0:
            need = None
        else:
            lo, hi = 0.0, 1.0
            for _ in range(12):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if p99(mid) >= 1.0 else (lo, mid)
            need = round(hi, 3)
        porous[d] = dict(layer=L, p99_now=round(p0, 3), p99_all_free=round(p1, 3), need_free=need)
    # region classes
    cls = np.full((g.ny, g.nx), "open", dtype=object)
    fb = max(1, int(round(cfg["face_um"] / b)))
    cls[:fb, :] = "face"
    cls[-fb:, :] = "face"
    cls[:, :fb] = "face"
    cls[:, -fb:] = "face"
    occ = macro_cov > 0.5
    sb = max(1, int(round(cfg["street_um"] / b)))
    if occ.any():
        def near(a, axis, rev):
            # a macro within sb bins on one side
            out = np.zeros_like(a)
            for s in range(1, sb + 1):
                sh = np.roll(a, s if not rev else -s, axis=axis)
                if axis == 0:
                    if not rev:
                        sh[:s, :] = False
                    else:
                        sh[-s:, :] = False
                else:
                    if not rev:
                        sh[:, :s] = False
                    else:
                        sh[:, -s:] = False
                out |= sh
            return out
        def between(a):
            return (~occ) & ((near(a, 1, False) & near(a, 1, True)) | (near(a, 0, False) & near(a, 0, True)))
        cls[between(occ)] = "mstreet"           # beside SRAM/ROM macros (M5-M7 free over them)
        cls[between(occ & ~(mem_cov > 0.5))] = "street"   # between two HARD cores (M6/M7 only over them)
    cls[ring_cells & ~occ] = "ring"
    cls[occ] = "core"
    cls[mem_cov > 0.5] = "mem"
    # worst region
    best = None
    stats = {}
    for c in ("core", "mem", "street", "mstreet", "face", "open", "ring"):
        m = cls == c
        if not m.any():
            continue
        for d, R in (("H", rH), ("V", rV)):
            v = R[m]
            p99 = float(np.percentile(v, 99))
            hot = int((v > cfg["hot"]).sum())
            mx = float(v.max())
            stats[f"{c}_{d}"] = dict(p99=round(p99, 3), max=round(mx, 3), hot_bins=hot, bins=int(m.sum()))
            key = (p99, mx)
            if best is None or key > best[0]:
                jj, ii = np.unravel_index(np.argmax(np.where(m, R, -1)), R.shape)
                best = (key, c, d, int(ii), int(jj), hot)
    if best is None:
        return None
    mh = cfg.get("macro_hotspot")
    if mh:
        # GRT-CALIB-2 (COORD 11-12): per-macro hot spot. The region p99 pools every core bin of the type, so one hot
        # macro among many (S81 col: 50+ macros) stays under the 99th percentile; GRT overflowed over single macros
        # (calib congestion maps). Per hard core over the bins it covers (> 0.5), max over the macros:
        # local: windowed demand / windowed supply summed over the macro (ratio of sums: a bin with ~0 supply, e.g.
        # under an M1-M7 view, cannot blow it up); pooled: mean of the macro-run pooled ratio.
        # Reported as region mhot_H / mhot_V (p99 = that max), so --verdict-mode calib also reads it. Stats only:
        # the worst-region choice and the default output do not change.
        for di, (d, R) in enumerate((("H", rH), ("V", rV))):
            top = None
            for (cv, h) in cov:
                m = cv > 0.5
                if int(m.sum()) < cfg.get("hotspot_min_bins", 4):
                    continue
                if mh == "local":
                    Dw, Sw = hot_loc[di]
                    v = float(Dw[m].sum() / max(Sw[m].sum(), 1e-6))
                else:
                    v = float(R[m].mean())
                if top is None or v > top[0]:
                    top = (v, h.get("inst", "?"), float(R[m].max()), int(m.sum()))
            if top:
                stats[f"mhot_{d}"] = dict(p99=round(top[0], 3), max=round(top[2], 3), hot_bins=0, bins=top[3],
                                         inst=top[1], mode=mh)
    (_, mx), c, d, ii, jj, hot = best[0], best[1], best[2], best[3], best[4], best[5]
    p99 = best[0][0]
    lay = [L for L in LAYERS if DIRN[L] == d]
    sh = {L: float(sup[L][jj, ii]) for L in lay}
    tot = sum(sh.values()) or 1.0
    main = max(sh, key=sh.get)
    hot_all = int(((rH > cfg["hot"]) | (rV > cfg["hot"])).sum())
    return dict(
        type=name, outline_um=[W, H], model=model, bins=[g.nx, g.ny],
        conns_src=_CONNS_SRC.get(cc_key) if cc else None,
        macros=len(mrects), mem_macros=sum(1 for v in h_kind.values() if v == "mem"),
        provisional_children=sorted(provisional),
        macro_area_frac=round(float(macro_cov.sum()) / (g.nx * g.ny), 3),
        mem_area_frac=round(float(mem_cov.sum()) / (g.nx * g.ny), 3), glue_pins=nglue, station_carried_pins=carried,
        core_pins=npins, unchecked_pins=unchecked, ft_bits=ft_bits, ft_core_internal_bits=ft_internal,
        ring_bands_core_internal=ring_internal,
        station_bits=st_bits, ring_bits=int(ring_bits),
        wirelength_mm=round(g.wl / 1000, 1),
        worst=dict(region=c, dir=d, p99=round(p99, 3), max=round(mx, 3),
                   at_um=[round((ii + 0.5) * b, 1), round((jj + 0.5) * b, 1)],
                   layer=main, layer_share={L: round(v / tot, 2) for L, v in sh.items()},
                   hot_bins_region=hot),
        hot_bins=hot_all, hot_area_um2=round(hot_all * b * b),
        porous=porous, children=children_fill(mrects, h_kind, cfg),
        fix=FIX.get((c, d), "?"), regions=stats, notes=notes, obs_src=dict(obs_src),
        _maps=(rH, rV, cls), _sup=(supH, supV), _bin=b, _rec=g.rec,
    )


def children_fill(mrects, h_kind, cfg):
    """child hard cores with cell fill: measured (--core-fill table) else plan 'cells' x cell_um2 (ESTIMATE)."""
    tab = cfg.get("core_fill") or {}
    out = {}
    for (x0, y0, x1, y1, h) in mrects:
        if h_kind.get(h["inst"]) != "core":
            continue
        m = h.get("module", "?")
        e = out.setdefault(m, dict(module=m, n=0, area_um2=round((x1 - x0) * (y1 - y0)), fill=None, src=None,
                                   free_M4=None, free_M5=None))
        e["n"] += 1
        if m in tab:
            t = tab[m]
            e.update(fill=t.get("fill"), free_M4=t.get("free_M4"), free_M5=t.get("free_M5"),
                     src="measured:" + str(t.get("src", "table")))
        elif h.get("cells") and e["fill"] is None:
            e.update(fill=round(min(1.0, float(h["cells"]) * cfg["cell_um2"] / max(e["area_um2"], 1)), 3),
                     src="ESTIMATE plan cells x %.3f um2" % cfg["cell_um2"])
    return sorted(out.values(), key=lambda e: -e["area_um2"] * e["n"])


def conns_sources(die_dir, plan_dir=None, ref_dirs=(), path=None):
    """core_conns files in precedence order: --core-conns; the plan's own dir (materialised HBM plan dirs carry
    core_conns.json beside die_plan.json); the --ref-dirs, newest (last) first; the die dir. .json or .json.gz."""
    if path:
        return [Path(path)]
    dirs = ([Path(plan_dir)] if plan_dir else []) + [Path(d) for d in reversed(list(ref_dirs))] + [Path(die_dir)]
    out, seen = [], set()
    for d in dirs:
        for n in ("core_conns.json", "core_conns.json.gz"):
            f = d / n
            if f.is_file() and f.resolve() not in seen:
                seen.add(f.resolve())
                out.append(f)
                break
    return out


def load_conns(die_dir, path=None, plan_dir=None, ref_dirs=()):
    """{type: {core: {port: [dest]}}}, merged per type: the first source (conns_sources order) that lists a type wins.
    Sets _CONNS_SRC[type] = file."""
    out = {}
    _CONNS_SRC.clear()
    _FANOUT.clear()
    _UNREAL.clear()
    for f in conns_sources(die_dir, plan_dir, ref_dirs, path):
        try:
            d = read_json(f)
        except (OSError, ValueError):
            continue
        top = d
        if isinstance(d, dict) and isinstance(d.get("core_conns"), dict):
            d = d["core_conns"]
        for t, v in (d or {}).items():
            if t not in out and isinstance(v, dict):
                out[t] = v
                _CONNS_SRC[t] = str(f)
        # S81-PLANMODEL-1 sidecar keys (s81_leaf_conns.py): real multi-sink nets and the plan stations the bound RTL lacks
        if isinstance(top, dict) and isinstance(top.get("core_conns"), dict):
            for key, dst in (("fanout_nets", _FANOUT), ("unrealised_stations", _UNREAL)):
                for t, v in (top.get(key) or {}).items():
                    dst.setdefault(t, v)
    return out


_CONNS_SRC = {}
_FANOUT = {}        # {type: [{name, kind, bits, pins: [[inst, port]..], glue_of: [[inst, port]..]}]}
_UNREAL = {}        # {type: {phantom: [{idx, conn, launch, capture, bits}]}}  (stscan format, bound depth 0)


def _names_core(dests, inst):
    """a core_conns destination list names core `inst` (core:<inst> or core_conns_from_bind's core:<inst>.<port>)."""
    c = "core:" + inst
    return any(d == c or (str(d).startswith(c + ".") and "." not in str(d)[len(c) + 1:]) for d in dests)


def _nf(r, d):
    p = r.get("porous", {}).get(d)
    if not p:
        return "-"
    return ">1" if p["need_free"] is None else p["need_free"]


# FLAG thresholds on the region p99 ratio, CALIBRATED on the controls (calib/README in the lane post): the RUDY model
# is close to measured GRT over hard cores and in streets between hard cores (the S81 M6 class), and over-predicts
# beside / over SRAM-ROM, in landing rings and in open area (signed / GRT-pass types reach ~2-3 there).
FLAG_AT = {"core": 1.0, "street": 1.0, "mstreet": 3.0, "mem": 3.0, "ring": 3.0, "open": 3.0, "face": 3.0,
           # std-cell density (synth cells incl. landing rings / um2 of outline not under a macro), not a track ratio:
           # QC slice types fail GRT on every layer from 0.424 (hc2) up, GRT-pass up to 0.413 (hc0) and 0.437 (st_b, 20
           # hard cores); measured on the kit synth_stat + 5_1_grt.log of 184 rows (PLAN-ROUTE-1 11-10)
           "dens": 0.42}


def _base_names(n):
    """type name, then the landing-cohort / sid bases it was derived from (x__clHASH__clHASH -> x__clHASH -> x)."""
    out = [n]
    while True:
        m = re.match(r"(.+?)(__cl[0-9a-f]{8}|__sid\w+|__v[0-9a-f]{6,})$", out[-1])
        if not m:
            return out
        out.append(m.group(1))


def load_cells(P, plan, die, measured_path):
    """type -> (cells, basis): measured kit synth (exact type, then cohort base), else cells.py plan estimate."""
    meas = {}
    try:
        meas = json.loads(Path(measured_path).read_text()).get(die, {})
    except (OSError, ValueError, AttributeError):
        pass
    est = {}
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import cells as C  # tools/die_plan/cells.py
        est, _ = C.estimate(P, plan_dir=plan.parent)
    except Exception as e:  # advisory: no estimate is not an error
        print(f"# cells.py estimate unavailable: {e}", file=sys.stderr)

    def get(n, has_cores=False):
        for b in _base_names(n):
            v = meas.get(b)
            if v and v.get("cells"):
                return int(v["cells"]), "measured synth " + (b if b == n else f"{b} (base of {n})")
        v = est.get(n)
        if has_cores:
            # plan / cells.py estimates are FLAT counts incl. the hard cores' own cells (measured synth counts the
            # type's top only, cores are black boxes): not a soft-area density, so not used
            return None, ("no measured synth; flat estimate incl. hard cores not used" if v and v[0] else None)
        if v and v[0]:
            return int(v[0]), "cells.py " + str(v[1])
        return None, None
    return get


def add_density(r, t, cb):
    cells, basis = cb
    w, h = t["outline_um"]
    soft = w * h * (1.0 - r.get("macro_area_frac", 0.0))
    r["cells"], r["cells_basis"], r["soft_um2"] = cells, basis, round(soft, 1)
    if cells and soft > 0:
        d = round(cells / soft, 4)
        r["regions"]["dens_A"] = {"p99": d, "max": d, "hot_bins": 0, "bins": 1}


def verdict(r, scale=1.0):
    """(FLAG|ok, [(region_dir, ratio/threshold)]) -- advisory."""
    hits = []
    for k, v in r["regions"].items():
        reg, d = k.rsplit("_", 1)
        t = FLAG_AT.get(reg, 3.0) * scale
        if v["p99"] >= t:
            hits.append((k, round(v["p99"] / t, 3)))
    hits.sort(key=lambda h: -h[1])
    return ("FLAG" if hits else "ok"), hits


def calib_fail(r, fail_p99=CALIB_FAIL_P99, hotspot_fail=CALIB_HOTSPOT_FAIL):
    """GRT-CALIB-1 (1): (FAIL?, reason) -- worst track-region p99 > fail_p99, or soft-cell density >= FLAG_AT dens.
    The region thresholds of FLAG_AT (3.0 for face/open/ring/mem) are NOT used here: measured GRT fails at any
    region p99 > 1 (calib.tsv, 11-11)."""
    worst = None
    hot = None
    for k, v in r["regions"].items():
        if k == "dens_A":
            continue
        if k.startswith("mhot_"):
            if hot is None or v["p99"] > hot[1]:
                hot = (k, v["p99"])
            continue
        if worst is None or v["p99"] > worst[1]:
            worst = (k, v["p99"])
    d = (r["regions"].get("dens_A") or {}).get("p99")
    if worst and worst[1] > fail_p99:
        return True, f"p99 {worst[1]:.3f} > {fail_p99:g} ({worst[0]})"
    if d is not None and d >= FLAG_AT["dens"]:
        return True, f"dens {d:.3f} >= {FLAG_AT['dens']} cells/um2"
    if hot and hot[1] > hotspot_fail:
        return True, f"macro hot spot {hot[1]:.3f} > {hotspot_fail:g} ({hot[0]} {r['regions'][hot[0]].get('inst', '')})"
    return False, (f"p99 {worst[1]:.3f} <= {fail_p99:g} ({worst[0]})" if worst else "no region")


def _station_lint():
    try:
        import station_lint as sl
    except ImportError:                      # python3 -I does not put the script dir on sys.path
        import importlib.util
        spec = importlib.util.spec_from_file_location("station_lint", Path(__file__).resolve().parent / "station_lint.py")
        sl = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sl)
    return sl


_SCAN = {}


def load_station_scan(path):
    """stscan --detail JSON (VIS-TRIAGE-HBM stscan.py: plan internal_stations vs the bound netlist): {type: {phantom:
    [{idx, conn, launch, capture, bits}], ...}}.  Cached per path."""
    if path not in _SCAN:
        _SCAN[path] = json.loads(Path(path).read_text())
    return _SCAN[path]


def drop_phantoms(tn, t, scan):
    """t with the bind-PHANTOM internal_stations removed (the plan station's endpoint pair has no bound connection,
    DIE-HBM-98 S7 class): kits do not build them, so they are not wire.  Records match on idx + conn, else on
    (conn, launch, capture).  Returns (t', dropped, dropped_bits, unmatched)."""
    rec = (scan.get(tn) or {}).get("phantom") or []
    st = list(t.get("internal_stations") or [])
    if not rec or not st:
        return t, 0, 0, 0
    key = lambda e: (str(e.get("conn", "")), str(e.get("launch", "")), str(e.get("capture", "")))
    by_key = defaultdict(list)
    for i, e in enumerate(st):
        by_key[key(e)].append(i)
    drop, unmatched = set(), 0
    for r_ in rec:
        i = r_.get("idx")
        if isinstance(i, int) and 0 <= i < len(st) and str(st[i].get("conn", "")) == str(r_.get("conn", "")):
            drop.add(i)
            continue
        c = [j for j in by_key.get(key(r_), []) if j not in drop]
        if c:
            drop.add(c[0])
        else:
            unmatched += 1
    bits = sum(int(st[i].get("bits", 1) or 1) for i in drop)
    return dict(t, internal_stations=[e for i, e in enumerate(st) if i not in drop]), len(drop), bits, unmatched


def score_rows(T, names, die_dir, repo, conns, cfg, cells_of, flag_ratio, maps=False, out=None, die=None):
    """route_supply rows (verdict, flag regions, fix) for the named types of partition_types T."""
    rows = []
    for n in names:
        t = T[n]
        if not t.get("outline_um"):
            continue
        ph = None
        if cfg.get("station_scan"):
            t, nd, nb, nu = drop_phantoms(n, t, load_station_scan(cfg["station_scan"]))
            ph = dict(phantom_stations_dropped=nd, phantom_bits_dropped=nb, phantom_unmatched=nu)
        r = analyze_type(n, t, die_dir, repo, conns, cfg)
        if r is None:
            continue
        add_density(r, t, cells_of(n, bool(t.get("hard_cores"))))
        if ph is not None:
            r.update(ph)
            if ph["phantom_stations_dropped"]:
                r.setdefault("notes", []).append(
                    f"PHANTOM {ph['phantom_stations_dropped']} plan station(s) / {ph['phantom_bits_dropped']} b with no "
                    f"bound path dropped (--station-scan)" + (f", {ph['phantom_unmatched']} scan rows unmatched"
                                                              if ph["phantom_unmatched"] else ""))
        r["verdict"], r["flag_regions"] = verdict(r, flag_ratio)
        if r["verdict"] != "FLAG" and r.get("unchecked_pins"):
            r["verdict"] = "UNCHECKED"          # scored demand is under threshold but some core pins were not scored
        if cfg.get("verdict_mode") == "calib":
            # GRT-CALIB-1 (1): p99 > 1 (or dens) is the FAIL class; FLAG regions stay as the fix hint
            fail, why = calib_fail(r, cfg.get("fail_p99", CALIB_FAIL_P99), cfg.get("hotspot_fail", CALIB_HOTSPOT_FAIL))
            r["verdict_flag"] = r["verdict"]
            r["calib_reason"] = why
            r["verdict"] = "FAIL" if fail else ("UNCHECKED" if r["verdict"] == "UNCHECKED" else "ok")
        # S1/S2 station-direction lint (COORD S7, DIE-KV-97 kv3_phy o_phy_Q): chains whose kit stage order runs
        # against the bus data flow; reported per type, never changes the verdict
        sl = _station_lint().lint_type(n, t)
        r["station_inverted"] = [f"{x['chain']}:{x['name']}#{x['index']}" for x in sl if x["kind"] == "INVERTED"]
        r["station_nonmonotone"] = sum(1 for x in sl if x["kind"] == "NONMONOTONE")
        if r["station_inverted"]:
            r.setdefault("notes", []).append(
                f"STATION-INVERTED {len(r['station_inverted'])} chain(s): " + ", ".join(r["station_inverted"][:6])
                + (" ..." if len(r["station_inverted"]) > 6 else ""))
        if r["flag_regions"]:
            reg, d = r["flag_regions"][0][0].rsplit("_", 1)
            r["fix"] = FIX.get((reg, d), r["fix"])
            r["fix_region"] = r["flag_regions"][0][0]
        maps_ = r.pop("_maps")
        for k_ in ("_sup", "_bin", "_rec"):
            r.pop(k_, None)
        if maps and out:
            Path(out).mkdir(parents=True, exist_ok=True)
            np.savez_compressed(Path(out) / f"{die}__{n}.npz", rH=maps_[0], rV=maps_[1],
                                cls=np.array(maps_[2], dtype="U6"), bin_um=cfg["bin_um"])
        rows.append(r)
    return rows


def _merge(base, patch):
    """deep merge: dicts merge; a dict patch onto a list of dicts merges by inst/name key (null deletes, new keys
    append); anything else replaces."""
    if isinstance(base, dict) and isinstance(patch, dict):
        out = dict(base)
        for k, v in patch.items():
            if v is None:
                out.pop(k, None)
            else:
                out[k] = _merge(base.get(k), v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(patch, dict) and all(isinstance(x, dict) for x in base):
        key = "inst" if any("inst" in x for x in base) else "name"
        out, seen = [], set()
        for x in base:
            kx = x.get(key)
            if kx in patch:
                seen.add(kx)
                if patch[kx] is None:
                    continue
                out.append(_merge(x, patch[kx]))
            else:
                out.append(x)
        for kx, v in patch.items():
            if kx not in seen and v is not None:
                out.append(dict(v, **{key: kx}) if isinstance(v, dict) else v)
        return out
    return patch


def apply_delta(T, D):
    """partition_types after a candidate delta (see --delta)."""
    import copy
    T2 = copy.deepcopy(T)
    if isinstance(D, list):
        rows = D
        D = {}
        for r in rows:
            r = dict(r)
            tn = r.pop("type")
            ins = r.pop("inst", None)
            if ins is None:
                D.setdefault(tn, {}).update(r)
            else:
                D.setdefault(tn, {}).setdefault("hard_cores", {})[ins] = r
    else:
        D = D.get("partition_types") or D.get("types") or {}
    for tn, p in D.items():
        T2[tn] = _merge(T2.get(tn, {}), p) if tn in T2 else p
    return T2


def _dir_worst(r):
    out = {}
    for k, v in r["regions"].items():
        reg, d = k.rsplit("_", 1)
        if d in ("H", "V") and v["p99"] > out.get(d, ("", -1))[1]:
            out[d] = (reg, v["p99"])
    return out


def delta_report(before, after, die, plan, delta):
    hdr = ["die", "type", "verdict_before", "verdict_after", "bit_mm_before", "bit_mm_after", "worst_H_before",
           "worst_H_after", "worst_V_before", "worst_V_after", "p99_before", "p99_after", "flag_regions_after"]
    lines = ["\t".join(hdr)]
    rows = []
    for n in after:
        b, c = before.get(n), after[n]
        wb, wc = (_dir_worst(b) if b else {}), _dir_worst(c)
        f = lambda w, d: (f"{w[d][0]}:{w[d][1]}" if d in w else "-")
        row = dict(type=n, verdict_before=b["verdict"] if b else "new", verdict_after=c["verdict"],
                   bit_mm_before=b["wirelength_mm"] if b else None, bit_mm_after=c["wirelength_mm"],
                   worst_H_before=wb.get("H"), worst_H_after=wc.get("H"), worst_V_before=wb.get("V"),
                   worst_V_after=wc.get("V"), p99_before=b["worst"]["p99"] if b else None,
                   p99_after=c["worst"]["p99"], flag_regions_after=c["flag_regions"],
                   unchecked_pins_after=c.get("unchecked_pins"))
        rows.append(row)
        lines.append("\t".join(map(str, [die, n, row["verdict_before"], row["verdict_after"], row["bit_mm_before"],
                                         row["bit_mm_after"], f(wb, "H"), f(wc, "H"), f(wb, "V"), f(wc, "V"),
                                         row["p99_before"], row["p99_after"],
                                         ",".join(f"{k}:{v}" for k, v in c["flag_regions"]) or "-"])))
    return dict(schema=SCHEMA + ".delta", advisory=True, do_not_count=True, die=die, plan=str(plan),
                delta=str(delta), rows=rows, lines=lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--plan", dest="plan_opt", help="same as the positional PLAN")
    ap.add_argument("--delta", help="score a candidate delta: JSON {partition_types|types: {TYPE: {field: value, "
                                    "hard_cores|buses|ft_slots: {inst|name: {field: value}}}}} or a list of "
                                    "{type, inst, origin_um, orient, ...} rows; prints before/after per type")
    ap.add_argument("--die")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--types")
    ap.add_argument("--match")
    ap.add_argument("--out")
    ap.add_argument("--bin", type=float, default=DEFAULTS["bin_um"])
    ap.add_argument("--window", type=int, default=DEFAULTS["window"])
    ap.add_argument("--derate", default="")
    ap.add_argument("--core-ceiling", default=DEFAULTS["core_ceiling"])
    ap.add_argument("--cell-fill", type=float, default=DEFAULTS["cell_fill"])
    ap.add_argument("--ring-tracks-per-bit", type=float, default=DEFAULTS["ring_tracks_per_bit"])
    ap.add_argument("--ring-um2-per-flop", type=float, default=DEFAULTS["ring_um2_per_flop"])
    ap.add_argument("--detour-um", type=float, default=DEFAULTS["detour_um"])
    ap.add_argument("--station-spread", action="store_true",
                    help="what-if: station hops spread over the detour window (moves leaf V to H, 8/14 vs 6/15 FAIL "
                         "directions right, but loses leaf t24; off by default)")
    ap.add_argument("--calib-1111", action="store_true",
                    help="GRT-CALIB-1 calibrated feasibility model (COORD 'GRT calibration'): --verdict-mode calib + "
                         "--over-macro-m67 + --grt-halving %s unless --grt-halving is given" % CALIB_HALVING)
    ap.add_argument("--verdict-mode", choices=("flag", "calib"), default=None,
                    help="flag (default) = FLAG/ok by the FLAG_AT region thresholds; calib = FAIL when the worst "
                         "region p99 > --fail-p99 or dens_A >= %s (GRT-CALIB-1)" % FLAG_AT["dens"])
    ap.add_argument("--fail-p99", type=float, default=CALIB_FAIL_P99, help="--verdict-mode calib threshold")
    ap.add_argument("--macro-hotspot", choices=("pooled", "local"), default=None,
                    help="GRT-CALIB-2: add region mhot_H/V = max over hard cores of the windowed demand/supply over the macro "
                         "(pooled = the macro-run pooled ratio, local = the detour-window box ratio)")
    ap.add_argument("--hotspot-min-bins", type=int, default=4, help="--macro-hotspot: skip macros under this many bins")
    ap.add_argument("--hotspot-fail", type=float, default=CALIB_HOTSPOT_FAIL,
                    help="--verdict-mode calib: FAIL when mhot_H/V > this (GRT-CALIB-2: 1.0)")
    ap.add_argument("--calib-1112", action="store_true",
                    help="GRT-CALIB-2: --calib-1111 + --macro-hotspot local (per-macro hot spot FAIL > --hotspot-fail)")
    ap.add_argument("--over-macro-m67", action="store_true",
                    help="GRT-CALIB-1: over every hard core (kind core) M2-M5 carry nothing, only M6 H / M7 V")
    ap.add_argument("--grt-halving", choices=("full", "edge", "edge_outline", "none"), default=None,
                    help="OpenROAD transition-layer halving over macro OBS: full = stock image (adjustTransitionLayers "
                         "under the whole OBS); GRT-PATCH-1 patched images: edge = only within --grt-edge-gcells of "
                         "each OBS rect boundary (+ pins), edge_outline = only within K of the macro instance bbox "
                         "(+ pins); none = no halving")
    ap.add_argument("--grt-halving-type", action="append", default=[], metavar="TYPE=MODE",
                    help="per-type --grt-halving (full|edge|edge_outline|none|off; off = none, the OT_GRT_TRANSITION_MODE "
                         "name) for rows on the GRT-PATCH-1 halving-off parallel arm; repeatable; absent = --grt-halving")
    ap.add_argument("--grt-edge-gcells", type=int, default=2, help="K for --grt-halving edge / edge_outline (gcells of %.3f um)"
                    % GRT_GCELL_UM)
    ap.add_argument("--ft-internal-as-parent", action="store_true",
                    help="old model: an ft slot whose stations_in are hard cores still runs as parent wire over them")
    ap.add_argument("--template-cap-default", action="store_true",
                    help="old model: cap whole-block template LEFs at --core-ceiling even when the plan gives obs_max")
    ap.add_argument("--no-planmodel", action="store_true",
                    help="ignore the fanout_nets / unrealised_stations keys of the core_conns sidecar (its core_conns overrides still apply)")
    ap.add_argument("--station-scan", help="stscan --detail JSON (plan internal_stations vs the bound netlist): "
                    "PHANTOM stations (no bound path) are not scored as wire (DIE-HBM-98 S7, COORD 02:5x)")
    ap.add_argument("--station-face-double", action="store_true",
                    help="old model: a core pin whose face bus is carried by an internal_stations chain also counts "
                         "its own pin -> face net (counted twice)")
    ap.add_argument("--empty-conns-glue", action="store_true",
                    help="old model: an empty core_conns entry scores every pin as a local glue escape")
    ap.add_argument("--pin-escape", action="store_true",
                    help="what-if: 2-pin core links as an L whose first leg follows the pin face normal (off by default)")
    ap.add_argument("--margin-bins", type=int, default=DEFAULTS["margin_bins"],
                    help="bins beside a macro run pooled with it (the router's sideways detour off the macro)")
    ap.add_argument("--flag-ratio", type=float, default=1.0, help="scale on the calibrated FLAG_AT region thresholds")
    ap.add_argument("--core-conns")
    ap.add_argument("--core-fill", help="JSON {module: {fill, free_M4, free_M5, src}} measured by porous-abstract lanes")
    ap.add_argument("--ref-dirs", nargs="*", default=[],
                    help="extra dirs (relative to physical/die_plan) that plan-relative refs resolve against")
    ap.add_argument("--release-cache", default=os.path.expanduser(
        "~/.local/state/fleet-viz/release_tree_plan_cache.json"),
        help="release-tree plan cache: its signed_cores/signed_designs name the children with a signed view")
    ap.add_argument("--views", default=str(Path(__file__).with_name("route_supply_views.json")),
                    help="signed-view blocked-layer table (JSON {views: {module: {lef|obs_top, coverage, src}}})")
    ap.add_argument("--maps", action="store_true", help="write per-type ratio maps (npz)")
    ap.add_argument("--kit-views", default=str(Path(__file__).with_name("route_supply_kit_views.json")),
                    help="per-die macro OBS fractions of the kit macros/*.lef (used when the repo LEF is missing)")
    ap.add_argument("--cells", default=str(Path(__file__).with_name("route_supply_cells.json")),
                    help="measured synth cells {die: {type: {cells, src}}}; else tools/die_plan/cells.py estimates")
    a = ap.parse_args(argv)
    if a.calib_1112:
        a.calib_1111 = True
        a.macro_hotspot = a.macro_hotspot or "local"
    if a.calib_1111:
        a.verdict_mode = a.verdict_mode or "calib"
        a.over_macro_m67 = True
        a.grt_halving = a.grt_halving or CALIB_HALVING
    a.grt_halving = a.grt_halving or "full"
    a.plan = a.plan or a.plan_opt
    if not a.plan:
        ap.error("PLAN (positional or --plan) is required")
    repo = Path(a.repo).resolve()
    plan = Path(a.plan)
    if not plan.is_absolute():
        plan = repo / plan
    P = read_json(plan)
    REF_DIRS[:] = [str(plan.parent)] + [str(repo / "physical" / "die_plan" / r) for r in a.ref_dirs]
    die = a.die or (P.get("die") or {}).get("name") or plan.parent.name
    die_dir = repo / "physical" / "die_plan" / ({"s81_head": "s81_head"}.get(die, die))
    if not die_dir.is_dir():
        die_dir = plan.parent
    der = dict(DERATE)
    for kv in filter(None, a.derate.split(",")):
        k, v = kv.split("=")
        der[k] = float(v)
    cfg = dict(DEFAULTS, bin_um=a.bin, window=a.window, derate=der, core_ceiling=a.core_ceiling,
               cell_fill=a.cell_fill, ring_tracks_per_bit=a.ring_tracks_per_bit,
               ring_um2_per_flop=a.ring_um2_per_flop, detour_um=a.detour_um, margin_bins=a.margin_bins,
               pin_escape=a.pin_escape, station_spread=a.station_spread,
               ft_core_internal=not a.ft_internal_as_parent, template_cap_obs_max=not a.template_cap_default,
               empty_conns_unchecked=not a.empty_conns_glue, station_face_dedupe=not a.station_face_double,
               station_scan=a.station_scan, fanout=not a.no_planmodel,
               grt_halving=a.grt_halving, grt_edge_gcells=a.grt_edge_gcells,
               grt_halving_types=grt_halving_types(a.grt_halving_type))
    # GRT-CALIB-1 keys only when opted in, so the default cfg (and the JSON dump of it) stays byte-identical
    if a.over_macro_m67:
        cfg["over_macro_m67"] = True
    if a.macro_hotspot:
        cfg["macro_hotspot"] = a.macro_hotspot
        cfg["hotspot_min_bins"] = a.hotspot_min_bins
        if a.verdict_mode == "calib":
            cfg["hotspot_fail"] = a.hotspot_fail
    if a.verdict_mode == "calib":
        cfg["verdict_mode"] = "calib"
        cfg["fail_p99"] = a.fail_p99
    conns =load_conns(die_dir, a.core_conns, plan.parent, REF_DIRS[1:])
    cfg["signed_modules"] = None
    cfg["core_fill"] = {}
    if a.core_fill:
        cfg["core_fill"] = json.loads(Path(a.core_fill).read_text())
    try:
        rc = json.loads(Path(a.release_cache).read_text()).get("plans", {})
        for k, v in rc.items():
            if re.sub(r"\.gz$", "", str(plan)).endswith(re.sub(r"\.gz$", "", k)):
                cfg["signed_modules"] = set(v.get("signed_cores", {})) | set(v.get("signed_designs", {}))
    except (OSError, ValueError):
        pass
    try:
        cfg["views"] = json.loads(Path(a.views).read_text()).get("views", {})
    except (OSError, ValueError):
        cfg["views"] = {}
    try:
        cfg["kit_views"] = json.loads(Path(a.kit_views).read_text()).get(die, {})
    except (OSError, ValueError, AttributeError):
        cfg["kit_views"] = {}
    T = P.get("partition_types", {})
    cells_of = load_cells(P, plan, die, a.cells)
    names = list(T)
    if a.types:
        want = a.types.split(",")
        names = [n for n in names if n in want]
    if a.match:
        names = [n for n in names if re.search(a.match, n)]
    if a.delta:
        D = read_json(Path(a.delta))
        T2 = apply_delta(T, D)
        dn = [n for n in T2 if T2[n] != T.get(n)]
        names2 = [n for n in names if n in dn] if (a.types or a.match) else dn
        before = {r["type"]: r for r in score_rows(T, names2, die_dir, repo, conns, cfg, cells_of, a.flag_ratio)}
        after = {r["type"]: r for r in score_rows(T2, names2, die_dir, repo, conns, cfg, cells_of, a.flag_ratio)}
        out = delta_report(before, after, die, a.plan, a.delta)
        if a.out:
            od = Path(a.out)
            od.mkdir(parents=True, exist_ok=True)
            (od / f"route_supply_{die}_delta.json").write_text(json.dumps(out, indent=1))
        print("\n".join(out["lines"]))
        return 0
    rows = score_rows(T, names, die_dir, repo, conns, cfg, cells_of, a.flag_ratio, a.maps and a.out, a.out, die)
    rows.sort(key=lambda r: (r["verdict"] not in ("FLAG", "FAIL"), -(r["flag_regions"][0][1] if r["flag_regions"] else 0),
                             -r["worst"]["p99"]))
    hdr = ["die", "type", "verdict", "flag_regions", "worst_region", "dir", "layer", "p99_ratio", "max_ratio", "hot_bins",
           "at_um", "core_H", "core_V", "mem_H", "mem_V", "street_H", "street_V", "ring_H", "ring_V", "open_H",
           "open_V", "cells_per_um2", "cells", "macro_frac", "mem_frac", "model", "need_free_M4", "need_free_M5", "provisional_children", "fix",
           "station_inverted"]
    lines = ["\t".join(hdr)]
    for r in rows:
        w = r["worst"]
        reg = [r["regions"].get(k, {}).get("p99", "") for k in
               ("core_H", "core_V", "mem_H", "mem_V", "street_H", "street_V", "ring_H", "ring_V", "open_H", "open_V")]
        lines.append("\t".join(map(str, [die, r["type"], r["verdict"],
                                         ",".join(f"{k}:{v}" for k, v in r["flag_regions"]) or "-", w["region"], w["dir"], w["layer"], w["p99"],
                                         w["max"], r["hot_bins"], "%s,%s" % tuple(w["at_um"])] + reg +
                                    [r["regions"].get("dens_A", {}).get("p99", ""), r.get("cells") or "",
                                     r["macro_area_frac"], r["mem_area_frac"], r["model"],
                                     _nf(r, "H"), _nf(r, "V"),
                                     ",".join(r["provisional_children"]) or "-", r["fix"],
                                     len(r.get("station_inverted") or [])])))
    out = dict(schema=SCHEMA, advisory=True, plan=str(a.plan), die=die,
               cfg={k: (sorted(v) if isinstance(v, set) else v) for k, v in cfg.items()}, rows=rows)
    if a.out:
        od = Path(a.out)
        od.mkdir(parents=True, exist_ok=True)
        (od / f"route_supply_{die}.tsv").write_text("\n".join(lines) + "\n")
        (od / f"route_supply_{die}.json").write_text(json.dumps(out, indent=1))
    print("\n".join(lines))
    nflag = sum(1 for r in rows if r["verdict"] == "FLAG")
    nfail = sum(1 for r in rows if r["verdict"] == "FAIL")
    ninv = sum(len(r.get("station_inverted") or []) for r in rows)
    print(f"# {die}: station-direction lint {ninv} INVERTED chain(s) in "
          f"{sum(1 for r in rows if r.get('station_inverted'))} type(s) (station_lint.py; ADVISORY)", file=sys.stderr)
    print(f"# {die}: {len(rows)} types, {nflag} FLAG (region thresholds x{a.flag_ratio}; GRT halving "
          f"{a.grt_halving}{' K=%d' % a.grt_edge_gcells if a.grt_halving.startswith('edge') else ''}); ADVISORY, not a gate",
          file=sys.stderr)
    if a.verdict_mode == "calib":
        print(f"# {die}: GRT-CALIB-1 calib verdicts: {nfail} FAIL (worst region p99 > {a.fail_p99:g} or dens >= "
              f"{FLAG_AT['dens']}; over-macro M6/M7 only: {'yes' if a.over_macro_m67 else 'no'}); ADVISORY, not a gate",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
