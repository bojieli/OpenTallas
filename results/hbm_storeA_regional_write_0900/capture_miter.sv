module capture_miter(input clk,ctl_reset_n,meta_reset_n,input[2055:0] rr_D,input[175:0] meta_D,output mismatch);
reg[2055:0] m23_q;reg[175:0] meta88_q;
always@(posedge clk or negedge ctl_reset_n)if(!ctl_reset_n)m23_q<=0;else m23_q<=rr_D;
always@(posedge clk or negedge meta_reset_n)if(!meta_reset_n)meta88_q<=0;else meta88_q<=meta_D;
wire[8191:0] data;wire[479:0]addr;wire[63:0]groups;wire[31:0]v;
wire[2047:0]packed_rr;wire[151:0]packed_meta;
for(genvar b=0;b<8;b=b+1)assign packed_rr[256*b+:256]=rr_D[257*b+:256];
for(genvar g=0;g<4;g=g+1)assign packed_meta[38*g+:38]=meta_D[44*g+6+:38];
ot_hgi_sfu_store_a_regional_capture gate(clk,ctl_reset_n,meta_reset_n,packed_rr,packed_meta,data,addr,groups,v);
wire[3:0] differs;
for(genvar r=0;r<4;r=r+1)begin:g
 wire[7:0]dv;wire[3:0]mv;
 for(genvar b=0;b<8;b=b+1)begin assign dv[b]=data[2048*r+256*b+:256]!=m23_q[257*b+:256];end
 for(genvar g=0;g<4;g=g+1)begin
  assign mv[g]=addr[120*r+30*g+:30]!=meta88_q[44*g+8+:30] || groups[16*r+4*g+:4]!=meta88_q[44*g+38+:4] || v[8*r+2*g+:2]!=(meta88_q[44*g+42+:2]&~meta88_q[44*g+6+:2]);
 end
 assign differs[r]=|dv|| |mv;
end
// Observe after one actual edge, without assuming equal initial DUT states.
reg observed=0;always@(posedge clk)observed<=1;
assign mismatch=observed&&|differs;
endmodule
