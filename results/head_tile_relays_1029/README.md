HEAD existing-stage corridor placement, trial only
================================================

The original current hd_tile placement has929register captures beyond405um.
Parent pass-through relocation (512x_q,511xo_q plus sharedu_x.line[255]alias)
fixes491bout destinations but leaves671captures, including new internal u_x
feedback reach. This candidate follows the full sequential-neighbour graph
through combinational logic, including every reset input, in both directions.
It moves2388EXISTING payload/control/strap flops into legal macro corridors;
no RTL, cycle, pin, macro placement or clock topology changes.

Measured placement-only successor (own epyc2 unit3481684-1793258070):
-2388targetedFFs fixed; DPL negotiation0overlaps; check_placement PASS;
 max DPL movement4.8um (other movable cells).
-Full post-legalization census671->29captures>405um, max502.5um.
-All remaining29are START/control/reset reach (see actual_census.json):
 s2 to W ring-reader states, plus rawreset to E fstart/ready/fault exports.
 The moved u_x/ad1/res/row0/enable families have no remaining capture failure.
-FAIL remains, no route/STA/freeze. Source-state exportcopy is under separate
 opt-in codex/head-startcopy-1029. Existing raw relay u_cland_rst_i can also move
 from351,362to354,500without changing its depth, avoiding a reset netlist edit.
 Fresh reg_spine sink assignment is required because the flops moved.

First own pilot3270832failed8'not in rows' atad1fixedcells. Cause: dbRows
still exist inside the die's reserved island placement blockages. The helper
now excludes getBlockages as well as hard macros and FIRM/LOCKED/COVER cells;
second pilot3481684passed. Original relay_fixed_fail_rows.odb and logs retained.

Own remote data: epyc2:/srv/opentallas-scratch2/claude/codex-head-relays-1029,
relay_dpl.odb/geom.tsv. Parent ODB is mounted read-only and never modified.
Original auto_geom.png and targets.png personally viewed; GEOM_REVIEW.md records
the conditional placement-only review. No signal routing or timing was run.

Production regeneration path (still trial/unqualified):
`head_tile_relay_kit.py KIT --targets TARGETS.tsv --banks HEAD_TILE_BANKS.tcl`
copies reviewed placement source and appends the hook after the generated face
and landing placements. It does not patch an ODB. Re-running is idempotent.
The parent owns head_tile_banks.tcl (efcbc8b737); this tool never edits it.
Use targets.tsv only to reproduce the29-failure diagnostic. The separate
 targets_copy_pending.tsv includes the additional existing raw-reset relay and
repositioned origin states for the new copy, but still needs the fresh synthesized
export-copy name and complete new-netlist census before any placement trial.

Production-hook integration updates:
-Helpers execute at global Tcl scope (PRE_GPL may call the hook inside a proc).
-Pack after the actual ring FFs but BEFORE the GPL-only landing-band reservation.
 The latter then protects both fixed landing/capture stages and is released
 normally before DPL; no hard clock/island reservation is removed.
-`head_tile_prepare.tcl` clears ONLY this source layout's own bank/target FFs
 before allocation. Actual3412-cell bank+relay hook repeated twice gave EXACT
 same positions/orientations/statuses,0differences (unit177380).
-Repack AGAIN after GP/resizer, in face_flops_release.tcl before DPL. Fresh GP
 resized FIRM DFFx1(width1080DBU)toDFFx2(width1134), causing74overlaps already
 present in3_4_resized (example pair u_bin138/481 overlaps54DBU); actual-width
 repacking fixed them, DPL/improve/mirroring/check PASS (unit341736).
-Fresh full-source placement then has10captures>405,max454.36, ALL result
 res_bits/res_row to held o_bits/o_row newly placed by GPL nearE/y640. Complete
 49-bit held-result stage is now planned at upper crossbar510,717, no pin/cycle
 changes; newgraph estimate0fails/max401.19. DPL-only successor439324 is running
 on the completed3_4 checkpoint (no GPL repeat), using targets_copy_result.tsv.
-Fresh reg_spine assignment AND built START-input timing remain required. Current
 sample S0/SF moves into the central channel; its actual input wire must be
 measured before freeze. An offline alternative keeps first samplers and all
 output FFs at original sites and uses M6/M7 over M5-only macro OBS (confirmed
 actualA/BLEFs), max395.12 estimate; not built, current job not interrupted.

All failed stage logs/JSON and old10-failure ODB retained under remote history/.
No route/CTS/STA or sign-off claim has been made.

Final actual source-integrated placement (2026-10-29 01:50 PDT):
- DPL successor439324 exit0; row/site/overlap/edge/padding checks all0.
- Actual dump478387:0/27665captures>405um,max400.95um,combloops0.
- `final_place_census.json` and VIEWED `final_place.png` reflect actual3_place,
  not target estimates. `targets_copy_result.tsv` is the final2440-target table.
- ODB: epyc2:/srv/opentallas-scratch2/claude/codex-head-startcopy-1029/tile/run/results/asap7/dp_hd_tile/base/3_place.odb
- Dump: epyc2:/srv/opentallas-scratch2/claude/codex-head-startcopy-1029/placed_geom.tsv
- Independent GEOM review requested. Fresh reg_spine assignment, actual built
  pin-to-S0 input timing/CA, clock closure and later routing remain HEAD lead work.
