module land32_native(input ck,input [9:0] reset_leaf,input [511:0] data,output [8*512-1:0] reads,output [511:0] delay_q);
wire [2047:0] bank;wire [87:0] valid;
ot_qw_lw_n32 #(.W(512)) w(.ck(ck),.rsi(reset_leaf[0]),.i(data),.bank(bank),.vld(valid));
for(genvar k=0;k<8;k=k+1) begin:r
 ot_qw_lr_n32 #(.W(512)) rr(.ck(ck),.rsi(reset_leaf[k+1]),.bank(bank),.vld(valid),.o(reads[k*512+:512]));
end
ot_qw_ring_delay_n32 #(.W(512),.D(10)) d(.clk(ck),.rst_n(reset_leaf[9]),.d(data),.q(delay_q));
endmodule
