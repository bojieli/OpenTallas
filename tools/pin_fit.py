#!/usr/bin/env python3
"""Pin-placement settings of the reference route and the two models every gate uses on them (flowfix 2026-10-13).

ONE SOURCE OF TRUTH.  tools/ref_tile/ref_tile.py (job route command), tools/ref_tile/ref_route.sh (its default), the
pre-route gate (pre_route_gate.py: the --remote / --cts run, the local kit check and the closure loop's submit hook) and
the die-master submit lint (closure_loop/submit_lint.py) all read the constants and the models below, so a gate can no
longer pass a pin plan that the route then places differently.

1. PPL group fit (PPL-0093).  The route chunks every --pin-region into ordered groups of ROUTE_PIN_GROUP_MAX pins
   (run_abi3_physical OT_PIN_GROUP_MAX); the gate ran without it, i.e. with ONE group per region.  OpenROAD place_pins
   cuts a region into sections of PPL_SECTION_SLOTS slots (a slot = PIN_MIN_TRACKS tracks of the pin layer) and a group
   must sit inside ONE section on ONE layer.  A 200-slot section takes six 32-pin groups and strands 8 slots, so a face
   filled above ~96 % of its slots has no home for the last group.  Measured on the five PPL-0093 routes of 10-12/13
   (place_iop logs): sections 19.104 um long on M4 at two tracks, first slot 0.732 um from the corner, last 0.804 um
   before the far one, "Not enough available positions (8)" in every full section:
     qkd_seq_fan-kc2     W face 162.00 um, 1,623 pins: 8 x 6 + 2 = 50 groups of 32 fit, the 51st (23 pins) does not
     smh_pt_w_ref_p45h   W face 371.52 um, 3,705 pins: 115 groups fit, the last (25) finds 22 contiguous slots
   The model is a lower bound on the failure (PDN-blocked slots and other regions on the face are ignored): it never
   refuses a plan the placer could place.  Replay on the 1,101 ref_tile jobs of 10-12/13: it fails every job that
   died at 3_2_place_iop on a region plan (5 x PPL-0093, 5 x PPL-0111 "constraint does not have available slots",
   1 x PPL-0086 "pin group was not assigned") and no job that placed its pins.
2. Pin-flop spread of kit recipe 2 (GRT-0116 behind a dense face).  physical/qwen_die_masters/io_flop_at_pins.tcl
   derives the same gap / column count in the flow (constants OFLOP_* are duplicated there and checked by
   tools/closure_loop/test_pin_fit.py): hold stages take depth = pins per um x stage width x row height behind the
   face, the pin flops start behind them.  Working setting it reproduces: qkd_seq_fan-kc4, 10.4 b/um output face,
   OT_OFLOP_GAP 4.5 with 6 columns (kc3 with gap 1.0 / 4 columns failed global route by one track in 66 gcells).
"""
from __future__ import annotations

import math

# ----------------------------------------------------------------------------------------- route pin placement
ROUTE_PIN_GROUP_MAX = 32            # OT_PIN_GROUP_MAX of every ref_tile route (kit.env `export OT_PIN_GROUP_MAX=` wins)
PPL_SECTION_SLOTS = 200             # OpenROAD place_pins slots per section
PPL_FIRST_SLOT_UM = 0.732           # first slot from the face's low corner (measured, M4 / M5 at two tracks)
PPL_LAST_SLOT_UM = 0.804            # last slot before the high corner
PITCH = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064, "M8": 0.08, "M9": 0.08}
FIX_TEXT = ("give every bus its own disjoint pin_ranges and set route.pin_balance (place_pin, uniform over the range, "
            "no PPL groups), or a longer edge / a second pin layer")


def chunks(n: int, group_max: int) -> list:
    """sizes of the ordered groups a region of n pins is cut into (group_max 0 = one group)"""
    if n <= 0:
        return []
    if not group_max:
        return [n]
    q, r = divmod(n, group_max)
    return [group_max] * q + ([r] if r else [])


def slot_count(lo: float, hi: float, edge_len: float, slot_um: float) -> int:
    """slots of one layer inside [lo, hi] of a face of edge_len (slots sit at PPL_FIRST_SLOT_UM + k x slot_um)"""
    lo, hi = max(lo, PPL_FIRST_SLOT_UM), min(hi, edge_len - PPL_LAST_SLOT_UM)
    if hi < lo:
        return 0
    k0 = math.ceil((lo - PPL_FIRST_SLOT_UM) / slot_um - 1e-6)
    k1 = math.floor((hi - PPL_FIRST_SLOT_UM) / slot_um + 1e-6)
    return max(0, k1 - k0 + 1)


