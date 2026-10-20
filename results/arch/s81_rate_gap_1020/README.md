# S81-RATE: why the measured DeepSeek S81 rate is below the estimate (2026-10-20)

Owner question: why is the measured S81 rate much lower than the estimate? This is an analysis only, based on
measurements. **Nothing is re-priced.** The projections in section 3 are estimates. They are not prices and not evidence.

Inputs (all on main): `results/token_pass/measured_s81_1019/cycles.json` (main 4989e8845, 80.25 % AR / 71.64 % MTP
measured), the same file at 265735167 (the 37 %-measured composition), `results/arch/token_path_1018/ds_rom.json` (the
10-19 composition), and `results/arch/token_path_20261009/ds_rom*.json` (the DAG, whose node cycles are the price of
record's per-stage numbers). Scripts are in this directory and run in seconds:
`python3 table.py <cycles.json> <cycles_at_265735167.json>`, `python3 project.py <worktree> projection.json`,
`python3 solved_path.py <worktree>`.

## Headline chain (AR cycles per token at 1.2 GHz)

| step | AR cyc | AR tok/s | MTP step cyc | MTP tok/s | what changed |
|---|---:|---:|---:|---:|---|
| price of record | 899,140 | 1,334.6 | 1,300,313 | 3,838.2 | p4l DV price: DAG + p4l/scan/L20 ledger; xdie priced (236.6k AR) |
| 10-19 composition (11 % measured) | 989,619 | 1,212.6 | 1,381,861 | 3,611.7 | **only xdie changed**: xdie_s81_1019 co-sim legs + PHY modelled at 453 cyc/crossing = 327.1k (+90.5k) |
| 37 % measured (265735167) | 1,173,913 | 1,022.2 | 1,566,172 | 3,186.6 | wq_b fullsix (+96.4k), index path (+72k), scores (+9.5k), SU exchange (+14k), small gains (-6.5k) |
| 80 % measured (main, now) | 1,438,803 | **834.0** | 1,883,939 | **2,649.1** | the remaining field matvecs measured (+249.8k), window_load (+11.3k), idx.q_field (+6.3k), softmax gains (-28k), basis = re-solved path (+21.7k) |

**The 1,022 -> 834 drop (+264.9k AR cycles) comes from more stages being measured. It is not a regression.** At 37 %,
the five biggest field matvecs still carried their old-die (m221pq) numbers. Measuring them on the p4l release RTL
added: wo_a +105.6k, experts_gu +53.7k, wo_b +36.6k, down +35.2k and router +18.7k (249.8k in total). window_load
(+11.3k) and the new idx.q_field node (+6.3k) add more. Measured softmax/gather/a_proj gains take back -28.0k, edges
add +4.8k and the LEG xdie hook adds +3.6k. The headline basis also changed from the fixed path (1,022.2) to
max(fixed, re-solved). With the faster softmax, the unmeasured `attn.pv` branch (23.8k, still on its old number)
became the longest path, which adds +21.7k (`solved_path.txt`). On the solved basis the 37 % figure was already
1,010.7. MTP follows the same pattern and also adds wave.busy (+73.9k), now measured from its components.

## 1. Per-stage table: measured vs priced (AR, critical path)

Priced = the DAG node cycles of the price of record. Measured = cycles.json now. Total gap = 1,438,803 - 899,140 =
**539,662 cycles (-37.5 % tok/s)**. Class codes are defined in section 2.

| stage (op) | n | priced /inst | measured /inst | priced total | at 37 % | measured total | delta | share of gap | class | cause (measured law) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| attn.wo_a | 40 | 2,222 | 4,862 | 88,880 | 88,880 | 194,480 | +105,600 | 19.6 % | S 53.2k + P 52.4k | 12 BF16 phases a frame run **serially** (8x354 + 4x348 = 4,224) + 584 wire; no multi-phase calendar is compiled |
| attn.wq_b | 40 | 1,144 | 3,556 | 45,754 | 142,160 | 142,240 | +96,486 | 17.9 % | S 54.9k + P 41.6k | 15 epochs on the serial calendar at P224 (231 + 224x14 + 1 = 3,359); the P126 pipelined calendar measures 1,987, bit-exact |
| ffn.experts_gu | 40 | 2,364 | 3,706 | 94,572 | 94,572 | 148,240 | +53,668 | 9.9 % | P | already back-to-back at the minimum period P145 (23x145 + 345); p4l puts 6 experts x w1/w3 = 24 phases on one frame in every layer |
| attn.wo_b | 40 | 549 | 1,464 | 21,956 | 21,956 | 58,560 | +36,604 | 6.8 % | S 22.8k + P 13.8k | 4 FP8 phases a frame run serially (4x316); the old die had 1 phase |
| attn.idx.topk_local | 8 | 1,473 | 5,993 | 11,784 | 47,945 | 47,945 | +36,161 | 6.7 % | H | p4l index reader is HBM-bound (8,702 cyc for 43,691 keys vs 3,724 in record D), then serial select; L2/8/14 spans 14.2k |
| ffn.down | 40 | 2,205 | 3,086 | 88,191 | 88,191 | 123,440 | +35,249 | 6.5 % | P | already back-to-back at P130 (20x130 + 289); 21 phases a frame |
| attn.idx.topk_final | 8 | 178 | 3,382 | 1,424 | 27,059 | 27,059 | +25,635 | 4.8 % | H | the release final is rung-ingress bound (6.5k vs a price of 178) |
| ffn.router | 40 | 977 | 1,445 | 39,088 | 39,088 | 57,800 | +18,712 | 3.5 % | H | 5 BF phases at the P231 floor: at <=230 the return words alias the next segment index (tag width) |
| attn.window_load | 32 | 178 | 532 | 5,699 | 5,699 | 17,024 | +11,325 | 2.1 % | S | HBM-latency bound; issued in sequence, not prefetched (W_SLACK 560 assumes latency <=56) |
| attn.idx.score | 8 | 2,285 | 3,657 | 18,282 | 29,253 | 29,253 | +10,971 | 2.0 % | H | re-index scorer L24..36, 5,829 each, HBM-bound reader |
| attn.scores | 40 | 53 | 289 | 2,104 | 11,560 | 11,560 | +9,456 | 1.8 % | H | svc GO -> last fold score at 1M context |
| attn.idx.q_field | 8 | 0 | 783 | 0 | 0 | 6,264 | +6,264 | 1.2 % | M | the indexer wq_b rows were missing from the price (new DAG node) |
| ffn.norm.scale + attn.q_quant + attn.quant | 120 | 306 / 288 / 324 | 438 / 418 / 418 | 36,720 | 50,960 | 50,960 | +14,240 | 2.6 % | D | a 16-slice neighbour exchange (247) replaces the star-hub reduction |
| attn.exp / max / sink / a_proj | 160 | | | 66,774 | | 43,766 | -23,008 | -4.3 % | gain | measured release SU/softmax faster than the old RTL |
| other on-die ops (34 types) | | | | 71,042 | | 60,311 | -10,730 | -2.0 % | gain | den, normalize, gather, z_quant, q_rope, softplus, hc_*, ... |
| **cross-die (coll + hop)** | | | | 236,598 | 327,076 | 330,628 | **+94,030** | **17.4 %** | M | co-sim legs measured on G8R2 + PHY modelled at 453 cyc/crossing vs the priced xdie; LEG hook +3.6k |
| p4l / scan / L20 / residual terms | | | | 70,274 | 67,607 | 67,609 | -2,665 | -0.5 % | gain | scan_d_reader measured 0 (inside topk_local) |
| re-solved path (attn.pv now longest) | | | | 0 | (13.3k unused) | 21,664 | +21,664 | 4.0 % | M | attn.pv 596/layer is still old-RTL, so the softmax gains moved the path onto it |
| **total** | | | | **899,140** | **1,173,913** | **1,438,803** | **+539,662** | **100 %** | | |

The S/P split of a field op comes from the measured laws. **S** = measured serial minus the same phases pipelined at the
measured minimum go period (wq_b P126 is measured; wo_a uses the BF floor P231; wo_b uses the FP8 P126). **P** = what
remains above the price.

MTP (step cycles, gap 583,626 = -31.0 %) has the same shares. wo_a is 18.1 %, wq_b 16.5 %, gu 9.2 %, wo_b 6.3 %,
topk_local 6.2 %, down 6.0 %, topk_final 4.4 % and router 3.2 %. Two items are specific to MTP: **wave.busy +73.9k
(12.7 %)**, the 5 draft positions now built from measured components, and xdie +85.4k (14.6 %). Full rows are in
`table_raw.txt`.

Accounting caveat (direction: the real rate is lower). FGU measured shared_gu + experts_gu back to back on the same
frame at 4,314 (experts 3,680 + shared 634). The DAG has shared_gu off the critical path (n_crit 0), so about 25k AR
cycles (-1.7 %) are not yet charged. This goes to TOKSIM.

## 2. Classification (AR share of the 539.7k gap)

| class | cycles | share | items |
|---|---:|---:|---|
| **S: compiler schedule bubbles** (serial phases, no overlap, no prefetch) | 142.2k | **26.3 %** | wq_b 54.9k, wo_a 53.2k, wo_b 22.8k, window_load 11.3k |
| **P: p4l field placement, modelled on the old die by the price** (more phases a frame; each phase pays the ~290-350 go->RET latency incl. landing) | 196.7k | **36.4 %** | experts_gu 53.7k, wo_a 52.4k, wq_b 41.6k, down 35.2k, wo_b 13.8k |
| **H: hardware structure** (top-k, HBM-bound index reader, tag width, svc fold) | 101.0k | **18.7 %** | topk_local 36.2k, topk_final 25.6k, router 18.7k, idx.score 11.0k, scores 9.5k |
| **D: safe-design closure costs** (neighbour exchange in place of the hub, pin pipes, landings, source-age edges) | 14.2k (+4.8k edges inside the field rows) | 2.6 % (+0.9 %) | SU 16-slice exchange; CAP_EDLD 3,072, CAPC2 416, VPX 520, guard 385, LEPCAP 387 |
| **M: modelling error in the price** | 122.0k | **22.6 %** | xdie +94.0k (priced crossings vs co-sim + 453 PHY), attn.pv path +21.7k, idx.q_field +6.3k |
| measured gains | -36.4k | -6.7 % | softmax/SU, a_proj, scan_d_reader |

Reading: **the hardware runs at about the rate it was designed for per phase. The token is slow because the compiled
field schedule runs a matvec's phases one after another**: each BF/FP8 phase waits for the previous one's last
frame-root return. On p4l a frame also holds 2-12x more phases of one op than the old die the price measured.
Safe-design cost (D) is small (about 3.5 %, inside the ledger). Most of the price-model error is the cross-die term,
which the 10-19 composition already showed.

## 3. Fixes for each class over 3 % (estimates, from measured laws; `project.py` re-runs the committed composer)

| id | class | fix (best practice) | basis | AR gain | MTP gain |
|---|---|---|---|---:|---:|
| F1 | S | wq_b pipelined calendar P126 into the die-level DV compiler (TOK2); CAP/deadline contract repair | **measured** WQBP 1,987 bit-exact | +33.1 tok/s (-54.9k) | +89.8 |
| F2 | S | wo_a: multi-phase BF calendar (phase i+1 GO at P231 after phase i, not after its RET): 11x231 + 354 | BF period floor measured (router/a_proj P231) | +32.0 (-53.2k) | +86.9 |
| F3 | S | wo_b pipelined at P126 (FP8, same as wq_b) | wq_b law | +13.5 (-22.8k) | +36.6 |
| F8 | S | window_load prefetch: issue the static HBM read at layer start, hidden behind wq_b | latency 532 measured | +6.6 (-11.3k) | +16.1 |
| F5 | H | top-k final TAIL_FINAL 276 (S81-TOPK hist32/succ quarter) or INDEXED13 | RATEFIX bench measured | +14.5 (-24.5k) | +80.8 (wave.busy too) |
| F4 | H | widen the field return segment-index tag, so BF phases are not aliased at <=230: router P231 -> P145 | gu period P145 measured | +8.1 (-13.8k) | +22.0 |
| F6 | H | index reader split over more dies/HBM channels back to the record-D rate (3,724 per 43.7k keys); re-index scorer to its price | record D | +20.7 (-34.8k) | +49.8 |
| F7 | H | tournament (streaming) top-k under the reader, so selection is hidden (~4k a scan layer) | estimate | +7.0 (-12.0k) | +17.0 |
| F2b | H | with F4's tag, wo_a BF phases at P145 instead of P231 | gu law | +22.6 (-37.8k) | +61.3 |
| F10 | P | xs_place deals the 6 routed experts' gu/down rows over 2 frames a slice (half the phases a frame); **needs a ROM-slot capacity check** | gu/down laws | +77.0 (-121.6k) | +207.5 |
| F9 | M | chunked attn.out / ffn.combine all-reduce streamed as the wo_b / down rows return (static, overlapped with the producing matvec): ~900 of 1,500 exposed hidden a collective | xdie_summary exposed 60k + 60k | ~+42 (~-72k) | ~+105 |
| -- | M | measure attn.pv on release RTL (now on the solved path, old-RTL 596/layer) | | unknown | |

Projected rates (composer re-run with the savings; conservative max(fixed, solved)):

| set | AR tok/s | MTP tok/s | vs MTP floor ~3,000 |
|---|---:|---:|---|
| measured now | 834.0 | 2,649.1 | -11.7 % |
| A near-term, bench-proven: F1 F3 F5 | 897.8 | 2,867.0 | -4.4 % |
| B schedule + top-k: F1 F2 F3 F5 F8 | 943.3 | 2,989.1 | at the floor (-0.4 %) |
| C = B + F4 router tag | 953.6 | **3,017.1** | **+0.6 %** |
| D = C + index F6 F7 | 990.4 | 3,104.8 | +3.5 % |
| E = D + F2b (wo_a P145) | 1,022.4 | 3,189.3 | +6.3 % |
| E + F9 collective overlap (manual, estimate) | ~1,089 | ~3,343 | +11 % |
| F = E + F10 expert placement (capacity check needed) | 1,140.5 | 3,494.8 | +16.5 % |

Conclusions:

1. **MTP gets back to the owner floor with compiler-schedule work plus the top-k final already on the S81-TOPK track
   (set B/C).** No new hardware is needed beyond the segment-tag widening (F4). F1, F2, F3 and F8 are compiler work:
   one multi-phase pipelined field calendar (the generalisation of `xs_calendar.compile_pipeline`) applied to every
   matvec stage.
2. AR stays far below the price (1,334.6). The -15 % ledger floor (~1,134) needs placement work (F10) or
   collective/matvec overlap (F9) on top. Both are architectural and need a capacity or schedule check first.
3. Risks against the projection: shared_gu is not yet charged (-1.7 %), attn.pv is unmeasured, and MU co-sim is still
   open.

Order: F1 + F2 + F3 as one compiler deliverable (TOK2/TOKSIM, fullsix vehicles for wo_a/wo_b), F5 (S81-TOPK), F4 (RTL
tag in the field return path, owner LEAD4-S81 frame), F8 (compiler), then F6/F7 (index die split, an architecture
decision) and F10/F9 studies.
