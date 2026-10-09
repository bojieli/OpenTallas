`timescale 1ns/1ps
// Whole-rowHCP, both operands privately resident in real protected SRAM.
// Production900MHzserialclock,service/producerCDC belongs to die collars.
// Tag identifies this residual snapshot, independent of static FN base.
module ot_hbm_hc_row_private(
 input wire clk,rst_n,cmd_valid,output wire cmd_ready,input wire[4:0]cmd_row,
 input wire[15:0]cmd_lease,input wire[29:0]cmd_weight_base,input wire[31:0]cmd_eps,
 output wire hq_v,input wire hq_rdy,output wire[29:0]hq_addr,output wire[2:0]hq_len,output wire[9:0]hq_tag,
 input wire hr_v,output wire hr_rdy,input wire[9:0]hr_tag,input wire[1:0]hr_beat,input wire[255:0]hr_data,
 input wire x_valid,output wire x_ready,input wire[15:0]x_lease,input wire[10:0]x_beat,input wire[255:0]x_data,
 output wire o_valid,input wire o_ready,output wire[4:0]o_row,output wire[15:0]o_lease,
 output wire[31:0]o_data,output wire fault
);
 reg busy,start,launch,cfault;reg[4:0]row;reg[15:0]lease;reg[29:0]base;reg[31:0]eps;
 wire wrdy,xrdy,wfault,xfault,hfault,hready,core_valid;
 assign o_valid=core_valid&&!fault;
 wire[7:0]wre,xre;wire[127:0]wa,xa;wire[8191:0]wq;wire[4095:0]xq;
 assign cmd_ready=!busy&&!fault;assign fault=cfault|wfault|xfault|hfault;
 assign o_row=row;assign o_lease=lease;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;start<=0;launch<=0;cfault<=0;end
  else begin
   start<=0;
   if(cmd_valid&&cmd_ready)begin
    if(cmd_row>=24)cfault<=1;
    else begin busy<=1;start<=1;row<=cmd_row;lease<=cmd_lease;base<=cmd_weight_base;eps<=cmd_eps;end
   end
   if(wrdy&&xrdy&&hready&&busy&&!fault)launch<=1;
   if(launch&&hready)launch<=0;
   if(o_valid&&o_ready)busy<=0;
  end
 end
 ot_hbm_hc_row_operand_sram weights(.clk(clk),.rst_n(rst_n),.start(start),.release_window(o_valid&&o_ready),
  .hbm_base(base),.ready(wrdy),.hq_v(hq_v),.hq_rdy(hq_rdy),.hq_addr(hq_addr),.hq_len(hq_len),.hq_tag(hq_tag),
  .hr_v(hr_v),.hr_rdy(hr_rdy),.hr_tag(hr_tag),.hr_beat(hr_beat),.hr_data(hr_data),
  .rom_re(wre),.rom_addr(wa),.rom_q(wq),.fault(wfault),.ce_seen(),.ue_seen());
 ot_hbm_hc_flat_operand_sram flat(.clk(clk),.rst_n(rst_n),.start(start),.release_window(o_valid&&o_ready),.lease(lease),
  .i_valid(x_valid),.i_ready(x_ready),.i_lease(x_lease),.i_beat(x_beat),.i_data(x_data),
  .ready(xrdy),.re(xre),.addr(xa),.q(xq),.fault(xfault),.ce_seen(),.ue_seen());
 ot_hdc_v41x_hcp #(.W(32),.TL(7),.PMAX(1),.OMAX(2),.ML(3))core(
  .clk(clk),.rst_n(rst_n),.cmd_valid(launch),.cmd_ready(hready),.cmd_npos(2'd1),.cmd_nout(2'd1),
  .cmd_nchunk(16'd2560),.cmd_scale(1'b1),.cmd_nf(32'h46a00000),.cmd_eps(eps),.cmd_wbase(16'd0),.cmd_xbase(16'd0),
  .w_re(wre),.w_addr(wa),.w_data(wq),.x_re(xre),.x_addr(xa),.x_data(xq),
  .o_valid(core_valid),.o_ready(o_ready),.o_pos(),.o_idx(),.o_data(o_data),.o_last(),.fault(hfault),.idle());
endmodule
