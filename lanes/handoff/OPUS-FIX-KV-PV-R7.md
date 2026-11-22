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

## State 2026-11-22 (supersedes "Running / next" above)
- COORD: D28 row 1 = v3 only (v3/v3e split + own-leg fix + taps); the row 2 pieces stay unsplit. Hand-off to KV-PLAN-R6 is due 11:30 PST 11-22.
- Bind 12 crash (duplicate cut legs for o_vport_E_N_vo/_d2) was fixed by the own-leg prefill patch in tree5 split_bind_routes.py
  (patch r7/sbr_patch.py, test 14 pass, NOT pushed to main yet).
- Row 1a (r7/compose_v3row1.py) bind: HARD_CORE_PARAM_WRAP x2, so row 1b (r7/compose_v3row1b.py) keeps the split-15 ring sites.
  The landing_remap'd plan 02da9cb896b3 is INSTALLED as tree5 plan_of_record; tap_split v3 +2 (SPLIT), v3e OK.
  Bind is running (r7/chain_v3b.sh via ot-run from intel2, log ~/tmp/okpvr7/chain_v3b.log, out split28/bindgate_v3b).
- Next: chain_r7b.sh (R3 rows -> bind -> pure/mixed banks + reprice + gen latency -> bind -> ONE r8_refresh -> bind 13 + LATCHECK).
  Then the D28 row 1 hand-off, then the v3 representative via kit_wave private-spec to sign-off.
- D29 (cut-face bank offset, COORD ruling): v6n draft with the bank 25.92 um inward (r7/compose_d29b.py, r7/d29/run_d29b.sh).
  Still over the cap: w 5773/1000, e 1371/1000. The residual is the old netlist register cluster at the cut corner, not the bank.
  plan_gate_pre FAILs with 10 new GEOM-STATION-IN-CORE (v6ne ft regs_um[3]). So v6n stays UNSPLIT for D29 (posted c4116c1f).
  Flow knob staged, not pushed: r7/face_flops_inset.tcl (OT_FF_EW_INSET_UM).
- Cleanup later (ot-delete): tree5 Q/por_*fail*, por_d29_*, r7 dbg dirs, dbg_all16_out.

## State 2026-11-22 03:3x PST (supersedes the block above)
- Own-leg fix PUSHED to main 4c484aef37 (split_bind_routes + regression test).
- Row 1b bind (bindgate_v3b): only the 30 expected R8_UNCOVERED (pv_S_3), no HARD_CORE_PARAM_WRAP.
- chain_r7b (log intel2 ~/tmp/okpvr7/chain_r7b.log): R3 rows -> bind 12b (same 30 R8 only) -> banks + reprice
  (R3_FIXED_CYCLES 20, net +55) -> plan 0268822b037f -> bind 12c RUNNING -> one R8 refresh -> bind 13 + LATCHECK.
  Then the D28 row 1 package to KV-PLAN-R6 (due 11:30): plan sha + v3 rows (r7/compose_v3row1b.py rows) + tap rows (v3 +2).
- D29 v6n CLOSED on the model (posted 722deacc): draft sha 78fe00f580fd at tree5 Q/por_d29_kv3_pv_v6n_1080_b25.92_stk5res_composed.
  Tools: r7/compose_d29c.py (D29_BINS, D29_XPREF, D29_RESERVE), r7/d29/run_d29c.sh, mk_bins5.py (regs from the KV-D23H odb,
  dumped by epyc7 /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r7/d29v6n/regs.sh), fix_st_in_core.py, assemble_d29.py,
  tap_probe.py, legal_probe.py. Next: bind the D29 draft.
- Staged, not pushed: r7/face_flops_inset.tcl (OT_FF_EW_INSET_UM).
- Cleanup (ot-delete, later): r7/negtest (SKIP: protected parent), por_d29_* trial dirs except stk5res.

## State 2026-11-22 06:3x PST
- D28 row 1 READY posted 617f8b82: plan 0268822b037f, manifest epyc8 split28/r7/row1_package.json.
- Bind 13 (one R8 refresh) -> 42 new (R8_STALE 30 pvw_1, R8_STRAP_PAD 5 pc, TYPE_SPLIT 3, EMIT 3, PARAM_REGEN). Snapshot tree5 Q/por_row1_bind13.
- chain_r7c.sh (2nd refresh from bind 13 -> bind 14) queued/running; log intel2 ~/tmp/okpvr7/chain_r7c.log.
- D29: v6n draft 78fe00f580fd closes (plan_gate_pre PASS). With the D29 levers: v2 closes; v12/v7 left only with INHERITED corner taps; v5ne still over (2114/1889).
  chain_d29.sh staged (binds the v6n draft after row 1; moves plan_of_record to por_row1_final).
- Pending: merge FIX-SYNC reset.inst_taps v2 rows (13 banks) when posted; FABLE-FIX-KV-PV-SINKSPREAD sync.
- Representative v3 build: needs an emitting (clean) bind -> after D28 seal or a clean bind 14.

## State 2026-11-22 07:0x PST (current)
- No running jobs or waiters. chain_r7c (2nd refresh + bind 14) was cancelled before admission (own exact PIDs, epyc8 load 147);
  tree5 plan_of_record = plan 0268822b037f with the bind-13 R8 table dc12dffd7a48 (snapshot Q/por_row1_bind13).
- D28 row 1 READY 617f8b82 (manifest split28/r7/row1_package.json). KV-PLAN-R6 owns the seal-time die R8 refresh + pair image.
- D29 pv: FABLE-FIX-KV-PV-SINKSPREAD owns the one-event candidate 54ac7f32109f; my drafts are inputs only (ALIGN 16c9052a).
  pv_v6 reset-leg coverage (FIX-SYNC 06:17) goes with SINKSPREAD unless COORD says otherwise.
- NEXT: after the D28 seal emits a clean bind, build the v3 split representative (kv3_pv_v3 and kv3_pv_v3e) with
  kit_wave.py private-spec qwen_kvsys <item> --tree <seal tree> --src-manifest seal --host epyc7|epyc8 (wave env), then run-item to sign-off.
- Cleanup later via ot-delete: tree5 Q/por_d29_* trial dirs, r7/negtest, por_*fail dirs.
