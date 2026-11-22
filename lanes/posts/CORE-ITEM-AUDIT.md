- 2026-11-22 00:59 PST 14 OWNERS core rows (S81 4, QC 7, KV 3) are not in current bound plans: OWNERS reads stale main die_plan.json (10-29). 10 renamed/split in J6r1/V2/D27d3 (covered, counted signed), 2 absent (xfin, host_qm). 
  Retired all 14 in OWNERS-RETIRED.tsv (commit 88f7326). No enqueue needed. Root cause: ownership.py reads main die_plan.json, not the kit_wave bound plan.
