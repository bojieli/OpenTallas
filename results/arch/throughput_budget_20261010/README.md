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

**SM HBM bandwidth floor (owner 2026-10-12).** Every SM weight line (136 B) is now priced at the SM's physical HBM share, 98.96 B/cycle (4 HBM3E stacks × 1.0 TB/s × 0.95 / 1.2 GHz / 32 SMs): 1.3743 cycles a line, not 1. SM.MATVEC goes from 103,968 to 126,876 cycles a token, and the DS S2 token from 2,121.8 to 2,080.8 tok/s. Qwen is unchanged. See `results/arch/hbm_bw_reprice_1012/README.md`.

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
- **SM.MATVEC:** 127k priced cycles after the 10-12 HBM floor (was 104k). d's `tb_hgi_sm_tput` rerun is pending.
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

## Provenance rule and automated bench II

**Provenance.** Every ratio must come from a committed bench record, with its path and commit (`measured_record` on each op row). The following are therefore downgraded to claims (`hand_entered`, never qualifying) and listed in `registry_gaps`:
- the Qwen-on-HBM ratios copied from budget_audit rows;
- the CP-fetch and svc-stream audit ratios;
- the removed KV-die name rule (1.124, a superseded model; qwen-1010/b is replacing it with the measured KV-die record).

COLL.ROW_GATHER now reads its ratio from the RGX matrix record (0.997).

**Automated bench II.** `bench_ii()` reads every CLOSED closure-loop job's passing exact benches and extracts the cycles line with its largest item count. This gives cycles per item, the job and the commit. An element qualifies by this route only under the fixed-pipeline full-rate rule: at most 1.10 cycles an item, with no stall-injected stimulus. Otherwise the line is attached to the element as `bench_ii`, with the budget still unmapped. `registry_gaps` lists, per owner, the elements that still need a production-shape throughput bench.

## Bound rule and measured trace windows (owner 2026-10-11)

**QUALIFIED_BY_BOUND.** An op or class qualifies by bound, with no throughput bench, when it is natively built and even a 10× slowdown moves the token rate by less than 1%:
- **HBM ops:** S2 is re-scheduled with the op at 10× its price.
- **ROM classes:** 9 × the class's critical cycles / token cycles < 1%.

The rule is recorded as `bound_rule` in budget.json.

**Apportioned trace windows.** Token-path nodes graded `apportioned` are op windows cut from a measured whole-layer RTL trace (for Qwen ROM, the stream4 RT_OPTRACE windows). They count as measured at production shape, which qualifies the Qwen ROM me and su classes.

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

S2 price 576,702.4 cycles = 2,080.8 tok/s; target 2,208.1 tok/s = 543,453.6 cycles, so every budget is the price × 0.9423.

