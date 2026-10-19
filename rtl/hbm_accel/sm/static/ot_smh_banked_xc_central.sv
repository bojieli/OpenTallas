`timescale 1ns/1ps
`default_nettype none
// Opt-in APPLICATION hard boundary: central bank selection AND original R/C.
// Model before build: banked calendar adds2 edges; the existing R/C below adds
// its existing1/2 edges, so this wrapper adds ZERO further calendar latency.
// COMMANDALIGN=0 deliberately carries no safe-cache command-only alignment;
// the independent +2 cache/mirror stages require separate priced composition.
// Physical OPEN: inherited word-valid/format/RELOC control fanout requires a
// mapped audit. No delayed-shadow control copies or timing exceptions added.
// XC R/C inventory: two173-bit nonreset payload registers,346 bits total.
// Positive R/C behavior is unchanged; CALMUT is the generic core mutant space,
// separate from legacy field-slice and pipeline-bypass diagnostic mutants.
module ot_smh_banked_xc_central #(
 parameter integer PREL=1,CALMUT=0,COMMANDALIGN=0
)(
 input wire clk,rst_n,
 input wire cfg_we,input wire[10:0]cfg_addr,input wire[255:0]cfg_data,
 input wire start_v,input wire[10:0]start_base,input wire[11:0]start_limit,
 input wire[15:0]start_loops,input wire[4:0]start_ctx,
 output wire cfg0_we,cfg1_we,output wire[9:0]bank_cfg_addr,output wire[255:0]bank_cfg_data,
 output wire[66:0]request0,request1,
 input wire[172:0]row0,row1,input wire[10:0]ok0,ok1,input wire[66:0]token0,token1,
 output wire[108:0]cmd_ext,output wire[63:0]kv_desc,
 output wire active,done,fault
);
 initial if(COMMANDALIGN!=0)$fatal(1,"command-only alignment is not implemented in this wrapper");
 wire[172:0]word0;wire[4:0]wctx;wire[31:0]word_ord;wire cal_v;
 ot_smh_calendar_banked_central #(.W(173),.AW(11),.XW(5),.MUT(CALMUT)) u_core(
  .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_ctx(start_ctx),
  .cfg0_we(cfg0_we),.cfg1_we(cfg1_we),.bank_cfg_addr(bank_cfg_addr),.bank_cfg_data(bank_cfg_data),
  .request0(request0),.request1(request1),.row0(row0),.row1(row1),.ok0(ok0),.ok1(ok1),.token0(token0),.token1(token1),
  .calendar(word0),.calendar_ctx(wctx),.calendar_iter(),.calendar_lastit(),
  .calendar_v(cal_v),.ordinal(word_ord),.active(active),.done(done),.fault(fault),.app_reset_n());
    // RELOC mirror of the svg feed: R stage (+1 edge) = the svg cache-read edge, C stage (+2) = the svg command edge.
    // mrel: the SM mode [183:181] (cmd_ext [100:98]) of every magic word comes from the descriptor (P2: one programme for
    // FP8 / FP4 / BF16 bodies of a shape); fl: the format-launch edge (R edge of the programme's first word) carries
    // {magic, mode} as the svg carries {format_launch, mode[1:0]}.  PREL=0: one stage (absolute words, old envelope).
    localparam [7:0] MAGIC = 8'ha2;
    reg [172:0] word_r, word_c;
    always @(posedge clk) begin
        word_r <= word0;
        if (PREL != 0 && cal_v && wctx[1] && word0[108:101] == MAGIC) word_r[100:98] <= wctx[4:2];
        word_c <= word_r;
        if (PREL != 0 && cal_v && word_ord == 0 && wctx[0]) begin word_c[108:101] <= MAGIC; word_c[100:98] <= wctx[4:2]; end
    end
    wire [172:0] word = (PREL != 0) ? word_c : word_r;
    assign cmd_ext = word[108:0];
    assign kv_desc = word[172:109];
endmodule
`default_nettype wire
