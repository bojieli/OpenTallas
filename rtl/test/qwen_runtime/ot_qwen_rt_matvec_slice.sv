`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION-ONLY runtime decomposition of rtl/hdc/ot_hdc_matvec.sv, part 2:
// everything the original holds per lane group g, for ONE group.  The group
// index arrives on `gi` (a constant the host drives), so one compiled model
// serves all G groups.  Each statement is the original's loop body for index
// g, reading the sequencer's register values from the b_* inputs.
//
//   operand capture/conditioning  kv_addr, x_re, x_addr, e_gm, s*_gm, mq_*,
//                                 s2_w, s3_w, s2_x, s3_x
//   W MAC lanes                   ot_hdc_bmul + ot_hdc_fadd + feedback delay
//   lane fault register           fault_q[g]
//   INT8 post-scale               scale request mask/address, W ot_hdc_fmul
//   result registers              o_we1/o_addr1/o_mask1/o_data1 and o_*
//   argmax                        W leaves and the log2(W) in-group levels
//
// Cross-group state (split tree, argmax above one group) is not here; see
// ot_qwen_rt_matvec_seq.sv for the contract.  Not hardware.
// ---------------------------------------------------------------------------
module ot_qwen_rt_matvec_slice #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_WEIGHT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [31:0]       gi,
    // memories (this group's lanes)
    input  wire [W*((INT8_WEIGHT != 0) ? 8 : 16)-1:0] wrom_q,
    output reg               scale_gre,
    output reg  [AW-1:0]     scale_addr,
    input  wire [W*16-1:0]   scale_q,
    output reg  [AW-1:0]     kv_addr,
    input  wire [W*32-1:0]   kv_q,
    output reg               x_re,
    output reg  [AW-1:0]     x_addr,
    input  wire [31:0]       x_q,
    output reg               o_we,
    output reg  [AW-1:0]     o_addr,
    output reg  [W-1:0]      o_mask,
    output reg  [W*32-1:0]   o_data,
    // sequencer broadcast
    input  wire              b_active,
    input  wire [AW-1:0]     b_cur,
    input  wire [3:0]        b_split_r,
    input  wire [AW-1:0]     b_ts_r,
    input  wire [AW-1:0]     b_wcs_r,
    input  wire [AW-1:0]     b_xc,
    input  wire [AW-1:0]     b_xcs_r,
    input  wire              b_wsrc_r,
    input  wire [NW-1:0]     b_k,
    input  wire [NW-1:0]     b_ktot_r,
    input  wire              b_s1b_wsrc,
    input  wire              b_s2_round,
    input  wire              b_s3_v,
    input  wire              b_fl_first4,
    input  wire              b_vline5,
    input  wire              b_pre_v,
    input  wire [3*(NW+1)+AW+4+3-1:0] b_pre,
    input  wire              b_raw_v,
    input  wire [3*(NW+1)+4+3-1:0] b_raw,
    input  wire              b_r_v,
    input  wire [3*(NW+1)+2*AW+4+3-1:0] b_r,
    // split tree
    output wire [W*32-1:0]   sum,        // lvl[0] for this group
    input  wire [W*32-1:0]   raw_res,    // lvl[LG] for this group
    // reductions
    output wire              pre_scale_active,
    output reg               fault_q,
    output wire              scale_fault,
    output wire [1+32+NW-1:0] amax_node   // argmax level log2(W) node of this group
);
    localparam integer LW = $clog2(W);
    localparam integer LG = $clog2(G);
    localparam integer FB = IL - 5;
    wire signed [31:0] g = gi;
    function automatic [15:0] int8_bf16(input [7:0] code);
        reg [7:0] mag, norm;
        reg [2:0] msb;
        integer bit_index;
        begin
            mag = code[7] ? (~code + 8'd1) : code;
            msb = 0;
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1)
                if (mag[bit_index]) msb = bit_index[2:0];
            norm = mag << (3'd7 - msb);
            int8_bf16 = (mag == 0) ? 16'd0 :
                        {code[7], (8'd127 + {5'd0, msb}), norm[6:0]};
        end
    endfunction

    // -- issue-side per-group registers -----------------------------------------
    wire [3:0] split_r = b_split_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x_re <= 0;
        end else if (!b_active) begin
            x_re <= 0;
        end else begin
            kv_addr <= b_cur + (g >> split_r) * b_ts_r + (g & ((1 << split_r) - 1)) * b_wcs_r;
            x_re <= ((g >> split_r) < (G >> split_r));
        end
    end
    always @(posedge clk)
        x_addr <= b_xc + (g & ((1 << split_r) - 1)) * b_xcs_r;
    reg e_gm;
    always @(posedge clk)
        e_gm <= ((g >> split_r) < (G >> split_r)) &&
                (!b_wsrc_r || (({{(32-NW){1'b0}}, b_k} << split_r) + (g & ((1 << split_r) - 1))
                               < {{(32-NW){1'b0}}, b_ktot_r}));

    // -- S1 -> S2 -> S3 operand path ---------------------------------------------
    reg [W*((INT8_WEIGHT != 0) ? 8 : 16)-1:0] mq_wrom;
    reg [W*32-1:0] mq_kv;
    reg [31:0]     mq_x;
    reg [W*32-1:0] s2_w, s3_w;
    reg [31:0]     s2_x, s3_x;
    reg            s1_gm, s1b_gm, s2_gm;
    integer l;
    always @(posedge clk) begin
        s1_gm <= e_gm; s1b_gm <= s1_gm; s2_gm <= s1b_gm;
        mq_wrom <= wrom_q; mq_kv <= kv_q; mq_x <= x_q;
        for (l = 0; l < W; l = l + 1)
            if (INT8_WEIGHT != 0)
                s2_w[32*l +: 32] <= !s1b_gm ? 32'd0 : b_s1b_wsrc ? mq_kv[32*l +: 32] :
                                          {int8_bf16(mq_wrom[8*l +: 8]), 16'h0000};
            else
                s2_w[32*l +: 32] <= !s1b_gm ? 32'd0 : b_s1b_wsrc ? mq_kv[32*l +: 32] :
                                          {mq_wrom[16*l +: 16], 16'h0000};
        s2_x <= mq_x;
        s3_w <= s2_w;
        s3_x <= !s2_gm ? 32'd0 :
                b_s2_round ? ((s2_x + 32'h7FFF + {31'd0, s2_x[16]}) & 32'hFFFF0000)
                           : s2_x;
    end

    // -- lanes -------------------------------------------------------------------
    wire [W-1:0] lfault;
    genvar gl;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_lane
            wire [31:0] prod, fb_pre, acc_in;
            reg  [31:0] acc_q;
            wire f0, f1;
            ot_hdc_bmul u_mul (.clk(clk), .rst_n(rst_n), .v(b_s3_v),
                               .a(s3_w[32*gl +: 32]), .b(s3_x), .y(prod), .fault(f0));
            always @(posedge clk) acc_q <= b_fl_first4 ? 32'd0 : fb_pre;
            assign acc_in = acc_q;
            ot_hdc_fadd u_add (clk, rst_n, b_vline5, acc_in, prod,
                               sum[32*gl +: 32], f1);
            ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*gl +: 32]), .q(fb_pre));
            assign lfault[gl] = f0 | f1;
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault_q <= 1'b0;
        else fault_q <= |lfault;
    end

    // -- INT8 post-scale -----------------------------------------------------------
    wire [W*32-1:0] res;
    wire pre_last, pre_wsrc, pre_mmode;
    wire [3:0] pre_split;
    wire [NW:0] pre_nb, pre_lb, pre_nout;
    wire [AW-1:0] pre_sbase;
    assign {pre_last, pre_wsrc, pre_mmode, pre_split, pre_nb, pre_lb, pre_nout, pre_sbase} = b_pre;
    wire raw_last, raw_wsrc, raw_mmode;
    wire [3:0] raw_split;
    wire [NW:0] raw_nb, raw_lb, raw_nout;
    assign {raw_last, raw_wsrc, raw_mmode, raw_split, raw_nb, raw_lb, raw_nout} = b_raw;
    generate if (INT8_WEIGHT != 0) begin : g_post_scale
        wire [W-1:0] scale_faults;
        assign pre_scale_active = b_pre_v && pre_last && !pre_wsrc &&
            (g < (G >> pre_split)) &&
            (pre_mmode ? (pre_lb + g*W < pre_nout) :
                         (pre_nb + g*(W*IL) < pre_nout));
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) scale_gre <= 1'b0;
            else scale_gre <= pre_scale_active;
        end
        always @(posedge clk)
            scale_addr <= pre_scale_active ? pre_sbase + (pre_nb >> LW) + g * IL : pre_sbase;
        genvar si;
        for (si = 0; si < W; si = si + 1) begin : g_scale
            localparam integer LANE = si;
            wire active_lane = (g < (G >> raw_split)) &&
                (raw_mmode ? (raw_lb + g*W + LANE < raw_nout) :
                             (raw_nb + g*(W*IL) + LANE < raw_nout));
            ot_hdc_fmul u_mul (
                .clk(clk), .rst_n(rst_n), .v(b_raw_v && raw_last && active_lane),
                .a(raw_res[32*si +: 32]),
                .b({raw_wsrc ? 16'h3F80 : scale_q[16*si +: 16], 16'd0}),
                .y(res[32*si +: 32]), .fault(scale_faults[si])
            );
        end
        assign scale_fault = |scale_faults;
    end else begin : g_no_post_scale
        assign pre_scale_active = 1'b0;
        always @(*) begin scale_gre = 1'b0; scale_addr = 0; end
        assign scale_fault = 1'b0;
        assign res = raw_res;
    end endgenerate

    // -- results -------------------------------------------------------------------
    wire          r_last, r_oen, r_mmode;
    wire [3:0]    r_split;
    wire [AW-1:0] r_oa, r_ots;
    wire [NW:0]   r_nb, r_lb, r_nout;
    assign {r_last, r_oen, r_mmode, r_split, r_oa, r_ots, r_nb, r_lb, r_nout} = b_r;
    wire [LG:0]   r_ports = G >> r_split;
    reg  [W-1:0]  r_mask;
    reg           o_we1;
    reg  [AW-1:0] o_addr1;
    reg  [W-1:0]  o_mask1;
    reg  [W*32-1:0] o_data1;
    integer ql;
    always @(*) begin
        for (ql = 0; ql < W; ql = ql + 1)
            r_mask[ql] = (g < r_ports) &&
                (r_mmode ? (r_lb + g * W + ql < r_nout) : (r_nb + g * (W * IL) + ql < r_nout));
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we1 <= 0;
        else o_we1 <= b_r_v && r_last && r_oen && (g < r_ports);
    end
    always @(posedge clk) begin
        o_addr1 <= r_oa + g * r_ots;
        o_mask1 <= r_mask; o_data1 <= res;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we <= 0;
        else o_we <= o_we1;
    end
    always @(posedge clk) begin
        o_addr <= o_addr1; o_mask <= o_mask1; o_data <= o_data1;
    end

    // -- argmax leaves and in-group levels --------------------------------------------
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer CW = 1 + 32 + NW;
    wire [CW*W-1:0] alv [0:LW];
    genvar e, lv;
    generate
        for (e = 0; e < W; e = e + 1) begin : g_leaf
            localparam integer EL = e;
            reg [CW-1:0] c;
            wire [NW-1:0] row = r_nb[NW-1:0] + g * (W * IL) + EL;
            always @(posedge clk)
                c <= {r_mask[e], okey(res[32*e +: 32]), row};
            assign alv[0][CW*e +: CW] = c;
        end
        for (lv = 1; lv <= LW; lv = lv + 1) begin : g_alvl
            for (e = 0; e < (W >> lv); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[lv-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[lv-1][CW*(2*e+1) +: CW];
                wire          x0_wins = x0[CW-1] && (!x1[CW-1] || x0[CW-2 -: 32] > x1[CW-2 -: 32] ||
                                        (x0[CW-2 -: 32] == x1[CW-2 -: 32] && x0[NW-1:0] < x1[NW-1:0]));
                reg  [CW-1:0] c;
                always @(posedge clk) c <= x0_wins ? x0 : x1;
                assign alv[lv][CW*e +: CW] = c;
            end
            if ((W >> lv) < W) begin : g_pad
                assign alv[lv][CW*W-1 : CW*(W >> lv)] = 0;
            end
        end
    endgenerate
    assign amax_node = alv[LW][CW-1:0];
endmodule