| op | records / token | layers | price cyc / record | budget cyc / record at target | cyc / layer | items / record | required items / cycle | elasticity (+10 % price) | measured / price | grade | status | token cycles at measured | owner |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---|
| COLL.ALL_GATHER | 584 | 40 | 389.2 | 366.7 | 5,681.8 | 8,519 bytes | 21.89 | 2.62 % | 0.716 | unit_bench | **QUALIFIED** | -41,060.0 | hgi-1010/c + fe-push-hgi-1010 |
| SU.VOP | 1,356 | 40 | 100.6 | 94.8 | 3,409.7 | 1,585 elements | 15.76 | 1.78 % | 1.067 | unit_bench | **QUALIFIED** | +6,766.6 | hgi-1010/b |
| SM.MATVEC | 1,095 | 41 | 115.9 | 109.2 | 3,094.5 | 166,975 MACs | 1,441.08 | 1.45 % | 27.202 | unit_bench | **UNQUALIFIED** | +3,232,365.8 | el1011-hbm-smmv |
| COLL.GROUP_REDUCE_MCAST | 40 | 40 | 1,325.9 | 1,249.5 | 1,325.9 | 4,096 bytes | 3.09 | 0.92 % | 0.908 | e2e | **QUALIFIED** | -4,879.5 | - |
| FUSED.HC_PRE_NORM | 81 | 41 | 649.3 | 611.9 | 1,282.8 | 20,480 elements | 31.54 | 0.91 % | 0.715 | unit_bench | **QUALIFIED** | -12,407.7 | hgi-1010/b |
| HC.HC_MIX_POST | 80 | 40 | 540.0 | 508.9 | 1,080.0 | 24 elements | 0.04 | 0.00 % | 1.282 | unit_bench | **UNQUALIFIED** | 0.0 | hgi-1010/d |
| DMA.LOAD | 340 | 40 | 104.4 | 98.3 | 887.1 | 1,153 bytes | 11.05 | 0.09 % | 0.622 | e2e | **QUALIFIED** | -1,927.5 | - |
| COLL.ROW_GATHER | 8 | 8 | 4,246.0 | 4,001.2 | 4,246.0 | 1,048,576 bytes | 246.96 | 0.59 % | 0.997 | unit_bench | **QUALIFIED** | -101.9 | hgi-1010/c |
| COLL.TOPK_MERGE | 9 | 8 | 2,382.8 | 2,245.4 | 2,680.6 | 2,428 bytes | 1.02 | 0.37 % | 1.057 | unit_bench | **QUALIFIED** | +1,222.4 | el1011-hbm-idx |
| FUSED.HC_POST | 80 | 40 | 222.7 | 209.8 | 445.3 | 20,480 elements | 91.97 | 0.30 % | 1.096 | unit_bench | **QUALIFIED** | +1,667.4 | hgi-1010/b |
| ATT.QK | 40 | 40 | 329.5 | 310.5 | 329.5 | 16,384 MACs | 49.72 | 0.23 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | hgi-1010/g2 |
| ATT.PV | 40 | 40 | 329.5 | 310.5 | 329.5 | 16,384 MACs | 49.72 | 0.23 % | – | none | **UNQUALIFIED_NO_BENCH** | 0.0 | hgi-1010/g2 |
| IDX.TOPK | 40 | 40 | 283.0 | 266.7 | 283.0 | 384 elements | 1.36 | 0.20 % | 4.286 | unit_bench | **UNQUALIFIED** | +37,198.6 | hgi-1010/g2 |
| IDX.INDEX | 8 | 8 | 939.2 | 885.0 | 939.2 | 851,968 keys scored | 907.13 | 0.13 % | 8.603 | e2e | **UNQUALIFIED** | +57,125.6 | el1011-hbm-idxs |
| DMA.KVWB_DS | 40 | 40 | 60.0 | 56.5 | 60.0 | 2,048 bytes | 34.13 | 0.00 % | 1.050 | unit_bench | **QUALIFIED** | 0.0 | el1011-hbm-fq |
| DMA.FENCE | 40 | 40 | 60.0 | 56.5 | 60.0 | 0  | 0.00 | 0.00 % | 0.117 | e2e | **QUALIFIED** | 0.0 | - |
| FUSED.QDQ_FP8 | 40 | 40 | 24.0 | 22.6 | 24.0 | 512 elements | 21.33 | 0.00 % | 2.740 | unit_bench | **ACCEPTED** | +958.1 | tput-gate-1010 |
| COLL.ARGMAX_MERGE | 1 | 1 | 765.4 | 721.3 | 765.4 | 8 bytes | 0.01 | 0.01 % | 0.802 | e2e | **QUALIFIED** | -151.6 | hbm-coll |
| ARGMAX.LOCAL | 1 | 1 | 142.7 | 134.4 | 142.7 | 1,347 elements | 9.44 | 0.00 % | – | none | **QUALIFIED_BY_BOUND** | 0.0 | UNOWNED |

### DS bottleneck ranking (measured shortfalls, token cycles on S2 with only that op at its measured ratio)

| # | op | measured / price | + cycles / token | tok/s lost | budget cyc / record (at target) | owner |
|---:|---|---:|---:|---:|---:|---|
| 1 | SM.MATVEC | 27.202 | 3,232,365.8 | -1,765.8 | 115.9 (109.2) | el1011-hbm-smmv (restructure + sm_pub arrival overrun) |
| 2 | IDX.INDEX | 8.603 | 57,125.6 | -187.5 | 939.2 (885.0) | el1011-hbm-idxs |
| 3 | IDX.TOPK | 4.286 | 37,198.6 | -126.1 | 283.0 (266.7) | hgi-1010/g2 (TOPKW=1 heap, 9473077de) |
| 4 | FUSED.QDQ_FP8 | 2.740 | 958.1 | -3.5 | 24.0 (22.6) | tput-gate-1010 (WIDE 2.74x ACCEPTED by owner rule; route hgi_quant_wide-68fe4bf34 + hb_quant lgE slot-2 share) |
| 5 | HC.HC_MIX_POST | 1.282 | 0.0 | 0.0 | 540.0 (508.9) | hgi-1010/d |

### DS ops with no production-shape bench (UNQUALIFIED_NO_BENCH), by exposure (token cycles if 2× price)

