`timescale 1ns/1ps
// Exact extraction of the real HSF0 controller's RESULT -> sequencer landing.
// The live destination/source header is a caller CSR, never a fabricated tie.
// No stage/host admission, START date, mesh encoding or draft topology is implied.
// One existing reset leaf controls pending state; payload flops are not reset.
module ot_s81hd_result_landing_hsf0 #(parameter integer MUT_USER_HI=0)(
 input wire ck,rst_result_n,
 input wire merged_valid,input wire[48:0] merged_row_bits,
 input wire[30:0] merged_identity,input wire[15:0] destination_header,
 input wire sequencer_grant,
 output wire result_pending,result_ready,overwrite,
 output wire flit_valid,output wire[511:0] flit_data
);
 wire[95:0] res_h;
 genvar g;
 generate for(g=0;g<3;g=g+1)begin:g_result_hold
  wire[95:0] dk={16'd0,merged_identity,merged_row_bits};
  ot_s81hd_hreg32 u_h(.ck(ck),.en(merged_valid),.d(dk[32*g+:32]),.q(res_h[32*g+:32]));
 end endgenerate
 reg res_l,rpend;
 wire r_cr;
 always@(posedge ck or negedge rst_result_n)
  if(!rst_result_n)begin res_l<=1'b0;rpend<=1'b0;end
  else begin res_l<=merged_valid;rpend<=(rpend&&!r_cr)||res_l;end
 wire[16:0] rs_row=res_h[16:0];
 wire[31:0] rs_bits=res_h[48:17];
 wire[9:0] rs_user=res_h[58:49];
 wire[20:0] rs_pos=res_h[79:59];
 // Original RESULT ABI: TYPE[19:16]=2, USER[39:32], POS[60:40],
 // IDX[81:61], VAL[113:82], USER_HI[152:151]. Reserved fields stay reserved.
 wire[511:0] rflit={359'd0,rs_user[9:8],37'd0,rs_bits,4'd0,rs_row,
                         rs_pos,rs_user[7:0],8'd0,4'd0,4'd2,destination_header};
 wire[511:0] checked_flit=rflit^(MUT_USER_HI ? (512'd1<<151) :512'd0);
 ot_dsrom_mtp_ltx #(.W(512))u_result_link(.clk(ck),.rst_n(rst_result_n),
  .c_valid(rpend),.c_ready(r_cr),.c_data(checked_flit),
  .l_valid(flit_valid),.l_ready(sequencer_grant),.l_data(flit_data));
 assign result_pending=rpend;
 assign result_ready=r_cr;
 assign overwrite=res_l&&rpend&&!r_cr;
endmodule
