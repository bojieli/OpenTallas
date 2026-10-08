`timescale 1ns/1ps
// II=1 successor of ot_hbm_collective_packet_fifo (same ports, storage, encoding, seal and fault rules).
// Opt-in: selected by ot_hbm_collective_fifo_adapter ENABLE_SRAM=2; the II=3 source is unchanged.
//
// The II=3 queue fetches only when nothing is pending or held: fetch -> pending (SRAM read, rd_out
// updates) -> held (encoded word captured, decoded, visible) -> pop, then the next fetch.
// The refill keeps a TWO-slot head with no new data register:
//   R    = the macro's own read latch (rd_out holds its value while r_ce_in is low; ot_sram_* behavioural
//          model: `if (r_ce_in) rd_out <= ...`), flag c.pending = "rd_out holds a fetched, untransferred word";
//   H    = captured (encoded, 648 b), flag c.held.
// Every cycle: xfer = pending && (!held || pop accepted) moves R -> H (captured <= ram_q);
//              fetch = unread != 0 && (!pending || xfer) issues the next SRAM read into R.
// In a stream with pop every cycle: H pops, R moves to H, the next read refills R -> one flit an edge.
// Empty start latency is unchanged (fetch, transfer, visible: 2 edges after the write edge).
// The read address is the REGISTERED c.rp (no pop -> address path); pop reaches only r_ce_in, the
// captured load enable and the control next-state, so the CDC's registered-address fix
// (addr = (hp==0) ? rb : rb_next) has no analogue here.
// count = unread + pending + held, exactly as before; ready = count < DEPTH; overflow latches.
module ot_hbm_collective_packet_fifo_refill #(parameter integer ENABLE=0, DEPTH=256)(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:g_off
  assign ready=0;assign valid=0;assign dout=0;assign fault=0;assign count=0;
 end else begin:g_on
 initial if(DEPTH!=64&&DEPTH!=256)$fatal(1,"collective FIFO depth must be 64 or 256");
 typedef struct packed {logic [7:0] wp,rp;logic [8:0] unread;logic pending,held,overflow;} ctl_t;
 ctl_t c,n;reg [71:0] seal;reg [647:0] captured;
 wire [767:0] ram_q;reg [767:0] ram_d;
 wire bad=seal!=encode64(64'(c));
 wire [575:0] decoded;wire [8:0] ue;
 for(genvar s=0;s<9;s=s+1)begin:g_decode
  wire [65:0] d=decode64(captured[s*72+:72]);
  assign decoded[s*64+:64]=d[63:0];assign ue[s]=d[65];
 end
 assign count=c.unread+9'(c.pending)+9'(c.held);
 assign fault=bad||c.overflow||(c.held&&((|ue)||(|decoded[575:545])));
 assign valid=c.held&&!fault;assign dout=decoded[544:0];
 assign ready=count<DEPTH&&!fault;
 wire put=push&&ready;
 wire take=valid&&pop;
 wire xfer=c.pending&&(!c.held||take)&&!fault;
 wire fetch=c.unread!=0&&(!c.pending||xfer)&&!fault;
 always @*begin
  ram_d=0;
  for(integer s=0;s<9;s=s+1)ram_d[s*72+:72]=encode64(64'(576'(din)>>(64*s)));
  n=c;
  if(push&&!ready)n.overflow=1;
  if(put)begin n.wp=(c.wp==DEPTH-1)?0:c.wp+1'b1;n.unread=n.unread+1'b1;end
  if(take)n.held=0;
  if(xfer)begin n.pending=0;n.held=1;end
  if(fetch)begin n.rp=(c.rp==DEPTH-1)?0:c.rp+1'b1;n.unread=n.unread-1'b1;n.pending=1;end
 end
 for(genvar m=0;m<3;m=m+1)begin:g_ram
  ot_sram_1r1w_256x256_m2_r2c2 storage(.clk(clk),.r_ce_in(fetch),.r_addr_in(c.rp),.rd_out(ram_q[m*256+:256]),
   .w_ce_in(put),.w_addr_in(c.wp),.wd_in(ram_d[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin c<='0;seal<=0;captured<=0;end
  else begin
   if(!fault)begin c<=n;seal<=encode64(64'(n));if(xfer)captured<=ram_q[647:0];end
  end
 end endgenerate
endmodule
