# CORE-PIN-RELAY-1930 handoff (2026-11-20 ~20:20 PST)

## 1. What CBC emits today, and why nothing sits at the pin (V)
- CBC rule 1 BOUNDARY (cbc_pass.py, BOUNDARY_REG_UM 50) covers BLOCK PORTS only (u_bin/u_bout face banks). No rule covers hard-core pins inside a type.
- relay_depth.py (S81-COLGEN-3) sizes core-to-core relay chains on the MIDPOINT model: stations = ceil(L/limit)-1. relay_mid.tcl then places the u_y_* stages FIRM at L*j/(n+1) between the fixed ends **by design**, so a 1-stage relay is ~L/2 from both pins (col_h9_r1 cl49d7a23e: u_u_y_xa_4_0.o -> u_u_t4 516 um, 566 such pairs).
- core_out_land.tcl (DIE-HEAD-69) seats single-load landing flops at core OUTPUT pins, but it is opt-in (core_out_land_types; QC cb uses it, S81 col does not), has no input side, and skips FIRM flops, so it never touches relay_mid stations.
- Census of placed legs over 300 um with a core end (precheck raw scans, epyc7/9/10): S81 col 96 kits: relay u_y_ -> core input 238k, core output -> relay 51k, core2core 25k, core -> istation 4.7k. QC cb 17 kits: core -> plan istation 3.7k (u_t12 -> u_ist_y_o12_0 475 um: a plan station site, kit_istations), other regs about 9k. KV kv3 46 kits: other-reg in 129k / out 106k, core2core 119k, relay 13k.

## 2. Implemented and PUSHED: main 2c832b890d1 (commit 91173db82e, rebased)
- Plan key `budgets.core_pin_relay` (true | {re, w, hop_um}) and `budgets.core_pin_relay_types` (types or base names); GEN env `OT_CORE_PIN_RELAY=1` (or a regex) for pilots. Absent = byte-identical kits.
- relay_mid.tcl PIN form (`OT_RELAY_MID_PIN=RE=W`, `OT_RELAY_MID_PIN_HOP_UM`, default 300): per chain it tries both ends at the core pin, then source end, then sink end, then none. The first form whose inner hop L/(w0+n-1+wl) fits the cap wins. Existing stages are only re-seated, never stretched. FIT keeps the cluster outside the halos. One summary line per kit: `OT_RELAY_MID_PIN seated chains: ...`.
- core_out_land.tcl IN side (`OT_CORE_IN_LAND=1`): the single-load driver flop of a core input pin sits FIRM at that pin and is released before DPL (same list).
- relay_depth.py `pin_weight` / `--pin-w` (also read from the plan key, so cbc_pass gets it): stations with both chain ends at the pins, ceil(L/300 + 0.8). Cycles are added only on paths over the limit; short core-to-core wires get none.
- gen_phys exports, schema keys (die_plan.schema.json regenerated), tests in tools/die_plan/test_core_pin_relay.py (6 unit tests + 1 OpenROAD docker test, all pass). Stale test_relay_depth D bound updated to the schema maximum of 16 (bbcc7f022a8).

## 3. Rows (for S81-J6-ASSEMBLY / QC-PLAN-R6 / KV-PLAN-R2)
- S81, J5 plan_h2_2249 + J5 bound (32 col types with bound RTL, epyc9): midpoint model 317 rows / +325 stages; pin model **573 rows / +1,255 stages, max D per path 2-4 (midpoint 1-2)**, so +1 to +2 cycles per long core path. Rows file: epyc9 /srv/opentallas-scratch2/claude/core-pin-relay-1930/rows/s81_core_pin_relay_rows.json (relay_depth row format, merge with `relay_depth.py merge`). Reports: rows/s81_{mid,pin}.json.
- Key for J6: add `"core_pin_relay": true` (or core_pin_relay_types: the col bases), regenerate the rows on the J6 bind with `relay_depth.py PLAN . BOUND --pin-w 0.1 --repo TREE --plan-dir ...`, and fold them in. Without the rows, the PIN form seats only the chains that already have enough stages.
- QC cb: the core class is core -> FIRST plan internal station (kit_istations sites at y 777.6, 475 um from u_t12). The fix is a plan station-site row (stage 0 at the core pin, plus 1 station where the chain gets too long), owned by QC-PLAN-R6/R7. The kit key adds the IN/OUT landing flops only. Not proven on a QC kit.
- KV: the key covers relay_mid (KV relay_mid_re) and landing flops. Rows come from relay_depth --pin-w on the D27 bind.

