# PRECHECK-LEDGER-R3 handoff (Sonnet 5.5, started 11-23 05:52 PST; replaces PRECHECK-R2 + FIX-LEDGER)
- ADV-STN-CONFLICT: on main 9f46e2ad94 (adv_stn_conflict.py + test). Run via ot-run on epyc hosts: plan_advisory.py --plan P --asbuilt <plan_of_record/native_bind/asbuilt_run.json> --checks STN-CONFLICT --all. Posted 06:1x to 4 die lanes. TODO: rerun on composed J9 / D29 / V4 / r18 plans at their gates (HEAD 11:00, KV 11:30, S81 10:30, QC 13:00).
- Ledger: lanes/DIE-FIX-LEDGER.tsv owner_lane remapped 06:12 (hub 994f14a91cc4), map in scratchpad remap.py. Kept FAM-QC-HCST-R3, CLASS-FIX-RHI. Agent-id column set to '-' on changed rows.
- Every 2 h: counts per die (status col) + OPEN past deadline to COORD. Next ~08:15. Sweep lanes/posts for status changes first (status was last swept 05:00 by FIX-LEDGER).
- Deadlines PST: HEAD gate 11:00; S81 rows 10:00, assembly 10:30, 2nd compose <17:00, cut 18:00; KV tools 11:30 pkg 12:30 gate 13:00; QC gate 13:00.
- 19:5x ledger sync from ALLFIX-*.tsv every round (sync.py in scratchpad): IN-COMPOSE/IN-BASE evidence; S81 LAND-CAP rerun on c7a post-tail + c8 when posted (OPEN-LEAFBAND owns the fix).
