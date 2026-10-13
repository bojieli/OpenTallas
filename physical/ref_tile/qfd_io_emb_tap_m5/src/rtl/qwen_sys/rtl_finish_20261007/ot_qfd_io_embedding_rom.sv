`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_io_embedding_rom: the root / column adapter between the embedding ROM banks and the die IO
// (qwen-rtl-finish 2026-10-07).
//
// The ROM: 2,374 code banks (ot_qwen_embed_code_bank_parent: 4,096 x 512-b code words each, 64 vocabulary rows) and 3
// scale banks (ot_qwen_embed_scale_bank_parent: 65,536 BF16 row scales each), all with the credit protocol of the bank
// parents (request: upstream starts with 2 credits, i_cr returns one; response: the bank holds OCRED seats, o_cr returns
// one).  The die face (r21 buses emb_a / emb): one request word {kind, address} with a credit return, one 512-b
// response word with a valid, in request order.
//
//   ot_qfd_emb_root   (one, at the block's die face)  request FIFO of CRD entries (its credits are the die-side
//                     credits), bank decode (code word a -> bank a >> 12, line a & 4095; scale row r -> scale bank
//                     NCODE + (r >> 16), line r & 65535), column = bank mod NCOL, tap = bank / NCOL; issues at most one
//                     request every two edges (the banks' read cadence), at most RW outstanding, and only to ONE bank at
//                     a time (a request to another bank waits until every response is back), so responses return in
//                     request order without tags.  The 64 code words of a token are one bank: they stream at one per
//                     two edges.  Responses (one column active) are OR-merged and registered out.
//   ot_qfd_emb_tap    (one beside each bank parent)   a registered hop on the column's request chain (down) and
//                     response chain (up); it takes the requests addressed to its bank into a 4-entry FIFO, launches
//                     them on the bank's credits, and puts the bank's response on the up chain (the slot is free: one
//                     bank is active), returning the bank's seat at once.
// Every port of both is registered (the chains are relay stations: one hop a tap, <= 100 um with a tap per bank).
// ot_qfd_io_embedding_rom assembles root + NCOL columns of taps + the banks (behavioural banks with the parents'
// protocol for simulation, BANK_BEH = 1; the bank parents are their own die-level element masters).
// MUT = 1: the root decodes the column with one bank off (the bench must FAIL).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_emb_root #(
    parameter integer AW = 24,
    parameter integer NCOL = 8,
    parameter integer NTAP = 297,             // taps a column
    parameter integer NCODE = 2374,           // code banks; scale banks follow
    parameter integer LWB = 12,               // code words a bank: 2^LWB
    parameter integer LSB = 16,               // scales a scale bank: 2^LSB
    parameter integer CRD = 4,
    parameter integer RW = 4,
    parameter integer MUT = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // die face
    input  wire                 ea_v,
    input  wire                 ea_kind,
    input  wire [AW-1:0]        ea_addr,
    output reg                  ea_cr,
    output reg                  eq_v,
    output reg  [511:0]         eq_data,
    // columns
    output reg  [NCOL-1:0]      c_v,
    output reg  [$clog2(NTAP)-1:0] c_tap,
    output reg  [17:0]          c_line,
    input  wire [NCOL-1:0]      r_v,
    input  wire [NCOL*512-1:0]  r_data,
    output reg                  fault
);
    localparam integer LT = $clog2(NTAP);
    localparam integer LC = (NCOL > 1) ? $clog2(NCOL) : 1;
    localparam integer LF = $clog2(CRD);
    // input register + FIFO
    reg iv, ik; reg [AW-1:0] ia;
    always @(posedge clk or negedge rst_n) if (!rst_n) iv <= 1'b0; else iv <= ea_v;
    always @(posedge clk) begin ik <= ea_kind; ia <= ea_addr; end
    reg [AW:0] fq [0:CRD-1];
    reg [LF:0] wp, rp;
    wire empty = wp == rp;
    // decode of the head request (registered one stage before it is issued)
    wire hk = fq[rp[LF-1:0]][AW];
    wire [AW-1:0] ha = fq[rp[LF-1:0]][AW-1:0];
    wire [31:0] hbank = hk ? (NCODE + (ha >> LSB)) : (ha >> LWB);
    wire [17:0] hline = hk ? (ha & ((1 << LSB) - 1)) : (ha & ((1 << LWB) - 1));
    reg  [31:0] cur_bank;
    reg  [3:0]  outst;
    reg         gap;
    wire        can = !empty && !gap && outst < RW && (outst == 0 || hbank == cur_bank);
    wire [31:0] mbank = hbank + ((MUT != 0) ? 1 : 0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wp <= 0; rp <= 0; outst <= 0; gap <= 1'b0; c_v <= 0; ea_cr <= 1'b0; eq_v <= 1'b0; fault <= 1'b0;
            cur_bank <= 0;
        end else begin
            c_v <= 0; ea_cr <= 1'b0; gap <= 1'b0;
            if (iv) begin
                if (wp - rp == CRD) fault <= 1'b1;
                wp <= wp + 1'b1;
            end
            if (can) begin
                c_v[mbank % NCOL] <= 1'b1;
                c_tap <= mbank / NCOL; c_line <= hline; cur_bank <= hbank;
                rp <= rp + 1'b1; ea_cr <= 1'b1; gap <= 1'b1;
                if (hbank >= NCOL * NTAP) fault <= 1'b1;
            end
            eq_v <= |r_v;
            outst <= outst + (can ? 1'b1 : 1'b0) - ((|r_v) ? 1'b1 : 1'b0);
            if ((r_v & (r_v - 1'b1)) != 0 || ((|r_v) && outst == 0)) fault <= 1'b1;
        end
    end
    always @(posedge clk) if (iv) fq[wp[LF-1:0]] <= {ik, ia};
    integer c;
    reg [511:0] m;
    always @(*) begin
        m = 512'd0;
        for (c = 0; c < NCOL; c = c + 1) if (r_v[c]) m = m | r_data[c*512 +: 512];
    end
    always @(posedge clk) eq_data <= m;
endmodule


module ot_qfd_emb_tap #(
    parameter integer LT = 9,
    parameter integer ID = 0,
    parameter integer QD = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    // request chain (down)
    input  wire          d_v,
    input  wire [LT-1:0] d_tap,
    input  wire [17:0]   d_line,
    output reg           n_v,
    output reg  [LT-1:0] n_tap,
    output reg  [17:0]   n_line,
    // response chain (up)
    input  wire          u_v,
    input  wire [511:0]  u_data,
    output reg           p_v,
    output reg  [511:0]  p_data,
    // the bank
    output reg           b_iv,
    output reg  [17:0]   b_iaddr,
    input  wire          b_icr,
    input  wire          b_ov,
    input  wire [511:0]  b_odata,
    output reg           b_ocr,
    output reg           fault
);
    localparam integer LQ = $clog2(QD);
    reg [17:0] q [0:QD-1];
    reg [LQ:0] wp, rp;
    reg [1:0] cr;
    wire mine = d_v && d_tap == ID;
    wire launch = (wp != rp) && (cr != 0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n_v <= 1'b0; p_v <= 1'b0; b_iv <= 1'b0; b_ocr <= 1'b0; wp <= 0; rp <= 0; cr <= 2'd2; fault <= 1'b0;
        end else begin
            n_v <= d_v && !mine;
            p_v <= u_v || b_ov;
            b_ocr <= b_ov;
            b_iv <= launch;
            if (mine) wp <= wp + 1'b1;
            if (launch) rp <= rp + 1'b1;
            cr <= cr - (launch ? 2'd1 : 2'd0) + (b_icr ? 2'd1 : 2'd0);
            if ((u_v && b_ov) || (mine && wp - rp == QD) || (b_icr && cr == 2'd2 && !launch)) fault <= 1'b1;
        end
    end
    always @(posedge clk) begin
        n_tap <= d_tap; n_line <= d_line;
        if (mine) q[wp[LQ-1:0]] <= d_line;
        if (launch) b_iaddr <= q[rp[LQ-1:0]];
        p_data <= b_ov ? b_odata : u_data;
    end
endmodule


// Behavioural bank with the bank parents' protocol (simulation): a 2-entry request queue (its credits returned on
// launch), a launch every second edge when a seat is free, the word three edges after the launch (two-edge macro read +
// the output register).  Contents: code word = ot_qfd_emb_word(bank * 4096 + line); scale row = ot_qfd_emb_scale(...).
module ot_qfd_emb_bank_beh #(
    parameter integer BANK = 0,
    parameter integer NCODE = 2374,
    parameter integer LWB = 12,
    parameter integer LSB = 16,
    parameter integer OCRED = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         i_v,
    input  wire [17:0]  i_addr,
    output reg          i_cr,
    output reg          o_v,
    output reg  [511:0] o_data,
    input  wire         o_cr
);
    reg [17:0] q [0:1];
    reg [1:0] wp, rp;
    reg [2:0] seats;
    reg ph;
    reg [2:0] vp;
    reg [17:0] ap0, ap1;
    wire launch = !ph && wp != rp && seats != 0;
    function automatic [511:0] word(input [31:0] a);
        integer k; reg [31:0] h;
        begin
            for (k = 0; k < 16; k = k + 1) begin
                h = (a * 32'h9E3779B1) ^ (k * 32'h85EBCA6B); h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; word[32*k +: 32] = h ^ (h >> 12);
            end
        end
    endfunction
    // yosys cannot parse a part-select of a function return (word(...)[15:0]): name both words first (same expressions)
    wire [511:0] w_scale = word(32'h8000_0000 | (((BANK - NCODE) << LSB) + ap1));
    wire [511:0] w_code  = word((BANK << LWB) + ap1);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin wp <= 0; rp <= 0; seats <= OCRED; ph <= 1'b0; vp <= 0; i_cr <= 1'b0; o_v <= 1'b0; end
        else begin
            i_cr <= launch; ph <= launch;
            if (i_v) wp <= wp + 1'b1;
            if (launch) rp <= rp + 1'b1;
            vp <= {vp[1:0], launch};
            o_v <= vp[1];
            seats <= seats - (launch ? 3'd1 : 3'd0) + (o_cr ? 3'd1 : 3'd0);
        end
    end
    always @(posedge clk) begin
        if (i_v) q[wp[0]] <= i_addr;
        if (launch) ap0 <= q[rp[0]];
        ap1 <= ap0;
        if (vp[1]) o_data <= (BANK >= NCODE) ? {496'd0, w_scale[15:0]} : w_code;
    end
endmodule


module ot_qfd_io_embedding_rom #(
    parameter integer AW = 24,
    parameter integer NCOL = 8,
    parameter integer NTAP = 297,
    parameter integer NCODE = 2374,
    parameter integer NSCALE = 3,
    parameter integer LWB = 12,
    parameter integer LSB = 16,
    parameter integer CRD = 4,
    parameter integer RW = 4,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          ea_v,
    input  wire          ea_kind,
    input  wire [AW-1:0] ea_addr,
    output wire          ea_cr,
    output wire          eq_v,
    output wire [511:0]  eq_data,
    output wire          fault
);
    localparam integer LT = (NTAP > 1) ? $clog2(NTAP) : 1;
    wire [NCOL-1:0] c_v, r_v;
    wire [LT-1:0] c_tap;
    wire [17:0] c_line;
    wire [NCOL*512-1:0] r_data;
    wire rf;
    wire [NCOL*NTAP-1:0] tf;
    ot_qfd_emb_root #(.AW(AW), .NCOL(NCOL), .NTAP(NTAP), .NCODE(NCODE), .LWB(LWB), .LSB(LSB), .CRD(CRD), .RW(RW),
        .MUT(MUT)) u_root (.clk(clk), .rst_n(rst_n), .ea_v(ea_v), .ea_kind(ea_kind), .ea_addr(ea_addr), .ea_cr(ea_cr),
        .eq_v(eq_v), .eq_data(eq_data), .c_v(c_v), .c_tap(c_tap), .c_line(c_line), .r_v(r_v), .r_data(r_data),
        .fault(rf));
    genvar col, t;
    generate for (col = 0; col < NCOL; col = col + 1) begin : g_col
        wire [NTAP:0] dv, uv;
        wire [(NTAP+1)*LT-1:0] dt;
        wire [(NTAP+1)*18-1:0] dl;
        wire [(NTAP+1)*512-1:0] ud;
        assign dv[0] = c_v[col]; assign dt[0 +: LT] = c_tap; assign dl[0 +: 18] = c_line;
        assign uv[NTAP] = 1'b0; assign ud[NTAP*512 +: 512] = 512'd0;
        for (t = 0; t < NTAP; t = t + 1) begin : g_tap
            localparam integer BANK = t * NCOL + col;
            wire b_iv, b_icr, b_ov, b_ocr;
            wire [17:0] b_ia;
            wire [511:0] b_od;
            ot_qfd_emb_tap #(.LT(LT), .ID(t)) u_tap (.clk(clk), .rst_n(rst_n),
                .d_v(dv[t]), .d_tap(dt[t*LT +: LT]), .d_line(dl[t*18 +: 18]),
                .n_v(dv[t+1]), .n_tap(dt[(t+1)*LT +: LT]), .n_line(dl[(t+1)*18 +: 18]),
                .u_v(uv[t+1]), .u_data(ud[(t+1)*512 +: 512]), .p_v(uv[t]), .p_data(ud[t*512 +: 512]),
                .b_iv(b_iv), .b_iaddr(b_ia), .b_icr(b_icr), .b_ov(b_ov), .b_odata(b_od), .b_ocr(b_ocr),
                .fault(tf[col*NTAP + t]));
            if (BANK < NCODE + NSCALE) begin : g_bank
                ot_qfd_emb_bank_beh #(.BANK(BANK), .NCODE(NCODE), .LWB(LWB), .LSB(LSB)) u_bank (.clk(clk), .rst_n(rst_n),
                    .i_v(b_iv), .i_addr(b_ia), .i_cr(b_icr), .o_v(b_ov), .o_data(b_od), .o_cr(b_ocr));
            end else begin : g_none
                assign b_icr = 1'b0; assign b_ov = 1'b0; assign b_od = 512'd0;
            end
        end
        assign r_v[col] = uv[0];
        assign r_data[col*512 +: 512] = ud[0 +: 512];
    end endgenerate
    assign fault = rf | (|tf);
endmodule
