`timescale 1ns/1ps
// Same-edge replacement for a four-entry asynchronous-head queue. Capacity,
// admission (pre-edge count<4), and pop remain unchanged. Registered SRAM
// reads prefetch the post-edge head; read-during-write uses a captured bypass.
// No reset on payload or bypass: a head is consumed only after an admitted
// write, which establishes both macro contents and the matching bypass bit.
module qkd_host_peer_sram_head #(parameter integer W=528)(
 input wire ck,rst_n,put,pop,input wire[W-1:0]data,output wire[W-1:0]head);
 localparam integer NS=(W+15)/16, NG=(NS+11)/12;
 (* keep *)reg[1:0]wp[0:NG-1],rp[0:NG-1];
 (* keep *)reg[2:0]count[0:NG-1];
 (* keep *)reg[NS-1:0]bypass;
 reg[W-1:0]bd;
 wire[545:0]mq;
 for(genvar g=0;g<NG;g=g+1)begin:g_ctrl
  wire wr=put&&count[g]<4&&rst_n;
  wire[1:0]next_head=rp[g]+2'(pop);
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin wp[g]<=0;rp[g]<=0;count[g]<=0;end
   else begin
    if(wr)wp[g]<=wp[g]+1'b1;
    if(pop)rp[g]<=rp[g]+1'b1;
    case({wr,pop})2'b10:count[g]<=count[g]+1'b1;2'b01:count[g]<=count[g]-1'b1;default:;endcase
   end
  for(genvar s=12*g;s<NS&&s<12*(g+1);s=s+1)begin:g_sel
   localparam integer LO=16*s,BW=(W-LO<16)?W-LO:16;
   always @(posedge ck)bypass[s]<=wr&&(wp[g]==next_head);
`ifdef OT_PEER_MUT_BYPASS
   assign head[LO+:BW]=mq[LO+:BW];
`else
   assign head[LO+:BW]=bypass[s]?bd[LO+:BW]:mq[LO+:BW];
`endif
  end
 end
 always @(posedge ck)bd<=data;
`ifdef OT_PEER_MUT_ADDR
 wire[1:0]ma=rp[0]+2'(pop)+1'b1;
`else
 wire[1:0]ma=rp[0]+2'(pop);
`endif
 ot_sram_1r1w_32x546_m1_p192_mir u_mem(.clk(ck),.r_ce_in(1'b1),.r_addr_in({3'b0,ma}),.rd_out(mq),
  .w_ce_in(put&&count[0]<4&&rst_n),.w_addr_in({3'b0,wp[0]}),.wd_in({{(546-W){1'b0}},data}),.w_mask_in({546{1'b1}}));
endmodule
