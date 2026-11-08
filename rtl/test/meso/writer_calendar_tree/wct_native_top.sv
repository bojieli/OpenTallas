module wct_native_top #(parameter W=514,WNEG=1,SEED=5)(input wire tclk,rclk,rst_n,input wire [575:0]d,output wire same,ready,ctrlsame);
wire[W-1:0]a,b;wire ar,br,af,bf;
ot_dp_clk_landing #(.W(W),.SETTLE(8),.WNEG(WNEG)) gold(.fclk(tclk),.clk(rclk),.rst_n(rst_n),.d(d[W-1:0]),.q(a),.ready(ar),.fault(af));
ot_dp_clk_landing #(.W(W),.SETTLE(8),.WNEG(WNEG),.WTREE(1)) cand(.fclk(tclk),.clk(rclk),.rst_n(rst_n),.d(d[W-1:0]),.q(b),.ready(br),.fault(bf));
initial begin gold.u_ring.tc=SEED;cand.u_ring.tc=SEED;end
assign same=(a==b);assign ready=ar;assign ctrlsame=({ar,af}=={br,bf});
endmodule
