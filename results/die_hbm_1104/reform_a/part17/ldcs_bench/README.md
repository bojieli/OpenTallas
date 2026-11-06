# lane1p RE-FORM proof (HBM-GAPS-5-L1P, 2026-11-05 21:19 PST)

Lock-step bench: ref = main ot_hbm_su_pg_lane1p_core (origin/main 7305773106: MLAT 4, ALAT 3, no LDCS; the three
changed modules renamed __ref) vs dut = branch core with #(MLAT, ALAT, LDCS). Same random stimulus every edge
(reform_1103 lockstep_gen.py), lane0_lane_id held at 11'h07F (all 7 offset terms) or 11'h2B5, 20000 cycles.
The dut wrapper delays each per-stage control input by its stage shift (the control pipe delivers it that much later).
Outputs vm_*, kv_*, ro_* are compared with the declared shift; rd_*, bank0_read_data and coll with shift 0.
lane0_fault is the registered OR of the stage fault flags, so it is compared per source (fault_cmp.py), each with its own shift.

| run | MLAT ALAT LDCS | declared shift | result |
|---|---|---|---|
| same | 4 3 0 | none | PASS (the opt-in LDCS 0 path = main) |
| ldcs, ldcs_b | 4 3 1 | none | PASS (carry-save offset load is bit-exact, same edges) |
| ldcs_m1/m2/m3 | 4 3 1 + LDCS_MUT_NOSHIFT / DROPCB / STALE | none | FAIL (caught) |
| vA, vA_b | 5 3 1 | in: cm +1, ca +2, ci/cs/side_y +2, ce +3, co +4; out vm/kv/ro +4 | PASS |
| vA_m3 / m4 / m6 / mc | out shift 3 / cm not delayed / f_e2 shift -1 / LDCS_MUT_DROPCB | | FAIL (caught) |
| vB, vB_b | 5 4 1 | in: cm +1, ca +2, ci/cs/side_y +3, ce +4, co +5; out vm/kv/ro +5 | PASS |
| vB_m3 / m4 / m5 / m6 / mc | out shift 4 / cm not delayed / ALAT not declared / f_e2 -1 / LDCS_MUT_STALE | | FAIL (caught) |

LDCS_MUT_DROPT3 is an equivalent mutant at LN 7 (groups of 3, 3, 1: a group's 4th term is always 0), so it is not used.
Fault sources (edges later than ref): f_m1 +DM, f_m2/f_q +2DM, f_ad +2DM+DA, f_e1a +2DM+2DA, f_e1m +3DM+DA, f_e2 +4DM+DA
(DM = MLAT - 4, DA = ALAT - 3).
Rerun (epyc5 /srv/opentallas-scratch2/claude/hbm-gaps-5-l1p/eq, docker python:3.12, 16 GB cap):
dk.sh NAME MLAT ALAT LDCS DM DA LANE_ID CYC MUT [-DDEFINE]; src/ = kit leaf RTL + branch new/ + main old/ (shas.txt).
Per-run map.json, gen.log, sim.log under runs/; summary.txt = all results.
