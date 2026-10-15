`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Static SU quarter CORE (H-ELEM-B 2026-10-15): the quarter's RF replica ot_hbm_su_static_rf (64 banks x 4 words, six read
// classes) and its reducer ot_hbm_su_reduce_static, between the four port-group slices of the quarter.
// RF read commands rf_rd_cmd[c] = {v, addr8} (addr[5:0] bank, addr[7:6] row), all on fixed edges:
//   class 0..3  lane operand broadcast: issued ONE edge before the lanes' request edge n; RF data held k+2..k+3 is
//               registered here (rf_bword, held n+2..n+3) and consumed by the lanes at n+3; rf_bcmd = the command delayed
//               one edge (the slices check every RF-source lane address against it);
//   class 4     reducer external operand: issued TWO edges before the reducer command edge E (operand taken at E+1);
//   class 5     RF sector drain: addr[2:0] must be 0; issued one edge before the slice-0 port-0 vmw (src 1) command;
//               the 8 words are registered here (rf_dsec) and taken by slice 0's drain stage.
// Reducer: red_cmd = {v, op3, a10, b10, dst10, tag32, osel, lane7} at E. The slices register the selected lane's ro_x at
// E; the core picks slice (lane[5:4]) or the RF class-4 word (osel) and registers operand + command at E+1; the reducer
// samples at E+2 (its issue), scalar valid held E+10.. (issue + 8, reducer r1 registered SRAM-operand stage). tag[8] = write RF word tag[7:0] (through the top's
// relay routes, which return to this replica's write port rf_w* like every other replica).
// Checks (FAULT): two RF writers on one bank in one edge; class-5 address not sector aligned; an RF-source drain without
// the class-5 read one edge earlier; reducer fault.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_qcore #(parameter integer MUT=0)(
 input wire [63:0] clk_rf,
 input wire clk_ctl,clk_red,rst_n,
 input wire [6*9-1:0] rf_rd_cmd,
 input wire [73:0] red_cmd,
 input wire rf_drain_now,                     // slice 0 port 0 vmw command is a valid src-1 (RF) drain at this edge
 input wire [4*32-1:0] slice_x,
 input wire [3:0] rf_wv, input wire [4*8-1:0] rf_wa, input wire [4*32-1:0] rf_wd,
 output reg [4*32-1:0] rf_bword,
 output reg [4*9-1:0] rf_bcmd,
 output reg [255:0] rf_dsec,
 output wire red_sv, output wire [31:0] red_tag, output wire [31:0] red_x,
 output reg fault
);
 wire [64*6-1:0] rf_rv; wire [64*6*2-1:0] rf_ra; wire [64*6*32-1:0] rf_q;
 wire [63:0] rf_wvb; wire [64*2-1:0] rf_wab; wire [64*32-1:0] rf_wdb; wire [63:0] rf_wconf;
 for(genvar bb=0;bb<64;bb=bb+1)begin:g_rfb
  for(genvar c=0;c<5;c=c+1)begin:g_c
   wire [8:0] cmd=rf_rd_cmd[c*9+:9];
   assign rf_rv[bb*6+c]=cmd[8]&&cmd[5:0]==6'(bb); assign rf_ra[(bb*6+c)*2+:2]=cmd[7:6];
  end
  wire [8:0] dc=rf_rd_cmd[5*9+:9];
  assign rf_rv[bb*6+5]=dc[8]&&dc[5:3]==3'(bb/8); assign rf_ra[(bb*6+5)*2+:2]=dc[7:6];
  reg wv; reg [1:0] wa; reg [31:0] wd; reg [2:0] nw; integer w;
  always @*begin
   wv=0;wa=0;wd=0;nw=0;
   for(w=0;w<4;w=w+1)if(rf_wv[w]&&rf_wa[w*8+:6]==6'(bb))begin wv=1;wa=rf_wa[w*8+6+:2];wd=rf_wd[w*32+:32];nw=nw+3'd1;end
  end
  assign rf_wvb[bb]=wv; assign rf_wab[bb*2+:2]=wa; assign rf_wdb[bb*32+:32]=wd; assign rf_wconf[bb]=nw>3'd1;
 end
 ot_hbm_su_static_rf #(.BANKS(64),.READERS(6)) u_rf(.clk_bank(clk_rf),.rst_n(rst_n),.read_v(rf_rv),.read_addr(rf_ra),
  .read_data(rf_q),.read_return(),.write_v(rf_wvb),.write_addr(rf_wab),.write_data(rf_wdb));
 // bank selects ride the read: command sampled at k -> data held k+2..k+3; select registers held the same window
 reg [5:0] bsel1 [0:5]; reg [5:0] bsel2 [0:5]; reg [5:0] bsel3 [0:5];
 integer cc;
 always @(posedge clk_ctl)for(cc=0;cc<6;cc=cc+1)begin
  bsel1[cc]<=rf_rd_cmd[cc*9+:6];bsel2[cc]<=bsel1[cc];bsel3[cc]<=bsel2[cc];
 end
 wire [31:0] rf_word [0:4];
 for(genvar c=0;c<5;c=c+1)begin:g_rfw assign rf_word[c]=rf_q[(bsel3[c]*6+c)*32+:32]; end
 reg [255:0] dsec; integer kk;
 always @*for(kk=0;kk<8;kk=kk+1)dsec[kk*32+:32]=rf_q[((bsel3[5][5:3]*8+kk)*6+5)*32+:32];
 always @(posedge clk_ctl)begin
  rf_bword<={rf_word[3],rf_word[2],rf_word[1],rf_word[0]};
  rf_bcmd<=rf_rd_cmd[0+:36];
  rf_dsec<=dsec;
 end
 // class-5 command must precede the RF drain by exactly one edge
 reg c5_d1;
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)c5_d1<=1'b0; else c5_d1<=rf_rd_cmd[5*9+8];
 wire dbad=(rf_drain_now&&!c5_d1)||(rf_rd_cmd[5*9+8]&&rf_rd_cmd[5*9+:3]!=3'd0);
 // reducer: operand + command registered once (E+1), reducer issue E+2
 reg rc_v; reg [2:0] rc_op; reg [9:0] rc_a,rc_b,rc_d; reg [31:0] rc_tag,rc_x;
 reg [1:0] e_sl; reg e_os; reg [72:8] e_f;
 always @(posedge clk_ctl)begin e_sl<=red_cmd[5:4];e_os<=red_cmd[7];e_f<=red_cmd[72:8];end
 // stage E: the command waits one edge with the slices' operand registers; stage E+1: operand chosen + registered
 reg e_v;
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)e_v<=1'b0; else e_v<=red_cmd[73];
 always @(posedge clk_ctl or negedge rst_n)if(!rst_n)rc_v<=1'b0; else rc_v<=e_v;
 always @(posedge clk_ctl)begin
  rc_op<=e_f[72:70];rc_a<=e_f[69:60];rc_b<=e_f[59:50];rc_d<=e_f[49:40];rc_tag<=e_f[39:8];
  rc_x<=e_os?rf_word[4]:slice_x[e_sl*32+:32];
 end
 wire red_fault;
 ot_hbm_su_reduce_static #(.AW(10)) u_red(.clk(clk_red),.rst_n(rst_n),.cmd_valid(rc_v),.cmd_op(rc_op),.cmd_a(rc_a),
  .cmd_b(rc_b),.cmd_dst(rc_d),.operand_fp32(rc_x),.cmd_tag(rc_tag),.scalar_valid(red_sv),.scalar_tag(red_tag),
  .scalar_fp32(red_x),.scalar_bf16(),.fault(red_fault));
 always @(posedge clk_ctl or negedge rst_n)
  if(!rst_n)fault<=1'b0; else if((|rf_wconf)||dbad||red_fault)fault<=1'b1;
endmodule
`default_nettype wire
