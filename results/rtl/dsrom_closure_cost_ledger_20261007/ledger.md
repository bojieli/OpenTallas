# DS closure-cost ledger (S81 die + tiles)

Pre-closure DS AR 1,675.0 tok/s, MTP 4,895.0 tok/s.

| item | cost | AR tok/s | AR % | MTP % | cum AR % | cum MTP % |
|---|---|---:|---:|---:|---:|---:|
| s81_die | S81 v6b die: field round trip 165 vs 137 at the same frame, less the meso d8g1 term (+24): hub stations, q banks, column relays, 215 um common-clock hops, budget-sheet hop stations, column FIFO v2 (+2) | 1,661.2 | -0.82 | -0.66 | -0.82 | -0.66 |
| meso_d8g1 | meso FIFOs d8g1 (DEPTH 8 / OFFSET 4 / GUARD_LO 1): +1 per crossing over d8, +2 over d4: 2 crossings a field round trip (+4) | 1,658.9 | -0.14 | -0.11 | -0.96 | -0.77 |
| ctrl_status | CTRL status chain: +1 cycle per column (HBM stream reads) | 1,658.8 | -0.01 | -0.00 | -0.97 | -0.78 |
| collective_lane | Collective lane tiles: +2 TX cycles; 448-record all-reduce 2,329 vs v1 2,587 cycles (x0.9003 on the all-reduces; +2 on the gathers) | 1,671.1 | +0.74 | +0.58 | -0.23 | -0.20 |
| vm_bank_group | VM bank-group chain: read latency 10 -> 18 (+8 a field phase) | 1,666.5 | -0.28 | -0.22 | -0.51 | -0.42 |
| gather_root_v4 | Gather root v4: +6 cycles per phase | 1,663.1 | -0.20 | -0.17 | -0.71 | -0.58 |
| capture | Capture tiles: VM write +3 a phase | 1,661.4 | -0.10 | -0.08 | -0.81 | -0.66 |
| selector | Selector tiles: +20 a segment (mean; +15 max) | 1,661.0 | -0.02 | -0.03 | -0.84 | -0.69 |
| collector | Collector tiles: +2 a job | 1,661.0 | +0.00 | -0.00 | -0.84 | -0.69 |
| svc_io | Scan service IO hub / per-PC tiles: one register each way (+2 a request) | 1,660.8 | -0.01 | -0.01 | -0.85 | -0.70 |
| softmax_safe_div | Softmax SAFE divider: +29 on normalize | 1,658.1 | -0.16 | -0.13 | -1.01 | -0.83 |
| code_pair | Code pair: LAT_DELTA 11 a field phase | 1,651.9 | -0.37 | -0.30 | -1.38 | -1.13 |
| bf_rowfix | BF rowfix: +1 per push (a field phase) | 1,651.3 | -0.04 | -0.03 | -1.42 | -1.16 |
| pq_qelem | PQ q-element: decode stage +0.17 % node time (field phases) | 1,649.9 | -0.09 | -0.07 | -1.50 | -1.23 |
| **TOTAL** | | **1,649.9** (MTP 4,834.9) | | | **-1.50** | **-1.23** |
