module native_bank_synth(input wire clk,d,output wire q3,q5);
ot_dp_landing_bank #(.D(3)) bank3(.clk(clk),.d(d),.q(q3));
ot_dp_landing_bank #(.D(5)) bank5(.clk(clk),.d(d),.q(q5));
endmodule
