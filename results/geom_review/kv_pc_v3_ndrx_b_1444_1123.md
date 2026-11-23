# KV pc_v3 D27d3 clock escape diagnostic review

2026-11-23 14:44 PST, FLOW-CLKGRT-R2. **BAD, hold diagnostic replay on this form.**

I viewed the exact layout, placement density and routed congestion renders for E10 kit `kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D27d3/private/FAM-KV-IOPC-R4/kv3_pc_v3_1122043653/gen/kv3_pc_v3` under `run/layout_review/{place,grt}`. The placed ODB SHA starts `8763515fdea8` and matches the inherited NDRX B place database byte for byte. The placement density plot shows loaded vertical gaps beside the outer PCF rectangles and a narrow central path where the four PCC faces funnel toward the four SRAMs. The GRT view marks congestion by those inner faces and the lower-east macro turns. Peak local density 0.929 and inherited signal overflow 17,932 align with the loaded channels.

Inherited phase 1 has 140 overflow and drops four clock tap NDRs before any signal routes. Those tap-escape capacity issues and the signal corridors each need a physical remedy. The NDRX B terminal at `flow-clkgrt-1121/ndrx/B/run_b.out` widened the candidate M7 slots at 38 taps, then make failed because the nonport hook requires `OT_VCLK_CORNER=ff` and make `CORNER=BC`. No arm B clock routing result exists. Carry the FF invocation requirement into a visually eligible successor and retain the existing phase-1 capture.
