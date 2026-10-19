`timescale 1ns/1ps
`default_nettype none
// tb_hnx_att4: one SM's KV-line-stationary 4-query attention slice (HBM-NEXT-ATT4 2026-10-19).  Declared external
// stimulus at the slice boundary: the union KV lines of the op (SM-KV8 / SM-KV4 canonical rows from the SM's own stack),
// the lanes' x words (QK: q images; PV: p_l by lane ordinal) and the op's lane masks.  Results are printed and compared
// bit for bit by tools/hbm_next/att4_bench.py against the golden of each lane ALONE (tools/hgi_sim/lib.py att_qk /
// att_pv csum8 over the lane's own list = 4 single-query runs).
// plusargs: +LINES=<hex> +NL=<lines> +X=<hex> (word w = lane w / 128, addr w % 128) +M=<hex> (16 x 64-b mask words)
//           +ROWS=<union rows> +QK=0|1 +KV4=0|1 +N8=<KV8 rows> +WANT=<results> +RN/+RD line rate
module tb_hnx_att4;
    parameter integer KVMUT = 0;
    parameter integer PVMUT = 0;
    parameter integer IMUT = 0;
    parameter integer LV = 4;
    parameter integer SHARED = 0;
    parameter integer STORE = 0;
    parameter integer SMUT = 0;
    parameter integer NLN = 3;          // query lanes = SM lanes P (P3 default, owner 10-19)
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [1087:0] lines [0:8191];
    reg [1023:0] xs [0:4*128-1];
    reg [63:0] ms [0:15];
    integer nl, rows, qk, kv4, n8, rn, rd, want;
    string lf, xf, mf;
    reg cfg_v = 0; reg s_valid = 0; reg [1087:0] s_data = 0;
    reg xw_en = 0; reg [1:0] xw_lane = 0; reg [6:0] xw_addr = 0; reg [1023:0] xw_data = 0;
    reg mclr = 0, mw_en = 0; reg [3:0] mw_addr = 0; reg [63:0] mw_data = 0;
    wire s_ready, op_issued, fault;
    wire [NLN-1:0] sc_v, pv_v, c_v; wire [32*NLN-1:0] sc_y; wire [16*NLN-1:0] sc_tag, pv_tag, c_tag; wire [2048*NLN-1:0] pv_y;
    wire [2:0] c_ph;
    ot_hnx_att4_slice #(.NL(NLN), .LV(LV), .KVMUT(KVMUT), .PVMUT(PVMUT), .IMUT(IMUT), .SHARED(SHARED), .STORE(STORE),
        .SMUT(SMUT)) dut (.clk(clk), .rst_n(rst_n),
        .cfg_v(cfg_v), .cfg_qk(qk[0]), .cfg_kv4(kv4[0]), .cfg_n8(n8[12:0]), .cfg_rows(rows[12:0]),
        .s_valid(s_valid), .s_ready(s_ready), .s_data(s_data),
        .xw_en(xw_en), .xw_lane(xw_lane), .xw_addr(xw_addr), .xw_data(xw_data),
        .mclr(mclr), .mw_en(mw_en), .mw_addr(mw_addr), .mw_data(mw_data),
        .sc_v(sc_v), .sc_y(sc_y), .sc_tag(sc_tag), .pv_v(pv_v), .pv_y(pv_y), .pv_tag(pv_tag),
        .op_issued(op_issued), .c_ph(c_ph), .c_v_o(c_v), .c_tag_o(c_tag), .fault(fault));
    integer cyc = 0, li = 0, acc = 0, first_in = -1, last_in = -1, last_out = -1, nres = 0, b, kk, bb, nbeat = 0;
    integer offered = 0; reg started = 0;
    always @(posedge clk) cyc <= cyc + 1;
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
        for (kk = 0; kk < NLN; kk = kk + 1) begin
            if (c_v[kk] && c_ph != c_tag[16*kk +: 3]) begin
                $display("FAULT ring residue: lane %0d tag %0h residue %0d", kk, c_tag[16*kk +: 16], c_ph); $fatal(1, "residue");
            end
            if (sc_v[kk]) begin $display("SC %0d %0d %08h", kk, sc_tag[16*kk + 3 +: 9], sc_y[32*kk +: 32]); nres = nres + 1; last_out = cyc; end
            if (pv_v[kk]) begin
                for (bb = 0; bb < 4; bb = bb + 1) $display("PV %0d %0d %0d %0128h", kk, pv_tag[16*kk +: 3], bb, pv_y[2048*kk + 512*bb +: 512]);
                nres = nres + 1; last_out = cyc;
            end
        end
        if (|c_v) nbeat = nbeat + 1;
        if (fault) begin $display("FAULT slice"); $fatal(1, "fault"); end
    end
    initial begin
        if (!$value$plusargs("LINES=%s", lf) || !$value$plusargs("X=%s", xf) || !$value$plusargs("M=%s", mf)) $fatal(1, "plusargs");
        void'($value$plusargs("NL=%d", nl)); void'($value$plusargs("ROWS=%d", rows));
        void'($value$plusargs("QK=%d", qk)); void'($value$plusargs("KV4=%d", kv4));
        n8 = kv4 ? 0 : rows; void'($value$plusargs("N8=%d", n8));
        rn = 8; rd = 11; void'($value$plusargs("RN=%d", rn)); void'($value$plusargs("RD=%d", rd));
        void'($value$plusargs("WANT=%d", want));
        $readmemh(lf, lines, 0, nl - 1); $readmemh(xf, xs); $readmemh(mf, ms);
        repeat (4) @(posedge clk); rst_n <= 1;
        repeat (4) @(posedge clk);
        @(posedge clk); mclr <= 1;
        @(posedge clk); mclr <= 0;
        for (b = 0; b < 16; b = b + 1) begin @(posedge clk); mw_en <= 1; mw_addr <= b[3:0]; mw_data <= ms[b]; end
        @(posedge clk); mw_en <= 0;
        for (b = 0; b < NLN * 128; b = b + 1) begin
            @(posedge clk); xw_en <= 1; xw_lane <= b / 128; xw_addr <= b % 128; xw_data <= xs[b];
        end
        @(posedge clk); xw_en <= 0;
        @(posedge clk); cfg_v <= 1;
        @(posedge clk); cfg_v <= 0; started <= 1;
        fork
            begin wait (nres == want); repeat (40) @(posedge clk); end
            begin repeat (200000) @(posedge clk); $display("FAULT timeout nres=%0d want=%0d li=%0d", nres, want, li); $fatal(1, "timeout"); end
        join_any
        $display("CYCLES rows=%0d qk=%0d kv4=%0d lines=%0d first_in=%0d last_in=%0d last_out=%0d span=%0d beats=%0d", rows, qk, kv4,
                 li, first_in, last_in, last_out, last_out - first_in, nbeat);
        $display("DONE results=%0d", nres);
        $finish;
    end
endmodule
`default_nettype wire
