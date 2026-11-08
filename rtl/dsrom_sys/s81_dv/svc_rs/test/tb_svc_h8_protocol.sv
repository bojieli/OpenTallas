`timescale 1ns/1ps
// Protocol-only unit test of real dsdv_svc_att decoder. Arithmetic engine is
// isolated below; numeric engine equivalence is checked by h8_engine_equiv.
module tb_svc_h8_protocol;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,qv=0;reg[511:0] q=0;
 integer phase=0,mut=0,errs=0;
 wire [1:0] st,rv; wire [3:0] kind[0:1];
 integer heads[0:2][0:1],rows[0:2][0:1];
 genvar g;
 generate for(g=0;g<2;g++)begin:d
 dsdv_svc_att #(.H(8)) u(.clk(clk),.rst_n(rst_n),.sid(4'(g)),.tile(g==0?4'd0:4'd8),.gd(8'd0),.pvs(8'd0),.root(1'b0),
  .q_v(qv),.q_d(q),.hw_v(1'b0),.hw_d(291'd0),.qrq(),.qrk(2'd0),.qwd(2'd0),.qrv(2'd0),.qr_data(512'd0),.qr_tag(34'd0),.qr_beat(8'd0),
  .l_v(),.l_d(),.pv_ov(),.pv_od(),.sm_st(st[g]),.sm_kind(kind[g]),.sm_jid(),.sm_rv(rv[g]),.sm_rp(),.sm_rj(),.sm_rd(),
  .go_o(),.tjob_o(),.done(),.tagj(),.hcr(),.hack(),.fault(),.fault_code(),.pio_o(),.pvo_o(),.jc_o(),.st_o(),.hb_o());
 always @(posedge clk)if(rst_n)begin
  if(st[g])heads[phase][g]++;
  if(rv[g])rows[phase][g]++;
 end
 end endgenerate
 task automatic word(input [511:0] w);@(negedge clk);qv=1;q=w;endtask
 task automatic gap;@(negedge clk);qv=0;q=0;repeat(4)@(negedge clk);endtask
 task automatic sm(input integer k);
  reg[511:0] h;h=0;h[511:508]=9;h[503]=1;h[491:480]=2;h[4:1]=4'(k);h[0]=1;
  word(h);word(512'h123);word(512'h456);gap();
 endtask
 initial begin
  reg[511:0] h;
  void'($value$plusargs("mut=%d",mut));
  for(integer p=0;p<3;p++)for(integer g=0;g<2;g++)begin heads[p][g]=0;rows[p][g]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(integer p=0;p<2;p++)begin
   phase=p;h=0;h[511:508]=1;h[503]=1;h[448]=1'(mut==1?1-p:p);word(h);gap();sm(4);
  end
  phase=2;if(mut!=2)sm(5);
  for(integer p=0;p<3;p++)for(integer g=0;g<2;g++)begin
   if(heads[p][g]!=(p==2||p==g?1:0)||rows[p][g]!=(p==2||p==g?2:0))errs++;
  end
  $display("H8_PROTOCOL mut=%0d errs=%0d heads=%0d/%0d,%0d/%0d,%0d/%0d",mut,errs,heads[0][0],heads[0][1],heads[1][0],heads[1][1],heads[2][0],heads[2][1]);
  if(errs==0)$display("H8_PROTOCOL PASS");else $display("H8_PROTOCOL FAIL");$finish;
 end
endmodule
module ot_hdc_v41x_attn_s #(
    parameter integer H = 16,          // heads per die
    parameter integer D = 512,         // head_dim
    parameter integer TD = 64,         // tile width (dims per q.k beat / rows per p.v block)
    parameter integer NL = 4,          // row lanes (rows per cycle)
    parameter integer TROWS = 640,     // staging buffer rows
    parameter integer SC_CRED = 64,     // score-beat credits; 0 = static scores (SVC-PV3): no credit, sc_cr ignored --
                                        //   the consumer takes every beat the cycle it is produced (valid-only)
    parameter integer PV_CRED = 64,    // pv-beat credits; 0 = static P.V (SVC-PV2): no credit, pv_cr ignored -- the
                                       //   consumer's buffer and drain are compiled and fault-checked there
    parameter bit SRAM_MACRO = 0,      // ASAP7 packed-row staging macro boundary
    parameter integer PWORDS = 1,      // probability words per p handshake (1 or 2)
    parameter integer ILV = 0,         // 1: position-interleaved verify mode (see the controller)
    parameter integer REPL = 0,        // 1 (needs ILV = 1): per-tile copies of the transposer read/write indices,
                                       //   the E-register q.k/p.v select and registered pad flags, and a 2-entry
                                       //   p-word input FIFO so q_ready/p_ready come from registers only;
                                       // 2: as 1, plus one register stage between every issue/fill decision and
                                       //   its per-tile copies and the staging read (q.k and p.v beats both enter
                                       //   the E register one cycle later; guards one cycle longer)
    parameter integer PHYS = 0,        // 1: physical characterisation only (transposers/merges stubbed)
    parameter integer NSTAGE = 1,      // 2 (needs ILV = 1): two staging buffers, the front job writes and reads
                                       //   one while the back job fills from the other (per-position row lists)
    parameter integer FPL = 3,         // binary32 add latency (7: 1.2 GHz streaming domain)
    parameter integer FML = 3,         // tile product latency
    parameter integer NBANKP = 0,      // stationary banks; 0 = as built (3 / 4 with PWORDS 2, +1 with ILV).  The
                                       // bank lifetime grows with the skew (6 FPL): at FPL 7 more banks keep p.v
                                       // at one beat per cycle (see the W11 stream record)
    parameter integer TILE_S = 0,      // 1: the head-group tile ot_hdc_v41x_attn_tile_s (same cycles; hardens
                                       //    hierarchically, rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv)
    parameter integer FPLX = 0,        // >0: FP32 add latency of the lane trees and block merges (default FPL)
    parameter integer F12 = 0,         // 1: every FP32 add is the 1.2 GHz f12 unit (LAT 4: ot_hdc_fp32_add_f12_l4,
                                       //    registered operands; LAT 5: ot_hdc_fp32_add_f12_l5x, operand mux in front)
    parameter integer TRX = 0,         // 1 (REPL >= 1): transposers with per-element one-hot read selects and per-row
                                       //    one-hot write enables (ot_hdc_v41x_attn_tr_x; same cycles)
    parameter integer MFAN = 0,        // 1: the block merges with per-head control copies (ot_hdc_v41x_attn_merge_x;
                                       //    +1 cycle on p.v results only)
    parameter integer NARROW = 0,      // 1: block counters (load / fill / issue / filled / count) BKW bits wide, not
                                       //    16 (values never exceed NBLKMAX; same values and cycles for T <= TROWS):
                                       //    shortens the controller's compare/increment loops for 1.2 GHz
    // SVC4 (LEAD2-S81, 10-19): landed engine.  TEXT 1 = the NT tiles are NOT instantiated here: tile t's input bundle
    // leaves on tx_i[t] and its output bundle returns on tx_o[t] (the landed parent dsdv_svc_attw_f_lp puts every tile
    // in its own clock region with LANDED crossings both ways).  TLX = edges the tile round trip takes beyond TLAT (the
    // compiler re-schedule: tags / lane trees wait TLX more); TXD = register stages on the returning bundle inside this
    // module (the flat lockstep reference of a landed parent: TXD = TLX; a landed build: TXD = 0).  Defaults = as built.
    parameter integer TEXT = 0,
    parameter integer TLX = 0,
    parameter integer TXD = 0,
    // ATTN1 (DRIVE-S81-ATTN1, 10-20, opt-in): NTP = PHYSICAL engine tiles (0 = NT = NL * D / TD, as built).  NTP < NT
    // (needs D = TD, i.e. S = 1, and NT % NTP == 0) time-multiplexes V = NT / NTP virtual tiles on each physical tile:
    // physical tile p runs virtual tiles p V + k in sub-beat k (k = 0 .. V - 1, consecutive cycles), so the controller
    // issues one beat (q.k or p.v) every V cycles, every stationary-bank guard grows by V (the sub-beats read up to V
    // cycles after the old E register), and the tile outputs are re-assembled into the NT-tile beat (lane values,
    // merges, sc_* / pv_* ABI and the merge order unchanged: bit-exact, only the cycles move).  Tile input +1 register
    // (the sub-beat shift chain), tile output re-assembly +V: tags wait TLAT + TLX + V + 1.
    parameter integer NTP = 0,
    parameter integer NMUT = 0,        // ATTN1 bench negative controls (V > 1 only): 1 = sub-beat re-assembly order
                                       //   reversed, 2 = issue slot free one cycle early (V - 1), 3 = no guard growth
    // derived (do not override): tile bundle widths, same formulas as the NBANK / BW localparams below
    parameter integer TX_NB = (NBANKP > 0) ? NBANKP : (((PWORDS >= 2) ? 4 : 3) + ((ILV != 0) ? 1 : 0)),
    parameter integer TX_BW = (TX_NB > 4) ? $clog2(TX_NB) : 2,
    parameter integer TXI = 1 + 1 + TX_BW + 8 + PWORDS*TD*16 + 1 + 1 + TX_BW + TD*18,  // {ib, ibank, iv, ld_w2v, ld_w, ld_grp, ld_bank, ld_mode, ld_v}
    parameter integer TXO = 1 + H*32 + H,                                               // {oflt, oy, ov}
    parameter integer TX_NT = (NTP > 0) ? NTP : NL*(D/TD)                               // tile bundles (physical tiles)
) (
    input  wire                   clk,
    input  wire                   rst_n,
    // job
    input  wire                   job_v,
    input  wire [15:0]            job_t,
    output wire                   job_ready,
    // q
    input  wire                   q_v,
    input  wire [D*16-1:0]        q_w,
    output wire                   q_ready,
    // kv rows
    input  wire                   kv_v,
    input  wire [NL-1:0]          kv_m,
    input  wire [NL*(D/32)*265-1:0] kv_w,
    output wire                   kv_ready,
    // scores
    output reg                    sc_v,
    output reg  [15:0]            sc_row,
    output reg  [NL-1:0]          sc_m,
    output reg  [NL*H*32-1:0]     sc_y,
    output reg  [NL*H-1:0]        sc_f,
    input  wire                   sc_cr,
    // probabilities
    input  wire                   p_v,
    input  wire [PWORDS*TD*16-1:0] p_w,
    output wire                   p_ready,
    // pv
    output reg                    pv_v,
    output reg  [7:0]             pv_c,
    output reg  [NL*(D/TD)*H*32-1:0] pv_y,
    output reg  [NL*(D/TD)*H-1:0] pv_f,
    input  wire                   pv_cr,
    // bench visibility
    output wire                   qk_iss,
    output wire                   pv_iss,
    // SVC4 landed engine (TEXT 1): tile bundles; unused (tx_i 0, tx_o ignored) when TEXT 0
    output wire [TX_NT*TXI-1:0] tx_i,
    input  wire [TX_NT*TXO-1:0] tx_o
);
assign job_ready=1;assign q_ready=1;assign kv_ready=1;assign p_ready=1;
assign qk_iss=0;assign pv_iss=0;assign tx_i=0;
always_comb begin sc_v=0;sc_row=0;sc_m=0;sc_y=0;sc_f=0;pv_v=0;pv_c=0;pv_y=0;pv_f=0;end
endmodule
