# DS closure-cost ledger (S81 die + tiles)

Pre-closure DS AR 1,675.0 tok/s, MTP 4,895.0 tok/s.

| item | cost | AR tok/s | AR % | MTP % | cum AR % | cum MTP % |
|---|---|---:|---:|---:|---:|---:|
| s81_die | S81 v6b die: field round trip 165 vs 137 at the same frame, less the meso d8g1 term (+24): hub stations, q banks, column relays, 215 um common-clock hops, budget-sheet hop stations, column FIFO v2 (+2) | 1,661.2 | -0.82 | -0.66 | -0.82 | -0.66 |
| meso_d8g1 | meso FIFOs d8g1 (DEPTH 8 / OFFSET 4 / GUARD_LO 1): +1 per crossing over d8, +2 over d4: 2 crossings a field round trip (+4) | 1,658.9 | -0.14 | -0.11 | -0.96 | -0.77 |
| ctrl_status | CTRL status chain: +1 cycle per column (HBM stream reads) | 1,658.8 | -0.01 | -0.00 | -0.97 | -0.78 |
| collective_lane | Collective slab v4 tiles (S81-PH f4b4e0a71: EDEPTH 512, link-up gate; bench_v4 coll_price, trained links, no bit errors, lane channel 1 cycle) over the C8 reference: all-reduce 320 rec +131 (CHB 251: 709 vs w15b 690); all-gather 24 rec +38, 57 +50, 256 +113, 1024 +348, 1056 +361 | 1,619.0 | -2.40 | -2.09 | -3.34 | -2.85 |
| link_split | SerDes tx / rx through two 256-b half-span stations (--link-split; 1,122 um pin span, last hop <= 281 um): +1 cycle per direction per traversal: stage hops +2, token return 8 traversals +16, TP4 all-reduce 2 traversals +4, all-gather +2 | 1,617.6 | -0.09 | -0.07 | -3.43 | -2.92 |
| sel_xstg | Selector / collector crossing stages (--sel-xstg: falling-edge capture 1.5 T + guard flop on the end block -> band block buses, 382-385 ps crossings): +1 cycle per selector segment / collector job | 1,617.6 | +0.00 | -0.00 | -3.43 | -2.92 |
| vm_bank_group | VM bank-group chain: read latency 10 -> 18 (+8 a field phase) | 1,613.3 | -0.27 | -0.22 | -3.68 | -3.13 |
| gather_root_v4 | Gather root v4: +6 cycles per phase | 1,610.0 | -0.20 | -0.16 | -3.88 | -3.29 |
| capture | Capture tiles: VM write +3 a phase | 1,608.4 | -0.10 | -0.08 | -3.98 | -3.36 |
| selector | Selector tiles: +20 a segment (mean; +15 max) | 1,608.1 | -0.02 | -0.03 | -3.99 | -3.39 |
| collector | Collector tiles: +2 a job | 1,608.1 | +0.00 | -0.00 | -3.99 | -3.39 |
| svc_io | Scan service IO hub / per-PC tiles: one register each way (+2 a request) | 1,607.8 | -0.02 | -0.01 | -4.01 | -3.40 |
| softmax_safe_div | Softmax SAFE divider: +29 on normalize | 1,605.4 | -0.15 | -0.12 | -4.16 | -3.52 |
| bf_rowfix | BF rowfix: +1 per push (a field phase) | 1,604.8 | -0.04 | -0.03 | -4.19 | -3.54 |
| pq_qelem | PQ q-element: decode stage +0.17 % node time (field phases) | 1,603.5 | -0.08 | -0.07 | -4.27 | -3.61 |
| **TOTAL** | | **1,603.5** (MTP 4,718.3) | | | **-4.27** | **-3.61** |

Measured as-is (PENDING-DEFECT included): AR 1,603.5 (-4.27 %), MTP 4,718.3 (-3.61 %).  The headline uses the table total.
