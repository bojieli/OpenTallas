`timescale 1ns/1ps
// Default-off physical leaf of ot_qwen_rt_kv_stream4_service's landed-beat decode.
// Four registered edges. One beat/cycle, 8 initial credits. Each input reserves
// a slot in the downstream FIFO (depth >=8); o_cr returns only on that FIFO pop.
// The trusted expected-sector/count/window tuple comes from the PC sequencer.
// No descriptor or map generation is claimed here. Invalid beats emit bad=1,
// never a write; bad must veto publication before its transaction can retire.
module ot_qwen_kvc_decode_pc #(parameter integer ENABLE=0)(
 input wire clk, rst_n,
 input wire i_v, input wire [255:0] i_data,
 input wire [16:0] i_sec, i_expected,
 input wire [12:0] i_pos, input wire [7:0] i_row, i_layer,
 input wire [10:0] i_count, i_limit,
 input wire i_active, i_done,
 input wire o_cr,
 output reg i_cr, output reg o_v,
 output reg [255:0] o_data,
 output reg [10:0] o_tile0, o_tile1,
 output reg [6:0] o_loc0, o_loc1,
 output reg [1:0] o_sel0, o_sel1, o_n,
 output reg o_isk, o_tail, o_bad, o_drop,
 output reg [3:0] o_tail_lanes,
 output reg fault
);
 (* keep *) reg v0, cr0;
 (* keep *) reg [255:0] data0;
 (* keep *) reg [16:0] sec0, expected0;
 (* keep *) reg [12:0] pos0;
 (* keep *) reg [7:0] row0, layer0;
 (* keep *) reg [10:0] count0, limit0;
 (* keep *) reg active0, done0;
 reg [3:0] credits;
 reg v1, v2, bad1, bad2, drop2, isk1, isk2, tail1, tail2;
 reg [255:0] data1, data2;
 reg [8:0] kmod1, kdiv1;
 reg [6:0] d1;
 reg h1;
 reg [12:0] pp1, pos1;
 reg [2:0] q1;
 reg [10:0] tile02, tile12;
 reg [6:0] loc02, loc12;
 reg [1:0] sel02, sel12, n2;
 reg [3:0] lanes2;
 wire admit = (ENABLE != 0) && v0 && (credits != 0);
 wire credit_ok = cr0 && (credits < 8 || admit);
 always @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
   v0<=0; cr0<=0; v1<=0; v2<=0; o_v<=0; i_cr<=0;
   credits<=8; fault<=0;
   data0<=0; sec0<=0; expected0<=0; pos0<=0; row0<=0; layer0<=0;
   count0<=0; limit0<=0; active0<=0; done0<=0;
   data1<=0; kmod1<=0; kdiv1<=0; d1<=0; h1<=0; pp1<=0; q1<=0;
   pos1<=0; bad1<=0; isk1<=0; tail1<=0;
   data2<=0; tile02<=0; tile12<=0; loc02<=0; loc12<=0;
   sel02<=0; sel12<=0; n2<=0; bad2<=0; drop2<=0; isk2<=0; tail2<=0; lanes2<=0;
   o_data<=0; o_tile0<=0; o_tile1<=0; o_loc0<=0; o_loc1<=0;
   o_sel0<=0; o_sel1<=0; o_n<=0; o_bad<=0; o_drop<=0;
   o_isk<=0; o_tail<=0; o_tail_lanes<=0;
  end else begin
   // All external signals terminate at pin registers, including credit return.
   v0<=i_v; cr0<=o_cr; data0<=i_data; sec0<=i_sec; expected0<=i_expected;
   pos0<=i_pos; row0<=i_row; layer0<=i_layer; count0<=i_count;
   limit0<=i_limit; active0<=i_active; done0<=i_done;
   i_cr<=credit_ok && (ENABLE != 0);
   if (ENABLE != 0) begin
    case ({credit_ok,admit})
     2'b01: credits<=credits-1'b1;
     2'b10: credits<=credits+1'b1;
     default: credits<=credits;
    endcase
    if ((v0 && !admit) || (cr0 && !credit_ok)) fault<=1;
   end
   v1<=admit;
   data1<=data0; pos1<=pos0;
   bad1<=!active0 || done0 || count0>=limit0 || sec0!=expected0 || row0!=layer0;
   isk1<=!expected0[16];
   h1<=expected0[15];
   kmod1<=expected0[14:6]%48; kdiv1<=expected0[14:6]/48;
   d1<={expected0[5:0],1'b0};
   pp1<=expected0[14:2]; q1<={expected0[1:0],1'b0};
   tail1<=expected0[14:6]==pos0[12:4];
   v2<=v1; data2<=data1; bad2<=bad1;
   isk2<=isk1; tail2<=isk1 && tail1; lanes2<=pos1[3:0];
   drop2<=!isk1 && pp1>=pos1;
   // Compact representation expands to exactly the golden 512b data/mask.
   tile02<=isk1 ? (kmod1*32+d1/4) : (q1*128+pp1[8:2]);
   tile12<=isk1 ? 0 : ((q1+11'd1)*128+pp1[8:2]);
   loc02<=isk1 ? (kdiv1*2+h1) : (22+pp1[12:9]*2+h1);
   loc12<=isk1 ? 0 : (22+pp1[12:9]*2+h1);
   sel02<=isk1 ? d1[1:0] : pp1[1:0];
   sel12<=isk1 ? 0 : pp1[1:0];
   n2<=bad1 ? 0 : isk1 ? 1 : pp1>=pos1 ? 0 : 2;
   o_v<=v2; o_data<=data2; o_tile0<=tile02; o_tile1<=tile12;
   o_loc0<=loc02; o_loc1<=loc12; o_sel0<=sel02; o_sel1<=sel12;
   o_n<=n2; o_isk<=isk2; o_tail<=tail2; o_tail_lanes<=lanes2;
   o_bad<=bad2; o_drop<=drop2;
  end
 end
endmodule
