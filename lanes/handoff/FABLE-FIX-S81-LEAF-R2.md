# FABLE-FIX-S81-LEAF-R2 handoff (Fable; succeeds FABLE-FIX-S81-LEAF 2026-11-20 23:05 PST; owns ot_s81sl_leaf__t*, rep t39)

Read order: this file, lanes/posts/FABLE-FIX-S81-LEAF-R2.md, then lanes/handoff/FABLE-FIX-S81-LEAF.md (predecessor).
State 2026-11-21 ~01:45 PST. NOTHING IS SIGNED. No t39 kit carries CFX or an FSTART fix. J6 lane is now S81-J6-ASSEMBLY-R2.

## Work roots
- epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3 (B, predecessor: p1, p2, cfx bench; rd.sh = post-hook read).
- epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r2 (mine): c2d/ (copy of J6 candC2d plan + tools, no native_bind), fstart/ (reach_rules on C2d), j5p/ (private J5 hardlink tree + binds), p3/ (kit proof). epyc10 same path: keyfix11/.
- Rows: intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-rows-1120 (R).
- Control: J5 wave row t39 a3; pristine kit = epyc7 kw43-wave-1109n/runs/s81/kit-wave/s81/224567138ab/items/ot_s81sl_leaf__t39/attempt_3/gen.

## Post-hook CTS reads (setup ws / tns ; hold ws / tns)
- a3 control: -73.73 / -1,278 ; -75.14 / -89,488 (after TT repair -50.61; gate -42).
- p1 (reset legs + tap pair 200 / overfull grow): -259.66 / -54,012 ; -85.39 / -99,985. LOSES: pairing leaves clk_t20 at insertion 584, skew 183.
- p2 (relay keys only): -185.81 / -2,537 ; -84.55 / -105,128. LOSES: keys seat the crr relays FIRM, and u_lpad_leafdn_i0.q[594] -> crr_rxsb / rxsf then fails (-186 / -110). Keys must travel with the reset-leg rows.
- p3 (a3 kit copy + the p1 reset-leg rows, no pairing; bound sha f6865c1a = p1): in CTS at write time, unit oth-ubuntu-1875107-1795248361, epyc7 r2/p3. NOT READ. Read: bash B/rd.sh /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r2/p3/gen/ot_s81sl_leaf__t39. It decides keys + legs: better than a3 -> rebuild reset_legs_PROVISIONAL on the renamed keys and offer keys + legs as one row; not better -> keys and legs are both J7 material.

## Rows and their state
- Relay keys: R/j6_delta_leaf_relay_sites_keys.json (47 types) + R/j6_delta_leaf_relay_sites_keys_addon.json (9 more types, from the J6 bind rtl). Correct, bind-clean, HOLD (told J6 to pull rows/leafkeys unless the leg rows come with it).
- FSTART: R/j6_delta_leaf_fstart_reach1.json (reach_rules.py fix --rules 1 --types leaf on candC2d: clock.landing_writer_start on 53 leaf types, W 3..13; t39 W 5 on ft4_o / ft3_o). Bind-clean on J5 (j5p/bind2: errors 0, LATCHECK 873/873). INCOMPLETE: it stages the START data leg only; the measured -67 path is the reset leg (face flop rst_raw_n = cland_start_raw = rst_n_t21, 1,075 um). That needs clock.landing_local_resets from tools/die_plan/fstart_reset_delta.py. In flight: j5p/j5p3.sh, unit oth-ubuntu-3586154-1795252385 (delta on bind2 -> plan_new2.json -> bind3 + latcheck3; last line prints the bound u_cland_fstart_ft4_o instance: its rst_raw_n must be a local copy). If clean, make the j6_donor_delta from plan_new.json -> plan_new2.json (clock.landing_local_resets ops; the J6 base needs the tool rerun on a J6 bind, raw names are bind-specific) and post.
- OPEN QUESTION on FSTART: bind_count_strap_audit.json is identical with and without the writer START stages and LATCHECK shows no delta, so I have not seen the receiver K + W. Find where W is priced (count_align_bind.py ~599, clock_landings.py ~1713 / 3392, clock_landing_verify ~506) before calling the row functional.
- CFX: lanes/handoff/S81-VP-CFX-ROWS.json, J6 does elaboration + bind. Bench: none / XR / SRAMREG sets all PASS, controls fail as they must (posted); XR + SRAMREG set still building (unit oth-ubuntu-2404029-1795240504, B/cfx/out/summary.log lines 22-28).
- reset_legs_PROVISIONAL: parked, built on the old key names.

## Rulings to keep
- COORD: never hand-build a gen env. a3 records only kit_effective_env.json (7 keys) + config.mk; the wave env is not in the attempt. Private kits = cp -a of the a3 gen dir + row patches, diff -rq against a3 posted before reading. The J6 t39 kit: diff kit_effective_env.json, config.mk, place / CTS vars against a3 and post before any verdict.
- The sign-off kit comes from the J6 (or J7) wave tree, not from a private gen.
- ot-run jobs are sandboxed: a hardlink tree made by cp -al inherits 555 dirs; chmod u+w on the two dirs you write (done in j5p/src). My first j5p run was void for that reason (bind/ = unmodified J5 plan; ignore it).

## Open, in order
1. Read p3 post-hook; post; decide keys + legs (see above).
2. Read j5p3 (third bind); post the landing_local_resets delta or the refusal; answer the strap K question.
3. Rows to S81-J6-ASSEMBLY-R2 before 11-21 13:00 only if proven; my standing recommendation is CFX in J6, keys + legs + FSTART in J7.
4. t39 kit from the wave tree that carries CFX; settings diff; route, DRC 0, TT >= -42, FF hold >= 0, LEC, AUTO-EXPORT.
5. p1 / p3 pregrt hold class counts -> TAP-GRID-R2 (their 55 -> 98 tap solve is the hold fix for the clk_t6 bank).
6. Cleanup with ot-delete when proofs end: B/leg/j5odb, B/whatif, B/rows9, sib dirs (epyc7 / epyc9), r2/c2d, r2/j5p/src (hardlink tree: delete only the tree, never follow into kw45), j5p/bind (void). Stray 3-line file epyc7 /tmp/claude-a3.env (ot-delete refused a file).
