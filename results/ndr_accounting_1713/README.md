# NDR usage accounting candidate, not an E5 trigger claim

Observed E5 GRT-0229: vertical edge(654,528) usage65356 limit2600,2002 clock nets, before any reported congestion iteration. Source revision OpenROAD6cb3f2b704/image26Q3-1510-g6cb3f2b704. GRT remains FAIL. No production image/netlist modification, router rebuild or PNR run was done.

Exact Graph2D method bodies and Edge type were extracted from the pinned source; one-edge/one-layer arrays and FrNet stand-ins provide the minimum test harness. Methods getCostNDRAware,hasNDRCapacity,updateNDRCapLayer,updateEstUsageV,addEstUsageToUsage are unchanged. Actual image GCC11.4 compiles this small harness. Initial synthetic4/2 proof unit oth-ubuntu-2660457-1792974565 EXIT0 retained. Actual-rule-cost3/5 successor unit oth-ubuntu-2849745-1792974825 EXIT0; both plain and sanitizer controls completed as expected.

Actual NDR rule costs were derived from pinned GlobalRouter::computeTrackConsumption, CLOCK immutable-ODB inventory, and image-native tech widths. It uses ndr_pitch=(ndr_width+2*ndr_spacing+default_width)/2 with integer division, then consumption=2*ceil(float(ndr_pitch)/track_pitch)-1. CTS_NDR_0 has cost3 and ot_dtsh_4w2s cost5 on every eligible M2-M5 layer. Their actual net counts are284 and297, so a heterogeneous NDR population exists. DEFAULT91496 is cost1 and bypasses NDR penalty management. Per-layer arithmetic is in actual_rule_costs.json; formula source in pinned_track_consumption.txt. The function fetches per-net range but its rule filtering uses the global routing range. No actual event order/edge membership was captured.

Native-cost results:
- Uniform NDR edgeCost5, capacity5, background15: additions+5/+500, removal-500 leaves20. A negative removal cost alone does not imply negative usage.
- Heterogeneous A cost5/B cost3, capacity5, background15: addA+5 unpenalized; addB+300 penalized; removeA-500 because global overflow count is1. Signed balance becomes-180; unchanged native conversion stores65356 under tested GCC11.4. The global count does not identify which net was penalized or its weight.
- Reverse removal returns15 safely. A positive65356 quantity also stores65356, so the observed E5 value is still ambiguous.
- UBSan rejects exact negative-double-to-uint16 conversion. C++ does not guarantee modulo behavior for out-of-range floating conversion.

This is a concrete source-reachable synthetic candidate with actual cost classes, not proof of the E5 event. Capacity5/background15 and the order are controlled model inputs, not measured edge state. NDR usage includes100x overflow penalties, not just physical tracks. M6/M7 avoiding the symptom would not establish which mechanism caused the old failure. Do not clamp or waive errors.

trace_candidate.patch is an OPTIONAL diagnostic-only patch against pinned graph2d.cpp, never applied/built/run on a router here. It logs targetedV654,528 and suspicious signed updates with netID/name,cost,request/delta,usage/estimated state,overflow count and membership, plus pre-conversion bad range. No clamping/accounting repair. TRACE_NEXT.md lists the complete desired census and notes extra phase/layer tracing as needed.

A minimal hypothetical repair model stores each net's charged weight and subtracts the identical weight on removal; global overflow count can guide additions, but cannot reprice an already credited net. ledger_control.py proves both removal orders conserve the additive charge and returnbackground15. This is not an OpenROAD logic patch or full fix; per-layer allocation/restoration also needs attribution and actual-trace validation.

Primary sources: [Graph2D source](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/grt/src/fastroute/src/graph2d.cpp), [Edge type](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/grt/src/fastroute/include/DataType.h), [initial route order](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/grt/src/fastroute/src/FastRoute.cpp). Source headers retain BSD3 attribution.
