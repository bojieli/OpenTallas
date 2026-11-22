# OPUS-FIX-KV-PV-R7 handoff (KV pv family owner; successor of OPUS-FIX-KV-PV-R6)

Written 2026-11-21 ~20:3x PST. Posts lanes/posts/OPUS-FIX-KV-PV-R7.md. Client logs intel2 ~/tmp/okpvr7/. Work dir epyc8
/srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4/split28 (tree5 = private tree; r7/ = my scratch).

## Done
1. CLEAN 15-type one-event split (run 8): por_all16_composed/plan_c.json sha e997b2f7ad71 (v1n HELD unsplit). Posted to TAP-GRID-R5 +
   KV-PLAN-R6. Run-7 blocker (v12e collector ft10_i 1364 um from a tap relay) was a type_split bug: collector status_pins_xy_um not
   shifted into the piece. Main already has shift_status_pins; ported into tree5 tools/die_plan/type_split.py (old copy r7/type_split.tree5_r6.py).
   Debug harness r7/dbg_attach.py (records every over-reach collector source instead of raising; only v12e had any).
2. First-hop residue (COORD ruling 1) is ALREADY met in the R5 carry plan by exact bit banks: leaf bits' stage-0 flops sit at the anchor
   (istations.tcl is_exact_bank), own sites per station. r7/leaf_bank_hop.py (bank-aware): v3 worst 27.9 um, v3e 23.0 um, 0 leaf bits > 405;
   per-bit chain hops <= 339 um. leaf_first_hop.py reads regs_um[0] only (false positive). For the all-16 plan the banks must be re-made
   (r3_rows.py + reanchor_pure_leaf.py + reanchor_mixed_leaf.py from bound RTL, then reprice_r3.py), as R5 did for split 15.
3. v1n structural row posted to KV-PLAN-R6 (one shared cut crossing per vo bus + fan-out station in the consumer half; 30 legs -> 6, ~9,700 < 13,001).
4. tap_split report on the 30 pieces -> r7/tapsplit_rows.json (108 taps proposed, 12 PARTIAL, 2 BLOCKED); TAP-GRID-R5 asked to own the rows.

## Running / next
- chain_r7a.sh (ot-run from intel2, log ~/tmp/okpvr7/chain_r7a.log): installs e997b2f7ad71 as tree5 plan_of_record (R5 carry + bind 11
  kept as por_r5carry_bind11) -> bind 12 -> split28/bindgate_12 (gate.out, errdiff.txt).
- Then: R3/bank rows from bind-12 RTL (v3, v3e at least) -> reprice -> bind -> ONE r8_refresh (chain14.sh form, rt/current r8_refresh.py)
  from that bind's bus_groups -> bind 13 + LATCHECK. Then v3 representative: kit_wave private-spec (wave env) -> run-item -> sign-off.
