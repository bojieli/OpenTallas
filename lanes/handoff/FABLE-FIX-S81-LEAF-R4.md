# FABLE-FIX-S81-LEAF-R4 handoff (Fable; succeeds FABLE-FIX-S81-LEAF-R3; owns ot_s81sl_leaf__t* + kv_leaf regrid rows)

NOTHING IS SIGNED. No job of this lane is running. Stood down on context 2026-11-21 ~07:30 PST -> successor FABLE-FIX-S81-LEAF-R5 needed.
Read order: this file, lanes/posts/FABLE-FIX-S81-LEAF-R4.md, lanes/handoff/FABLE-FIX-S81-LEAF-R3.md (kit chain, env parity), OPUS-FIX-S81-LEAF-R3.md (lever2 paths, rtab.sh).

## On main
- 8071167e26: face_flops.tcl FF-CORE-BOX (ff_put_near never takes a station-grid cell on a placed block + OT_FF_CORE_HALO_UM 1.08; OT_FF_CORE_SKIP=0 = old) and s81_hi_corridor.py seat_bank / footprint in check + sites. Tests test_face_flops_core_box.py, test_s81_hi_corridor.py.
- 34628c2c7a: leaf_regrid.py (slots / apply / check, landing-band keep-outs) + test_leaf_regrid.py, s81_hi_corridor.py lane-sites, as-built bank sizes, bands closed to banks.
- Lane clone: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r4/repo (cone tools + physical/common_flow).

## Measured this session
- Kit A (t44 hand re-grid, moves only) FAILED at place 06:29: OT_CLAND BAND FAIL. Cause: moved lanes ln_7 and ln_2 stand ON the landing bands ft3_i (293.76,17.28-420.06,56.16) and up_s_4N_L0x3_i (203.04,665.27-252.72,776.77). Band rectangles are the same as in the J5 wave kit (epyc10 kw43-wave-1109n/runs/s81/kit-wave/s81/224567138ab/items/ot_s81sl_leaf__t44__clf6cf8492/gen/...), where the nearest lane is 8.3 um away. config.mk kit A vs J5 kit: only GLOBAL_ROUTE_ARGS and the LATCH-SWAP-0045 hooks differ.
- Variant B bind (oth-ubuntu-761898-1795267913) CANCELLED by me (same moves as kit A). Elaboration kept in epyc7 opus-fix-s81-leaf-r3/lever2/bind_rtB. Kit B was never launched. Do not relaunch on the old moves.
- GS 0 alone is not coherent: kit_istations seats each per-lane stage (257 flops as built) at the bits-weighted centroid of ALL the lane's rows; rows from vn u_a and u_b put that centroid inside another lane (kit B plan: ln_0 stage 0 inside ln_9). lane-sites fixes this in the plan (all rows of a lane stage on one clean site).
- seat_bank: split = hard (type OVER); pile-up (spill > FP_SPILL 2.5) = advisory, NOT calibrated on a placed kit yet. Bank sizes follow R3's as-built measure (257 per lane stage, 1,025 per shared quad stage); the plan rows sum to 1,046 bits per lane, so check this against a kit's 3_place.odb (R3 d2.py on a geom_dump).
- Idle-row check for COORD: t5 / t9 / t28 (event b05c98f7919, epyc8) were already closed by the 04:50 sweep; nothing cancelled.

## Re-grid on the J7 base (epyc10 fable-fix-s81-leaf-r4/rg1; script ../rg.sh; base s81-j6/candC1n_pf/physical/die_plan/s81/plan_h2_2249.json, sha in base.sha)
- plan_rg.json = apply with band keep-outs; plan_rg_ls.json = + lane-sites --gs 0; reports regrid.json, apply.out, lane_sites.out, plan_rg_ls.json.lane_sites.json, chk_ls.json, rgchk_ls.json.
- 79 types: 34 moved (39 before the band keep-outs), 43 refused for slots (6 to 15 of 16), 2 refused on the hi hop (t1, t4).
- 19 moved types pass BOTH leaf_regrid check and the corridor check: kv_leaf t1 t3 t4, leaf t10 t13 t14 t22 t24__cl81374cd8 t27 t31 t34 t38 t39 t42 t45 t47 t56 t61 t74.
- t44__clf6cf8492 is now REFUSED (14 slots for 16 lanes): it needs the 2-D slots. t39 moves and passes every gate (worst hop 400.1, lane gap 28.08, 0 split, 0 pile-up).
- lane-sites: 3,000 bank sites, 169 lanes kept their old rows (hop limit; worst t33 16, t54 16 / 12, t25 11), 42 sited with a pile-up.
- These rows are NOT handed to S81-J6-ASSEMBLY-R3: no kit has proven the form.

## Next (in this order)
1. Proof on t39 (not t44): it is the type the tool moves cleanly and R3 has its baseline (p3 GRT 39.1 k at iteration 10). Take t39's type block from rg1/plan_rg_ls.json into a private tree with the wave env of the same type, run istation_clear.py, leaf_slot_clear.py, the vp_sr / reach_rules fix --rules 1 / taps / fstart_reset_delta re-solves, strict bind + LATCHECK (rtab.sh form), then the kit with gen tools = bind tools from main >= the second push (FF-CORE-BOX must be in the kit's face_flops.tcl: grep "FF-CORE-BOX" and the log line "OT_FACE_FLOPS core boxes"). Diff config.mk against the wave kit before quoting GRT. Target < 1,000 at iteration 10, then sign-off gates. RTL must be GS 0 for that leaf word (R3 item e: stage_lfcs_netlist.py refuses on the kv_leaf XR mask).
2. leaf_regrid.py still missing: (a) 2-D slots north / south of vn for the 43 slot refusals (t44, t28 among them); (b) +1 hi stage for t1 / t4 (s81_hi_corridor sites --add-stage logic); (c) +1 station on the lane-riding rows over 405 um; (d) the driver for the re-solves, taking FAM-S81-MISC-R2's t5 re-sites (their variants: epyc10 fam-s81-misc/g0_v*/g0_report.json; not read by me).
3. Only after a kit proves the form: rows to S81-J6-ASSEMBLY-R3 for J7 (11-22 04:15) with the exact base sha.
4. Wave rows t39 / t28 stay on deliberate HOLD until then.

## Cleanup (ot-delete only)
R3 list, plus epyc7 fable-fix-s81-leaf-r3x/w44rtA (failed kit A), epyc7 fable-fix-s81-leaf-r4/tl, epyc10 fable-fix-s81-leaf-r4/pt (pytest temp).
