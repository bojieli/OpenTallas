module parent(input wire clk,rst_n,output wire[63:0]q);
 for(genvar i=0;i<8;i++)begin:g
`ifdef EXPLICIT_DEFAULTS
 ot_s81c_attn_hcore #(.BZ0(1),.WPRE(2),.WSEG(0)) u(.clk(clk),.rst_n(rst_n),.i(8'(i)),.q(q[8*i+:8]));
`else
 ot_s81c_attn_hcore u(.clk(clk),.rst_n(rst_n),.i(8'(i)),.q(q[8*i+:8]));
`endif
 end
endmodule
