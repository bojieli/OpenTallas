HEAD hd_tile clock pad-site legality fix (DIE-HEAD-22, 2026-10-29 02:44 PDT). Plan only; no CTS/GRT; no timing claim.

Defect: reg_spine.py snap_out clears only the tap DRIVER point; reg_spine.tcl abuts the pad chain to the left in one row.
Audit (audit.py vs actual 3_place.odb rows/macros(+2.16um row cut-back)/die-island blockages, dumped blk.tsv) of the
committed ca2607c93 plan: 45 illegal rects on taps 4,9,14,33,35,37,38,43 (before_audit.txt). Codex's 26 counted
macro/outside-core only and missed the die-island rows at tap 9 (y 349.92-358.56).

Fix (opt-in spec key tap_footprint, default output byte-identical): legalize_tap_footprints moves a tap to the nearest
point where its WHOLE pad+driver footprint is legal, or FOLDS the same chain onto consecutive rows (optional 6th tap
field pad_xy, consumed by reg_spine.tcl). head_tile_clock_plan.py --footprint iterates pads<->positions to a fixed point.
Result: 333 pads (unchanged), 45 taps, max radius 97.225 <= 100, predicted TT 512.97-544.76 / FF 406.66-432.04 (unchanged).
Folded in place: 4,9,37,38,43; 14 moved +2.97um x and folded; 17/35/40/42 moved <=0.54um. Remaining audit: 1 overlap of
tap33 pad11 with a FIXED std cell (DPL-legalizable, not a macro/row/island fault). fold.png VIEWED.
In-flow reg_spine.py on the same sinks reproduces this plan except tap18 y 717.80 vs 717.79 (pre-existing rounding diff,
identical in the default form).
Next: install in hd_tile kit (reg_spine.json from here), independent clock G1, then diagnostic CTS/GRT both corners.
