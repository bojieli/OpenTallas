# item2 r3: service -> PQ full bit-RTL (PASS)
L20 actual GU service (hubble-wg-service-r2) into NC8 arithmetic with ENABLE/PQ_ENABLE/XMAP/PACK_W2/WG = 1,
experts 41,65,158,164,259,266, 6 slots under Verilator (build 7 h 53 m, PVE1).
- 6/6 slots exact (INTEGRATED_PQ_XMAP_PASS results=12; cycles 696-944 per slot), 9,408 returns.
- Negative control: corrupted GU sector -> assertion "GU sector mismatch" (rejected).
- All 43 source digests bind origin/main at harvest (2026-10-06).
Scope: W2 byte transport only; not an all-lever layer/token bench or physical qualification.
Job: PVE1 /srv/opentallas-scratch/codex/item2-hbm-integrated-20261006/r3 (tools/hbm_integrated_expert_pq.py --step build-run).
