# DIE-HEAD-19 (2026-10-28): ring-clock windows for the 187 non-hd_tile HEAD crossings (ESTIMATE BEFORE BUILD)

Base: claude/die-head-18-1028@2876d8b484 (--ca-ring tool, approved, not yet on main). Runs: intel2:/srv/opentallas-scratch2/claude/die-head-19.

## 1. Inventory: no routed kit exists for any non-tile HEAD type (CHECKED)
Fleet search (intel1/intel2/epyc2 scratch, `*/asap7/dp_hd_*`) + autopilot OWNERS.tsv (tick 20:24):
- NEEDS-KIT (no kit at all): hd_ctl, hd_host, hd_lep0N, hd_mesh, hd_serdes (owner LAND-HEAD, default S81-HEAD).
- FIX (old 10-25 kits failed geometry review, withdrawn): hd_spn, hd_spn_end, hd_st_k5/m/n3/n4/str/turn, hd_turn_a/b.
- Only routed artifacts were the 10-25 proto hd_turn_a/b and hd_st_m runs on epyc1 (retired, ODBs deleted; old form,
  insertion 199 TT). hd_lep0N has synth-only dirs (die-head-8, codex-head-die-1028-0405). No measured ring clock is
  obtainable today for any of the 14 non-tile types.

## 2. Per-crossing windows (fixed K, the current DH18 plan; shared gate model, st_max_2, clock_variation table)
Shift of a crossing = reader(td) - [fwd_out(ts) + fwd_wire + fclk_in(td)] (ca_ring_fn).  The gate needs
margin_lo + shift_lo >= 100 and margin_hi - shift_hi >= T/8 (104.2, guard).  For two unbuilt types define the centre
m = reader - fclk_in - fwd_out, with tile-like intra spreads (R 38 + C 23 + F 4 TT; 34+21+4 FF) and wire [0,1].
Full table: windows.txt (spec_win.py on ports_r1.json.gz = DH18 r1 gate rows).  Tight rows (TT / FF):
| pair | ports | window |
|---|---|---|
| hd_spn -> hd_spn | 32 | m in [-2, 438] / [-33, 493]  (the HEAD gate worst rows, lo 136.0 / hi 574.9) |
| hd_turn_b -> hd_tile | 12 | fwd_out(hd_turn_b) late <= 354 / 328 |
| hd_spn_end -> hd_spn | 4 | m >= -51 / -76 |
| all other 47 pair kinds | 139 | m >= -100 ... -810, m <= +882 ... +1883 |
The declared model (common latency on both sides) is m = 0, F + C = L.  The tile form measured in DH18 gives m = +124 TT.

