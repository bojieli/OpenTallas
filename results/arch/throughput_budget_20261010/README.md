# Per-unit throughput budget and qualification, 2026-10-10

This record applies the owner's throughput-qualification rule (AGENTS.md, 2026-10-10, main 8a62d15ae). A unit is complete only when it:
- is bit-exact;
- closes timing;
- passes a production-shape throughput bench whose measured cycles are within 10% of the simulator price the token is charged for that unit (measured / price ≤ 1.10).

Timing closure alone never qualifies a unit.

`budget.json` holds the full record and `tools/throughput_budget/build.py` regenerates it:

```
python3 -m throughput_budget.build --out results/arch/throughput_budget_20261010/budget.json
```

Run it from `tools/`; it takes about 15 minutes of single-core Python. `tools/throughput_budget/readme.py` renders the tables below from the JSON.

## Method

**Top-down budget.** The budget comes from the target token rate. For each target, the exact per-die program is scheduled with the command processor modelled (S2):
- DeepSeek: the G25 rank-0 program that runs bit-exact on 96 dies;
- Qwen: `qwen_compiler`.

Each record is charged its simulator price. Per unit and op class, the budget is:
- the price per record and per token;
- the price per layer;
- the items a record moves or computes at production shape;
- the items per cycle the unit must sustain to meet the price.

The DeepSeek target is the table rate, 2,208.1 tok/s (543,454 cycles). The current G25 S2 price is 2,116.8 tok/s (with the corrected QDQ price below; 2,121.8 before), so each record's budget at target is its price × about 0.959. DS MTP uses τ = 4.159 on the same per-record prices (`hgi_sim_20261010/ds_rates_g25.json`: fixed RTL 3,640.3 tok/s).

**HBM fetch overlap.** Fetches overlap exactly as S2 models them. No fixed fraction of HBM peak is assumed: a weight or KV stream needs only its overlap-aware minimum (owner rule, 10-10 06:58).

**Measured column.** Each entry is RTL cycles divided by the simulator price on the same records, taken from the best production-shape evidence:
1. a unit bench (`results/rtl/hgi_unit_tput_20261010/*/report.json`);
2. failing that, the die e2e with every unit real (`results/rtl/hgi_e2e_20261010`);
3. or a price fitted to a measurement (`COLL.ROW_GATHER` G25 hardware).

Numbers that appear only in a stream log are listed as `interim` and never qualify a unit. A unit with no production-shape number is UNQUALIFIED_NO_BENCH.

**Bottleneck rank.** Each measured op is re-scheduled alone at its measured ratio, with everything else at price, and the extra token cycles are recorded. Unbenched ops are ranked by exposure: the token cycles they would cost at 2× price, from the +10% elasticity.

## Findings, DeepSeek on the HBM die first

1. **FUSED.HC_POST and FUSED.HC_PRE_NORM** (hgi-1010/b) are the dataflow's bottleneck by an order of magnitude. Measured at 20.1× and 6.5× (wide UN64, d 5,120; main 57499aeea), they add +339k and +290k cycles a token when applied alone.
   - Budgets: HC_POST ≤ 213.5 cycles and HC_PRE_NORM ≤ 622.6 cycles a record at the target (92 and 31.5 elements a cycle).
   - b's root cause (21:30): FUSED issues its micro-ops serially, and the HC_POST mix is a 4-term SEQ reduction on half the lanes. The fix, pipelined micro-op issue plus an elementwise mix chain, is b's.
2. **IDX.TOPK** (g2) is at 4.29×, +37k cycles. Budget: ≤ 271 cycles for a 384-score top-6. g2's TOPKW=1 heap with IW4 packed writes is under test.
3. **FUSED.QDQ_*** was at 14.6× (+10.4k cycles): the packet transport moved one sector every 2 cycles with ≤ 4 outstanding. Nobody was raising its rate, so **tput-gate-1010 took it** and built `ot_hgi_quant_unit` WIDE (`results/rtl/hgi_unit_tput_20261010/qdq_wide/`): 32 elements a cycle on the VM lane group, bit-exact, mutants fail, 65 cycles for a 512-element row with a registered boundary (5.4× faster).
   - The old price, ceil(n/32) + 8, left out the decode's 23-edge latency and the VM round trip, so it was unreachable by any structure. It is corrected to the measured ceil(n/32) + 49.
   - Measured/price is now 1.012–1.019, which qualifies the throughput. The route and the hb_quant lgE slot-2 share are still open.
