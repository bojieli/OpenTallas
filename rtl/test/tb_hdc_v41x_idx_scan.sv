`timescale 1ns/1ps
// Index-key scan bench: NS HBM3E stacks (ot_hdc_v41x_idx_hbm, 32 pseudo-
// channels each, refresh on) -> one ot_hdc_v41x_idx_kstream per stack ->
// ot_hdc_v41x_idx_kmerge (NS >= 4; NS = 1 takes the stack's stream directly)
// -> a sink of SINKW keys per cycle (the indexer engine's ingest).  The HBM
// returns a pattern of the sector address (MEM_MODE 1), so every delivered key
// is checked against the bytes its position's layout puts in HBM (the key
// layout of ot_hdc_v41x_idx_kstream, 16-key groups interleaved over stacks).
// Plusargs: NKEYS (die total), ORDY (1/16ths of cycles the sink refuses),
// WIN0/WIN1 (steady-state window as fractions x1000 of the delivered keys).
// Reports cycles, keys, errors, HBM sectors read, refreshes, bytes/cycle.
module tb_hdc_v41x_idx_scan #(
    parameter integer NS    = 5,
    parameter integer WB    = 32,
    parameter integer GA    = 64,
    parameter integer QD    = 64,
    parameter integer REFPB = 2,
    parameter longint REFI_PS = 3900000,
    parameter integer CLK_PS = 967,
    parameter integer SINKW = 64,
    parameter integer FQ    = 4
) (input wire clk);
    localparam integer NPC = 32, AW = 28, HW = 20, TAGW = 16, LENW = 4, BEATW = 4, DW = 256;
    integer nkeys = 0, ordy = 0, win0 = 125, win1 = 875;
    initial begin
        if (!$value$plusargs("NKEYS=%d", nkeys)) nkeys = 4096;
        if (!$value$plusargs("ORDY=%d", ordy)) ordy = 0;
        if (!$value$plusargs("WIN0=%d", win0)) win0 = 125;
        if (!$value$plusargs("WIN1=%d", win1)) win1 = 875;
    end
    function automatic [DW-1:0] pat(input [AW-1:0] s);
        integer w;
        begin
            for (w = 0; w < DW / 32; w = w + 1) pat[32*w +: 32] = (s * 32'd8 + w) * 32'h9E3779B1 ^ 32'h5bd1e995;
        end
    endfunction
    // keys on stack s of a die scan of n keys (16-key groups, group g on stack g mod NS)
    function automatic integer skeys(input integer s, input integer n);
        integer g, full, k;
        begin
            g = (n + 15) / 16;
            k = 0;
            for (full = s; full < g; full = full + NS) k = k + ((full == g - 1 && n % 16 != 0) ? n % 16 : 16);
            skeys = k;
        end
    endfunction
    // expected 544-bit key of die position k
    function automatic [543:0] expkey(input integer k);
        integer g, s, lk, j, kk, b, kb;
        reg [AW-1:0] sc, cs;
        reg [DW-1:0] ps;
        begin
            g = k / 16; s = g % NS;
            lk = (g / NS) * 16 + k % 16;
            j = lk / 1024; kk = lk % 1024;
            b = kk / 64 + 1; kb = kk % 64;
            cs = (17 * j + b) * 128 + 2 * kb;
            sc = (17 * j) * 128 + kk / 8;
            ps = pat(sc);
            expkey = {ps[32 * (kk % 8) +: 32], pat(cs + 1), pat(cs)};
        end
    endfunction

    reg rst_n = 1'b0;
    reg cmd_v = 1'b0;
    wire [NS-1:0] busy, sv, sr;
    wire [NS*16-1:0] skv;
    wire [NS*16*544-1:0] skey;
    genvar gs;
    generate
        for (gs = 0; gs < NS; gs = gs + 1) begin : g_st
            wire [NPC-1:0] req_v, req_rdy, rsp_v, rsp_rdy;
            wire [NPC*AW-1:0] req_addr;
            wire [NPC*LENW-1:0] req_len;
            wire [NPC*TAGW-1:0] req_tag, rsp_tag;
            wire [NPC*BEATW-1:0] rsp_beat;
            wire [NPC*DW-1:0] rsp_data;
            ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .DW(DW), .MEM_WORDS(1), .TAGW(TAGW), .LENW(LENW),
                                  .BEATW(BEATW), .QD(QD), .CLK_PS(CLK_PS), .REFPB(REFPB), .REFI_PS(REFI_PS),
                                  .MEM_MODE(1)) u_hbm (
                .clk(clk), .rst_n(rst_n), .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len),
                .req_tag(req_tag), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
                .rsp_data(rsp_data));
            ot_hdc_v41x_idx_kstream #(.NPC(NPC), .WB(WB), .GA(GA), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW),
                                      .BEATW(BEATW), .DW(DW)) u_ks (
                .clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd_base({HW{1'b0}}), .cmd_nkeys(skeys(gs, nkeys)),
                .busy(busy[gs]), .req_v(req_v), .req_rdy(req_rdy), .req_addr(req_addr), .req_len(req_len),
                .req_tag(req_tag), .rsp_v(rsp_v), .rsp_rdy(rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat),
                .rsp_data(rsp_data), .o_valid(sv[gs]), .o_ready(sr[gs]), .o_kv(skv[16*gs +: 16]),
                .o_key(skey[16*544*gs +: 16*544]));
            integer pp;
            longint sref, srd;
            final begin
                sref = 0; srd = 0;
                for (pp = 0; pp < NPC; pp = pp + 1) begin
                    sref = sref + u_hbm.st_ref[pp];
                    srd = srd + u_hbm.st_rd[pp];
                end
                $display("V41XHBM stack=%0d rd=%0d ref=%0d lat_sum=%0d lat_max_ps=%0d", gs, srd, sref,
                         u_hbm.st_rd_lat_sum, u_hbm.st_rd_lat_max);
            end
        end
    endgenerate

    // the die stream
    wire             dv;
    reg              dr = 1'b0;
    wire [SINKW-1:0] dkv;
    wire [SINKW*544-1:0] dkey;
    generate
        if (NS == 1) begin : g_one
            assign dv = sv[0];
            assign sr[0] = dr;
            assign dkv = skv;
            assign dkey = skey;
        end else begin : g_merge
            ot_hdc_v41x_idx_kmerge #(.NS(NS), .FQ(FQ)) u_m (.clk(clk), .rst_n(rst_n), .i_valid(sv), .i_ready(sr),
                .i_kv(skv), .i_key(skey), .o_valid(dv), .o_ready(dr), .o_kv(dkv), .o_key(dkey));
        end
    endgenerate

    integer cyc = 0, t0 = -1, tend = -1, kout = 0, errors = 0, i, p, s, tw0 = -1, tw1 = -1, kw0 = 0, kw1 = 0;
    reg [31:0] seed = 32'h9a3c5e71;
    reg started = 1'b0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        cmd_v <= 1'b0;
        if (rst_n && !started) begin
            cmd_v <= 1'b1; started <= 1'b1; t0 = cyc + 1;
        end
        if (rst_n) begin
            seed = seed ^ (seed << 13); seed = seed ^ (seed >> 17); seed = seed ^ (seed << 5);
            dr <= !(ordy > 0 && seed[7:4] < ordy);
        end
        if (dv && dr) begin
            for (i = 0; i < SINKW; i = i + 1)
                if (dkv[i]) begin
                    if (dkey[544*i +: 544] !== expkey(kout)) begin
                        errors = errors + 1;
                        if (errors <= 5) $display("KEY MISMATCH position %0d lane %0d", kout, i);
                    end
                    kout = kout + 1;
                end
            // steady-state window marks (keys and HBM sectors read so far)
            if (tw0 < 0 && kout * 1000 >= win0 * nkeys) begin tw0 = cyc; kw0 = kout; end
            if (tw1 < 0 && kout * 1000 >= win1 * nkeys) begin tw1 = cyc; kw1 = kout; end
            if (kout >= nkeys) tend = cyc;
        end
        if (started && tend >= 0) begin
            $display("V41XSCAN ns=%0d wb=%0d ga=%0d qd=%0d refpb=%0d keys=%0d delivered=%0d errors=%0d cycles=%0d win_keys=%0d win_cycles=%0d",
                     NS, WB, GA, QD, REFPB, nkeys, kout, errors, tend - t0 + 1, kw1 - kw0, tw1 - tw0);
            $finish;
        end
        if (cyc > 50000000) begin
            $display("V41XSCAN TIMEOUT delivered=%0d", kout);
            $finish;
        end
    end
endmodule