def section_bins(slots: int) -> list:
    """the sections place_pins cuts a run of slots into"""
    return [PPL_SECTION_SLOTS] * (slots // PPL_SECTION_SLOTS) + ([slots % PPL_SECTION_SLOTS] if slots % PPL_SECTION_SLOTS else [])


def pack(sizes: list, bins: list) -> list:
    """groups (sizes) that find no section (first-fit decreasing: at least as good as the placer's own order)"""
    free, left = list(bins), []
    for g in sorted(sizes, reverse=True):
        for i, f in enumerate(free):
            if f >= g:
                free[i] -= g
                break
        else:
            left.append(g)
    return left


def region_fit(n: int, lo: float, hi: float, edge_len: float, layers: list, tracks: float, group_max: int,
               balance: bool = False) -> dict:
    """{"fits", "why", "slots", "groups", "left"} for n pins of one --pin-region on [lo, hi] of a face, placed as the
    route places them: ordered groups of group_max on one of `layers` (PPL), or uniformly by place_pin (balance)."""
    span = hi - lo
    if n <= 0:
        return {"fits": True, "why": "", "slots": 0, "groups": 0, "left": []}
    if balance:
        k = len(layers) if group_max == 1 else 1            # layers alternate per chunk of group_max pins
        step = span / n * k
        need = max(PITCH.get(lay, 0.048) for lay in layers)
        ok = span > 0 and step >= need - 1e-9
        return {"fits": ok, "slots": 0, "groups": 0, "left": [] if ok else [n],
                "why": "" if ok else f"{n} balanced pins on {span:g} um = {step:.4f} um a pin on one layer < the "
                                     f"{need:g} um track pitch"}
    sizes = chunks(n, group_max)
    bins, slots, per_layer = [], 0, []
    for lay in layers:
        s = slot_count(lo, hi, edge_len, tracks * PITCH.get(lay, 0.048))
        slots += s
        per_layer.append(s)
        bins += section_bins(s)
    # a group larger than a section is placed in the placer's fallback mode: one contiguous run on one layer
    big = [g for g in sizes if g > PPL_SECTION_SLOTS]
    if big:
        left = [] if sum(big) <= max(per_layer, default=0) else big
    else:
        left = pack(sizes, bins)
    why = ""
    if left:
        why = (f"{n} pins = {len(sizes)} ordered groups of <= {group_max or n} on {slots} slots "
               f"({'+'.join(layers)} at {tracks:g} track(s), sections of {PPL_SECTION_SLOTS}): "
               f"{len(left)} group(s) of {max(left)}{'' if len(set(left)) == 1 else '..' + str(min(left))} pins find no "
               f"section ({n * 100 // max(slots, 1)} % of the slots used; a section strands "
               f"{PPL_SECTION_SLOTS % group_max if group_max else 0} slots)")
    return {"fits": not left, "why": why, "slots": slots, "groups": len(sizes), "left": left}


# ----------------------------------------------------------------------------------------- recipe-2 pin-flop spread
# duplicated in physical/qwen_die_masters/io_flop_at_pins.tcl (ot_au_*): test_pin_fit.py keeps the two equal
OFLOP_WIN_UM = 10.0          # sliding window along the face
OFLOP_ROW_UM = 0.27          # ASAP7 row height
OFLOP_DENSE_UM = 2.0         # hold-stage depth behind the face from which the flops are moved behind the stages
OFLOP_SLACK = 1.28           # legalised hold stages fill ~78 % of their rows (kc4: 3.52 um of cells -> x 2.2..6.7)
OFLOP_GAP_UM = 1.0           # the hook's default gap (sparse faces: unchanged)
OFLOP_COLS = 4               # the hook's default staggered columns
OFLOP_COLS_V = 2.0           # W / E face: columns = 2 x pin flops per row
OFLOP_COLS_H = 1.5           # N / S face: rows = 1.5 x pin flops per flop pitch
OFLOP_FF_PITCH_UM = 1.28     # DFFHQNx1 1.08 um + the hook's 0.2 um column gap
OFLOP_DEPTH_MAX = 0.45       # hold stages + flop band may take this share of the core behind the face
STAGE_OUT_UM = 1.242         # outhold: BUFx4f 0.432 + HB4xp67 0.378 + BUFx4f 0.432
STAGE_IN_UM = 0.81           # inhold: HB4xp67 0.378 + BUFx4f 0.432 (0.378 without the driver)


def face_density(n: int, span: float, layers: list, tracks: float, balance: bool) -> float:
    """pins per um over the densest OFLOP_WIN_UM of a region (lower bound), counted as the hook counts them (pins
    inside a window): a PPL region packs at the slot pitch of its coarsest layer, a balanced one is uniform"""
    if n <= 0:
        return 0.0
    step = span / n if balance else tracks * max(PITCH.get(lay, 0.048) for lay in layers)
    if step <= 0:
        return n / OFLOP_WIN_UM
    return min(n, math.floor(OFLOP_WIN_UM / step + 1e-9) + 1) / OFLOP_WIN_UM


def oflop_plan(density: float, stage_um: float, vertical: bool, cols: int | None = None) -> dict:
    """what io_flop_at_pins.tcl derives for a face with `density` anchored pins per um whose hold stage is stage_um wide
    (vertical: a W / E face).  cols: the kit's OT_OFLOP_COLS (a floor)."""
    depth = density * stage_um * OFLOP_ROW_UM
    base = cols or OFLOP_COLS
    if depth < OFLOP_DENSE_UM:
        return {"dense": False, "depth": round(depth, 2), "gap": OFLOP_GAP_UM, "cols": base, "band": 0.0}
    gap = max(OFLOP_GAP_UM, round(depth * OFLOP_SLACK, 1))
    if vertical:
        need = math.ceil(OFLOP_COLS_V * density * OFLOP_ROW_UM - 1e-9)
        pitch = OFLOP_FF_PITCH_UM
    else:
        need = math.ceil(OFLOP_COLS_H * density * OFLOP_FF_PITCH_UM - 1e-9)
        pitch = OFLOP_ROW_UM
    c = max(base, need)
    return {"dense": True, "depth": round(depth, 2), "gap": gap, "cols": c, "band": round(gap + c * pitch, 2)}
