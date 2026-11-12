# Per-type positions-only overlay (KIT-OVERLAY-1)

Fast path for a placement-only change inside ONE type: core positions/orients (hard_cores, placed contents) and
internal station sites, same type outline, same core outlines (CORE-SHAPE FREEZE: cores move or rotate only), same
ports/lanes/latency/RTL. No die plan event, no die-wide strict bind, no kit regeneration for other types.

    python3 -I tools/die_plan/type_overlay.py diff  BOUND_PLAN NEW_PLAN --type T --out OV.json   # or write OV.json by hand
    python3 -I tools/die_plan/type_overlay.py check BOUND_PLAN OV.json [--g0-full]
    python3 -I tools/die_plan/gen.py phys BOUND_PLAN --types T --type-overlay OV.json --kit-rtl T=FILELIST ... --out DIR

BOUND_PLAN is the die's last strict-bound plan; --kit-rtl is that bind's kit RTL for T (unchanged). Without
`--type-overlay` every kit is byte-identical to before (verified against origin/main). With it, only T's placement
files change (macro_place.tcl, pins/taps/stations as the moved sites dictate) and DIR/T/type_overlay.json records the base
and overlaid plan sha256.

## Why it is EQ by construction
Allowlist (anything else is rejected): hard_cores[*].{origin_um,orient,track_offset_um}, contents[*].{origin_um,orient},
internal_stations[i].{regs_um,bit_sites_um,leaf_um} with the same station count. Rejected: ports, buses, lanes, latency,
die, partitions, clock/reset declarations, any outline (type or core), module/params/pins/bind, other types.
bind.py/gen_rtl.py read core positions in exactly one place (CORE_SPLIT reset gate: nearest wavefront tap to the core
centre) and reset_tree reads core boxes as obstacles, so `rtl_projection` re-derives clock/core tap names, the reset tree
structure (coordinates stripped) and every gate-tap choice; any difference rejects the overlay (it is a plan event).

## Type-scoped validation
schema.scope_errors_typed: only this type's errors plus its partitions/ports/lanes (the old --types scope kept all die rows,
including other types' port and lane rows). Then collector_reach.type_findings (ERROR), seam_hop on the type's lanes
(no hop may newly exceed 405 um or worsen), and a G0 subset (check_types, core_pg, taps_cores, core_faces, geometry; `--g0-full`
runs all of check.run) that adds no ERROR naming the type or its lanes. `gen phys` without an overlay keeps the old
whole-plan `scope_errors` (unchanged); `--type-overlay` switches to the typed scope.

## How a signed overlay run becomes counted
1. The kit runs the normal flow to sign-off (signoff.py + post-route LEC) under the flow tag; the type is "signed on
   BOUND_PLAN + OV.json".
2. The die owner folds the same OV.json into its next plan event (apply `type_overlay.py apply BOUND_PLAN OV.json --out
   PLAN'`, or copy the values). The type's physical kit inputs are then identical to what was signed (same positions,
   same RTL), so the routed DB is valid for the new plan.
3. The count follows the existing RE-SIGN rule (OWNER 12.20, COORD 2026-10-30 02:03 (3b)): `tools/die_plan/resign.py run`
   re-runs sign-off and LEC on the SAME routed DB with the released flow tag's tools and writes the kind:resign
   PROVENANCE.json that the release counter reads. No second P&R. The autopilot form is `resign.py run --auto`
   (tools/autopilot/auto_resign.py). Until the owner's event contains the delta the overlay result stays "overlay-only".
