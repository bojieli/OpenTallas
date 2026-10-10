`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_bg -- bank-group TILE of the S81 VM memory subsystem (CLAUDE S81-PH vm v2, redesign pass).
// The v1 sub-macro ot_s81ph_vm_mem (NP 8, NB 32: 128 SRAM macros, 1015 x 2000 um, one 8-port x 32-bank crossbar)
// becomes a CHAIN of 4 of these tiles (1015.176 x 500.04 um each, 8 banks = 32 macros, R0, stacked S -> N... the
// chain runs N -> S): requests enter tile 0 and are forwarded tile to tile, read data flows the SAME way, merged by
// OR (every tile drives zeros for rows it does not hold), and leaves tile 3.  Each tile is ot_s81ph_vm_mem with
// NBL = 8 local banks of group grp (static pin), unchanged otherwise: the same in-order bank queues, the same fixed
// read latency, the same exact (issue cycle, port) order -- every bank lives in exactly one tile and every tile
// sees every request in the same order.
// Pins are flops: rq_i -> p_q (pin register) -> {the tile's ot_s81ph_vm_mem, the forward register rq_o};
// rp_i -> rp_q (pin register) -> OR with the tile's output register -> rp_o.  Both hops are 2 cycles, so tile k
// sees its requests 2k cycles after tile 0 and the merged read data of tiles 0 .. k-1 in the same cycle as its own.
// Read latency (request at tile 0's pins -> o_v / o_d at tile 3's pins) = L + 8 = QD + 14 cycles, fixed.
// Status (fault, code, max_occ) merges along the same chain (OR / max).
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_bg #(
    parameter integer NP = 8,
    parameter integer NB = 32,
    parameter integer NBL = 8,
    parameter integer QD = 4,
    parameter integer RQ = 8,
    parameter integer MACRO = 1,
    parameter integer DW = 512          // CLAUDE s81-blocks: row slice width (256: dsfd_vm_bgh bit-sliced half tile)
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rs,        // async reset (active low), synchronised in the tile
    input  wire [$clog2(NB/NBL)-1:0] grp, // static: this tile's bank group
    // request chain
    input  wire [NP-1:0]       i_v,
    input  wire [NP-1:0]       i_we,
    input  wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*(DW/32)-1:0] i_mask,
    input  wire [NP*DW-1:0]    i_d,
    output reg  [NP-1:0]       f_v,
    output reg  [NP-1:0]       f_we,
    output reg  [NP*($clog2(NB)+9)-1:0] f_row,
    output reg  [NP*(DW/32)-1:0] f_mask,
    output reg  [NP*DW-1:0]    f_d,
    // read data / status chain
    input  wire [NP-1:0]       r_v,
    input  wire [NP*DW-1:0]    r_d,
    input  wire [3:0]          r_f,       // {fault, code[2:0]}
    input  wire [$clog2(QD):0] r_o,       // max_occ
    output reg  [NP-1:0]       o_v,
    output reg  [NP*DW-1:0]    o_d,
    output reg  [3:0]          o_f,
    output reg  [$clog2(QD):0] o_o
);
    localparam integer RA = $clog2(NB) + 9;
    localparam integer OW = $clog2(QD) + 1;
    wire clk = ck[0];
    // reset: async assert, synchronised release (the wrapper flops reset; the core synchronises again)
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [NP-1:0] p_v, p_we; reg [NP*RA-1:0] p_row; reg [NP*(DW/32)-1:0] p_mask; reg [NP*DW-1:0] p_d;
    reg [NP-1:0] q_v; reg [NP*DW-1:0] q_d; reg [3:0] q_f; reg [OW-1:0] q_o;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin p_v <= 0; f_v <= 0; q_v <= 0; q_f <= 0; q_o <= 0; end
        else begin p_v <= i_v; f_v <= p_v; q_v <= r_v; q_f <= r_f; q_o <= r_o; end
    always @(posedge clk) begin
        p_we <= i_we; p_row <= i_row; p_mask <= i_mask; p_d <= i_d;
        f_we <= p_we; f_row <= p_row; f_mask <= p_mask; f_d <= p_d;
        q_d <= r_d;
    end
    wire [NP-1:0] m_v; wire [NP*DW-1:0] m_d; wire m_f; wire [2:0] m_c; wire [OW-1:0] m_o;
    ot_s81ph_vm_mem #(.NP(NP), .NB(NB), .QD(QD), .RQ(RQ), .MACRO(MACRO), .NBL(NBL), .DW(DW)) u_mem (.clk(clk), .rst_n(rst_n),
        .grp(grp), .i_v(p_v), .i_we(p_we), .i_row(p_row), .i_mask(p_mask), .i_d(p_d), .o_v(m_v), .o_d(m_d),
        .fault(m_f), .fault_code(m_c), .max_occ(m_o));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 0; o_f <= 0; o_o <= 0; end
        else begin
            o_v <= q_v | m_v;
            o_f <= q_f | {m_f, m_c};
            o_o <= (q_o > m_o) ? q_o : m_o;
        end
    always @(posedge clk) o_d <= q_d | m_d;
endmodule

// dsfd_vm_mem: the 4-tile chain (the composition netlist; bench target)
module dsfd_vm_mem #(parameter integer NP = 8, parameter integer NB = 32, parameter integer QD = 4, parameter integer RQ = 8,
                     parameter integer MACRO = 1) (
    input  wire clk, input wire rst_n,
    input  wire [NP-1:0] i_v, input wire [NP-1:0] i_we, input wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*16-1:0] i_mask, input wire [NP*512-1:0] i_d,
    output wire [NP-1:0] o_v, output wire [NP*512-1:0] o_d, output wire fault, output wire [2:0] fault_code,
    output wire [$clog2(QD):0] max_occ
);
    localparam integer NT = 4, NBL = NB / NT, RA = $clog2(NB) + 9, OW = $clog2(QD) + 1;
    wire [NP-1:0] cv [0:NT], cwe [0:NT], ov [0:NT];
    wire [NP*RA-1:0] crow [0:NT]; wire [NP*16-1:0] cmask [0:NT]; wire [NP*512-1:0] cd [0:NT], od [0:NT];
    wire [3:0] of [0:NT]; wire [OW-1:0] oo [0:NT];
    assign cv[0] = i_v; assign cwe[0] = i_we; assign crow[0] = i_row; assign cmask[0] = i_mask; assign cd[0] = i_d;
    assign ov[0] = 0; assign od[0] = 0; assign of[0] = 0; assign oo[0] = 0;
    genvar t;
    generate for (t = 0; t < NT; t = t + 1) begin : g_t
        wire [$clog2(NT)-1:0] gid = t;
        dsfd_vm_bg #(.NP(NP), .NB(NB), .NBL(NBL), .QD(QD), .RQ(RQ), .MACRO(MACRO)) u_bg (.ck(clk), .rs(rst_n), .grp(gid),
            .i_v(cv[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cmask[t]), .i_d(cd[t]),
            .f_v(cv[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cmask[t+1]), .f_d(cd[t+1]),
            .r_v(ov[t]), .r_d(od[t]), .r_f(of[t]), .r_o(oo[t]), .o_v(ov[t+1]), .o_d(od[t+1]), .o_f(of[t+1]), .o_o(oo[t+1]));
    end endgenerate
    assign o_v = ov[NT]; assign o_d = od[NT]; assign fault = of[NT][3]; assign fault_code = of[NT][2:0]; assign max_occ = oo[NT];
endmodule

// CLAUDE s81-blocks 2026-10-07: BIT-SLICED VM (vm_bg 37f7479aa: 1.02 M instances, global route congested 17 h).  The
// bank-group tile splits by row bits: dsfd_vm_bgh holds bits [256h, 256h + 256) of every row of its 8 banks (16
// macros, 1015.176 x 250.02 um).  Requests (v, we, row) go to both halves unchanged and each half sees its half of
// the data and mask, so every queue / due-slot / fault decision is the same function of the same inputs in both:
// read data = {hi, lo}, o_v / fault / max_occ identical (taken from lo; the bench asserts equality).  Same chain
// latency, zero added cycles.
module dsfd_vm_bgh #(parameter integer NP = 8, parameter integer NB = 32, parameter integer NBL = 8,
                     parameter integer QD = 4, parameter integer RQ = 8, parameter integer MACRO = 1) (
    input  wire [0:0] ck, input wire [0:0] rs, input wire [$clog2(NB/NBL)-1:0] grp,
    input  wire [NP-1:0] i_v, input wire [NP-1:0] i_we, input wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*8-1:0] i_mask, input wire [NP*256-1:0] i_d,
    output wire [NP-1:0] f_v, output wire [NP-1:0] f_we, output wire [NP*($clog2(NB)+9)-1:0] f_row,
    output wire [NP*8-1:0] f_mask, output wire [NP*256-1:0] f_d,
    input  wire [NP-1:0] r_v, input wire [NP*256-1:0] r_d, input wire [3:0] r_f, input wire [$clog2(QD):0] r_o,
    output wire [NP-1:0] o_v, output wire [NP*256-1:0] o_d, output wire [3:0] o_f, output wire [$clog2(QD):0] o_o
);
    dsfd_vm_bg #(.NP(NP), .NB(NB), .NBL(NBL), .QD(QD), .RQ(RQ), .MACRO(MACRO), .DW(256)) u (.ck(ck), .rs(rs), .grp(grp),
        .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_mask), .i_d(i_d), .f_v(f_v), .f_we(f_we), .f_row(f_row),
        .f_mask(f_mask), .f_d(f_d), .r_v(r_v), .r_d(r_d), .r_f(r_f), .r_o(r_o), .o_v(o_v), .o_d(o_d), .o_f(o_f), .o_o(o_o));
endmodule

// dsfd_vm_mem_s: NS bit-sliced chains of 4 tiles (NS 2: dsfd_vm_bgh, NS 4: dsfd_vm_bgq), same ports as dsfd_vm_mem
module dsfd_vm_mem_s #(parameter integer NS = 2, parameter integer NP = 8, parameter integer NB = 32, parameter integer QD = 4,
                       parameter integer RQ = 8, parameter integer MACRO = 1) (
    input  wire clk, input wire rst_n,
    input  wire [NP-1:0] i_v, input wire [NP-1:0] i_we, input wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*16-1:0] i_mask, input wire [NP*512-1:0] i_d,
    output wire [NP-1:0] o_v, output wire [NP*512-1:0] o_d, output wire fault, output wire [2:0] fault_code,
    output wire [$clog2(QD):0] max_occ,
    output wire slice_mismatch          // bench: the slices' control outputs differ (never, by construction)
);
    localparam integer NT = 4, NBL = NB / NT, RA = $clog2(NB) + 9, OW = $clog2(QD) + 1, SW = 512 / NS, SM = 16 / NS;
    wire [NP-1:0] ovh [0:NS-1]; wire [3:0] ofh [0:NS-1]; wire [OW-1:0] ooh [0:NS-1]; wire [NP*SW-1:0] odh [0:NS-1];
    genvar h, t, pp;
    generate for (h = 0; h < NS; h = h + 1) begin : g_h
        wire [NP*SM-1:0] mk; wire [NP*SW-1:0] dh;
        for (pp = 0; pp < NP; pp = pp + 1) begin : g_p
            assign mk[SM*pp +: SM] = i_mask[16*pp + SM*h +: SM];
            assign dh[SW*pp +: SW] = i_d[512*pp + SW*h +: SW];
            assign o_d[512*pp + SW*h +: SW] = odh[h][SW*pp +: SW];
        end
        wire [NP-1:0] cv [0:NT], cwe [0:NT], ov [0:NT];
        wire [NP*RA-1:0] crow [0:NT]; wire [NP*SM-1:0] cmask [0:NT]; wire [NP*SW-1:0] cd [0:NT], od [0:NT];
        wire [3:0] of [0:NT]; wire [OW-1:0] oo [0:NT];
        assign cv[0] = i_v; assign cwe[0] = i_we; assign crow[0] = i_row; assign cmask[0] = mk; assign cd[0] = dh;
        assign ov[0] = 0; assign od[0] = 0; assign of[0] = 0; assign oo[0] = 0;
        for (t = 0; t < NT; t = t + 1) begin : g_t
            wire [$clog2(NT)-1:0] gid = t;
            if (NS == 2) begin : g_bgh
            dsfd_vm_bgh #(.NP(NP), .NB(NB), .NBL(NBL), .QD(QD), .RQ(RQ), .MACRO(MACRO)) u_bg (.ck(clk), .rs(rst_n), .grp(gid),
                .i_v(cv[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cmask[t]), .i_d(cd[t]),
                .f_v(cv[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cmask[t+1]), .f_d(cd[t+1]),
                .r_v(ov[t]), .r_d(od[t]), .r_f(of[t]), .r_o(oo[t]), .o_v(ov[t+1]), .o_d(od[t+1]), .o_f(of[t+1]), .o_o(oo[t+1]));
            end else begin : g_bgq
            dsfd_vm_bgq #(.NP(NP), .NB(NB), .NBL(NBL), .QD(QD), .RQ(RQ), .MACRO(MACRO)) u_bg (.ck(clk), .rs(rst_n), .grp(gid),
                .i_v(cv[t]), .i_we(cwe[t]), .i_row(crow[t]), .i_mask(cmask[t]), .i_d(cd[t]),
                .f_v(cv[t+1]), .f_we(cwe[t+1]), .f_row(crow[t+1]), .f_mask(cmask[t+1]), .f_d(cd[t+1]),
                .r_v(ov[t]), .r_d(od[t]), .r_f(of[t]), .r_o(oo[t]), .o_v(ov[t+1]), .o_d(od[t+1]), .o_f(of[t+1]), .o_o(oo[t+1]));
            end
        end
        assign ovh[h] = ov[NT]; assign ofh[h] = of[NT]; assign ooh[h] = oo[NT]; assign odh[h] = od[NT];
    end endgenerate
    reg mism; reg [3:0] fo; integer k;
    always @* begin
        mism = 1'b0; fo = 4'd0;
        for (k = 0; k < NS; k = k + 1) begin
            fo = fo | ofh[k];
            if (ovh[k] != ovh[0] || ofh[k] != ofh[0] || ooh[k] != ooh[0]) mism = 1'b1;
        end
    end
    assign o_v = ovh[0]; assign fault = fo[3]; assign fault_code = fo[2:0]; assign max_occ = ooh[0];
    assign slice_mismatch = mism;
endmodule

// dsfd_vm_bgq: quarter slice (128 b of every row: 8 macros, 253.794 x 500.04 um), as dsfd_vm_bgh
module dsfd_vm_bgq #(parameter integer NP = 8, parameter integer NB = 32, parameter integer NBL = 8,
                     parameter integer QD = 4, parameter integer RQ = 8, parameter integer MACRO = 1) (
    input  wire [0:0] ck, input wire [0:0] rs, input wire [$clog2(NB/NBL)-1:0] grp,
    input  wire [NP-1:0] i_v, input wire [NP-1:0] i_we, input wire [NP*($clog2(NB)+9)-1:0] i_row,
    input  wire [NP*4-1:0] i_mask, input wire [NP*128-1:0] i_d,
    output wire [NP-1:0] f_v, output wire [NP-1:0] f_we, output wire [NP*($clog2(NB)+9)-1:0] f_row,
    output wire [NP*4-1:0] f_mask, output wire [NP*128-1:0] f_d,
    input  wire [NP-1:0] r_v, input wire [NP*128-1:0] r_d, input wire [3:0] r_f, input wire [$clog2(QD):0] r_o,
    output wire [NP-1:0] o_v, output wire [NP*128-1:0] o_d, output wire [3:0] o_f, output wire [$clog2(QD):0] o_o
);
    dsfd_vm_bg #(.NP(NP), .NB(NB), .NBL(NBL), .QD(QD), .RQ(RQ), .MACRO(MACRO), .DW(128)) u (.ck(ck), .rs(rs), .grp(grp),
        .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_mask), .i_d(i_d), .f_v(f_v), .f_we(f_we), .f_row(f_row),
        .f_mask(f_mask), .f_d(f_d), .r_v(r_v), .r_d(r_d), .r_f(r_f), .r_o(r_o), .o_v(o_v), .o_d(o_d), .o_f(o_f), .o_o(o_o));
endmodule
