`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_l5 -- G-unit leaf L5 (top, N face = the unit's s_3N rung pins): the exact HC
// tail (dsdv_gunit_tail: sigmoid pre / post, exp, Sinkhorn on the gated stream clock) and the six coefficient CTL rows.
// Inputs from L4: launch + the 24 mixes + the job {set, which, row, masks}; cw (relayed): table rows of set cw_a[8]:
// 56 + 3 w + i = HC bases 8 i .. 8 i + 7 of which w (0 attn, 1 ffn), 62 = {.., ffn scales 2..0 [191:96], attn scales
// 2..0 [95:0]}.  Output: the 24 coefficients (pre 0..3, post 0..3, comb row-major) as six CTL row writes (target 5,
// mask 1111) row .. row + 5, one an edge, zero when idle, down to L4 (relayed to L2's inject).
// fault (sticky): a tail fault, a tail result while the previous rows are still leaving.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 8 = the tail's pre path skips + eps.
// S81U-GUNIT3 (10-17): the tail's exp and fdiv units (11.5k flops) moved to the E-side leaf dsdv_gunit_l5f (the
// one-leaf L5 was 23,268 sinks, TT insertion 563 ps / spread 109 ps: clock-rule FAIL).  Seam (E face): the tail's
// operand registers leave as x?_v / x?_*, the results come back into this leaf's input flops (XS = 3 in the tail).
// The mixes arrive one a cycle (mx_v / mx_i / mx_y) into input flops and are assembled here; launch is held one more
// edge (ln0 -> ln) so the last mix is in mx when the tail takes them.
// S81U-GUNIT6 (10-17, native pin rules, NATIVE-2 lessons): rst_n drives only ot_rst_relay (4 kept region copies:
// feedthroughs, input flops, the tail, the CTL rows); release +3 edges after the port (transaction-level exact; the
// tail's Sinkhorn gate counter is phase-free: result latency is independent of the divider phase).  0 data edges.
// S81-SAFE-FIX/GUNIT (10-19, SAFE-DESIGN review after the first route): the tail's Sinkhorn is pipelined on the core
// clock (ot_hdc_sinkhorn_p; the ICG + 9-cycle multicycle SDC are gone; HC result +55 edges), the table select is
// replicated (kept, 108 copies), reset lands in 2 + 1 registered stages (ot_rst_relay) as before.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l5 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // S face (L4)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    input  wire          launch, input wire mx_v, input wire [4:0] mx_i, input wire [31:0] mx_y, input wire t_set, input wire t_w, input wire [9:0] t_row,
    input  wire [4:0]    t_lm, input wire [15:0] t_sm,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output reg           ct_v, output reg [275:0] ct_b, output reg fault,
    // N face (unit pins, s_3N)
    output wire [275:0]  vo_n,  input wire [275:0] vi_n,
    // E face (L5f: exp / fdiv)
    output wire          xe_v, output wire [31:0] xe_x, input wire ye_v, input wire [31:0] ye_y, input wire ye_f,
    output wire          xd_v, output wire [31:0] xd_b, input wire yd_v, input wire [31:0] yd_y, input wire yd_f
);
    localparam integer V = 276, NSET = 2;
    integer j;
    wire [3:0] rq;
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rq[0]), .d(rs_i), .q(vo_n));
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rq[0]), .d(vi_n), .q(rs_o));
    // ---------------------------------------------------------------- input flops
    reg ln0, ln, wv, qm_v; reg [4:0] qm_i; reg [31:0] qm_y; reg [767:0] mx; reg tj_set, tj_w; reg [9:0] tj_row; reg [4:0] tj_lm; reg [15:0] tj_sm;
    reg [9:0] wa; reg [255:0] wd; reg [3:0] sid_c; reg [9:0] rj_row; reg [4:0] rj_lm; reg [15:0] rj_sm;
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin ln0 <= 1'b0; ln <= 1'b0; wv <= 1'b0; qm_v <= 1'b0; end
        else begin ln0 <= launch; ln <= ln0; wv <= cw_v; qm_v <= mx_v; end
    always @(posedge clk) begin
        qm_i <= mx_i; qm_y <= mx_y; if (qm_v) mx[32 * qm_i +: 32] <= qm_y;   // the 24 mixes, one a cycle
        tj_set <= t_set; tj_w <= t_w; tj_row <= t_row; tj_lm <= t_lm; tj_sm <= t_sm;
        wa <= cw_a; wd <= cw_d; sid_c <= sid_i;
        if (ln) begin rj_row <= tj_row; rj_lm <= tj_lm; rj_sm <= tj_sm; end   // the launched job's rows
    end
    // ---------------------------------------------------------------- tables: bases, scales
    reg [31:0] base_t [0:NSET*48-1];                    // [set][which][24]
    reg [95:0] scl_t  [0:NSET*2-1];
    always @(posedge clk) if (wv && !wa[9]) begin
        if (wa[5:0] >= 6'd56 && wa[5:0] < 6'd62)
            for (j = 0; j < 8; j = j + 1) base_t[48 * wa[8] + 8 * (wa[5:0] - 6'd56) + j] <= wd[32 * j +: 32];
        if (wa[5:0] == 6'd62) begin scl_t[2 * wa[8]] <= wd[95:0]; scl_t[2 * wa[8] + 1] <= wd[191:96]; end
    end
    // S81-SAFE-FIX/GUNIT (10-19): the job's table select {tj_set, tj_w} drove the whole 4:1 table read (3,456 loads on one
    // flop).  It is stable from L4's mix_go (>= 29 edges before launch), so it is replicated in two KEPT ranks (8 copies
    // -> 108 copies, one per 8-bit read group, <= ~32 mux loads each) that settle long before the tail takes the bases /
    // scales at launch: 0 edges.
    reg [767:0] bases; reg [95:0] scales;
    genvar g;
    generate
        for (g = 0; g < 8; g = g + 1) begin : g_tj1
            (* keep = "true" *) reg s, w;
            always @(posedge clk) begin s <= tj_set; w <= tj_w; end
        end
        for (g = 0; g < 108; g = g + 1) begin : g_tj2
            (* keep = "true" *) reg s, w;
            always @(posedge clk) begin s <= g_tj1[g % 8].s; w <= g_tj1[g % 8].w; end
            if (g < 96) begin : g_b                     // base word g / 4, byte g % 4
                always @(posedge clk) bases[32 * (g / 4) + 8 * (g % 4) +: 8] <= base_t[48 * s + 24 * w + g / 4][8 * (g % 4) +: 8];
            end else begin : g_s                        // scale byte g - 96
                always @(posedge clk) scales[8 * (g - 96) +: 8] <= scl_t[2 * s + w][8 * (g - 96) +: 8];
            end
        end
    endgenerate
    // ---------------------------------------------------------------- the tail
    wire tl_v, tl_f; wire [767:0] coef;
    reg qe_v, qe_f, qd_v, qd_f; reg [31:0] qe_y, qd_y;   // L5f results: input flops
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin qe_v <= 1'b0; qd_v <= 1'b0; end else begin qe_v <= ye_v; qd_v <= yd_v; end
    always @(posedge clk) begin qe_y <= ye_y; qe_f <= ye_f; qd_y <= yd_y; qd_f <= yd_f; end
    dsdv_gunit_tail #(.MUT_PRE(MUT == 8 ? 1 : 0), .MUT_SK(MUT == 10 ? 1 : 0)) u_tail (.clk(clk), .rst_n(rq[2]), .launch(ln), .mixes(mx), .bases(bases), .scales(scales),
        .result_v(tl_v), .result(coef), .fault(tl_f),
        .xe_v(xe_v), .xe_x(xe_x), .xe_vo(qe_v), .xe_y(qe_y), .xe_f(qe_f),
        .xd_v(xd_v), .xd_b(xd_b), .xd_vo(qd_v), .xd_y(qd_y), .xd_f(qd_f));
    // ---------------------------------------------------------------- coefficient CTL rows (target 5), output flops
    function automatic [V-1:0] ctl(input [9:0] a, input [127:0] d, input [15:0] sm, input [4:0] lm, input [3:0] s);
        reg [185:0] p;
        begin
            p = 186'd0; p[15:0] = sm; p[20:16] = 5'd5; p[25:21] = lm;
            p[26 +: 10] = a; p[36 +: 4] = 4'hf; p[40 +: 128] = d;
            ctl = {V{1'b0}}; ctl[0] = 1'b1; ctl[12:9] = s; ctl[21 +: 186] = p;
        end
    endfunction
    reg c_on; reg [2:0] c_i;
    always @(posedge clk or negedge rq[3])
        if (!rq[3]) begin c_on <= 1'b0; c_i <= 3'd0; ct_v <= 1'b0; fault <= 1'b0; end
        else begin
            if (tl_v) begin c_on <= 1'b1; c_i <= 3'd0; end
            else if (c_on) begin c_i <= c_i + 3'd1; if (c_i == 3'd5) c_on <= 1'b0; end
            ct_v <= c_on;
            if (tl_f || (tl_v && c_on)) fault <= 1'b1;
        end
    reg [127:0] cq;                                     // coefficient row c_i (decoded constant-index slices)
    always @(*) case (c_i)
        3'd0: cq = coef[127:0];   3'd1: cq = coef[255:128]; 3'd2: cq = coef[383:256];
        3'd3: cq = coef[511:384]; 3'd4: cq = coef[639:512]; default: cq = coef[767:640];
    endcase
    always @(posedge clk) ct_b <= c_on ? ctl(rj_row + {7'd0, c_i}, cq, rj_sm, rj_lm, sid_c) : {V{1'b0}};
endmodule
