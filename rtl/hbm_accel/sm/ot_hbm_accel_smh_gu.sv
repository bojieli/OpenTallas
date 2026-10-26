`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hbm_accel_smh_gu (H-SM 2026-10-15): SM BF16 lanes with GRADUAL UNDERFLOW.  Measured defect: the Qwen PV component
// (smoke2, src 4bf62695d; debug 17:3x) faulted in the closed lane multiplier ot_hbm_accel_smh_bmul on a softmax
// probability p = 0x00b3 (BF16, 1.6e-38) times |v| < 2^-6: products below 2^-133 were a sticky fault, while the
// arithmetic contract (tools/hdc_golden.py mul) is IEEE RNE with gradual underflow.  Attention on the SM engines feeds
// probabilities down to the subnormal range by construction (exp(s - m)), so the lane multiplier must implement the
// contract's full range.  These are copies of the closed ot_hbm_accel_smh_bmul / ot_hbm_accel_smh_tcl with only the
// stage-3b/4 subnormal encode changed (same 7-cycle latency, same ports); the closed modules stay untouched (closed
// views stand) and the SM successor tiles instantiate the _gu lanes.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_accel_smh_bmul_gu (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire        kill,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg         fault
);
    function automatic [17:0] dec;   // {sig[7:0], E[9:0] signed}
        input [7:0] e;
        input [6:0] m;
        integer i;
        reg [2:0] p;
        begin
            if (e != 0) dec = {1'b1, m, e - 10'sd127};
            else begin
                p = 0;
                for (i = 0; i < 7; i = i + 1) if (m[i]) p = i[2:0];
                dec = {({1'b0, m} << (7 - p)), $signed(-10'sd133) + $signed({7'd0, p})};
            end
        end
    endfunction
    wire [17:0] da = dec(a[30:23], a[22:16]);
    wire [17:0] db = dec(b[30:23], b[22:16]);
    // stage 1: decode
    reg        s1_v, s1_s, s1_z, s1_nf;
    reg [7:0]  s1_a, s1_b;
    reg signed [9:0] s1_ea, s1_eb;       // (m3e) the exponent sum moved to stage 2a (x_l -> s1_e was -14 ps, 14 levels)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= v;
    end
    always @(posedge clk) begin
        s1_s <= a[31] ^ b[31];
        s1_z <= kill || (a[30:16] == 15'd0) || (b[30:16] == 15'd0);
        s1_nf <= (a[30:23] == 8'hFF) || (b[30:23] == 8'hFF);
        s1_a <= da[17:10]; s1_b <= db[17:10];
        s1_ea <= $signed(da[9:0]); s1_eb <= $signed(db[9:0]);
    end
    // stage 2a: four 8x2 partial products
    reg        t_v, t_s, t_z, t_nf;
    reg [9:0]  t_q0, t_q1, t_q2, t_q3;
    reg signed [10:0] t_e8, t_e7;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) t_v <= 1'b0;
        else t_v <= s1_v;
    end
    always @(posedge clk) begin
        t_s <= s1_s; t_z <= s1_z; t_nf <= s1_nf;
        t_e8 <= $signed(s1_ea) + $signed(s1_eb) + 11'sd128; t_e7 <= $signed(s1_ea) + $signed(s1_eb) + 11'sd127;
        t_q0 <= s1_a * s1_b[1:0]; t_q1 <= s1_a * s1_b[3:2];
        t_q2 <= s1_a * s1_b[5:4]; t_q3 <= s1_a * s1_b[7:6];
    end
    // stage 2b: the two 8x4 products
    reg        s2_v, s2_s, s2_z, s2_nf;
    reg [11:0] s2_pl, s2_ph;
    reg signed [10:0] s2_e8, s2_e7;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= t_v;
    end
    always @(posedge clk) begin
        s2_s <= t_s; s2_z <= t_z; s2_nf <= t_nf; s2_e8 <= t_e8; s2_e7 <= t_e7;
        s2_pl <= {2'd0, t_q0} + {t_q1, 2'd0};
        s2_ph <= {2'd0, t_q2} + {t_q3, 2'd0};
    end
    // stage 3: normalise (leading bit 15 or 14) and bias
    wire [15:0] s2_p;
    wire        s2_pc;
    ot_hdc_ksadd_k #(.W(16)) u_psum (.a({4'd0, s2_pl}), .b({s2_ph, 4'd0}), .cin(1'b0), .s(s2_p), .cout(s2_pc));
    reg        s3_v, s3_s, s3_z, s3_nf;
    reg [22:0] s3_f;
    reg signed [10:0] s3_be;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s3_v <= 1'b0;
        else s3_v <= s2_v;
    end
    always @(posedge clk) begin
        s3_s <= s2_s; s3_z <= s2_z; s3_nf <= s2_nf;
        if (s2_p[15]) begin s3_f <= {s2_p[14:0], 8'd0}; s3_be <= s2_e8; end
        else          begin s3_f <= {s2_p[13:0], 9'd0}; s3_be <= s2_e7; end
    end
    // stage 3b (margin m1, +1): the encode decision and both candidate words registered; stage 4 only selects
    // GRADUAL UNDERFLOW (H-SM 2026-10-15): a result below 2^-126 is the IEEE binary32 subnormal of the exact product,
    // rounded to nearest even (the golden hdc_golden.mul: IEEE RNE with gradual underflow, every zero result +0).  The
    // predecessor faulted every product below 2^-133 (s3_be < -6): attention PV multiplies softmax probabilities that
    // legitimately reach 2^-126 and below, so the SM PV path faulted on valid data.  Stage 3b registers the aligned
    // significand with its guard / sticky bits; stage 4 adds the rounding increment (a carry into the exponent field
    // gives the normal 2^-126 exactly).  Products below half the smallest subnormal round to +0.
    reg        t3_v, t3_zero, t3_bad, t3_norm, t3_rinc;
    reg [31:0] t3_n;
    reg        t3_ss;
    reg [22:0] t3_sq;
    wire [23:0] sig24 = {1'b1, s3_f};
    wire signed [10:0] sub_d = 11'sd1 - s3_be;                       // right shift of the subnormal significand (>= 1)
    wire [4:0]  sub_sh = (sub_d > 11'sd25) ? 5'd25 : sub_d[4:0];      // >= 25: the value is below 2^-150 (or a tie at it)
    wire [23:0] sub_q = sig24 >> sub_sh;                              // truncated subnormal fraction (bit 23 always 0)
    wire [24:0] sub_r = {sig24, 1'b0} >> sub_sh;                      // bit 0 = guard (the first bit shifted out)
    wire [23:0] sub_lo = sig24 & ((24'd1 << (sub_sh - 5'd1)) - 24'd1); // bits below the guard
    wire        sub_g = sub_r[0];
    wire        sub_st = |sub_lo;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) t3_v <= 1'b0;
        else t3_v <= s3_v;
    end
    always @(posedge clk) begin
        t3_zero <= s3_z && !s3_nf;
        t3_bad  <= s3_nf || s3_be > 11'sd254;
        t3_norm <= s3_be >= 11'sd1;
        t3_n    <= {s3_s, s3_be[7:0], s3_f};
        t3_ss   <= s3_s;
        t3_sq   <= sub_q[22:0];
        t3_rinc <= sub_g && (sub_st || sub_q[0]);
    end
    // stage 4: encode (select)
    reg        s4_v, s4_bad;
    reg [31:0] s4_y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s4_v <= 1'b0;
        else s4_v <= t3_v;
    end
    always @(posedge clk) begin
        s4_bad <= 1'b0;
        if (t3_zero) s4_y <= 32'd0;
        else if (t3_bad) begin s4_y <= 32'd0; s4_bad <= 1'b1; end
        else if (t3_norm) s4_y <= t3_n;
        else if (t3_sq == 23'd0 && !t3_rinc) s4_y <= 32'd0;           // rounds to zero: canonical +0
        else s4_y <= {t3_ss, 31'({8'd0, t3_sq}) + 31'(t3_rinc)};
    end
    // stage 5: output register
`ifdef OT_SMH_DRST0
    // fe-push-hphys-1010: y is data (qualified by the valid line beside it); only fault keeps its reset
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else fault <= s4_v && s4_bad;
    end
    always @(posedge clk) y <= s4_y;
