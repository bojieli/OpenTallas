// ASAP7 standard cells used by the S81-DV bound die top (library function models)
module BUFx8_ASAP7_75t_R (input A, output Y); assign Y = A; endmodule
module INVx2_ASAP7_75t_R (input A, output Y); assign Y = ~A; endmodule
module ICGx4_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK); reg en_l; /* verilator lint_off COMBDLY */ always_latch if (!CLK) en_l = ENA | SE; /* verilator lint_on COMBDLY */ assign GCLK = CLK & en_l; endmodule
