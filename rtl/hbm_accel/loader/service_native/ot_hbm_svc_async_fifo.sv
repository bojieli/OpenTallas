`default_nettype none
// SPSC Gray-pointer FIFO. Two pointer synchronizer stages in each direction;
// empty/full compare synchronized Gray pointers directly. Consumers capture
// rd_data on rd_valid&&rd_ready; pointer release follows that same edge.
// Data is held until the synchronized read pointer permits slot reuse.
module ot_hbm_svc_async_fifo #(parameter integer WIDTH=32,DEPTH=8)(
 input wire wr_clk,wr_rst_n,wr_valid,output wire wr_ready,
 input wire [WIDTH-1:0] wr_data,output reg wr_overflow,
 input wire rd_clk,rd_rst_n,output wire rd_valid,input wire rd_ready,
 output wire [WIDTH-1:0] rd_data,output reg rd_underflow
);
 localparam integer AW=$clog2(DEPTH),PW=AW+1;
 initial if(DEPTH<4||(DEPTH&(DEPTH-1))!=0)$error("FIFO depth must be power-of-two >=4");
 wire both_reset=wr_rst_n&&rd_rst_n;wire wr_reset,rd_reset;
 ot_reset_sync u_wr_reset(.clk(wr_clk),.async_rst_n(both_reset),.sync_rst_n(wr_reset));
 ot_reset_sync u_rd_reset(.clk(rd_clk),.async_rst_n(both_reset),.sync_rst_n(rd_reset));
 reg [WIDTH-1:0] mem[0:DEPTH-1];
 reg [PW-1:0] wr_bin,wr_gray,rd_bin,rd_gray;
 (* async_reg="true" *)reg [PW-1:0] rd_gray_w1,rd_gray_w2,wr_gray_r1,wr_gray_r2;
 reg wr_online,rd_online;
 (* async_reg="true" *)reg rd_online_w1,rd_online_w2,wr_online_r1,wr_online_r2;
 wire full=wr_gray=={~rd_gray_w2[PW-1:PW-2],rd_gray_w2[PW-3:0]};
 wire empty=rd_gray==wr_gray_r2;
 assign wr_ready=wr_reset&&rd_online_w2&&!full;
 assign rd_valid=rd_reset&&wr_online_r2&&!empty;
 assign rd_data=mem[rd_bin[AW-1:0]];
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
   if(wr_fire)begin mem[wr_bin[AW-1:0]]<=wr_data;wr_bin<=wr_next;wr_gray<=(wr_next>>1)^wr_next;end
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
endmodule

// Error-only sticky status transfer. A single FIFO token replaces a separate
// ad hoc status synchronizer, so all asynchronous data follows the audited
// Gray FIFO. This does not participate in normal compiled issue or pacing.
// The source remembers a transient fault even before the FIFO is online.
// Resetting either interface flushes the token and permits resending a still
// asserted source fault. Detection takes the FIFO online/synchronizer latency
// plus one source edge and one destination capture edge, rather than two flops.
module ot_hbm_svc_fault_cdc #(parameter integer MUT=0)(
 input wire wr_clk,wr_rst_n,rd_clk,rd_rst_n,input wire src_fault,
 output wire dst_fault,output wire wr_overflow,rd_underflow
);
 wire both_reset=wr_rst_n&&rd_rst_n;
 wire src_reset=(MUT==3)?wr_rst_n:both_reset;
 reg pending,sent;
 wire ready,valid;wire[0:0]data;
 wire offer=(MUT==1)?1'b0:((MUT==4)?pending:((MUT==5)?(src_fault&&!sent&&ready):(pending&&!sent&&ready)));
 always @(posedge wr_clk or negedge src_reset)begin
  if(!src_reset)begin pending<=0;sent<=0;end
  else begin
   if(src_fault)pending<=1;
   if(pending&&!sent&&ready)sent<=1;
  end
 end
 ot_hbm_svc_async_fifo #(.WIDTH(1),.DEPTH(4)) u_status(
  .wr_clk(wr_clk),.wr_rst_n(wr_rst_n),.wr_valid(offer),.wr_ready(ready),.wr_data(1'b1),.wr_overflow(wr_overflow),
  .rd_clk(rd_clk),.rd_rst_n(rd_rst_n),.rd_valid(valid),.rd_ready(valid),.rd_data(data),.rd_underflow(rd_underflow));
 reg sticky;
 always @(posedge rd_clk or negedge both_reset)begin
  if(!both_reset)sticky<=0;
  else if(valid&&data[0])sticky<=1;
 end
 assign dst_fault=(MUT==2)?valid:sticky;
endmodule
`default_nettype wire
