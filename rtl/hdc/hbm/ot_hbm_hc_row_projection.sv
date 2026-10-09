`timescale 1ns/1ps
// One whole F32[20480] row. Prefetch complete before fixed-latency HCP.
// The operand window is a functional SRAM contract, not a hardened view.
// Scheduler assigns owner=(sublayer*24+row)%96 and appends zero-filled results
// to the existing collective. No arithmetic partial crosses dies.
module ot_hbm_hc_row_projection (
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
 wire ready,wfault,hfault,hready,last;wire [7:0] qv,qr,rv,rr,wre;
 wire [239:0] qa;wire [23:0] ql;wire [55:0] qt;
 wire [55:0] rt;wire [15:0] rb;wire [2047:0] rd;
 wire [127:0] wa;wire [8191:0] wq;reg [8191:0] wd;
 wire [31:0] received;reg [2:0] arb;reg [2:0] selected;reg found;
 integer i,j;
 always @* begin
  found=0;selected=arb;
  for(i=0;i<8;i=i+1) begin
   j=(int'(arb)+i)%8;
   if(!found && qv[j]) begin selected=3'(j);found=1;end
  end
 end
 assign hq_v=found;assign hq_addr=qa[selected*30+:30];
 assign hq_len=ql[selected*3+:3];assign hq_tag={selected,qt[selected*7+:7]};
 assign qr=(hq_v && hq_rdy) ? (8'b1<<selected):0;
 assign rv=hr_v?(8'b1<<hr_tag[9:7]):0;
 assign hr_rdy=rr[hr_tag[9:7]];
 genvar b;generate for(b=0;b<8;b=b+1)begin:response
  assign rt[b*7+:7]=hr_tag[6:0];assign rb[b*2+:2]=hr_beat;
  assign rd[b*256+:256]=hr_data;
 end endgenerate
 assign cmd_ready=!busy;assign o_row=row;assign fault=wfault|hfault;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin busy<=0;start<=0;launch<=0;arb<=0;end
  else begin
   start<=0;
   if(cmd_valid && cmd_ready)begin busy<=1;start<=1;row<=cmd_row;base<=cmd_weight_base;eps<=cmd_eps;end
   if(hq_v&&hq_rdy)arb<=selected+1'b1;
   if(ready && hready && busy)launch<=1;
   if(launch && hready)launch<=0;
   if(o_valid&&o_ready)busy<=0;
  end
 end
 always @(posedge clk)wd<=wq;
 ot_hdc_v41x_hcp_hbm_window #(.HW(32),.WORDS(128),.AW(16),.HAW(30)) mem(
  .clk(clk),.rst_n(rst_n),.start(start),.release_window(o_valid&&o_ready),
  .rom_base(16'd0),.hbm_base(base),.nwords(8'd80),.ready(ready),
  .hq_v(qv),.hq_rdy(qr),.hq_addr(qa),.hq_len(ql),.hq_tag(qt),
  .hr_v(rv),.hr_rdy(rr),.hr_tag(rt),.hr_beat(rb),.hr_data(rd),
  .rom_re(wre),.rom_addr(wa),.rom_q(wq),.fault(wfault),.received_sectors(received));
 ot_hdc_v41x_hcp #(.W(32),.TL(7),.PMAX(1),.OMAX(2),.ML(2)) core(
  .clk(clk),.rst_n(rst_n),.cmd_valid(launch),.cmd_ready(hready),
  .cmd_npos(2'd1),.cmd_nout(2'd1),.cmd_nchunk(16'd2560),.cmd_scale(1'b1),
  .cmd_nf(32'h46a00000),.cmd_eps(eps),.cmd_wbase(16'd0),.cmd_xbase(16'd0),
  .w_re(wre),.w_addr(wa),.w_data(wd),.x_re(x_re),.x_addr(x_addr),.x_data(x_data),
  .o_valid(o_valid),.o_ready(o_ready),.o_pos(),.o_idx(),.o_data(o_data),
  .o_last(last),.fault(hfault),.idle());
endmodule
