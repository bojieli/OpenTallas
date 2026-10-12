`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_rgx_src (hgi-1010/a 2026-10-10, spec G25 hardware COLL.ROW_GATHER): one rank's SOURCE side.
//
// From the replicated selection list I (K <= 2,048 U32 row ids in VM, 16 ids a 512-bit word) it finds, in list order, the
// entries x this rank owns under the ROW_GATHER owner rule (id v: owner (v div B) mod G, local row (v div BG) B + v mod B),
// reads each owned row from its HBM row store (S <= 64 sectors of 32 B at A + local * stride) with up to RING sectors in
// flight on NL read lanes (any return order), and streams the row as F = ceil(S / 2) flits of 512 bits to the endpoint,
// flit f of entry x tagged gi = x * F + f.  Only owned rows leave the rank: no padding to the group's largest owned count,
// no slot loop, no per-slot gather epochs.  The endpoint multicasts each flit once; every destination writes gi straight
// to its list-order row store (O row x), so neither the slot-major array nor the inverse map R exists in this path.
//
//   list fetch (LBUF words outstanding + held) -> scan, one id a cycle (5 registered stages: id / shift / owner + local /
//   local x stride / + base) -> owned-row queue (OWNQ) -> sector issue (NL lanes through 2-entry request skids, lane =
//   ring slot parity, a row takes 2F slots: an odd S leaves one zero slot without a read) -> response pin flops ->
//   reorder ring (two 128 x 256 SRAM macros, even / odd slot = lane, one write port each; a valid bit a slot) -> pair read
//   (one 512-bit flit a cycle: macro read, capture flops with no logic before them, then the zero-half select) -> 4-entry
//   out FIFO (credit for the 2 read stages in flight).
//
// Faults (sticky until rst_n): an id >= 2^20, a malformed configuration.  rs_end (level) = this rank sent every owned
// flit: list scanned, every queue, the ring and the out FIFO empty.
module ot_hgi_coll_rgx_src #(
    parameter integer NL     = 2,      // HBM read lanes (sector parity); 2 = one 512-bit flit a cycle
    parameter integer RING   = 256,    // reorder ring, sectors (2 banks x RING/2 x 256 b: two 128 x 256 macros)
    parameter integer LBUF   = 4,      // list words outstanding + held
    parameter integer OWNQ   = 8,      // owned-row descriptors queued
    parameter integer METAQ  = 32,     // rows issued and not yet streamed
    parameter integer AW     = 35,     // HBM sector address bits
    parameter integer FW     = 512,
    parameter integer MUT_SLOT = 0,    // bench mutant: the flit tag uses the owner-local slot j instead of the list index x
    parameter integer MUT_OMAJ = 0,    // bench mutant: owner-major row r * ceil(K / G) + j (the superseded r * M + j layout)
    parameter integer MUT_DUP  = 0     // bench mutant: the first owned row is streamed twice
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    input  wire [11:0]          cfg_k,        // K - 1 is not used: K = 1 .. 2,048 (2,048 = 12'h800)
    input  wire [2:0]           cfg_lb,       // log2 B
    input  wire [7:0]           cfg_g,        // 1, 2, 4, 8, 96
    input  wire [7:0]           cfg_rrel,     // this rank's index in the group
    input  wire [AW-1:0]        cfg_abase,    // A: sector address of local row 0
    input  wire [15:0]          cfg_astride,  // A: sectors between rows
    input  wire [6:0]           cfg_sec,      // S: sectors a row (1 .. 64)
    input  wire [5:0]           cfg_nflit,    // F = ceil(S / 2)
    input  wire [31:0]          cfg_lbase,    // I: VM 512-bit word address of the list
    // list read (VM): in-order responses
    output wire                 lq_v,
    input  wire                 lq_rdy,
    output wire [31:0]          lq_addr,
    input  wire                 lr_v,
    input  wire [511:0]         lr_data,
    // HBM read lanes: any order, tag = ring slot
    output wire [NL-1:0]        hq_v,
    input  wire [NL-1:0]        hq_rdy,
    output wire [NL*AW-1:0]     hq_addr,
    output wire [NL*8-1:0]      hq_tag,
    input  wire [NL-1:0]        hr_v,
    input  wire [NL*8-1:0]      hr_tag,
    input  wire [NL*256-1:0]    hr_data,
    // flit stream to the endpoint
    output wire                 rs_v,
    output wire [15:0]          rs_gi,
    output wire [FW-1:0]        rs_data,
    input  wire                 rs_rdy,
    output reg                  rs_end,
    output wire                 busy,
    output reg                  fault
);
    localparam integer RA = $clog2(RING);
    // ---------------- run configuration ----------------
    reg run;
    reg [11:0] k_q; reg [2:0] lb_q; reg [7:0] g_q, rr_q; reg [AW-1:0] ab_q; reg [15:0] as_q; reg [6:0] sec_q; reg [5:0] f_q;
    reg [31:0] lb0_q; reg [1:0] lg_q; reg g96_q;
    wire [7:0] nwords = 8'(({1'b0, k_q} + 13'd15) >> 4);
    wire cfg_bad = (cfg_k == 12'd0) || (cfg_k > 12'd2048) ||
                   !(cfg_g == 8'd1 || cfg_g == 8'd2 || cfg_g == 8'd4 || cfg_g == 8'd8 || cfg_g == 8'd96) || (cfg_rrel >= cfg_g) ||
                   (cfg_sec == 7'd0) || (cfg_sec > 7'd64) || (cfg_nflit != 6'((cfg_sec + 7'd1) >> 1));
    // ---------------- list fetch ----------------
    reg [7:0] wq;                         // next word to request
    reg [2:0] lcnt;                       // requested + held words
    reg [511:0] lbuf [0:LBUF-1];
    reg [1:0] lb_wp, lb_rp; reg [2:0] lb_n;
    assign lq_v = run && (wq < nwords) && (lcnt < 3'(LBUF));
    assign lq_addr = lb0_q + {24'd0, wq};
    wire lq_fire = lq_v && lq_rdy;
    // ---------------- scan ----------------
    reg [3:0] e;                          // id within the head word
    reg [11:0] xs;                        // list index of the next id
    reg scan_done;
    reg v1, v2, v3, v4, v5; reg [11:0] x1, x2, x3, x4, x5; reg [31:0] id1; reg [AW-1:0] pr4; reg [11:0] j5;
    reg [19:0] t2; reg [6:0] lo2; reg [14:0] y2; reg bad2;
    reg [7:0] own3; reg [19:0] loc3; reg bad3;
    reg [AW-1:0] ad4; reg [11:0] j4;
    reg [11:0] jcnt;                      // owned entries found so far (the slot j of the next owned row)
    reg [3:0] oq_n;
    reg [AW-1:0] oq_a [0:OWNQ-1]; reg [11:0] oq_x [0:OWNQ-1];
    reg [2:0] oq_wp, oq_rp;
    wire [3:0] pipe_n = 4'(v1) + 4'(v2) + 4'(v3) + 4'(v4) + 4'(v5);
    wire scan_go = run && !scan_done && (lb_n != 3'd0) && (oq_n + pipe_n < 4'(OWNQ));
    wire last_id = (xs == k_q - 12'd1);
    wire lb_pop = scan_go && ((e == 4'd15) || last_id);
    // ---------------- sector issue / ring ----------------
    reg cur_v; reg [AW-1:0] cur_a; reg [6:0] cur_s; reg [15:0] cur_gi0; reg dup_done;
    reg [RA:0] tail, head;               // ring slot counters (RA+1 bits: full / empty)
    reg [RING-1:0] vb, zb;               // slot valid, slot is the zero half of an odd-S row
    // response pin flops, then the ring macros
    reg [NL-1:0] hp_v; reg [7:0] hp_tag [0:NL-1]; reg [255:0] hp_d [0:NL-1];
    wire [255:0] bank_q [0:NL-1];
    reg [5:0] mq_n; reg [15:0] mq_gi [0:METAQ-1]; reg [4:0] mq_wp, mq_rp;
    wire [7:0] s2f = {1'b0, f_q, 1'b0};  // slots a row takes
    reg [NL-1:0] iss; reg [RA:0] iss_n; reg [NL-1:0] zfill; reg [NL-1:0] kq_push;
    reg [AW+7:0] kq_din [0:NL-1];
    // per-lane request skid (2 entries): hq_v never depends on hq_rdy; the lanes drain independently (slots are
    // independent, the ring reorders)
    reg [AW+7:0] kq [0:NL-1][0:1]; reg [NL-1:0] kq_wp, kq_rp; reg [1:0] kq_n [0:NL-1];
    for (genvar l = 0; l < NL; l = l + 1) begin : g_kq
        assign hq_v[l] = (kq_n[l] != 2'd0);
        assign hq_addr[l*AW +: AW] = kq[l][kq_rp[l]][AW+7:8];
        assign hq_tag[l*8 +: 8] = kq[l][kq_rp[l]][7:0];
    end
    wire oq_empty = (oq_n == 4'd0);
    wire load_cur = run && !cur_v && !oq_empty && (mq_n < 6'(METAQ));
    always @* begin : issue
        reg ok;
        iss = '0; zfill = '0; iss_n = '0; kq_push = '0; ok = 1'b1;
        for (integer l = 0; l < NL; l = l + 1) kq_din[l] = '0;
        for (integer i = 0; i < NL; i = i + 1) begin : lane
            reg [RA:0] slot; reg [7:0] s; integer ln;
            slot = tail + (RA+1)'(i); s = {1'b0, cur_s} + 8'(i); ln = integer'(slot[0]);   // lane = slot parity = sector parity
            if (ok && cur_v && s < s2f && (tail - head + (RA+1)'(i)) < (RA+1)'(RING)) begin
                if (s < {1'b0, sec_q}) begin
                    if (kq_n[ln] != 2'd2) begin
                        iss[i] = 1'b1; kq_push[ln] = 1'b1;
                        kq_din[ln] = {cur_a + AW'(s), 8'(slot[RA-1:0])};
                    end else ok = 1'b0;
                end else begin iss[i] = 1'b1; zfill[i] = 1'b1; end      // the odd row's spare half: zero, no read
            end else ok = 1'b0;
            if (iss[i]) iss_n = iss_n + 1'b1;
        end
    end
    wire row_last = cur_v && (({1'b0, cur_s} + 8'(iss_n)) == s2f);
    // ---------------- flit read ----------------
    reg rd_v, rd_v2; reg [15:0] rd_gi, rd_gi2; reg [255:0] cap [0:1]; reg rd_z1, rd_z12;
    reg [FW+15:0] of [0:3]; reg [1:0] of_wp, of_rp; reg [2:0] of_n;
    reg [5:0] fcur;
    wire [RA-1:0] hs = head[RA-1:0];
    wire pair_ok = vb[hs] && vb[hs + 1'b1];
    wire rd_go = run && pair_ok && (mq_n != 6'd0) && (of_n + 3'(rd_v) + 3'(rd_v2) < 3'd4);
    for (genvar l = 0; l < NL; l = l + 1) begin : g_ring
        // one 128 x 256 macro a lane (RING / NL <= 128 slots); write from the response pin flops, read on rd_go
        ot_hcoll_sram128 #(.W(256)) u_bank (.clk(clk), .r_ce(rd_go), .r_addr(7'(hs >> 1)), .rd(bank_q[l]),
            .w_ce(hp_v[l]), .w_addr(7'(hp_tag[l] >> 1)), .wd(hp_d[l]));
    end
    assign rs_v = (of_n != 3'd0);
    assign rs_gi = of[of_rp][FW +: 16];
    assign rs_data = of[of_rp][FW-1:0];
    wire of_pop = rs_v && rs_rdy;
    assign busy = run;
    // ---------------- sequential ----------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; fault <= 1'b0; rs_end <= 1'b0;
            wq <= 0; lcnt <= 0; lb_wp <= 0; lb_rp <= 0; lb_n <= 0; e <= 0; xs <= 0; scan_done <= 1'b0;
            v1 <= 0; v2 <= 0; v3 <= 0; v4 <= 0; v5 <= 0; jcnt <= 0; hp_v <= '0; rd_v2 <= 1'b0; oq_n <= 0; oq_wp <= 0; oq_rp <= 0;
            cur_v <= 1'b0; cur_s <= 0; dup_done <= 1'b0; kq_wp <= '0; kq_rp <= '0;
            for (integer l = 0; l < NL; l = l + 1) kq_n[l] <= 2'd0; tail <= 0; head <= 0; vb <= '0; zb <= '0;
            mq_n <= 0; mq_wp <= 0; mq_rp <= 0; rd_v <= 1'b0; of_wp <= 0; of_rp <= 0; of_n <= 0; fcur <= 0;
            k_q <= 0; lb_q <= 0; g_q <= 8'd1; rr_q <= 0; ab_q <= 0; as_q <= 0; sec_q <= 7'd1; f_q <= 6'd1; lb0_q <= 0; lg_q <= 0; g96_q <= 0;
        end else begin
            if (start && !run) begin
                if (cfg_bad) fault <= 1'b1;
                else begin
                    run <= 1'b1; rs_end <= 1'b0;
                    k_q <= cfg_k; lb_q <= cfg_lb; g_q <= cfg_g; rr_q <= cfg_rrel; ab_q <= cfg_abase; as_q <= cfg_astride;
                    sec_q <= cfg_sec; f_q <= cfg_nflit; lb0_q <= cfg_lbase; g96_q <= (cfg_g == 8'd96);
                    lg_q <= (cfg_g == 8'd8) ? 2'd3 : (cfg_g == 8'd4) ? 2'd2 : (cfg_g == 8'd2) ? 2'd1 : 2'd0;
                    wq <= 0; lcnt <= 0; lb_wp <= 0; lb_rp <= 0; lb_n <= 0; e <= 0; xs <= 0; scan_done <= 1'b0;
                    jcnt <= 0; dup_done <= 1'b0; fcur <= 0;
                end
            end
            // list fetch
            if (lq_fire) wq <= wq + 8'd1;
            lcnt <= lcnt + 3'(lq_fire) - 3'(lb_pop);
            if (lr_v) begin lbuf[lb_wp] <= lr_data; lb_wp <= lb_wp + 2'd1; end
            lb_n <= lb_n + 3'(lr_v) - 3'(lb_pop);
            if (lb_pop) lb_rp <= lb_rp + 2'd1;
            // scan stage 1: the id
            v1 <= scan_go;
            if (scan_go) begin
                id1 <= lbuf[lb_rp][32*e +: 32]; x1 <= xs; xs <= xs + 12'd1; e <= (e == 4'd15 || last_id) ? 4'd0 : e + 4'd1;
                if (last_id) scan_done <= 1'b1;
            end
            // stage 2: v div B, v mod B, (v div B) div 32
            v2 <= v1; x2 <= x1;
            t2 <= id1[19:0] >> lb_q; lo2 <= 7'(id1[6:0] & ((7'd1 << lb_q) - 7'd1)); y2 <= 15'(id1[19:0] >> ({1'b0, lb_q} + 4'd5)); bad2 <= v1 && (id1[31:20] != 12'd0);
            // stage 3: owner = (v div B) mod G, local = ((v div B) div G) B + v mod B; G = 96: div 3 by reciprocal (y < 2^15)
            v3 <= v2; x3 <= x2; bad3 <= bad2;
            if (g96_q) begin : d96
                reg [30:0] pm; reg [14:0] q3; reg [1:0] m3;
                pm = {16'd0, y2} * 31'd21846; q3 = 15'(pm >> 16); m3 = 2'(y2 - 15'(q3 * 3));
                own3 <= {1'b0, m3, t2[4:0]}; loc3 <= (20'(q3) << lb_q) | 20'(lo2);
            end else begin
                own3 <= 8'(t2 & ((20'd1 << lg_q) - 20'd1)); loc3 <= ((t2 >> lg_q) << lb_q) | 20'(lo2);
            end
            // stage 4: owned? local x stride; stage 5: + base
            v4 <= v3 && (own3 == rr_q); x4 <= x3; j4 <= jcnt;
            pr4 <= AW'(loc3) * AW'(as_q);
            if (v3 && own3 == rr_q) jcnt <= jcnt + 12'd1;
            if (bad3) fault <= 1'b1;
            v5 <= v4; x5 <= x4; j5 <= j4; ad4 <= ab_q + pr4;
            // owned-row queue
            if (v5) begin
                oq_a[oq_wp] <= ad4;
                oq_x[oq_wp] <= (MUT_SLOT != 0) ? j5 : (MUT_OMAJ != 0) ? 12'(32'(rr_q) * ((32'(k_q) + 32'(g_q) - 1) / 32'(g_q)) + 32'(j5)) : x5;
                oq_wp <= oq_wp + 3'd1;
            end
            // row load (MUT_DUP: the first owned row is loaded twice)
            if (load_cur) begin
                cur_v <= 1'b1; cur_a <= oq_a[oq_rp]; cur_s <= 0;
                mq_gi[mq_wp] <= 16'(oq_x[oq_rp]) * 16'(f_q); mq_wp <= mq_wp + 5'd1;
                if (MUT_DUP != 0 && !dup_done) dup_done <= 1'b1; else oq_rp <= oq_rp + 3'd1;
            end
            oq_n <= oq_n + 4'(v5) - 4'(load_cur && !(MUT_DUP != 0 && !dup_done));
            // sector issue
            if (cur_v) begin
                cur_s <= cur_s + 7'(iss_n);
                if (row_last) cur_v <= 1'b0;
            end
            tail <= tail + iss_n;
            for (integer l = 0; l < NL; l = l + 1) begin
                if (kq_push[l]) begin kq[l][kq_wp[l]] <= kq_din[l]; kq_wp[l] <= ~kq_wp[l]; end
                if (hq_v[l] && hq_rdy[l]) kq_rp[l] <= ~kq_rp[l];
                kq_n[l] <= kq_n[l] + 2'(kq_push[l]) - 2'(hq_v[l] && hq_rdy[l]);
            end
            for (integer i = 0; i < NL; i = i + 1) if (zfill[i]) begin
                vb[(tail[RA-1:0] + RA'(i))] <= 1'b1; zb[(tail[RA-1:0] + RA'(i))] <= 1'b1;
            end
            // response pin flops -> macro write; the slot is valid from the write edge (read the next cycle at the earliest)
            for (integer l = 0; l < NL; l = l + 1) begin
                hp_v[l] <= hr_v[l]; hp_tag[l] <= hr_tag[l*8 +: 8]; hp_d[l] <= hr_data[l*256 +: 256];
                if (hp_v[l]) vb[hp_tag[l][RA-1:0]] <= 1'b1;
            end
            // flit read (registered read of both banks), out FIFO
            rd_v <= rd_go; rd_v2 <= rd_v;
            cap[0] <= bank_q[0]; cap[1] <= bank_q[1 % NL]; rd_gi2 <= rd_gi; rd_z12 <= rd_z1;   // capture: no logic before
            if (rd_go) begin
                rd_z1 <= zb[hs + 1'b1];
                rd_gi <= mq_gi[mq_rp] + 16'(fcur);
                vb[hs] <= 1'b0; vb[hs + 1'b1] <= 1'b0; zb[hs] <= 1'b0; zb[hs + 1'b1] <= 1'b0;
                head <= head + (RA+1)'(2);
                if (fcur == f_q - 6'd1) begin fcur <= 0; mq_rp <= mq_rp + 5'd1; end else fcur <= fcur + 6'd1;
            end
            mq_n <= mq_n + 6'(load_cur) - 6'(rd_go && fcur == f_q - 6'd1);
            if (rd_v2) begin of[of_wp] <= {rd_gi2, (rd_z12 ? 256'd0 : cap[1]), cap[0]}; of_wp <= of_wp + 2'd1; end
            if (of_pop) of_rp <= of_rp + 2'd1;
            of_n <= of_n + 3'(rd_v2) - 3'(of_pop);
            // end of stream
            if (run && scan_done && !v1 && !v2 && !v3 && !v4 && !v5 && oq_empty && !cur_v && mq_n == 0 && tail == head && !(|hq_v) &&
                !rd_v && !rd_v2 && of_n == 0 && !lr_v && lcnt == 0) begin
                run <= 1'b0; rs_end <= 1'b1;
            end
        end
    end
`ifndef SYNTHESIS
    initial if (NL != 2 || RING > 256 || RING % 2 != 0 || OWNQ != 8 || LBUF != 4 || METAQ != 32 || OWNQ < 6)
        $fatal(1, "ot_hgi_coll_rgx_src: built for NL 2, RING <= 256 (even), OWNQ 8, LBUF 4, METAQ 32");
`endif
endmodule
`default_nettype wire
