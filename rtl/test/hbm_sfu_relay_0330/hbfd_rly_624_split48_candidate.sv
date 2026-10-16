`default_nettype none
// Additive candidate only. Thirteen actual 48-bit masters carry every payload
// bit exactly once. Explicit reset tree preserves the 624-bit release latency;
// its thirteen region outputs still require physical placement/qualification.
module hbfd_rly_624_split48_candidate #(parameter integer MUT=0)(
 input wire ck,rs,input wire [623:0] i,output wire [623:0] o);
 wire [12:0] rn;
 ot_rst_relay #(.REGIONS(13),.SYNC_STAGES(2),.TREE_STAGES(1)) reset_tree
   (.clk(ck),.rst_n_in(rs),.rst_n(rn));
 wire[623:0] q;
 for(genvar k=0;k<13;k=k+1)begin:g
  localparam integer SRC=(MUT==2)?(12-k):k;
  hbfd_rly_48_EW lane(.ck(ck),.rs((MUT==3)?rs:rn[k]),
   .i(i[SRC*48+:48]),.o(q[k*48+:48]));
 end
 generate if(MUT==1)begin:extra
  hbfd_rly_624_EW late(.ck(ck),.rs(rs),.i(q),.o(o));
 end else assign o=q;endgenerate
endmodule
`default_nettype wire
