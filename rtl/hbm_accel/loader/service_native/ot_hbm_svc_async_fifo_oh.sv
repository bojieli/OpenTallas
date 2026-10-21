`default_nettype none
// HBM-SVGREL8 2026-10-20: ot_hbm_svc_async_fifo (SPSC Gray-pointer FIFO, 2-stage pointer synchronisers each way, same
// handshake, same edge of every rd_valid / wr_ready / rd_data change) with the storage addressed by REGISTERED one-hot
// slot selects instead of a binary decode / mux (native census: the 8 x 285 b landing FIFOs had 570-load write-enable
// and read-select nets):
//   * write: the FREE tail slot (one-hot of wr_bin, gated by not-full, both computed from the next pointer state and
//     registered, KEPT per <= 32-bit slice) captures wr_data on every edge; the slot is published only by the Gray
//     pointer of an accepted write, so the stored word at publication is the accepted wr_data (unpublished slots are
//     never read as valid);
//   * read: rd_data = AND-OR of the slots with the registered one-hot of rd_bin (KEPT per slice).
// Resets: wr_rst_n / rd_rst_n are already-synchronised leaves of the writer / reader families (the hard svg asserts
// both from either port reset, as ot_hbm_svc_async_fifo's both_reset); each family's flops use its own leaf vector.
module ot_hbm_svc_async_fifo_oh #(parameter integer WIDTH=32,DEPTH=8,parameter integer NRW=4,NRR=4)(
 input wire wr_clk,input wire[NRW-1:0]wr_rst_n,input wire wr_valid,output wire wr_ready,
 input wire [WIDTH-1:0] wr_data,output reg wr_overflow,
 input wire rd_clk,input wire[NRR-1:0]rd_rst_n,output wire rd_valid,input wire rd_ready,
 output wire [WIDTH-1:0] rd_data,output reg rd_underflow
);
 localparam integer AW=$clog2(DEPTH),PW=AW+1,NS=(WIDTH+31)/32;
 initial if(DEPTH<4||(DEPTH&(DEPTH-1))!=0)$error("FIFO depth must be power-of-two >=4");
 initial if(NRW<1+(DEPTH*NS+31)/32||NRR<1+(DEPTH*NS+31)/32)$error("async_fifo_oh: too few reset leaves");
 reg [WIDTH-1:0] mem[0:DEPTH-1];
 reg [PW-1:0] wr_bin,wr_gray,rd_bin,rd_gray;
 (* async_reg="true" *)reg [PW-1:0] rd_gray_w1,rd_gray_w2,wr_gray_r1,wr_gray_r2;
 reg wr_online,rd_online;
 (* async_reg="true" *)reg rd_online_w1,rd_online_w2,wr_online_r1,wr_online_r2;
 (* keep="true",dont_touch="true" *) reg[DEPTH*NS-1:0]wsel_k,rsel_k;   // [slot*NS+slice]
 wire full=wr_gray=={~rd_gray_w2[PW-1:PW-2],rd_gray_w2[PW-3:0]};
 wire empty=rd_gray==wr_gray_r2;
 assign wr_ready=wr_rst_n[0]&&rd_online_w2&&!full;
 assign rd_valid=rd_rst_n[0]&&wr_online_r2&&!empty;
 wire wr_fire=wr_valid&&wr_ready,rd_fire=rd_valid&&rd_ready;
 wire [PW-1:0] wr_next=wr_bin+wr_fire,rd_next=rd_bin+rd_fire;
 wire [PW-1:0] wr_gray_next=wr_fire?((wr_next>>1)^wr_next):wr_gray;
 // next-edge full: the next write Gray pointer against the next synchronised read pointer (rd_gray_w1 -> w2)
 wire full_next=wr_gray_next=={~rd_gray_w1[PW-1:PW-2],rd_gray_w1[PW-3:0]};
 genvar s;
 generate for(s=0;s<NS;s=s+1)begin:g_sl
  localparam integer B=(WIDTH-s*32<32)?WIDTH-s*32:32;
  reg[B-1:0]o;integer k;
  always @*begin o=0;for(k=0;k<DEPTH;k=k+1)if(rsel_k[k*NS+s])o=o|mem[k][s*32+:B];end
  assign rd_data[s*32+:B]=o;
  always @(posedge wr_clk)for(k=0;k<DEPTH;k=k+1)if(wsel_k[k*NS+s])mem[k][s*32+:B]<=wr_data[s*32+:B];
 end endgenerate
 // writer family: pointer state on wr_rst_n[0], slot selects on wr_rst_n[1..] (<= 32 each)
 always @(posedge wr_clk or negedge wr_rst_n[0])begin
  if(!wr_rst_n[0])begin
   wr_bin<=0;wr_gray<=0;rd_gray_w1<=0;rd_gray_w2<=0;
   wr_online<=0;rd_online_w1<=0;rd_online_w2<=0;wr_overflow<=0;
  end else begin
   wr_online<=1;rd_online_w1<=rd_online;rd_online_w2<=rd_online_w1;
   rd_gray_w1<=rd_gray;rd_gray_w2<=rd_gray_w1;
   if(wr_valid&&!wr_ready)wr_overflow<=1;
   if(wr_fire)begin wr_bin<=wr_next;wr_gray<=(wr_next>>1)^wr_next;end
  end
 end
 generate for(s=0;s<DEPTH*NS;s=s+1)begin:g_wk
  always @(posedge wr_clk or negedge wr_rst_n[1+s/32])
   if(!wr_rst_n[1+s/32])wsel_k[s]<=(s/NS==0);
   else wsel_k[s]<=(wr_next[AW-1:0]==(s/NS))&&!full_next;
  always @(posedge rd_clk or negedge rd_rst_n[1+s/32])
   if(!rd_rst_n[1+s/32])rsel_k[s]<=(s/NS==0);
   else rsel_k[s]<=(rd_next[AW-1:0]==(s/NS));
 end endgenerate
 always @(posedge rd_clk or negedge rd_rst_n[0])begin
  if(!rd_rst_n[0])begin
   rd_bin<=0;rd_gray<=0;wr_gray_r1<=0;wr_gray_r2<=0;
   rd_online<=0;wr_online_r1<=0;wr_online_r2<=0;rd_underflow<=0;
  end else begin
   rd_online<=1;wr_online_r1<=wr_online;wr_online_r2<=wr_online_r1;
   wr_gray_r1<=wr_gray;wr_gray_r2<=wr_gray_r1;
   if(rd_ready&&!rd_valid)rd_underflow<=1;
   if(rd_fire)begin rd_bin<=rd_next;rd_gray<=(rd_next>>1)^rd_next;end
  end
 end
endmodule
`default_nettype wire
