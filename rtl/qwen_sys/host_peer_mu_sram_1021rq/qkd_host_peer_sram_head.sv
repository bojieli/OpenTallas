`timescale 1ns/1ps
// QE3-HROOT-PEER 10-21: registered-head successor of the historical
// qkd_host_peer_sram_head (fixture/historical/.../host_integrated_20261014). Same module
// name, ports, capacity, admission (pre-edge count<4), pop and head timing (cycle-exact
// at the ports), but the head is now a REGISTER (hq):
//  - the SRAM rd_out is captured straight into hq through ONE select level (sel_mq ? mq : alt);
//    no consumer logic sits between the macro and a flop any more (p32j EARLY_FAIL_SETUP: rd_out
//    -> 17-level compare cone -> DFF, TT -424 ps). Every consumer now starts at hq flops.
//  - the macro is read one slot AHEAD (ma = post-edge rp + 1), so on a pop with >=2 entries
//    the next head is already on rd_out; a slot written on the previous edge (not yet visible
//    in that read) is taken from bd (registered write data, flag nb); a write into an empty
//    queue (or count 1 + pop) loads the write data directly.
// No reset on payload/head/flags: a head is consumed only after an admitted write, which
// establishes hq (direct load) or both macro contents and nb/bd.
module qkd_host_peer_sram_head #(parameter integer W=528)(
 input wire ck,rst_n,put,pop,input wire[W-1:0]data,output wire[W-1:0]head);
 localparam integer NS=(W+15)/16, NG=(NS+11)/12;
 (* keep *)reg[1:0]wp[0:NG-1],rp[0:NG-1];
 (* keep *)reg[2:0]count[0:NG-1];
 (* keep *)reg[NS-1:0]nb;
 reg[W-1:0]bd,hq;
 wire[545:0]mq;
`ifdef OT_PEER_MUT_ADDR
 wire[1:0]ma=rp[0]+2'(pop)+2'd2;
`else
 wire[1:0]ma=rp[0]+2'(pop)+2'd1;
`endif
 for(genvar g=0;g<NG;g=g+1)begin:g_ctrl
  wire wr=put&&count[g]<4&&rst_n;
`ifdef OT_PEER_MUT_ADDR
  wire[1:0]ma_g=rp[g]+2'(pop)+2'd2;
`else
  wire[1:0]ma_g=rp[g]+2'(pop)+2'd1;
`endif
  wire ld_data=wr&&(count[g]==0||(count[g]==1&&pop));
  wire ld_next=pop&&count[g]>=2;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin wp[g]<=0;rp[g]<=0;count[g]<=0;end
   else begin
    if(wr)wp[g]<=wp[g]+1'b1;
    if(pop)rp[g]<=rp[g]+1'b1;
    case({wr,pop})2'b10:count[g]<=count[g]+1'b1;2'b01:count[g]<=count[g]-1'b1;default:;endcase
   end
  for(genvar s=12*g;s<NS&&s<12*(g+1);s=s+1)begin:g_sel
   localparam integer LO=16*s,BW=(W-LO<16)?W-LO:16;
   always @(posedge ck)nb[s]<=wr&&(wp[g]==ma_g);
`ifdef OT_PEER_MUT_BYPASS
   wire sel_mq=ld_data||ld_next;
`else
   wire sel_mq=!ld_data&&ld_next&&!nb[s];
`endif
   wire[BW-1:0]alt=ld_data?data[LO+:BW]:(ld_next?bd[LO+:BW]:hq[LO+:BW]);
   always @(posedge ck)hq[LO+:BW]<=sel_mq?mq[LO+:BW]:alt;
   assign head[LO+:BW]=hq[LO+:BW];
  end
 end
 always @(posedge ck)bd<=data;
 ot_sram_1r1w_32x546_m1_p192_mir u_mem(.clk(ck),.r_ce_in(1'b1),.r_addr_in({3'b0,ma}),.rd_out(mq),
  .w_ce_in(put&&count[0]<4&&rst_n),.w_addr_in({3'b0,wp[0]}),.wd_in({{(546-W){1'b0}},data}),.w_mask_in({546{1'b1}}));
endmodule
