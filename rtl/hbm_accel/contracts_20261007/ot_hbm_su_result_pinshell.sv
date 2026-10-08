`timescale 1ns/1ps
// Pin shell of the SU result ingress (redesign-hbm 2026-10-08).  The consistent die-link IO budget gives every
// port R = S = 254.5 ps (in/out max = T-60-254.5): the plain ingress failed it at TT by -569 ps (op_rows ->
// range/fault decode -> op_r; out_r -> take -> free/releasable adders and the SRAM read enable/address).
// This shell makes every data input land in a flop with no logic before it and every output leave a flop:
//   op_v/op_rows -> pin flops; the core sees op_v_p masked for one edge after op_ack (ack_d), so a stale
//                   pin-flopped op_v (the SU drops op_v up to one cycle after seeing op_ack) never re-requests.
//                   Cost: op_ack +1 cycle.
//   consumer side -> CREDIT flow instead of a same-cycle ready (a valid/ready output can't be pin-registered):
//                   out_v pulses (registered) once per row; the consumer owns an OCR-row buffer and returns one
//                   credit per freed slot on the out_r pin (now a CREDIT-RETURN pulse, pin-flopped).  The core's
//                   take = out_v_c && ocr_nz (ocr_nz registered from the exact next count).  Cost: +1 cycle on
//                   out_v/out_row/out_data; full rate needs OCR >= 4 (take -> out_v -> pop -> out_r -> cr_p -> ocr).
// Exactness: the core is unchanged; tb_sm_su_result_edge PIN=1 checks every row bit-exactly, op order, no early
// release, credits back to 64 and no consumer overflow (SMSU_OUT_OVERFLOW / SMSU_OUT_CREDIT).
module ot_hbm_su_result_pinshell #(parameter integer RW=12, DW=256, OCR=4)(
 input wire clk,rst_n,
 // die-side pins
 input wire op_v,input wire [6:0] op_rows,
 output wire out_v,input wire out_r,output wire [RW-1:0] out_row,output wire [DW-1:0] out_data,
 // core side
 input wire c_op_ack,output wire c_op_v,output wire [6:0] c_op_rows,
 input wire c_out_v,output wire c_out_r,input wire [RW-1:0] c_out_row,input wire [DW-1:0] c_out_data);
 localparam integer CW=$clog2(OCR+1)+1;
 localparam [CW-1:0] OCRV=OCR;
 reg op_v_p,ack_d;reg [6:0] op_rows_p;
 reg cr_p,ocr_nz,ov_q;reg [CW-1:0] ocr;reg [RW+DW-1:0] od_q;
 wire take=c_out_v&&ocr_nz;
 wire [CW-1:0] ocr_n=ocr-{{(CW-1){1'b0}},take}+{{(CW-1){1'b0}},cr_p};
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin op_v_p<=1'b0;ack_d<=1'b0;op_rows_p<=7'd0;cr_p<=1'b0;ocr<=OCRV;ocr_nz<=(OCR!=0);ov_q<=1'b0;end
  else begin
   op_v_p<=op_v;op_rows_p<=op_rows;ack_d<=c_op_ack;
   cr_p<=out_r;ocr<=ocr_n;ocr_nz<=ocr_n!={CW{1'b0}};ov_q<=take;
  end
 always @(posedge clk)if(take)od_q<={c_out_row,c_out_data};
 assign c_op_v=op_v_p&&!ack_d;assign c_op_rows=op_rows_p;
 assign c_out_r=ocr_nz;
 assign out_v=ov_q;assign out_row=od_q[RW+DW-1:DW];assign out_data=od_q[DW-1:0];
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n&&ocr_n>OCRV)$fatal(1,"SMSU_OUT_CREDIT credit return beyond OCR=%0d (ocr_n=%0d)",OCR,ocr_n);
`endif
endmodule
