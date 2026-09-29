# Candidate spill relocation: destination capacity not established

The root-selected first remedy was to move at least 28,062 Engram rows out of
candidate stage17/rank0 while preserving expert boundaries and representations.
`tools/v41_floorplan_spill_relocation.py` now audits all 28 layer stages and all
112 rank-specific spill allocations from actual checkpoint headers. All
46,080 routed-expert matrix headers and scale shapes are checked. Every dense
source tensor belongs to exactly one conservative reservation; uncertain
partitions remain fully replicated rather than creating unproved spare space.

**No destination has proven free capacity.** The conservative payload audit
reports 2,234,824,496 bytes of total excess across the layer dies and zero
positive headroom. Stage17/rank0 still exceeds by 7,408,140 bytes, matching the
focused complete reservation. Several common dense stages exceed by about
2.708 MB; larger unresolved dense/Engram projection stages exceed more.

This does not prove the architecture globally infeasible: some conservative
replication may be replaceable by verified partitions. It does reject the
proposed relocation under the current proved bindings. The dedicated table
dies were filled to whole-row capacity. Head spill capacity still comes from
the analytical head model; no exact complete head image proves another
receiver. No row move or new ownership lookup has been approved or emitted.

## Two-expert alternative

Moving two whole experts frees exactly **9,400,320 rank-local bytes**, enough
to repair stage17 itself. Adjacent stage16 is already over by **20,976,932
bytes/rank**, and stage18 by **15,242,532 bytes/rank** under the audit. Adding
the two experts would increase those deficits to **30,377,252** or
**24,642,852 bytes/rank**, respectively. The minimum relay payload is the same
activation/return contract already required for a split expert stage; actual
added critical-path delay cannot be priced without selected-expert traffic,
endpoint placement and link service. Moving experts alone is not a proven
global solution.

## Required next decisions

1. Verify uncertain dense partitions against executable program ownership,
   replacing conservative replication only with numerical and port evidence.
2. Evaluate compact wo_a storage with local BF16 dequantization: this recovers
   8,126,464 bytes for one dense layer at rank shape, but requires decoder
   exactness and delivered-bandwidth budget.
3. Derive a complete head-die tensor reservation before considering it a spill
   destination.
4. Re-run capacity and then minimize actual gather path delay among feasible
   receivers. Stage-number distance alone is not a critical-path proof.

The audit changes no RTL, ownership or capacity. It intentionally refuses to
invent a destination or silently increase logical ROM capacity.

## Program-declared partition refinement

The source-pinned emitter declares `engram.wkv` output quarters and indexer
`weights_proj` output quarters. Applying those shapes reduces the conservative
layer-die total excess from 2,234,824,496 to **1,253,750,576 bytes**. There is
still no positive per-die headroom under the equal-row spill proposal. This
refinement is recorded separately in `v41_spill_resolved_dense.json`; it does
not silently overwrite the earlier conservative observation.

The HC projections are correctly replicated. Indexer wq_b and wk are also
replicated. Compressor wkv/wgate remain conservatively replicated: although
the emitter allocates a smaller cwkv shape, complete collective/reduction and
consumer semantics across full compressor layers have not been demonstrated.
No memory credit is taken just because an address allocation is smaller.

As a **non-adopted sensitivity**, compact wo_a with row-local scales yields
718,324 bytes spare at stage17/rank0; across layer dies it gives 231,980,096
positive bytes and 185,496,432 bytes of deficits elsewhere. The aggregate
surplus does not itself prove a legal redistribution: physical banks, source
formats, gather destinations and actual link latency still need binding.
Root must approve the decoder timing and ME alignment before using this
representation for either capacity acceptance or rates.
