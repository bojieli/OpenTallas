`timescale 1ns/1ps
// TU 545b receive boundary -> owner 537b boundary. Destination validated
// BEFORE stripping; ordinal16 is sliced only from the actual hub record.
// Default CUTS=0 forwards the pinned original runtime. All identity checks retained.
// No credits, publication or lease authority is introduced here.
module ot_ha2_tu_owner_adapter_item9_cuts #(
 parameter integer CUTS=0,
 parameter integer NC=8,NOG=8,PFMAX=384,LANES=16,BF16=1,INJ=2,NPT=8,LAT=7,SLOTREG=1,
 parameter integer FW=32*LANES,PWT=FW+33
)(input wire clk,rst_n,active,arm,input wire [7:0] rank,input wire [15:0] pf,
 input wire [INJ-1:0] h_v,input wire [INJ*(32+FW)-1:0] h_d,
 input wire [NPT-1:0] p_v,input wire [NPT*PWT-1:0] p_flit,
 output wire r_v,output wire [15:0] r_m,output wire [FW-1:0] r_d,
 output wire dupe,issue_o,quiet);
 wire [INJ*(16+FW)-1:0] own;
 wire [NPT*(FW+25)-1:0] peer;
 wire [NPT-1:0] valid,bad;
 for(genvar i=0;i<INJ;i=i+1)begin:g_own
   assign own[i*(FW+16)+:FW+16]=h_d[i*(FW+32)+:FW+16];
 end
 for(genvar p=0;p<NPT;p=p+1)begin:g_peer
   wire identity=p_flit[p*PWT+FW+24+:8]==rank && !p_flit[p*PWT+PWT-1];
   assign valid[p]=p_v[p]&&identity;
   assign bad[p]=p_v[p]&&!identity;
   assign peer[p*(FW+25)+:FW+25]={p_flit[p*PWT+PWT-1],p_flit[p*PWT+:FW+24]};
 end
 ot_ha2_owner_reduce_item9_cuts #(.CUTS(CUTS),.NC(NC),.PFMAX(PFMAX),.LANES(LANES),.BF16(BF16),
 .INJ(INJ),.NP(NPT),.LAT(LAT),.SLOTREG(SLOTREG)) u_reduce
 (.clk(clk),.rst_n(rst_n),.rank(rank),.pf(pf),.active(active),.arm(arm),.bad_peer(|bad),
 .h_v(h_v),.h_d(own),.p_v(valid),.p_flit(peer),.r_v(r_v),.r_m(r_m),.r_d(r_d),
 .dupe(dupe),.issue_o(issue_o),.quiet(quiet));
endmodule
