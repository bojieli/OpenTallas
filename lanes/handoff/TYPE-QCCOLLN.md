# TYPE-QCCOLLN handoff (2026-11-14, lane for qwen_compute/coll_n, job 7d79f8c65d41)
- Failure: DRT-0255 in DRT iter 1 (after iter0 13221 violations, 3:45 h); wave kit intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q102B0/items/coll_n/attempt_8/gen/coll_n
- Cause found: kit HAS pg_track_truth.tcl + grt_pre hook, but config.mk has NO `export OT_PG_TRACK_TRUTH = 1` (hook gated ==1 in pg_track_truth.tcl), 5_1_grt.log has no OT_PG_TRACK_TRUTH line -> hook never ran. Class: QC wave src gen_phys RFLOW did not export it for this kit (FLOW-PGCAP-1 says qwen_compute should) -> src predates pgcap.
- Forms on epyc10 /srv/opentallas-scratch2/claude/type-qccolln/{a,b,c}/ (run: bash run_kit.sh coll_n route 48 8, ot-run --hosts epyc10, logs intel2 ~/type-qccolln/{a,b,c}.log):
  a = hook on, resume.json start=grt from 4_cts.odb (fast); b = density 0.4 fresh synth; c = both fresh.
- Waiter: scratchpad qccolln-wait-1114.sh
- On pass: AUTO-RESIGN.tsv row, archive per SIGNED-RECOVER.md ARCHIVE HOW-TO, RESULT line. Kill losers by exact PID.

## fw_v1 pair (added 11-14 ~14:00)
- Pilot forms epyc10 /srv/opentallas-scratch2/claude/type-qccolln/fw/{a,b} on sle_fw_v1__clf58b4dfb; a=pgtt+0.4, b=a+no strap pins (io.tcl.orig_straps kept). Apply winner to slw_fw_v1__clf51c11d8__cl592e3d37 (epyc8 attempt_5).

## strap snap (11-14 ~15:00)
- patches in ~/coord/lanes/patches/QC-STRAP-TRACK-1114.py, test_strap_pin_track.py, QC-STRAP-TRACK-SNAPIO-1114.py. In-place snap DONE 141 dirs. TODO: branch+READY ROOT-MERGE-63 after hub clone epyc10 .../type-qccolln/wt finishes (apply patch to tools/die_plan, add test, commit).

## successor 11-14 19:30
- coll_n forms a/b/d dead ends (cancelled). fw a/b/c + cbn c wait for PG-AWARE-1 generator fix, then are proof builds (no blind relaunch).
- LIVE: cbn_q00__cld7bf7197 as-is + mirror place-only on epyc2 (run_kit.sh place 48 8, started 19:17, in floorplan 19:22; logs intel2 ~/type-qccolln/whatif_asis.log, whatif_mir.log; dirs epyc2 .../type-qccolln/cbn). GRT comparison after place finishes.
