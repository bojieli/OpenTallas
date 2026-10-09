`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// S81 HBM / SRAM protection (stream ds-control, 2026-10-08; gap F01 of the T2 coverage ledger).  AGENTS.md's ROM
// reliability policy (2026-10-02) removed ROM ECC but keeps "SRAM, HBM, link or mutable control-state protection";
// nothing on the S81 dies provided it.  This file holds the three protection blocks:
//
//   ot_s81_secded_enc72 / ot_s81_secded_dec72: SECDED(72,64), the ot_gpu_w6_secded_pkg bit layout (Hamming
//     positions 1..71 with check bits at the powers of two, overall parity at bit 71), the code the KV path's / the
//     near-HBM row client's SECDED72 and the Qwen emb-hbm stored copy already use.  Combinational XOR trees.
//   ot_s81_hbm_secded_wr: the HBM write path of one stack: a 32-B sector (256 b) + 32 check bits = four SECDED72
//     words, carried in the HBM3E ECC side-band (32 b per 32-B sector: no capacity cost).  One register stage
//     (+1 cycle on a write; writes are off the token path's dependency chain except the own-row KV write, where it
//     adds 1 cycle).
//   ot_s81_hbm_secded_rd: the HBM read-return path of one stack: syndrome + correction registered in two stages
//     (+2 cycles of read latency per HBM job: a scan / gather / window / RoPE stream pays it once, the stream rate is
//     unchanged).  A single-bit error in a 72-bit word is corrected (ce), a double-bit error is detected (ue: the
//     sector is flagged, the fault latched; the consumer fails closed).
//   ot_s81_sram_secded: a protected 1R1W SRAM wrapper for the dies' large SRAMs (W data bits, W/64 SECDED72 words a
//     row: +12.5 % bits); registered read as the macro, decode in one added register stage (+1 cycle read latency).
// MUT (bench negative controls): 1 = decoder detects but never corrects; 2 = encoder drops the overall parity bit.
// ---------------------------------------------------------------------------
module ot_s81_secded_enc72 #(parameter integer MUT = 0) (
    input  wire [63:0] d,
    output wire [71:0] c
);
    reg [71:0] x;
    integer p, k, j;
    always @(*) begin
        x = 72'd0; j = 0;
        for (p = 1; p <= 71; p = p + 1)
            if ((p & (p - 1)) != 0) begin x[p-1] = d[j]; j = j + 1; end
        for (k = 0; k < 7; k = k + 1)
            for (p = 1; p <= 71; p = p + 1)
                if ((p & (1 << k)) != 0 && p != (1 << k)) x[(1<<k)-1] = x[(1<<k)-1] ^ x[p-1];
        x[71] = (MUT == 2) ? 1'b0 : ^x[70:0];
    end
    assign c = x;
endmodule

module ot_s81_secded_dec72 #(parameter integer MUT = 0) (
    input  wire [71:0] c,
    output wire [63:0] d,
    output wire        ce,          // a single-bit error was corrected
    output wire        ue           // uncorrectable (double-bit) error detected
);
    reg [71:0] x; reg [6:0] sy; reg ov, ce_r, ue_r; reg [63:0] dd;
    integer p, k, j;
    always @(*) begin
        x = c; sy = 7'd0; ov = ^c; ce_r = 1'b0; ue_r = 1'b0;
        for (k = 0; k < 7; k = k + 1)
            for (p = 1; p <= 71; p = p + 1)
                if ((p & (1 << k)) != 0) sy[k] = sy[k] ^ c[p-1];
        if (sy != 0) begin
            if (ov && sy <= 7'd71) begin
                if (MUT != 1) x[sy-1] = ~x[sy-1];
                ce_r = 1'b1;
            end else ue_r = 1'b1;
        end else if (ov) begin
            x[71] = ~x[71]; ce_r = 1'b1;
        end
        dd = 64'd0; j = 0;
        for (p = 1; p <= 71; p = p + 1)
            if ((p & (p - 1)) != 0) begin dd[j] = x[p-1]; j = j + 1; end
    end
    assign d = dd; assign ce = ce_r; assign ue = ue_r;
endmodule

// HBM write path, one stack: {v, addr, 256-b sector} -> registered {v, addr, sector, 32 check bits}
module ot_s81_hbm_secded_wr #(parameter integer AW = 30, parameter integer MUT = 0) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            i_v,
    input  wire [AW-1:0]   i_a,
    input  wire [255:0]    i_d,
    output reg             o_v,
    output reg  [AW-1:0]   o_a,
    output reg  [255:0]    o_d,
    output reg  [31:0]     o_e
);
    wire [287:0] cw;
    genvar w;
    generate for (w = 0; w < 4; w = w + 1) begin : g_w
        ot_s81_secded_enc72 #(.MUT(MUT)) u_e (.d(i_d[64*w +: 64]), .c(cw[72*w +: 72]));
    end endgenerate
    // side-band = the 8 check bits of each word: positions 1,2,4,8,16,32,64 and 72 (bit 71)
    function automatic [7:0] chk(input [71:0] c);
        chk = {c[71], c[63], c[31], c[15], c[7], c[3], c[1], c[0]};
    endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) o_v <= 1'b0;
        else o_v <= i_v;
    always @(posedge clk) begin
        o_a <= i_a; o_d <= i_d;
        o_e <= {chk(cw[216 +: 72]), chk(cw[144 +: 72]), chk(cw[72 +: 72]), chk(cw[0 +: 72])};
    end
endmodule

// HBM read-return path, one stack: {v, tag, sector, check bits} -> 2 register stages -> corrected sector + flags
module ot_s81_hbm_secded_rd #(parameter integer TW = 20, parameter integer MUT = 0) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            i_v,
    input  wire [TW-1:0]   i_t,          // tag / beat / anything that travels with the data
    input  wire [255:0]    i_d,
    input  wire [31:0]     i_e,
    output reg             o_v,
    output reg  [TW-1:0]   o_t,
    output reg  [255:0]    o_d,
    output reg             o_ce,
    output reg             o_ue,
    output reg             fault,         // sticky: an uncorrectable sector was returned
    output reg  [31:0]     st_ce,
    output reg  [31:0]     st_ue
);
    // stage 1: rebuild the four 72-bit code words and register them
    reg          s1_v; reg [TW-1:0] s1_t; reg [287:0] s1_c;
    function automatic [71:0] cword(input [63:0] d, input [7:0] e);
        reg [71:0] x; integer p, j;
        begin
            x = 72'd0; j = 0;
            for (p = 1; p <= 71; p = p + 1)
                if ((p & (p - 1)) != 0) begin x[p-1] = d[j]; j = j + 1; end
            {x[71], x[63], x[31], x[15], x[7], x[3], x[1], x[0]} = e;
            cword = x;
        end
    endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) s1_v <= 1'b0; else s1_v <= i_v;
    always @(posedge clk) begin
        s1_t <= i_t;
        s1_c <= {cword(i_d[192 +: 64], i_e[24 +: 8]), cword(i_d[128 +: 64], i_e[16 +: 8]),
                 cword(i_d[64 +: 64], i_e[8 +: 8]), cword(i_d[0 +: 64], i_e[0 +: 8])};
    end
    // stage 2: syndrome, correction, flags
    wire [255:0] dd; wire [3:0] ce, ue;
    genvar w;
    generate for (w = 0; w < 4; w = w + 1) begin : g_w
        ot_s81_secded_dec72 #(.MUT(MUT)) u_d (.c(s1_c[72*w +: 72]), .d(dd[64*w +: 64]), .ce(ce[w]), .ue(ue[w]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            o_v <= 1'b0; o_ce <= 1'b0; o_ue <= 1'b0; fault <= 1'b0; st_ce <= 0; st_ue <= 0;
        end else begin
            o_v <= s1_v;
            o_ce <= s1_v && (|ce); o_ue <= s1_v && (|ue);
            if (s1_v && (|ue)) begin fault <= 1'b1; st_ue <= st_ue + 1; end
            if (s1_v && (|ce)) st_ce <= st_ce + 1;
        end
    end
    always @(posedge clk) begin o_t <= s1_t; o_d <= dd; end
endmodule

// Protected 1R1W SRAM (W data bits a row, W multiple of 64): registered read as the macro + one decode stage.
module ot_s81_sram_secded #(parameter integer W = 512, parameter integer DEPTH = 512, parameter integer MUT = 0,
                            parameter integer AW = $clog2(DEPTH), parameter integer NWD = W / 64) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            we,
    input  wire [AW-1:0]   wa,
    input  wire [W-1:0]    wd,
    input  wire            re,
    input  wire [AW-1:0]   ra,
    output reg             rv,            // read data valid (2 cycles after re)
    output reg  [W-1:0]    rd,
    output reg             ce,
    output reg             ue,
    output reg             fault,
    output reg  [31:0]     st_ce,
    output reg  [31:0]     st_ue,
    // bench / scrub access: flip stored bits (never driven in a die build)
    input  wire            inj_v,
    input  wire [AW-1:0]   inj_a,
    input  wire [NWD*72-1:0] inj_m
);
    reg [NWD*72-1:0] mem [0:DEPTH-1];
    wire [NWD*72-1:0] enc;
    genvar w;
    generate for (w = 0; w < NWD; w = w + 1) begin : g_e
        ot_s81_secded_enc72 #(.MUT(MUT)) u_e (.d(wd[64*w +: 64]), .c(enc[72*w +: 72]));
    end endgenerate
    always @(posedge clk) begin
        if (we) mem[wa] <= enc;
        else if (inj_v) mem[inj_a] <= mem[inj_a] ^ inj_m;
    end
    // macro read register
    reg r1_v; reg [NWD*72-1:0] r1_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) r1_v <= 1'b0; else r1_v <= re;
    always @(posedge clk) if (re) r1_q <= mem[ra];
    // decode stage
    wire [W-1:0] dd; wire [NWD-1:0] c1, u1;
    generate for (w = 0; w < NWD; w = w + 1) begin : g_d
        ot_s81_secded_dec72 #(.MUT(MUT)) u_d (.c(r1_q[72*w +: 72]), .d(dd[64*w +: 64]), .ce(c1[w]), .ue(u1[w]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rv <= 1'b0; ce <= 1'b0; ue <= 1'b0; fault <= 1'b0; st_ce <= 0; st_ue <= 0; end
        else begin
            rv <= r1_v; ce <= r1_v && (|c1); ue <= r1_v && (|u1);
            if (r1_v && (|u1)) begin fault <= 1'b1; st_ue <= st_ue + 1; end
            if (r1_v && (|c1)) st_ce <= st_ce + 1;
        end
    end
    always @(posedge clk) rd <= dd;
endmodule
