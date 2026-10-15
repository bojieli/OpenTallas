module probe(input ca, cb, en, output [545:0] qa,qb);
ot_sram_1r1w_32x546_m1 u_0(.clk(ca),.r_ce_in(en),.rd_out(qa));
ot_sram_1r1w_32x546_m1 u_1(.clk(cb),.r_ce_in(en),.rd_out(qb));
endmodule