4. **DMA.KVWB_DS** is at 3.8×, +5.4k cycles. The measurement predates c's posted KVWB retire (87b97e35e, `DMA_POSTED`), so it needs a regrade on the posted mover (c / e).
5. **HC.HC_MIX_POST** is at 1.28×, so UNQUALIFIED, but S2 has it off the critical path: it costs 0 token cycles.
6. **SU.VOP** at 1.067 and **COLL.ALL_GATHER** at 0.716 are qualified. So are GROUP_REDUCE_MCAST, DMA.LOAD, DMA.FENCE and ROW_GATHER (the last by price fit).

**Unbenched (UNQUALIFIED_NO_BENCH), by exposure:**
- **SM.MATVEC:** 104k priced cycles; 53k exposure at 2×. d's `tb_hgi_sm_tput` rerun is pending.
- **COLL.TOPK_MERGE:** 21k priced cycles, and there is **no RTL path**: `ot_hgi_coll_record` refuses op 2 ("merge stage not installed yet"). The merge engine exists (`ot_hgi_idx_merge`, IDX.MERGE), but nothing reaches it. A lowering proposal (two PIPE gathers plus IDX.MERGE) is posted to hgi-1010 for an owner.
- **ATT.QK and ATT.PV:** 13k cycles each. The PIPE=2 vehicle is H4 D128, not hd512 at 1M.
- **IDX.INDEX:** 7.5k cycles. Only the IKS key-stream piece is measured (1.36×, one stack).
- **ARGMAX:** small.

**`HC.HC_MIX_ROWS` is not in the G25 AR program.** The HC mixes lower to SU.VOP, a 24-word ALL_GATHER and HC_MIX_POST. The 125× HC_MIX_ROWS ratio and the HC weight-prefetch sizing (c40d28d23, 23.8 B/cycle a die) therefore do not move the DS AR price. They matter only if a program (MTP verify, or a later lowering) issues HC_MIX_ROWS again. This was flagged to hgi-1010.

**Today's whole-token composition** (`e2e_calibration.json`, all measured ratios together): 994.0 tok/s, against 2,121.8 at price. The FUSED pair accounts for almost all of the gap.

**DS S2 price change:** the corrected QDQ price (ceil(n/32) + 49, the registered-boundary successor; its RTL commit follows its gate) moves S2 by about −5 tok/s. `ds_rates_g25.json` (hgi-1010/e) is not regenerated here.

**The CP fetch** needs 0.867 B/cycle a die, overlap-aware (audit `hbm_ds_cp_fetch`). The one-sector native port gives 0.308, which is 2.8× short. Fixes in flight:
- hbm-phys `[svc-ep]` PS native endpoint;
- fe-push-hgi `RUNPRE` (d0b63f82d);
- kport NO 16 (bee505fe4).

**HBM loader / svc endpoint, per stack** (the table below): the reads that must keep their price are DMA.LOAD at 11.0 B/cycle a die while a load runs (2.8 a stack striped) and the CP fetch at 0.87 a die. The token averages are far lower: 0.72 and 0.15 B/cycle a die. The `[svc-ep]` sizing in hbm-phys-1010 (reads ≥ 6.2 B/cycle a stack, which includes the HC prefetch; writes ≥ 6) covers the DS AR program's needs.

## Build gate (PRICED-NOT-BUILT)

Every op the simulator prices must run natively in a committed RTL bench (unit or die e2e, real and exact, no stub, no behavioural model, no unsupported status). An op without one is PRICED-NOT-BUILT, and every rate that prices it is inflated by an unbuilt unit. The table under "Tables" lists the offenders with their priced cycles and their critical-path weight (S2 with the op at zero cost). `gaps/registry_gaps.py` prints the same list.

