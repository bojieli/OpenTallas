# OWN-KV-1123 handoff (11-23 02:2x PST)
- hub_Wi: HELD in kit_wave.json (owner KV-WAITBIND-R1, last post 11-22 19:21), D28 prelint advisory only, never placed. Cause = D29 spine reset pin rs_host_die_rst_n__113 missing (PORT_BIND). No DIE-FIX-LEDGER row -> asked KV-PLAN-R6 to add one. VIS-COVERAGE DRAFT (by sibling hub_Wo): no relaunch.
- hub_C: NOT dead: KV-D28 attempt_4 running place since 00:58 (epyc2); RINGMAC rows + AHUB applied in D28. No failure yet; no ledger rows needed until result. VIS DRAFT -> asked VIS-KV to render on landing.
- pc_v1 cl4ea58a5c/cl23f6a148 (FAM-KV-IOPC-R4): ledger rc122 PCV1BANK 0d4e9cf6034e ROW-DRAFT (covers all 3 clones), rc118-121 OPEN. sys_c (FAM-KV-HUBC-SYSC-R2): rc116 row C 08be3955c5c7 ROW-DRAFT, rc117 taps OPEN (TAP-GRID dropped to D30), census HOLD-SKEW/IO-BOUNDARY OPEN. Owners pinged 02:2x (resumed; agents were idle).
- Pending: replies via post.sh; check at 12:00 that rows exist.
