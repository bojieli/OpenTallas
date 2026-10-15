`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen3-8B TP8 two-die split (owner 2026-10-14 06:45 PT), COMPUTE die: the ROM end of the die link (die master
// qfd_d2d_rom = ot_qkvd_rom_end, unchanged) plus its level-face codec, so that the ROM sequencer (qfd_seq_su raw
// stage-step pins), the SU (x3, ea / eq) and the VM (ar) keep exactly the faces they had toward the merged-die
// sequencer.  Contract: results/arch/qwen_split_1014/LINK.md.
//   sd  56 b levels (ROM sequencer -> KV/system die stepper)    -> CTL op 1 event words (ot_qwen_split_lvl_tx)
//   kvd {v, kindk, pos 18, wbase 24} posted pulses (SU)          -> CTL op 2 words (KF-deep queue, overrun = fault)
//   SCTL event words (KV/system die)                           -> ds 187 b / pw 75 b levels + one-cycle pulses
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_split_romlink #(
    parameter integer XS     = 64,
    parameter integer OCR_AR = 64,
    parameter integer RB_RES = 32,
    parameter integer KF     = 4,
    parameter integer MUT    = 0,
    parameter integer W      = 528,
    parameter integer FW     = 548
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          x3_v,
    input  wire [511:0]  x3_d,
    input  wire [10:0]   x3_tag,
    output wire          x3_cr,
    output wire          ar_v,
    output wire [518:0]  ar_d,
    input  wire          ar_cr,
    input  wire          ea_v,
    input  wire          ea_kind,
    input  wire [23:0]   ea_addr,
    output wire          ea_cr,
    output wire          eq_v,
    output wire [511:0]  eq_d,
    input  wire [55:0]   sd,
    input  wire [43:0]   kvd,
    output wire [186:0]  ds,
    output wire [74:0]   pw,
    input  wire          tx_up,
    output wire          tx_v,
    output wire [FW-1:0] tx_flit,
    input  wire          rx_v,
    input  wire [FW-1:0] rx_flit,
    output reg           fault,
    output wire [7:0]    fault_cause
);
    // ---- kvd pulses -> queue; sd levels -> event words; both -> CTL (dc) under the ROM end's dc credits ----
    reg         kv;
    reg  [42:0] kd;
    always @(posedge clk) kd <= kvd[42:0];
    always @(posedge clk or negedge rst_n) if (!rst_n) kv <= 1'b0; else kv <= kvd[43];
    wire        ke, kf_full;
    wire [42:0] kh;
    reg  [7:0]  dcc;                     // dc credits (rom_end DCD = 4)
    wire        dc_cr;
    reg         dcq;
    wire        sv;
    wire [55:0] sdat;
    wire        sfault;
    reg         s_take;                  // SD word accepted into the dc slot this cycle
    // the SD event source sees one credit per free dc slot it may use; KVD has priority
    wire        kpop = !ke && dcc != 8'd0;
    ot_qkvd_fifo #(.RH(1), .W(43), .D(KF)) u_kq (.clk(clk), .rst_n(rst_n), .push(kv), .din(kd), .pop(kpop), .dout(kh),
        .empty(ke), .full(kf_full), .count());
    // SD events wait in a one-word holding register when the slot is taken by a KVD word
    reg         shv;
    reg  [55:0] shd;
    wire        spop = shv && dcc != 8'd0 && !kpop;
    ot_qwen_split_lvl_tx #(.W(56), .PM(56'd0), .C0(1)) u_sd (.clk(clk), .rst_n(rst_n), .face(sd), .v(sv), .d(sdat),
        .cr(s_take), .fault(sfault));
    reg          dv;
    reg  [W-1:0] dd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin shv <= 1'b0; shd <= 56'd0; dcc <= 8'd4; dcq <= 1'b0; dv <= 1'b0; dd <= {W{1'b0}}; s_take <= 1'b0; end
        else begin
            dcq <= dc_cr;
            if (sv) begin shv <= 1'b1; shd <= sdat; end else if (spop) shv <= 1'b0;
            s_take <= spop;
            dv <= kpop || spop;
            if (kpop) dd <= {4'd2, 12'd0, 469'd0, kh};
            else if (spop) dd <= {4'd1, 12'd0, 456'd0, shd};
            dcc <= dcc - ((kpop || spop) ? 8'd1 : 8'd0) + (dcq ? 8'd1 : 8'd0);
        end
    // ---- SCTL (dh) -> ds / pw ----
    wire          dh_v;
    wire [W-1:0]  dh_d;
    wire          dh_cr;
    wire [261:0]  sface;
    ot_qwen_split_lvl_rx #(.W(262), .PM(262'(1) << 261 | 262'(1) << 186 | 262'(1) << 118 | 262'(1) << 42)) u_sc (
        .clk(clk), .rst_n(rst_n), .v(dh_v), .d(dh_d[261:0]), .cr(dh_cr), .face(sface));
    assign {pw, ds} = sface;
    wire       rf;
    ot_qkvd_rom_end #(.XS(XS), .OCR_AR(OCR_AR), .RB_RES(RB_RES), .MUT(MUT)) u_end (
        .clk(clk), .rst_n(rst_n), .x3_v(x3_v), .x3_d(x3_d), .x3_tag(x3_tag), .x3_cr(x3_cr),
        .ar_v(ar_v), .ar_d(ar_d), .ar_cr(ar_cr), .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(ea_cr),
        .eq_v(eq_v), .eq_d(eq_d), .dc_v(dv), .dc_d(dd), .dc_cr(dc_cr), .dh_v(dh_v), .dh_d(dh_d), .dh_cr(dh_cr),
        .tx_up(tx_up), .tx_v(tx_v), .tx_flit(tx_flit), .rx_v(rx_v), .rx_flit(rx_flit), .fault(rf), .fault_cause(fault_cause));
    reg f_kq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin f_kq <= 1'b0; fault <= 1'b0; end
        else begin
            if (kv && kf_full && !kpop) f_kq <= 1'b1;
            if (sv && shv && !spop) f_kq <= 1'b1;
            fault <= rf | f_kq | sfault;
        end
endmodule
