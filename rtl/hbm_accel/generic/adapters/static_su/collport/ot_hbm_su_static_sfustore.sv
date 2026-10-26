`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_su_static_sfustore (H-NETLIST/suport 2026-10-16): the SFU core's gather/KV store (sfus_<q>), the pgslice g_bank
// pattern for the 16 lanes of ot_hgi_sfu_scheduled_engine (sfucore_<q>), without fill or drain. It closes the SFU
// core's vi_re/vi_addr -> vi_q gather read and its kv_we/kv_waddr/kv_wdata writes (SFU_RESULT_AND_OPERAND_SERVICE).
//   Lane n owns pinned bank n (16 x ot_hbm_su_static_pinned_bank, READERS 1, RB 9: 512 words, the real 128x256 SRAM).
//   Element address (the lane's 24-b AW): a[3:0] = lane n (checked), a[15:14] = QID (checked), a[6:4] = 0 and a[23:18] = 0 (checked),
//   row = {a[17:16], a[13:7]} (the pgslice row map).
//   Read  : vi_re/vi_addr sampled at the bank pins at n, SRAM n+1, vi_q registered n+2, consumed by the lane at n+3
//           (the pgslice port-4 latency, FETCH_EXTRA_EDGES 2).
//   Write : kv_we/kv_waddr/kv_wdata sampled at n, commit n+1 (a read sampled at >= n+1 sees it).
//   Clock : the SFU core's clock (die: stream 1.2 GHz); one clk_bank root and one SRAM root per bank.
// No queue, ready or arbitration. FAULT (sticky): address outside the lane's own bank / quarter.
// MUT (bench, must FAIL): 1 vi_q of lane n taken from bank n^1; 2 write row bits swapped.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_sfustore #(parameter integer QID=0, MUT=0)(
 input wire clk, rst_n,
 input wire [15:0] clk_bank,
 input wire [15:0] clk_bank_macro,
 input wire [15:0] vi_re,
 input wire [383:0] vi_addr,
 output wire [511:0] vi_q,
 input wire [15:0] kv_we,
 input wire [383:0] kv_waddr,
 input wire [511:0] kv_wdata,
 output reg fault
);
 wire [15:0] bad;
 wire [511:0] q;
 for(genvar n=0;n<16;n=n+1)begin:g_bank
  wire [23:0] ra=vi_addr[24*n+:24], wa=kv_waddr[24*n+:24];
  wire [8:0] rrow={ra[17:16],ra[13:7]};
  wire [8:0] wrow=(MUT==2)?{wa[13:7],wa[17:16]}:{wa[17:16],wa[13:7]};
  assign bad[n]=(vi_re[n]&&(ra[23:18]!=0||ra[3:0]!=4'(n)||ra[6:4]!=3'd0||ra[15:14]!=2'(QID)))||
                (kv_we[n]&&(wa[23:18]!=0||wa[3:0]!=4'(n)||wa[6:4]!=3'd0||wa[15:14]!=2'(QID)));
  ot_hbm_su_static_pinned_bank #(.READERS(1),.RB(9)) u_bank(.clk(clk_bank[n]),.rst_n(rst_n),.clk_rd(clk_bank[n]),
   .clk_ws(clk_bank[n]),.clk_macro(clk_bank_macro[n]),.read_v(vi_re[n]),.read_addr(rrow),.read_data(q[32*n+:32]),
   .read_return(),.write_v(kv_we[n]),.write_addr(wrow),.write_data(kv_wdata[32*n+:32]));
  assign vi_q[32*n+:32]=(MUT==1)?q[32*(n^1)+:32]:q[32*n+:32];
 end
 reg bad_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin bad_q<=1'b0; fault<=1'b0; end
  else begin bad_q<=|bad; if(bad_q) fault<=1'b1; end
endmodule
`default_nettype wire