- **DS SM.MATVEC FP8/FP4 block-dot** (54.6k + 19.2k priced cycles, 20.3k on the critical path): `ot_hgi_sm_xload` refuses x fmt 1/2.
- **COLL.TOPK_MERGE** (21.4k priced, 21.0k critical): `ot_hgi_coll_record` refuses op 2.
- **IDX.INDEX** and **COLL.ARGMAX_MERGE**: RTL exists but no committed native bench.

## Registry gate

`tools/fleet_viz/elements.py` reads the `elements` map of the latest `results/arch/throughput_budget_*/budget.json`, from the working tree or else origin/main. Every element row in `/api/elements` and ELEMENTS.md then gets two fields:
- **`throughput`:** the worst status over the ops the element serves, with its ratio, limiting op and owner.
- **`gate`:** for example `CLOSED-TIMING, THROUGHPUT-UNQUALIFIED`.

`throughput_summary` counts, per target, the closed elements by throughput status. `gaps/registry_gaps.py` lists every throughput-unqualified element, CLOSED-TIMING first. An element becomes THROUGHPUT-QUALIFIED only when its ops' production-shape benches are all within 1.10.

**Mapping.**
- HBM elements map to the op classes they execute; see the `ELEMENTS` table in `build.py`.
- ROM elements map to their token-path class. The ROM node prices are themselves measured RTL unit cycles at production shape, so a class qualifies when at least 95% of its cycles are measured. Its few modelled nodes are listed as unbenched gaps.
- Relays, stations and other pure-transport elements carry no budget row (`NO-THROUGHPUT-BUDGET-ROW`).

## Tables

### DeepSeek-V4.1 1M on the generic HBM die (rank-0 head die, S2)

S2 price 566,881.1 cycles = 2,116.8 tok/s; target 2,208.1 tok/s = 543,453.6 cycles, so every budget is the price × 0.9587.

| op | records / token | layers | price cyc / record | budget cyc / record at target | cyc / layer | items / record | required items / cycle | elasticity (+10 % price) | measured / price | grade | status | token cycles at measured | owner |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---|
| COLL.ALL_GATHER | 584 | 40 | 389.2 | 373.1 | 5,681.8 | 8,519 bytes | 21.89 | 2.82 % | 0.716 | unit_bench | **QUALIFIED** | -41,550.1 | hgi-1010/c + fe-push-hgi-1010 |
| SU.VOP | 1,356 | 40 | 100.6 | 96.4 | 3,409.7 | 1,585 elements | 15.76 | 1.88 % | 1.067 | unit_bench | **QUALIFIED** | +7,149.6 | hgi-1010/b |
| SM.MATVEC | 1,095 | 41 | 94.9 | 91.0 | 2,535.8 | 166,975 MACs | 1,758.59 | 0.93 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | hgi-1010/d |
| COLL.GROUP_REDUCE_MCAST | 40 | 40 | 1,325.9 | 1,271.1 | 1,325.9 | 4,096 bytes | 3.09 | 0.94 % | 0.908 | e2e | **QUALIFIED** | -4,879.5 | - |
| FUSED.HC_PRE_NORM | 81 | 41 | 649.3 | 622.5 | 1,282.8 | 20,480 elements | 31.54 | 0.93 % | 6.514 | unit_bench | **UNQUALIFIED** | +290,013.7 | hgi-1010/b |
| HC.HC_MIX_POST | 80 | 40 | 540.0 | 517.7 | 1,080.0 | 24 elements | 0.04 | 0.00 % | 1.282 | unit_bench | **UNQUALIFIED** | 0.0 | hgi-1010/d |
| DMA.LOAD | 340 | 40 | 104.4 | 100.1 | 887.1 | 1,153 bytes | 11.05 | 0.09 % | 0.622 | e2e | **QUALIFIED** | -1,927.5 | - |
| COLL.ROW_GATHER | 8 | 8 | 4,246.0 | 4,070.5 | 4,246.0 | 1,048,576 bytes | 246.96 | 0.60 % | 1.000 | price_fit | **QUALIFIED** | 0.0 | hgi-1010/c |
| COLL.TOPK_MERGE | 9 | 8 | 2,382.8 | 2,284.3 | 2,680.6 | 2,428 bytes | 1.02 | 0.38 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | tput-gate-1010 |
| FUSED.HC_POST | 80 | 40 | 222.7 | 213.5 | 445.3 | 20,480 elements | 91.97 | 0.31 % | 20.085 | unit_bench | **UNQUALIFIED** | +339,233.8 | hgi-1010/b |
| ATT.QK | 40 | 40 | 329.5 | 315.9 | 329.5 | 16,384 MACs | 49.72 | 0.23 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | hgi-1010/g2 |
| ATT.PV | 40 | 40 | 329.5 | 315.9 | 329.5 | 16,384 MACs | 49.72 | 0.23 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | hgi-1010/g2 |
| IDX.TOPK | 40 | 40 | 283.0 | 271.3 | 283.0 | 384 elements | 1.36 | 0.20 % | 4.286 | unit_bench | **UNQUALIFIED** | +37,198.6 | hgi-1010/g2 |
| IDX.INDEX | 8 | 8 | 939.2 | 900.4 | 939.2 | 851,968 keys scored | 907.13 | 0.13 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | hgi-1010/g2 |
| FUSED.QDQ_FP8 | 40 | 40 | 65.0 | 62.3 | 65.0 | 512 elements | 7.88 | 0.04 % | 1.012 | unit_bench | **QUALIFIED** | +25.0 | tput-gate-1010 |
| DMA.KVWB_DS | 40 | 40 | 60.0 | 57.5 | 60.0 | 2,048 bytes | 34.13 | 0.03 % | 3.817 | e2e | **UNQUALIFIED** | +5,376.6 | hgi-1010/c |
| DMA.FENCE | 40 | 40 | 60.0 | 57.5 | 60.0 | 0  | 0.00 | 0.00 % | 0.117 | e2e | **QUALIFIED** | 0.0 | - |
| COLL.ARGMAX_MERGE | 1 | 1 | 765.4 | 733.8 | 765.4 | 8 bytes | 0.01 | 0.01 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | UNOWNED |
| ARGMAX.LOCAL | 1 | 1 | 142.7 | 136.8 | 142.7 | 1,347 elements | 9.44 | 0.00 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | UNOWNED |

