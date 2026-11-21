# FABLE-FIX-S81-LEAF-R3 handoff (Fable; succeeds OPUS-FIX-S81-LEAF-R3 2026-11-21 05:24 PST; owns ot_s81sl_leaf__t*, proof type t44__clf6cf8492)

Read order: this file, lanes/posts/FABLE-FIX-S81-LEAF-R3.md, lanes/handoff/OPUS-FIX-S81-LEAF-R3.md (lever2 paths), FABLE-PD-S81-0440 C3.
NOTHING IS SIGNED. State 2026-11-21 ~06:25 PST.

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

## Generator (open; promised to FABLE-PD-S81-0440 C3, J7 Layer C; J7 cut 11-22 04:15)
tools/die_plan/leaf_regrid.py, lane clone epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3x/repo (main b8c28cb918, cone tools + physical/common_flow). J7 base plan: epyc10 /srv/opentallas-scratch2/claude/s81-j6/candC1n_pf/physical/die_plan/s81/plan_h2_2249.json (ask S81-J6-ASSEMBLY-R3 for the composed J7 base).
Survey of that base (epyc10 fable-fix-s81-leaf-r3x/sv.out): 75 leaf + 4 kv_leaf types with cores, 75 distinct floorplans; every type has 8 to 34 lane gaps under 25.92 um (min 2.2 to 19.4); estimator OVER on 74 of 79; lanes are on the W side on about 30 types and the E side on about 45.
Steps per type (generalise lever2/l2_plan_ft_safe.py, which has fixed t44 columns):
1. Lane slots: columns parallel to the vn hi pin face (from_um of the hi rows), column gap 28.08, row gap >= 25.92, on the 4.32 grid, clear of non-lane cores and ft bit sites / ft regs; 16 nearest slots; Hungarian by displacement.
2. s81_hi_corridor.move_lanes (rigid riding records), then per-lane hi / ho sites on the strip + row-gap path (GS 0).
3. istation_clear.py, leaf_slot_clear.py, seat (sites within 8.64 um of a core edge pushed out; the R3 seat script was inline and is not on disk: rewrite).
4. Re-solve on the moved cores: vp_sr stations, reach_rules.py fix --rules 1 (start stages), taps (s81_hi_corridor.clear_added_taps / tap rule), fstart_reset_delta.py (reset anchors), with bind tools == gen tools.
5. Checks per type, all must pass: 0 register sites inside a core; every bank footprint (bits x 0.58 um2 at the station comb) fits the free channel area around its site; min facing lane gap >= 25.92; every hop <= 405; strip cut load (lanes beyond the cut x 257 bits) under the strip V tracks.
6. GS 0 for the family needs LF_CS_HI_GS / LF_CS_HO_GS 0 on every leaf word of die_b178_lfcs.v; stage_lfcs_netlist.py full restage refuses on the kv_leaf XR mask (R3 edited one word by copy+mv): fix the tool or add --update HI_GS,HO_GS.
Also wanted on main: ff_put_near must skip station-grid cells under hard-core boxes; `sites` must test the bank footprint.

## Other rows (unchanged from R3)
- Keys + reset legs: J7 material. FSTART local resets: Codex donor epyc10 s81-j6/rows/j7_leaf_local_reset (52 types). CFX bench passes on 4 define sets.
- Wave rows t39 / t28: deliberate HOLD until the lever-2 form is proven (relaunch as item@N:fix=lever2-regrid-gs0).
- kv_leaf t2 / t5 belong to FAM-S81-MISC-R2: take their t5 re-sites, do not duplicate.

## Cleanup (ot-delete only, after the proofs)
R3 list in OPUS-FIX-S81-LEAF-R3.md, plus epyc7 fable-fix-s81-leaf-r2/p3, fable-fix-s81-leaf-r3/p1, p2 (cancelled kits), epyc7 + epyc10 fable-fix-s81-leaf-r3x/gd_*.
