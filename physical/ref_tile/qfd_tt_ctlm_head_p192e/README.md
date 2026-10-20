# qfd_tt_ctlm_head_p192e (QW-SRAM3 10-19) -- structural redesign after qfd_tt_ctlm_head_p192 (p192a) gate FAIL

p192a FAIL (results/arch/qw_sram3_1019/head_p192a): trial GRT overflow 18365 over the whole abutted 308-um macro stack
(nets between W- and E-face pins cannot cross: M1-M4 obstructed, cap M5), spine pin-flop spread TT 124.9 / FF 135.7,
rst_n reached 8 flops unlanded. Std area only 3016 um2 (tile is macro/pin-limited; util waived).
QW-SRAM3 10-19: same RTL/params/pins as closed qfd_tt_ctlm_head; only the two 64x512 program SRAMs bind the <=5.21 pins/um successor ot_sram_1r1w_64x512_m1_r2c2_p192_mir (171.288x153.912, W/E 793 pins at 0.192 um; old master 10.2 pins/um). PARALLEL fallback: original p192_mir pin plan, macros separated by a 62-um crossing channel (y 43.2 / 259.2), 259.2x453.6, reset landing ON, TritonCTS.

Safe-design checklist: 1 pins registered in RTL at the face (io_flop_at_pins), reset_landing ON (fixed); 2 reach: gate lint;
3 fanout: unchanged RTL; 4 depth: unchanged (687 ps WARN stage is pre-existing head logic); 5 SRAM macros;
6 macros x=43.2 lattice, faces 5.21/um, aspect <=1.75, pin channels >=43 um; 7 clock per variant, TT/FF spread <=80 checked;
8 zero added data cycles (reset landing adds 2 reset-only stages).
p192e: QW-SRAM3 10-19: same RTL/params/pins as closed qfd_tt_ctlm_head; only the two 64x512 program SRAMs bind the <=5.21 pins/um successor ot_sram_1r1w_64x512_m1_r2c2_p192_mir (171.288x153.912, W/E 793 pins at 0.192 um; old master 10.2 pins/um). p192d FAIL only on TT pin-flop spread 84.6 (FF 72.3; GRT ovf 0): clock entered at the SW corner (S face 6-7.5 um), 713 um Manhattan to the far pin flops -> clk moved to the W-face centre (225-228 um, provisional die pin). Bit-sliced p192_bs master (no W<->E data crossing).
