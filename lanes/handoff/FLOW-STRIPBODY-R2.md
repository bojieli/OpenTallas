# FLOW-STRIPBODY-R2 handoff (Opus 5.5) -- live, 11-21 ~21:xx PST
Goal: lepe_mu_C t1 strip/body split bindable (strict + LATCHECK), then private kits strip_S / body / strip_N to floorplan
cell counts -> S81-J6-ASSEMBLY-R5 (J8 rows); if pieces < 400k carry to sign-off.
L=intel2 /srv/opentallas-scratch2/claude/flow-stripbody-r2 (lane clone $L/lc, branch claude/flow-stripbody-r2, on main).
Base = sealed J7 a6771d121e95 (intel2 kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work), NOT J6r1.

## Pushed to main
- 9f844e40a0 type_split carries clock.landing_local_resets per piece (J7 START local reset copies); reset_tree_anchor dropped via spec drop_clock_keys.
- cd2cd11c4e split_bind_routes own cut leg also matches o_<stem>_p (unprefixed bus). Needed but NOT sufficient (see below).

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
## Cleanup owed
- trees ..._work_stripbody_r2 and ..._r2b (55 GB each) superseded; ot-delete guard refuses now (newer than die tree,
  apply pending). Delete via ot-delete after the J7 apply.
## Next
private-spec script $L/specs.sh (edit tree to r2c, bind-out bind7c) -> run-item to floorplan (epyc7/epyc9 gen; hub gen
guard lifted 2e21a81724) -> cell counts to S81-J6-ASSEMBLY-R5 + FAM-S81-LEPE-4.
