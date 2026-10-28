KV-PLAN-DELTA-5 (2026-10-27) single KV plan event on hm_r26q5c 7a03069b -> hm_r26q5c39 4190246956824a7a
(plan real copy: intel1+intel2:/srv/opentallas-scratch2/claude/kv-plan-d5-1027/{q5c_pd,pd}/hm_r26q5c39.json; cores/ = q5c dir)
Deltas: D-KV-PG-C39 (COORD ruling: c39 grid + PG-ACTIVITY-3 edge-fit bumps), D-KV-INGEST-42 (ingest_eng [4,2] core_tree islands,
ingest_eng_slice_42.json + ingest_eng_42.png), D-KV-X6-MODELED (record only). See event_d5.json.
Die GRT (TT+FF): overflow 0 on M4-M9 at -congestion_iterations 50 -critical_nets_percentage 0; continuous mesh with 2048 vias, 0 PG shorts (chainC.sh).
Die STA: shared main die_sta_related (1907eb530), own mesh MC 24 samples. Results in sta/G39{,_ab}.{log,json.gz} (sta39.sh).
PG candidate solves on the canonical deck (ir_*.json, colo.py), co-located, +6.05 below M7:
  A 38.88 FAIL, B 28.04 PASS, C 43.80 FAIL, E 33.14 PASS.
  B: the q5c-axis mesh does not build (no PG-free M8 track). Superseded by the COORD c39 ruling.
FT: wi_bands2.py hub_Wi seam-window widening coupon FAIL 58486. The tile-level FT capacity is the blocker (lane file).
All numbers UNCHECKED (own runs) unless marked.
