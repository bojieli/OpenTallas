module tag_gate(input wire clk,input wire[3:0]code,input wire[255:0]sector,input wire[255:0]held,output wire[143:0]one,two);
 reg[255:0]s,h;always@(posedge clk)begin s<=sector;h<=held;end
`ifdef BASELINE
 reg[3:0]c;always@(posedge clk)c<=code;
 wire[7:0]offset=8'(144*c);
 wire[511:0]both={s,h};
 assign one=144'({256'd0,s}>>offset);assign two=144'(both>>offset);
`else
 wire[71:0]cc;
 for(genvar b=0;b<18;b=b+1)begin:g_c
  ot_hdc_v41x_kreg #(.W(4),.R(0))u(.clk(clk),.rst_n(1'b1),.d(code),.q(cc[4*b+:4]));
 end
 dsdv_svc_offset144_n32 u_one(.codes(cc),.banks({256'd0,s}),.word_out(one));
 dsdv_svc_offset144_n32 u_two(.codes(cc),.banks({s,h}),.word_out(two));
`endif
endmodule
