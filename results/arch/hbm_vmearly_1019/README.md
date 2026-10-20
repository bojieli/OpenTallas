# HBM-VMEARLY (10-19): compiler early issue of VM-bank reads (model)

Lane HBM-VMEARLY. Branch `claude/hbm-vmearly-1019`. Tool: `tools/hgi_sim/d4g_vmearly_1019.py`. It wraps LH-REPRICE3
(`d4g_reprice3b_1019`, `--bw 45.03`, the current controller) without changing any term. The only change is a copy of
`timing.schedule` with the early-issue rule in the tool docstring. **This is a model, not a price of record.** The RTL
measurements come from the sub-lanes HBM-VMEARLY-XL, -COLL, -DMA and -IDX (see `lanes/HBM-VMEARLY*.md`).

## Rule

The S2 schedule charges each VM-bank round trip as unit occupancy, so it is fully exposed on every record.

Early issue changes this. Record i's VM read issues at:

`t_iss = max(RAW producers retired + wire, start(i-N), end(i-N-1) - RT)`

and the record computes at `max(unit free, t_iss + RT)`. The consumer holds NBUF = N + 1 operand slots, and the slot index is
static. Only the read part of each budget is hidden:

- x-load: the x leg.
- COLL: 2 of its 3 COLL_VM crossings.
- DMA: VM->HBM moves only.
- IDX/ARGMAX: the whole op-reader budget.

The rest stays exposed.

N = 0 reproduces LH-REPRICE3 exactly: 1,206.3 / 407.0.

## Result (DS AR at 45.03 B/edge/SM; Qwen AR)

| row | N=0 (as priced) | N=1 (double buffer) | N=2 |
|---|---:|---:|---:|
| info_banklat_all (every term + bank-latency budgets), DS tok/s | 1,206.3 | **1,264.3 (+4.8 %)** | 1,264.3 |
| same, Qwen tok/s | 407.0 | 408.3 (+0.3 %) | 408.3 |
| bank-latency term on top of `all`, DS cycles | 97,960 | **52,364 (-46.5 %)** | 52,364 |
| x-load alone (info_gen2c_xload), DS tok/s | 1,783.0 | 1,853.4 | 1,864.9 |
| COLL alone (info_bl_coll) | 1,781.5 | 1,820.9 | 1,820.9 |
| DMA alone (info_bl_dma) | 1,875.8 | 1,875.8 | 1,875.8 |
| IDX alone (info_bl_idx) | 1,879.5 | 1,881.9 | 1,881.9 |

If the TOKEN-REC composition ratio is applied (1,233.4 / 1,206.3), the composed DS rate is about **1,293** (an estimate, not
a price).

## Exposed VM-bank edges for a typical DS layer (layer 5, AR, record list in layer5_records_n1.tsv)

| client | records | base (fully exposed) | N=1 exposed | what binds the rest |
|---|---:|---:|---:|---|
| x-load (SM.MATVEC / ATT) | 29 | 1,295.7 | 294.1 | 9 records RAW-bound: x is the previous record's output (wq_a/wq_b/wo_a/wo_b, router gate, expert w2 after the SU, attention q/P) |
| COLL | 13 | 704.3 | 301.1 | 6 gathers / reduce of the operand that was just produced |
| IDX.TOPK | 1 | 181.0 | 164.0 | route.top6 reads the router scores produced just before |
| DMA (KV window append) | 1 | 27.8 | 15.8 | reads the KV row produced just before |
| **layer total** | 44 | **2,208.8** | **775.0** | |

The N=2 result equals N=1 on the composed row: the window and slot constraints never bind there; everything left is
RAW-bound.

## Reading

- One record of issue-ahead (NBUF 2) hides every round trip whose operand was already resident. These are the expert w1/w3
  pairs sharing x, wkv, and the expert intermediate gathers. It recovers 46.5 % of the term (+4.8 % DS).
- The remaining 52.4k cycles are true producer -> VM -> consumer dependences, plus the COLL write crossing, the DMA LOAD leg
  and the IDX result write. Early issue cannot hide them. The levers are:
  1. Shorter round trips: the GEN2d floorplan places the IDX readers and the COLL shares beside their bank groups (IDX 181
     -> ~20).
  2. Producer -> consumer forwarding: the SU output goes straight into the x-store or COLL operand slot (dataflow level 2)
     instead of a VM write and a read-back.
- Hand-off: TOKSIM-HBM (lanes/TOKSIM-HBM.md).
