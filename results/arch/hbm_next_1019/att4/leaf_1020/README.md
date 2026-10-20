# HNEXT.ATT4 cluster-leaf successor: bench evidence (claude/hnx-att4-leaf-1020, 2026-10-20)

Design and checklist: physical/hbm_next/att4/leaf_1020/README.md.

## m3: census-safe core (current RTL)
Run with `tools/hbm_next/att4_scl_matrix.sh` and `MUTS=... SEED=...`. Setup: Verilator 5.050 on ot-epyc7, HNX_ATT_SAFE_RESET=1, NL 3. The native fan-32 adders are unpacked by tools/prepare_fp32_fan32_models.py (FAN32_MODELS_PASS sha 3606964b).

| run | expected | result |
|---|---|---|
| m0, seed 1019, 24 rounds | PASS | 576/576 nodes bit-exact vs golden csum8; `LOCKSTEP lag=3 mismatches=0` vs the flat ot_hnx_att4_spvm |
| m0, seed 2027, 32 rounds | PASS | 768/768 nodes; LOCKSTEP lag 3, 0 mismatches |
| m1: B event bypass dropped | FAIL | 332 node mismatches |
| m2: result into lane^1 ring | FAIL | 576 |
| m3: ripple reads one level high | FAIL | 470 |
| m4: flush B = +0 | FAIL | 108 |
| m5: publication reads lane^1 | FAIL | 576 |
| m6: storage reads one residue early | FAIL | 573 |
| m7: S->N lane-2 seam 1 edge late | FAIL | 192 (lane 2) |
| m8: S leaf seam events 1 edge late | FAIL | sticky fault |
| m9: S leaf picks the wrong publication half | FAIL | 576 |

The fail witnesses are in witness/scl_m{1..9}.log.

## m1_flatcore: first RTL (the flat core's fanout, before the census rewrite)
- m0 PASSED, and 2/6/7/9 FAILED as expected.
- m8r held the S reset run one stage longer. It PASSED 576 nodes and lockstep, so a reset release skew between the leaves is an equivalent mutant: at idle the merge is time-invariant and the late leaf relabels its residues consistently. It was replaced by the seam-event mutant m8.
- Kept as evidence.
