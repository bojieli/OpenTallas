# HNEXT.ATT4 cluster-leaf successor: bench evidence (claude/hnx-att4-leaf-1020, 2026-10-20)
Design and checklist: physical/hbm_next/att4/leaf_1020/README.md.
Matrix m2 (`tools/hbm_next/att4_scl_matrix.sh`; Verilator 5.050 on ot-epyc7; HNX_ATT_SAFE_RESET=1; NL 3; 24 rounds; seed 1019; 576 nodes):

| run | expected | result |
|---|---|---|
| m0 | PASS | 576/576 nodes bit-exact vs the golden; `LOCKSTEP lag=3 mismatches=0` vs the flat ot_hnx_att4_spvm |
| m2 (core: result into lane^1 ring) | FAIL | 576 node mismatches |
| m6 (core: storage reads one residue early) | FAIL | 573 node mismatches |
| m7 (seam: S->N lane-2 words land 1 edge late) | FAIL | 192 node mismatches (lane 2 only), plus LOCKSTEP_MISMATCH |
| m8 (seam: S leaf event bits land 1 edge late) | FAIL | sticky fault (replica collision) |
| m9 (S leaf picks the wrong publication half) | FAIL | 576 node mismatches |

The fail witnesses are in witness/scl_m{2,6,7,8,9}.log.

m8r (matrix m1, before the fix) held the S leaf's reset run one stage longer. It PASSED 576 nodes and lockstep. A reset
release skew between the leaves is therefore an equivalent mutant: at idle the merge is time-invariant, so the late
leaf relabels its residues consistently. It was replaced by the seam-event mutant m8. Its log is kept as evidence.
