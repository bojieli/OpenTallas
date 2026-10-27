# MODEL-REFIT 2026-10-26: core clock insertion model, all dies

Data: points.json (47 trials: HBM 22, QC 10, S81 6, KV 9). src column: CBR = CHECKED-BY-REFIT (recomputed from raw run artifacts), NC = NUMBER-CHECK, LANE = lane receipt (UNCHECKED). Excluded from fits: HBM side_rest centre (invalid outline), QC btab R3 (broken assignment, raw log gone). L = entry -> farthest outline corner (Manhattan, plan geometry). basis PL = placement RC, GRT = global-route RC.

| set | target / form | n | max |res| | rms | LOO max | LOO rms | coef |
|---|---|---|---|---|---|---|---|
| ALL (edge+centre, all structures) | tt_mean | CURRENT main (0.943*0.896*L, no offset) | 45 | 207.5 | 92.1 | - | - | bias -23.9 |
| ALL (edge+centre, all structures) | tt_mean | K*L+c | 45 | 191.9 | 89.0 | 196.3 | 91.0 | [-23.8991] |
| ALL (edge+centre, all structures) | tt_mean | a+bL | 45 | 192.4 | 58.1 | 321.5 | 70.9 | [93.6391, 0.5797] |
| ALL (edge+centre, all structures) | tt_mean | a+bL+PL | 45 | 198.4 | 55.9 | 306.5 | 69.1 | [106.6444, 0.6055, -36.6482] |
| ALL (edge+centre, all structures) | tt_mean | a+bL+PL+struct | 45 | 199.4 | 51.0 | 313.2 | 66.1 | [116.3637, 0.6074, -48.2263, 25.5589, 16.55, -64.6599] |
| ALL (edge+centre, all structures) | tt_mean | a+bL+PL+log2N | 45 | 220.7 | 54.5 | 305.7 | 70.9 | [-31.4004, 0.6187, -48.5465, 10.7387] |
| ALL (edge+centre, all structures) | tt_max | a+bL | 36 | 304.5 | 86.3 | 420.8 | 105.7 | [67.5122, 0.7668] |
| CENTRE entry, CTS-grown (cts+rt) | tt_mean | a+bL | 13 | 58.6 | 25.2 | 95.1 | 34.7 | [122.1565, 0.5659] |
| CENTRE entry, CTS-grown (cts+rt) | tt_mean | a+bL+PL | 13 | 31.8 | 15.6 | 66.9 | 25.7 | [176.6278, 0.4233, -40.6029] |
| CENTRE entry, CTS-grown (cts+rt) | tt_max | a+bL+PL | 12 | 15.2 | 9.4 | 34.8 | 15.4 | [232.0599, 0.3107, -56.4169] |
| CENTRE entry, CTS-grown, GRT only | tt_mean | CURRENT main (0.943*0.896*L, no offset) | 6 | 84.4 | 77.8 | - | - | bias 77.6 |
| CENTRE entry, CTS-grown, GRT only | tt_mean | K*L+c | 6 | 9.2 | 5.0 | 11.1 | 5.9 | [77.6149] |
| CENTRE entry, CTS-grown, GRT only | tt_mean | a+bL | 6 | 9.0 | 4.8 | 10.9 | 6.6 | [86.9273, 0.8054] |
| CENTRE entry, CTS-grown, GRT only | tt_max | a+bL | 5 | 12.4 | 6.2 | 69.6 | 32.1 | [181.9019, 0.5195] |
| CENTRE entry, CTS-grown, GRT only | tt_max | K*L+c | 5 | 21.9 | 11.6 | 27.4 | 14.5 | [103.7048] |
| CENTRE entry, CTS-grown, GRT only | ff_mean | a+bL | 6 | 10.0 | 5.1 | 12.2 | 6.6 | [54.8009, 0.722] |
| EDGE entry (cts+trunk) | tt_mean | a+bL | 27 | 197.5 | 67.5 | 341.0 | 91.0 | [65.4377, 0.6185] |
| EDGE entry (cts+trunk) | tt_mean | a+bL+PL | 27 | 213.3 | 61.9 | 319.0 | 85.2 | [116.7724, 0.6458, -78.6002] |
| PLAN-built trees (QC SU R4b/R5/R6) | tt_mean | K*L+c | 5 | 36.1 | 24.2 | 45.2 | 30.2 | [-20.1221] |
| PLAN-built trees (QC SU R4b/R5/R6) | tt_mean | a+bL | 5 | 34.2 | 23.9 | 179.5 | 86.5 | [-81.1312, 1.047] |

## Chosen form (implemented in tools/die_plan/master_plan.py core_insertion)
TT_GRT = 86.86 + 0.8057 x L_max; FF = 0.8118 x TT. Calibrated on the 6 centre-entry CTS-grown GRT trials (HBM gq_issue, pc_ctrl_leaf; S81 gunit_l0 x2, l2, l4). Residual max 9.0 / rms 4.8; LOO max 10.9 / rms 6.6 (TT); FF LOO max 11.3 / rms 7.4. Calibrated L range 181-259 um.
Expected error band for the 250+-20 gate: +-11 ps TT (LOO max) inside 181-259 um; L for 230/250/270 TT = 178/202/227 um. Outside the range it over-predicts long cores (HBM edge points 400-850 um sit 60-260 ps below the line), which only adds restructure flags (conservative).

## Not covered by the line
- Placement-RC trials: PL->GRT delta is not constant (S81 l4 +26, l0 +45, KV ~+10-13); PL points cannot calibrate GRT. KV pv_pair (380x190 centre, PL 224.9) sits 92 below the line: long-thin cores with SRAM-CK branches need their own measurement.
- Edge entries: no single L form (rms 62-89); banned by 12.8a anyway.
- Plan-built trees (core_infra_htree / su_tree_model, TritonCTS not run): L does not predict them (btab R4b 211.5 / R5 279.8 / R6 260.8 at the same L 312). Use the tree model + its OWN offset (master_plan.PLAN_TREE_OFFSETS): core_infra_htree NLDM TT -12.8 (R5 -12.5, R6 -13.1), FF -24.5 (R6 only); su_tree_model NLDM TT +1.9 / FF -5.1 (R5 only).
- MASTER-PLAN-R5 su_unequal predictions add TT +13 / FF +24.5 to su_tree_uf raw NLDM. Wrong sign and wrong model: the -13/-24.5 offsets are meas - core_infra_htree; su_tree_model own offset on R5 is +1.9 / -5.1. Corrected (raw + su_tree offset): vmr 231.2 / FF 175.5 (FF BELOW 182.5), rp1 213.4 / 161.5, prog current 254.1 / 194.0, prog F3 249.0 / 191.0. One calibration point, UNCHECKED raw values from the MASTER-PLAN-R5 lane.
- btab R6 pad question: the OT_MSCTS_BAL grt iter 0 line plans 18-ps pads, but the final per-tap GRT means equal the pre-BAL means (T001 253.4, T031 270.0, window 16.6). So no pad affected the measured number. Fit with and without R6: R6 is not in the chosen calibration set (plan-built), so the line does not change; the core_infra_htree offset without R6 = -12.5 (R5 only).
