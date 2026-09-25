`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Multi-package bench of the KV multicast / all-gather node and the carried
// argmax (Verilator).
//
// KV.  NP packages in a chain (RING = 1 closes it), each an ot_rom_mcast_node
// joined to the next by an ot_rom_pkg_link.  Every package injects its own
// records (+VEC/inj<p>.mem, in order) and every delivered record is checked:
// it must be addressed to that package, arrive once, carry the injected
// bytes, and keep its source's order.  Records carry a unique id in header
// bits [127:112].  A record's dst_mask is either its own or, when zero, the
// injecting node's CONSUMERS entry of CONS (16 bits per package).
//
// ARGMAX.  NP ot_rom_argmax_reduce engines, one per vocabulary slice, chained
// by links; each is fed its slice's logits (LANES per beat) and the last one's
// record must name the golden argmax (+VEC/am.mem).
// Plusargs: +NA tokens for the argmax, +SEED, +BP back-pressure percent.
// ---------------------------------------------------------------------------
import ot_rom_coll_pkg::*;

module tb_rom_kv_argmax #(
    parameter integer NP      = 8,
    parameter integer RING    = 0,
    parameter integer CREDITS = 128,
    parameter integer CH      = 60,
    parameter [16*NP-1:0] CONS = {16*NP{1'b0}},
    parameter integer SLICE   = 505,          // logits per package
    parameter integer LANES   = 16
) (
    input wire clk
);
    localparam integer FW = 512, MAXR = 4096, MAXA = 256;
    localparam integer BEATS = (SLICE + LANES - 1) / LANES;

    reg [3:0] rcnt = 4'd0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (rcnt != 4'hF) rcnt <= rcnt + 4'd1;
    reg [63:0] now = 64'd0;
    always @(posedge clk) now <= now + 64'd1;
    function [31:0] xs(input [31:0] s);
        reg [31:0] v;
        begin v = s ^ (s << 13); v = v ^ (v >> 17); xs = v ^ (v << 5); end
    endfunction

    // -- vectors -----------------------------------------------------------------------------------
    reg [FW:0]  inj  [0:NP-1][0:MAXR-1];          // {last, flit}
    reg [31:0]  ninj [0:NP-1];                     // flits per package
    reg [15:0]  rmask[0:MAXR-1];                   // expected destination set of record id
    reg [3:0]   rsrc [0:MAXR-1];
    reg [31:0]  rlen [0:MAXR-1];                   // flits
    reg [31:0]  roff [0:MAXR-1];                   // first flit's index in its source's inj list
    reg [31:0]  nrec_m [0:0];
    reg [FW-1:0] lg  [0:MAXA*NP*BEATS-1];
    reg [63:0]  am   [0:MAXA-1];                   // {id, value}
    string dir;
    integer NA, SEED, BP, NREC, k, p;
    reg [FW:0] tmp [0:MAXR-1];
    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("NA=%d", NA)) NA = 0;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("BP=%d", BP)) BP = 0;
        $readmemh({dir, "/ninj.mem"}, ninj);
        for (p = 0; p < NP; p = p + 1) begin
            $readmemh({dir, $sformatf("/inj%0d.mem", p)}, tmp);
            for (k = 0; k < MAXR; k = k + 1) inj[p][k] = tmp[k];
        end
        $readmemh({dir, "/nrec.mem"}, nrec_m);
        NREC = nrec_m[0];
        $readmemh({dir, "/rmask.mem"}, rmask);
        $readmemh({dir, "/rsrc.mem"}, rsrc);
        $readmemh({dir, "/rlen.mem"}, rlen);
        $readmemh({dir, "/roff.mem"}, roff);
        if (NA > 0) begin
            $readmemh({dir, "/lg.mem"}, lg);
            $readmemh({dir, "/am.mem"}, am);
        end
    end

    // -- KV chain ------------------------------------------------------------------------------------
    wire [NP-1:0] up_v, up_r, up_l, dn_v, dn_r, dn_l;
    wire [FW-1:0] up_d [0:NP-1];
    wire [FW-1:0] dn_d [0:NP-1];
    wire [31:0]   deliv [0:NP-1], fwd [0:NP-1], injd [0:NP-1], lstall [0:NP-1];
    wire [31:0]   kv_err [0:NP-1], kv_got [0:NP-1];
    wire [NP-1:0] inj_done;
    // delivered[id] bit p: record id reached package p
    reg  [NP-1:0] delivered [0:MAXR-1];
    reg  [63:0]   inj_t [0:MAXR-1];                // when record id's header entered its source node
    wire [31:0]   mlw [0:NP*NP-1], mxw [0:NP*NP-1];
    initial for (k = 0; k < MAXR; k = k + 1) delivered[k] = {NP{1'b0}};
    genvar g;
    generate for (g = 0; g < NP; g = g + 1) begin : g_kv
        reg  [31:0] r;
        reg         st_inj, st_loc, st_dn;
        always @(posedge clk) begin
            if (!rst_n) r <= (32'h85EB_CA6B * (g + 1)) ^ SEED;
            else r <= xs(r);
            st_inj <= (r % 100) < BP;
            st_loc <= ((r >> 8) % 100) < BP;
            st_dn  <= ((r >> 16) % 100) < BP;
        end
        reg [31:0] ip = 0;
        wire iv = rst_n && ip < ninj[g] && !st_inj;
        wire ir;
        reg first_i = 1'b1;
        always @(posedge clk) if (iv && ir) begin
            ip <= ip + 1;
            if (first_i) inj_t[inj[g][ip][127:112]] = now;
            first_i <= inj[g][ip][FW];
        end
        assign inj_done[g] = (ip >= ninj[g]);
        wire lv, ll;
        wire [FW-1:0] ld;
        wire lr = !st_loc;
        ot_rom_mcast_node #(.FLIT_W(FW), .SELF(g), .CONSUMERS(CONS[16*g +: 16])) u_node (
            .clk(clk), .rst_n(rst_n),
            .up_valid(up_v[g]), .up_ready(up_r[g]), .up_data(up_d[g]), .up_last(up_l[g]),
            .inj_valid(iv), .inj_ready(ir), .inj_data(inj[g][ip][FW-1:0]), .inj_last(inj[g][ip][FW]),
            .dn_valid(dn_v[g]), .dn_ready(dn_r[g]), .dn_data(dn_d[g]), .dn_last(dn_l[g]),
            .loc_valid(lv), .loc_ready(lr), .loc_data(ld), .loc_last(ll),
            .delivered(deliv[g]), .forwarded(fwd[g]), .injected(injd[g]));
        // the link to the next package (none after the last one unless RING)
        if (g < NP - 1 || RING != 0) begin : g_link
            wire ov;
            // back-pressure at the receiving end: the flit is neither offered nor taken this cycle
            ot_rom_pkg_link #(.FLIT_BYTES(FW / 8), .CHANNEL_CYCLES(CH), .CREDITS(CREDITS)) u_l (
                .clk(clk), .rst_n(rst_n), .in_valid(dn_v[g]), .in_ready(dn_r[g]), .in_data(dn_d[g]),
                .in_last(dn_l[g]), .out_valid(ov), .out_ready(up_r[(g + 1) % NP] && !st_dn),
                .out_data(up_d[(g + 1) % NP]), .out_last(up_l[(g + 1) % NP]), .credit_stalls(lstall[g]));
            assign up_v[(g + 1) % NP] = ov && !st_dn;
        end else begin : g_end
            assign dn_r[g] = 1'b1;                   // nothing may leave the chain's end
            assign lstall[g] = 32'd0;
        end
        if (g == 0 && RING == 0) begin : g_head
            assign up_v[0] = 1'b0; assign up_d[0] = {FW{1'b0}}; assign up_l[0] = 1'b0;
        end
        // delivery check
        integer e = 0, got = 0, pos = 0, id = -1, src, hops;
        integer lastid [0:NP-1];
        integer ml [0:NP-1], mx [0:NP-1];          // delivery latency by hop count: min, max
        initial for (k = 0; k < NP; k = k + 1) begin lastid[k] = -1; ml[k] = 1 << 30; mx[k] = 0; end
        genvar h;
        for (h = 0; h < NP; h = h + 1) begin : g_h
            assign mlw[g * NP + h] = ml[h];
            assign mxw[g * NP + h] = mx[h];
        end
        always @(posedge clk) if (rst_n && lv && lr) begin
            if (pos == 0) begin
                id = ld[127:112];
                src = ld[H_SRC +: 8];
                got = got + 1;
                if (id < 0 || id >= NREC) e = e + 1;
                else begin
                    if (!rmask[id][g]) e = e + 1;
                    if (delivered[id][g]) e = e + 1;
                    delivered[id][g] = 1'b1;
                    if (src != rsrc[id]) e = e + 1;
                    if (id <= lastid[src]) e = e + 1;       // per-source order
                    lastid[src] = id;
                    hops = (g - src + NP) % NP;
                    if (now - inj_t[id] < ml[hops]) ml[hops] = now - inj_t[id];
                    if (now - inj_t[id] > mx[hops]) mx[hops] = now - inj_t[id];
                end
            end
            if (id >= 0 && id < NREC) begin
                // the payload flits verbatim; the header's routing fields are the fabric's own
                if (pos > 0 && ld !== inj[rsrc[id]][roff[id] + pos][FW-1:0]) e = e + 1;
                if (pos == 0 && ld[FW-1:64] !== inj[rsrc[id]][roff[id]][FW-1:64]) e = e + 1;
                // the fabric id: the package itself when it is the nearest remaining consumer
                if (pos == 0 && ld[H_DST +: 8] != g) e = e + 1;
                if (ll != (pos == rlen[id] - 1)) e = e + 1;
            end
            pos = ll ? 0 : pos + 1;
        end
        assign kv_err[g] = e;
        assign kv_got[g] = got;
        // anything reaching the chain's end must have had an empty mask: count it as an error
        integer leak = 0;
        if (g == NP - 1 && RING == 0) begin : g_leak
            always @(posedge clk) if (rst_n && dn_v[g]) leak = leak + 1;
        end
    end endgenerate

    // -- argmax chain -----------------------------------------------------------------------------------
    wire [NP-1:0] a_uv, a_ur, a_ul, a_dv, a_dr, a_dl;
    wire [FW-1:0] a_ud [0:NP-1];
    wire [FW-1:0] a_dd [0:NP-1];
    wire [NP-1:0] a_fault;
    generate for (g = 0; g < NP; g = g + 1) begin : g_am
        reg [31:0] r;
        reg        st;
        always @(posedge clk) begin
            if (!rst_n) r <= (32'h27D4_EB2F * (g + 7)) ^ SEED;
            else r <= xs(r);
            st <= (r % 100) < BP;
        end
        reg [31:0] tk = 0, bt = 0;
        wire lgv = rst_n && tk < NA && !st;
        wire lgr;
        reg [LANES-1:0] msk;
        always @* for (k = 0; k < LANES; k = k + 1) msk[k] = (bt * LANES + k) < SLICE;
        always @(posedge clk) if (lgv && lgr) begin
            if (bt == BEATS - 1) begin bt <= 0; tk <= tk + 1; end else bt <= bt + 1;
        end
        wire [31:0] tko;
        ot_rom_argmax_reduce #(.FLIT_W(FW), .LANES(LANES), .SELF(g), .NEXT((g + 1) % 16), .FIRST(g == 0 ? 1 : 0)) u_am (
            .clk(clk), .rst_n(rst_n),
            .lg_valid(lgv), .lg_ready(lgr), .lg_data(lg[(tk * NP + g) * BEATS + bt][LANES*32-1:0]), .lg_mask(msk),
            .lg_base(g * SLICE + bt * LANES), .lg_tag(tk[7:0]), .lg_last(bt == BEATS - 1),
            .up_valid(a_uv[g]), .up_ready(a_ur[g]), .up_data(a_ud[g]), .up_last(a_ul[g]),
            .dn_valid(a_dv[g]), .dn_ready(a_dr[g]), .dn_data(a_dd[g]), .dn_last(a_dl[g]),
            .tokens_out(tko), .fault(a_fault[g]));
        if (g < NP - 1) begin : g_link
            wire [31:0] cs;
            ot_rom_pkg_link #(.FLIT_BYTES(FW / 8), .CHANNEL_CYCLES(CH), .CREDITS(CREDITS)) u_l (
                .clk(clk), .rst_n(rst_n), .in_valid(a_dv[g]), .in_ready(a_dr[g]), .in_data(a_dd[g]),
                .in_last(a_dl[g]), .out_valid(a_uv[g + 1]), .out_ready(a_ur[g + 1]),
                .out_data(a_ud[g + 1]), .out_last(a_ul[g + 1]), .credit_stalls(cs));
        end
        if (g == 0) begin : g_head
            assign a_uv[0] = 1'b0; assign a_ud[0] = {FW{1'b0}}; assign a_ul[0] = 1'b0;
        end
    end endgenerate
    reg [31:0] r_out;
    reg        st_out;
    always @(posedge clk) begin
        if (!rst_n) r_out <= 32'h1656_67B1 ^ SEED; else r_out <= xs(r_out);
        st_out <= (r_out % 100) < BP;
    end
    assign a_dr[NP-1] = !st_out;
    integer am_got = 0, am_err = 0;
    reg [63:0] am_first = 0, am_last = 0, am_q1 = 0, am_q3 = 0;
    always @(posedge clk) if (rst_n && a_dv[NP-1] && a_dr[NP-1]) begin
        if (a_dd[NP-1][H_ARG_ID +: 32] != am[am_got][63:32] || a_dd[NP-1][H_ARG_VAL +: 32] != am[am_got][31:0]
            || a_dd[NP-1][H_TAG +: 8] != am_got[7:0] || !a_dd[NP-1][H_ARG_OK]) begin
            am_err = am_err + 1;
            if (am_err <= 5) $display("AMMISMATCH token=%0d got_id=%0d want_id=%0d", am_got, a_dd[NP-1][H_ARG_ID +: 32], am[am_got][63:32]);
        end
        am_got = am_got + 1;
        if (am_got == 1) am_first = now;
        if (am_got == NA / 4) am_q1 = now;
        if (am_got == (3 * NA) / 4) am_q3 = now;
        am_last = now;
    end

    // -- end of run --------------------------------------------------------------------------------------
    integer tot_err, tot_got, tot_want, tot_stall, tot_fwd, tot_inj, id2;
    reg [63:0] kv_done = 0;
    reg        kv_fin = 1'b0;
    integer hmin, hmax, hh;
    reg     want_done = 1'b0;
    always @(posedge clk) begin
        tot_got = 0;
        for (k = 0; k < NP; k = k + 1) tot_got = tot_got + kv_got[k];
        if (!want_done) begin
            want_done = 1'b1;
            tot_want = 0;
            for (id2 = 0; id2 < NREC; id2 = id2 + 1)
                for (k = 0; k < NP; k = k + 1) if (rmask[id2][k]) tot_want = tot_want + 1;
        end
        if (!kv_fin && rst_n && tot_got == tot_want && &inj_done) begin kv_fin = 1'b1; kv_done = now; end
        if (rst_n && ((kv_fin && am_got == NA) || now > 64'd2000000)) begin
            tot_err = 0; tot_stall = 0; tot_fwd = 0; tot_inj = 0;
            for (k = 0; k < NP; k = k + 1) begin
                tot_err = tot_err + kv_err[k]; tot_stall = tot_stall + lstall[k];
                tot_fwd = tot_fwd + fwd[k]; tot_inj = tot_inj + injd[k];
            end
            $display("KV records=%0d deliveries=%0d expected=%0d errors=%0d leaked=%0d injected=%0d forwarded=%0d credit_stalls=%0d done_cycle=%0d",
                     NREC, tot_got, tot_want, tot_err, g_kv[NP-1].leak, tot_inj, tot_fwd, tot_stall, kv_done);
            for (hh = 1; hh < NP; hh = hh + 1) begin
                hmin = 1 << 30; hmax = 0;
                for (k = 0; k < NP; k = k + 1) begin
                    if (mlw[k * NP + hh] < hmin) hmin = mlw[k * NP + hh];
                    if (mxw[k * NP + hh] > hmax) hmax = mxw[k * NP + hh];
                end
                $display("KVHOP hops=%0d lat_min=%0d lat_max=%0d", hh, hmin, hmax);
            end
            $display("ARGMAX tokens=%0d got=%0d errors=%0d faults=%0d first=%0d last=%0d q1=%0d q3=%0d",
                     NA, am_got, am_err, |a_fault, am_first, am_last, am_q1, am_q3);
            $finish;
        end
    end
endmodule
