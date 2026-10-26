# Next actual diagnostic (not launched here)

Instrument the pinned mutators for the selected failed vertical edge654,528 and the first signed-range violation. Record an initial edge/net census before routing and the operation stream through initial L/RSMT/L/spiral/Z routing into convertToMazeroute. Keep existing failing exit behavior.

For every updateEstUsageV/updateUsageV and addEstUsageToUsage event, record: phase/callsite+ordinal, net ID/name, NDR rule, edge H/V,x,y, FrNet edgeCost, requested amount, returned getCostNDRAware delta, uint16 usage before/after, est_usage before/after, signed total before conversion, ndr_overflow before/after, net-present before/after and NDR-net-set size. Also record per-layer getLayerEdgeCost,cap,cap_ndr before/after to tell equal rule names from equal effective costs and identify capacity allocation/restoration.

The decisive event is a signed total outside0..65535 BEFORE conversion, or an actual positive total that explains the diagnostic. A negative returned delta alone is insufficient. Include uniform-cost and reverse-removal controls in any proposed fix. If the heterogeneous bug is actual, a correctness fix needs per-net/edge charged weight (and capacity-layer attribution), not merely a global overflow count. Do not clamp; that would hide inconsistent accounting. No production patch or complete fix is claimed by this synthetic receipt.
