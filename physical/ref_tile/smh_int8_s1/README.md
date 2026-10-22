# smh_int8_s1 -- SM INT8 adapter hard tile, SAFE successor from source (H.STA.BLK.14.5, L2H-SMATT 10-19)
Top ot_smh_int8_tile_safe (Codex da40a2a46, imported unchanged; benches + mutant witnesses results/arch/hbm_int8_safe_source_1019/bench).
Outline 237.6 x 129.6 (= t1 geometry, accepted 121b7ec9a). Parallel twin smh_int8_s1 / smh_int8_s2; bind the first to close, cancel the other.
Why: t1/t2 (ot_smh_int8_tile) gated WARN util-only, but the source audit (b5d7898df) found 17 unsafe logical roots (pend fanout 85-110,
reset 87). Codex then tried an in-place clone ECO of a hand-placed checkpoint (FIRM orientation abort, 265 protected-growth overlaps):
dropped per LEAD2-HBM D4. This kit is a normal fresh flow run from the fanout-safe source: synthesis, placement, resizer buffering,
CTS and hold repair by the standard ref_tile recipe.
SAFE-DESIGN checklist (owner 10-19):
1 Pins: PASS -- every input registered in RTL (p_v kept copies / p_tag / p_codes), every output a flop Q (r_v/r_tag/r_data/r_sel);
  pin_regs OFF (would add a cycle). Reset: two sampled posedge stages IN RTL (kept reset_first -> 9 kept reset_final), flow landing OFF
  (same reset age as t1's 2-stage flow landing).
2 Reach: PASS -- outline < 240 um wide; every path pin->flop->flop->pin < 405 um.
3 Fanout: FIXED -- 128 kept pend copies, input-valid copies <= 8 loads, reset copies <= 24; mapped max transparent fanout 24, 0 unsafe roots
  (t1 RTL 17 roots, max 87). Gate fanout census must confirm Yosys kept the copies.
4 Depth: PASS -- one ~12-level converter stage (t1 measured setup +99 ps TT).
5 Storage: PASS -- no storage > 2 kb (pipeline registers only).
6 Floorplan: PASS -- no macros; one continuous std band; pins over FULL N/S faces (pin_ranges + pin_balance, <= 5 pins/um);
  util ~5% WAIVED pin-bound (2,106 pins).
7 Clock: PASS -- single centre-fed root over 2,782 sinks (t1 pin-flop spread 23/22 TT/FF); io_hold_margin 0.03.
8 Schedule: PASS -- static; ages unchanged (low beat +2, high +3, already priced); 0 added edges.
smh_* is not a critical prefix: submit after a clean gate (reroute_reason: t1/t2 kits never closed; source fanout redesign).
