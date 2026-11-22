# FLOW-STRIPBODY-R2 handoff (Opus 5.5) -- live, 11-21 ~21:xx PST
Goal: lepe_mu_C t1 strip/body split bindable (strict + LATCHECK), then private kits strip_S / body / strip_N to floorplan
cell counts -> S81-J6-ASSEMBLY-R5 (J8 rows); if pieces < 400k carry to sign-off.
L=intel2 /srv/opentallas-scratch2/claude/flow-stripbody-r2 (lane clone $L/lc, branch claude/flow-stripbody-r2, on main).
Base = sealed J7 a6771d121e95 (intel2 kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work), NOT J6r1.

## Pushed to main
- 9f844e40a0 type_split carries clock.landing_local_resets per piece (J7 START local reset copies); reset_tree_anchor dropped via spec drop_clock_keys.
- cd2cd11c4e split_bind_routes own cut leg also matches o_<stem>_p (unprefixed bus).
- a699139ec4 clock_landings finds partition instances by bind sv_id name (s_7N_C__strip_S -> s_7N_C_strip_S).
- 74bbd8a8a6 type_split drops landing_local_resets copies sited outside the keep piece (strip trees are shallow).

## Spec / plan (scripts in $L: split7.sh, full_c.sh, tmp/mkplan7.py, tmp/mkpack7.py)
- plan_sb7.json = J7 + strip_body key on lepe_mu_C t1 + private RING-WINDOW row: 1104-bit windows at local y[6.144,..]
  start 47.52 on BOTH ends (lepe_mu_C t1 xring_i0 + lepk_o0, c1x_C t9 xring_o1, lepe_mu_LP t2 lepk_i0, ports
  kd_s_7N__0 / xring__s_6N_C__s_7N_C__0). Without it the port-geometry check fails (window crosses the S cut 43.2).
  J8 row candidate; touches SLICE-R5 (c1x_C t9) and LEPE-4 (lepe_mu_LP t2) types.
- spec: census7.json + base_defect_rows off (census ends name as-built wrapper u_s_7N.u_sl.$N) + drop reset_tree_anchor.
- split cuts y 43.2 / 1183.68; strip_S/N 1442.88x43.2, body 1442.88x1140.48.

## Bind history
- r2 / r2b trees (real copies, nlink 1): strict bind FAILED `native stations s_7N_C.o_leafdn_o2_p: expected one outgoing lane`.
  Root cause: with whole_map_to_keep the cut lanes body->strip get no as-built bits (bind.build_buses only keeps lanes with
  items); the split needs spec lane_reference (split_lane_reference_export of the base bind) so split_bind_routes refills them.
- round c (full_c.sh, ot-run localhost, PID 562685): laneref7.json export (J7 unsplit bind) -> split7c with lane_reference ->
  pack7c -> tree ..._stripbody_r2c -> strict bind + LATCHECK (bind7c.log, latcheck7c.*).
- round c: station error GONE with lane_reference (prefill 4356 cut puts); 1 error left: strip_S local reset fstart_1 raw
  rst_rl_135 no driver -> fixed by 74bbd8a8a6.
- round d (full_d.sh, ot-run localhost, PID 2053096): split7d -> tree _stripbody_r2d -> bind7d + latcheck7d.
- round d: 1 error: EMIT clock landing: expected exactly one bound instance s_7N_C__strip_S (sv_id vs ident) -> a699139ec4;
  the J7 tree's clock_landings + this fix rides as overlay tmp/clock_landings_j7_fix.py.
- round e (full_e.sh, ot-run localhost, PID 2651813): reuses split7d -> pack7e -> tree _stripbody_r2e -> bind7e + latcheck7e.
- round e: 1 error class: count-strap audit keyed s_7N_C__strip_S vs top instance s_7N_C_strip_S -> main 0af17ef0a4 (bind audit sv_id).
- round f (bind_f.sh, ot-run localhost PID 1932001): bind of r2e tree from overlay root $L/ovl_e (tools copy + fix, symlinks
  physical/rtl/results -> r2e), out bind7f, latcheck7f. No new tree: scratch2 at 96%. Kits then: tree r2e, bind-out bind7f.
- round f: audit fixed; 2 lanes up_s_7N_L0/L2 delivered +1 (carry_short_fixed went to 0) -> main ef6cae97e1 carried_fixed.
- round g (full_g.sh, ot-run localhost PID 1577850): split7g (only L0/L2 0->1 vs split7d), pack7g (+clock_landings fix +
  tmp/bind_j7_fix.py), tree _stripbody_r2g (nlink 1, LINKS 0), bind7g, latcheck7g. r2e deleted. Kits: tree r2g, bind-out bind7g.
- ovl_e: tools copy with dangling links, ot-delete SKIP protected (kit_wave marker); small, retry later.
- round g: BIND PASS (0 errors), LATCHECK PASS 893/893 with main cb780b6d04 (latcheck7g3.json).
- private-spec (specs2.sh, lc kit_wave with efe70f16d3 + fix 0890cc9405: spec kit_rtl.asbuilt = bind's asbuilt_vN, rt-floor exempt):
  specs $L/spec_<item>/spec.json for strip_S, t1 (body), strip_N.
- run-item x3 started 07:04 (rt/current kit_wave, logs $L/runitem_<item>.log, PIDs 3697331/2/4). Adopt: never relaunch while alive.
## Cleanup owed
- trees ..._work_stripbody_r2, _r2b, _r2c, _r2d (55 GB each; ASK posted to COORD/FLEET-OPS 02:4x) superseded; ot-delete guard refuses now (newer than die tree,
  apply pending). Delete via ot-delete after the J7 apply.
## Next
private-spec script $L/specs.sh (edit tree to r2e, bind-out bind7f; --host intel2 already set) -> run-item to floorplan (epyc7/epyc9 gen; hub gen
guard lifted 2e21a81724) -> cell counts to S81-J6-ASSEMBLY-R5 + FAM-S81-LEPE-4.
