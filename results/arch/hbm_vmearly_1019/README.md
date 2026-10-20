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

## Integration 10-19 ~22:00 (int_1019/): DMA + IDX rules in the model, rotated layout, N=1 for every client

The tool now carries the per-client rules from the sub-lanes (tool docstring):

- **DMA** (HBM-VMEARLY-DMA bc57f015e): `dma_min_next_issue`, an ISSUE_AHEAD 0 calendar, because the controller holds one
  move. bl_dma is charged on VM-read DMA records only (KVWB/STORE/swap-out). `OT_VME_BLDMA=all` reproduces LH-REPRICE3.
- **IDX** (HBM-VMEARLY-IDX 0b423e28d): `A_i = max(RAW_i, F_i - LB)` with LB = bl_idx + 2 = 183. NBUF 1: the query store is
  the static slot.
- **x-load / COLL**: NBUF 2 (the slots are built by HBM-VMEARLY-XLCOLL).
- **Layout**: rotated bank layout for every stream (`OT_VME_LAYOUT=rotated`). A successor-bandwidth run with any other layout
  is refused.

Composed row `info_banklat_all`, N=1 for all clients:

| controller | N=0, bl_dma every record (LH-REPRICE3) | N=0 + bl_dma split | **N=1, all rules** | `all` (no bank-latency term) |
|---|---:|---:|---:|---:|
| H9b current, 45.03 B/edge/SM: DS / Qwen tok/s | 1,206.3 / 407.0 | 1,217.6 / 407.2 | **1,276.6 / 408.4** (+5.8 % / +0.3 %) | 1,338.1 / 410.1 |
| successor PC (release, rotated), 90.67 + bridge 1 | 1,406.9 / 746.7 | 1,422.3 / 747.2 | **1,494.3 / 751.4** (+6.2 % / +0.6 %) | 1,596.8 / 757.0 |

DS exposed bank-latency edges per token, base -> N=1, at 45.03:

- x-load: 52,499 -> 11,955
- COLL: 30,449 -> 13,514
- DMA: 1,112 -> 632
- IDX: 8,763 -> 7,872 (RAW-bound)

At 90.67 the x-load figure is 14,721 at N=1.

What is left is RAW-bound: producer -> VM -> consumer dependences. Early issue cannot hide it. The levers are GEN2d placement
(shorter IDX/COLL round trips) and producer -> consumer forwarding.

Even with all bank-latency removed, the successor only reaches DS 1,596.8, still below the owner's 1,600-1,700. So the
bank-latency term alone does not close the gap.

The IDX bench `tb_idx_vme_n12` needs the n12 `#(171)` RTL from `claude/hbm-banklat-idx-1019`, which is not on main yet.
Its committed evidence stands either way.
