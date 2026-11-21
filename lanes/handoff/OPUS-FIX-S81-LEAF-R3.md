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
