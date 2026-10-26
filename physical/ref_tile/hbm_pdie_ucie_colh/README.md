
## UCIE6 SAFE review (HBM-OWN/PHY 10-21 12:25) -- successor of ucie5f route NEEDS_RTL TT-341.65/FF+27.19/DRC0
MAIN colh: outline 259.2x1555.2 (-216 um vs colf), SRAM u_rmm at (43.2,1382.4) = 43.2 um channel above the PMA tops; tx face regs -> PMA d pins 216 um.
Causes (route hbm_pdie_ucie_colf-ucie5f-b5f0313fd): PMA_TX484 output buffer GPL-placed at (3.24,4.05) vs port (249.04,0.04), final wire 517.69 ps;
208/513 tx drivers >100 um from their ports; u_rm m_waddr->push->u_rmm/w_ce_in -17.99; u_rm wp_g2->empty->rp -14.21; u_txf->u_ptx/d -6.98.
1 pins PASS: every core pin registered in RTL (u_txf, 2-stage u_lpo_rx/st, landed resets); PMA pads registered in the hard abstracts; unchanged.
2 reach PASS/FIX tx face->PMA d 216 um (colf 432 um > 405); pma_tx drivers placed on port->pin segment (<= ~100 um, was 250.8).
3 fanout PASS: rate matcher flags add 3 flops; empty_r <= ~22 loads (16 sel copies + rp mux + r_ce); census in the gate (max 32).
4 depth FIX: FIFO flags registered (ot_ucie_rate_match_pf): push = AND-OR of 4 flops -> w_ce_in; rp D = 2:1 mux; flag D = 4-bit compare.
5 storage PASS: dual-clock SRAM rate matcher + PMA abstracts unchanged.
6 floorplan FIX outline shrunk to the content (no squeeze: std area ~0.8k um2 vs 140k placeable; 43.2 um channels at PMA tops, SRAM side channels 43/39 um), PMA off-lattice/aspect inherited owner exception, fits colf/cold die slot.
7 clock PASS: same 3 regional roots ck_tx/ck_rx/ck_rck, no new phase; CDC = 2-stage gray syncs (1st stages feed only 2nd stages).
8 schedule PRICED: +1 cycle RX elastic latency (pointer visibility 3 stages) at the off-die UCIe boundary (elastic, flow control
  kept at off-die boundaries); no on-die scheduled edge, no port/width change. Pin-driver repair: placement only, no netlist edit.
PDN: inherited validated macro_m5 grid for the M5-PG PMA abstracts (as colf; the generator still treats every macro as an M4-PG SRAM -> PDN-0233 in the 12:20 gate).
