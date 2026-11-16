"""PG-AWARE-1 11-14 (FABLE-WAVE-REVIEW fix 6, FABLE-HARD-QCHEAD sections 2 and 5): pin access against the partition PG grid.

The partition PDN (gen_phys.PDN; type frame, pdngen offsets from CORE_AREA) draws VSS/VDD stripe pairs:
  M5 vertical   width 0.120, gap 0.072, pitch 4.32, pair centre 2.16 + 4.32 k
  M6 horizontal width 0.288, gap 0.096, pitch 4.32, pair centre 2.16 + 4.32 k
  M7 vertical   width 0.288, gap 0.096, pitch 8.64, pair centre 4.32 + 8.64 k (plan phase, OT_PG_DIE_PHASE=1) or
                0 + 8.64 k (the 4.32-um core margin without the phase fix); both phases are checked.
A routing track next to a stripe is legal only at half its wire width + the wide-metal spacing (0.072 next to a stripe
wider than 0.025, ASAP7 SPACINGTABLE) from the stripe edge.

Two pin rules (Fable's 630-kit scan rule is rule 1 for M7):
  1. DOWN ACCESS: an interior pin on a vertical layer (M7, M5) must hold, inside its y extent, a legal track of the
     horizontal layer below (M6 for M7; M4 has no PG) -- else no via can leave it downwards (QC su_l0 cland_tstart_in,
     HEAD hd_spn_end rst_start_raw_5, hd_host_e rst_start_raw_0/2: Rect Only DRC, DRT-0255).  Same for an interior M6 pin
     and the M5 tracks under its x extent.
  2. OWN TRACK: a pin's crossing coordinate must not lie on a spacing-illegal track of a same-layer stripe (QC sle_st_b_v2
     x_fw_ctl_p2_i[464] on the M7 VDD track).
safe_site moves a pin the least distance (along its own layer first: any along-coordinate is a legal site) so both hold.
"""
import math
import re

WIDE_SPACING_UM = 0.072
# layer: (horizontal, pitch, stripe width, pair gap, [pair centre phases])
STRIPES = {"M5": (False, 4.32, 0.12, 0.072, (2.16,)),
           "M6": (True, 4.32, 0.288, 0.096, (2.16,)),
           "M7": (False, 8.64, 0.288, 0.096, (4.32, 0.0))}
TRACKS = {"M4": (0.048, 0.024), "M5": (0.048, 0.024), "M6": (0.064, 0.032), "M7": (0.064, 0.032),
          "M8": (0.080, 0.040), "M9": (0.080, 0.040)}
WIRE_W = {"M4": 0.024, "M5": 0.024, "M6": 0.032, "M7": 0.032, "M8": 0.040, "M9": 0.040}
BELOW = {"M7": "M6", "M6": "M5"}      # the perpendicular PG layer a via down lands on (M5 -> M4: no partition PG)
HORIZ = {"M4": True, "M5": False, "M6": True, "M7": False, "M8": True, "M9": False}


def track_clear(layer, t, spacing=WIDE_SPACING_UM, phases=None):
    """True when a wire of `layer` centred on cross coordinate t keeps `spacing` from every PG stripe of that layer
    (phases: {layer: pair centre phases} overriding STRIPES, e.g. the one M7 phase a kit's pdn.tcl really draws)."""
    if layer not in STRIPES:
        return True
    _, pitch, w, gap, ph = STRIPES[layer]
    phases = (phases or {}).get(layer, ph)
    hw = WIRE_W.get(layer, 0.032) / 2
    half_pair = w + gap / 2              # pair spans centre +- half_pair
    for c in phases:
        d = (t - c) % pitch
        d = min(d, pitch - d)            # distance from the nearest pair centre
        # stripes occupy [gap/2, half_pair] on each side of the centre; the gap itself is no track either
        if d < half_pair + hw + spacing - 1e-9:
            return False
    return True


def tracks_in(layer, lo, hi, tracks=None):
    p, off = (tracks or TRACKS)[layer]
    k0, k1 = math.ceil((lo - off) / p - 1e-9), math.floor((hi - off) / p + 1e-9)
    return [round(off + k * p, 6) for k in range(k0, k1 + 1)]


def down_access(layer, x, y, along, tracks=None, phases=None):
    """rule 1: a legal below-layer track inside the pin's along extent (True for layers without PG below)."""
    b = BELOW.get(layer)
    if b is None:
        return True
    c = x if HORIZ[layer] else y          # along coordinate of the pin = cross coordinate of the layer below
    hw = WIRE_W[b] / 2
    return any(track_clear(b, t, phases=phases) for t in tracks_in(b, c - along / 2 + hw, c + along / 2 - hw, tracks))


