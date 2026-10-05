# DS ROM scenario C re-check: build S81, not S82 and not S73

Every figure here comes from the model, except the credit-depth sweep. That sweep is measured directed RTL (Icarus), against the W1 sources pinned at 046bf5026.

## Why S73 failed

C priced S73 at 855.9 mm². Codex priced it at 897.56 mm². The whole 41.7 mm² gap is the return tree:

| Item | C | Codex | Δ |
|---|---:|---:|---:|
| Fixed debit, of which complement removal is applied in **neither** | 465.48 | 465.48 | 0 |
| Variable + post-r4 increments. Field padding trim is applied in **both**. | 385.41 | 379.18 | −6.23 |
| Return storage | 5.01 (credit RD4 at NP2682) | 52.90 (RD64 at NP4096) | **+47.89** |

The +47.89 return gap has two parts:
- **29.9 mm²** is credit depth. W1 measured RD4 and rejected it: the slot-reuse loop is 9 cycles, and the saturated loss is 54%.
- **18.0 mm²** is return padding. NP4096 storage was kept for only 2,682 pairs.

## What the RD sweep measured

The bench is a 4-leaf, 2-level tree compared against the RD64 reference (`credit_rd_sweep.json`).

| Credit depth | Saturated loss | Loss in 8-row/40-cycle rounds | Notes |
|---|---:|---:|---|
| RD4 | 53.8% | 0.4% | |
| RD8 | 10.3% | 0 | |
| RD16 | 0 | 0 | Exact, 0 added cycles |
| RD32 | 0 | 0 | Exact, 0 added cycles |

When sibling skew exceeds WAIT = 2, the RD64 reference itself overflows. The credit tree stalls without a fault there.

## Levers

| Lever | Δ area at S73 (mm²) | Per-user | First S at ≥ 2% margin |
|---|---:|---:|---:|
| L1: ragged RD64 return (no new logic) | −17.98 | 0 | 81 |
| L2: credit RD16 ragged return | −39.64 | 0 | 77 |
| L3: one stage fewer | about −5/die | −0.482 µs, −4 dies | – |
| **L4: replicate the 20 TP-unsharded indexer projections on all 4 ranks** | 0 | **−29.48 µs** (parallel ports) to −85.37 µs (one shared link) | – |
| L5: PHY credit / removal of the 287 mm² complement | about −30 | 0 | not adoptable until W4 maps the rectangles |

Notes on L4:
- The screen never credited the deduplication (`frame_credit_mm2 = 0`).
- The multicast costs latency and saves no area.
- C never carried this term.

**S73 cannot reach 2% margin with any adoptable lever.** With RD16 it lands at 857.9 mm² (0.01% margin), and it needs another 17.1 mm² that only L5 could supply.

## Prices

In each a/b pair, a is the 1M value and b the 200K value. The wavefront verify is a separate pending factor and is not applied.

| Design | mm² (margin) | Dies | AR tok/s | MTP τ 3.649 | Static kW (ICG / batch-1 PG) | Batch-1 PG AR tok/s per kW, 1M |
|---|---:|---:|---:|---:|---:|---:|
| S82, Codex, multicast on parallel ports | 856.54 (0.17%) | 372 | 2,296.5 / 2,389.8 | 3,618.6 / 3,948.3 | 21.80 / 7.35 | 301.4 |
| S82, multicast on one shared link | 856.54 (0.17%) | 372 | 2,035.2 / 2,108.2 | 3,407.6 / 3,698.4 | 21.80 / 7.35 | 268.2 |
| **S81: ragged RD64 + replication** | **839.24 (2.19%)** | **368** | **2,466.2 / 2,574.1** | **3,742.8 / 4,096.7** | 21.59 / 7.32 | 324.1 |
| S77: credit RD16 + replication | 837.91 (2.34%) | 352 | 2,478.0 / 2,586.9 | 3,751.1 / 4,106.7 | 20.74 / 7.19 | 331.1 |

S81 against S82 at 1M: AR is +7.4% against the parallel-ports case and +21.2% against the shared-link case.

The credit RD16 lever over S81 is **REJECTED** under the owner rule: it gains only +0.48% per user (<1%), even though it would save 16 dies and 0.85 kW. Reopen it only if the owner prefers the die count. Before adoption it would then need the L0/L20 occupancy gate and ASAP7 synthesis of the RD16 node.

## Build

**S81** (2,417 pairs per die). It has three parts:
1. The unchanged `ot_v41_retn_w17w10` nodes, wired by the W1 ragged generator topology, with the ragged golden reduction order.
2. Indexer `wk` and `wq_b` issued locally on every rank, with no canonical-owner multicast.
3. Everything else as in the Arendt S82 directory, re-run at `--stages 81 --pairs 2417 --bf 519`.

## Replay

```
python3 tools/dsrom_credit_rd_sweep.py --out /tmp/rdsw   # then strip log_tail -> credit_rd_sweep.json
python3 tools/dsrom_c_recheck.py --verify
```
