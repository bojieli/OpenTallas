`timescale 1ns/1ps
`default_nettype none
// HGI-1 vector memory core (hgi-takeover die integration, 2026-10-09; GH-d VM endpoint).
//
// 262,144 FP32 words = 32,768 sectors of 8 words, in NB = 32 banks (sector s: bank s[4:0], row s[14:5]); each bank is
// two ot_sram_1r1w_1024x256 macros side by side holding 8 x 39-bit words: every FP32 word carries its own (39,32)
// SECDED code (owner rule: mutable SRAM payload SECDED), so word-masked writes need no read-modify-write.  1R1W per
// bank per cycle.
//
// Clients (NC) speak the plain packet ABI of the qualified quant VM transport (ot_hgi_quant_vm_transport):
//   req 337 = {we 1, byte address 32 (sector aligned: [4:0] = 0), wdata 256, byte mask 32, tag 16}
//   rsp 273 = {tag 16, write echo 1, rdata 256}   (bit 256 echoes the request's we; a write returns 0 data)
// One request outstanding per client: a client is ready when its response slot is empty and its bank port (read or
// write) is granted.  Per bank and port the lowest-index requesting client wins.  Latency: grant edge (address at the macro
// pins) -> macro read edge -> rd_out capture flop -> correction into the response flop: 4 edges, reads and writes alike.
// Corrected single-bit errors count on ce; an uncorrectable word latches ue (sticky, fail-closed; the response still
// returns so the client's protocol drains) and its data is returned unmodified.  The mask is FP32-word granular: a
// word is written iff all 4 of its byte-mask bits are set; a partial word mask latches mask_fault.
module ot_hgi_vm_core #(
    parameter integer NC = 2,
    parameter integer OUT = 4,         // requests a client may have outstanding (VM fast path, review ~16:40); 1 = v1
    parameter integer WP = 1,          // wide write lanes (DMA streaming port, coordinator 2026-10-10: up to ~1 KB / cycle)
    parameter integer WDIRECT = 0,     // 1 (WP = 32): lane b writes bank b only (the DMA front routes by bank); a lane
                                       // whose sector is in another bank is dropped and latches wl_conflict
    parameter integer MUT = 0          // bench mutants: 1 no correction, 2 bank index from sector[5:1],
                                       //   3 write responses skip the read pipeline (out of order: must FAIL),
                                       //   4 the wide port ignores its word mask
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC-1:0]     req_v,
    output wire [NC-1:0]     req_r,
    input  wire [NC*337-1:0] req,
    output reg  [NC-1:0]     rsp_v,
    input  wire [NC-1:0]     rsp_r,
    output reg  [NC*273-1:0] rsp,      // FIFO head per client (in request order)
    output reg  [15:0]       ce,
    output reg               ue,
    output reg               mask_fault,
    // WIDE WRITE PORT (hgi-takeover 2026-10-10): WP lanes, each one whole-word-masked sector write a cycle
    //   {v, sector 15, wdata 256, word mask 8}; lanes of one cycle must address distinct banks (consecutive sectors do).
    //   Always accepted: a wide lane takes its bank's write port before any client (a client write to that bank waits
    //   one cycle); wl_done[p] pulses when lane p's write is in the macro (2 edges), so the writer can retire on it.
    input  wire [WP-1:0]     wl_v,
    input  wire [WP*15-1:0]  wl_sec,
    input  wire [WP*256-1:0] wl_d,
    input  wire [WP*8-1:0]   wl_m,
    output reg  [WP-1:0]     wl_done,
    output reg               wl_conflict,  // two lanes on one bank in a cycle (producer bug): sticky
    // fault injection (bench only; tie 0): flip bit b of word w of bank k on its next write
    input  wire              inj_v,
    input  wire [4:0]        inj_bank,
    input  wire [2:0]        inj_word,
    input  wire [38:0]       inj_mask
);
    localparam integer NB = 32;
    // ---------------------------------------------------------------- (39,32) SECDED (Hsiao-style odd-weight columns)
    function automatic [6:0] chk(input [31:0] d);
        integer i; reg [6:0] c; reg [6:0] col;
        begin
            c = 7'd0;
            for (i = 0; i < 32; i = i + 1) begin
                col = colv(i);
                if (d[i]) c = c ^ col;
            end
            chk = c;
        end
    endfunction
    // column of data bit i: the i-th 7-bit vector with 3 ones (35 of them; the first 32 used)
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1)
                for (b = a + 1; b < 7; b = b + 1)
                    for (c = b + 1; c < 7; c = c + 1) begin
                        if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                        n = n + 1;
                    end
            colv = v;
        end
    endfunction
    function automatic [38:0] enc(input [31:0] d);
        enc = {chk(d), d};
    endfunction
    // decode: {ue, ce, corrected data}
    function automatic [33:0] dec(input [38:0] w);
        reg [6:0] syn; integer i; reg [31:0] d; reg hit;
        begin
            d = w[31:0]; syn = chk(w[31:0]) ^ w[38:32]; hit = 1'b0;
            if (syn != 7'd0) begin
                for (i = 0; i < 32; i = i + 1) if (syn == colv(i)) begin d[i] = ~d[i]; hit = 1'b1; end
                // a check-bit error (weight-1 syndrome) leaves the data correct
                if (syn == 7'd1 || syn == 7'd2 || syn == 7'd4 || syn == 7'd8 || syn == 7'd16 || syn == 7'd32 || syn == 7'd64) hit = 1'b1;
            end
            dec = {(syn != 7'd0) && !hit, (syn != 7'd0) && hit, (MUT == 1) ? w[31:0] : d};
        end
    endfunction
    // ---------------------------------------------------------------- request fields
    wire          c_we   [0:NC-1];
    wire [14:0]   c_sec  [0:NC-1];
    wire [255:0]  c_wd   [0:NC-1];
    wire [31:0]   c_bm   [0:NC-1];
    wire [15:0]   c_tag  [0:NC-1];
    wire [4:0]    c_bank [0:NC-1];
    reg  [2:0]    ocnt [0:NC-1];                          // requests outstanding (granted, response not yet taken)
    reg  [NC-1:0] busy;

    genvar g, k;
    for (g = 0; g < NC; g = g + 1) begin : g_c
        wire [336:0] q = req[g*337 +: 337];
        assign c_tag[g] = q[15:0];
        assign c_bm[g]  = q[47:16];
        assign c_wd[g]  = q[303:48];
        assign c_sec[g] = q[323:309];                     // byte address [335:304]: sector = byte >> 5
        assign c_we[g]  = q[336];
        assign c_bank[g] = (MUT == 2) ? c_sec[g][5:1] : c_sec[g][4:0];
    end
    // ---------------------------------------------------------------- per bank arbitration (lowest index wins)
    reg [NC-1:0] gr_r [0:NB-1];
    reg [NC-1:0] gr_w [0:NB-1];
    integer b, c;
    // wide lanes per bank
    reg [NB-1:0] wb_hit; reg [4:0] wb_lane [0:NB-1]; reg [NB-1:0] wb_dup;
    always @* begin
        wb_hit = {NB{1'b0}}; wb_dup = {NB{1'b0}};
        for (integer ab = 0; ab < NB; ab = ab + 1) begin
            wb_lane[ab] = 5'd0;
            if (WDIRECT != 0) begin
                if (ab < WP) begin
                    wb_lane[ab] = 5'(ab);
                    wb_hit[ab] = wl_v[ab] && wl_sec[ab*15 +: 5] == 5'(ab);
                    wb_dup[ab] = wl_v[ab] && wl_sec[ab*15 +: 5] != 5'(ab);
                end
            end else
            for (integer ap = WP - 1; ap >= 0; ap = ap - 1)
                if (wl_v[ap] && wl_sec[ap*15 +: 5] == 5'(ab)) begin
                    if (wb_hit[ab]) wb_dup[ab] = 1'b1;
                    wb_hit[ab] = 1'b1; wb_lane[ab] = 5'(ap);
                end
        end
    end
    always @* begin
        for (integer ab = 0; ab < NB; ab = ab + 1) begin
            gr_r[ab] = {NC{1'b0}}; gr_w[ab] = {NC{1'b0}};
            for (integer ac = NC - 1; ac >= 0; ac = ac - 1) begin
                if (req_v[ac] && !busy[ac] && c_bank[ac] == ab && !c_we[ac]) gr_r[ab] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << ac);
                if (req_v[ac] && !busy[ac] && c_bank[ac] == ab &&  c_we[ac] && !wb_hit[ab]) gr_w[ab] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << ac);
            end
        end
    end
    reg [NC-1:0] acc;
    always @* begin
        acc = {NC{1'b0}};
        for (integer ab = 0; ab < NB; ab = ab + 1) acc = acc | gr_r[ab] | gr_w[ab];
    end
    assign req_r = acc;
    // ---------------------------------------------------------------- banks
    reg  [NB-1:0] m_re, m_we;
    reg  [9:0]    m_ra [0:NB-1];
    reg  [9:0]    m_wa [0:NB-1];
    reg  [311:0]  m_wd [0:NB-1];
    reg  [311:0]  m_wm [0:NB-1];
    wire [511:0]  m_rd [0:NB-1];
    reg  [NB-1:0] word_ok;
    integer w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m_re <= {NB{1'b0}}; m_we <= {NB{1'b0}}; mask_fault <= 1'b0; wl_conflict <= 1'b0; end
        else begin
            if (|wb_dup) wl_conflict <= 1'b1;
            for (b = 0; b < NB; b = b + 1) begin
                m_re[b] <= |gr_r[b]; m_we[b] <= |gr_w[b] | wb_hit[b];
                if (wb_hit[b]) begin : wide
                    integer lp; lp = wb_lane[b];
                    m_wa[b] <= wl_sec[lp*15 + 5 +: 10];
                    for (w = 0; w < 8; w = w + 1) begin
                        m_wd[b][w*39 +: 39] <= enc(wl_d[lp*256 + w*32 +: 32]);
                        m_wm[b][w*39 +: 39] <= {39{wl_m[lp*8 + w] | (MUT == 4)}};   // MUT 4: the word mask ignored
                    end
                end
                for (c = 0; c < NC; c = c + 1) begin
                    if (gr_r[b][c]) m_ra[b] <= c_sec[c][14:5];
                    if (gr_w[b][c]) begin
                        m_wa[b] <= c_sec[c][14:5];
                        for (w = 0; w < 8; w = w + 1) begin
                            m_wd[b][w*39 +: 39] <= enc(c_wd[c][w*32 +: 32]) ^ ((inj_v && inj_bank == b && inj_word == w) ? inj_mask : 39'd0);
                            m_wm[b][w*39 +: 39] <= {39{&c_bm[c][w*4 +: 4]}};
                            if (|c_bm[c][w*4 +: 4] && !(&c_bm[c][w*4 +: 4])) mask_fault <= 1'b1;
                        end
                    end
                end
            end
        end
    end
    for (k = 0; k < NB; k = k + 1) begin : g_bank
        wire [511:0] wd = {200'd0, m_wd[k]};
        wire [511:0] wm = {200'd0, m_wm[k]};
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(clk), .r_ce_in(m_re[k]), .r_addr_in(m_ra[k]), .rd_out(m_rd[k][255:0]),
            .w_ce_in(m_we[k]), .w_addr_in(m_wa[k]), .wd_in(wd[255:0]), .w_mask_in(wm[255:0]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(clk), .r_ce_in(m_re[k]), .r_addr_in(m_ra[k]), .rd_out(m_rd[k][511:256]),
            .w_ce_in(m_we[k]), .w_addr_in(m_wa[k]), .wd_in(wd[511:256]), .w_mask_in(wm[511:256]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end
    // ---------------------------------------------------------------- response pipeline (per client, one outstanding)
    reg [NC-1:0] p1_v, pm_v, p2_v;                // p1: address at the macro pins; pm: macro read edge; p2: rd_out captured
    reg [NC-1:0] p1_we, p2_we;
    reg [4:0]    p1_bank [0:NC-1];
    reg [15:0]   p1_tag [0:NC-1];
    reg [NC-1:0] pm_we;
    reg [4:0]    pm_bank [0:NC-1];
    reg [15:0]   pm_tag [0:NC-1];
    reg [15:0]   p2_tag [0:NC-1];
    reg [311:0]  p2_raw [0:NC-1];
    reg [33:0]   dw;
    reg [15:0]   ce_n;
    reg          ue_n;
    // per-client response FIFO (OUT deep, in request order): the pipeline always has room because a client never has
    // more than OUT requests outstanding
    reg [272:0] rf [0:4*NC-1];             // client c entry e at 4c + e (flat: simulator-safe)
    reg [1:0]   rf_h [0:NC-1];
    reg [1:0]   rf_t [0:NC-1];
    reg [2:0]   rf_n [0:NC-1];
    // head registers: a copy of each client's FIFO head kept in flops (simulators do not wake @* on array words)
    reg [272:0] rhd [0:NC-1]; reg [NC-1:0] rvn;
    for (g = 0; g < NC; g = g + 1) begin : g_rsp
        always @* begin rsp_v[g] = rvn[g]; rsp[g*273 +: 273] = rhd[g]; end
    end
    reg [272:0] pk; reg push, pop, wsk; reg [1:0] hn;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            p1_v <= {NC{1'b0}}; pm_v <= {NC{1'b0}}; p2_v <= {NC{1'b0}}; ce <= 16'd0; ue <= 1'b0;
            for (c = 0; c < NC; c = c + 1) begin ocnt[c] <= 3'd0; rf_h[c] <= 2'd0; rf_t[c] <= 2'd0; rf_n[c] <= 3'd0; end
            rvn <= {NC{1'b0}}; busy <= {NC{1'b0}};
        end else begin
            ce_n = 16'd0; ue_n = 1'b0;
            for (c = 0; c < NC; c = c + 1) begin
                if (acc[c]) begin p1_v[c] <= 1'b1; p1_we[c] <= c_we[c]; p1_bank[c] <= c_bank[c]; p1_tag[c] <= c_tag[c]; end
                else p1_v[c] <= 1'b0;
                wsk = (MUT == 3) && p1_v[c] && p1_we[c];         // mutant: a write answers from p1 (overtakes reads)
                pm_v[c] <= p1_v[c] && !wsk;
                if (p1_v[c]) begin pm_we[c] <= p1_we[c]; pm_tag[c] <= p1_tag[c]; pm_bank[c] <= p1_bank[c]; end
                p2_v[c] <= pm_v[c];
                if (pm_v[c]) begin p2_we[c] <= pm_we[c]; p2_tag[c] <= pm_tag[c]; end
                push = p2_v[c] || wsk;
                pk = 273'd0;
                if (wsk) pk = {p1_tag[c], 1'b1, 256'd0};
                else if (p2_v[c]) begin
                    for (w = 0; w < 8; w = w + 1) begin
                        dw = dec(p2_raw[c][w*39 +: 39]);
                        if (!p2_we[c]) begin
                            pk[w*32 +: 32] = dw[31:0];
                            if (dw[32]) ce_n = ce_n + 16'd1;
                            if (dw[33]) ue_n = 1'b1;
                        end
                    end
                    pk[256] = p2_we[c]; pk[257 +: 16] = p2_tag[c];
                end
                pop = rsp_v[c] && rsp_r[c];
                if (push) begin rf[4*c + rf_t[c]] <= pk; rf_t[c] <= rf_t[c] + 2'd1; end
                if (pop) rf_h[c] <= rf_h[c] + 2'd1;
                // the head after this edge: the next entry on a pop (or the pushed word if that empties into it)
                hn = rf_h[c] + 2'd1;
                if (pop) rhd[c] <= (rf_n[c] == 3'd1) ? pk : rf[4*c + hn];
                else if (rf_n[c] == 3'd0 && push) rhd[c] <= pk;
                rf_n[c] <= rf_n[c] + {2'd0, push} - {2'd0, pop};
                rvn[c] <= (rf_n[c] + {2'd0, push} - {2'd0, pop}) != 3'd0;
                ocnt[c] <= ocnt[c] + {2'd0, acc[c]} - {2'd0, pop};
                busy[c] <= (ocnt[c] + {2'd0, acc[c]} - {2'd0, pop}) >= 3'(OUT);
            end
            ce <= ce + ce_n;
            if (ue_n) ue <= 1'b1;
        end
    end
    reg [WP-1:0] wl_d1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wl_d1 <= {WP{1'b0}}; wl_done <= {WP{1'b0}}; end
        else begin wl_d1 <= wl_v; wl_done <= wl_d1; end
    // capture the macro output of the client's bank one edge after the access (rd_out is valid after the access edge)
    always @(posedge clk)
        for (integer pc = 0; pc < NC; pc = pc + 1)
            if (pm_v[pc]) p2_raw[pc] <= m_rd[pm_bank[pc]][311:0];
endmodule
`default_nettype wire
