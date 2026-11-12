# HBM plan d53b_d6e_scorer_1111 (HBM-COMPOSE-2, 2026-11-11) DO_NOT_COUNT, PENDING COORD APPROVAL

Applies on top of d53a (746e88cc6a35). Plan die_plan.json.gz sha256 ad080c302a2bd80dc7a12e1258f4dedc129c3fcbd7715ec7b83a0f6a22375e50. No COORD ruling on d6e or the scorer was in the queue when composed; ROOT-MERGE / COORD may drop this directory.
(f1) CPL-HBM-B1 d6e (3d05a7b89aa8, delta sha b351dafd): L15_o fix q_b001 + pv1, no pin cycle. G0 549 -> 548: 3 re-keyed NW_b001 cut rows (cuts 9750/10000/10250 already failed with other track counts), 0 genuinely new. Bind OK, pad_flops 945214.
(f2) DIE-LAYOUT-HBM scorer d6e (1a10ae9674, delta sha 79925e02): 4 whole-list internal_stations sets on q_b001, q_b001__physical_v1, q_b000, q_b000__physical_v1. Overlap with d6e (882 paths) is expected: the scorer replaces lists d6e edits; applied after d6e. G0 548 -> 548, 0 new, 0 lost. Bind OK (92 partitions, 420 crossings, n_errors 0, stale 0, uncovered 0, pad_flops 945214).
The tree's plan equals the t31 plan, whose bind receipt is here (bind_t31).