## 3. WHAT-IF gate runs (main gate code path, --ca-ring with ASSUMED non-tile values; hd_tile = DH18 measured)
FF values = TT x 0.817 (tile ratio, UNCHECKED for other types).  CHECKED own (run_gate.sh, whatif/*.log):
| form for all 14 non-tile types (TT fwd_out / fclk_in / reader) | TT lo/hi | FF lo/hi | fails |
|---|---|---|---|
| A tile form (DH18 measured values) | 227.0 / 417.1 | 226.2 / 503.9 | 0 PASS |
| D centre (165-170 / 150-170 / 525-565) | 284.2 / 324.9 | 288.9 / 421.7 | 0 PASS |
| F fwd_buffer export at clk source (45-60 / 150-200 / 525-565) | 394.2 / 204.9 | 378.8 / 323.7 | 0 PASS |
| B writer late (295-300 / 290-310 / 525-565, m = -55) | 50.0 / 594.9 | 93.3 / 642.3 | TT 12 (spn->spn 8, spn_end->spn 4), FF 8 |
| C writer early (40-45 / 40-60 / 525-565, m = +445) | 409.2 / 89.9 | 391.0 / 229.8 | TT 4 spn->spn (hi + guard) |
| E deep-tap export (fwd_out at a leaf tap 500-545 / 150-200 / 525-565) | -90.8 / 659.9 | -17.5 / 695.4 | TT 66 (24 slot_read), FF 33 |
The window algebra predicts A/B/C exactly (227.0/417.1, 50.0, 89.9), so the table in section 2 is the gate's own bound.
Finding: the forwarded-clock EXPORT POINT decides it.  The DH9 one-entry plan exports fclk_out_* of the non-tile types
from regional tap nets (clk_t1..clk_t44, die-head-9 plan_one_entry_450.one_entry.json; hd_tile legacy clk_t3 measured
195 TT, i.e. form A).  If a type's export tap sits near its leaf insertion, the HEAD gate fails on up to 66 crossings (E).  With fclk_out at the clk source (FLOW-GEN-2 landing_export_form=fwd_buffer) every row
passes with >=205 TT margin (F).  hd_spn is the only type with a two-sided window (fclk_in + fwd_out in ~[110, 550] TT
when its reader sits at the common latency 545).

## 4. Status of steps 1/2
cts0114 @343c8080d0 and die-head-18-regspine @71b0f83f9d (approved 20:04/20:20) and die-head-18 @2876d8b484 are NOT on
main at 20:49 (origin/main 6afcb8f45).  The hd_tile kit is a patched diagnostic lineage (DH9 mk_kit.py with kit-local
generator fixes + DH11 band patch + DH14 pre_cts/cts_post workarounds), so the clean regeneration must run the
compose -> latency -> ft adapter -> reserve -> gen.py phys chain on main with reg_spine + fwd_buffer + tap_passthrough.

## 5. Step 1 precondition found (CHECKED in code/history): no clean generator path for hd_tile on main
The hd_tile kits since DIE-HEAD-9 are diagnostic copies: DH9 mk_kit.py = gen_phys.write_type_kit on
plan_one_entry_450.json produced by the Codex UNTRACKED helper tools/s81_head/head_regional_one_entry.py (on
claude/die-head-9-oe-1028@f1f3eeb84 only, not on main) from codex/head-die-1028-0405 plan_rs_countsites_fullpin.json,
then DH11 band patch, DH14 ring_ff band (now main compose) + pre_cts/cts_post workarounds, DH17 reg_spine files.
Of the 5 DH9 kit-local generator fixes, main now has the strap [0] fix and the landing_placement uplevel fix (gen_phys);
the DFFHQN+INV status-driver and status-site fixes were not found on main (UNCHECKED beyond grep).
So "regenerate hd_tile" from main needs the one-entry plan generator on main first (die-local tools/s81_head, Codex
author) or a committed one-entry HEAD plan file; otherwise the gate run is again a DIAGNOSTIC copy.

## 6. Step 1 launched (DIAGNOSTIC gate-shaped run, cts0114 + regspine on main 5123301db at 20:52)
Kit intel1:/srv/opentallas-scratch2/claude/die-head-19/kits/hd_tile = copy of DH17 hd_tile_gen (synth/floorplan/place
reused, 4_*/5_* removed) with kit-local edits = what main gen_phys emits for the approved keys (kitlocal_h19.diff):
landing_exports.tcl from main landing_contract.export_tcl (landing_export_form=fwd_buffer); main tap_balance.tcl +
OT_TAP_PASSTHRU=1 (tap_passthrough); OT_TAP_REPORT_ONLY=1 (reg_spine); DH14 pre_cts/cts_post workarounds removed;
IO/tap basis = the reg_spine target 525 TT / 425.25 FF (0.81 x, gen_phys rule) instead of 450/380 (constraint.sdc,
stage SDCs, config.mk, budget.json; kit_preflight PASS).  run_diag.sh (DH14 copy: face_guard FAIL recorded, not fatal)
via ot-run intel1, 32 GB / 16 thr, GOAL=route, unit oth-ubuntu-2789635-1793246256, container dpkit-hd_tile-2789721.
CHECKED so far (4_1_cts.log, hold_gate.log, 21:03): no CTS-0114; OT_CLAND_EXPORT drops orphan output655 and drives
fclk_out_o from cland_fwd_fclk_out_o (BUFx24 at clk); OT_TAP_PASSTHRU follows ft_ck0/ft_ck1/ft_mesh of all 5 cores;
REG_SPINE 34 taps / 276 pads; post-CTS FF structural hold gate PASS (OT_HOLD_GATE PASS FF wns -82.15, 1797 endpoints,
vclk FF 425.25).  Core tap effective (placement RC) 568-600 TT vs 525 (WARN, same as DH17 placement-RC 313-351 pins;
routed RC was 503-517).  At 21:04 in 5_1_grt.  NOT a sign-off run (diagnostic kit lineage, section 5).