### DS bottleneck ranking (measured shortfalls, token cycles on S2 with only that op at its measured ratio)

| # | op | measured / price | + cycles / token | tok/s lost | budget cyc / record (at target) | owner |
|---:|---|---:|---:|---:|---:|---|
| 1 | FUSED.HC_POST | 20.085 | 339,233.8 | -792.5 | 222.7 (213.5) | hgi-1010/b (FUSED UWIDE / wide VM lanes) |
| 2 | FUSED.HC_PRE_NORM | 6.514 | 290,013.7 | -716.4 | 649.3 (622.5) | hgi-1010/b (FUSED UWIDE / wide VM lanes) |
| 3 | IDX.TOPK | 4.286 | 37,198.6 | -130.4 | 283.0 (271.3) | hgi-1010/g2 (TOPKW=1 heap, 9473077de) |
| 4 | DMA.KVWB_DS | 3.817 | 5,376.6 | -19.9 | 60.0 (57.5) | hgi-1010/c (posted KVWB retire 87b97e35e merged; ratio predates it: regrade with DMA_POSTED) + e (e2e) |
| 5 | HC.HC_MIX_POST | 1.282 | 0.0 | 0.0 | 540.0 (517.7) | hgi-1010/d |

### DS ops with no production-shape bench (UNQUALIFIED_NO_BENCH), by exposure (token cycles if 2× price)

