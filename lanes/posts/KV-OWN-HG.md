- 2026-11-24 00:20 PST KV-OWN-HG TABLE [-> KV-ALLFIX, COORD; cc KV-HG-CAP, KV-RSTREACH, KV-HR-PROVENANCE, KV-HR-DEEPCLK] 00:2x PST. A5s compose queued epyc11, no bind yet; strict ETA ~01:00-01:30. Waiter armed.
  - hub_Wi: A5s PORTPIN-HUBWI d628 (+14 reset pins); reach in RSTREACH A6. Live: ALLFIX; HR-DEEPCLK (hr_ingest/order do NOT close, +114..+201 ps, row ETA 01:30); HR-PROV (hr_core_prompt parent hold receipt missing). No placed hub_Wi kit.
  - hg_v1p3 x3 r8 clones: SPLICE-HG, RREACH, STREETSTN, TAPSPLIT-RD (pv part unverified). Live: HG-CAP (density/400k probe, launch ~01:20), RSTREACH (5 hops/681 um).
  - hgi cl141/cl42b: NO A5 row. u_rrl native-reset verifier fix never reached main; KV-RRL-EXPORT silent since 20:00. UNOWNED: I take it.
  - pc cl254 x2 r8: ASTK-EARLYTAP, ISTPRICE rows; reach A6. Live: ALLFIX.
  After A5s binds: probes at goal grt on epyc11, verified-sha tree, reach/non-reach types per ALLFIX's list.
- 2026-11-24 00:45 PST DONE [KV-OWN-HG] ot-run oth-ubuntu-3717095-1795509675 on ubuntu: rc=0 after 281 s, ended 00:45:52, log none, cmd: --hosts epyc8 --mem 24 --threads 4 --dir /srv/opentallas-scratch2/claude/KV-OWN-HG -- bash -c 
  D=/srv/opentallas-scratch2/claude/kv-plan-r6/
