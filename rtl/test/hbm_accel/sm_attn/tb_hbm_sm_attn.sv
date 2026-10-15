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
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [1087:0] lines [0:8191];
    reg [1023:0] xs [0:127];
    integer nl, nx, rows, qk, kv4, rn, rd;
    string lf, xf;
    // converter
    reg cfg_v = 0; reg s_valid = 0; reg [1087:0] s_data = 0;
    wire s_ready, m_valid, m_ready, m_last, busy, kfault;
    wire [1023:0] m_data; wire [2:0] m_slot, m_step; wire [3:0] m_wrows;
    ot_hbm_sm_kv_line #(.MUT(KVMUT)) u_kv (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_qk(qk[0]), .cfg_kv4(kv4[0]),
        .cfg_rows(rows[12:0]), .s_valid(s_valid), .s_ready(s_ready), .s_data(s_data), .m_valid(m_valid), .m_ready(m_ready),
        .m_data(m_data), .m_slot(m_slot), .m_step(m_step), .m_wrows(m_wrows), .m_last(m_last), .busy(busy), .fault(kfault));
    // issue
    reg xw_en = 0; reg [6:0] xw_addr = 0; reg [1023:0] xw_data = 0;
    wire c_v, c_first, c_last, op_issued; wire [15:0] c_tag; wire [1023:0] c_w, c_x; wire [2:0] c_ph;
    ot_hbm_sm_attn_issue u_is (.clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_qk(qk[0]), .cfg_rows(rows[12:0]),
        .xw_en(xw_en), .xw_addr(xw_addr), .xw_data(xw_data), .b_valid(m_valid), .b_ready(m_ready), .b_data(m_data),
        .b_slot(m_slot), .b_step(m_step), .b_wrows(m_wrows), .b_last(m_last), .c_v(c_v), .c_first(c_first),
        .c_last(c_last), .c_tag(c_tag), .c_w(c_w), .c_x(c_x), .c_ph(c_ph), .op_issued(op_issued));
    // 4 sub-row columns
    wire [3:0] ov, pvv, cf; wire [127:0] y; wire [63:0] otag, pvt; wire [2047:0] pvy;
    genvar q;
    generate for (q = 0; q < 4; q = q + 1) begin : g_c
        ot_hbm_sm_tcpv_col #(.L(16), .IL(8), .TAGW(16), .ALAT(7), .LV(LV), .MUT(PVMUT)) u_c (.clk(clk), .rst_n(rst_n),
            .v(c_v), .first(c_first), .last(c_last), .tag(c_tag), .w(c_w[256*q +: 256]), .x(c_x[256*q +: 256]),
            .ov(ov[q]), .y(y[32*q +: 32]), .otag(otag[16*q +: 16]), .pv_v(pvv[q]), .pv_y(pvy[512*q +: 512]),
            .pv_tag(pvt[16*q +: 16]), .fault(cf[q]));
    end endgenerate
    wire t_ov, t_f; wire [31:0] t_y; wire [15:0] t_tag;
    ot_gpu_tree #(.N(4), .TAGW(16), .ALAT(7)) u_be (.clk(clk), .rst_n(rst_n), .v(ov[0]), .d(y), .tag(otag[15:0]),
        .ov(t_ov), .y(t_y), .otag(t_tag), .fault(t_f));
    // stimulus + monitor
    integer cyc = 0, li = 0, acc = 0, first_in = -1, last_in = -1, last_out = -1, nres = 0, want = 0, k, b, fb = -1, lb = -1, nb = 0;
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
        if (c_v && (qk != 0 ? c_ph != c_tag[2:0] : c_ph != c_tag[2:0])) begin
            $display("FAULT ring residue: beat for slot %0d at residue %0d", c_tag[2:0], c_ph); $fatal(1, "residue");
        end
        if (c_v) begin if (fb < 0) fb = cyc; lb = cyc; nb = nb + 1; end
        if (t_ov) begin $display("SC %0d %08h", t_tag[12:0], t_y); nres = nres + 1; last_out = cyc; end
        if (pvv[0]) begin
            for (k = 0; k < 4; k = k + 1) $display("PV %0d %0d %0128h", pvt[2:0], k, pvy[512*k +: 512]);
            if (pvv != 4'hf) begin $display("FAULT pv lanes misaligned %b", pvv); $fatal(1, "pv"); end
            nres = nres + 1; last_out = cyc;
        end
        if (kfault || (|cf) || t_f) begin $display("FAULT kv=%0d col=%b tree=%0d", kfault, cf, t_f); $fatal(1, "fault"); end
    end
    initial begin
        if (!$value$plusargs("LINES=%s", lf) || !$value$plusargs("X=%s", xf)) $fatal(1, "plusargs");
        void'($value$plusargs("NL=%d", nl)); void'($value$plusargs("NX=%d", nx)); void'($value$plusargs("ROWS=%d", rows));
        void'($value$plusargs("QK=%d", qk)); void'($value$plusargs("KV4=%d", kv4));
        rn = 8; rd = 11; void'($value$plusargs("RN=%d", rn)); void'($value$plusargs("RD=%d", rd));
        $readmemh(lf, lines, 0, nl - 1); $readmemh(xf, xs, 0, nx - 1);
        want = qk ? rows : 8;
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
