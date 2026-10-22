# GQ R14 MUL8 structural successor
Actual predecessor k14q native FAIL: one operand FF QN drove 33 pins in a constant 0x25 multiply. k14r WR2 fallback passed native32 and remains progressing.

SAFE review before gate: 1 unchanged registered boundaries/reset landing; 2 unchanged 475.2x561.6 floorplan/reach; 3 changed to kept per-byte stage1 operands, 24 copies plus top decision at source (25 planned), each eight-bit output product pruned separately; actual mapped native census must pass <=32 before floorplan; 4 original exact 32-bit constant product and stage2 register, byte extraction does not change carries; 5 +432 unreset datapath FF per aq scale (no new indexed storage); 6 unchanged outline, no squeezing, synthesis measures utilization; 7 unchanged clock roots K24 MAIN/K32 WR2 fallback and existing landing interfaces, measured CTS decides; 8 zero added port cycles, same static schedule. Default off OT_GQ_MUL8; no adoption until exact bench and physical closure.

QA2 actual successor: sole33-load row-OR after MUL8 -> two kept same-row reads, four QA adders each, existing cur_ohc[1] aligned (planned26loads), RFbit+1load, no state/latency. SAFE1/2/4-8 unchanged, SAFE3 actual native required; both original nativefailures retained.

QA2 selector repair: predecessor k14w/k14x failed at sixteen cur_ohc[1] roots with 41 native loads. The second QA read now uses existing same-edge calendar copy 3 for seven bits and copy 0 for six. Predecessor mapped loads 22 and 24 imply 29 and 30; actual mapped census remains authoritative. No added state, edges, ports, clock exceptions, or timing changes. MAIN and fallback preserve their respective outlines and read residence.

QA2 selector repair distributes thirteen reads across existing same-edge selector copies: seven on copy 3, six on copy 0. Predecessor measured loads 22/24; expected 29/30, subject to actual mapped census. No added state or latency.
