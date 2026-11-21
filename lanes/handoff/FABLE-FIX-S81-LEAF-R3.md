# FABLE-FIX-S81-LEAF-R3 handoff (Fable; succeeds OPUS-FIX-S81-LEAF-R3 2026-11-21 05:24 PST; owns ot_s81sl_leaf__t*, proof type t44__clf6cf8492)

Read order: this file, lanes/posts/FABLE-FIX-S81-LEAF-R3.md, lanes/handoff/OPUS-FIX-S81-LEAF-R3.md (lever2 paths), FABLE-PD-S81-0440 C3.
NOTHING IS SIGNED. State 2026-11-21 ~07:05 PST. STOOD DOWN on context -> successor FABLE-FIX-S81-LEAF-R4 needed.
Re-arm first: (1) epyc7: while kill -0 4191487 (B bind client; unit oth-ubuntu-761898-1795267913), then tail lever2/rtB2.otrun.log; (2) intel2: kit A chain PID 2876997, wait on "route start|NO_PLACE|CHAIN_DONE" in /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3x/w44rtA/chain.log (at 07:0x it was in gen on epyc7).

## Diagnosis (measured; posts 05:4x and 06:0x)
- Cause of the vp block overflow = lane-column placement + bank siting, not pin access.
- t44 J5 wave kit (epyc10 /srv/opentallas-scratch2/claude/ot-jobs/ot_s81sl_leaf__t44__clf6cf8492-route-civil-redfish-2124552-1795231168/work; congestion-10 >= 58,900, report capped at 20,000 entries): 61 % of the overflow inside lane core boxes, 87 % within 15 um of one; ln_9 alone 23.1 k. t39 p3: ln_10 + ln_13 21.5 k of 39.1 k.
- In 3_place.odb 6 of the 8 shared hi-quad banks (1,025 flops each) + the per-lane banks of ln_9 / ln_4 sit wrapped around ln_9 (gaps 10.8 to 28 um); std-cell utilisation of the free area there 0.76 to 0.88. Over a lane only M6-M8 route (M1-M5 OBS): V capacity 6-10 per 0.57-um gcell against 26 free.
- Lane core pins: 139 signal (80 N, 48 W, 9 E, clk + rst_n S). Hot gcells are over the core body.
- Tool gap: s81_hi_corridor.py `sites` checks the bank POINT, not the bank footprint (1,025 flops = about 95 x 12 um seated; 257 flops = about 47 x 6 um); face_flops.tcl ff_put_near does not exclude core boxes (the legaliser then pushes the flops into the nearest gap).
- Variant A (moves only, CS_HI_GS 2) is expected to stay OVER: on plan_l2_ft_safe_seated_1121.json the estimator at GS 2 gives 2 of 8 shared banks inside a core (quad 0 s1 in ln_12, quad 3 s1 in ln_10) and worst ratio 35.6, because the shared bank goes to the centroid of the per-lane sites. At GS 0 it is OK (0 banks). Variant B is the coherent form.
- Scripts and raw outputs: rtx-pro scratchpad leafr3/ (d1.py congestion vs core boxes from a kit dir; d2.py / d3.py on a geom_dump tsv; d4.py / d5.py plan checks; sv.py family survey). Geometry dump of the t44 baseline: epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3x/gd_t44/geom.tsv.

