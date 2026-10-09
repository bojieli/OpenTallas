// Additive128-row logical successor; original source remains byte-identical.
`timescale 1ns/1ps
// Candidate only: full 545-bit TU flit, 64, 128 or 256 logical entries. Three real
// 256x256 1R1W macros, nine 64+8 SECDED words. Default disabled. Explicit clk
// is the queue's one domain: this is NOT a replacement for dual-clock FIFOs.
// Model: tools/hbm_collective_storage_model.py. II=3; no throughput credit.
module ot_hbm_collective_packet_fifo_128 #(parameter integer ENABLE=0, DEPTH=256)(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:g_off
  assign ready=0;assign valid=0;assign dout=0;assign fault=0;assign count=0;
 end else begin:g_on
 initial if(DEPTH!=64&&DEPTH!=128&&DEPTH!=256)$fatal(1,"collective FIFO depth must be 64, 128 or 256");
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
 wire fetch=c.unread!=0&&!c.pending&&!c.held&&!fault;
 always @*begin
  ram_d=0;
  for(integer s=0;s<9;s=s+1)ram_d[s*72+:72]=encode64(64'(576'(din)>>(64*s)));
  n=c;
  if(push&&!ready)n.overflow=1;
  if(put)begin n.wp=(c.wp==DEPTH-1)?0:c.wp+1'b1;n.unread=n.unread+1'b1;end
  if(fetch)begin n.rp=(c.rp==DEPTH-1)?0:c.rp+1'b1;n.unread=n.unread-1'b1;n.pending=1;end
  if(c.pending)begin n.pending=0;n.held=1;end
  if(valid&&pop)n.held=0;
 end
 for(genvar m=0;m<3;m=m+1)begin:g_ram
  ot_sram_1r1w_256x256_m2_r2c2 storage(.clk(clk),.r_ce_in(fetch),.r_addr_in(c.rp),.rd_out(ram_q[m*256+:256]),
   .w_ce_in(put),.w_addr_in(c.wp),.wd_in(ram_d[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin c<='0;seal<=0;captured<=0;end
  else begin
   if(!fault)begin c<=n;seal<=encode64(64'(n));if(c.pending)captured<=ram_q[647:0];end
  end
 end endgenerate
endmodule
