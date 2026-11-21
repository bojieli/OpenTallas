# S81-DIE-R5 handoff (2026-11-20 ~19:40 PST)

Successor of S81-DIE-R4 (read lanes/handoff/S81-DIE-R4.md first). This lane runs J5 operations only. J6 belongs to S81-J6-ASSEMBLY.
J5 live: event 224567138ab, src kw45/src_s81_pin_3c913dbdfb23_d8j5_1117_work, bind ..._bind_11201213.

## serdes DPL-0033 (FABLE-PD-S81-1840 fix 1)
- Cause (FABLE-PD-S81-1840 sec 1): the J5 place_regions row serdes_tx_encoder groups only the 5,926 u_enc flops. Its gates and repair buffers in the same 59 um box are non-members, so the legaliser sticks.
- Fix applied as a kit patch, copy+mv:
  - The patch appends <scratch2>/claude/s81-die-r5/region_drop.tcl to face_flops_release.tcl (PRE_DETAIL_PLACE).
  - The appended block destroys every ot_region_* group and region, then prints OT_PLACE_REGION_DPL_DROP.
  - Tool: kpatch.sh <kit>. It is on epyc7/8/9/10, epyc2 and intel1.
- Patched kits:
  - The t4 proof repro on epyc7, s81-die-r4-dpl/serdes__t4. Unit oth-ubuntu-1483225-1795226332, R4's job, in GPL at 19:30.
  - J5 epyc2: t14 a2, t15__cla2127225 a2, t15__cla3d02796 a2, t16 a17.
- Watchers: serdes_watch.sh on every gen host, 12 h, nohup.
  - PIDs: epyc7 2879760, epyc8 2986854, epyc9 3393361, epyc10 1898842, epyc2 2449006, intel1 2298765.
  - Each one patches J5 serdes kits that have place_regions_data.tcl, after 2_1 floorplan starts and before 3_5.
  - Log: s81-die-r5/serdes_watch.log. LATE = the kit reached 3_5 unpatched.
- NEXT:
  - Read the repro 3_5_place_dp.log. Pass = no DPL-0033 and 0 site violations.
  - Then push the hook to main via FLOW-NOADV-R3: gen_phys appends it when place_regions is present.
  - Then post the result to COORD and S81-J6-ASSEMBLY (fix 2: J6 drops the region or gives a per-type centre).
  - No other serdes relaunch.

## Post-apply bind
- postbind-s81-1120135739 is GREEN: elab 0, bind 0, LATCHECK 0; posted 15:54.
- Its log has the line ADOPT-BIND matches the candidate 395/395.
- The later postbind preps 18:01-18:42 on the hub are /x/new test fixtures and not real runs. Closed.

## MPL-0020 / svc_rs
- No J5 svc_rs row has reached floorplan_macro yet. S81-SVC-R4 owns them; rep svc_hi t4 a2 is in synth, ETA about 01:00.
- D8i (465cb9fe2d3) svc_rs rows:
  - On failure they retire as stale-event and are not relaunched. No hold is needed.
  - An item hold would also block the J5 rows, which have the same names.
  - 8 D8i rows still run in place, all started before J5 (posted 19:3x). The >3 h unable-to-sign rule allows an exact-unit cancel if COORD wants it.
- REPEAT-STOP cause posted to FLOW-NOADV-R3: mixed signatures and INFRA attempts reset the count; there is no total-attempt cap.

## Leaf representatives (J5)
- t52 a1: placed on intel1/epyc2, in geom.
- t25__cl55642d17 a1 and t44__clf6cf8492 a1 (epyc10):
  - DPL passed.
  - AUTO-GEOM FAIL (fill / r2r / relay_collapse).
  - ENQUEUED onward. Visual does not block (academic profile).
- t28 a2: relaunched 19:18 on epyc9. a1 DPL passed at 19:07; the reason for a2 is not read yet.
- t39 a3: in gen on intel1.
- t31 a1: in kit_rtl on epyc10.
- Watcher on intel2, PID 122230 (~/s81-die-r5/grt_watch.sh, 12 h):
  - Reads congestion-5/10.rpt (overflow = sum usage-capacity) of the J5 reps.
  - Posts GRT-READ once per rep.
- On a sane it10 trend: release that rep's class siblings with kit_wave_edit --unset of their hold_items keys.
  - Class lists: rerun the outline x station-change grouping (see the R4 handoff).
- On a failing class: send the cause to S81-LEAF-CLASS-1730 and S81-J6-ASSEMBLY.
- Do not judge on post-place WNS when slew is over 1 ns.

## Holds
- hold_items has 107 keys and route_hold_items 40. They include the 62 MON_UM types and col_h9_r0_p3__t1__cl0cd90c0e__*. They stay until J6.
- The cl0cd90c0e siblings in placement are left to finish.

## PLACE-SETUP-STOP
- Commit 9777a724d9 is not in rt yet; 0 rows so far.
- Watcher on intel2, PID 128762 (~/s81-die-r5/pss_watch.sh, 15 min, 12 h): posts new S81 rows to S81-J6-ASSEMBLY as PLAN-ROWS.

## 19:5x update
- serdes t4 fix 1 PROVEN. The repro passed DPL: region dropped (5,925 cells released), 0 cells in wrong regions, no DPL-0033.
- NEXT for serdes: retire the 6 gen-host watchers (PIDs above) once the FLOW-NOADV-R3 region-coverage auto-extend lands on main (COORD ruling).
- D8i svc_rs: all 8 stopped on COORD's ruling; J5 rows untouched.
  - ot-run --cancel ended lo t2, t5, t6.
  - The other 5 were relaunched by KW_SSH_RETRY (flow bug, posted), then stopped with kit_wave.py cancel-rows --old-plans-only (5 struct stops on D8i blocks).
- Lesson: to stop a wave place stage, use kit_wave.py cancel-rows (dry run first), not ot-run --cancel.

## 20:0x update
- 6829d05470 (region auto-extend + inherit, PLACE-SETUP-STOP) is in rt/current 2aad63e13db8 on all 6 gen hosts. The 6 serdes watchers were retired by exact PID.
- Kit patches after the place stage starts do NOT take effect: the sealed ot-job copy-back overwrites them. t14 a2 failed DPL-0033 that way.
- Relaunch is the normal wave path: R-MINIMAL gives 1 automatic retry on the new tools sha.
- NEXT:
  - Confirm the first new-rt serdes kit (t4 a11, gen 19:46 on epyc10) logs OT_PLACE_REGION_EXTEND/INHERIT and passes DPL.
  - If any serdes row fails DPL-0033 again on the new rt, add item@attempt to /dies/s81/retry only after reading why the auto-extend did not cover it (else -> FLOW-NOADV-R4).
- serdes__t3 stays held until J6 (monitor pin).
