# DS closure-cost ledger (S81 die + tiles)

Pre-closure DS AR 1,675.0 tok/s, MTP 4,895.0 tok/s.

| item | cost | AR tok/s | AR % | MTP % | cum AR % | cum MTP % |
|---|---|---:|---:|---:|---:|---:|
| s81_die | S81 v9d scan/layer1 floorplan: maximum field round trip 168 vs 137 at the same frame, less the separately priced meso d8g1 term (+4), giving +27: hub stations, q banks, column relays, 215 um common-clock hops, budget-sheet hop stations, column FIFO v2 (+2). Measured global-route feasibility; die DRT/SS/FF qualification and final mixed-BF/PQ geometry remain pending | 1,659.5 | -0.93 | -0.74 | -0.93 | -0.74 |
| meso_d8g1 | meso FIFOs d8g1 (DEPTH 8 / OFFSET 4 / GUARD_LO 1): +1 per crossing over d8, +2 over d4: 2 crossings a field round trip (+4) | 1,657.2 | -0.14 | -0.11 | -1.06 | -0.85 |
| ctrl_status | CTRL status chain: +1 cycle per column (HBM stream reads) | 1,657.1 | -0.01 | -0.00 | -1.07 | -0.86 |
| collective_lane | Collective slab v4 tiles (S81-PH f4b4e0a71: EDEPTH 512, link-up gate; bench_v4 coll_price, trained links, no bit errors, lane channel 1 cycle) over the C8 reference: all-reduce 320 rec +131 (CHB 251: 709 vs w15b 690); all-gather 24 rec +38, 57 +50, 256 +113, 1024 +348, 1056 +361 | 1,617.4 | -2.40 | -2.09 | -3.44 | -2.93 |
| link_split | SerDes tx / rx through two 256-b half-span stations (--link-split; 1,122 um pin span, last hop <= 281 um): +1 cycle per direction per traversal: stage hops +2, token return 8 traversals +16, TP4 all-reduce 2 traversals +4, all-gather +2 | 1,616.0 | -0.09 | -0.07 | -3.52 | -3.00 |
| sel_xstg | Selector / collector crossing stages (--sel-xstg: d8g1 meso FIFO with registered pins on the end block -> band block buses, 382-385 ps crossings): +6 cycles per selector segment / collector job | 1,615.8 | -0.01 | -0.01 | -3.53 | -3.01 |
| vm_bank_group | VM bank-group chain: read latency 10 -> 18 (+8 a field phase) | 1,611.5 | -0.27 | -0.22 | -3.79 | -3.22 |
| gather_root_v4 | Gather root v4: +6 cycles per phase | 1,608.3 | -0.20 | -0.16 | -3.98 | -3.38 |
| capture | Capture tiles: VM write +3 a phase | 1,606.7 | -0.10 | -0.08 | -4.08 | -3.45 |
| selector | Selector tiles: +20 a segment (mean; +15 max) | 1,606.3 | -0.03 | -0.03 | -4.10 | -3.48 |
| collector | Collector tiles: +2 a job | 1,606.3 | +0.00 | -0.00 | -4.10 | -3.48 |
| svc_io | Scan service IO hub / per-PC tiles: one register each way (+2 a request) | 1,606.1 | -0.01 | -0.01 | -4.11 | -3.49 |
| softmax_safe_div | Softmax SAFE2 measured against MARGIN baseline (dsrom_softmax_recovery_20261007): normalize 141 -> 171 (+30), exp 224 -> 225 (+1). Cost only; die pin FF hold remains unqualified | 1,603.4 | -0.17 | -0.13 | -4.28 | -3.62 |
| bf_rowfix | BF rowfix: +1 per push (a field phase) | 1,602.9 | -0.03 | -0.03 | -4.30 | -3.64 |
| pq_qelem | PQ q-element: decode stage +0.17 % node time (field phases) | 1,601.6 | -0.08 | -0.07 | -4.38 | -3.71 |
| softmax_exp_recut | Softmax exp tile closed only with RECUT (dsrom_softmax_safe_exprcf_bd30aca4a CLOSED SS +123.11 / FF +16.70, f12r multiplier/adder +2 cuts, LAT 11): attn.exp 225 -> 255 (+30 over SAFE2; dsrom_softmax_recovery_20261007 RECUT1_or_2_vs_m5 +31) | 1,599.0 | -0.16 | -0.13 | -4.54 | -3.83 |
| su_meso_d8g1 | SU crossings through the d8g1 meso FIFO (fullsys_recheck_20261007/ds_su_xing, 64/64 phases exact): +2.5 ns (+3 fast cycles) each way vs the d4 crossing in su_cdc, on every slow<->fast edge consumer | 1,594.2 | -0.30 | -0.24 | -4.82 | -4.07 |
| **TOTAL** | | **1,594.2** (MTP 4,696.0) | | | **-4.82** | **-4.07** |
| head_elem (CANDIDATE, not adopted) | lm_head element A/B (ot_dsrom_head_elem IOREG + SAFE argmax + CUT 511 + fadd SPLIT9): bundle EXACT 8,357 -> 8,414 (+57 a sweep); on head.lm_head and on every draft head sweep (elemB CLOSED 9adbc6104; elemA routing) | 1,594.1 | -0.01 | -0.03 | | |
| fused_head (CANDIDATE, not adopted) | DSpark fused head r4 structure (8 hquad LRET + ctl SAFE2 + endpoint FPIPE3, QPIN): gold4 EXACT 63,028 -> 63,153 (+125 fixed cycles per gamma-5 draft, not a Markov-scaled head occupancy; ctl/ep/hquad views routing) | 1,594.2 | +0.00 | -0.01 | | |
| bf_half (CANDIDATE, not adopted) | BF SAFE B: element at half rate (ot_s81_bf_native HALF=1, claude/dsrom-bf-rowfix-20261007 61c1cf230, exact PASS; closure-loop bf_half_61c1cf230): BF16 field phases doubled (upper bound; fracs = BF16 phase share (go->idle+1)/node, field_qelem_qx10.json, a_proj max over layer types); adopt only if B closes first (variant A re-cut is the target).  UNDER-PRICED: BF pairs also hold 20.6 % of the q words, so HALF=1 on shared pairs doubles those q phases too (the BF-dedicated-pair plan of the BF doubling agent replaces it) | 1,355.4 | -14.98 | -12.58 | | |
| bf_recut (CANDIDATE, not adopted) | BF re-cut A (ot_s81_bf_native RECUT=2, claude/dsrom-bf-rowfix-20261007 260869fd0; exact record e2d358837; closure-loop bf_recut_260869fd0): latency only, transaction lag per partial 4 / 7.9 / 15; upper bound +15 per field phase (wo_a 4 phases, a_proj 3) | 1,579.2 | -0.94 | -0.75 | | |
| bf_unroll (CANDIDATE, not adopted) | BF unroll-by-2 (ot_s81_bf_native RECUT=3, claude/dsrom-bf-rowfix-20261007 9cf64047e; exact record c394c0ace; closure-loop bf_unroll_9cf64047e): re-cut A + lane chains unrolled by 2 on a half-rate gated clock, latency only, lag per partial 4 / 8.8 / 18; upper bound +18 per field phase | 1,576.2 | -1.13 | -0.90 | | |
| selector_pipe2 (CANDIDATE, not adopted) | Selector PIPE2 (claude/s81-blocks-20261007 36b7a0452: selt_q hist input reg + pair-sum cuts, out-FIFO input reg, registered sweep bound, CMP_RETIME; selt_c MRG_PIPE + RQPIPE + SLAT 4): bench tail mean 153 vs 127 (+26 a segment over the +20 already priced) | 1,593.7 | -0.03 | -0.03 | | |
| pq_rootcam_B (CANDIDATE, not adopted) | PQ root CAM stage B (4251eb216, OPC 0): measured eight-leaf root +4 cycles vs native, charged per field phase (upper bound: every phase exposes one 8-leaf root) | 1,591.9 | -0.14 | -0.11 | | |
| pq_rootcam_CP (CANDIDATE, not adopted) | PQ root CAM stage C + PAR protected face (claude/s81-blocks-20261007 387610a35, OPC 1 PAR 1): eight-leaf +8 vs native (input station +1, operand fetch +1 a pass) | 1,589.5 | -0.29 | -0.23 | | |
| coll_gbx_fmt1 (CANDIDATE, not adopted) | Collective gearbox FMT1 (fixed 3-in-4 slot format, no bit shifter): slot rate 0.75 vs 0.765 per gearbox beat (-2.0 %), charged as +2.0 % of every collective node (upper bound; link-up is faster: TP4 bench end 3,012 vs 3,374 cycles) | 1,589.4 | -0.30 | -0.25 | | |
| fh_half (UNPRICED, not adopted) | The whole reduced gold4 core/memory/VM domain was slowed, not only the head. VOCAB4040, G4 x W16 is not a full-shape draft measurement. The previous 8,387 cycles per head position underpriced blocks and leaked into verification II. A whole-domain physical clock/CDC contract and full-shape composition are missing; no numerical candidate rate is published. | unknown | | | | |

Composed as-is (PENDING-DEFECT included): AR 1,594.2 (-4.82 %), MTP 4,696.0 (-4.07 %).  The table is a modeled cost composition, not physical adoption.