## 4. Clock-tap form (FABLE-CLOSURE-1930 lever 1): do NOT put pin relays on the core tap (V)
- The 540-690 ps "related pair" is arithmetic: report_clock_skew adds |source| + target for the early core port, which carries a negative clock source latency (col_h9_r1 cl49d7a23e: 406.17 + 194.48 = 600.65 printed, clk_c8 source latency -225.39; QC cbn_q01 cld9ff4c40: 267.34 + 424.93 = 692.27).
- The core ETM arcs are referenced to the early pin and absorb the early pin and the internal tree: S81 ot_v41_rom_elem setup -361 ps, hold +385, clk->q 481-611, clock_tree_path 342/533. QC qfd_tile_nk_a0c setup median -680, hold +715, clk->q 866, tree 304/818. The core_taps.txt early_ps contract (insertion - common latency) lines the core's internal clock up with the kit taps.
- On the early core tap a pin relay would run 200-480 ps EARLY against the core's internal clock, which makes hold into the core worse. Rule: **pin relays keep their kit tap (common latency)**. Judge flop -> core pairs by setup/hold SLACK at CTS, not by report_clock_skew. On col_h9_r1 the worst CTS setup path is core -> core (u_u_s6 go_tag -> u_u_e6_u_w, a falling-edge half cycle, -226.9), not flop -> core.
- Stop-list item "no J6 col volume with relay registers on the nearest tap": I recommend it be withdrawn on this evidence (COORD's call).

## 5. Proof in flight (private, OT_LANE=CORE-PIN-RELAY-1930)
- epyc9 kits /srv/opentallas-scratch2/claude/core-pin-relay-1930/kits/col_A (control) and col_B (OT_RELAY_MID_PIN=.=0.1, HOP 300, OT_CORE_IN_LAND=1, OT_CORE_OUT_LAND=1). Both are copies of ot-jobs col_h9_r1__t1__cl49d7a23e__pva2370bfd-route-renewed-glider-1462088-1795153827 from 3_2_place_iop, with main relay_mid.tcl and core_out_land.tcl in both.
- Runner: kits/run_ab.sh (docker orfs:asap7lock, do-3_3 .. do-3_5, do-3_place, do-4_1_cts). Log: <kit>/cpr_ab.log, last line CPR_AB_RC.
- Launched 19:5x via `ot-run --mem 24 --threads 12 --hosts epyc9` (localhost client PIDs 1269339 and 1269340, logs scratchpad cpr/otrun_{A,B}.log). At 20:20 they were still queued for memory on epyc9 (admits 0).
- Read when done: (a) legs over 300 um: run tools/precheck/placed_hops_or.py on each 3_place.odb (kit_scan run_placed shape), then classify with the scratchpad legs.py (copied to epyc9 core-pin-relay-1930/legs.py); the control's original raw scan is at epyc9 ~/.local/state/precheck-kit-scan/<kit>.placed_raw.json (core_in 2,416 / core_out 1,517 / core2core 694 legs). (b) place WNS: 3_detailed_place.rpt. (c) CTS: 4_cts_final.rpt worst setup/hold slack of flop -> core and core -> flop ends, A vs B. (d) the OT_RELAY_MID_PIN seated line.
- Not done: no QC cb kit proof (see section 3); no post of the rows to the three lanes beyond the progress post; no CTS-level skew A/B yet.
