`timescale 1ns/1ps
`default_nettype none
// One engine, eight reusable shells, thirty-two parameterless CLOSED MACs.
// Clock inputs are actual source roots; synchronous phase closure is external.
module ot_hgi_hc_projection_sys1_static #(
 parameter integer SYS_LAT=86
)(
 input wire clk,reduction_clk,scalar_clk,rst_n,
 input wire [7:0] bank_clk,
 input wire [31:0] mac_clk,
 input wire [2223:0] weight_ap,
 input wire x_wave_v,input wire [9:0] x_wave_word,input wire [8191:0] x_wave,
 input wire launch,raw_read,weight_slot,
 input wire [3:0] npos,input wire [31:0] eps,
 output wire result_v,output wire [2:0] result_pos,
 output wire [31:0] result_data,output wire fault
);
 wire [8:0] dv,ss,ff;
 wire [53:0] nv;
 wire [143:0] wa,xa;
 wire [9215:0] sums;
 assign sums[1023:0]=0;assign ff[0]=0;
 for(genvar b=0;b<8;b=b+1)begin:bank
  wire [511:0] xd;
  wire [1023:0] wd;
  wire [31:0] lv,ls;
  wire go;wire [3:0] lf;
  wire [511:0] xwrite;
  for(genvar m=0;m<2;m=m+1)begin:half
   for(genvar l=0;l<16;l=l+1)begin:lane
    assign xwrite[m*256+l*16+:16]=x_wave[(m*16+l)*256+b*32+16+:16];
   end
  end
  ot_hgi_hc_bank_shell_shared_static shell(
   .clk(bank_clk[b]),.rst_n(rst_n),.expected_bank_id(3'(b)),
   .weight_ap(weight_ap[b*278+:278]),.x_write_v(x_wave_v),
   .x_write_word(x_wave_word),.x_write_data(xwrite),
   .d_v(dv[b]),.d_ss(ss[b]),.d_nv(nv[b*6+:6]),.d_wa(wa[b*16+:16]),.d_xa(xa[b*16+:16]),
   .f_in(ff[b]),.lane_fault(lf),.o_v(dv[b+1]),.o_ss(ss[b+1]),
   .o_nv(nv[(b+1)*6+:6]),.o_wa(wa[(b+1)*16+:16]),.o_xa(xa[(b+1)*16+:16]),
   .f_out(ff[b+1]),.lane_valid(lv),.lane_ss(ls),.lane_go(go),
   .weight_data(wd),.residual_data(xd),.write_done(),.read_valid(),.memory_fault());
  for(genvar q=0;q<4;q=q+1)begin:mac
   ot_hdc_v41x_hcp_lanes lanes(
    .clk(mac_clk[4*b+q]),.rst_n(rst_n),.fst(b==0),.gov_i(go),
    .lv_i(lv[q*8+:8]),.ss_i(ls[q*8+:8]),.w_i(wd[q*256+:256]),.x_i(xd[q*128+:128]),
    .s_i(sums[b*1024+q*256+:256]),.y(sums[(b+1)*1024+q*256+:256]),.lf(lf[q]));
  end
 end
 ot_hdc_v41x_hcp_sys1_static #(.W(32),.PMAX(8),.OMAX(2),.DF(32),
  .STATIC_CALENDAR(1),.SYS(1),.SYS_LAT(SYS_LAT)) core(
  .clk(clk),.reduction_clk(reduction_clk),.scalar_clk(scalar_clk),.rst_n(rst_n),.calendar_pop(raw_read),
  .cmd_valid(launch),.cmd_ready(),.cmd_npos(npos),.cmd_nout(2'd1),.cmd_nchunk(16'd2560),
  .cmd_scale(1'b1),.cmd_nf(32'h46a00000),.cmd_eps(eps),.cmd_wbase({8'd0,weight_slot,7'd0}),.cmd_xbase(16'd0),
  .w_re(),.x_re(),.w_addr(),.x_addr(),.w_data(8192'd0),.x_data(4096'd0),
  .o_valid(result_v),.o_ready(1'b1),.o_pos(result_pos),.o_idx(),.o_data(result_data),.o_last(),.fault(fault),.idle(),
  .sd_v(dv[0]),.sd_ss(ss[0]),.sd_nv(nv[0+:6]),.sd_wa(wa[0+:16]),.sd_xa(xa[0+:16]),
  .sys_sum(sums[8192+:1024]),.sys_fault(ff[8]));
endmodule
`default_nettype wire
