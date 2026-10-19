# hnx_fused_tnode_1019: FUSED csum tree node (x28 on die f4c_t9p3, one view, straps tied by the die binder)

LH-P3UNITS/FUSHUB 2026-10-19. RTL `rtl/hbm_next/fused/ot_hnx_fused_tree.sv`; design, hops per level, pads, CMTP costs and benches: `results/arch/hbm_next_1019/units/fushub/README.md`.

## SAFE-DESIGN checklist (owner 10-19), reviewed before the first gate

| # | Item | Result |
|---|---|---|
| 1 | Pins registered, 2-stage reset landing | PASS. Every input lands in a pin flop: iac/iad/ibc/ibd, idv/idd, and the straps in pk_q/pb_q. Every output is a flop Q. `reset_landing` uses 2 stages plus `ot_rst_relay` REGIONS 4. |
| 2 | Reach <= 405 um a cycle | PASS. The tile is 172.8 sq, so every path is < 250 um. Die links are relay stations at 405 um, with landings between regions. |
| 3 | Fanout <= ~32 / kept copies | PASS. The down bus has one kept copy per child (`keep`). The strap selects are registered once, and the gate measures their fanout. Reset uses 4 relay regions. |
| 4 | Depth <= 600 ps | PASS-pending gate. SRAM rd -> select ends at the aligned-pair register. The add is the closed f12 l6 core. |
| 5 | Storage > 2 kb in SRAM | PASS. The 8.7 kb pad is in 128x256 + 32x64 1R1W macros. There are no flop delay lines >= 3 deep: the pad is the ring, and the add valid is a 6-bit vline. |
| 6 | Floorplan | Macros on the 43.2 lattice, >= 25.9 um from the pin faces, 45 um channel, one std band. Aspect 1. Utilisation is WAIVED: the tile is pin-limited, with 1,350 pins at 2.6/um per face, so the outline is set by the faces. |
| 7 | Clock | One small centre-fed root (~3k flops). io_hold_margin 0.03. The gate measures spread <= 80. |
| 8 | Static schedule | PASS. Pads and WSC are derived statically. Every added edge is listed above for CMTP. |