| op | price cyc / token | exposure if 2× | owner | interim |
|---|---:|---:|---|---|
| SM.MATVEC | 103,968.3 | 52,606.6 | hgi-1010/d (tb_hgi_sm_tput) + fe-push-hgi-1010 (sm_xload SRAM + FP8 x-path) | hgi-1010.log 20:04: SM DS ratio rerun with tb_hgi_sm_tput on exp_2c9860e12 -> d (pending) |
| COLL.TOPK_MERGE | 21,445.0 | 21,428.1 | tput-gate-1010 (taken 10-10: production-shape bench) |  |
| ATT.QK | 13,181.8 | 13,208.3 | hgi-1010/g2 (ATT PIPE=2 a7613320f; wide VM wclient open) | main a7613320f ATT PIPE=2: H4 D128 NL2 vehicle QK T512 1,951 cyc (not DS production shape hd512 / 1M) |
| ATT.PV | 13,181.8 | 13,208.3 | hgi-1010/g2 | main a7613320f ATT PIPE=2: PV T512 2,968 cyc (vehicle, not production shape) |
| IDX.INDEX | 7,513.6 | 7,539.5 | hgi-1010/g2 (idx chunk) + hbm-phys-1010 (IKS svc stripe) + e (IKS compiler c9d5c8dea) | results/rtl/hgi_unit_tput_20261010/iks/README.md: key-stream issuer q0 460 vs 339 priced (one stack; not the whole record) (ratio 1.36) |
| COLL.ARGMAX_MERGE | 765.4 | 793.6 | UNOWNED |  |
| ARGMAX.LOCAL | 142.7 | 0.0 | UNOWNED |  |

### HBM loader / svc endpoint budget (DS AR, per die; stack figures assume the 4-stack stripe)

| stream | kind | bytes / token | B / cycle at the record's price (die) | per stack | token average (die) |
|---|---|---:|---:|---:|---:|
| DMA.LOAD | read | 392,054 | 11.049 | 2.762 | 0.721 |
| DMA.KVWB_DS | write | 81,920 | 34.133 | 8.533 | 0.151 |
| COLL.ROW_GATHER | write (head-die HBM row write) | 8,388,608 | 246.956 | 61.739 | 15.436 |
| CP.FETCH | read | 478,720 | needs 0.867 (overlap-aware minimum) | – | designed 0.308 |

### Qwen3-8B 8K on the generic HBM die (S2)

S2 price 1,269,120.1 cycles = 945.5 tok/s; target 953.8 tok/s. Qwen on HBM is deprioritised (runs exactly; TOKEN_SAVE 10-10); ratios are the audit's Qwen-shape measurements.

| op | records / token | price cyc / record | budget at target | items / record | elasticity | measured / price | status | token cycles at measured |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| SM.MATVEC | 145 | 6,718.3 | 6,660.1 | 13,048,444 | 7.68 % | 2.013 | UNQUALIFIED | 986,819.0 |
| COLL.ALL_REDUCE_SUM | 72 | 1,350.0 | 1,338.3 | 16,384 | 0.77 % | 0.911 | QUALIFIED | -8,650.8 |
| SU.VOP | 362 | 147.8 | 146.6 | 2,028 | 0.42 % | 2.896 | UNQUALIFIED | 101,214.2 |
| ATT.QK | 72 | 660.1 | 654.4 | 1 | 0.38 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| ATT.PV | 72 | 660.1 | 654.4 | 1 | 0.38 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| FUSED.ROW_NORM | 145 | 150.2 | 148.9 | 2,380 | 0.17 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| DMA.LOAD | 149 | 106.6 | 105.7 | 8,210 | 0.00 % | 9.204 | UNQUALIFIED | 861.1 |
| SFU.GLU | 36 | 120.0 | 119.0 | 3,072 | 0.03 % | 2.896 | UNQUALIFIED | 8,190.7 |
| ARGMAX.LOCAL | 1 | 2,394.0 | 2,373.3 | 37,984 | 0.00 % | 1.263 | UNQUALIFIED | 0.0 |
| DMA.STORE | 72 | 30.0 | 29.7 | 1,024 | 0.02 % | 4.300 | UNQUALIFIED | 7,128.0 |
| DMA.FENCE | 36 | 60.0 | 59.5 | 0 | 0.02 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| COLL.ARGMAX_MERGE | 1 | 586.0 | 580.9 | 8 | 0.01 % | – | UNQUALIFIED_NO_BENCH | 0.0 |

### ROM pipelines (token-path node prices; per-class critical cycles and the stage II limiter)

**qwen_rom** (4810.9 tok/s, 249,431.0 cycles; 37 stage groups; II limiter Layer 1 = 6,835.0 cycles)