| op | price cyc / token | exposure if 2× | owner | interim |
|---|---:|---:|---|---|
| ATT.QK | 13,181.8 | 13,206.5 | hgi-1010/g2 (ATT PIPE=2 a7613320f; wide VM wclient open) | main a7613320f ATT PIPE=2: H4 D128 NL2 vehicle QK T512 1,951 cyc (not DS production shape hd512 / 1M) |
| ATT.PV | 13,181.8 | 13,206.5 | hgi-1010/g2 | main a7613320f ATT PIPE=2: PV T512 2,968 cyc (vehicle, not production shape) |

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
| SM.MATVEC | 145 | 6,718.3 | 6,660.1 | 13,048,444 | 7.68 % | – | UNQUALIFIED_NO_BENCH | 986,819.0 |
| COLL.ALL_REDUCE_SUM | 72 | 1,350.0 | 1,338.3 | 16,384 | 0.77 % | – | UNQUALIFIED_NO_BENCH | -8,650.8 |
| SU.VOP | 362 | 147.8 | 146.6 | 2,028 | 0.42 % | – | UNQUALIFIED_NO_BENCH | 101,214.2 |
| ATT.QK | 72 | 660.1 | 654.4 | 1 | 0.38 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| ATT.PV | 72 | 660.1 | 654.4 | 1 | 0.38 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| FUSED.ROW_NORM | 145 | 150.2 | 148.9 | 2,380 | 0.17 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| DMA.LOAD | 149 | 106.6 | 105.7 | 8,210 | 0.00 % | – | QUALIFIED_BY_BOUND | 861.1 |
| SFU.GLU | 36 | 120.0 | 119.0 | 3,072 | 0.03 % | – | UNQUALIFIED_NO_BENCH | 8,190.7 |
| ARGMAX.LOCAL | 1 | 2,394.0 | 2,373.3 | 37,984 | 0.00 % | – | QUALIFIED_BY_BOUND | 0.0 |
| DMA.STORE | 72 | 30.0 | 29.7 | 1,024 | 0.02 % | – | UNQUALIFIED_NO_BENCH | 7,128.0 |
| DMA.FENCE | 36 | 60.0 | 59.5 | 0 | 0.02 % | – | UNQUALIFIED_NO_BENCH | 0.0 |
| COLL.ARGMAX_MERGE | 1 | 586.0 | 580.9 | 8 | 0.01 % | – | QUALIFIED_BY_BOUND | 0.0 |

### ROM pipelines (token-path node prices; per-class critical cycles and the stage II limiter)

**qwen_rom** (4810.9 tok/s, 249,431.0 cycles; 37 stage groups; II limiter Layer 1 = 6,835.0 cycles)

| class | critical cyc / token | share | measured fraction | status | unbenched nodes |
|---|---:|---:|---:|---|---|
| me | 124,746.0 | 50.0 % | 100.0 % | QUALIFIED | 0 () |
| link | 75,600.0 | 30.3 % | 100.0 % | QUALIFIED | 0 () |
| su | 45,676.0 | 18.3 % | 100.0 % | QUALIFIED | 0 () |
| head | 3,101.0 | 1.2 % | 100.0 % | QUALIFIED | 0 () |
| embed | 272.0 | 0.1 % | 0.0 % | QUALIFIED_BY_BOUND | 1 (embed) |

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
| DS | SM.MATVEC | FP8 | NOT_BUILT | 290 | 63,860.5 | 24,260.4 | 2,172.2 | rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv refuses x fmt 1 / 2 (x_fault): no FP8 block-dot x path (audit ds_sm_xload_fp8_fp4_no_peer; FP8 x-path rebase = fe-push-hgi-1010 / hgi-1010/d) |
| DS | SM.MATVEC | FP4 | NOT_BUILT | 720 | 26,386.9 | 1,029.6 | 2,084.5 | rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv refuses x fmt 2 |

Rate figures these ops inflate (each prices the op at its simulator cost although no RTL runs it): DS AR fixed-RTL 2,121.8 tok/s (results/arch/hgi_sim_20261010/ds_rates_g25.json AR.fixed_rtl); DS AR table 2,208.1 (budget_audit targets / token_path hbm_gen_ds); DS MTP fixed-RTL 3,640.3 tok/s (ds_rates_g25.json MTP.fixed_rtl); this budget's DS S2 2080.8 tok/s.

### Hand-entered ratios (unmeasured; never qualify)