def own_track(layer, x, y, phases=None):
    """rule 2: the pin's crossing coordinate is on a legal track of its own layer."""
    return track_clear(layer, y if HORIZ.get(layer, False) else x, phases=phases)


def pin_ok(layer, x, y, along, interior=True, tracks=None):
    return own_track(layer, x, y) and (not interior or down_access(layer, x, y, along, tracks))


def safe_site(layer, x, y, along, interior=True, tracks=None, extent=None, max_um=8.64):
    """(x, y) unchanged when pin_ok, else the nearest site that is: the along coordinate moves on the below layer's track
    pitch, the crossing coordinate on its own track pitch; ties go to the positive direction.  extent=(w, h) keeps the
    site inside [0.432, w - 0.432] x [0.432, h - 0.432].  Returns None when nothing within max_um passes."""
    if pin_ok(layer, x, y, along, interior, tracks):
        return x, y
    hz = HORIZ.get(layer, False)
    tr = tracks or TRACKS
    p_own = tr[layer][0]
    p_al = tr[BELOW[layer]][0] if BELOW.get(layer) else p_own
    cands = []
    na, nc = int(max_um / p_al) + 1, int(max_um / p_own) + 1
    for i in range(-na, na + 1):
        for j in range(-nc, nc + 1):
            da, dc = i * p_al, j * p_own
            q = (x + da, y + dc) if hz else (x + dc, y + da)
            q = (round(q[0], 4), round(q[1], 4))
            if extent is not None and not (0.432 <= q[0] <= extent[0] - 0.432 and 0.432 <= q[1] <= extent[1] - 0.432):
                continue
            cands.append((round(math.hypot(da, dc), 6), abs(j), -i, -j, q))
    for *_, q in sorted(cands):
        if pin_ok(layer, q[0], q[1], along, interior, tracks):
            return q
    return None


_PIN = re.compile(r"place_pin -pin_name \{?(\S+?)\}? -layer (M\d) -location \{([\d.\-]+) ([\d.\-]+)\} "
                  r"-pin_size \{([\d.]+) ([\d.]+)\}")


def kit_phases(pdn_text, core_area):
    """{layer: (pair centre phase,)} the kit pdn.tcl really draws (type frame): pdngen first stripe centre = core origin +
    offset, pair centre = that + (width + gap) / 2."""
    out = {}
    for m in re.finditer(r"add_pdn_stripe -grid \{top\} -layer \{(M[5-7])\} -width \{([\d.]+)\} -spacing \{([\d.]+)\} "
                         r"-pitch \{([\d.]+)\} -offset \{([\d.]+)\}", pdn_text):
        ln, w, gap, pitch, off = m.group(1), *(float(v) for v in m.groups()[1:])
        o = core_area[1] if HORIZ[ln] else core_area[0]
        out[ln] = (round((o + off + (w + gap) / 2) % pitch, 4),)
    return out


PIN_LAYER = "M7"   # pdn.tcl define_pdn_grid -pins {M7}: pdngen extends the M7 stripes to the die edge; M5/M6 stop at the core


def scan_io(io_text, outline, core_area=None, phases=None):
    """[(pin, layer, x, y, rule)] of io.tcl pins that break rule 2 (own track; M7 everywhere, as its stripes reach the die
    edge, M5/M6 inside the core) or rule 1 (down access, pins inside the core: the core margin has no M5/M6 stripes).
    core_area defaults to the 4.32-um partition margin."""
    w, h = outline
    cx0, cy0, cx1, cy1 = core_area or (4.32, 4.32, w - 4.32, h - 4.32)
    bad = []
    for m in _PIN.finditer(io_text):
        name, ln = m.group(1), m.group(2)
        x, y, sw, sh = (float(v) for v in m.groups()[2:])
        if ln not in STRIPES:
            continue
        along = sh if not HORIZ[ln] else sw
        inside = cx0 < x < cx1 and cy0 < y < cy1
        if (inside or ln == PIN_LAYER) and not own_track(ln, x, y, phases):
            bad.append((name, ln, x, y, "own_track"))
        elif inside and not down_access(ln, x, y, along, phases=phases):
            bad.append((name, ln, x, y, "down_access"))
    return bad
