// DIE-HBM-61/SPLIT bench-only behavioural models of the two ASAP7 cells the kit RTL instantiates under SYNTHESIS
// (ot_hdly hold-delay buffer = wire in function; ot_hdc_cg ICG = latch-based clock gate).
module HB4xp67_ASAP7_75t_R (input wire A, output wire Y); assign Y = A; endmodule
module ICGx1_ASAP7_75t_R (input wire CLK, input wire ENA, input wire SE, output wire GCLK);
    reg en_l; always @(CLK or ENA or SE) if (!CLK) en_l = ENA | SE; assign GCLK = CLK & en_l;
endmodule
