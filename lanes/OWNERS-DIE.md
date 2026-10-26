# Die ownership (METHODOLOGY 12.9a, owner 2026-10-26 ~08:1x). One owner per die plan and per die clock. Edit only via COORD.
| die | PLAN owner | CLOCK owner | core latency (12.8) | notes |
|---|---|---|---|---|
| qwen_compute (CRITICAL PATH) | INFRA-FIRST (QC plan event) + MASTER-PLAN slice | INFRA-FIRST | QC-SU-LAT (+ other QC cores via INFRA-FIRST) | QC-SU-LAT, MASTER-PLAN never edit the QC clock |
| s81_head | HEAD-CORE-LAT-R2 plan event (via PATH-S81 for the delta) | HEAD-CORE-LAT-R2 | HEAD-CORE-LAT-R2 | H-tree commensurate with core array (COORD ruling) |
| s81 | PATH-S81 | PATH-S81 (on CLOCK-128 tool) | S81-CORE-LAT | |
| qwen_kvsys | PATH-KV | PATH-KV (re-measure c3t under 12.8) | PATH-KV core-latency sub-lanes | |
| hbm | PATH-HBM (D-HBM-B1) | CLOCK-128 (tool + HBM r8 run) | HBM-CORE-LAT | "HBM clock r8 skew" lane PARKS -> CLOCK-128 |
Shared tools: die_clock_mesh.py = CLOCK-128 · die_infra.py master-plan mode = MASTER-PLAN · die_infra.py pg/clock/reset = INFRA-FIRST · flow tags = ROOT-MERGE/FLOW.
Number check: NUMBER-CHECK recomputes every owner-reported gate number (12.9f).
