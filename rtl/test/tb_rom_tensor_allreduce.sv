`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One-shot fixed-order all-reduce of a 4-die tensor group through the fabric
// router (Verilator).
//
// results/roofline/critical_path selects, for the DeepSeek-V4.1 array, a
// 4-die package whose dies form a tensor group joined by UCIe, with one-shot
// fixed-order collectives ("every die sums all partials in rank order").
// Here each die multicasts its binary32 partial vector as one RETURN record
// (dest = GROUP_BASE + 4'b1111, rank = its die index) into its port of
// rtl/rom/ot_rom_fabric_router.sv, whose routing table expands the group to
// all four ports; each die's ot_rom_moe_combine (IN_W = 32, NRANK = 4) sums
// the four partials in rank order.  Dies inject with random gaps and the
// router serialises its outputs, so partials arrive in varying orders.  Every
// die's sum is checked against the expected rank-order sum (+VEC/ar_sum.mem)
// and therefore against the other three replicas.
// Plusargs: +VEC, +N reductions, +SEED, +GAP percent.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module tb_rom_tensor_allreduce #(
    parameter integer TAGS = 4,
    parameter integer VF   = 5                // flits per partial vector (16 binary32 per flit)
) (
    input wire clk
);
    localparam integer FW = 512, ND = 4, MAXN = 1024, DESTS = 64;

    reg [3:0] rcnt = 4'd0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (rcnt != 4'hF) rcnt <= rcnt + 4'd1;
    reg [63:0] now = 64'd0;
    always @(posedge clk) now <= now + 64'd1;
    function [31:0] xs(input [31:0] s);
        reg [31:0] v;
        begin v = s ^ (s << 13); v = v ^ (v >> 17); xs = v ^ (v << 5); end
    endfunction
    function [DESTS*ND-1:0] route_init(input integer dummy);
        integer d;
        begin
            route_init = {DESTS*ND{1'b0}};
            for (d = 0; d < ND; d = d + 1) route_init[d*ND +: ND] = 4'b0001 << d;           // a die
            for (d = 1; d < 16; d = d + 1) route_init[(GROUP_BASE + d)*ND +: ND] = d;       // a die set
        end
    endfunction

    reg [FW-1:0] vpart [0:MAXN*ND*VF-1];           // partial of die r for reduction n, flit c
    reg [FW-1:0] vsum  [0:MAXN*VF-1];              // the expected rank-order sum
    string dir;
    integer N, SEED, GAP, k;
    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("N=%d", N)) N = 16;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        $readmemh({dir, "/ar_part.mem"}, vpart);
        $readmemh({dir, "/ar_sum.mem"}, vsum);
    end

    wire [ND-1:0]    r_in_valid, r_in_ready, r_in_last, r_out_valid, r_out_last, r_credit;
    wire [ND*FW-1:0] r_in_data, r_out_data;
    wire [31:0]      r_drops;
    wire             r_overflow;
    ot_rom_fabric_router #(.NP(ND), .FW(FW), .BUF(4), .DESTS(DESTS), .DEST_LSB(H_DST),
                           .ROUTE_INIT(route_init(0))) u_router (
        .clk(clk), .rst_n(rst_n), .in_valid(r_in_valid), .in_ready(r_in_ready), .in_credit(r_credit),
        .in_data(r_in_data), .in_last(r_in_last), .out_valid(r_out_valid), .out_ready({ND{1'b1}}),
        .out_data(r_out_data), .out_last(r_out_last), .cfg_we(1'b0), .cfg_dest(8'd0), .cfg_mask({ND{1'b0}}),
        .drops(r_drops), .overflow(r_overflow));

    wire [31:0] d_err [0:ND-1], d_got [0:ND-1];
    wire [ND-1:0] d_fault;
    wire [63:0] d_last_t [0:ND-1];
    // reduction n may start once every die has finished reduction n - TAGS (same tag)
    wire [31:0] done_cnt [0:ND*TAGS-1];
    genvar g;
    generate for (g = 0; g < ND; g = g + 1) begin : g_die
        // -- sender: reduction n uses tag n mod TAGS once every die has released it
        reg [31:0] r;
        reg [31:0] n = 0, c = 0;
        reg        busy = 1'b0;
        always @(posedge clk) begin
            if (!rst_n) r <= (32'h9E37_79B9 * (g + 11)) ^ SEED; else r <= xs(r);
        end
        reg ok;
        integer q;
        always @* begin
            ok = 1'b1;
            for (q = 0; q < ND; q = q + 1) if (done_cnt[q * TAGS + n % TAGS] < n / TAGS) ok = 1'b0;
        end
        wire go = rst_n && n < N && (busy || ok) && (r % 100) >= GAP;
        reg [FW-1:0] hdr;
        always @* begin
            hdr = {FW{1'b0}};
            hdr[H_DST +: 8]  = GROUP_BASE + 4'b1111;
            hdr[H_SRC +: 8]  = g;
            hdr[H_KIND +: 4] = K_RETURN;
            hdr[H_LEN +: 8]  = VF;
            hdr[H_TAG +: 8]  = n % TAGS;
            hdr[H_RANK +: 3] = g;
            hdr[H_MASK +: 16] = 16'h000F;
        end
        assign r_in_valid[g] = go && r_in_ready[g];      // the router counts every valid flit as sent
        assign r_in_data[g*FW +: FW] = (c == 0) ? hdr : vpart[(n * ND + g) * VF + c - 1];
        assign r_in_last[g] = (c == VF);
        always @(posedge clk) if (go && r_in_ready[g]) begin
            busy <= (c != VF);
            if (c == VF) begin c <= 0; n <= n + 1; end else c <= c + 1;
        end
        // -- the die's combine: rank-order sum of the four partials
        wire          ov, ol, fv;
        wire [7:0]    ot, oc, ft;
        wire [FW-1:0] od;
        wire [31:0]   ri, ci, ww;
        wire          rdy;
        ot_rom_moe_combine #(.FLIT_W(FW), .TAGS(TAGS), .NRANK(ND), .VEC_FLITS(VF), .IN_W(32), .OUT_BF16(0)) u_cmb (
            .clk(clk), .rst_n(rst_n), .in_valid(r_out_valid[g]), .in_ready(rdy), .in_data(r_out_data[g*FW +: FW]),
            .in_last(r_out_last[g]), .out_valid(ov), .out_tag(ot), .out_chunk(oc), .out_data(od), .out_last(ol),
            .tag_free_valid(fv), .tag_free(ft), .results_in(ri), .chunks_issued(ci), .walker_waits(ww),
            .fault(d_fault[g]));
        // -- check: reductions finish in order per tag; the k-th finish of tag t is reduction t + k*TAGS
        integer e = 0, got = 0;
        integer seq [0:TAGS-1];
        reg [63:0] lt = 0;
        initial for (k = 0; k < TAGS; k = k + 1) seq[k] = 0;
        integer nn;
        always @(posedge clk) if (rst_n && ov) begin
            nn = ot + seq[ot] * TAGS;
            if (od !== vsum[nn * VF + oc]) e = e + 1;
            if (ol) begin seq[ot] = seq[ot] + 1; got = got + 1; lt = now; end
        end
        assign d_err[g] = e;
        assign d_got[g] = got;
        assign d_last_t[g] = lt;
        genvar t;
        for (t = 0; t < TAGS; t = t + 1) begin : g_cnt
            assign done_cnt[g * TAGS + t] = seq[t];
        end
    end endgenerate

    integer te, tg;
    always @(posedge clk) begin
        tg = 0; te = 0;
        for (k = 0; k < ND; k = k + 1) begin tg = tg + d_got[k]; te = te + d_err[k]; end
        if (rst_n && (tg == ND * N || now > 64'd100000 + 64'd1000 * N)) begin
            $display("ALLREDUCE reductions=%0d replicas=%0d errors=%0d faults=%0d drops=%0d overflow=%0d cycles=%0d",
                     N, tg, te, |d_fault, r_drops, r_overflow, now);
            $finish;
        end
    end
endmodule
