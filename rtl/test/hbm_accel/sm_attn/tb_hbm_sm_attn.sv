`timescale 1ns/1ps
`default_nettype none
// tb_hbm_sm_attn: one SM's attention datapath (H-SM-ATT 2026-10-15): KV lines (SM-KV8 / SM-KV4, from the SM's own HBM
// stack: a declared external stimulus at the KV descriptor port) -> ot_hbm_sm_kv_line -> ot_hbm_sm_attn_issue (x store
// = 4 real 128x256 macros) -> 4 x ot_hbm_sm_tcpv_col (the SM's 4 BF16 sub-rows of one x column) -> QK: the column-pair
// tree (ot_gpu_tree N 4, the SM back end's combine) / PV: run nodes.  Results are printed and compared bit for bit by
// tools/hbm_sm_attention/sm_attn_bench.py against tools/hgi_sim/lib.py att_qk / att_pv (csum8) node values.
// plusargs: +LINES=<hex> +NL=<lines> +X=<hex> +NX=<words> +ROWS=<n> +QK=0|1 +KV4=0|1 +RN=<num> +RD=<den> (line rate)
module tb_hbm_sm_attn;
    parameter integer KVMUT = 0;
    parameter integer PVMUT = 0;
    parameter integer LV = 4;
    parameter integer NCOL = 1;
    parameter integer NATIVE = 0;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [1087:0] lines [0:8191];
    reg [NCOL*1024-1:0] xs [0:127];
    integer nl, nx, rows, qk, kv4, h128, n8, rn, rd;
    string lf, xf;
    // converter
    reg cfg_v = 0; reg s_valid = 0; reg [1087:0] s_data = 0;
    wire s_ready, m_valid, m_ready, m_last, m_wend, busy, kfault;
    wire [1023:0] m_data; wire [2:0] m_slot, m_step;
    ot_hbm_sm_kv_line #(.MUT(KVMUT)) u_kv (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_qk(qk[0]), .cfg_kv4(kv4[0]), .cfg_n8(n8[12:0]), .cfg_h128(h128[0]),
        .cfg_rows(rows[12:0]), .s_valid(s_valid), .s_ready(s_ready), .s_data(s_data), .m_valid(m_valid), .m_ready(m_ready),
        .m_data(m_data), .m_slot(m_slot), .m_step(m_step), .m_wend(m_wend), .m_last(m_last), .busy(busy), .fault(kfault));
    // issue
    reg xw_en = 0; reg [6:0] xw_addr = 0; reg [NCOL*1024-1:0] xw_data = 0;
    wire c_v, c_first, c_last, op_issued; wire [15:0] c_tag; wire [1023:0] c_w; wire [NCOL*1024-1:0] c_x; wire [2:0] c_ph;
    ot_hbm_sm_attn_issue #(.NCOL(NCOL)) u_is (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_qk(qk[0]), .cfg_h128(h128[0]), .cfg_rows(rows[12:0]),
        .xw_en(xw_en), .xw_addr(xw_addr), .xw_data(xw_data), .b_valid(m_valid), .b_ready(m_ready), .b_data(m_data),
        .b_slot(m_slot), .b_step(m_step), .b_wend(m_wend), .b_last(m_last), .c_v(c_v), .c_first(c_first),
        .c_last(c_last), .c_tag(c_tag), .c_w(c_w), .c_x(c_x), .c_ph(c_ph), .op_issued(op_issued));
    // NCOL x columns x 4 sub-rows
    wire [4*NCOL-1:0] ov, pvv, cf; wire [128*NCOL-1:0] y; wire [64*NCOL-1:0] otag, pvt; wire [2048*NCOL-1:0] pvy;
    wire [NCOL-1:0] t_ov, t_f; wire [32*NCOL-1:0] t_y; wire [16*NCOL-1:0] t_tag;
    genvar q, cc;
    generate for (cc = 0; cc < NCOL; cc = cc + 1) begin : g_col
        for (q = 0; q < 4; q = q + 1) begin : g_c
            localparam integer I = 4 * cc + q;
            if (NATIVE != 0) begin : g_native
                ot_hbm_sm_attn_native_col #(.TAGW(16), .LV(LV), .MUT(PVMUT)) u_c (
                    .clk(clk), .rst_n(rst_n), .i_v(c_v), .i_first(c_first),
                    .i_qk_last(c_last && !c_tag[15]), .i_pv_last(c_last && c_tag[15]),
                    .i_run_first(c_tag[14]), .i_run_last(c_tag[13]), .i_tag(c_tag),
                    .i_w(c_w[256*q +: 256]), .i_x(c_x[1024*cc + 256*q +: 256]),
                    .ov(ov[I]), .y(y[32*I +: 32]), .otag(otag[16*I +: 16]),
                    .pv_v(pvv[I]), .pv_y(pvy[512*I +: 512]), .pv_tag(pvt[16*I +: 16]), .fault(cf[I]),
                    .pub_start(1'b0), .pub_slot(3'd0), .pub_v(), .pub_data(), .pub_word(), .pub_out_slot(), .pub_tag());
            end else begin : g_flat
            ot_hbm_sm_tcpv_col #(.L(16), .IL(8), .TAGW(16), .ALAT(7), .LV(LV), .MUT(PVMUT)) u_c (.clk(clk), .rst_n(rst_n),
                .v(c_v), .first(c_first), .last(c_last), .tag(c_tag), .w(c_w[256*q +: 256]), .x(c_x[1024*cc + 256*q +: 256]),
                .ov(ov[I]), .y(y[32*I +: 32]), .otag(otag[16*I +: 16]), .pv_v(pvv[I]), .pv_y(pvy[512*I +: 512]),
                .pv_tag(pvt[16*I +: 16]), .fault(cf[I]));
            end
        end
        // the SM back end's 4-leaf combine (QK at head dim 512; bypassed at head dim 128)
        ot_gpu_tree #(.N(4), .TAGW(16), .ALAT(7)) u_be (.clk(clk), .rst_n(rst_n), .v(ov[4*cc]), .d(y[128*cc +: 128]),
            .tag(otag[64*cc +: 16]), .ov(t_ov[cc]), .y(t_y[32*cc +: 32]), .otag(t_tag[16*cc +: 16]), .fault(t_f[cc]));
    end endgenerate
    // stimulus + monitor
    integer cyc = 0, li = 0, acc = 0, first_in = -1, last_in = -1, last_out = -1, nres = 0, want = 0, k, b, fb = -1, lb = -1, nb = 0, kk, bb;
    always @(posedge clk) cyc <= cyc + 1;
    // line rate: a line may be offered on cycles where the rate accumulator wraps (RN / RD lines per cycle)
    integer offered = 0; reg started = 0;
    always @(posedge clk) begin
        if (started) begin
            if (s_valid && s_ready) begin
                if (first_in < 0) first_in = cyc;
                last_in = cyc; li = li + 1;
            end
            if (!(s_valid && !s_ready)) begin
                acc = acc + rn;
                if (offered < nl && acc >= rd) begin
                    acc = acc - rd; s_valid <= 1'b1; s_data <= lines[offered]; offered = offered + 1;
                end else s_valid <= 1'b0;
            end
        end
    end
    always @(posedge clk) begin
        if (c_v && c_ph != ((qk != 0 && h128 != 0) ? c_tag[4:2] : c_tag[2:0])) begin
            $display("FAULT ring residue: beat tag %0h at residue %0d", c_tag, c_ph); $fatal(1, "residue");
        end
        if (c_v) begin if (fb < 0) fb = cyc; lb = cyc; nb = nb + 1; end
        for (kk = 0; kk < NCOL; kk = kk + 1) begin
            if (!h128 && t_ov[kk]) begin $display("SC %0d %0d %08h", kk, t_tag[16*kk +: 13], t_y[32*kk +: 32]); nres = nres + 1; last_out = cyc; end
            if (h128 && ov[4*kk]) for (bb = 0; bb < 4; bb = bb + 1)
                if (otag[64*kk + 16*bb +: 13] + bb < rows) begin
                    $display("SC %0d %0d %08h", kk, otag[64*kk + 16*bb +: 13] + bb, y[128*kk + 32*bb +: 32]); nres = nres + 1; last_out = cyc;
                end
            if (pvv[4*kk]) begin
                for (bb = 0; bb < 4; bb = bb + 1) $display("PV %0d %0d %0d %0128h", kk, pvt[64*kk +: 3], bb, pvy[2048*kk + 512*bb +: 512]);
                if (pvv[4*kk +: 4] != 4'hf) begin $display("FAULT pv lanes misaligned"); $fatal(1, "pv"); end
                nres = nres + 1; last_out = cyc;
            end
        end
        if (kfault || (|cf) || (|t_f)) begin $display("FAULT kv=%0d col=%b tree=%b", kfault, cf, t_f); $fatal(1, "fault"); end
    end
    initial begin
        if (!$value$plusargs("LINES=%s", lf) || !$value$plusargs("X=%s", xf)) $fatal(1, "plusargs");
        void'($value$plusargs("NL=%d", nl)); void'($value$plusargs("NX=%d", nx)); void'($value$plusargs("ROWS=%d", rows));
        h128 = 0; void'($value$plusargs("QK=%d", qk)); void'($value$plusargs("KV4=%d", kv4)); void'($value$plusargs("H128=%d", h128));
        n8 = kv4 ? 0 : rows; void'($value$plusargs("N8=%d", n8));
        rn = 8; rd = 11; void'($value$plusargs("RN=%d", rn)); void'($value$plusargs("RD=%d", rd));
        $readmemh(lf, lines, 0, nl - 1); $readmemh(xf, xs, 0, nx - 1);
        void'($value$plusargs("WANT=%d", want));
        repeat (4) @(posedge clk); rst_n <= 1;
        repeat (4) @(posedge clk);
        for (b = 0; b < nx; b = b + 1) begin
            @(posedge clk); xw_en <= 1; xw_addr <= b[6:0]; xw_data <= xs[b];
        end
        @(posedge clk); xw_en <= 0;
        @(posedge clk); cfg_v <= 1;
        @(posedge clk); cfg_v <= 0; started <= 1;
        fork
            begin wait (nres == want); repeat (4) @(posedge clk); end
            begin repeat (200000) @(posedge clk); $display("FAULT timeout nres=%0d want=%0d li=%0d", nres, want, li); $fatal(1, "timeout"); end
        join_any
        $display("CYCLES rows=%0d qk=%0d kv4=%0d lines=%0d first_in=%0d last_in=%0d last_out=%0d span=%0d beats=%0d first_beat=%0d last_beat=%0d", rows, qk, kv4,
                 li, first_in, last_in, last_out, last_out - first_in, nb, fb, lb);
        $display("DONE results=%0d", nres);
        $finish;
    end
endmodule
`default_nettype wire
