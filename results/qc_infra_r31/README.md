# INFRA-FIRST-QC-R31 (2026-10-27 15:45-16:25 PDT): event NUMBER-CHECK + clock dry-build track allotment

Branch base = cbe5946d11 (exact dry14 builder source, Codex codex-qc-clock-r29-1351 lineage; it already contains the
allotment commits b2f6c09c10/116fbe3481 = rebased ae347e0de/a14a3bce5 and the 975d1b2ee index measured by f57cc46b0)
+ R30 results (cherry-pick of cc6d8023d8). Event plan = results/qc_infra_r30/event_n100_ft_leg.json.gz (sha dc6f65ad).

## 1. NUMBER-CHECK of the R30 152 FT island moves (independent checker, numcheck_leg_r30.py, own code)
CHECKED PASS: (a) whole-plan recursive diff: only ft_slots[].bit_sites_um change, exactly 152 cells, all = ledger, ledger
plan sha = file; (b) max displacement 3.78 um (2 cells), 58 at 0.81; (c) before 152 island / 0 macro hits, after 0 / 0 over
156,903 FT cells; (d) 0 FT/FT 2-D overlaps before and after, all on 0.27 rows / 0.054 sites, inside outline; (e) worst
bank-to-bank hop of a moved bit 375.84 -> 374.76 (worst over all bits of the 21 affected slots 380.7 before = after).
CAVEAT (pre-existing, not from the moves, not checked by R30 check_leg.py): pin -> bank0 hop worst 403.99 um
(coll_ftc crec_rx_s0, slot regs_um[0] taken as the pin) = 1 um under 405; with bits spread over the pin window the
first/last hop worst-case is 465.3 / 460.6 um (> 405). Needs a per-bit pin-window model in the FT gate (FT packet owner).
No render (numeric check only).

## 2-3. Dry build (die_clock_mesh build --explicit-cells, census mode) on the event plan, band8w dry14 clock_spec
| run | option | errors (all no_clock_track) |
|---|---|---|
| dry14 (Codex, dry14 plan) | input order | 1,796 |
| dry15a | route_order=gap_wide_first (Codex allotment ordering, opt-in, never enabled before) | 2,055 (worse: 408 M8 16w jogs) |
| dry15b | trunk_escape=true (new: window-full M8 trunks to the next PG gaps, M9 drop + M8 jog ends) | 1,680 |
| dry15c | trunk_escape=100 (trunks >= 100 um escape first) + tight jog/drop reservation | 1,179 |
| dry15d | trunk_escape=30 | 1,190 |
Root cause (CHECKED on dry14 spec, own script): the island pin window (+-2.455 um of the pin row) carries up to 6 parallel
same-row M8 trunks (5x 8w + 1x 16w, e.g. y 22394.88 x 2653: three band L chains b16_00/01/03 + row x-tree levels) where it
holds ~4-5 drawn 8w; ordering cannot fix over-subscription. dry15c remaining 1,179 = endpoint access at saturated islands:
escape jogs M8 at band tap elbows (b:*_tap_elbow 321+98 driver jogs), row trees 133, top t_b/t_m 108, escape M9 drops 211,
column-net driver jogs M8 4w 164 + drops 114. I.e. too many pins per island row window at the same x (band tap elbows =
W-edge feeds converging), a plan/export problem (cells of different nets must be on different rows / islands), not a
builder problem.
Source: tools/die_plan/die_clock_128.py opt-in meta.trunk_escape (spec key trunk_escape: true | span um), off by default;
29 focused clock tests PASS (test_explicit_clock_v2, test_clock128_r12, test_clock128_shield, test_qc_track_allotment).
Data: intel2:/srv/opentallas-scratch2/claude/qc-infra-r31/dry15{a,b,c,d} (+ src_r31b/src_r31c source snapshots).

## Next (not done): export-level per-island row allotment in qc_clk_mesh3 band_trees/orthogonal_lift (stack the band L
chains and tap-elbow cells of different nets on different rows / adjacent island columns so each pin window holds <= its
track count), then dry16 with trunk_escape=100 -> 0; then die GRT0 (>=50 it) and die_sta_related.py. No GRT/STA run.
