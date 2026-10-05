`timescale 1ns/1ps
// Rung-5 die-slice assembly for the Qwen O4 ROM die: one row of N routed
// ROM/MAC neighbourhood abstracts (ot_qwen_o4_g4_rommac, SCALE_BANKS = 0)
// running from the spine end (tile 0) to the die edge, with the top-level
// glue the floorplan's corridors carry:
//
//  * issue broadcast: the instruction fields and go, registered once per
//    tile hop (one tile pitch is below the 1.10 mm a cycle the routed
//    express links allow at 0.910 ns with 60 ps uncertainty);
//  * x stream: each tile's four 32-bit operands, carried on a pipeline that
//    drops one tile's slice at every hop (the VM streams x one way);
//  * split tree above the tile: tile t's first result word (16 lanes of
//    FP32) is summed pairwise with its neighbours by ot_hdc_qadd, one level
//    per doubling, each level ending in a register, and the root result is
//    returned to the spine end on a registered pipeline;
//  * the KV operand is tile-local (the ring slice is in the tile) and is tied
//    here; faults and progress are OR-reduced.
//
// The glue is physical-composition logic, not a functional slice of the
// monolithic ot_hdc_matvec (see qwen_o4_die_inventory.json, 'physical
// partition'): it has the widths, registers and adders the corridors must
// hold, so its route answers whether abstracts plus glue compose at the clock.
module ot_qwen_o4_die_row #(
    parameter integer N  = 14,
    parameter integer AW = 24,
    parameter integer NW = 16
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                go,
    input  wire [NW-1:0]       i_nout, i_tiles, i_k,
    input  wire [AW-1:0]       i_wbase, i_ts, i_ks, i_xbase, i_xks, i_xcs, i_wcs, i_obase, i_ots, i_ojs,
    input  wire [3:0]          i_split,
    input  wire                i_amax,
    input  wire [N*128-1:0]    x_in,          // one 4 x 32-bit operand set per tile, from the VM end
    output reg  [16*32-1:0]    root_data,
    output reg                 root_v,
    output reg  [N-1:0]        x_req,
    output reg                 fault_any
);
    localparam integer IB = 3 * NW + 10 * AW + 4 + 1;      // issue bundle width
    localparam integer LV = $clog2(N);
    wire [IB-1:0] issue_in = {i_nout, i_tiles, i_k, i_wbase, i_ts, i_ks, i_xbase, i_xks, i_xcs, i_wcs,
                              i_obase, i_ots, i_ojs, i_split, i_amax};
    // ---- issue pipeline: stage t feeds tile t -------------------------------------------
    reg [IB-1:0] iss [0:N-1];
    reg [N-1:0]  go_p;
    integer t;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) go_p <= {N{1'b0}};
        else begin
            go_p[0] <= go;
            for (t = 1; t < N; t = t + 1) go_p[t] <= go_p[t-1];
        end
    end
    always @(posedge clk) begin
        iss[0] <= issue_in;
        for (t = 1; t < N; t = t + 1) iss[t] <= iss[t-1];
    end
    // ---- x stream: hop t carries the slices of tiles t..N-1 --------------------------------
    reg [N*128-1:0] xs [0:N-1];
    always @(posedge clk) begin
        xs[0] <= x_in;
        for (t = 1; t < N; t = t + 1) xs[t] <= xs[t-1];
    end
    // ---- tiles ---------------------------------------------------------------------------
    wire [N*2048-1:0] o_data;
    wire [N*4-1:0]    o_we, x_re;
    wire [N-1:0]      ov, fault;
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_tile
        wire [IB-1:0] f = iss[g];
        wire [NW-1:0] nout, tiles, kk;
        wire [AW-1:0] wbase, ts, ks, xbase, xks, xcs, wcs, obase, ots, ojs;
        wire [3:0] split;
        wire amax;
        assign {nout, tiles, kk, wbase, ts, ks, xbase, xks, xcs, wcs, obase, ots, ojs, split, amax} = f;
        wire unused_ready, unused_idle, unused_kv_re, unused_am_any, unused_mx_we;
        wire [4*AW-1:0] unused_kv_addr, unused_x_addr, unused_o_addr;
        wire [4*16-1:0] unused_o_mask;
        wire [NW-1:0] unused_am_idx;
        wire [31:0] unused_am_val;
        wire [AW-1:0] unused_mx_addr;
        wire [15:0] unused_mx_mask, unused_progress;
        wire [16*32-1:0] unused_mx_data;
        ot_qwen_o4_g4_rommac u_tile (   // the routed plain-tile abstract in the physical flow
            .clk(clk), .rst_n(rst_n), .go(go_p[g]), .ready(unused_ready), .idle(unused_idle),
            .i_nout(nout), .i_tiles(tiles), .i_k(kk), .i_wsrc(1'b0),
            .i_wbase(wbase), .i_ts(ts), .i_ks(ks), .i_js({AW{1'b0}}),
            .i_xbase(xbase), .i_xks(xks), .i_xjs({AW{1'b0}}), .i_xcs(xcs),
            .i_jsh(3'd0), .i_split(split), .i_wcs(wcs), .i_round(1'b1),
            .i_obase(obase), .i_ots(ots), .i_ojs(ojs),
            .i_mmode(1'b0), .i_oen(1'b1), .i_amax(amax), .i_rmax(1'b0), .i_mbase({AW{1'b0}}),
            .kv_re(unused_kv_re), .kv_addr(unused_kv_addr), .kv_q({4*16*32{1'b0}}),
            .x_re(x_re[4*g +: 4]), .x_addr(unused_x_addr), .x_q(xs[g][128*g +: 128]),
            .ov(ov[g]), .o_we(o_we[4*g +: 4]), .o_addr(unused_o_addr), .o_mask(unused_o_mask),
            .o_data(o_data[2048*g +: 2048]),
            .am_idx(unused_am_idx), .am_val(unused_am_val), .am_any(unused_am_any),
            .mx_we(unused_mx_we), .mx_addr(unused_mx_addr), .mx_mask(unused_mx_mask), .mx_data(unused_mx_data),
            .progress(unused_progress), .fault(fault[g]));
    end endgenerate
    always @(posedge clk) begin
        for (t = 0; t < N; t = t + 1) x_req[t] <= |x_re[4*t +: 4];
        fault_any <= |fault;
    end
    // ---- split tree over tiles: level l pairs blocks of 2^(l-1) tiles ----------------------
    localparam integer NP = 1 << LV;
    wire [NP*512-1:0] lvl [0:LV];
    wire [NP-1:0]     vl  [0:LV];
    generate
        for (g = 0; g < NP; g = g + 1) begin : g_leaf
            if (g < N) begin : g_real
                reg [511:0] q;
                reg v;
                always @(posedge clk) begin q <= o_data[2048*g +: 512]; v <= ov[g]; end
                assign lvl[0][512*g +: 512] = q;
                assign vl[0][g] = v;
            end else begin : g_pad
                assign lvl[0][512*g +: 512] = 512'd0;
                assign vl[0][g] = 1'b0;
            end
        end
    endgenerate
    genvar l, pp, ln;
    generate
        for (l = 1; l <= LV; l = l + 1) begin : g_lvl
            for (pp = 0; pp < (NP >> l); pp = pp + 1) begin : g_pair
                // registered channel: the partner block is 2^(l-1) tile pitches away, about one
                // reach (1.10 mm) per pitch, so both operands cross 2^(l-1) - 1 extra registers
                localparam integer EX = (1 << (l - 1)) - 1;
                wire [511:0] a_in = lvl[l-1][512*(2*pp) +: 512];
                wire [511:0] b_in = lvl[l-1][512*(2*pp+1) +: 512];
                wire [511:0] a_d, b_d;
                wire v_d;
                if (EX > 0) begin : g_ch
                    ot_hdc_delay #(.W(512), .D(EX)) u_a (.clk(clk), .rst_n(rst_n), .d(a_in), .q(a_d));
                    ot_hdc_delay #(.W(512), .D(EX)) u_b (.clk(clk), .rst_n(rst_n), .d(b_in), .q(b_d));
                    reg [EX-1:0] vv;
                    always @(posedge clk or negedge rst_n) begin
                        if (!rst_n) vv <= {EX{1'b0}};
                        else vv <= {vv, vl[l-1][2*pp]};
                    end
                    assign v_d = vv[EX-1];
                end else begin : g_noch
                    assign a_d = a_in;
                    assign b_d = b_in;
                    assign v_d = vl[l-1][2*pp];
                end
                wire [511:0] s;
                wire [15:0] pf;
                for (ln = 0; ln < 16; ln = ln + 1) begin : g_lane
                    ot_hdc_qadd u_add (clk, rst_n, v_d, a_d[32*ln +: 32], b_d[32*ln +: 32], s[32*ln +: 32], pf[ln]);
                end
                wire [3:0] vd;
                ot_hdc_vline #(.D(3)) u_v (.clk(clk), .rst_n(rst_n), .v(v_d), .vd(vd));
                reg [511:0] q;
                reg v;
                always @(posedge clk) begin q <= s; v <= vd[3]; end
                assign lvl[l][512*pp +: 512] = q;
                assign vl[l][pp] = v;
            end
            for (pp = (NP >> l); pp < NP; pp = pp + 1) begin : g_zero
                assign lvl[l][512*pp +: 512] = 512'd0;
                assign vl[l][pp] = 1'b0;
            end
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) root_v <= 1'b0;
        else root_v <= vl[LV][0];
    end
    always @(posedge clk) root_data <= lvl[LV][511:0];
endmodule
