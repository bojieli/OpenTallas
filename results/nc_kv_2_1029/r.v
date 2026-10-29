module r(clk, d, q);
input clk; input d; output q;
DFFHQNx1_ASAP7_75t_R u (.CLK(clk), .D(d), .QN(q));
endmodule
