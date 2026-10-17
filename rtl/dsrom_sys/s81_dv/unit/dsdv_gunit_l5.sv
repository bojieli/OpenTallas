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
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l5 #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // S face (L4)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    input  wire          launch, input wire [767:0] mixes, input wire t_set, input wire t_w, input wire [9:0] t_row,
    input  wire [4:0]    t_lm, input wire [15:0] t_sm,
    input  wire          cw_v, input wire [9:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output reg           ct_v, output reg [275:0] ct_b, output reg fault,
    // N face (unit pins, s_3N)
    output wire [275:0]  vo_n,  input wire [275:0] vi_n
);
    localparam integer V = 276, NSET = 2;
    integer j;
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rst_n), .d(rs_i), .q(vo_n));
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rst_n), .d(vi_n), .q(rs_o));
    // ---------------------------------------------------------------- input flops
    reg ln, wv; reg [767:0] mx; reg tj_set, tj_w; reg [9:0] tj_row; reg [4:0] tj_lm; reg [15:0] tj_sm;
    reg [9:0] wa; reg [255:0] wd; reg [3:0] sid_c; reg [9:0] rj_row; reg [4:0] rj_lm; reg [15:0] rj_sm;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ln <= 1'b0; wv <= 1'b0; end else begin ln <= launch; wv <= cw_v; end
    always @(posedge clk) begin
        mx <= mixes; tj_set <= t_set; tj_w <= t_w; tj_row <= t_row; tj_lm <= t_lm; tj_sm <= t_sm;
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
    reg [767:0] bases; reg [95:0] scales;
    always @(posedge clk) begin
        for (j = 0; j < 24; j = j + 1) bases[32 * j +: 32] <= base_t[48 * tj_set + 24 * tj_w + j];
        scales <= scl_t[2 * tj_set + tj_w];
    end
    // ---------------------------------------------------------------- the tail
    wire tl_v, tl_f; wire [767:0] coef;
    dsdv_gunit_tail #(.MUT_PRE(MUT == 8 ? 1 : 0)) u_tail (.clk(clk), .rst_n(rst_n), .launch(ln), .mixes(mx), .bases(bases), .scales(scales),
        .result_v(tl_v), .result(coef), .fault(tl_f));
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
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin c_on <= 1'b0; c_i <= 3'd0; ct_v <= 1'b0; fault <= 1'b0; end
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
