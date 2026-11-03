`timescale 1ns/1ps
// SOURCE PREP ONLY: active bank4 public ROM/converter/return boundary.
// This uses the actual macro's VIAMAP content-context ABI. It does not instantiate
// or retarget qfd_tile_* ROM_TILE identity. Every fresh process must authenticate
// original tile/bank/column/path/fullmask SHA in its immutable context manifest.
// It preserves selected RPH3/REGROOT3/ARELAY2/CAP2=1/CAPX2/RQR1 stages.
module native_head_rom_return_cut(
 input wire clk,rst_n,wrom_re,input wire[17:0]wrom_addr,
 output wire[1023:0]wrom_q
);
 // Exact selected ce0 and first request relay. ROM_ARELAY's second request
 // stage is the real per-macro MPR inside ot_qwen_romleaf_logic below.
 wire[4:0]ce0={5{wrom_re}}&(5'b00001<<wrom_addr[17:12]);
 reg[4:0]rq_ce_n1;reg[11:0]rq_ad_n1;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)rq_ce_n1<=0;else rq_ce_n1<=ce0;
 always @(posedge clk)rq_ad_n1<=wrom_addr[11:0];
 wire any_leaf;
 ot_qwen_a0_leaf_any_local #(.BANKS(5)) any_local(.ce_i(rq_ce_n1),.any_o(any_leaf));
 wire[1023:0]bank4_word;
 for(genvar col=0;col<2;col=col+1)begin:columns
  // Actual selected per-ROM leaf reset relay, unchanged data stages.
  reg rst_leaf;
  always @(posedge clk or negedge rst_n)if(!rst_n)rst_leaf<=0;else rst_leaf<=1;
  wire[12:0]req_m;wire[265:0]rd;
  ot_qwen_romleaf_logic native_logic(.clk(clk),.rst_n(rst_leaf),
   .ce_d(rq_ce_n1[4]),.any_d(any_leaf),.ad_d(rq_ad_n1),
   .req_m(req_m),.rd(rd[255:0]),.r_q(bank4_word[512*col+:512]));
  // VIAMAP is the unmodified public macro parameter, fixed at elaboration.
  // Fresh-process CWD contains these immutable generic component input names.
  // No selected INSTANCE name, ROM_TILE guard, mask bytes or DUT port is changed.
  ot_rom_4096x266_m8 #(.VIAMAP(col==0?"mask_c0.viamap.hex":"mask_c1.viamap.hex")) native_macro(
   .clk(clk),.ce_in(req_m[12]),.addr_in(req_m[11:0]),.rd_out(rd));
 end
 // Bank4 is north (SB3). Under the guarded bank4-only request domain, all
 // other bank outputs are unselected0. These are the existing RQR column regs.
 reg[1023:0]gn;
 always @(posedge clk)begin gn[511:0]<=bank4_word[511:0];gn[1023:512]<=bank4_word[1023:512];end
 assign wrom_q=gn;
 always @(posedge clk)if(rst_n&&wrom_re&&wrom_addr[17:12]!=6'd4)
  $fatal(1,"ROMreturn component only accepts genuine HEAD bank4 requests");
endmodule
