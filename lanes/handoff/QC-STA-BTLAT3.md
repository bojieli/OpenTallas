# QC-STA-BTLAT3 handoff (Opus 5.5, child of QC-ALLFIX; COORD job from FABLE-RC-QC 00:14 RC st_a (b)). Report to QC-C1O-COMPOSE + QC-ALLFIX, cc COORD.
Job: two st_a rows for C1o (cut 03:00, ROW-READY by 02:45): STA-BTSEAT (g_read q + u_sel relay_sites at the btab stack W face, 11 types)
and STA-BTLAT3 (OT_BTAB_RQ request-leg register, region masters _bt2 -> _bt3 BT_LAT 3, v2 types only; v1 waits for RC97-V1).
Lane dir epyc2 /srv/opentallas-scratch3/claude/QC-STA-BTLAT3 (repo = lane clone, tree/tree2 = forks of QC-STA-PROBE tree + C1n overlays,
rows/ = plans+deltas+guards, cores/ = 3 _bt3 child kits, bin/ = mk_bt3.py, scopedB*.sh).
## 00:5x state
- main 636f4081887: btab_s4 OT_BTAB_RQ + bench run_btab_rq.sh (PASS == safe delayed 2; one-delay FAILs), qc_fabric_transport BT_LAT 3 (fail closed),
  tests 6/6, tools/die_plan/qc_sta_btlat3_row.py.
- Plans: C1n 26036a + both rows = 53ef32342357 (seats only 5e74a727732b, bt3 only 8e1408c25ecb); guard OT_COMPOSE_DROP=fail PASS 0 silent, sidecar PASS.
  C1n-r c26a + both = 36b6bcd290f8 (guard PASS). C1n-r2 a372 + QC-STA-HOLD PRUNE 960d3bc44689 + both = c33240972f9d.
- Scoped --crit strict bind of 11 st_a: sb/ (plan 53ef, unit oth-ubuntu-739299-1795595982, log scopedB.log); sb2/ (plan c332, tree2) after fork2.
- Core kits _bt3 (h17_n7_s8, h18_n7_s8, h15_n9_s11) on epyc2 via ot-run, logs run_<m>.otrun.log; views go to physical/die_plan/qwen_compute/qcviews_btlat3/<m>/.
- Latency: 0 lane / core_latency change; compiler table = stn_transport_params from the bind (hook bt_lat 3 -> result/busy +2).

## 2026-11-25 02:09 PST update
- Superseded: 53ef / d0f63 (rq seats at stack face: 584+117 um). Generator main ec0881df03b seats rq flops at midpoint (347+355 um, asserted <=405).
- Current rows: C1n + both = 3c5b379130e0 (guard PASS 0 silent, 0 new collisions); C1n-r2 + both = 4557d9ec3716 (C1o row).
- PRE on 4557 running on intel1 (rt 899f launch view, --priority die), log intel1 /srv/opentallas-scratch2/claude/QC-STA-BTLAT3/pre.log; d0f6 PRE cancelled at 2962 s with 0 FAIL lines.
- _bt3 masters SIGNED + LEC EQUIVALENT (TT +28.0/+17.74/+30.58, DRC 0); views epyc2 /srv/opentallas-scratch3/claude/QC-STA-BTLAT3/views, copied into intel1 tree qcviews_btlat3.
- epyc2 tree deleted (ot-delete). intel1 tree: ot-delete same hour PRE/scoped bind finish (QC-ALLFIX disk ask).
- v1 (6 types): C1p row note posted (RC97-V1 by QC-STA-CLK first, then STA-BTLAT3 unchanged).
