# NDR usage accounting candidate, not an E5 trigger claim

Observed E5 GRT-0229: vertical edge(654,528) usage65356 limit2600,2002 clock nets, before any reported congestion iteration. Source revision OpenROAD6cb3f2b704/image26Q3-1510-g6cb3f2b704. GRT remains FAIL. No production image/netlist modification, router rebuild or PNR run was done.

Exact Graph2D method bodies and Edge type were extracted from the pinned source; one-edge/one-layer arrays and FrNet stand-ins provide the minimum test harness. Methods getCostNDRAware,hasNDRCapacity,updateNDRCapLayer,updateEstUsageV,addEstUsageToUsage are unchanged. Actual image GCC11.4 compiles this small harness. Unit oth-ubuntu-2660457-1792974565 EXIT0; both plain and sanitizer controls completed as expected.

Results:
- Uniform NDR edgeCost4, background16: additions+4/+400, removal-400 leaves20. A negative removal cost alone does not imply negative usage.
- Heterogeneous A cost4/B cost2, capacity4, background16: addA+4 (unpenalized), addB+200 (penalized), removeA-400 because the global overflow count is1. Signed estimated balance becomes-180; unchanged native conversion stores65356 under the tested GCC11.4 build. The global overflow count does not identify which net was originally penalized or its weight.
- Removing B first, then A, balances16 safely. This demonstrates order dependence for the heterogeneous case.
- A positive65356 test quantity also stores65356. The actual E5 number alone cannot distinguish these cases or prove an actual unsigned-wrap event.
- -fsanitize=float-cast-overflow rejects the exact negative-double-to-uint16 conversion. C++ does not guarantee modulo behavior for an out-of-range floating conversion; the tested compiler behavior is not a portable language guarantee.

No actual E5 FrNet cost distribution or operation trace was collected. If all actual NDR nets have the same effective cost and state starts coherent, this specific heterogeneous-weight candidate does not explain E5; investigate state resets, mixed estimated/actual accounting, or other operation streams next. NDR usage includes100x overflow penalties, so it is also not a direct count of physical tracks. Enabling M6/M7 may avoid the capacity penalty without proving which mechanism caused the old failure. Do not clamp negative values or waive the error.

Primary sources: [Graph2D source](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/grt/src/fastroute/src/graph2d.cpp), [Edge type](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/grt/src/fastroute/include/DataType.h), [initial route order](https://github.com/The-OpenROAD-Project/OpenROAD/blob/6cb3f2b704/src/grt/src/fastroute/src/FastRoute.cpp). Source headers retain BSD3 attribution.
