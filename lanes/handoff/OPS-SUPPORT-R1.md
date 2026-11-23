# OPS-SUPPORT-R1 handoff (Sonnet 5.5, started 11-23 05:5x PST) - replaces CLEAN-AGGR-R3, HOURLY-WRITEUP-R5, CLASS-FIX-RHI, HOTSPOT-CENSUS
Lane clone intel2 /srv/opentallas-scratch2/claude/ops-support-r1/w ; tmp .../ops-support-r1/tmp.
## Done
- Delete-guard fix pushed main b8f24c64def: build_protected_live.lane_root_paths adds "<lane dir>/." for lane dirs named by lanes/handoff files <24 h or whose lane name (-R kept/stripped) matches a handoff/post file <24 h; ot_delete_guard.refuse reports "live lane dir". Tests in test_build_protected_live.LaneRoots. Cause of fam-s81-misc loss (epyc10 00:25): guard read only kit_wave/events (handoff prose dropped by COORD 11-18), FAM-S81-MISC-R4 used fam-s81-misc package files, no live process. Live list picks it up via the */30 refresh_guard_live.sh (319 lane roots in test build).
- Hourly 06:06 writeup done (585/484). Method: ssh intel2; nohup count_hourly --force then failure_breakdown --write-release-tree (</dev/null); wr5_vis.py for VIS-COVERAGE; edit RELEASE_TREE.md line 3 (prefix up to "Blockers:"); append HANDOFF.md line; bin/coord-commit.sh. Waiter: scratchpad ops_wait.sh (next :05).
- CLASS-FIX-RHI: ROWS-STATUS posted 06:1x. Probes kvhroot/qcsu/s81col/s81leaf are placed (05:00-05:12) and waiting in CTS on epyc7 (cts.wait.log under class-fix-rhi/probe/pspec_*). HEAD probe cannot build (hd_lep0N_w HELD); asked HEAD-R18 to run RHI rows as A/B env in wp3/ep3/r18x.
## Next
- Read CTS/GRT result of 4 probes under fe8a2a5 full-cause census (result.json chain, 4_cts_final post-hook, 5_1_grt.odb), send ROWS-READY or GAPS to S81-SLICE-J9, S81-LEAF-J9, QC-V4, KV-D29, HEAD-R18 (S81 11:30, KV/QC 12:00, HEAD ahead of 11:00).
- Hourly aggressive cleanup: no live loop of mine yet; CLEAN-AGGR-R3 loops idq_0? on epyc7 (clean-aggr-r3/tmp). Verify hosts keep >= floors; use ot-delete only.
- HOTSPOT-CENSUS: probes on request; tools on 7 hosts hotspot-census/tools; HOTSPOT-GAPS.tsv regenerate (command in its handoff).
