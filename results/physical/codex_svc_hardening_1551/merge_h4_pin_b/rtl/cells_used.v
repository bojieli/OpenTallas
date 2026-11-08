// ASAP7 standard cells used by the S81-DV bound die top (functional models of library cells, not stand-ins)
module BUFx8_ASAP7_75t_R (input A, output Y); assign Y = A; endmodule
module INVx2_ASAP7_75t_R (input A, output Y); assign Y = ~A; endmodule
module ICGx4_ASAP7_75t_R (input CLK, input ENA, input SE, output GCLK);   // latch transparent while CLK is low, ANDed with CLK
    reg en_l;
    /* verilator lint_off COMBDLY */
    always_latch if (!CLK) en_l = ENA | SE;
    /* verilator lint_on COMBDLY */
    assign GCLK = CLK & en_l;
endmodule
