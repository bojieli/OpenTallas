# V4.1 non-routed inventory and placement priorities

The checkpoint-header audit reconciles **8,522,921,408 bytes** of non-routed
ordinary-decode inventory exactly to the model profile. It reads tensor headers,
not payloads, and records tensor names, shapes, formats, category and source hashes.
This establishes storage accounting; it does not prove every byte is read on every
runtime path or that a proposed cache has the needed ports.

| Category | Packed bytes | Fraction of non-routed inventory |
|---|---:|---:|
| Attention projections and norms | 5,069,721,600 | 59.48% |
| Shared experts | 1,416,960,000 | 16.63% |
| Output head | 1,323,827,200 | 15.53% |
| Engram projection/gate, excluding lookup tables | 315,043,840 | 3.70% |
| Router | 157,409,280 | 1.85% |
| Hyper-connection coefficients/projections | 157,295,040 | 1.85% |
| Attention indexer | 45,130,752 | 0.53% |
| Attention compressor | 36,704,256 | 0.43% |
| Layer and final norms | 829,440 | 0.01% |

Attention matrices, shared experts and the head account for **91.64%** of this
inventory. The ROM-array architecture must price these paths explicitly alongside
routed experts. The HBM-array baseline must receive the same opportunity for
locality and persistent caching. An expert-only optimization cannot stand in for
a full decode architecture.

## What the source audit distinguishes

The pinned reference creates and uses each layer's `attn.wkv` in `_window_kv`.
Compressed-KV reuse does not eliminate those per-layer sliding-window projections.
The current non-routed inventory correctly retains them. The owner-local design
must distinguish the window path from shared compressed KV rather than deleting
all repeated KV weights or work.

The role classifier includes both router `bias` and `bias_vl` for all forty layers.
The pinned `Gate.forward` uses `bias_vl` only when `image_mask` is not None. For
the explicit text path with no image mask, **61,440 bytes** of vision-routing bias
are inactive. Subtracting only this proven conditional inventory yields
**8,522,859,968 bytes**. The difference is tiny and does not change the architecture
conclusions, but it demonstrates why an inventory is not automatically a complete
runtime traffic ledger. Other conditional paths and broadcasts still need auditing.
No production model inventory is changed here: storage must retain those tensors
unless deployment scope explicitly removes them.

Engram's 315 MB in this table is projection/gating data, not the 202.758 GB lookup
tables. Moving the lookup tables to external HBM does not remove the projection
work. The output head is an untied full projection; it is not interchangeable with
the input embedding row lookup.

## Primary array placement decisions to evaluate

- **Attention:** co-locate projection compute with layer scheduling and KV/index
  consumers where practical. Sweep matrix sharding against reduction/activation
  movement. The shared KV owner and each layer's window path need separate routes.
- **Shared experts:** keep these near their consuming layer because they execute
  every token. They are natural HBM-cache candidates; charge cache area and local
  service before selecting coverage. ROM places immutable weights locally.
- **Output head:** evaluate vocabulary-row partitioning. For greedy decode, local
  score/token candidates can avoid transporting all vocabulary logits, provided
  score precision and tie rules are preserved. Sampling and full-logit output
  require separate communication accounting; no universal small-result credit.
- **Engram projection/gating:** retain compute near the returned row data and
  consuming layer. Account for lookup completion latency before the projection.
- **Router and hyper-connections:** their smaller byte count does not make their
  critical-path numerical service negligible. Routing precedes expert dispatch;
  hyper-connection dependencies can serialize otherwise fast matrix engines.

These are placement candidates, not accepted schedules. First derive per-operator
service and cross-chip reductions, then compare area/power and achieved scheduling
bounds. Do not simply sort weights by size and call the result an optimal cache.
A 100 µs target requires all 8.523 GB to be served at an average 85.229 TB/s if read
once within that interval; local cache/ROM reads still exist even when HBM traffic
is removed. Shared service and serial phases can require higher active rates.

## Reproduction and scope

Run `python3 tools/audit_v41_dense_inventory.py` with the pinned local checkpoint
snapshot installed. The [tensor inventory](../results/architecture/v41_dense_inventory.json)
records all 1,253 classified tensors and hashes every shard header read. The audit
uses the repository's existing role classifier and independently sums checkpoint
header offsets to reconcile its bytes. It is not an independent proof of that
classifier's runtime semantics; the conditional-bias finding is recorded explicitly.

No hardware implementation or workload simulation is performed. This inventory
supports the primary [HBM-array versus ROM-array comparison](DEEPSEEK_V41_THREE_DESIGN_COMPARISON.md),
with one-/multi-wafer ROM remaining secondary.
