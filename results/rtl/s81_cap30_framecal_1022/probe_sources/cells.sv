module dsfd_rly_1_WN(input ck,rs,i,output o); ot_s81_rly #(.W(1)) u(.ck(ck),.rs(rs),.i(i),.o(o)); endmodule
module ICGx4_ASAP7_75t_R(input CLK,ENA,SE,output GCLK); reg en_l; /* verilator lint_off COMBDLY */ always_latch if(!CLK) en_l=ENA|SE; /* verilator lint_on COMBDLY */ assign GCLK=CLK&en_l; endmodule
