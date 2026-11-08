module ot_hbm_svc_async_fifo_local3 #(parameter integer WIDTH=32,DEPTH=8,SL=32,MUT=0)(
 input wire wr_clk,wr_rst_n,wr_valid,wr_pending,output wire wr_ready,
 input wire [WIDTH-1:0] wr_data,output reg wr_overflow,
 input wire rd_clk,rd_rst_n,output wire rd_valid,input wire rd_ready,
 output wire [WIDTH-1:0] rd_data,output reg rd_underflow
);
 localparam integer AW=$clog2(DEPTH),PW=AW+1,NS=(WIDTH+SL-1)/SL;
 wire both_reset=wr_rst_n&&rd_rst_n;wire wr_reset,rd_reset;
 ot_reset_sync u_wr_reset(.clk(wr_clk),.async_rst_n(both_reset),.sync_rst_n(wr_reset));
 ot_reset_sync u_rd_reset(.clk(rd_clk),.async_rst_n(both_reset),.sync_rst_n(rd_reset));
 reg [PW-1:0] wr_bin,wr_gray,rd_bin,rd_gray;
 (* async_reg="true" *)reg [PW-1:0] rd_gray_w1,rd_gray_w2,wr_gray_r1,wr_gray_r2;
 (* keep = "true" *) reg wr_online,rd_online;
 (* keep = "true", async_reg="true" *)reg rd_online_w1,rd_online_w2,wr_online_r1,wr_online_r2;
 wire full=wr_gray=={~rd_gray_w2[PW-1:PW-2],rd_gray_w2[PW-3:0]};
 wire empty=rd_gray==wr_gray_r2;
 assign wr_ready=wr_reset&&rd_online_w2&&!full;
 assign rd_valid=rd_reset&&wr_online_r2&&!empty;
 wire wr_fire=wr_valid&&wr_ready,rd_fire=rd_valid&&rd_ready;
 wire [PW-1:0] wr_next=wr_bin+wr_fire,rd_next=rd_bin+rd_fire;
 always @(posedge wr_clk or negedge wr_reset)begin
  if(!wr_reset)begin
   wr_bin<=0;wr_gray<=0;rd_gray_w1<=0;rd_gray_w2<=0;
   wr_online<=0;rd_online_w1<=0;rd_online_w2<=0;wr_overflow<=0;
  end else begin
   wr_online<=1;rd_online_w1<=rd_online;rd_online_w2<=rd_online_w1;
   rd_gray_w1<=rd_gray;rd_gray_w2<=rd_gray_w1;
   if(wr_valid&&!wr_ready)wr_overflow<=1;
   if(wr_fire)begin wr_bin<=wr_next;wr_gray<=(wr_next>>1)^wr_next;end
  end
 end
 always @(posedge rd_clk or negedge rd_reset)begin
  if(!rd_reset)begin
   rd_bin<=0;rd_gray<=0;wr_gray_r1<=0;wr_gray_r2<=0;
   rd_online<=0;wr_online_r1<=0;wr_online_r2<=0;rd_underflow<=0;
  end else begin
   rd_online<=1;wr_online_r1<=wr_online;wr_online_r2<=wr_online_r1;
   wr_gray_r1<=wr_gray;wr_gray_r2<=wr_gray_r1;
   if(rd_ready&&!rd_valid)rd_underflow<=1;
   if(rd_fire)begin rd_bin<=rd_next;rd_gray<=(rd_next>>1)^rd_next;end
  end
 end
 genvar s;
 generate for(s=0;s<NS;s=s+1)begin:g_sl
  localparam integer LO=s*SL;
  localparam integer W=(LO+SL>WIDTH)?(WIDTH-LO):SL;
  (* keep *) reg[AW-1:0]wp_k,rp_k;
  // Same edge/value as rd_online_w2; retained per slice to bound write-enable fanout.
  (* keep = "true", async_reg = "true" *) reg online_k;
  always @(posedge wr_clk or negedge wr_reset)
   if(!wr_reset) online_k<=0;
   else online_k <= (MUT==26 && s==1) ? 1'b0 : ((MUT==27 && s==1) ? rd_online_w2 : rd_online_w1);
  wire wr_fire_k = wr_pending && wr_reset && online_k && !full;
  reg[W-1:0]mem[0:DEPTH-1];
  always @(posedge wr_clk or negedge wr_reset)if(!wr_reset)wp_k<=0;else if(wr_fire_k&&!(MUT==20&&s==1&&wp_k==3))wp_k<=wp_k+1'b1;
  always @(posedge rd_clk or negedge rd_reset)if(!rd_reset)rp_k<=0;else if(rd_fire&&!(MUT==19&&s==1&&rp_k==3))rp_k<=rp_k+1'b1;
  always @(posedge wr_clk)if(wr_fire_k)mem[wp_k]<=wr_data[LO+:W];
  assign rd_data[LO+:W]=mem[rp_k];
 end endgenerate
endmodule
