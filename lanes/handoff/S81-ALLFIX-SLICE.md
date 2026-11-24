# S81-ALLFIX-SLICE handoff (Opus 5.5; from 11-23 16:29 PST). FAMILY lane, posts -> S81-ALLFIX-INT.
Brief: scratchpad allfix_brief.txt + resume_1123e.txt. Base B1 post-tail ae3101241d6b (b1_tree E10). Lane dir epyc10 /srv/opentallas-scratch2/claude/s81-allfix-slice (row.sh = compose + tail copy + PRE; in/ ops; rows/<tag>/).
## Census vs B1 (measured)
- IN BASE: rc28 rc29 rc30(plan) rc31 rc32 rc33-C rc34-C hop-sliceC (Wave A slice chain); rc34-LP R1; rc36 SP-W2+XGARRAY-1 LP (mu_LP t2 contents/taps identical); rc37 F2/N1/N2/RS1.
- ROWS (epyc10 rows/): tpcap (rc35 af658d95d0f9), pt1 (rc33-LP PT1 ops b9a2fab893de), vnb (KVLEAF-VNB-HARD-1 v2 d8156e224c7e), lepw (rc33/rc34 lepw LP: lpsplit + apply_rc33). Logs rows_<tag>.otrun.log.
- rc37 LP-PROFILE-1b: FABLE-OPEN-S81-A B1 PRE PASS plan 301aa03b2751; LK1 on B1 wrappers = lk1/lk1_b1_out.json b13345f8a10e (same price as e49ee45a5ca1).
- Leaf: adopted S81-LEAF-J9 BL1 0d01d7ccb385 (PRE FAIL 14 LANDREMAP). Fix leaffix2.sh: repick_types.py (common landing depth, -1 on 7 types) + nearreach.py (6 IST-LEAFDN-VP rows re-sited M 8 um, 0 cycles) -> rows/leaf/r2_near.json; log leaffix3.otrun.log.
- rc8 CRR_PRE2 + rc9 SELREP: RTL carry rows posted to INT (vp.sv 2a7dbb06ab12, slice.sv 36236edd9c48 from s81-leaf-j9/tree_c5; die define OT_S81SL_CRR_PRE2).
- kv_leaf t2: ROW-DROP posted (die fit + view-pending masters + stage RTL); owner MISC-SERDES-J9.
- COORD: leaf kits OT_GPL_OVERFLOW=0; iqf__t1 excluded (BL1 regex leaf only).
## 19:1x
- Batch 1 ROW-REBASED PRE 0: tpcap 2d5e21b9501f, pt1 40b567b4c4a0, lepw eb3efa2c89c3, vnb 5dea7d173b54 (post 521ebc1a). Leaf r2_near 8ce96cfc7c52 PRE 0 but G0 schema-stops on 5 t55/svc_13 seam ports (C4 t55 in old frame). Fix: in/ops_t55revert.json 81ecc8dfed2c (t55 -> B1); check rows/leaf2 (rows_leaf2.otrun.log) running tail+PRE+G0. INT told (bc6ce7c3). t55 handed back to LEAF-J9.
- INT c4 (E9 s81-allfix-int/c4) already composed my rows.
- KVLEAF-T2-SLOT (COORD 19:00 4700.16x1918.08): ROW-DROP posted 1e439ed5 - die re-floor (station E-W chain tl/ca/cb at die y 23911-24093 blocks station shrink; width needs east-half shift + die +25.92). Proposed ASSEMBLY/INT die event 11-24.
## For S81-T2-REFLOOR (COORD 19:12)
- Census: epyc10 /srv/opentallas-scratch2/claude/s81-allfix-slice/rows/t2fit/census.json sha 8e45f60a22ac (base B1 ae3101241d6b).
  - Max local slot 4527.36x1226.88 (west gap 13608.0..13754.88). Target 4700.16x1918.08.
  - Width: +172.8 east (east-edge slack 146.88) -> east-half shift (183 partitions, 60 seam ports cross) + die width +25.92 (857.3 mm2).
  - Height +691.2: north stacks of cols 2-4 (12 parts + 3 stations); 55 ports cross the moved set incl t2 itself; stations t46/t47/t48 carry 28 chain ports (tl/ca/cb E-W at die y 23911-24093 into s_1N_x06/s_0N_LP + xtier/unit/flt N-S legs to gunit/bk_sel) -> cannot shrink.
- Seating: intel2 ~/coord/lanes/handoff/S81-KVLEAF-T2-ARCH-R2-partb_seats_v3.json (COORD 19:35: v3, not v2). Seat-import reference: epyc10 /srv/opentallas-scratch2/claude/s81-misc-serdes-j9/t2row/t2_row.py (v1/Codex form, part A from t5 + VNB ops).
