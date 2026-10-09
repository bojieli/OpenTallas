`timescale 1ps/1ps
// emb-hbm 2026-10-08: the REPLACED path's fill latency, for the cycle comparison.  The same SU requester
// (ot_qfd_su_embed_pf, CRD = the ROM root's 4 die-side credits, as r21f) against the r21f embedding ROM
// (ot_qfd_io_embedding_rom: root + 8 columns x 297 taps + bank-parent-protocol banks, PINREG 1) at full size, with the
// r21b relay chains on the die words (emb_a / emb / emb_cr: EA_STG / EQ_STG / CR_STG registered stages each, the SU
// master's IS / OS stations included).  Records go -> fill (core cycles) for tokens at the near, middle and far taps.
module tb_emb_rom_baseline;
    parameter integer EA_STG = 56, EQ_STG = 56, CR_STG = 56, CRD = 4, NTOK = 6;
    localparam integer CKP = 833;
    reg ck = 0, rst_n = 0;
    always begin #(CKP/2) ck = 1; #(CKP - CKP/2) ck = 0; end
    reg go_in = 0, a_src = 0; reg [17:0] tok = 0;
    wire go_out, pend, su_fault;
    wire s_ea_v, s_ea_kind; wire [23:0] s_ea_addr; wire s_ea_cr, s_eq_v; wire [511:0] s_eq_d;
    ot_qfd_su_embed_pf #(.SW(64), .AW(24), .NW(18), .HID(4096), .CRD(CRD), .FI(1)) u_su (.clk(ck), .rst_n(rst_n),
        .go_in(go_in), .a_src(a_src), .tok(tok), .f_in(1'b0), .go_out(go_out), .f_out(), .pend(pend),
        .su_va_re(64'd0), .su_va_addr({64*24{1'b0}}), .su_va_q(), .va_re(), .va_addr(), .va_q({64*32{1'b0}}),
        .ea_v(s_ea_v), .ea_kind(s_ea_kind), .ea_addr(s_ea_addr), .ea_cr(s_ea_cr), .eq_v(s_eq_v), .eq_data(s_eq_d),
        .fault(su_fault));
    wire r_ea_v, r_ea_kind; wire [23:0] r_ea_addr; wire r_ea_cr, r_eq_v; wire [511:0] r_eq_d;
    ot_hdc_delay #(.W(1), .D(EA_STG), .RESET(1)) u_a0 (.clk(ck), .rst_n(rst_n), .d(s_ea_v), .q(r_ea_v));
    ot_hdc_delay #(.W(25), .D(EA_STG)) u_a1 (.clk(ck), .rst_n(rst_n), .d({s_ea_kind, s_ea_addr}), .q({r_ea_kind, r_ea_addr}));
    ot_hdc_delay #(.W(1), .D(CR_STG), .RESET(1)) u_c0 (.clk(ck), .rst_n(rst_n), .d(r_ea_cr), .q(s_ea_cr));
    ot_hdc_delay #(.W(1), .D(EQ_STG), .RESET(1)) u_q0 (.clk(ck), .rst_n(rst_n), .d(r_eq_v), .q(s_eq_v));
    ot_hdc_delay #(.W(512), .D(EQ_STG)) u_q1 (.clk(ck), .rst_n(rst_n), .d(r_eq_d), .q(s_eq_d));
    wire rom_fault;
    ot_qfd_io_embedding_rom #(.NCOL(8), .NTAP(297), .NCODE(2374), .NSCALE(3), .CRD(CRD), .PINREG(1)) u_rom (.clk(ck),
        .rst_n(rst_n), .ea_v(r_ea_v), .ea_kind(r_ea_kind), .ea_addr(r_ea_addr), .ea_cr(r_ea_cr), .eq_v(r_eq_v),
        .eq_data(r_eq_d), .fault(rom_fault));
    reg [17:0] toks [0:7];
    integer t, j; longint cyc = 0, t0;
    always @(posedge ck) cyc = cyc + 1;
    initial begin
        // bank = t >> 6, tap = bank / 8: tap 0, tap 1, ~mid (tap 148), far (tap 296), last token (tap 296)
        toks[0] = 18'd5; toks[1] = 18'd600; toks[2] = 18'd75800; toks[3] = 18'd151700; toks[4] = 18'd151935; toks[5] = 18'd40000;
        repeat (8) @(negedge ck); rst_n = 1; repeat (20) @(negedge ck);
        for (t = 0; t < NTOK; t = t + 1) begin
            tok = toks[t]; a_src = 1; go_in = 1; t0 = cyc; @(negedge ck); go_in = 0; a_src = 0;
            j = 0; while (!go_out && j < 100000) begin @(negedge ck); j = j + 1; end
            $display("ROMLAT token=%0d tap=%0d cycles=%0d", toks[t], (toks[t] >> 6) / 8, cyc - t0);
            repeat (20) @(negedge ck);
        end
        $display("ROM_BASELINE done fault=%0d su_fault=%0d EA_STG=%0d EQ_STG=%0d CR_STG=%0d CRD=%0d", rom_fault, su_fault,
                 EA_STG, EQ_STG, CR_STG, CRD);
        $finish;
    end
endmodule