| class | critical cyc / token | share | measured fraction | status | unbenched nodes |
|---|---:|---:|---:|---|---|
| me | 124,746.0 | 50.0 % | 52.6 % | UNQUALIFIED_NO_BENCH | 144 (L0.qkv, L0.o_proj, L0.gate_up, L0.down) |
| link | 75,600.0 | 30.3 % | 100.0 % | QUALIFIED | 0 () |
| su | 45,676.0 | 18.3 % | 0.0 % | UNQUALIFIED_NO_BENCH | 180 (L0.rmsnorm1, L0.qknorm_rope, L0.attn_tail, L0.rmsnorm2) |
| head | 3,101.0 | 1.2 % | 100.0 % | QUALIFIED | 0 () |
| embed | 272.0 | 0.1 % | 0.0 % | UNQUALIFIED_NO_BENCH | 1 (embed) |

**ds_rom** (1447.7 tok/s, 828,878.4 cycles; 58 stage groups; II limiter Stage 29: L19, L20.ffn = 33,183.5 cycles)

| class | critical cyc / token | share | measured fraction | status | unbenched nodes |
|---|---:|---:|---:|---|---|
| field | 418,381.8 | 50.5 % | 99.5 % | QUALIFIED | 2 (E1.wkv, E14.wkv) |
| hop | 123,191.2 | 14.9 % | 73.0 % | UNQUALIFIED_NO_BENCH | 2 (E1.lead_flit, E14.lead_flit) |
| su | 116,151.3 | 14.0 % | 96.3 % | QUALIFIED | 43 (L0.attn.hc.fn, L0.ffn.hc.fn, L1.ffn.hc.fn, L2.ffn.hc.fn) |
| coll | 113,406.5 | 13.7 % | 98.1 % | QUALIFIED | 2 (E1.rows_allgather, E14.rows_allgather) |
| hbm | 26,084.8 | 3.1 % | 100.0 % | QUALIFIED | 0 () |
| select | 21,811.0 | 2.6 % | 100.0 % | QUALIFIED | 0 () |
| head | 8,765.5 | 1.1 % | 100.0 % | QUALIFIED | 0 () |
| embed | 1,074.3 | 0.1 % | 51.8 % | UNQUALIFIED_NO_BENCH | 4 (E1.hash, E1.hbm_read, E14.hash, E14.hbm_read) |

**ds_rom_mtp** (4238.4 tok/s, 1,177,528.1 cycles; 58 stage groups; II limiter verify Stage 29: L19, L20.ffn = 33,183.5 cycles)

| class | critical cyc / token | share | measured fraction | status | unbenched nodes |
|---|---:|---:|---:|---|---|
| field | 462,327.0 | 39.3 % | 99.2 % | QUALIFIED | 1 (accept.seed) |
| wave | 161,546.0 | 13.7 % | 100.0 % | QUALIFIED | 0 () |
| su | 149,594.7 | 12.7 % | 100.0 % | QUALIFIED | 0 () |
| coll | 135,421.7 | 11.5 % | 100.0 % | QUALIFIED | 0 () |
| hop | 135,397.6 | 11.5 % | 100.0 % | QUALIFIED | 0 () |
| head | 51,223.0 | 4.3 % | 99.0 % | QUALIFIED | 6 (draft.markov0, draft.markov1, draft.markov2, draft.markov3) |
| ctl | 30,651.0 | 2.6 % | 99.9 % | QUALIFIED | 2 (accept.commit, accept.round) |
| hbm | 26,399.8 | 2.2 % | 100.0 % | QUALIFIED | 0 () |
| select | 23,881.0 | 2.0 % | 100.0 % | QUALIFIED | 0 () |
| embed | 1,074.3 | 0.1 % | 99.9 % | QUALIFIED | 1 (accept.engram_rewind) |

### Build gate: priced ops with no native RTL bench (PRICED-NOT-BUILT)

every op the simulator prices needs a committed bench that executes it natively in RTL (no stub, no behavioural model, no unsupported status); else PRICED-NOT-BUILT.

