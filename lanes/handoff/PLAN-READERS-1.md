# PLAN-READERS-1 handoff, 2026-11-14/15

Branch claude/plan-readers-1-1114 @55258ce2a07 (on origin; base main 76537ad08a5). Worktree intel2 /srv/opentallas-scratch2/claude/plan-readers-1/wt.
Smoke (epyc2 /srv/opentallas-scratch2/claude/plan-readers-1/smoke: smoke_plr1.py, smoke2.py, kit/serdes__t2, out/plan_smoke.json).

## Delivered
1. rck_island (tools/die_plan/rck_island.py; schema; kit hooks serdes_lanes.tcl + serdes_lanes_release.tcl from claude/hard-s81-serdes-1-1113, islands section added).
   Type key {rect_um, clock, inst_re, release_before_dpl}. G0 in schema.validate: inside outline, holds u_chn + SRAMs (PMA ot_s81_pma* excluded), no other macro, no PHY PG domain overlap.
   clock.keepouts_um NOT enforced (die-clock-cell exclusion; covers the whole logic area on serdes types) - COORD accepted.
   Helpers for B6d: RI.derive(P,tn) (island from the type's own io_pma_rck pad x; t2 = [245,640,1005,944]), RI.plan_patch(P,tn,rck_buf_cell=...) -> rck_island, u_chn/SRAM moves (t2 shift -583.2,+587.52; core_moves are plan origins, kit location = origin+track_offset), the rck_isl/rck_chn pad-clock entries (rck_chn min_early_ps 175), die_pg_domain_rects.
2. min_early_ps on pad-clock entries and early core taps (pad_clock.ENTRY_OPT/early_rows): kit rck_early.txt + OT_RCK_EARLY, rck_early_report.tcl sourced at the end of postcts_gate.tcl (report only). Early core tap: G0 fails if insertion_ps - die common latency < min_early_ps.
3. type_m9_grant: reader already on main (32d070ea31); added the precondition (m8_grant.check_m9_clock): guide required, must hold M9 clock segments, must cover the type's instances when clock.layer is M9, tracks must remain. Fail closed, "M9 grant refused" message. OT_GEN_M9_GRANT=1 also needs a guide.
4. COORD item 4: check.py check_completeness insertion_target exempts types with rck_island or clock.insertion_target_override {reason}; non-numeric values reported not raised (I could not reproduce the TypeError: schema rejects a None insertion_ps first).

## IMPORTANT for DIE-S81-92 (B6d)
- The REAL S81 die M9 clock guide (OpenROAD write_guides of the die clock route) is a PRECONDITION for any M9 grant. None exists in the B6 tree. The smoke used a SYNTHETIC guide (one M9 clock leg per tap pin).
- Moving u_chn + SRAMs into the island makes gen_phys.phy_pg_domains grow the PHY PG domain over them (t2: floor 947.16 -> 645.84), G0 then flags the island. Fix: write RI.domain_patch / plan_patch()["die_pg_domain_rects"] into die.pg.domains[].rect_um BEFORE the moves (smoke did this: phy_lk_WN2 -> 25597..25876 y band, ES1 likewise). Needs a die PG domain edit, not just type data.
- Band top for t2 is 947.16; island top 944 = band top - 3.16 (derive band_gap_um).
- B6c1 plan carries relay_polylines / budgets.gutter_block_* keys unknown to main schema; the smoke stripped them (not mine).
- Serdes 450: set clock.insertion_ps 450 together with rck_island (exempt) or insertion_target_override.

## Smoke result (serdes__t2, B6c1 + patch, gen_phys.write_type_kit)
- config.mk: OT_RCK_ISLAND=1, RECT 245,640,1005,944, CLOCK io_pma_rck, RELEASE 1, OT_RCK_EARLY, MAX_ROUTING_LAYER M9.
- serdes_lanes_cfg.tcl islands {rck_isl 245 640 1005 944 io_pma_rck {u_core[.](u_dec|u_rxf|u_lrx)}}; hooks appended to face_flops.tcl / face_flops_release.tcl.
- rck_early.txt: rck_chn u_core.u_dec.u_chn clk 175; pre_cts.tcl pce_entries: rck_isl (4 sink pins) + rck_chn (u_chn clk, buffer west of the core).
- pdn.tcl: M9 GRANT (type 8641 of 36072 tracks, die route 163 tracks from the guide). Without guide: refused with the message.
- NOT verified: the island Tcl hook inside OpenROAD (syntax only), rck_early_report.tcl at a real post-CTS gate, gen.py phys end to end (needs bind kit-rtl; used write_type_kit), G0 on B6c4 with serdes 450 (unit-tested only).

## Tests
test_rck_island.py (30), test_m8_grant.py, test_check.py, test_pad_clock*.py, test_s81_rck_form.py: 156 pass on the clone. Full die_plan suite was still running (intel2 ot-run, log /tmp/claude-1000/pytest_full.log local); 9 files do not collect in the sparse checkout; run the suite in the merge queue.
