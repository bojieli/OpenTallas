`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// sys-takeover 2026-10-09: qfd_native_collective_binding bench.  Four Qwen ROM dies, each
//   sequencer model (ckd, 0.9 GHz) -> ot_qwen_die_io_xfifo NCOLL=1 sq (546-b {tag32, mode, last, data512}, credits)
//   -> ot_rom_oneshot_die_m (ck, 1.2 GHz; the r21 qfd_io_collective engine, MARGIN form, IB 4, DEPTH 32)
//   -> ot_rom_ucie_link ring to the other three dies
//   -> engine push output -> io_xfifo cq return channel (516-b {err, rank2, last, data512}) -> sequencer (ckd).
// The sequencer holds the 4 initial forward credits and takes more only from i_seq_coll_cr (the xfifo's return-space
// gate); it consumes returned words from a 4-deep landing buffer at a random rate (+CONS percent per ckd edge) and
// returns one o_coll_seq_cr per word consumed.  Vectors as tb_rom_oneshot_allreduce (+VEC part/sum/mode.hex, golden
// tools/hdc_golden.fold).  Every returned word is checked: reduce vs sum.hex, gather vs the sender's word and rank,
// last flag, no err; every fault output must stay 0.  Prints NCOLL_NATIVE PASS / FAIL and the ck cycles used.
// ---------------------------------------------------------------------------
// Clocks come from the C++ harness (physical/sys_takeover/coll_native_harness.cpp): ck 1.2 GHz, ckd 0.9 GHz, unrelated
// phase; reset releases after 20 ckd edges.
module tb_qfd_coll_native #(parameter integer CQ_AD = 64, parameter integer CR = 4, parameter integer ENG_IB = 4, parameter integer LCR = 4) (input wire ck, input wire ckd);
    localparam integer N = 4, LANES = 16, FW = 512, TAGW = 32, RB = 2, PW = FW + 2 + TAGW, MAXW = 1 << 14;
    localparam integer WSQ = 546, WCQ = 516;
    reg [4:0] rcnt = 0;
    wire rst_n = (rcnt == 5'd20);
    always @(posedge ckd) if (!rst_n) rcnt <= rcnt + 1'b1;
    // the blocks release their own reset synchronisers after rst_n; the sequencer starts 16 ckd edges later
    reg [4:0] scnt = 0;
    wire run = (scnt == 5'd16);
    always @(posedge ckd) if (rst_n && !run) scnt <= scnt + 1'b1;
    reg [FW-1:0] part [0:MAXW-1];
    reg [FW-1:0] sum  [0:MAXW-1];
    reg          mode [0:4095];
    integer NMSG, WORDS, GAP, CONS, SEED;
    string dir;
    integer cyc = 0, bad = 0, done_n = 0, words_out = 0, first = -1, lastc = 0;
    always @(posedge ck) cyc <= cyc + 1;

    wire [N-1:0] txv;
    wire [N*PW-1:0] txr;
    wire [N*N-1:0] txrdy, crin, crout, rxv;
    wire [N*N*PW-1:0] rxr;
    wire [N-1:0] fck, fckd, fdie;

    function [31:0] xs(input [31:0] v0);
        reg [31:0] v;
        begin v = v0 ^ (v0 << 13); v = v ^ (v >> 17); xs = v ^ (v << 5); end
    endfunction

    genvar g, t;
    generate for (g = 0; g < N; g = g + 1) begin : g_die
        // ---------------- sequencer model (ckd) ----------------
        integer m = 0, w = 0, fcr = CR;
        reg [31:0] rnd = 32'h9e3779b9 * (g + 1);
        wire s_v, s_cr;
        wire [WSQ-1:0] s_d;
        reg go = 0;
        wire send = go && fcr > 0 && m < NMSG;
        assign s_v = send;
        assign s_d = {m[TAGW-1:0], mode[m], (w == WORDS - 1), part[(m*N + g)*WORDS + w]};
        always @(posedge ckd) begin
            rnd <= xs(rnd ^ SEED);
            go <= run && ((rnd % 100) >= GAP);
            if (send) begin
                if (first < 0) first = cyc;
                if (w == WORDS - 1) begin w <= 0; m <= m + 1; end else w <= w + 1;
            end
            fcr <= fcr - (send ? 1 : 0) + (s_cr ? 1 : 0);
        end
        // return landing buffer (4 = the cq channel's downstream credits) and checker
        wire r_v; wire [WCQ-1:0] r_d;
        reg [WCQ-1:0] lb [0:LCR-1];
        integer lw = 0, lr = 0, rm = 0, rk = 0, per;
        reg r_cr = 0;
        reg [FW-1:0] exp;
        reg [WCQ-1:0] hd;
        always @(posedge ckd) begin
            r_cr <= 1'b0;
            if (r_v) begin
                if (lw - lr >= LCR) begin bad = bad + 1; $display("LANDING OVERFLOW die=%0d", g); end
                lb[lw % LCR] <= r_d; lw <= lw + 1;
            end
            if (lr < lw && (xs(rnd + 77) % 100) < CONS) begin
                hd = lb[lr % LCR];
                per = mode[rm] ? N * WORDS : WORDS;
                exp = mode[rm] ? part[(rm*N + rk % N)*WORDS + rk / N] : sum[rm*WORDS + rk];
                if (hd[FW-1:0] !== exp) begin bad = bad + 1; if (bad < 6) $display("MISMATCH die=%0d msg=%0d word=%0d got=%h exp=%h", g, rm, rk, hd[63:0], exp[63:0]); end
                if (mode[rm] && hd[FW+2:FW+1] != rk % N) begin bad = bad + 1; if (bad < 6) $display("RANK die=%0d msg=%0d", g, rm); end
                if (hd[FW] != (rk == per - 1)) begin bad = bad + 1; if (bad < 6) $display("LAST die=%0d msg=%0d word=%0d", g, rm, rk); end
                if (hd[FW+3]) begin bad = bad + 1; if (bad < 6) $display("ERR die=%0d msg=%0d", g, rm); end
                words_out = words_out + 1; lastc = cyc;
                if (rk == per - 1) begin rk = 0; rm = rm + 1; if (rm == NMSG) done_n = done_n + 1; end else rk = rk + 1;
                lr <= lr + 1; r_cr <= 1'b1;
            end
        end
        // ---------------- io_xfifo (NCOLL) ----------------
        wire e_v, e_cr, o_v, o_last, o_err;
        wire [WSQ-1:0] e_d;
        wire [FW-1:0] o_data;
        wire [RB-1:0] o_rank;
        wire [2:0] fcode;
        ot_qwen_die_io_xfifo #(.WSQ(WSQ), .NCOLL(1), .WCQ(WCQ), .N(N), .MB(FW + 1), .CQ_AD(CQ_AD), .CR(CR), .ENG_IB(ENG_IB), .LCR(LCR)) u_x (
            .ck(ck), .cku(ck), .cks(ck), .ckd(ckd), .rst_n(rst_n),
            .i_ucie_tx_v(1'b0), .i_ucie_tx(1024'b0), .i_ucie_tx_cr(), .o_ucie_tx_v(), .o_ucie_tx(), .o_ucie_tx_cr(1'b0),
            .i_ucie_rx_v(1'b0), .i_ucie_rx(1024'b0), .i_ucie_rx_cr(), .o_ucie_rx_v(), .o_ucie_rx(), .o_ucie_rx_cr(1'b0),
            .i_serdes_tx_v(1'b0), .i_serdes_tx(1024'b0), .i_serdes_tx_cr(), .o_serdes_tx_v(), .o_serdes_tx(), .o_serdes_tx_cr(1'b0),
            .i_serdes_rx_v(1'b0), .i_serdes_rx(1024'b0), .i_serdes_rx_cr(), .o_serdes_rx_v(), .o_serdes_rx(), .o_serdes_rx_cr(1'b0),
            .i_seq_coll_v(s_v), .i_seq_coll(s_d), .i_seq_coll_cr(s_cr),
            .o_seq_coll_v(e_v), .o_seq_coll(e_d), .o_seq_coll_cr(e_cr),
            .i_coll_seq_v(o_v), .i_coll_seq({o_err, o_rank, o_last, o_data}),
            .o_coll_seq_v(r_v), .o_coll_seq(r_d), .o_coll_seq_cr(r_cr),
            .fault_ck(fck[g]), .fault_cku(), .fault_cks(), .fault_ckd(fckd[g]));
        // ---------------- collective engine (ck) ----------------
        ot_rom_oneshot_die_m #(.N(N), .RANK(g), .LANES(LANES), .TAGW(TAGW), .DEPTH(32), .IB(ENG_IB)) u_die (
            .clk(ck), .rst_n(rst_n),
            .in_valid(e_v), .in_cr(e_cr), .in_data(e_d[FW-1:0]), .in_last(e_d[FW]), .in_mode(e_d[FW+1]),
            .in_tag(e_d[FW+2 +: TAGW]),
            .tx_valid(txv[g]), .tx_rec(txr[g*PW +: PW]), .tx_ready(txrdy[g*N +: N]), .cr_in(crin[g*N +: N]),
            .rx_valid(rxv[g*N +: N]), .rx_rec(rxr[g*N*PW +: N*PW]), .cr_out(crout[g*N +: N]),
            .out_valid(o_v), .out_data(o_data), .out_last(o_last), .out_rank(o_rank), .out_err(o_err),
            .fault(fdie[g]), .fault_code(fcode));
        for (t = 0; t < N; t = t + 1) begin : g_to
            if (t == g) begin : g_self
                assign txrdy[g*N + t] = 1'b1; assign crin[g*N + t] = 1'b0;
                assign rxv[g*N + t] = 1'b0; assign rxr[(g*N + t)*PW +: PW] = {PW{1'b0}};
            end else begin : g_link
                ot_rom_ucie_link #(.PW(PW), .LAT(12), .FLIT_BYTES(FW / 8), .BPC_NUM(3600), .BPC_DEN(1)) u_link (
                    .clk(ck), .rst_n(rst_n), .in_valid(txv[g]), .in_rec(txr[g*PW +: PW]), .in_ready(txrdy[g*N + t]),
                    .out_valid(rxv[t*N + g]), .out_rec(rxr[(t*N + g)*PW +: PW]),
                    .cr_in(crout[t*N + g]), .cr_out(crin[g*N + t]));
            end
        end
    end endgenerate

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("NMSG=%d", NMSG)) NMSG = 16;
        if (!$value$plusargs("WORDS=%d", WORDS)) WORDS = 8;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        if (!$value$plusargs("CONS=%d", CONS)) CONS = 100;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/sum.hex"}, sum);
        $readmemh({dir, "/mode.hex"}, mode);
    end
    always @(posedge ck) begin
        if (done_n == N || cyc > 200000 + NMSG * WORDS * 400) begin
            $display("NCOLL_NATIVE msgs=%0d words=%0d gap=%0d cons=%0d mismatches=%0d words_out=%0d done=%0d fault_ck=%b fault_ckd=%b fault_die=%b first=%0d last=%0d",
                     NMSG, WORDS, GAP, CONS, bad, words_out, done_n, fck, fckd, fdie, first, lastc);
            if (bad == 0 && done_n == N && fck == 0 && fckd == 0 && fdie == 0) $display("NCOLL_NATIVE PASS cycles=%0d", lastc - first);
            else $display("NCOLL_NATIVE FAIL");
            $finish;
        end
    end
endmodule