`else
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end
    end
`endif
endmodule

module ot_hbm_accel_smh_tcl_gu #(parameter integer L = 8, parameter integer IL = 8, parameter integer ALAT = 7) (
    input  wire clk, input wire rst_a,
    input  wire i_v, input wire i_first, input wire [L*16-1:0] i_w, input wire [L*16-1:0] i_x,
    output wire [L*32-1:0] sum_o, output wire lfault
);
    localparam integer FB = IL - ALAT;
    localparam integer ML = 7;
    wire rst_n;
`ifdef OT_SMH_RSTRELAY
    ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_a), .rst_n(rst_n));
`else
    assign rst_n = rst_a;
`endif
    reg jv, jfirst;
    reg [L*16-1:0] jw, jx;
    always @(posedge clk or negedge rst_n) if (!rst_n) jv <= 1'b0; else jv <= i_v;
    always @(posedge clk) begin jfirst <= i_first; jw <= i_w; jx <= i_x; end
    reg v_q, first_q, v_q2, first_q2;
    reg [L-1:0] v_ql;
    reg [L*16-1:0] w_q, x_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v_q <= 1'b0; first_q <= 1'b0; v_q2 <= 1'b0; first_q2 <= 1'b0; v_ql <= {L{1'b0}}; end
        else begin v_q <= jv; first_q <= jv && jfirst; v_q2 <= v_q; first_q2 <= first_q; v_ql <= {L{v_q}}; end
    end
    always @(posedge clk) begin w_q <= jw; x_q <= jx; end
    wire [ML:0] fl, vl;
    ot_hdc_vline #(.D(ML)) u_f (.clk(clk), .rst_n(rst_n), .v(first_q2), .vd(fl));
    ot_hdc_vline #(.D(ML)) u_v (.clk(clk), .rst_n(rst_n), .v(v_q2), .vd(vl));
    wire [L*32-1:0] sum;
    reg  [L*32-1:0] sum_q;
    wire [L-1:0] lf;
    genvar l;
    generate for (l = 0; l < L; l = l + 1) begin : g_lane
        wire [31:0] prod, fb_pre;
        reg  [31:0] acc_q;
        reg  [15:0] w_l, x_l;
        wire f0, f1;
        always @(posedge clk) begin w_l <= w_q[16*l +: 16]; x_l <= x_q[16*l +: 16]; end
        ot_hbm_accel_smh_bmul_gu u_mul (.clk(clk), .rst_n(rst_n), .v(v_q2), .kill(!v_ql[l]), .a({w_l, 16'd0}),
                                     .b({x_l, 16'd0}), .y(prod), .fault(f0));
        reg flc;
        always @(posedge clk or negedge rst_n) if (!rst_n) flc <= 1'b0; else flc <= fl[ML-2];
        always @(posedge clk) acc_q <= flc ? 32'd0 : fb_pre;
        ot_gpu_fadd #(.LAT(ALAT)) u_add (.clk(clk), .rst_n(rst_n), .v(vl[ML]), .a(acc_q), .b(prod), .y(sum[32*l +: 32]), .fault(f1));
        ot_hdc_delay #(.W(32), .D(FB - 1)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb_pre));
        always @(posedge clk) sum_q[32*l +: 32] <= sum[32*l +: 32];
        assign lf[l] = f0 | f1;
    end endgenerate
    reg lane_fault;
    always @(posedge clk or negedge rst_n) if (!rst_n) lane_fault <= 1'b0; else lane_fault <= lane_fault | (|lf);
    assign sum_o = sum_q;
    assign lfault = lane_fault;
endmodule
`default_nettype wire
