HBM central hub detour: source-of-record S2 sensitivity, 2026-10-30

The old 11/12 cycle values describe DIFFERENT BUSES IN BOTH DIRECTIONS:
L4/L4m data2816b=11, L96/L96m control22b=12. Candidate L700 NE->NW2775b=16,
L701 NW->NE2730b=18. Thus data+5/+7, control+4/+6; data roundpair+12,
control roundpair+10. The naive directional+5/+6=11 premise is incorrect.
Old pair map retained in hh_original_pair_lanes.json. Candidate plan-only,
new pair per-bit packing still pending; this work does not adopt or bind it.

Exact native source families, from HBM bind lane:
NE->NW2775 = VM2170 hb_vms_SE.ccw_out + HCOL280ccw+280cw hcollb_NE outputs
 +obs32data+8index+1valid +4run_done bits. Reverse2730 = VM2170
hb_vms_SW.cw_out +HCOL280ccw+280cw hcollb_NW outputs. The large data path
maps to COLL records; status/observation must not be charged to every record.
VM traffic is not synonymous with ALL_GATHER: mirror broadcasts and request/
response paths can serve SM/HC/FUSED/IDX/SU/ATT/ARGMAX/DMA as well. The current
finite-phase compiler's relocated per-record bank/crossing map is not yet
qualified; legacy descriptor addresses cannot supply that missing authority.

Price uses the SAME accepted DT.NativeCost/T.schedule DS native S2 reference
as TOK-9: clean576702.4178 cycles, A+B606474.9312, referenceIDX31/SU3 price
~1799.8. Source tools are pinned by e49e61e1d worktree main ancestor. Gate
rejects a missing measured-record fallback through the clean baseline assert.
The dependency's historical F_SER0.9 constant is normalized through walltime
and1200cycles/us; it does not itself impose a physical serial clock. No clock
or timing constraint changes occur here.

Cases are explicit assumed ENCOUNTERS, not measured timing or a universal
whole-VM bound: per-COLL-record+5/+7 directional; +12serial data pair;
+7 or+12per_cross_phase (2forALL_REDUCE_SUM/GROUP_REDUCE_MCAST,1otherwise)
uses the existing TOK-9 phase model. +10controlpair is a SEPARATE sensitivity,
not added automatically on top of data. ALL_GATHER-only separates584records
from total642COLL (40group reduce,9topk merge,8row gather,1argmax merge).
The wide VM rows assume one serial samepair encounter per memory-unit record;
unknown multiple encounters, source concurrency, control publication dates
and finite capacities can change this charge. They do not prove every VM
record crosses the boundary or that all transactions fit one encounter.

All shown rates EXCLUDE native VM phase spill/DMA/drain overhead. Current
bounded source1458–1558 has689commands/6,250,560 added boundary bytes;
source1559–1590 adds6expert-inputLOADs/132,288bytes. Scratch/backend mapping
and whole-programme executable image are unqualified; those bytes cannot be
silently repeated, amortized, or integrated into a complete rate here.

Operations: local ot-run forwards to the intel2 scheduler; --hosts localhost
runs on actual intel2 tolerant-swine (scratch2), not coordinator. An initial
--hosts intel2 failed admission alias resolution NOT RUN. Two small staging
failures (missing top-level tool modules, then missing SU-chain records) were
diagnosed/restored from the exact pinned checkout; no existing job killed or
in-place failed result overwritten. Successful model job3823499.
