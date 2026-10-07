# DS closure-cost ledger (S81 die + tiles)

Pre-closure DS AR 1,675.0 tok/s, MTP 4,895.0 tok/s.

| item | cost | AR tok/s | AR % | MTP % | cum AR % | cum MTP % |
|---|---|---:|---:|---:|---:|---:|
| s81_die | S81 v6b die: field round trip 165 vs 137 at the same frame, less the meso d8g1 term (+24): hub stations, q banks, column relays, 215 um common-clock hops, budget-sheet hop stations, column FIFO v2 (+2) | 1,661.2 | -0.82 | -0.66 | -0.82 | -0.66 |
| meso_d8g1 | meso FIFOs d8g1 (DEPTH 8 / OFFSET 4 / GUARD_LO 1): +1 per crossing over d8, +2 over d4: 2 crossings a field round trip (+4) | 1,658.9 | -0.14 | -0.11 | -0.96 | -0.77 |
| ctrl_status | CTRL status chain: +1 cycle per column (HBM stream reads) | 1,658.8 | -0.01 | -0.00 | -0.97 | -0.78 |
| collective_lane | Collective slab v3 tiles: all-reduce 320 records +288 cycles over the C8 reference (measured, S81-PH src_v3, no bit errors, lane channel 1 cycle; coll_price 2026-10-07).  Replaces x0.9003 = 2,329 / 2,587 (absolute TB times incl. the 1,111-cycle preamble, bit-error injection on, against a node priced from tb_w15b_v41_tp4).  All-gathers: PENDING-DEFECT (below) | 1,607.6 | -3.09 | -2.46 | -4.02 | -3.22 |
| vm_bank_group | VM bank-group chain: read latency 10 -> 18 (+8 a field phase) | 1,603.4 | -0.26 | -0.21 | -4.28 | -3.43 |
| gather_root_v4 | Gather root v4: +6 cycles per phase | 1,600.2 | -0.20 | -0.16 | -4.47 | -3.58 |
| capture | Capture tiles: VM write +3 a phase | 1,598.6 | -0.10 | -0.08 | -4.56 | -3.66 |
| selector | Selector tiles: +20 a segment (mean; +15 max) | 1,598.3 | -0.02 | -0.03 | -4.58 | -3.68 |
| collector | Collector tiles: +2 a job | 1,598.2 | -0.01 | -0.00 | -4.58 | -3.69 |
| svc_io | Scan service IO hub / per-PC tiles: one register each way (+2 a request) | 1,598.0 | -0.01 | -0.01 | -4.60 | -3.70 |
| softmax_safe_div | Softmax SAFE divider: +29 on normalize | 1,595.6 | -0.15 | -0.12 | -4.74 | -3.81 |
| bf_rowfix | BF rowfix: +1 per push (a field phase) | 1,595.0 | -0.04 | -0.03 | -4.78 | -3.84 |
| pq_qelem | PQ q-element: decode stage +0.17 % node time (field phases) | 1,593.7 | -0.08 | -0.07 | -4.85 | -3.91 |
| **TOTAL** | | **1,593.7** (MTP 4,703.8) | | | **-4.85** | **-3.91** |
| collective_ag (PENDING-DEFECT, not in the headline) | S81 collective tile defects (credits 256 < RTT, ~900-cycle small-AG latency, AG256/1024 exactness errors) under repair; measured as-is all-gathers over the C8 reference: 24 rec +914, 57 +922, 256 +273 (FAIL), 1024 +509 (FAIL), 1056 +516 | | | | | |

Measured as-is (PENDING-DEFECT included): AR 1,441.1 (-13.96 %), MTP 4,325.0 (-11.64 %).  The headline uses the table total.
