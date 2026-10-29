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
