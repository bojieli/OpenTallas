# HBM-AGSM8 (10-20): DS expert-intermediate gather TRAIN + static w2 GO (lever (c))

Lane HBM-AGSM8 (parent HBM-RATE8 / LEAD7-HBM), tree TOK.HDS. Base: the composed measured DS AR row of HBM-RATE7
(census `toksim_hbm_census_1019 --measured results/rtl/hbm_rate7_1020/census/m_all.json --bw 98 --bridge 1`,
job info_banklat_all): **1341.1 tok/s, 894.8k token cycles** (reproduced: `census/base.AR.json`, schedule 868,624.7).

## What the census showed (one DS layer, seg 10)
- Per layer the 7 `expert_intermediate_gather.s<k>` records (2304-word QBG gathers, measured 260.2 each) are 7 separate
  CP records on the non-pipelined COLL unit (7 x 260.2 = 1,821 serial), and every `expert slot k w2` SM.MATVEC waits
  on the COLL **unit** bit (CP drains every dispatched COLL record). swiglu end -> moe_sum.6 end = 2,612 cycles.
- The RAW edge is region `ea.s<k>` (gather k writes, w2 k reads); the wait is unit-granular, not segment-granular.
- The expert FFN window (w1 start -> moe end, ~5.3k of 19.2k cycles/layer) is **SM-bound**: 14 x 204 (w1/w3) + 7 x 221
  (w2) = 4.4k SM cycles. Any AG/SM-chain lever can only remove the AG latency exposed between swiglu and the w2 stream.

## Census variants (`tools/hgi_sim/agsm8_train_census_1020.py`, waits rebuilt for every new order; base_rb == base)
| variant | what | DS AR tok/s | token cycles |
|---|---|---|---|
| base | compiled order | 1341.1 | 894,806.7 |
| interleave | compiler only: s_k, w2_k pairs (wait bits) | 1345.7 | 891,743.5 |
| batch (a), step 129 | one 7-row gather launch, w2 keep whole-record COLL wait | 1326.0 (worse) | 904,945.9 |
| go (b) | per-record gathers, w2_k static GO on gather k | 1354.6 | 885,885.3 |
| **train_go (c), step 129** | **one 7-row launch (measured on-die step 129) + w2_k static GO on segment k** | **1363.8** | **879,894.8** |
| train_go (c), step 110.4 | same at the off-die-only step 773/7 (needs overlapping fires in the gather master) | 1370.7 | 875,479.7 |
| ep_static (info) | expert-granular pipeline: swiglu split per expert + static GO | 1334.0 (worse) | 899,574.1 |

Chosen: **(c) train_go at the measured step 129: +1.7 % (-14.9k token cycles), 1341.1 -> 1363.8 tok/s.** Gains come
from removing the unit-drain wait (w2 slot k starts on its own segment), not from batching alone ((a) alone is worse:
the w2 stream then waits for the whole train). AG crit 143.0k -> 118.1k; SM crit rises 290k -> 297k (now the binder).
Rule (module doc): segment k publishes at t0 + 260.2 + k * STEP (each segment keeps the measured single-record latency;
STEP = max(on-die busy span 129 MEASURED here, off-die train step 110.4 measured, coll.json)), w2_k starts at that
publication + LEAD 16 (the same retire wire 4 + SM dispatch wire 12 the wait path pays; the bench shows the GO can be
tight to the landing, so 16 is conservative). Outputs: `census/*.AR.json`, `census/v_tok_raw.txt`.

**1,600-1,700 is NOT reachable on the AG/SM chain**: the expert FFN is SM-bound after (c). The next lever is SM.MATVEC
itself (21 small expert records a layer at ~210 cycles each, fixed-cost dominated; e.g. one record for w1+w3 sharing x,
or multi-expert records), untested.

## RTL + bench (production shape, Verilator 5.050, fleet ot-epyc6)
- No gather-master change: `ot_hgi_coll_gq` already runs several descriptor rows from ONE launch (t_start per row) and
  faults a fire while busy. The train = 7 rows, t_start(k) = 129 k (busy span at VM_RT 74; a 128 spacing faults).
- NEW `rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_seg_go.sv`: static GO calendar for the w2 x-load, armed by the same
  launch broadcast; go_v @ L + 4 + off(k), off(k) = t_start(k) + span(F,R) (span 128). No credit / ready / wait bit.
- Bench `tb_agsm8_chain.sv` + `run_agsm8_chain.sh` (vehicle = tb_hgi_coll_gq at LANES 1 / VM_RT 74 / BANK_RT 72: 4 quadrant
  gather masters, both rings, real read / kq shares, banked VM models with compiled-edge reservation checks), golden
  `tools/hgi_sim/agsm8_chain_vectors_1020.py` (hdc_golden_v41.quant_fp8, 7 x 4 x 576 FP32, mixed distributions).
  At every GO the bench plays the slot-k w2 x-load: reads all 4 slices of segment k from the quadrant VM at the GO edge
  (destination poisoned first) and compares bit-exact.
- **PASS** (`bench/pass`): 2,128 VM words + 28 x-loads bit-exact, every read / write at its compiled edge, gq faults 1..4
  still caught. Segment k fires L+3+129k, last landing write L+131+129k, GO L+132+129k (lead 1 edge).
  **Train launch -> last landing 905 edges, -> last x-load GO 906** (7 separate records: 7 x (CP record + 260.2)).
- **Mutants, all FAIL as required** (fail witnesses committed): `bench/goe` (segment 4 GO one edge early: 1 word not
  landed in each quadrant), `bench/swap` (w2 slots 2/3 swapped vs landing order: 76 words), `bench/overlap` (SP 128:
  gather masters fault gq1111).
- Not measured here (kept at their measured laws): the w2 SM.MATVEC itself (smhbm_xl_f200, 221.2) and the off-die train.

## SAFE-DESIGN checklist (ot_hgi_coll_seg_go; gq unchanged)
1 Pins: PASS - every input (cfg_*, launch_v) and output (go_v, go_seg, fault) registered; reset via ot_rst_relay (2 sync + 1 relay).
2 Reach: PASS - leaf is ~200 flops, placed beside the SM x-load front (one per SM group); launch is the existing broadcast.
3 Fanout: PASS by construction - next offset via a one-hot AND-OR select (each one-hot bit 16 loads), hit term 32 loads,
  no runtime-indexed mux; native census owed at synthesis (see below).
4 Depth: PASS - 16-b equality on a preloaded register; offsets must be >= 2 edges apart (fault), the train is 129 apart.
5 Storage: PASS - 8 x 16 b = 128 b of flops (< 2 kb).
6 Floorplan: n/a - no new tile; lands inside the SM svc tile (die generator param, owed).
7 Clock: n/a - single clock, same domain as the SM front.
8 Schedule: PASS - static; every added cycle priced (STEP 129 measured, LEAD 16 = today's wait path) in the census.
Owed before any gate/bind: synthesis + PRE-GATE native32 census of the svc tile with the leaf; GEN2e die bind (SM x-load
issues on go_v instead of the CP COLL wait; DS compiler emits the 7-row launch + w2 records without the COLL wait bit
and with off(k)); SM-front integration bench (the bench plays the x-load; the SM RTL is not in this vehicle).