| model | op / element | claimed ratio | source | owner |
|---|---|---:|---|---|
| Qwen | SM.MATVEC | 2.013 | budget_audit table.json qwen_sm_xload_serial (2,762 measured vs 1,372 designed a record) | el1011-hbm-smmv (restructure + sm_pub arrival overrun) |
| Qwen | COLL.ALL_REDUCE_SUM | 0.911 | budget_audit table.json hbm_qwen_allreduce | hgi-1010 |
| Qwen | SU.VOP | 2.896 | budget_audit table.json qwen_su_sfu (measured rtl/sim) | hgi-1010/b |
| Qwen | DMA.LOAD | 9.204 | budget_audit table.json hbm_dma_load | hgi-1010 |
| Qwen | SFU.GLU | 2.896 | budget_audit table.json qwen_su_sfu (SU/SFU staging, same row) | hgi-1010 |
| Qwen | ARGMAX.LOCAL | 1.263 | budget_audit table.json qwen_head_stream_chain | UNOWNED |
| Qwen | DMA.STORE | 4.3 | budget_audit table.json hbm_qwen_dma_store | hgi-1010 |
| qwen_rom | KV die (name rule) | 1.124 | removed hand rule (superseded audit model) | qwen-1010/b |

### Automated bench II (75 elements with a cycles line in a passing exact closure-loop bench)

