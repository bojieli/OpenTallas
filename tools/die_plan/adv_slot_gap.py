"""ADV-SLOT-GAP and ADV-CHANNEL-WIDTH (FP-CONVERGE-S81 11-25, COORD 05:0x; WARN only, never a gate, every die).

SLOT-GAP       two hard cores of a type face each other across a gap g with 0 < g < SLOT_MIN_UM (28 um) over >= MIN_FACE_UM of
               common facing length: too narrow for a street (no repeater, no tap, no pin escape) yet not abutted.  Fable review of
               S81 c9s: 3.78 / 6.17 / 8.64 um slots on iq_C, leaf t10, kv_leaf t5, col_h9_r1, svc_lo/hi, dsdv_*_C.  Fix = abut to 0
               (pins on the outer faces only) or open to >= 28 um.
CHANNEL-WIDTH  a facing gap g <= CHAN_MAX_UM (200) over >= CHAN_MIN_FACE_UM (50) carries the bits of every station chain with a
               register inside the gap strip; needed width = bits / (tracks_per_um * SUPPLY_FRAC), tracks_per_um = the sum 1/pitch
               of the ASAP7 routing layers running along the channel (adv_route_demand._sup(0), as ADV-CHANNEL-PILE, which rates only cb* quad types) (V layers M3/M5/M7 for a vertical channel,
               H layers M4/M6/M8 for a horizontal one; adv_route_demand.LAYERS), SUPPLY_FRAC = adv_route_demand.SUPPLY_FRAC (0.5).
               Warns when g < needed.  Each chain counts once (its bits), not once per register stage.
               S81 c9s leaf t10 vn_a/vn_b: 30,331 bits in a 59-um channel; iq_C u_cap W margin 34.6 um with ~2,200 bits."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402
import adv_route_demand as RD  # noqa: E402

SLOT_MIN_UM = 28.0
MIN_FACE_UM = 10.0
CHAN_MAX_UM = 200.0
CHAN_MIN_FACE_UM = 50.0
MAX_EX = 4


def _w(check, *parts):
    return f"WARN ADV-{check} " + " ".join(str(p) for p in parts)


def facing_pairs(t, max_gap):
    """-> [(gap, axis, face_len, rectA, rectB, strip)] hard-core pairs facing across 0 < gap <= max_gap (axis 'x' = vertical channel)"""
    rs = G.hard_rects(t)
    out = []
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            for lo, hi in ((a, b), (b, a)):
                gx = hi[0] - lo[2]
                oy = min(lo[3], hi[3]) - max(lo[1], hi[1])
                if 0 < gx <= max_gap and oy > 0:
                    out.append((gx, "x", oy, lo, hi, (lo[2], max(lo[1], hi[1]), hi[0], min(lo[3], hi[3]))))
                gy = hi[1] - lo[3]
                ox = min(lo[2], hi[2]) - max(lo[0], hi[0])
                if 0 < gy <= max_gap and ox > 0:
                    out.append((gy, "y", ox, lo, hi, (max(lo[0], hi[0]), lo[3], min(lo[2], hi[2]), hi[1])))
    return out


def slot_gaps(t, slot_min=SLOT_MIN_UM, min_face=MIN_FACE_UM):
    """[(gap, face_len, nameA, nameB, axis)] gaps strictly between 0 and slot_min facing over >= min_face"""
    return sorted((round(g, 3), round(f, 1), a[4], b[4], ax) for g, ax, f, a, b, _ in facing_pairs(t, slot_min)
                  if 0 < g < slot_min - 1e-6 and f >= min_face)


def tracks_per_um(axis):
    """routing tracks/um along a channel: vertical channel ('x' gap) = V layers above M2, horizontal = H layers"""
    h, v = RD._sup(0)               # same supply model as ADV-ROUTE-DEMAND / ADV-CHANNEL-PILE (all layers above M1 = level 0)
    return v if axis == "x" else h


def chain_bits_in(t, strip):
    """bits of the station chains with >= 1 register inside strip (each chain once)"""
    x0, y0, x1, y1 = strip
    tot = 0
    for s in t.get("internal_stations") or []:
        try:
            bits = int(s.get("bits") or 0)
            regs = s.get("regs_um") or []
        except (TypeError, ValueError, AttributeError):
            continue
        if any(x0 <= float(p[0]) <= x1 and y0 <= float(p[1]) <= y1 for p in regs if isinstance(p, (list, tuple)) and len(p) >= 2):
            tot += bits
    return tot


def channel_findings(t, max_gap=CHAN_MAX_UM, min_face=CHAN_MIN_FACE_UM):
    """[(gap, needed_um, bits, face_len, nameA, nameB, axis)] facing gaps narrower than the width their station bits need"""
    out = []
    for g, ax, f, a, b, strip in facing_pairs(t, max_gap):
        if f < min_face:
            continue
        bits = chain_bits_in(t, strip)
        if not bits:
            continue
        need = bits / (tracks_per_um(ax) * RD.SUPPLY_FRAC)
        if g < need:
            out.append((round(g, 2), round(need, 1), bits, round(f, 1), a[4], b[4], ax))
    return sorted(out, key=lambda r: r[0] - r[1])


def _types(raw):
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if isinstance(t, dict) and t.get("hard_cores"):
            yield tn, t


def slot_gap(raw, plan_path, tree=None, **_kw):
    out, n = [], 0
    for tn, t in _types(raw):
        v = slot_gaps(t)
        if not v:
            continue
        n += 1
        ex = "; ".join(f"{a}|{b} {g} um x {f} um" for g, f, a, b, _ in v[:MAX_EX])
        out.append(_w("SLOT-GAP", tn, f"{len(v)} gap(s) 0 < g < {SLOT_MIN_UM:g} um (abut to 0 or open to >= {SLOT_MIN_UM:g}):", ex))
    return out + [_w("SLOT-GAP", f"summary {n} of {sum(1 for _ in _types(raw))} types with a sub-{SLOT_MIN_UM:g} um slot (report only)")]


def channel_width(raw, plan_path, tree=None, **_kw):
    out, n = [], 0
    for tn, t in _types(raw):
        v = channel_findings(t)
        if not v:
            continue
        n += 1
        ex = "; ".join(f"{a}|{b} {g} um < {need} um for {bits} bits ({f} um long, {ax})" for g, need, bits, f, a, b, ax in v[:MAX_EX])
        out.append(_w("CHANNEL-WIDTH", tn, f"{len(v)} channel(s) narrower than bits/(tracks/um x {RD.SUPPLY_FRAC}):", ex))
    return out + [_w("CHANNEL-WIDTH", f"summary {n} types with an under-width channel (report only)")]


findings = G._safe("SLOT-GAP", slot_gap)
findings_channel = G._safe("CHANNEL-WIDTH", channel_width)
