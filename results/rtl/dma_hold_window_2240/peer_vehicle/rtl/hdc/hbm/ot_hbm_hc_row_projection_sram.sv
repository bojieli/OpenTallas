`timescale 1ns/1ps
// One whole F32[20480] row. Prefetch complete before fixed-latency HCP.
// Operand supply uses40 real SRAM instances and SECDED; physical view
// qualification remains pending. Weight ML3; caller supplies x at ML2.
// Scheduler assigns owner=(sublayer*24+row)%96 and appends zero-filled results
// to the existing collective. No arithmetic partial crosses dies.
module ot_hbm_hc_row_projection_sram (
 input wire clk,rst_n,cmd_valid, output wire cmd_ready,
 input wire [4:0] cmd_row, input wire [29:0] cmd_weight_base,
 input wire [31:0] cmd_eps,
 output wire hq_v,input wire hq_rdy,output wire [29:0] hq_addr,
 output wire [2:0] hq_len,output wire [9:0] hq_tag,
 input wire hr_v,output wire hr_rdy,input wire [9:0] hr_tag,
 input wire [1:0] hr_beat,input wire [255:0] hr_data,
 output wire [7:0] x_re,output wire [127:0] x_addr,
 input wire [4095:0] x_data,
 output wire o_valid,input wire o_ready,output wire [4:0] o_row,
 output wire [31:0] o_data,output wire fault
);
 reg busy,start,launch; reg [4:0] row; reg [29:0] base;reg [31:0] eps;
 wire ready,wfault,hfault,hready,last;wire [7:0] wre;
 wire [127:0] wa;wire [8191:0] wq;reg [4095:0] xd;
 wire [31:0] ce_seen,ue_seen;
 assign cmd_ready=!busy;assign o_row=row;assign fault=wfault|hfault;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin busy<=0;start<=0;launch<=0;end
  else begin
   start<=0;
   if(cmd_valid && cmd_ready)begin busy<=1;start<=1;row<=cmd_row;base<=cmd_weight_base;eps<=cmd_eps;end
   if(ready && hready && busy)launch<=1;
   if(launch && hready)launch<=0;
   if(o_valid&&o_ready)busy<=0;
  end
 end
 always @(posedge clk)xd<=x_data;
 ot_hbm_hc_row_operand_sram mem(
  .clk(clk),.rst_n(rst_n),.start(start),.release_window(o_valid&&o_ready),
  .hbm_base(base),.ready(ready),.hq_v(hq_v),.hq_rdy(hq_rdy),
  .hq_addr(hq_addr),.hq_len(hq_len),.hq_tag(hq_tag),
  .hr_v(hr_v),.hr_rdy(hr_rdy),.hr_tag(hr_tag),.hr_beat(hr_beat),.hr_data(hr_data),
  .rom_re(wre),.rom_addr(wa),.rom_q(wq),.fault(wfault),.ce_seen(ce_seen),.ue_seen(ue_seen));
 ot_hdc_v41x_hcp #(.W(32),.TL(7),.PMAX(1),.OMAX(2),.ML(3)) core(
  .clk(clk),.rst_n(rst_n),.cmd_valid(launch),.cmd_ready(hready),
  .cmd_npos(2'd1),.cmd_nout(2'd1),.cmd_nchunk(16'd2560),.cmd_scale(1'b1),
  .cmd_nf(32'h46a00000),.cmd_eps(eps),.cmd_wbase(16'd0),.cmd_xbase(16'd0),
  .w_re(wre),.w_addr(wa),.w_data(wq),.x_re(x_re),.x_addr(x_addr),.x_data(xd),
  .o_valid(o_valid),.o_ready(o_ready),.o_pos(),.o_idx(),.o_data(o_data),
  .o_last(last),.fault(hfault),.idle());
endmodule
