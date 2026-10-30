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

Measured tool results (conditional reference model):
Clean 576702.417847; record 610734.931155 cycles / 1799.790306 tok/s.
COLL_ne_to_nw_data5_once: 1791.678780 tok/s, +2765.0cycles, lossvsrecord0.450693%, loss vs1812.4 1.143303%.
COLL_nw_to_ne_data7_once: 1788.454606 tok/s, +3871.0cycles, lossvsrecord0.629834%, loss vs1812.4 1.321198%.
COLL_pair_data12_once: 1780.444710 tok/s, +6636.0cycles, lossvsrecord1.074881%, loss vs1812.4 1.763148%.
COLL_data7_per_cross_phase: 1787.640199 tok/s, +4151.0cycles, lossvsrecord0.675085%, loss vs1812.4 1.366133%.
COLL_pair_data12_per_cross_phase: 1779.061507 tok/s, +7116.0cycles, lossvsrecord1.151734%, loss vs1812.4 1.839467%.
COLL_pair_control10_once: 1783.640043 tok/s, +5530.0cycles, lossvsrecord0.897341%, loss vs1812.4 1.586844%.
COLL_AG_only_pair12: 1782.454179 tok/s, +5940.0cycles, lossvsrecord0.963230%, loss vs1812.4 1.652274%.
wide_all_VM_units_pair12_once: 1730.168260 tok/s, +24576.0cycles, lossvsrecord3.868342%, loss vs1812.4 4.537174%.
wide_nonCOLL_VM_pair12_plus_COLL_pair12_perphase: 1728.862043 tok/s, +25056.0cycles, lossvsrecord3.940918%, loss vs1812.4 4.609245%.

Wide assumed-one-encounter row1728.862 is4.609% below1812.4, only7.082tok/s above5%floor1721.78 BEFORE unpriced spill/drains. Separate unintegrated arithmetic IF all6382848bytes occur once serially: +2015.636cycles at die BW =>1723.398tok/s; at single-stack BW +8062.545 =>1707.213. This is not authority for repeat counts, overlap, mapping, fences or a whole-token rate.

Tnode-only source service sensitivity, source39624526a:
Four external physical tnode levels each input+1/output+1 give down+8/up+8,
RT/WSC+16. Same row pace implies HC_POST+32 and HC_PRE+48 per native command.
All161selectedS2HC records are primitive records with no appended ROWX;
full codec consumption and exact reencoding were asserted. Emitter authority
setsN=rx.n if ROWX present, else1. Tensor dimension5120 is NOT rowcount5.
81PRE/N1+80POST/N1 change;40QDQ records unchanged. Source81*48+80*32=6448
addedcommandcycles; S2 overlap absorbs118.552;
nettoken+6329.448cycles =>1781.329219tok/s,
lossvs1799.790reference1.025735% andvs1812.4
1.714345%. No hubdetour cost included in this row.
No multiuserROWX grouping inferred. N>4 chosenRGap+4 would givePRE5+64/
PRE6+68, but the true minimum increase is derived from current bound and
can be0..3 when previous ceiling was clipped at0; not priced bythisN1row.
Spill/DMA/drains remain excluded; no physical or G5 adoption claim.

04:12 owner refinement (candidate hh_coherent2, G0C/strict bind pending):
New16/18detour serves SOUTHERN whole words only. Northern VMS/prHCOL old
L4/L4m paths retain11cycles; old width2816->2784 removes32Southern bits.
NewL7002807/L7012762 include2202SouthernVMSbits+560HCOLb (NEalso45obs).
Existing22controlbits onL96/L96m are group-padded+4/+6,220FF total; full
SouthernVMS word2224=2202+22. The retained initialnative bit snapshot in
this packet predates that coherent refinement and is immutable history.
No scalar price needs recomputation: assumedencounters+5/+7 are unchanged.
But the price cases charging allCOLL/allVM records are over-exposure
sensitivities, not proof that unchanged Northern traffic acquires a delay.
Exact Southern per-record crossing identity still needs bound current
source/compiler mapping. No adoption or combined full-token rate follows.
