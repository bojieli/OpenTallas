# hnx_fused_hub_1019: FUSED hub (fus_hub slot, 432 x 432 reserve on the strip centre line)

LH-P3UNITS/FUSHUB 2026-10-19. RTL `rtl/hbm_next/fused/ot_hnx_fused_tree.sv`; design, hops per level, pads, CMTP costs and benches: `results/arch/hbm_next_1019/units/fushub/README.md`.

## SAFE-DESIGN checklist (owner 10-19), reviewed before the first gate

| # | Item | Result |
|---|---|---|
| 1 | Pins | PASS. Quadrant buses land in the hub nodes' pin flops, the job word in jq, wsc in wt. Outputs are flop Q: tnode kept da/db, done/fault/busy_q. busy is now registered (+1 edge). `reset_landing` 2 stages plus relay REGIONS 4. |
| 2 | Reach | PASS-pending gate. Logic sits between the W/E faces (345.6 um). The face -> node pin flops are at the face; the gate measures > 405-um stages. |
| 3 | Fanout | PASS. Reset uses 4 relay regions and each node has its own relay. The heap leaf hit decode drives 20 leaves (32 b each). |
| 4 | Depth | PASS-pending gate. The heap and tail are `ot_hnx_fused_top`'s closed-form cores. scb rd goes to one 2:1 half-select into a pipe register. |
| 5 | Storage | **FIXED**: scb (12.3 kb flop array) moved to a 1R1W 128x256 SRAM. The 3 node pads are SRAM rings. |
| 6 | Floorplan | 4 x 128x256 + 3 x 32x64 on the 43.2 lattice, with channels >= 34.8 um, >= 43.2 um from the W pin face and 69 um from N. Aspect 1, one std band. The outline is estimated (~35k std + 17.2k macros, util ~0.45); the gate's synthesis area re-sizes it. |
| 7 | Clock | One centre-fed root (~8k flops). io_hold_margin 0.03. The gate measures spread <= 80. |
| 8 | Static schedule | PASS. No credits or backpressure. The +1 command pipe, WSC 115 and the busy edge are handed to CMTP. |
