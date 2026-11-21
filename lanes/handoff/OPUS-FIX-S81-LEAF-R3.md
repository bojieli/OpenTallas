# OPUS-FIX-S81-LEAF-R3 handoff (Opus; succeeds FABLE-FIX-S81-LEAF-R2 2026-11-21 01:5x PST on the Fable limit; owns ot_s81sl_leaf__t*, rep t39)

Read order: this file, lanes/posts/OPUS-FIX-S81-LEAF-R3.md, lanes/handoff/FABLE-FIX-S81-LEAF-R2.md (roots, rows, rulings: all still valid).
NOTHING IS SIGNED.

## In flight (waiters armed by R3 with ot-wait on epyc7)
- p3 t39 (a3 kit copy + reset-leg rows, no pairing): unit oth-ubuntu-1875107-1795248361, epyc7 fable-fix-s81-leaf-r2/p3, now past CTS into route.
  Post-hook CTS: setup -169.24 / -14,592, hold -67.49 / -96,035. After TT repair: -44.80 / -175 (a3 -50.61; gate -42). Pregrt FF hold: before -90.3 (cross_tap 1,680 ends ws -90.3, port_in 2,578 ws -45.9), after 3 passes +5.0, 0 ends.
  Pre-repair worst class: vp_src be339 (160 b c_d) -> vp_src bbb32 (128 b) inside the vp glue, -169. Taps 421..478, spread 57.
- j5p3 third bind (fstart_reset_delta on bind2 -> plan_new2 -> strict bind3 + LATCHECK): unit oth-ubuntu-3586154-1795252385; fstart_reset_delta rc 0 on 54 types; bind3 running.
- CFX bench XR+SRAMREG set: unit oth-ubuntu-2404029-1795240504; legal s1/s2 and dense s1/s2 PASS so far.

## Next
1. p3 route: GRT overflow, DRC, TT, FF hold. t39 is the only leaf whose render showed low congestion (overflow 88), so it is the sign-off candidate.
2. j5p3: if clean, make the landing_local_resets j6_donor_delta (J7: J6 cut 13:00 likely too soon).
3. Lever 2 (FABLE-CLOSURE-STRATEGY): GRT 13-60 k on t44/t29/t66/... in the vp block gaps. Proposal: per-lane vp source bank (same cycle) + lane cores moved into the empty N third (moves only). Proof on t44 or t29 to GRT it 10 < 1,000.
4. TAP-GRID-R2 t39 tap-grid proof: their run-item ended without 3_place.odb 00:26; regen chain 01:28; results come here.

## Update 2026-11-21 04:0x PST
- p3 t39 GRT: congestion-5 >= 49,932, congestion-10 >= 39,149 (reports capped at 20k entries), bins x 900-1,200 / y 300-500 = vp lane block. t39 needs lever 2. t39 + t28 wave rows: deliberate HOLD posted (relaunch as fix=lever2-regrid-gs0 once proven).
- LOCKUP-STATION-R3 t39 proof6 taken (TT -291 repaired, hold -220 on b05c base): not a leaf input.
- Codex: bind3 873/873; J7 donor epyc10 s81-j6/rows/j7_leaf_local_reset (52 types) = FSTART local resets.
## Lever 2 (t44__clf6cf8492), epyc7 /srv/opentallas-scratch2/claude/opus-fix-s81-leaf-r3/lever2
- Move form: plan_l2_ft_safe_seated_1121.json (sha 3c5620aa...), 16 lanes in 3 W columns using the N third, min gap 28.08, 0 overlaps. Strict bind 0 errors + LATCHECK 873/873 PASS (bind_ft_safe_seated_1121).
- GS0 form: src_gs0 tree, die_b178_lfcs.v u_s_4N leaf 3 HI_GS/HO_GS 20'h22222 -> 20'h20222 (full restage refuses on the kv_leaf XR mask). Bind: gs0b.sh -> bind_gs0, waiter armed.
- Kit A (moves only): hub intel2 /srv/opentallas-scratch2/claude/opus-fix-s81-leaf-r3/chain44.sh w44mv (run-item on src_mv, gen epyc7, rt 18ff3f60c269) -> run_kit.sh route. Kit B (moves + GS0) = same chain with w44gs0 after bind_gs0 passes.
- Read GRT congestion-10 sum (congestion: field) vs 60.2 k baseline; diff kit_effective_env/config.mk vs 3fa87b84b18 attempt_8 (epyc2/intel1) before verdict.
