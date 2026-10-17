`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_redstn -- the reduction station absorbed into the Q-DV slice: matvec tree levels 7, 8 and 9 of the quad's
// output row blocks, then the BF16 per-row scale, exactly as the q15 result port computes them:
//   level adders  ot_hdc_fp32_add_lat #(LAT 7, DRST 0) x 16 lanes, the qfd_slab_pair_add level-7 pair (a = left, b =
//                 right sibling of the golden pairwise tree ((c0 + c1) + (c2 + c3)) + ...)
//   row scale     ot_hdc_fp32_mul_lat #(SCALE_LAT) (bit-identical to ot_hdc_fmul, the ot_qwen_me_spport_w12 soft path):
//                 y = t x {scale_bf16, 16'h0}, or x 1.0 (16'h3F80) when the op's weights carry no scale (wsrc)
// Word format (cluster, neighbour): {fault, valid, 16 x FP32}, lane l = row base + l.
//
// Static schedule (compiler-fixed; no ready, no credit; violations are sticky faults):
//   cw0 / cw1 carry the LEFT / RIGHT cluster word of one level-7 pair in the same edge.
//   MODE 0 (L7, S = 128, gate/up): every level-7 word is a result word (the lower pair's 8 words = the gate block,
//          then the upper pair's 8 words = the up block).
//   MODE 1 (L8, S = 256, o/down) and MODE 2/3 (L9, S = 512): level-7 words come in blocks of 16: 8 of the lower pair
//          (held), then 8 of the upper pair; word k of the upper half meets held word k at level 8.
//   MODE 2 (L9 receiver, even g): level-8 word k is held; the k-th neighbour word (nb_i) meets it at level 9
//          (left = own = the even column group, right = the neighbour, odd g).
//   MODE 3 (L9 sender, odd g): level-8 words leave on nb_o; no local result.
// Result word j (j = 0 .. nwords-1) is scaled by BTAB word sbase + j and leaves on r_* with its index j.
// MUT 3 (bench negative control): the scale word of result j is read at sbase + j + 1 (must FAIL).
// =====================================================================================================================
module qfd_dv_redstn #(
    parameter integer ADD_LAT   = 7,
    parameter integer SCALE_LAT = 6,
    parameter integer MUT       = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    // op configuration (held from the STN command until the next one)
    input  wire          cfg_v,
    input  wire [1:0]    cfg_mode,
    input  wire          cfg_wsrc,
    input  wire [7:0]    cfg_nwords,
    input  wire [8:0]    cfg_sbase,
    // words (pin-registered by the slice top)
    input  wire [513:0]  cw0,
    input  wire [513:0]  cw1,
    input  wire [513:0]  nb_i,
    output reg  [513:0]  nb_o,
    // BF16 table read (word address; answer 2 edges later)
    output reg           bt_re,
    output reg  [8:0]    bt_word,
    input  wire [255:0]  bt_q,
    // scaled result word
    output reg           r_v,
    output reg  [7:0]    r_idx,
    output reg           r_last,
    output reg  [511:0]  r_d,
    output reg           fault
);
    // ---------------------------------------------------------------- configuration
    reg [1:0] mode; reg wsrc; reg [7:0] nwords; reg [8:0] sbase;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin mode <= 2'd0; wsrc <= 1'b0; nwords <= 8'd0; sbase <= 9'd0; end
        else if (cfg_v) begin mode <= cfg_mode; wsrc <= cfg_wsrc; nwords <= cfg_nwords; sbase <= cfg_sbase; end
    // ---------------------------------------------------------------- level 7
    wire v7_in = cw0[512] & cw1[512];
    wire [511:0] y7;
    wire [15:0] v7l;
    wire [31:0] e7;
    genvar l;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l7
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(0)) u_add (.clk(ck), .rst_n(rst_n), .valid_in(v7_in),
            .a(cw0[32*l +: 32]), .b(cw1[32*l +: 32]), .y(y7[32*l +: 32]), .err(e7[2*l +: 2]), .valid_out(v7l[l]));
    end endgenerate
    wire v7 = v7l[0];
    // ---------------------------------------------------------------- level 8: hold the lower pair's 8 words
    reg [3:0] c7;                                   // level-7 word counter within a 16-word block
    reg [511:0] h8 [0:7];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) c7 <= 4'd0;
        else if (cfg_v) c7 <= 4'd0;
        else if (v7 && mode != 2'd0) c7 <= c7 + 4'd1;
    always @(posedge ck) if (v7 && mode != 2'd0 && !c7[3]) h8[c7[2:0]] <= y7;
    wire v8_in = v7 && mode != 2'd0 && c7[3];
    wire [511:0] y8;
    wire [15:0] v8l;
    wire [31:0] e8;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l8
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(0)) u_add (.clk(ck), .rst_n(rst_n), .valid_in(v8_in),
            .a(h8[c7[2:0]][32*l +: 32]), .b(y7[32*l +: 32]), .y(y8[32*l +: 32]), .err(e8[2*l +: 2]), .valid_out(v8l[l]));
    end endgenerate
    wire v8 = v8l[0];
    // ---------------------------------------------------------------- level 9 (receiver): own level-8 word k + nb word k
    reg [2:0] c8, c9;
    reg [3:0] lead;                                 // own level-8 words held but not yet met (0 .. 8)
    reg [511:0] h9 [0:7];
    wire nbv = nb_i[512];
    wire own9 = v8 && mode == 2'd2;
    wire v9_in = nbv && mode == 2'd2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin c8 <= 3'd0; c9 <= 3'd0; lead <= 4'd0; end
        else if (cfg_v) begin c8 <= 3'd0; c9 <= 3'd0; lead <= 4'd0; end
        else begin
            if (own9) c8 <= c8 + 3'd1;
            if (v9_in) c9 <= c9 + 3'd1;
            lead <= lead + (own9 ? 4'd1 : 4'd0) - (v9_in ? 4'd1 : 4'd0);
        end
    always @(posedge ck) if (own9) h9[c8] <= y8;
    wire [511:0] y9;
    wire [15:0] v9l;
    wire [31:0] e9;
    generate for (l = 0; l < 16; l = l + 1) begin : g_l9
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT), .DRST(0)) u_add (.clk(ck), .rst_n(rst_n), .valid_in(v9_in),
            .a(h9[c9][32*l +: 32]), .b(nb_i[32*l +: 32]), .y(y9[32*l +: 32]), .err(e9[2*l +: 2]), .valid_out(v9l[l]));
    end endgenerate
    wire v9 = v9l[0];
    // ---------------------------------------------------------------- level-9 sender: own level-8 words leave on nb_o
    always @(posedge ck or negedge rst_n)
        if (!rst_n) nb_o <= 514'd0;
        else nb_o <= {1'b0, v8 && mode == 2'd3, y8};
    // ---------------------------------------------------------------- the finished word of the op's mode
    wire        fv = (mode == 2'd0) ? v7 : (mode == 2'd1) ? v8 : (mode == 2'd2) ? v9 : 1'b0;
    wire [511:0] fd = (mode == 2'd0) ? y7 : (mode == 2'd1) ? y8 : y9;
    reg  [7:0]  j;                                  // result index within the op
    always @(posedge ck or negedge rst_n)
        if (!rst_n) j <= 8'd0;
        else if (cfg_v) j <= 8'd0;
        else if (fv) j <= j + 8'd1;
    // scale read: request on the finished word's edge, the word waits 2 edges for the BF16 table answer
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin bt_re <= 1'b0; bt_word <= 9'd0; end
        else begin bt_re <= fv && !wsrc; bt_word <= sbase + {1'b0, j} + ((MUT == 3) ? 9'd1 : 9'd0); end
    reg [511:0] fd1, fd2, fd3;
    reg         fv1, fv2, fv3, ws1, ws2, ws3, ls1, ls2, ls3;
    reg [7:0]   j1, j2, j3;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin fv1 <= 1'b0; fv2 <= 1'b0; fv3 <= 1'b0; end
        else begin fv1 <= fv; fv2 <= fv1; fv3 <= fv2; end
    always @(posedge ck) begin
        fd1 <= fd; fd2 <= fd1; fd3 <= fd2; ws1 <= wsrc; ws2 <= ws1; ws3 <= ws2; j1 <= j; j2 <= j1; j3 <= j2;
        ls1 <= (j + 8'd1 == nwords); ls2 <= ls1; ls3 <= ls2;
    end
    // fd3 / bt_q are aligned: bt_re is registered on the edge after fv (E1), the macro reads at E2, the capture flop at
    // E3: bt_q and fd3 are both valid in the cycle after E3
    wire [511:0] y;
    wire [15:0]  vs;
    wire [31:0]  es;
    generate for (l = 0; l < 16; l = l + 1) begin : g_sc
        ot_hdc_fp32_mul_lat #(.LAT(SCALE_LAT)) u_mul (.clk(ck), .rst_n(rst_n), .valid_in(fv3),
            .a(fd3[32*l +: 32]), .b({ws3 ? 16'h3F80 : bt_q[16*l +: 16], 16'd0}),
            .y(y[32*l +: 32]), .err(es[2*l +: 2]), .valid_out(vs[l]));
    end endgenerate
    wire [7:0] jo; wire lo;
    ot_hdc_delay #(.W(9), .D(SCALE_LAT)) u_jd (.clk(ck), .rst_n(rst_n), .d({ls3, j3}), .q({lo, jo}));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) r_v <= 1'b0;
        else r_v <= vs[0];
    always @(posedge ck) begin r_d <= y; r_idx <= jo; r_last <= lo; end
    // ---------------------------------------------------------------- faults (sticky): valid mismatch, a cluster /
    // neighbour fault bit, an FP error, a neighbour word with no held own word, more result words than configured
    wire in_bad = (cw0[512] ^ cw1[512]) | cw0[513] | cw1[513] | nb_i[513] | (nbv && mode != 2'd2) |
                  (v9_in && lead == 4'd0) | (fv && j >= nwords);
    wire fp_bad = (v7 && |e7) | (v8 && |e8) | (v9 && |e9) | (vs[0] && |es);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | in_bad | fp_bad;
endmodule
