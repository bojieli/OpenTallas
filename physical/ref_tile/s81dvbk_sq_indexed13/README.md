# INDEXED13 selector quarter qualification

Isolated candidate master dsdv_bksel_q, opt-in OT_S81PH_SEL_INDEXED13. The original s81dvbk_sq kit stays unchanged. Candidate shape302.4x388.8um, aspect1.29; two quarters use604.8um of the existing680um column. Six existing SRAMs remain: x43.2/172.8; y43.2/129.6/216.0um; macro94.824x41.064. Channels34.776um horizontal /45.336um vertical. Full-width std-cell band above y257.064um. North pins spread over298.08um; max group t_s density865/144.36=5.992pins/um. Clock at N x146.52..150.84 beside the register band. Output t_o spans the W face.

Safe-design pre-gate review:
1. PASS: lane captured at input, commands captured (QIO1); t_s/t_o flops; explicit kit reset_landing2.
2. PASS topology: tile axes302.4/388.8um fit405um planning budget; no long external link added. Physical path reach to be checked in placement.
3. FIXED: 27 KEPT format-select copies; each score/index copy drives <=16/20 tuple mux bits, metadata copy14bits. Pin type bits feed27predecode copies plus their ordinary capture. Gate synthesis must verify kept copies survived.
4. PASS RTL structure: one 4-bit type decode into capture; then 2:1 local tuple mux and native registered pipeline. No input-output combinational path or resource arbitration; no new pipeline cycle.
5. PASS: six original SRAMs, no new array/queue/delay line. Extra capture+format bits236/quarter (<2kb). STG0 in the real quarter.
6. FIXED geometry: 43.2lattice, one full-width band, full-face pins <=6/um and generous macro channels, aspect1.29. Provisional footprint117,573um2 closely matches old121,306um2 with only236 extra capture bits. Gate synthesis area must establish 40-60% fill or a concrete perimeter-bound allowance before submission; no route authorized on an unresolved geometry/fill failure.
7. PASS provisions: clock N centre at register band, regional quarter root, unchanged neighboring control interface, io_hold_margin0.03. TT/FF pin-flop spread <=80ps remains a measured gate/adoption obligation.
8. PASS: static 324-beat input; unchanged640-tail budget and74-beat drain; safe reserved1037cycles. Compiler `--bk-indexed13` is OFF by default. Conditional token-path costs AR0.822% /MTP0.939% above178price.

Production benchmark and negative witnesses: results/arch/s81_topk_final_1019. Full2048candidates, masked13th tuple tail, repeated ties, signed zero, infinity/ninf, wrong score/index and early drain. Runtime TP4 score/index producer, IDX-to-gather consumer and downstream schedule propagation remain explicit integration GAPs; no live die path is claimed. No default/claim flip before gate, physical closure and producer integration.
