# K-tree R9 safe32 closure successor

Source: claude/kv-params4-qkh-1020 95c10fdb9f55421b6d9416a4238ad0e5bee6882f. No arithmetic or schedule change in the takeover.

Coordinator 10-20 03:30 explicitly accepts the single 34-load combinational node inside each of the 15 library safe adders, at most 36 loads per node; timing decides at the gate. The 32-load rule remains binding for all new logic. This authority does not cover reset, input ports, sequential drivers, multipliers, other tiles, or any additional nodes. Exact node and source identities are in results/rtl/kv_qkh_gate_takeover_1020/KTREE_WAIVER_PACKET.json. Raw failed native-census evidence is preserved; it must never be changed to claim an unconditional max32 PASS.

Safe-design checklist before the successor gate:

1. Pins PASS: existing core input and output registers retained. Generic wrapper disabled to preserve compiled K ages. Reset input lands through rst_l0/rst_l1, then bounded32 farm.
2. Reach PASS planning: outline172.8x129.6um, diagonal216um<405um; final routed native reach audit is mandatory before integration.
3. Fanout WAIVED ONLY AS ABOVE: in-gate mapped max34 on exact15 known adder decode nodes, zero role errors. Every other root<=32. Global audit remains unchanged.
4. Depth: R9 arithmetic benchmark and mutants PASS/expectedFAIL on pinned Verilator5.050; timing must be measured in the new gate.
5. Storage PASS: arithmetic pipeline only; no new indexed storage or long delay line.
6. Floorplan PASS planning: zero macros, one contiguous cell area, aspect1.33, outline on43.2 lattice, source synthesis~10.9kum2 (~49% of rectangle), full N/S data faces, W clock/reset.
7. Clock PASS planning: compact216um diagonal, W input root, no hard-child clocks; measured TT/FF pin-flop spread<=80ps still required. Route io_hold_margin0.03/HM0.03.
8. Schedule PASS: same ports and compiled ages, zero token cycles added. Bounded reset release is explicit; source KPV lockstep fault checking retained.

Original native failure was admission before floorplan, not a failed route. Launch requires ROOT scoped waiver transport and provenance verification; there is no local bypass.
