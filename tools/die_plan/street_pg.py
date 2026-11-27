#!/usr/bin/env python3
"""street_pg.py -- PG-adjusted street track supply (C-STREET-R2, 11-26; opt-in, plan flag top-level `street_sizing: {pg: 1}`).

The stock street models use fixed supplies (adv_fp_floorplan TV/TH = raw M2-M8 tracks x 0.75 derate; street_rule K = 3 layers x 0.6
fill / 0.048).  Neither sees the partition PG stripe bands.  Codex S81 LEPW C (11-26): the MU_C XG aisle is 6.984 um at a stock
demand of 1.195; a street between macros carries the PG stripes of both neighbours, so the usable tracks per um are the raw
ones minus the schema.PART_PG_BANDS exclusion bands (M5 .264/4.32, M6 .48/4.32, M7 .48/8.64, M8 .66/4.32 half widths).
This module derives that loss from the band table (never a new constant).

  blocked_share(layer)      2 x half / pitch of the layer's band (0 for layers without one: M2, M3, M4)
  street_layer_loss()       mean blocked share over the three street layers M3/M5/M7 (used by street_rule: 3 layers x fill)
  tracks_per_um(direction)  raw tracks per um of the M2..M8 layers running in `direction` after the band exclusion
"""
import schema as S

LAYERS = (("M2", "H"), ("M3", "V"), ("M4", "H"), ("M5", "V"), ("M6", "H"), ("M7", "V"), ("M8", "H"))
STREET_LAYERS = ("M3", "M5", "M7")


def blocked_share(ln):
    b = S.PART_PG_BANDS.get(ln)
    if not b:
        return 0.0
    pitch, _cen, half = b
    return min(1.0, 2.0 * half / pitch)


def street_layer_loss():
    return sum(blocked_share(ln) for ln in STREET_LAYERS) / len(STREET_LAYERS)


def tracks_per_um(direction):
    pitch = {L["name"]: L["pitch_um"] for L in S.ASAP7_LAYERS}
    return sum((1.0 / pitch[ln]) * (1.0 - blocked_share(ln)) for ln, d in LAYERS if d == direction)


def raw_tracks_per_um(direction):
    pitch = {L["name"]: L["pitch_um"] for L in S.ASAP7_LAYERS}
    return sum(1.0 / pitch[ln] for ln, d in LAYERS if d == direction)


def pg_factor(direction):
    """usable / raw tracks of one street direction (V: streets run along y and use the vertical layers)."""
    return tracks_per_um(direction) / raw_tracks_per_um(direction)