## Units
- Cancelled 05:3x by exact unit (flat GRT over 2+ rounds, evidence in the 05:4x post): t39 p3 oth-ubuntu-1875107, p1 oth-ubuntu-2178345, p2 oth-ubuntu-3896596. Kit dirs kept.
- Variant A bind: DONE 05:40, BIND_RC=0, LATCHECK 873/873 PASS (epyc7 lever2/bind_rtA; the unit's exit 2 is the trailing grep).
- Variant B bind (moves + GS0): unit oth-ubuntu-761898-1795267913 on epyc7, admitted ~05:55, client PID 4191487, log lever2/rtB2.otrun.log (ELAB then bind then LATCHECK, about 1.5 h).
- Kit A: chain on intel2 PID 2876997, /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3x/chain44.sh w44rtA (log w44rtA/chain.log): kit_wave run-item (gen + place on epyc7) then run_kit.sh route via ot-run --mem 56.
  Kit dir epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3x/w44rtA/root/items/ot_s81sl_leaf__t44__clf6cf8492/attempt_1/gen/ot_s81sl_leaf__t44__clf6cf8492.
- Kit B: after the B bind passes: on intel2 `bash -s B < mkw.sh` (scratchpad leafr3/mkw.sh; makes w44rtB/spec.json from w44mv/spec.json with src_rtB / bind_rtB), then `nohup bash chain44.sh $D/w44rtB B-gs0`.

## COORD ruling d442c09bb6e (env parity)
- Spec gen_env / gen_args of w44rtA against live autopilot/kit_wave.json dies.s81 (envd.py): equal except OT_CELL_WAIVER=r703 (added by kit_wave at launch), OT_SIGNED_VIEW_SHA and --clock-landing pointing at the J5 tree instead of J6 (the proof base is J5, same as the 60.2 k baseline kit).
- STILL TO DO before quoting any GRT number: diff the generated config.mk, kit_effective_env.json and flow_tag of kit A against the J5 wave kit work dir on epyc10 (path above) and post the diff.

## Read plan
- Kit A / B: sum of the congestion: field of congestion-10.rpt (and whether the report is capped at 20,000 entries); baseline 58.9 k to 60.2 k; target < 1,000. Then run d1.py on the kit dir (where the overflow sits) and a geom_dump of 3_place.odb + d2.py (bank positions, utilisation).
- If B < 1,000: let it route; sign-off gates; then the generator.

## Generator: tools/die_plan/leaf_regrid.py, WIP, NOT on main
- Lane clone epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3x/repo, branch fable-fix-s81-leaf-r3-regrid, commit 878c4d76b4 (base main b8c28cb918). Copy: rtx-pro scratchpad leafr3/leaf_regrid.py. No tests yet, not pushed.
- Commands: slots / apply / check (see the docstring). apply = lane slots in columns parallel to the vn face on the lane side (col gap 28.08, row gap >= 25.92, 12.96 to non-lane cores, clear of ft sites, strip >= 43.2 with the slack added), Hungarian by displacement, s81_hi_corridor.move_lanes, per-lane hi / ho sites at equal arc on face -> strip -> row gap -> pin (GS 0 form), seat (8.64 um off every core). A type that is refused keeps its rows.
- Run on the J7 base (epyc10 s81-j6/candC1n_pf plan_h2_2249.json; outputs fable-fix-s81-leaf-r3x/plan_regrid_c1n.json sha bf90a3f4d034..., regrid_c1n.json, apply.out, slots.out, sv.out): 79 types with cores (75 leaf + 4 kv_leaf).
  - 39 moved; on all 39: 0 station / relay / start sites inside a core, lane-lane gap >= 28.08, t44__clf6cf8492 gets 16 slots on the same 3 columns R3 drew by hand (4.32 / 146.88 / 289.44).
  - 26 of the 39 pass every hard gate. 13 fail only on a non-hi/ho row hop over 405 (407 to 509 um: t17 t21 t24__cl2456157b t33 t37 t43 t44 x2 t51 t60 t68 t71 t73): rows that ride a lane; istation_clear.py --grow / a +1 station is the next step for them.
  - 2 refused on the hi hop (t1 425.5, t4 463.2): need +1 hi stage (s81_hi_corridor sites --add-stage logic).
  - 38 refused for slots: only 2 columns fit beside the vn face and they hold 7 to 15 slots (list in slots.out). They need the 2-D form: slots north / south of vn (or a third column over the strip side), with the path going round the vn corner. NOT WRITTEN.
- bank_spill is an ADVISORY estimator (flops per 4.32 cell at half the station comb, spread to free cells); it says PILE-UP (50 to 80 um) on 36 of 39 and is not calibrated: calibrate on kit B's 3_place.odb dump (d2.py bank extents) before using it as a gate.
- Still to do: (a) 2-D slots; (b) +1 stage for the hop refusals; (c) driver that runs apply -> istation_clear -> leaf_slot_clear -> vp_sr re-solve -> reach_rules.py fix --rules 1 -> taps -> fstart_reset_delta.py -> check, with bind tools == gen tools; (d) tests + ot-push-main; (e) GS 0 restage of die_b178_lfcs.v for every leaf word (stage_lfcs_netlist.py refuses on the kv_leaf XR mask; R3 edited one word by copy+mv); (f) ff_put_near must skip station-grid cells under core boxes, and s81_hi_corridor `sites` must test the bank footprint; (g) rows to S81-J6-ASSEMBLY-R3 with the exact base plan (J7 Layer C), only after t44 proves in a kit.

## Other rows (unchanged from R3)
- Keys + reset legs: J7 material. FSTART local resets: Codex donor epyc10 s81-j6/rows/j7_leaf_local_reset (52 types). CFX bench passes on 4 define sets.
- Wave rows t39 / t28: deliberate HOLD until the lever-2 form is proven (relaunch as item@N:fix=lever2-regrid-gs0).
- kv_leaf t2 / t5 belong to FAM-S81-MISC-R2: take their t5 re-sites, do not duplicate.

## Cleanup (ot-delete only, after the proofs)
R3 list in OPUS-FIX-S81-LEAF-R3.md, plus epyc7 fable-fix-s81-leaf-r2/p3, fable-fix-s81-leaf-r3/p1, p2 (cancelled kits), epyc7 + epyc10 fable-fix-s81-leaf-r3x/gd_*.
