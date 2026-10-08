# DS closure-cost ledger (S81 die + tiles)

Pre-closure DS AR 1,675.0 tok/s, MTP 4,895.0 tok/s.

| item | cost | AR tok/s | AR % | MTP % | cum AR % | cum MTP % |
|---|---|---:|---:|---:|---:|---:|
| s81_die | S81 v6b die: field round trip 165 vs 137 at the same frame, less the meso d8g1 term (+24): hub stations, q banks, column relays, 215 um common-clock hops, budget-sheet hop stations, column FIFO v2 (+2) | 1,661.2 | -0.82 | -0.66 | -0.82 | -0.66 |
| meso_d8g1 | meso FIFOs d8g1 (DEPTH 8 / OFFSET 4 / GUARD_LO 1): +1 per crossing over d8, +2 over d4: 2 crossings a field round trip (+4) | 1,658.9 | -0.14 | -0.11 | -0.96 | -0.77 |
| ctrl_status | CTRL status chain: +1 cycle per column (HBM stream reads) | 1,658.8 | -0.01 | -0.00 | -0.97 | -0.78 |
| collective_lane | Collective slab v4 tiles (S81-PH f4b4e0a71: EDEPTH 512, link-up gate; bench_v4 coll_price, trained links, no bit errors, lane channel 1 cycle) over the C8 reference: all-reduce 320 rec +131 (CHB 251: 709 vs w15b 690); all-gather 24 rec +38, 57 +50, 256 +113, 1024 +348, 1056 +361 | 1,619.0 | -2.40 | -2.09 | -3.34 | -2.85 |
| link_split | SerDes tx / rx through two 256-b half-span stations (--link-split; 1,122 um pin span, last hop <= 281 um): +1 cycle per direction per traversal: stage hops +2, token return 8 traversals +16, TP4 all-reduce 2 traversals +4, all-gather +2 | 1,617.6 | -0.09 | -0.07 | -3.43 | -2.92 |
| sel_xstg | Selector / collector crossing stages (--sel-xstg: d8g1 meso FIFO with registered pins on the end block -> band block buses, 382-385 ps crossings): +6 cycles per selector segment / collector job | 1,617.4 | -0.01 | -0.01 | -3.44 | -2.93 |
| vm_bank_group | VM bank-group chain: read latency 10 -> 18 (+8 a field phase) | 1,613.1 | -0.27 | -0.21 | -3.70 | -3.14 |
| gather_root_v4 | Gather root v4: +6 cycles per phase | 1,609.9 | -0.20 | -0.16 | -3.89 | -3.30 |
| capture | Capture tiles: VM write +3 a phase | 1,608.3 | -0.10 | -0.08 | -3.98 | -3.38 |
| selector | Selector tiles: +20 a segment (mean; +15 max) | 1,607.9 | -0.03 | -0.03 | -4.01 | -3.40 |
| collector | Collector tiles: +2 a job | 1,607.9 | +0.00 | -0.00 | -4.01 | -3.40 |
| svc_io | Scan service IO hub / per-PC tiles: one register each way (+2 a request) | 1,607.7 | -0.01 | -0.01 | -4.02 | -3.41 |
| softmax_safe_div | Softmax SAFE divider: +29 on normalize | 1,605.2 | -0.16 | -0.12 | -4.17 | -3.53 |
| bf_rowfix | BF rowfix: +1 per push (a field phase) | 1,604.6 | -0.04 | -0.03 | -4.20 | -3.56 |
| pq_qelem | PQ q-element: decode stage +0.17 % node time (field phases) | 1,603.3 | -0.08 | -0.07 | -4.28 | -3.62 |
| bf_merge_ksplit | BF16 phase merges + router K split on the mixed-slot S81 die (release results/uarch/dsrom_s81_released_binding_20261007: 2,304 pairs = 18 a region, 512 BF = 4 a region on the flat is_bf map, BF slots f198.72 + q slots f183.60, 77 allocator stages): wo_a 4 -> 2 phases, a_proj BF16 merged, router 3 golden-aligned K segments; MEASURED full field (qelem10 vehicle, 18,288 regions exact) vs the as-built field, every node (q phases included); wire ESTIMATED at f183.60 | 1,754.3 | +9.42 | +8.07 | +4.73 | +4.15 |
| **TOTAL** | | **1,754.3** (MTP 5,098.3) | | | **+4.73** | **+4.15** |
| fh_half (CANDIDATE, not adopted) | DSpark fused head SAFE half-rate backstop (whole draft-core domain on the die clock / 2; gold4 OT_FH_HALF EXACT 126,310 die cycles vs 63,153, claude/takeover-ds-head-20261006 7d63728a0): draft head occupancy x2 (+8,387 cyc = 6.9892 us a draft position); adopt only for a view whose full-rate route misses | 1,754.3 | +0.00 | -4.14 | | |
| head_elem (CANDIDATE, not adopted) | lm_head element A/B (ot_dsrom_head_elem IOREG + SAFE argmax + CUT 511 + fadd SPLIT9): bundle EXACT 8,357 -> 8,414 (+57 a sweep); on head.lm_head and on every draft head sweep (elemB CLOSED 9adbc6104; elemA routing) | 1,754.1 | -0.01 | -0.04 | | |
| fused_head (CANDIDATE, not adopted) | DSpark fused head r4 structure (8 hquad LRET + ctl SAFE2 + endpoint FPIPE3, QPIN): gold4 EXACT 63,028 -> 63,153 (+125 per gamma-5 draft = +25 a draft position; ctl/ep/hquad views routing) | 1,754.3 | +0.00 | -0.01 | | |
| bf_half (CANDIDATE, not adopted) | BF SAFE B: element at half rate (ot_s81_bf_native HALF=1, claude/dsrom-bf-rowfix-20261007 61c1cf230, exact PASS; closure-loop bf_half_61c1cf230): BF16 field phases doubled (upper bound; fracs = BF16 phase share (go->idle+1)/node, field_qelem_qx10.json, a_proj max over layer types); adopt only if B closes first (variant A re-cut is the target).  UNDER-PRICED: BF pairs also hold 20.6 % of the q words, so HALF=1 on shared pairs doubles those q phases too (the BF-dedicated-pair plan of the BF doubling agent replaces it) | 1,560.7 | -11.04 | -9.03 | | |
| bf_halfphl (CANDIDATE, not adopted) | BF HALF_PHL (ot_s81_bf_native HALF=1 HALF_PHL=1, claude/s81-bf-20261007 4000b1ea7; exact PASS results/rtl/s81_bf_native_20261007/halfphl_exact; closure-loop bf_halfphl_0e90389e9_f / _p700_4000b1ea7_f): the half-rate element with the phase FF on the ICG clock net (0 cycles vs HALF).  Priced on the adopted bf_merge_ksplit field: every BF16 field-vehicle phase doubled (merged meas from merge_price.json / router_ksplit_price.json; a_proj less its as-built FP8 phase, 410) + 2 per BF16 phase (pin capture, output register).  UPPER BOUND (region return / gather stay full rate).  Requires BF16-DEDICATED BF pairs (q never on a BF pair: tools/dsrom_bf_double_alloc.py without --shared) -- the die/stage count of that allocation is reported in results/rtl/s81_bf_native_20261007/halfphl_price.json | 1,619.6 | -7.68 | -6.31 | | |
| bf_recut (CANDIDATE, not adopted) | BF re-cut A (ot_s81_bf_native RECUT=2, claude/dsrom-bf-rowfix-20261007 260869fd0; exact record e2d358837; closure-loop bf_recut_260869fd0): latency only, transaction lag per partial 4 / 7.9 / 15; upper bound +15 per field phase (wo_a 4 phases, a_proj 3) | 1,737.0 | -0.99 | -0.78 | | |
| bf_unroll (CANDIDATE, not adopted) | BF unroll-by-2 (ot_s81_bf_native RECUT=3, claude/dsrom-bf-rowfix-20261007 9cf64047e; exact record c394c0ace; closure-loop bf_unroll_9cf64047e): re-cut A + lane chains unrolled by 2 on a half-rate gated clock, latency only, lag per partial 4 / 8.8 / 18; upper bound +18 per field phase | 1,733.4 | -1.19 | -0.95 | | |

Measured as-is (PENDING-DEFECT included): AR 1,754.3 (+4.73 %), MTP 5,098.3 (+4.15 %).  The headline uses the table total.