| element | II (cycles / item) | item | stalled stimulus | job @ commit | line |
|---|---:|---|---|---|---|
| dsfd_cap_mtp_ep | 562.5 | flits |  | fixlat-capmtp-ffbec0c86-tc @ ffbec0c86 | FIXLAT pep_s1 PASS (expect pass) :: PEP PASS FC=6 RC=7 FV=11 RV=11 VM-end hops 11/11 flits=4x1200 cycles=2250  |
| dsfd_coll_p2_ep | 79.681 | rows |  | el1011-collp2-966562e4c-tc-a @ 966562e4c | FIXLAT p2_s1 PASS (expect pass) :: P2FL PASS FV=12 RV=14 FC=8 RC=9 transactions=2 rows=160 lane0=320 lane1=160 |
| dsfd_coll_p2_lane_ba | – | items | yes | qf-p2lba-ogrant-5b059065b-tc-hm0-lvt @ 5b059065b | MEASURED_ACCEPT, density 0.025: 1.079 cycles an item |
| dsfd_coll_p2_lane_pa | – | items | yes | mtpl-dsfd_coll_p2_lane_pa-0ddaf548b-tc-hm10-b @ 0ddaf548b | MEASURED_ACCEPT, density 0.321: 34.504 cycles an item |
| dsfd_colt_lane | 3.688 | reads |  | s81ph-dsfd_colt_lane-ring-e96dd1e56-tc-hm10-g12-ttfix @ e96dd1e56 | COLT_RING PASS cycles=100000 reads=27118 |
| dsfd_hstnh_515 | – | – |  | s81-dsfd-hstnh-515-pe-4a12f4d5d-tc-cl @ 4a12f4d5d | HSTNH_PE PASS cycles=2000 |
| dsfd_mtp_seed_launch | – | items | yes | mtp-seedl-4b2f329b3-tc @ 4b2f329b3 | MEASURED_ACCEPT, density 0.566: 1.000 cycles an item |
| dsfd_mtp_seq | 450.25 | issues |  | mtp-mtp_seq-b-511fa714d-tc @ 511fa714d | {"case": "s0_tr_forced", "expect": "pass", "params": {"MODE": 0, "NUSR": 2}, "defines": [], "trace": {"trace": |
| dsfd_mtp_seq_rtt | 457.315 | issues |  | mtp-seq-rtt-native-61b4bc729-tc @ 61b4bc729 | {"case": "rtt_rly_s0_tr_forced", "expect": "pass", "params": {"MODE": 0, "NUSR": 2, "SEQ_RTT": 1, "RLY": 1}, " |
| dsfd_p2_lnk | 1.0 | items |  | fixlat-p2lnk-c917ea78d-tc-hm20 @ c917ea78d | MEASURED_ACCEPT, density 1.0: 1.000 cycles an item |
| dsfd_svc_join | – | – |  | svc_join-a6cf4500f-tc @ a6cf4500f | SVC_JOB_GATE PASS b1=0 b2=0 b3=0 ns1=0 ns4=0 tile1=0 tile4=0 dropstart=1 wrongdesc_end=1 wrongdesc_nq=1 earlyd |
| dsfd_svch_pcs | 3.163 | beats |  | svch_pcs-eccab9f14-pd60-tc @ eccab9f14 | SVCHPCS sent=3000 beats=6639 max_outstanding=8 errors=0 fault=0 cycles=21000 verdict=PASS |
| dsfd_svcio_job | – | – |  | svcio_job-a6cf4500f-tc @ a6cf4500f | SVC_JOB_GATE PASS b1=0 b2=0 b3=0 ns1=0 ns4=0 tile1=0 tile4=0 dropstart=1 wrongdesc_end=1 wrongdesc_nq=1 earlyd |
| dsfd_vm_be_sl | – | – |  | s81vm-besl4a-c15e2bf6a-tc-rd-pd45 @ c15e2bf6a | RESULT cyc=64000 checked=43251 mismatches_or_fails=0 phases=120 arm=120 p2rd=714 done=8322 rows_ready=60 start |
| dsfd_vm_clt | – | – |  | s81vm-clt8-964ae59f7-tc-rd-pd40 @ 964ae59f7 | RESULT cyc=64000 checked=44301 mismatches_or_fails=0 phases=139 arm=139 p2rd=671 done=8141 rows_ready=69 start |
| dsfd_vm_mtp_ep | 562.5 | flits |  | fixlat-vmmtp-189894fc2-tc-hm20 @ 189894fc2 | FIXLAT pep_s1 PASS (expect pass) :: PEP PASS FC=6 RC=7 FV=11 RV=11 VM-end hops 11/11 flits=4x1200 cycles=2250  |
| dsfd_vm_p2_ep | 79.325 | rows |  | fixlat-vmp2-ffbec0c86-tc @ ffbec0c86 | FIXLAT p2_s1 PASS (expect pass) :: P2FL PASS FV=12 RV=14 FC=8 RC=9 transactions=2 rows=160 lane0=320 lane1=160 |
| dsfd_vm_wfc_ep | – | – |  | mtp-vm_wfc_ep-rd2-9c9ac6963-tc @ 9c9ac6963 | OK         rd2_stg_r1         expect=pass MTP_STG PASS jobs=60 starts=60 out=60 cycles=17939 vmslow=0 core_use |
| dsfd_wfc_crp | – | – |  | el1011-wfccrp-bb847e831-tc-hm25-pr @ bb847e831 | OK         crp_stg_r1             expect=pass MTP_STG PASS jobs=60 starts=60 out=60 cycles=27585 vmslow=0 core |
| dsfd_wfc_lnk | – | – |  | mtp-wfc_lnk-b-0cd6caa1b-tc @ 0cd6caa1b | {"case": "stg_r1", "expect": "pass", "params": {"SEED": 1, "NJOB": 60}, "defines": [], "result": "MTP_STG PASS |
| dsfd_wfc_vmx | 1.015 | items |  | mtp-wfc_vmx-prd-c39e235bb-tc-o292-r2-cl @ c39e235bb | MEASURED_RECORDED, density 0.986: 1.015 cycles an item |
| hfd_att_su_relay | – | – |  | hfd_att_su_relay-d578aa824-tc-cl @ d578aa824 | pos.log:RELAYCHAIN N=9 cycles=20000 in=13919 out=13899 mismatches=0 latency=9 RELAY_PASS |
| hfd_hc_tile_xl | – | – |  | hfd_hc_tilexl-cons1011-c95527ec0-tc-hm10-pd55-pka10-cl @ c95527ec0 | TILE_XL PASS cycles=600 active=583 rootskew_ns=0.100 |
| hfd_idx_t4_join | 2.962 | beats | yes | hgi_idx_t4_join-fe-f7cabb9b7-b-tc-cl @ f7cabb9b7 | PASS atomic T4 join beats=342 cycles=1013 depth128 downstreamstall500 MEM=1 FE=1 |
| hfd_su_tile_xl | – | – |  | hfd_su_tilexl-fe-fa7b65cba-sw147-ongrid-pdnp-tc-hm10-pd55-cl @ fa7b65cba | TILE_XL PASS cycles=300 rootskew_ns=0.100 |
| hgi_att_rows_g12_120 | 1.751 | rows |  | hgi-att-g12-120-187a8471c-tc-cx @ 187a8471c | PASS CF-ATT cases=142 rows=1081866 cycles=1894250 legacy_lockstep=300 |
| hgi_att_rows_g12_140 | 1.751 | rows |  | hgi-att-g12-140-187a8471c-tc-cx @ 187a8471c | PASS CF-ATT cases=142 rows=1081866 cycles=1894250 legacy_lockstep=300 |
| ot_attn_tile_m6h1q | – | – |  | hbm_attn_quad_cg-pka-04424cd9f-tc-hm10-grta-cl @ 04424cd9f | TILERLOCK cycles=12000 mismatches=0 ov=3597 gated_quad0=1060 stale=0 guard_faults=0 |
| ot_coll_fold_slice | – | – |  | coll_fold_slice_rt-rt1-ae9fa22a9 @ ae9fa22a9 | se gather_1w margin=7 mutant=0 PASS mismatches=0 words_out=1024 cycles=355 |
| ot_dsrom_aq12t | – | – |  | el1011-pqc-aq12t-c-9b9338026-tc-cl @ 9b9338026 | AQ12T_EQ PASS valid_outputs=26534 cycles=40000 |
| ot_dsrom_hc_input_reader | – | – |  | hcreader-plain300-lk-b678636a2-tc-cl @ b678636a2 | PASS full shape 3x1280 BF16 means 120 flits cycles=17011 CE=0 |
| ot_dsrom_hc_mean_capture | – | – |  | hcmean-mc560-lk-a7bdfef93-tc-cl @ a7bdfef93 | PASS full shape 3x1280 BF16 means 120 flits cycles=16943 CE=0 |
| ot_dsrom_hc_seed_join | – | – |  | hcjoin-mc420-lk-d4211f538-tc-cl @ d4211f538 | PASS join120frames cycles=1099 CE=0 reset=0 |
| ot_dsrom_su_hcpost_lane_pr | – | – |  | hbm_hcp_lane_pr_79315a431-tc @ 79315a431 | PASS_HCPOST_LANE_PR cycles=20000 outputs=15083 latency=+1 |
| ot_dsrom_wfc_tokpipe_src | – | items | yes | mtp-wfc-src-hard-mxb-910e67c7b-tc-cx @ 910e67c7b | MEASURED_ACCEPT, density 0.003: 1.000 cycles an item |
| ot_dsrom_wfc_tokpipe_stg | – | items | yes | mtp-wfc-stg-tokpipe-9f7a7f35e-tc @ 9f7a7f35e | MEASURED_ACCEPT, density 0.148: 1.051 cycles an item |
| ot_hbm_index_global_order | 38.919 | tuples |  | gorderscan_fast2_a-f11374855-tc-hm10 @ f11374855 | PASS_GLOBAL_ORDER ranks=96 tuples=4096 actual_reads=4288 cycles=159412 |
| ot_hbm_index_global_order_mt | 5.034 | tuples |  | hbm_gorder_mt_ref-v1-23c517d1e @ 23c517d1e | PASS_GLOBAL_ORDER ranks=96 tuples=12288 actual_reads=12480 cycles=61862 |
| ot_hbm_native_candidate_format | 2.155 | packets |  | candfmt_rb-937531860-tc-hm10-cl @ 937531860 | FORMAT_DONE packets=863 flits=118 cycles=1860 errors=0 |
| ot_hbm_native_candidate_parse | 1.3 | tuples |  | candparse_rb-937531860-tc-hm25-cl @ 937531860 | PARSE_DONE tuples=60 cycles=78 |
| ot_hbm_native_index_query_credit | 7.0 | blocks |  | qcredit_rb-2db44a8cd-tc-hm25-cl @ 2db44a8cd | QUERY_DONE blocks=256 cycles=1792 |
| ot_hdc_v41x_sfu_chain | – | – |  | hbm_sfu_chain-b70b0112c-c108-tc-cl @ b70b0112c | random N=16 seed=2 ops=38 pass=True vm_bad=0 kv_bad=0 faults=0 order=0 cycles=1109 |
| ot_hgi_argmax18_m | 2382.875 | rows |  | hgi_argmax18_pinsep-30853dbe1-pd55-tc-cl @ 30853dbe1 | HGI_ARGMAX18 PASS rows=8 cycles=19063 DS_LOCKSTEP=1 |
| ot_hgi_coll_row_formatter | – | – |  | hgi_coll_row_formatter_c130-264ff331a-tc-cl @ 264ff331a | B=8 K=2048 W=32 destinations=96 badrow=-1 cycles=333826 |
| ot_hgi_coll_tkm_tile | – | – |  | hgi-coll-tkm-tile-c-7258eeb45-tc-cl @ 7258eeb45 | OK syn_cand expect=PASS got=PASS CYCLES=7073 SURV=5682 INS=1425 SINK=7062  / syn_cand |
| ot_hgi_cp_mtp_pinreg | – | – |  | hgi_cp_mtp_pinreg-a-7d9c1b45e-tc-cl-r2 @ 7d9c1b45e | PASS HGI_CP_MTP_PINREG system drained reset twice native40layer pairedresults finitequeue cycles=26539 |
| ot_mtp_p2_prefix_path | – | items | yes | mtp-p2-path-rb4-s-9dda063ff-tc @ 9dda063ff | MEASURED_ACCEPT, density 0.502: 1.000 cycles an item |
| ot_qkvd_fbuf8 | – | – |  | qkd_fbuf8-a-87a8d98ac-tc-hm10-ka @ 87a8d98ac | PASS buf_tile D=8 cycles=200000 pops=70919 head_gap_cycles=13082 |
| ot_qkvd_sbuf | – | – |  | qkd_sbuf-a-87a8d98ac-tc-hm10-ka @ 87a8d98ac | PASS buf_tile D=48 cycles=200000 pops=72516 head_gap_cycles=12358 |
| ot_s81_host_dispatch | 1.0 | items |  | s81hdisp_rb-937531860-tc-hm25-cl @ 937531860 | MEASURED_RECORDED, density 1.0: 1.000 cycles an item |
| ot_s81_ingest_visibility_fence | – | items |  | sp-visfence-006e20771-tc-hm10-cl @ 006e20771 | MEASURED_RECORDED, density 1.0: 86.000 cycles an item |
| ot_su12_sfu | – | – |  | hbm_sfu_lane_ring3_aa5dd28d5 @ aa5dd28d5 | random N=16 seed=3 ops=37 pass=True vm_bad=0 kv_bad=0 faults=0 order=0 cycles=1604 |
| ot_v41_rom_elem_q_qxpq_w10 | – | – |  | dsrom-qelem-qs5f-efs-7fb23b7ff-tc-hm10-cl @ 7fb23b7ff | QS5_GATE_BOUND_PASS sources=37 positives=5 negatives=3 cycles=12775002 |
| qfd_coll_xfifo | – | – |  | qfd_coll_xfifo_a-66fd85cda-tc @ 66fd85cda | case reduce_8w PASS NCOLL_NATIVE PASS cycles=481 |
| qfd_coll_xfifo_b | – | – |  | qfd_coll_xfifo_b-66fd85cda-tc @ 66fd85cda | case reduce_8w PASS NCOLL_NATIVE PASS cycles=481 |
| qfd_coll_xfifo_l8 | – | – |  | qfd_coll_xfifo_l8n_a-6d8e992da-tc-cl @ 6d8e992da | case reduce_8w PASS NCOLL_NATIVE PASS cycles=318 |
| qfd_coll_xfifo_l8_b | – | – |  | qfd_coll_xfifo_l8n_b-6d8e992da-tc-cl @ 6d8e992da | case reduce_8w PASS NCOLL_NATIVE PASS cycles=318 |
| qfd_embed_code_bank_parent | 7.838 | words |  | qfd_embed_code_bank_parent_flat-e510ca8c2tt @ e510ca8c2 | PASS embed words=4096 cycles=32103 first_latency=7 min_gap=2 duplicate_credit=detected metadata_faults=7 SS_RO |
| qfd_embed_code_bank_retained | 7.838 | words |  | qfd_embed_code_bank_retained-24bd6a53b-tt @ 24bd6a53b | PASS embed words=4096 cycles=32103 first_latency=7 min_gap=2 duplicate_credit=detected metadata_faults=7 SS_RO |
| qfd_embed_ingress_code | 7.838 | words |  | qfd_embed_ingress_code-0e025d03c @ 0e025d03c | PASS embed words=4096 cycles=32103 first_latency=7 min_gap=2 duplicate_credit=detected metadata_faults=7 SS_RO |
| qfd_embed_ingress_code_numeric | 7.838 | words |  | qfd_embed_ingress_code_numeric-82c12047d-lbc @ 387a4d2ac | PASS embed words=4096 cycles=32103 first_latency=7 min_gap=2 duplicate_credit=detected metadata_faults=7 SS_RO |
| qfd_embed_ingress_code_padded | 7.838 | words |  | qfd_embed_ingress_code_padded-3d5ad2a4ftt @ 3d5ad2a4f | PASS embed words=4096 cycles=32103 first_latency=7 min_gap=2 duplicate_credit=detected metadata_faults=7 SS_RO |
| qfd_io_collective_fs | – | – |  | qfd_io_collective_fs-b760fc991-tc-cl @ b760fc991 | se gather_1w margin=7 mutant=0 PASS mismatches=0 words_out=1024 cycles=355 |
| qfd_io_emb_root | 3.228 | requests |  | qfd_io_emb_root-1e23a4915-lvt-tc @ 1e23a4915 | PASS qfd_embedding_rom NCOL=3 NTAP=4 PINREG=0 requests=6000 responses=6000 cycles=19370 |
| qfd_io_emb_tap | 3.228 | requests |  | qfd_io_emb_tap-c1e4eba84tt @ c1e4eba84 | PASS qfd_embedding_rom NCOL=3 NTAP=4 requests=6000 responses=6000 cycles=19370 |
| qfd_io_serdes | 1.126 | words |  | qfd_io_serdes_adapter_rxd512_pin-073694e6b-tc @ 073694e6b | PASS qfd_link_adapter W=1024 RXD=512 LAT=223 words=2000 each way cycles=2252 |
| qfd_res_ctl | 8.191 | beats |  | qfd_res_ctl-f46a68c8a-tc-hm0 @ f46a68c8a | PASS res_tiles bursts=360 beats=1465 cycles=12000 request_to_chain=19 request_to_output=21 peak_bursts=55 |
| qfd_row_merge_native_fence | 1.471 | halves |  | rowfence_b-7eea9e354-tc @ 7eea9e354 | PASS_ROW_FENCE layers=24 heads_last_layer=126 halves=3200 fence_hold_edges=3328 cycles=4706 |
| qfd_seq_su | – | – |  | qfd_seq_su-fea-f3e3d6b6f-tc-hm0-cl @ f3e3d6b6f | PASS seq_su_bi_psram cycles=20997 program_reads=800 loads=600 |
| qfd_seq_su_bi_fea | – | – |  | qfd_seq_su_bi-fearl-19fe61d1d-tc-hm0-cl @ 19fe61d1d | PASS seq_su_bi_psram cycles=20997 program_reads=400 loads=200 core_done=0 cwait=19050 coll=0 vm_writes=0 chase |
| qfd_seq_su_bi_feb | – | – |  | qfd_seq_su_bi-febra-dace0dae3-tc-hm0-cl @ dace0dae3 | PASS seq_su_bi_psram cycles=20997 program_reads=400 loads=200 core_done=0 cwait=19050 coll=0 vm_writes=0 chase |
| qfd_sp_constants_sequencer_sys | – | – |  | qfd_sp_constants_sequencer_sys_icut_t-a8f3ba53c-tc-hm10-lvt-cl @ a8f3ba53c | SYS_CASE pos=8191 starts=38 me=440 su=1448 coll=146 cycles=43612 bad=0 |
| qfd_sysctl_stn_pb2 | – | – |  | qfd_sysctl_stn_pb2_cl-d4760be45-tc-hm10-b-cl @ d4760be45 | s=00000000 turn_min=21 turn_max=100 turn_avg=87 step_cycles=736 CL=40 cycles=6226309 |
| qfd_tile | – | – |  | qfd_tile_lsl3-17c2e7993-tc-hm0-cl @ 17c2e7993 | "verdict": "PASS GT=16 TG=4 SMIN=3 SMAX=4 TCUT=3 BD=2 XVM=0 NWS=1 TWS=2 ORD=1 ops=300 cycles=22937 result_writ |
| qfd_tile_lsl | – | – |  | qfd_tile_lsl6-e032e6e6f-tc-hm0-cl @ e032e6e6f | "verdict": "PASS GT=16 TG=4 SMIN=3 SMAX=4 TCUT=3 BD=2 XVM=0 NWS=1 TWS=2 ORD=1 ops=300 cycles=22937 result_writ |

### DS ROM BF of record: hierarchical full-rate (ot_v41_bf_col + ot_s81_bf_front)

| item | value |
|---|---|
| target | AR 1,553.4 / MTP 4,443.6 tok/s (hier_compact on the current base; Option A (compact column + front <= 198.72 um tall, pair <= 1,031.6 um); else HALF_PHL fallback) |
| budget (bench workload: 456 rows, 232 partials, 4,288 issues) | 124,422 issue cycles + 3 cycles a partial |
| measured | 124,422 issue cycles; partial lag +2.499 ns mean / +2.499 ns max = +3.0 cycles |
| measured / price | 1.0 (QUALIFIED) |
| timing | column: bfh_col600_28fa6290c-cl CLOSED TT +34.26 / FF +0.67 (compact col: bfh_compact220_col_a1200); front: bfh_compact220_front_a1200_84d63c93f-cl CLOSED TT +87.90 / FF +9.98 (main 943cad2b2); results/rtl/s81_bf_arch_20261009/compose/summary.json: interface TT +265.8 / FF +45.1 balanced |
| evidence | results/rtl/s81_bf_arch_20261009/bench/tcg0.json, results/rtl/s81_bf_arch_20261009/bench/hcol.json, results/rtl/s81_bf_arch_20261009/bench/full.json |

ROM blocks outside the token-path classes: 226 covered by name rules (`rom_block_rules`); unmapped: ot_qwen_rom_tile_nk, ot_qwen_slab_port_group.

### Registry gate (elements)

451 elements mapped: ACCEPTED 3, EXEMPT 15, QUALIFIED 352, QUALIFIED_BY_BOUND 10, UNQUALIFIED 38, UNQUALIFIED_NO_BENCH 33.

