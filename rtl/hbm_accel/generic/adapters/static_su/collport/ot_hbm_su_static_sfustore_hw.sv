`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_su_static_sfustore_hw (RBH-SFUS 10-18): the hard tile of sfus_<q> (x4, one view for all d4g quadrants).
// Same function as ot_hbm_su_static_sfustore (16 lanes, lane n owns ot_hbm_su_static_pinned_bank n, READERS 1, RB 9,
// the real 128x256 SRAM; row = {a[17:16], a[13:7]}; vi_q n+2; write commit n+1; sticky FAULT on an address outside
// the lane's bank / quarter), in hard-tile form:
//   ports : per-lane l<NN>_* (lane n = bits [24n+:24] / [32n+:32] / [n] of the soft master's vi_addr / vi_q /
//           kv_waddr / kv_wdata / vi_re / kv_we) so each lane's pins sit on the S face over its own SRAM column;
//   qid   : the quarter id is an identity strap pin (qid[1:0], pin-registered) instead of the QID parameter, so ONE
//           hardened view serves sfus_SW/SE/NW/NE (straps 0/1/2/3);
//   clock : ONE root -- every bank register and every SRAM clock pin runs on clk (no clk_bank / clk_bank_macro pins);
//   reset : rst_n drives only ot_rst_relay (4 regions = the 4 SRAM columns; async assert, release +3 clk edges);
//   pins  : flop-first -- the identity-check bits {re/we, a[23:18], a[15:14], a[6:4], a[3:0]} are pin registered
//           before the compare (the bank pin-registers row/data/valid), so FAULT rises one edge later (n+2, was n+1).
//   r2 (HBM-SFUHW 10-18; r1 route NEEDS_RTL TT -102.29 / FF -42.33): (a) read capture beside each SRAM (lane bank
//           ot_hbm_su_sfustore_hw_bank = pinned_bank READERS 1 + rd_cap after the word mux; shared pinned_bank untouched):
//           vi_q n+3 (was n+2) -- COMPILER: the sfus read latency is +1 edge; write commit n+1 unchanged;
//           (b) qid fanout replicated per lane (qid_l, one pair beside each lane's check flops) and the identity
//           compare registered per lane (bad_l) -- fault timing unchanged (n+2), the 16-lane OR moves to fault's D.
// No queue, ready or arbitration.  MUT (bench, must FAIL): 1 vi_q of lane n from bank n^1; 2 write row bits swapped;
// 3 lane n's check reads lane n^1's registered check bits; 4 read capture dropped (vi_q n+2); 5 lanes 8..15 compare
// against a bit-swapped qid replica.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_sfustore_hw #(parameter integer MUT=0)(
 input wire clk, rst_n,
 input wire [1:0] qid,
 input wire l00_vi_re, input wire [23:0] l00_vi_addr, output wire [31:0] l00_vi_q,
 input wire l00_kv_we, input wire [23:0] l00_kv_waddr, input wire [31:0] l00_kv_wdata,
 input wire l01_vi_re, input wire [23:0] l01_vi_addr, output wire [31:0] l01_vi_q,
 input wire l01_kv_we, input wire [23:0] l01_kv_waddr, input wire [31:0] l01_kv_wdata,
 input wire l02_vi_re, input wire [23:0] l02_vi_addr, output wire [31:0] l02_vi_q,
 input wire l02_kv_we, input wire [23:0] l02_kv_waddr, input wire [31:0] l02_kv_wdata,
 input wire l03_vi_re, input wire [23:0] l03_vi_addr, output wire [31:0] l03_vi_q,
 input wire l03_kv_we, input wire [23:0] l03_kv_waddr, input wire [31:0] l03_kv_wdata,
 input wire l04_vi_re, input wire [23:0] l04_vi_addr, output wire [31:0] l04_vi_q,
 input wire l04_kv_we, input wire [23:0] l04_kv_waddr, input wire [31:0] l04_kv_wdata,
 input wire l05_vi_re, input wire [23:0] l05_vi_addr, output wire [31:0] l05_vi_q,
 input wire l05_kv_we, input wire [23:0] l05_kv_waddr, input wire [31:0] l05_kv_wdata,
 input wire l06_vi_re, input wire [23:0] l06_vi_addr, output wire [31:0] l06_vi_q,
 input wire l06_kv_we, input wire [23:0] l06_kv_waddr, input wire [31:0] l06_kv_wdata,
 input wire l07_vi_re, input wire [23:0] l07_vi_addr, output wire [31:0] l07_vi_q,
 input wire l07_kv_we, input wire [23:0] l07_kv_waddr, input wire [31:0] l07_kv_wdata,
 input wire l08_vi_re, input wire [23:0] l08_vi_addr, output wire [31:0] l08_vi_q,
 input wire l08_kv_we, input wire [23:0] l08_kv_waddr, input wire [31:0] l08_kv_wdata,
 input wire l09_vi_re, input wire [23:0] l09_vi_addr, output wire [31:0] l09_vi_q,
 input wire l09_kv_we, input wire [23:0] l09_kv_waddr, input wire [31:0] l09_kv_wdata,
 input wire l10_vi_re, input wire [23:0] l10_vi_addr, output wire [31:0] l10_vi_q,
 input wire l10_kv_we, input wire [23:0] l10_kv_waddr, input wire [31:0] l10_kv_wdata,
 input wire l11_vi_re, input wire [23:0] l11_vi_addr, output wire [31:0] l11_vi_q,
 input wire l11_kv_we, input wire [23:0] l11_kv_waddr, input wire [31:0] l11_kv_wdata,
 input wire l12_vi_re, input wire [23:0] l12_vi_addr, output wire [31:0] l12_vi_q,
 input wire l12_kv_we, input wire [23:0] l12_kv_waddr, input wire [31:0] l12_kv_wdata,
 input wire l13_vi_re, input wire [23:0] l13_vi_addr, output wire [31:0] l13_vi_q,
 input wire l13_kv_we, input wire [23:0] l13_kv_waddr, input wire [31:0] l13_kv_wdata,
 input wire l14_vi_re, input wire [23:0] l14_vi_addr, output wire [31:0] l14_vi_q,
 input wire l14_kv_we, input wire [23:0] l14_kv_waddr, input wire [31:0] l14_kv_wdata,
 input wire l15_vi_re, input wire [23:0] l15_vi_addr, output wire [31:0] l15_vi_q,
 input wire l15_kv_we, input wire [23:0] l15_kv_waddr, input wire [31:0] l15_kv_wdata,
 output reg fault
);
 wire [15:0] vi_re={l15_vi_re,l14_vi_re,l13_vi_re,l12_vi_re,l11_vi_re,l10_vi_re,l09_vi_re,l08_vi_re,l07_vi_re,l06_vi_re,l05_vi_re,l04_vi_re,l03_vi_re,l02_vi_re,l01_vi_re,l00_vi_re};
 wire [15:0] kv_we={l15_kv_we,l14_kv_we,l13_kv_we,l12_kv_we,l11_kv_we,l10_kv_we,l09_kv_we,l08_kv_we,l07_kv_we,l06_kv_we,l05_kv_we,l04_kv_we,l03_kv_we,l02_kv_we,l01_kv_we,l00_kv_we};
 wire [383:0] vi_addr={l15_vi_addr,l14_vi_addr,l13_vi_addr,l12_vi_addr,l11_vi_addr,l10_vi_addr,l09_vi_addr,l08_vi_addr,l07_vi_addr,l06_vi_addr,l05_vi_addr,l04_vi_addr,l03_vi_addr,l02_vi_addr,l01_vi_addr,l00_vi_addr};
 wire [383:0] kv_waddr={l15_kv_waddr,l14_kv_waddr,l13_kv_waddr,l12_kv_waddr,l11_kv_waddr,l10_kv_waddr,l09_kv_waddr,l08_kv_waddr,l07_kv_waddr,l06_kv_waddr,l05_kv_waddr,l04_kv_waddr,l03_kv_waddr,l02_kv_waddr,l01_kv_waddr,l00_kv_waddr};
 wire [511:0] kv_wdata={l15_kv_wdata,l14_kv_wdata,l13_kv_wdata,l12_kv_wdata,l11_kv_wdata,l10_kv_wdata,l09_kv_wdata,l08_kv_wdata,l07_kv_wdata,l06_kv_wdata,l05_kv_wdata,l04_kv_wdata,l03_kv_wdata,l02_kv_wdata,l01_kv_wdata,l00_kv_wdata};
 wire [511:0] q, vi_q;
 assign l00_vi_q=vi_q[31:0];
 assign l01_vi_q=vi_q[63:32];
 assign l02_vi_q=vi_q[95:64];
 assign l03_vi_q=vi_q[127:96];
 assign l04_vi_q=vi_q[159:128];
 assign l05_vi_q=vi_q[191:160];
 assign l06_vi_q=vi_q[223:192];
 assign l07_vi_q=vi_q[255:224];
 assign l08_vi_q=vi_q[287:256];
 assign l09_vi_q=vi_q[319:288];
 assign l10_vi_q=vi_q[351:320];
 assign l11_vi_q=vi_q[383:352];
 assign l12_vi_q=vi_q[415:384];
 assign l13_vi_q=vi_q[447:416];
 assign l14_vi_q=vi_q[479:448];
 assign l15_vi_q=vi_q[511:480];
 wire [3:0] rst_r;
 ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_r));
 reg [1:0] qid_q;                       // identity strap, registered at its pin (no reset: a constant)
 always @(posedge clk) qid_q<=qid;
 wire [16*16-1:0] chk_r, chk_w;         // per lane {valid, a[23:18], a[15:14], a[6:4], a[3:0]} at the pin
 wire [15:0] bad;
 reg [15:0] bad_l;                      // per-lane registered identity compare (replaces the single bad_q)
 for(genvar n=0;n<16;n=n+1)begin:g_bank
  wire [23:0] ra=vi_addr[24*n+:24], wa=kv_waddr[24*n+:24];
  wire [8:0] rrow={ra[17:16],ra[13:7]};
  wire [8:0] wrow=(MUT==2)?{wa[13:7],wa[17:16]}:{wa[17:16],wa[13:7]};
  reg re_q,we_q; reg [14:0] ra_q,wa_q;
  always @(posedge clk or negedge rst_r[n/4])
   if(!rst_r[n/4])begin re_q<=1'b0; we_q<=1'b0; end
   else begin re_q<=vi_re[n]; we_q<=kv_we[n]; end
  always @(posedge clk)begin ra_q<={ra[23:18],ra[15:14],ra[6:4],ra[3:0]}; wa_q<={wa[23:18],wa[15:14],wa[6:4],wa[3:0]}; end
  assign chk_r[16*n+:16]={re_q,ra_q}; assign chk_w[16*n+:16]={we_q,wa_q};
  wire [15:0] cr=(MUT==3)?chk_r[16*(n^1)+:16]:chk_r[16*n+:16];
  wire [15:0] cw=(MUT==3)?chk_w[16*(n^1)+:16]:chk_w[16*n+:16];
  reg [1:0] qid_l;                      // per-lane qid replica (static strap; settles 2 edges after power-up)
  always @(posedge clk) qid_l<=(MUT==5&&n>=8)?{qid_q[0],qid_q[1]}:qid_q;
  assign bad[n]=(cr[15]&&(cr[14:9]!=0||cr[3:0]!=4'(n)||cr[6:4]!=3'd0||cr[8:7]!=qid_l))||
                (cw[15]&&(cw[14:9]!=0||cw[3:0]!=4'(n)||cw[6:4]!=3'd0||cw[8:7]!=qid_l));
  always @(posedge clk or negedge rst_r[n/4])
   if(!rst_r[n/4]) bad_l[n]<=1'b0; else bad_l[n]<=bad[n];
  ot_hbm_su_sfustore_hw_bank #(.RD_CAP(MUT==4?0:1)) u_bank(.clk(clk),.rst_n(rst_r[n/4]),
   .read_v(vi_re[n]),.read_addr(rrow),.read_data(q[32*n+:32]),
   .write_v(kv_we[n]),.write_addr(wrow),.write_data(kv_wdata[32*n+:32]));
  assign vi_q[32*n+:32]=(MUT==1)?q[32*(n^1)+:32]:q[32*n+:32];
 end
 always @(posedge clk or negedge rst_r[0])
  if(!rst_r[0]) fault<=1'b0;
  else if(|bad_l) fault<=1'b1;
endmodule

// Lane bank of the hard tile: ot_hbm_su_static_pinned_bank #(READERS 1, RB 9, PIN_RST 0, one clock) -- same pin
// registers (sample n, SRAM n+1), same instance names (a_pin/wa_pin/wd_pin/r_pin/w_pin/read_data, u_data =
// ot_hbm_su_static_replicated_bank) -- plus RD_CAP: rd_cap registers the SRAM word-mux output beside the macro's
// W-face rd_out pins, then read_data: read data n+3 (n+2 with RD_CAP 0, the pinned_bank timing).
module ot_hbm_su_sfustore_hw_bank #(parameter integer RD_CAP=1)(
 input wire clk, rst_n,
 input wire read_v, input wire [8:0] read_addr, output reg [31:0] read_data,
 input wire write_v, input wire [8:0] write_addr, input wire [31:0] write_data
);
 reg r_pin, w_pin; reg [8:0] a_pin, wa_pin; reg [31:0] wd_pin;
 wire [31:0] raw_data;
 always @(posedge clk) begin a_pin<=read_addr; wa_pin<=write_addr; wd_pin<=write_data; end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin r_pin<=1'b0; w_pin<=1'b0; end
  else begin r_pin<=read_v; w_pin<=write_v; end
 if(RD_CAP!=0) begin:g_rd_cap
  reg [31:0] rd_cap;
  always @(posedge clk) begin rd_cap<=raw_data; read_data<=rd_cap; end
 end else begin:g_rd_direct
  always @(posedge clk) read_data<=raw_data;
 end
 ot_hbm_su_static_replicated_bank #(.READERS(1),.RB(9),.MUT_COHERENCE(0)) u_data(
  .clk(clk),.clk_macro(clk),.read_v(r_pin),.read_addr(a_pin),.read_data(raw_data),
  .write_v(w_pin),.write_addr(wa_pin),.write_data(wd_pin));
endmodule
`default_nettype wire
