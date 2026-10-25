# TYPE-REDUCE lane (owner-approved 10-25 ~06:45): cut distinct hardened designs (types + hard cores) on all release dies
Branch claude/type-reduce-1025 (wt rtx-pro /home/ubuntu/wt/type-reduce-1025). Read-only analysis + proposal; builds on lanes/TYPE-DEDUP.md (tools/die_plan/dedup.py).
2026-10-25 06:35 PDT TYPE-REDUCE: started. Census of origin/main@6a6fc12dd plans (lane plan branches s81-plan2-1025r / qc-plan3-1025 / hbm-b2o-1025r have the same counts): S81 177 types -> 166 exact netlist -> 48 ignoring ft slots -> 34 RTL groups; head 16->16->10->8; QC 56->56->54->51; KV 49->45->35->25; HBM 49 types all distinct, 210 core modules / 436 inst / 280 pin tables. 3 sub-agents (S81, QC+KV, HBM cores) running.
2026-10-25 06:46 PDT TYPE-REDUCE: DONE claude/type-reduce-1025@befcf3f66 results/type_reduce_1025/REPORT.md + proposals.csv (per die). Types 347 -> 231/207; real core designs 337 -> 160/143. PROPOSAL posted to COORD-REVIEW-QUEUE.
## PARKED 2026-10-25 06:46 PDT
branch claude/type-reduce-1025@befcf3f66 (wt rtx-pro /home/ubuntu/wt/type-reduce-1025, sparse). No live jobs. Sub-agent scratch: rtx-pro ~/scratch/type-reduce, /tmp/trx (copies in results/type_reduce_1025/scripts).
NEXT (plan lanes): fold the accepted items into the per-die batched deltas; HBM-KITS stop per-piece kits; INFRA ownership.py master+template keying.
OWNER? (1) strap -> boot-config/chain-derived ID register (real lane) = allowed? (2) KV R8 pads -> published per-row latency? (3) S81 misc lanes moved to station columns, +2..4 cycles?
