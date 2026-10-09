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
    parameter integer MUT = 0          // bench mutants: 1 no correction, 2 bank index from sector[5:1]
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC-1:0]     req_v,
    output wire [NC-1:0]     req_r,
    input  wire [NC*337-1:0] req,
    output reg  [NC-1:0]     rsp_v,
    input  wire [NC-1:0]     rsp_r,
    output reg  [NC*273-1:0] rsp,
    output reg  [15:0]       ce,
    output reg               ue,
    output reg               mask_fault,
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
    reg  [NC-1:0] busy;                                   // response outstanding
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
    always @* begin
        for (b = 0; b < NB; b = b + 1) begin
            gr_r[b] = {NC{1'b0}}; gr_w[b] = {NC{1'b0}};
            for (c = NC - 1; c >= 0; c = c - 1) begin
                if (req_v[c] && !busy[c] && c_bank[c] == b && !c_we[c]) gr_r[b] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << c);
                if (req_v[c] && !busy[c] && c_bank[c] == b &&  c_we[c]) gr_w[b] = {NC{1'b0}} | ({{(NC-1){1'b0}}, 1'b1} << c);
            end
        end
    end
    reg [NC-1:0] acc;
    always @* begin
        acc = {NC{1'b0}};
        for (b = 0; b < NB; b = b + 1) acc = acc | gr_r[b] | gr_w[b];
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
        if (!rst_n) begin m_re <= {NB{1'b0}}; m_we <= {NB{1'b0}}; mask_fault <= 1'b0; end
        else begin
            for (b = 0; b < NB; b = b + 1) begin
                m_re[b] <= |gr_r[b]; m_we[b] <= |gr_w[b];
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
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= {NC{1'b0}}; p1_v <= {NC{1'b0}}; pm_v <= {NC{1'b0}}; p2_v <= {NC{1'b0}}; rsp_v <= {NC{1'b0}}; ce <= 16'd0; ue <= 1'b0;
        end else begin
            ce_n = 16'd0; ue_n = 1'b0;
            for (c = 0; c < NC; c = c + 1) begin
                if (acc[c]) begin busy[c] <= 1'b1; p1_v[c] <= 1'b1; p1_we[c] <= c_we[c]; p1_bank[c] <= c_bank[c]; p1_tag[c] <= c_tag[c]; end
                else p1_v[c] <= 1'b0;
                pm_v[c] <= p1_v[c];
                if (p1_v[c]) begin pm_we[c] <= p1_we[c]; pm_tag[c] <= p1_tag[c]; pm_bank[c] <= p1_bank[c]; end
                p2_v[c] <= pm_v[c];
                if (pm_v[c]) begin p2_we[c] <= pm_we[c]; p2_tag[c] <= pm_tag[c]; end
                if (p2_v[c]) begin
                    for (w = 0; w < 8; w = w + 1) begin
                        dw = dec(p2_raw[c][w*39 +: 39]);
                        if (!p2_we[c]) begin
                            rsp[c*273 + w*32 +: 32] <= dw[31:0];
                            if (dw[32]) ce_n = ce_n + 16'd1;
                            if (dw[33]) ue_n = 1'b1;
                        end else rsp[c*273 + w*32 +: 32] <= 32'd0;
                    end
                    rsp[c*273 + 256] <= p2_we[c];
                    rsp[c*273 + 257 +: 16] <= p2_tag[c];
                    rsp_v[c] <= 1'b1;
                end else if (rsp_v[c] && rsp_r[c]) begin
                    rsp_v[c] <= 1'b0; busy[c] <= 1'b0;
                end
            end
            ce <= ce + ce_n;
            if (ue_n) ue <= 1'b1;
        end
    end
    // capture the macro output of the client's bank one edge after the access (rd_out is valid after the access edge)
    always @(posedge clk)
        for (c = 0; c < NC; c = c + 1)
            if (pm_v[c]) p2_raw[c] <= m_rd[pm_bank[c]][311:0];
endmodule
`default_nettype wire
