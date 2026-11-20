# FABLE-FIX-S81-LEAF-2140 handoff (Fable; owns every ot_s81sl_leaf__t* and ot_s81sl_kv_leaf__t* type)
Predecessor: lanes/handoff/FABLE-FIX-S81-LEAF.md (Opus lane, closed 11-19 21:45). Work dirs B = /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-2140
on epyc9 (trees, kits), epyc7 (j4 rows), epyc10 (lane clone B/repo). Hub logs D = intel2 ~/lanes-fable-s81leaf-2140.

## State 2026-11-20 02:30 PST
On main (mine): 0747cc824096 SWR station tests (restage tool is 6ac236963d: stage_lfcs_netlist.py PLAN NETLIST OUT --update SWR_D);
a6e4c44e8cb0 + 6cf5fa3beeaf corridor tap rule = the bind's rule, runs under -I; 069b960d0b85 keep_firm ft flop on a tap / edge cell released for DPL
(t21 / t60 DPL-0033); 5287da7b29cd sites: a refused quad keeps its old rows, and sites --add-stage (+1 per-lane hi stage on a refused type).

Rows handed to S81-DIE-R3:
- SWR: lanes/handoff/S81-LEAF-SWR-STATION-ROWS.json (5 types) + the restage command. Strict bind with them passes on tree CW (LF-CS gate, LATCHECK 873/873).
- Bank sites: lanes/handoff/S81-LEAF-HI-ROWS-J5.json.gz on plan_j3 f925a42b1336 (whole plan epyc7 / epyc9 B/j4/plan_j4b.json e73254a139b4).
  44 types HIGH (sites only), 26 MEDIUM (+1 hi stage, hi depth 4, full LF_CS_HI_D restage; no bind yet), 9 for J6 (kv_leaf t5, leaf t1 t2 t3 t4 t5 t8 t17 t35).
- WREG: lanes/handoff/S81-VPW-WREG-ROWS.json. Use OT_S81SL_VP_WREG in the die-wide asbuilt defines (the die bind does not elaborate per-type defines)
  after s81_vpw_wreg_overlay.py on the tree. Tree CW binds strict and passes LATCHECK 873/873 with it, so no priced latency row was needed there.
  Function: leaf_bench + beat_bench PASS with XR + WREG (epyc9 B/wregb/out).
- Do not use plan_j4a or plan_famC 750f33553a0e (made before the refused-keeps-old fix; rows over 405 um).

Measured so far:
- Control tree_C (Opus, sites only) t31: PLACE-HPWL 1.001 x, CTS TT setup -1,026.8 (no WREG in it), GRT started 01:3x. t28 in CTS.
- Live-plan failures: t21 / t60 keep_firm (fixed, wave relaunched 23:33); t42 DPL-0033 on shared-bank flops; t37 / t47 / t51 / t52 PLACE-HPWL stop 1.40-1.57 x.
- Estimator (s81_hi_corridor check) says OVER on almost every type under every form (C, A, add-stage). It is NOT calibrated against GRT yet.

Running / queued (epyc9 is out of memory; every launch waits on ot-run admission, do not relaunch):
- Trees: B/cw/tree_CW (plan 0251647be92c: famC sites + SWR + WREG) and B/aw/tree_AW (plan c94729828ffe: form A on t28 / t31 / t60 + SWR + WREG).
  Both strict-bound, LATCHECK 873/873, PRE PASS, kb_d8i/.keep_stage_odbs present (one CTS pass).
- GRT queued: CW t28, t31 (D/cw_grt_CW_*.log), AW t28, t31 (D/cw_grt_AW_*.log), control C t28, t31 (~/lanes-opus-s81leaf).
- D/cw_par_hub.sh: parallel kit gen on CW for t42 t52 t37 t47 t51 t21, then GRT launch each; then patches (B/kf_patch.py) and launches CW t60.
- D/cw_more_hub.sh AW: after the AW kits, patches and launches AW t60.
- D/j4c.log: form A + sites --add-stage on the 9 J6 types (B/j4c.sh), queued. Output B/j4/plan_j4c.json.
- Wave rows waiting on epyc2 admission since 22:2x: kv_leaf__t2, leaf__t38, t50, t57 (asked WAVE-PILOT-FIX to respill).

Next, in order:
1. First GRT read (control t31, then CW / AW t28 / t31): CTS passes = 1, GRT overflow + extra iterations, TT setup / hold. State how far the estimator is from GRT.
2. Decide the form per type from that read: C where GRT closes, A + sites --add-stage where it does not. Post the decision and the J6 rows.
3. t60 on CW and AW to GRT TT (deliverable 2 names t28 / t31 / t60).
4. CW kits of t37 / t47 / t51 / t52 / t42: do they pass place? If the HPWL stop still fires with banks in channels, fix the stop rule (compare from overflow <= 0.3 only).
5. Sign-off + export (AGIdock /archive, rtx-pro ~/signed-export-1114) once a kit meets DRC 0, TT >= -42, hold >= 0. None has yet.
