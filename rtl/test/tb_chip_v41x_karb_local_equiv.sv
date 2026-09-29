`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Transaction equivalence of ot_chip_v41x_hbm_karb_local (LOCAL = 1) and the
// pipelined ot_chip_v41x_hbm_karb_pipe (LOCAL = 2) against
// the monolithic ot_chip_v41x_hbm_karb (LOCAL = 0).  One env per arbiter, each
// with its own refresh-aware HBM model (ot_hdc_v41x_idx_hbm, the model inside
// ot_chip_v41x_hbm3e_phy) preloaded identically, driven by the same trace
// files: a K stream (reads and masked writes, any PC, no completion wait, as
// the KV prefetch) and one B stream per PC (a B write waits for its wr_done
// before that PC's next B request, as the pooled bridge).  Every response beat
// and the final memory image are logged; tools/rtl_chip_v41x_karb_local.py
// compares the two logs as multisets per requester and per tag.
// Plusargs: +trace=<dir> +log=<file> +seed=<n> +krdy=<percent> +brdy=<percent>
// ---------------------------------------------------------------------------
module tb_karb_env #(
    parameter integer LOCAL = 0,   // 0 monolithic, 1 local, 2 pipelined local
    parameter bit     FENCE = 1'b1,
    parameter integer NPC = 32,
    parameter integer AW = 28,
    parameter integer MEMW = 1 << 14,
    parameter integer NK = 512,
    parameter integer NB = 64
) (
    input  wire clk,
    input  wire rst_n,
    output reg  done
);
    localparam integer TAGW = 16, DW = 256;
    // trace: K entry {we, len[3:0], addr[27:0], tag[15:0], wstrb[31:0], dseed[31:0]}
    reg [112:0] kt [0:NK-1];
    reg [112:0] bt [0:NPC*NB-1];
    integer nk, nb [0:NPC-1];
    reg [31:0] nkr;  // K read beats expected
    reg [31:0] nbr;  // B read beats expected
    function automatic [DW-1:0] wd(input [31:0] seed);
        integer j; reg [31:0] x;
        begin x = seed; for (j = 0; j < 8; j = j + 1) begin x = x * 32'd1664525 + 32'd1013904223; wd[j*32 +: 32] = x; end end
    endfunction
    // DUT signals
    wire [NPC-1:0] b_rdy, b_wr_done, b_rsp_v, h_v, h_rdy, h_we, h_wr_done, r_v, r_rdy;
    reg  [NPC-1:0] b_v, b_we, b_rsp_rdy;
    reg  [NPC*AW-1:0] b_addr; reg [NPC*4-1:0] b_len; reg [NPC*TAGW-1:0] b_tag;
    reg  [NPC*DW-1:0] b_wdata; reg [NPC*32-1:0] b_wstrb;
    wire [NPC*TAGW-1:0] b_rsp_tag; wire [NPC*4-1:0] b_rsp_beat; wire [NPC*DW-1:0] b_rsp_data;
    reg  k_v, k_we, k_rsp_rdy; reg [AW-1:0] k_addr; reg [3:0] k_len; reg [TAGW-1:0] k_tag;
    reg  [DW-1:0] k_wdata; reg [31:0] k_wstrb;
    wire k_rdy, k_wr_done, k_rsp_v; wire [TAGW-1:0] k_rsp_tag; wire [3:0] k_rsp_beat; wire [DW-1:0] k_rsp_data;
    wire [NPC*AW-1:0] h_addr; wire [NPC*4-1:0] h_len, r_beat; wire [NPC*(TAGW+1)-1:0] h_tag, r_tag;
    wire [NPC*DW-1:0] h_wdata, r_data; wire [NPC*32-1:0] h_wstrb;
    wire [31:0] kg, bg, ct;
    generate if (LOCAL == 2) begin : g_dut
        ot_chip_v41x_hbm_karb_pipe #(.NPC(NPC), .AW(AW), .TAGW(TAGW), .K_RD_FENCE(FENCE)) u (
            .clk(clk), .rst_n(rst_n), .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag),
            .b_we(b_we), .b_wdata(b_wdata), .b_wstrb(b_wstrb), .b_wr_done(b_wr_done), .b_rsp_v(b_rsp_v),
            .b_rsp_rdy(b_rsp_rdy), .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat), .b_rsp_data(b_rsp_data),
            .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we),
            .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy),
            .k_rsp_tag(k_rsp_tag), .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done), .r_v(r_v), .r_rdy(r_rdy),
            .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data), .k_grants(kg), .b_grants(bg), .contended(ct));
    end else if (LOCAL == 1) begin : g_dut
        ot_chip_v41x_hbm_karb_local #(.NPC(NPC), .AW(AW), .TAGW(TAGW), .K_RD_FENCE(FENCE)) u (
            .clk(clk), .rst_n(rst_n), .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag),
            .b_we(b_we), .b_wdata(b_wdata), .b_wstrb(b_wstrb), .b_wr_done(b_wr_done), .b_rsp_v(b_rsp_v),
            .b_rsp_rdy(b_rsp_rdy), .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat), .b_rsp_data(b_rsp_data),
            .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we),
            .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy),
            .k_rsp_tag(k_rsp_tag), .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done), .r_v(r_v), .r_rdy(r_rdy),
            .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data), .k_grants(kg), .b_grants(bg), .contended(ct));
    end else begin : g_dut
        ot_chip_v41x_hbm_karb #(.NPC(NPC), .AW(AW), .TAGW(TAGW)) u (
            .clk(clk), .rst_n(rst_n), .b_v(b_v), .b_rdy(b_rdy), .b_addr(b_addr), .b_len(b_len), .b_tag(b_tag),
            .b_we(b_we), .b_wdata(b_wdata), .b_wstrb(b_wstrb), .b_wr_done(b_wr_done), .b_rsp_v(b_rsp_v),
            .b_rsp_rdy(b_rsp_rdy), .b_rsp_tag(b_rsp_tag), .b_rsp_beat(b_rsp_beat), .b_rsp_data(b_rsp_data),
            .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len), .k_tag(k_tag), .k_we(k_we),
            .k_wdata(k_wdata), .k_wstrb(k_wstrb), .k_wr_done(k_wr_done), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy),
            .k_rsp_tag(k_rsp_tag), .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data),
            .h_v(h_v), .h_rdy(h_rdy), .h_addr(h_addr), .h_len(h_len), .h_tag(h_tag), .h_we(h_we),
            .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_wr_done(h_wr_done), .r_v(r_v), .r_rdy(r_rdy),
            .r_tag(r_tag), .r_beat(r_beat), .r_data(r_data), .k_grants(kg), .b_grants(bg), .contended(ct));
    end endgenerate
    ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .DW(256), .MEM_WORDS(MEMW), .TAGW(TAGW+1), .LENW(4), .BEATW(4),
                          .QD(64), .REFPB(3), .MEM_MODE(0)) u_k (
        .clk(clk), .rst_n(rst_n), .req_v(h_v), .req_rdy(h_rdy), .req_addr(h_addr), .req_len(h_len),
        .req_tag(h_tag), .req_we(h_we), .req_wdata(h_wdata), .req_wstrb(h_wstrb), .wr_done(h_wr_done),
        .rsp_v(r_v), .rsp_rdy(r_rdy), .rsp_tag(r_tag), .rsp_beat(r_beat), .rsp_data(r_data));

    string tdir, lfile; integer lf, seed, krdy, brdy, i, p;
    integer ki, bi [0:NPC-1]; reg bwait [0:NPC-1];
    integer kbeats, bbeats, kwd_ev, bwd_n, kw_n, bw_n, cyc, t_kacc0, t_krsp0;
    initial begin
        if (!$value$plusargs("trace=%s", tdir)) tdir = ".";
        if (!$value$plusargs("seed=%d", seed)) seed = 1;
        if (!$value$plusargs("krdy=%d", krdy)) krdy = 100;
        if (!$value$plusargs("brdy=%d", brdy)) brdy = 100;
        if (!$value$plusargs("log=%s", lfile)) lfile = "karb.log";
        if (LOCAL == 2) lfile = {lfile, ".pipe"}; else if (LOCAL == 1) lfile = {lfile, ".local"}; else lfile = {lfile, ".mono"};
        $readmemh({tdir, "/k.hex"}, kt);
        $readmemh({tdir, "/b.hex"}, bt);
        $readmemh({tdir, "/init.hex"}, u_k.mem);
        lf = $fopen(lfile, "w");
        nkr = 0; nbr = 0; nk = 0; kw_n = 0; bw_n = 0;
        for (i = 0; i < NK; i = i + 1) if (kt[i] !== {113{1'bx}}) begin
            nk = nk + 1; if (!kt[i][112]) nkr = nkr + kt[i][111:108]; else kw_n = kw_n + 1;
        end
        for (p = 0; p < NPC; p = p + 1) begin
            nb[p] = 0;
            for (i = 0; i < NB; i = i + 1) if (bt[p*NB+i] !== {113{1'bx}}) begin
                nb[p] = nb[p] + 1; if (!bt[p*NB+i][112]) nbr = nbr + bt[p*NB+i][111:108]; else bw_n = bw_n + 1;
            end
        end
    end
    // drivers (registered at the edge, like the real requesters)
    reg [31:0] rs;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            k_v <= 0; ki = 0; b_v <= 0; b_rsp_rdy <= 0; k_rsp_rdy <= 0; rs <= 32'(seed) | 1;
            for (p = 0; p < NPC; p = p + 1) begin bi[p] = 0; bwait[p] = 0; end
            kbeats = 0; bbeats = 0; kwd_ev = 0; bwd_n = 0; cyc = 0; done <= 0; t_kacc0 = -1; t_krsp0 = -1;
        end else begin
            cyc = cyc + 1;
            // K
            if (k_v && k_rdy) begin ki = ki + 1; if (t_kacc0 < 0) t_kacc0 = cyc; end
            if (ki < nk) begin
                k_v <= 1; {k_we, k_len, k_addr, k_tag, k_wstrb} <= kt[ki][112:32]; k_wdata <= wd(kt[ki][31:0]);
            end else k_v <= 0;
            // B
            for (p = 0; p < NPC; p = p + 1) begin
                if (b_v[p] && b_rdy[p]) begin
                    if (b_we[p]) bwait[p] = 1;
                    bi[p] = bi[p] + 1;
                end
                if (b_wr_done[p]) begin bwait[p] = 0; bwd_n = bwd_n + 1; end
                if (bi[p] < nb[p] && !bwait[p]) begin
                    b_v[p] <= 1;
                    {b_we[p], b_len[p*4 +: 4], b_addr[p*AW +: AW], b_tag[p*TAGW +: TAGW], b_wstrb[p*32 +: 32]}
                        <= bt[p*NB+bi[p]][112:32];
                    b_wdata[p*DW +: DW] <= wd(bt[p*NB+bi[p]][31:0]);
                end else b_v[p] <= 0;
            end
            // responses
            if (k_rsp_v && k_rsp_rdy) begin
                $fdisplay(lf, "K %h %h %h", k_rsp_tag, k_rsp_beat, k_rsp_data);
                kbeats = kbeats + 1; if (t_krsp0 < 0) t_krsp0 = cyc;
            end
            for (p = 0; p < NPC; p = p + 1) if (b_rsp_v[p] && b_rsp_rdy[p]) begin
                $fdisplay(lf, "B %0d %h %h %h", p, b_rsp_tag[p*TAGW +: TAGW], b_rsp_beat[p*4 +: 4], b_rsp_data[p*DW +: DW]);
                bbeats = bbeats + 1;
            end
            if (k_wr_done) kwd_ev = kwd_ev + 1;
            rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5);
            k_rsp_rdy <= (rs % 100) < krdy;
            for (p = 0; p < NPC; p = p + 1) b_rsp_rdy[p] <= (((rs >> (p % 24)) ^ 32'(p * 7)) % 100) < brdy;
            if (!done && ki == nk && kbeats == nkr && bbeats == nbr && bwd_n == bw_n
                && (&(~bi_pending())) && u_idle()) begin
                done <= 1;
                $fdisplay(lf, "CYCLES %0d", cyc);
                $fdisplay(lf, "FIRST_K_ACC %0d FIRST_K_RSP %0d", t_kacc0, t_krsp0);
                $fdisplay(lf, "KWD_EVENTS %0d KWRITES %0d KGRANTS %0d BGRANTS %0d", kwd_ev, kw_n, kg, bg);
            end
        end
    function automatic [NPC-1:0] bi_pending();
        integer q; begin for (q = 0; q < NPC; q = q + 1) bi_pending[q] = (bi[q] < nb[q]); end
    endfunction
    // quiescent: no request presented by the arbiter and no response pending
    function automatic u_idle(); u_idle = (h_v == 0) && (r_v == 0) && !k_rsp_v; endfunction
    // after done, wait for write drain then dump memory
    integer w;
    always @(posedge done) begin
        repeat (4000) @(posedge clk);
        for (w = 0; w < MEMW; w = w + 1) $fdisplay(lf, "M %0d %h", w, u_k.mem[w]);
        $fclose(lf);
    end
endmodule

module tb_chip_v41x_karb_local_equiv #(parameter bit FENCE = 1'b1);
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    wire d0, d1, d2;
    tb_karb_env #(.LOCAL(0)) e_mono  (.clk(clk), .rst_n(rst_n), .done(d0));
    tb_karb_env #(.LOCAL(1), .FENCE(FENCE)) e_local (.clk(clk), .rst_n(rst_n), .done(d1));
    tb_karb_env #(.LOCAL(2), .FENCE(FENCE)) e_pipe (.clk(clk), .rst_n(rst_n), .done(d2));
    integer tmo;
    initial begin
        if (!$value$plusargs("timeout=%d", tmo)) tmo = 400000;
        repeat (5) @(posedge clk); rst_n = 1;
        fork
            begin wait (d0 && d1 && d2); repeat (4100) @(posedge clk); $display("DONE"); $finish; end
            begin repeat (tmo) @(posedge clk); $display("TIMEOUT mono=%0d local=%0d pipe=%0d", d0, d1, d2); $finish; end
        join_any
    end
endmodule
