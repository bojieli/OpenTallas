module coupon(input clk,rst_n,input[31:0]din,input[119:0]wide,output[31:0]q,output[119:0]out);
(* keep = 1 *) reg a_lo30;
always @(posedge clk) a_lo30<=1'b0;
wire[31:0]v={din[31],a_lo30,din[29:0]};
ot_hdc_delay__su_startup_keep1030 #(.W(32),.D(4)) d_lo(clk,rst_n,v,q);
wire[119:0]cv={wide[119:72],q[30],wide[70:0]};
ot_hdc_w11_cut__su_startup_keep1030 #(.W(120),.CUT(1),.VB(118)) u_ca(clk,rst_n,cv,out);
endmodule
