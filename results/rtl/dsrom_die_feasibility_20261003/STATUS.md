# DSROM die-level feasibility (Claude) -- STATUS, handed over to Codex (Maxwell/Archimedes) 2026-10-03

Branch: claude/dsrom-die-feasibility-20261003 (tool: tools/dsrom_die_feasibility.py, commit fbb69bffd + handover commit)
EPYC worktree: /srv/opentallas-scratch/claude/dsrom-die-feas/wt (pinned fbb69bffd); runner jobs/run_grt.sh

## Running (detached; leave alone)
- runs/C_local_k16: docker dsfeas-C_local_k16. Bundled (k=16) top-level GRT of the literal parent map
  (dsrom_noECC_complete_parent_map_20261002/r2), q frame C 510.84x126.9, return tree nodes local in the field channels.
- runs/C_band_k16: docker dsfeas-C_band_k16. Same, return tree nodes in the DECLARED_RETURN_FF50 band
  (every pair leaf runs vertically to the band, as the map's storage placement implies).
  Each writes grt.log (GRT-0096 per-layer congestion), gcell_usage.txt, wirelength.csv, grt.odb, exit_code.
  Case: 22,615 instances, 140,412 bundle nets, 1.99 M wires (manifest.json per run).

## Queued: none.

## Results so far (python legality screen, tools/dsrom_die_feasibility.py analyse; seconds)
- 16,409 instances (2,048 element frames, 14,336 cfg ROMs, bands/services/capture home/stage PHYs) all inside
  the 33x26 mm die, zero overlaps, for frame C AND enlarged frame D (510.84x151.2 fits the 166.32 um row pitch).
- FAIL as mapped: 1,982 of 2,048 element origins are off the 54 nm site grid and/or 48 nm M5 track
  (only 66 on the joint grid) -> element M5 edge pins would be off-track (the DRT-0419/0255 class).
  Smallest fix: snap element x origins down to the 432 nm joint grid; min same-row gap 8.64 -> 8.42 um, still 0 overlaps.
- cfg ROMs (v2 38.04x62.952 in 47.52x73.44 slots): all 14,336 on site/row grid, M4 pins on track (R0).
- Map gaps (not placed in the parent map): PAR2 UCIe PHY, TP4 collective PHYs, HBM PHYs; tool assumes
  UCIe x11-17 mm / collectives x17.5-23 mm on the north edge (0.5 mm strips).

## Next steps
1. Parse GRT logs (per-layer overflow, local vs band; v41_die.parse_log/congestion_map reusable); record into
   results/rtl/dsrom_die_feasibility_20261003/ with REPLAY.md.
2. Repeat GRT at frame D and k=8 (prepare --frame D / --k 8).
3. Not yet written: real-tech jobs (legal: OpenROAD containment/pin-on-track + pin_access with snapped origins;
   pdn: M8/M9 mesh over element M7 straps + cfg macro grid, PSM at 204 W with 90 um bumps; cts: 1.2 GHz trunk
   from die centre to elements/cfg/bands/services/capture-home relay sites, SS skew/insertion). Design notes are in
   the tool docstring; the main() placeholder for these jobs raises SystemExit.
