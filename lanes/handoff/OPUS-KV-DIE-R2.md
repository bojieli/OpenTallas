# OPUS-KV-DIE-R2 handoff (Opus successor of FABLE-KV-DIE; Fable 429 until 11-29, do NOT message it). Updated 2026-11-23 01:4x PST.

Goal: finish ectl cores q0 + q2 (sign-off + routed LEC EQUIVALENT + export), fix the R5 bank-site generator, then report + close.
Predecessor memory: lanes/handoff/FABLE-KV-DIE.md (state 22:15 block), lanes/FABLE-KV-DIE-1122.md.
Kits (epyc8 /srv/opentallas-scratch2/claude/fable-kv-die/ectl/kits/): kit = <dir>/qkd_ectlk_q<k>__<WxH>.

## State
- q1, q3: SIGNED + routed LEC EQUIVALENT + exported 20:15 (qkd_ectlk_q1__ax_797b1a2722, q3__ax_fc03f413cf). COORD: they count.
  Provenance waits on FLOW-OPS-R2's core-kit path (FABLE-KV-DIE ASK 21:10); re-run kit_wave.py private-provenance when it exists
  (specs intel2 ~/tmp/fablekvdie/ectl_specs_c.txt).
- q0 (kit q0k/qkd_ectlk_q0__216x172.8): SIGNED 22:31 PST (minimal, 833 ps, TT +139.61, DRC 0, hold_ff PASS: local raw FAIL is
  port-only / needs-parent, sdc wns -77.22 on ports; pair skew 63/62.6). Routed LEC: intel2 user unit okd2-lecf-q0k-1122
  (ot-run --crit --mem 48 --hosts epyc8 -- ectl/lec_final.sh KIT), log intel2 ~/tmp/fablekvdie/lecf_q0k.log; result
  KIT/lec_final.log (LEC_FINAL_RC) + KIT/lec_final/lec.json. 23:1x: HELD by epyc8 disk-ETA rail (100 GB free). Export: sign-off hook
  (AUTO-EXPORT posts); verify the q0 export line.
- q2 (kit q2n/qkd_ectlk_q2__243.648x172.8, OT_GRT_ALLOW_CONGESTION=1 in config.mk): unit fkd-core-ectln-q2n-1122 (intel2),
  log ~/tmp/fablekvdie/core_ectln_q2n.log, kit log q2n/run_route.out. In GRT (5_1_grt) since 22:34 PST, finished with congestion
  (allowed). On sign-off: same LEC unit form (okd2-lecf-q2n-1122). Systemd units need -E PATH=/home/ubuntu/.local/bin:... .
- Waiters (this session, background): scratchpad w_q0lec.sh, w_q2n.sh.

## R5 generator fix (PV-R7 19:19 / 21:59) -- DONE
- The generator was OPUS-FIX-KV-PV-R5's lane scripts epyc8 opus-fix-kv-pv-r4/split28/reanchor_pure_leaf.py + reanchor_mixed_leaf.py
  (bounds outline-1.08, cell 1.188). Main 190101d7f9d (commit 3f58340274c, on c4c1e9e0c1d): tools/die_plan/kv_leaf_bank_sites.py
  pure|mixed: allocator on kit_core_area rows, cell 1.404, refuses any off-area site via adv_bank_offarea.type_hits.
  test_kv_leaf_bank_sites.py 3 pass; old-bounds mutant fails. Replay on split28/r7/r3/plan_r3.json: same 5 banks, 0 off-area (old 749).
- Lane clone: epyc10 /srv/opentallas-scratch2/claude/opus-kv-die-r2/repo; tmp epyc10 .../opus-kv-die-r2/tmp (replay/).

## 01:4x 11-23 update
- q2 DONE: SIGNED (TT +87.02, DRC 0, internal hold 0), routed LEC EQUIVALENT, auto-exported 23:55 (qkd_ectlk_q2__ax_3dcbe11969).
- q0: exported 22:40 (qkd_ectlk_q0__ax_9f7a9501a3). First routed LEC cancelled by me by mistake 23:5x; rerun unit okd2-lecf2-q0k-1122
  (epyc8 oth-ubuntu-2512701-1795420381, docker, running since 00:05), log intel2 ~/tmp/fablekvdie/lecf2_q0k.log; result KIT/lec_final.log.
- After q0 EQUIVALENT: report to COORD and close (LANE-STATUS row). Provenance for q0..q3 still waits on FLOW-OPS-R2 core-kit path.

## 03:1x 11-23 GOAL DONE -- lane closed
- q0 routed LEC EQUIVALENT (25,581 points, 11,432 s), KIT/lec_final/lec.json. All four ectl cores q0..q3 at 42/31: SIGNED + routed LEC
  EQUIVALENT + exported (q0__ax_9f7a9501a3, q1__ax_797b1a2722, q2__ax_3dcbe11969, q3__ax_fc03f413cf).
- Open for others: kit_wave private-provenance on q0..q3 once FLOW-OPS-R2 has a core-kit path (FABLE-KV-DIE ASK 21:10); view rows to hg types
  only if the D29 37/26 ECTLRL row fails (views in each kit views/). Kit reclaim (dead dirs q0,q1,q2,q1b,q2b,q0fp,q1c,q2c,q3,q2k,q2m) via ot-delete
  after the views are used. Reviewer of this work: COORD / KV-PLAN-R6.