| model | op | variant | status | records / token | priced cycles / token | critical-path cycles (op at 0) | rate if the op were free | evidence |
|---|---|---|---|---:|---:|---:|---:|---|
| DS | COLL.TOPK_MERGE |  | NOT_BUILT | 9 | 21,445.0 | 21,021.0 | 2,198.4 | rtl/hbm_accel/generic/collective/ot_hgi_coll_record.sv refuses op 2 ('merge stage not installed yet'); the IDX.MERGE engine (ot_hgi_idx_merge) is not reachable from the record path |
| DS | SM.MATVEC | FP8 | NOT_BUILT | 290 | 54,578.4 | 20,334.9 | 2,195.6 | rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv refuses x fmt 1 / 2 (x_fault): no FP8 block-dot x path (audit ds_sm_xload_fp8_fp4_no_peer; FP8 x-path rebase = fe-push-hgi-1010 / hgi-1010/d) |
| DS | IDX.INDEX |  | NO_NATIVE_EVIDENCE | 8 | 7,513.6 | 4,003.5 | 2,131.9 | ot_hgi_idx_index / _native exist; every committed die e2e runs IDX.INDEX as a stub (DS L2 with IDX stub); only the IKS key-stream issuer is benched (hgi_unit_tput_20261010/iks) |
| DS | COLL.ARGMAX_MERGE |  | NO_NATIVE_EVIDENCE | 1 | 765.4 | 765.4 | 2,119.7 | ot_hgi_coll_record op 3 + ot_hgi_coll_amerge exist; tb_hgi_coll_record checks only the endpoint control with a stubbed endpoint (no exact native data run committed) |
| Qwen | COLL.ARGMAX_MERGE |  | NO_NATIVE_EVIDENCE | 1 | 586 | 586.0 | 946.0 | ot_hgi_coll_record op 3 + ot_hgi_coll_amerge exist; tb_hgi_coll_record checks only the endpoint control with a stubbed endpoint (no exact native data run committed) |
| DS | SM.MATVEC | FP4 | NOT_BUILT | 720 | 19,200.0 | 224.0 | 2,117.7 | rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv refuses x fmt 2 |

Rate figures these ops inflate (each prices the op at its simulator cost although no RTL runs it): DS AR fixed-RTL 2,121.8 tok/s (results/arch/hgi_sim_20261010/ds_rates_g25.json AR.fixed_rtl); DS AR table 2,208.1 (budget_audit targets / token_path hbm_gen_ds); DS MTP fixed-RTL 3,640.3 tok/s (ds_rates_g25.json MTP.fixed_rtl); Qwen AR 953.8 tok/s (results/arch/hgi_sim_20261009/qwen_timing_P8191_v10.json S2); Qwen DFlash b16 1,791.8 tok/s (dflash_timing.json); this budget's DS S2 2116.8 tok/s; this budget's Qwen S2 945.5 tok/s.

### DS ROM BF of record: hierarchical full-rate (ot_v41_bf_col + ot_s81_bf_front)

| item | value |
|---|---|
| target | AR 1,553.4 / MTP 4,443.6 tok/s (hier_compact on the current base; Option A (compact column + front <= 198.72 um tall, pair <= 1,031.6 um); else HALF_PHL fallback) |
| budget (bench workload: 456 rows, 232 partials, 4,288 issues) | 124,422 issue cycles + 3 cycles a partial |
| measured | 124,422 issue cycles; partial lag +2.499 ns mean / +2.499 ns max = +3.0 cycles |
| measured / price | 1.0 (QUALIFIED) |
| timing | column: bfh_col600_28fa6290c-cl CLOSED TT +34.26 / FF +0.67 (compact col: bfh_compact220_col_a1200); front: bfh_compact220_front_a1200_84d63c93f-cl CLOSED TT +87.90 / FF +9.98 (main 943cad2b2); results/rtl/s81_bf_arch_20261009/compose/summary.json: interface TT +265.8 / FF +45.1 balanced |
| evidence | results/rtl/s81_bf_arch_20261009/bench/tcg0.json, results/rtl/s81_bf_arch_20261009/bench/hcol.json, results/rtl/s81_bf_arch_20261009/bench/full.json |

ROM blocks outside the token-path classes: 162 covered by name rules (`rom_block_rules`); unmapped: ot_dsrom_engram_lead_producer, qfd_sp_tree_top_b_f1a, qfd_sp_tree_top_b_f1b.

### Registry gate (elements)

360 elements mapped: QUALIFIED 146, UNQUALIFIED 49, UNQUALIFIED_NO_BENCH 165.

