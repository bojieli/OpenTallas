`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT2 (2026-10-17): dsdv_gunit_tail -- the exact HC tail of the G-unit (sigmoid pre/post, exp, Sinkhorn
// ITERS 20) at the 1.2 GHz stream clock, replacing ot_hbm_hc_tail_unit_static in the G-unit (that unit and
// ot_hgi_hc_tail_static are unchanged and stay the HBM's).
//
// Same function, bit for bit (tools/hdc_golden_v41 Model.hc_mixes after the mixes; the bench checks all 24
// coefficients), with the two 0.833-ns risks of the reused tail removed:
//   1. arithmetic: the LAT-3 ot_hdc_fp32_add_fast / mul_fast (SS 975 MHz, w11_fp_latency_sweep) and the LM 3 / LA 3
//      exp / LAT-19 fdiv become the 1.2 GHz units of the f12 file swap (rtl/hdc/ot_hdc_fastfp_lat_f12.sv:
//      ot_hdc_qadd_lat KEEP 1 LAT 4 = ot_hdc_fp32_add_f12_l4, ot_hdc_qmul_lat LAT 5 = ot_hdc_fp32_mul_f12_l5;
//      ot_dsrom_exp_f12 #(LM 5, LA 4) DEPTH 76; ot_dsrom_fdiv_f12 DEPTH 21), bit-identical to the originals by their
//      own qualification; every operand is REGISTERED in front of its unit (the age decode + 24:1 operand mux never
//      shares a stage with a unit's first stage), so each unit costs its latency + 1 on the fixed calendar below.
//   2. Sinkhorn: S81-SAFE-FIX/GUNIT (10-19) replaced the gated-clock ot_hdc_sinkhorn (one 5.3-ns normalisation per
//      unit edge, a 9-cycle multicycle path behind an ICG -- masked depth, SAFE-DESIGN item 4) by ot_hdc_sinkhorn_p:
//      the same function bit for bit, pipelined on the core clock (15 registered stages a normalisation, step 0 in
//      17), no clock gate, no multicycle exception.  Result latency SLAT = 602 edges after the accepting edge.
// Calendar (ages from launch; Le = unit latency + 1 for the operand register):
//   P1      24 mul   t[i] * scale                     P2 = P1 + 24 + LMe   24 add  t[i] + base[i]
//   MAX     row max of t[8..23] (2 stages)            P3 = MAX + 2         16 add  t[i] - max[row]
//   P4      24 exp (pre/post negated)                 P5 = P4 + 24 + LEe   8 add   t[i] + 1
//   P6      8 fdiv 1 / t[i]                           P7 = P6 + 8 + LDe    4 add + eps (pre), 4 mul x 2 (post)
//   EREADY  = P7 + 8 + max(LMe, LAe): the Sinkhorn input is stable.
// Sinkhorn schedule: sink_launch (sl) is a one-edge pulse set at age EREADY + 1, the unit accepts on the next edge
// (a0); out_valid pulses at a0 + SLAT; the result is captured at a0 + SLAT + 1 (capture_q, CAP = SLAT + 1 from sl);
// result_v / result at launch + L, L = EREADY + CAP + 3 (= old L + 55: the old unit took 9 x 42 edges + the divider
// wrap wait).  No ready / busy / response signal moves any event; a capture without out_valid, a launch while active,
// an arithmetic exception or a Sinkhorn fault is a sticky fault.
// MUT_PRE (bench only): the pre path skips + eps.  MUT_SK (bench only): the Sinkhorn steady step lands one stage early.
// S81U-GUNIT3 (10-17): the exp and fdiv units (11.5k flops) live in the side leaf dsdv_gunit_l5f; this module drives
// their registered operands out (x_* ports) and takes their results back XS = 3 edges later than in place (L5f input
// flop, L5f output flop, L5's input flop): LE / LD below include XS, so the calendar stays exact.  MAX is a two-stage
// tree (pairs, then the pair winners; first maximum wins ties exactly as the sequential scan: `greater` is a total
// preorder): the one-cycle 3-deep scan was TT -970 ps.  P3 = MAX + 2.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_tail #(
    parameter integer ITERS = 20,
    parameter [31:0] HC_EPS = 32'h358637bd,
    parameter integer MUT_PRE = 0,
    parameter integer MUT_SK = 0,
    parameter integer PIN_COPY = 0,
    parameter integer CONTROL_SAFE = 0,
    parameter integer Q4 = 0,
    parameter integer XS = 3            // S81-KITS-RTLC 10-24: L5 lands ye/yd in a pin register -> 4
) (
    input  wire          clk, rst_n,
    input  wire          launch,
    input  wire [3:0]    launch_pre,
    input  wire [767:0]  mixes, bases,
    input  wire [95:0]   scales,
    output reg           result_v,
    output wire [767:0]  result,
    output wire          fault,
    // the exp / fdiv units (dsdv_gunit_l5f): operands out of this module's operand registers, results XS edges later
    output wire          xe_v, output wire [31:0] xe_x, input wire xe_vo, input wire [31:0] xe_y, input wire xe_f,
    output wire          xd_v, output wire [31:0] xd_b, input wire xd_vo, input wire [31:0] xd_y, input wire xd_f
);
    localparam integer LM = 5, LA = 4, LE = 7 * LM + 6 * LA + 2 * 6 + 5 + XS, LD = 21 + XS;   // LE 76 + XS
    localparam integer LMe = LM + 1, LAe = LA + 1, LEe = LE + 1, LDe = LD + 1;
    localparam integer P1 = 1, P2 = P1 + 24 + LMe, MAX = P2 + 24 + LAe, P3 = MAX + 2, P4 = P3 + 16 + LAe;
    localparam integer P5 = P4 + 24 + LEe, P6 = P5 + 8 + LAe, P7 = P6 + 8 + LDe;
    localparam integer EREADY = P7 + 8 + ((LMe > LAe) ? LMe : LAe);
    localparam integer SLAT = 17 + (Q4 != 0) + (2 * ITERS - 1) * (15 + (Q4 != 0));   // ot_hdc_sinkhorn_p LAT (D0 17, DS 15): 602 for ITERS 20
    localparam integer CAP = SLAT + 1;
    localparam integer L = EREADY + CAP + 3;
    // ---------------------------------------------------------------- calendar
    reg active; reg [9:0] age;
    reg [31:0] t [0:23], b [0:23], s [0:2], mx [0:3], mp [0:7];
    reg [767:0] final_result;
    assign result = final_result;
    wire p1 = active && age >= P1 && age < P1 + 24;
    wire p2 = active && age >= P2 && age < P2 + 24;
    wire p3 = active && age >= P3 && age < P3 + 16;
    wire p4 = active && age >= P4 && age < P4 + 24;
    wire p5 = active && age >= P5 && age < P5 + 8;
    wire p6 = active && age >= P6 && age < P6 + 8;
    wire p7 = active && age >= P7 && age < P7 + 8;
    wire [4:0] i = p1 ? 5'(age - P1) : p2 ? 5'(age - P2) : p3 ? 5'(age - P3 + 8) :
                   p4 ? 5'(age - P4) : p5 ? 5'(age - P5) : p6 ? 5'(age - P6) : 5'(age - P7);
    wire mv = p1 || (p7 && i >= 4), av = p2 || p3 || p5 || (p7 && i < 4);
    // operand registers (one stage in front of every unit)
    reg mv_q, av_q, ev_q, dv_q; reg [31:0] ma_q, mb_q, aa_q, ab_q;
    wire [31:0] ex_q, db_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin mv_q <= 1'b0; av_q <= 1'b0; ev_q <= 1'b0; dv_q <= 1'b0; end
        else begin mv_q <= mv; av_q <= av; ev_q <= p4; dv_q <= p6; end
    always @(posedge clk) begin
        ma_q <= t[i]; mb_q <= p1 ? s[(i < 4) ? 0 : (i < 8) ? 1 : 2] : 32'h40000000;
        aa_q <= t[i];
        ab_q <= p2 ? b[i] : p3 ? (mx[(i - 5'd8) >> 2] ^ 32'h80000000) : p5 ? 32'h3f800000 : (MUT_PRE ? 32'd0 : HC_EPS);

    end
    // Independent SAME-edge operand copies: no extra calendar stage. The kept,
    // unparameterized module prevents synthesis sharing these boundary flops
    // with ma_q/aa_q or with the other external operand bank.
    generate if (PIN_COPY) begin : g_pin_copy
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_exp (
            .clk(clk), .d((i < 8) ? (t[i] ^ 32'h80000000) : t[i]), .q(ex_q));
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_div (.clk(clk), .d(t[i]), .q(db_q));
    end else begin : g_legacy_operand
        reg [31:0] ex, db;
        always @(posedge clk) begin
            ex <= (i < 8) ? (t[i] ^ 32'h80000000) : t[i];
            db <= t[i];
        end
        assign ex_q = ex; assign db_q = db;
    end endgenerate
    wire [31:0] my, ay, ey, dy; wire mo, ao, eo, do_, mf, af, ef, df;
    wire [LM:0] vm; wire [LA:0] va;
    ot_hdc_qmul_lat #(.LAT(LM)) u_mul (clk, rst_n, mv_q, ma_q, mb_q, my, mf);
    ot_hdc_qadd_lat #(.KEEP(1), .LAT(LA)) u_add (clk, rst_n, av_q, aa_q, ab_q, ay, af);
    ot_hdc_vline #(.D(LM)) u_vm (.clk(clk), .rst_n(rst_n), .v(mv_q), .vd(vm));
    ot_hdc_vline #(.D(LA)) u_va (.clk(clk), .rst_n(rst_n), .v(av_q), .vd(va));
    assign mo = vm[LM]; assign ao = va[LA];
    assign xe_v = ev_q; assign xe_x = ex_q; assign eo = xe_vo; assign ey = xe_y; assign ef = xe_f;
    assign xd_v = dv_q; assign xd_b = db_q; assign do_ = xd_vo; assign dy = xd_y; assign df = xd_f;
    // result index of each unit: the operand index issued 1 + latency edges earlier.  The calendar is a function of age
    // (age advances one an edge while active), so it is recomputed from age, registered -- no index delay lines (the
    // 5-bit x 79 / 24 / 5 / 4 shift chains were 560 flop->flop hold chains, SAFE-DESIGN item 5; S81-SAFE-FIX/GUNIT).
    function automatic [4:0] fidx(input [9:0] x);
        fidx = (x >= 10'(P1) && x < 10'(P1 + 24)) ? 5'(x - 10'(P1)) : (x >= 10'(P2) && x < 10'(P2 + 24)) ? 5'(x - 10'(P2)) :
               (x >= 10'(P3) && x < 10'(P3 + 16)) ? 5'(x - 10'(P3) + 10'd8) : (x >= 10'(P4) && x < 10'(P4 + 24)) ? 5'(x - 10'(P4)) :
               (x >= 10'(P5) && x < 10'(P5 + 8)) ? 5'(x - 10'(P5)) : (x >= 10'(P6) && x < 10'(P6 + 8)) ? 5'(x - 10'(P6)) :
               5'(x - 10'(P7));
    endfunction
    reg [4:0] mi, ai, ei, di;                         // = i of age - 1 - latency (registered from age - latency)
    always @(posedge clk) begin
        mi <= fidx(age - 10'(LM)); ai <= fidx(age - 10'(LA)); ei <= fidx(age - 10'(LE)); di <= fidx(age - 10'(LD));
    end
    function automatic greater(input [31:0] a, c);
        if (a[30:0] == 0 && c[30:0] == 0) greater = 0;
        else if (a[31] != c[31]) greater = !a[31];
        else greater = a[31] ? (a[30:0] < c[30:0]) : (a[30:0] > c[30:0]);
    endfunction
    // ---------------------------------------------------------------- Sinkhorn, pipelined on the core clock
    wire [511:0] se, sy; wire sr, sv, sf, sbusy;
    genvar gj;
    generate for (gj = 0; gj < 16; gj = gj + 1) begin : g_se assign se[32 * gj +: 32] = t[gj + 8]; end endgenerate
    reg sl;
    ot_hdc_sinkhorn_p #(.ITERS(ITERS), .EPS(HC_EPS), .MUT(MUT_SK), .CONTROL_SAFE(CONTROL_SAFE), .Q4(Q4)) u_sinkh (.clk(clk), .rst_n(rst_n), .in_valid(sl), .in_ready(sr),
        .in_e(se), .out_valid(sv), .y(sy), .fault(sf), .busy(sbusy));
    // ---------------------------------------------------------------- control, fixed latency
    reg armed, captured, capture_q, flt; reg [9:0] sage;
    assign fault = flt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            active <= 1'b0; age <= 10'd0; sl <= 1'b0; armed <= 1'b0; captured <= 1'b0; capture_q <= 1'b0;
            sage <= 10'd0; result_v <= 1'b0; flt <= 1'b0;
        end else begin
            capture_q <= 1'b0; result_v <= 1'b0;
            if (active) age <= age + 1'b1;
            if (launch) begin
                if (active) flt <= 1'b1;
                active <= 1'b1; age <= 10'd1; armed <= 1'b0; captured <= 1'b0;
            end
            if ((mo && mf) || (ao && af) || (eo && ef) || (do_ && df)) flt <= 1'b1;
            if (sl && !sr) flt <= 1'b1;
            if (active && !armed && age == 10'(EREADY + 1)) begin sl <= 1'b1; armed <= 1'b1; sage <= 10'd1; end
            else sl <= 1'b0;
            if (armed && !captured) begin
                sage <= sage + 1'b1;
                if (sage == 10'(CAP)) begin capture_q <= 1'b1; captured <= 1'b1; end
            end
            if (capture_q && (!sv || sf)) flt <= 1'b1;
            if (active && age == 10'(L - 1)) begin
                result_v <= 1'b1; active <= 1'b0;
                if (!captured) flt <= 1'b1;
            end
        end
    wire [101:0] launch_local;
    wire [47:0] capture_local;
    generate if (CONTROL_SAFE) begin : g_local_control
        for (genvar lc = 0; lc < 102; lc = lc + 1) begin : g_launch
            (* keep = 1 *) dsdv_gunit_control_bit u_en (.clk(clk), .d(launch_pre[lc % 4]), .q(launch_local[lc]));
        end
        for (genvar cc = 0; cc < 2; cc = cc + 1) begin : g_capture
            (* keep = 1 *) dsdv_gunit_capture_bank24 u_en (.clk(clk), .armed(armed), .captured(captured),
                .sage(sage), .deadline(10'(CAP)), .q(capture_local[24*cc +: 24]));
        end
        for (genvar bw = 0; bw < 24; bw = bw + 1) begin : g_payload
            for (genvar half = 0; half < 2; half = half + 1) begin : g_half
                always @(posedge clk) begin
                    if (launch_local[2*bw+half]) t[bw][16*half +: 16] <= mixes[32*bw+16*half +: 16];
                    if (mo && mi == bw) t[bw][16*half +: 16] <= my[16*half +: 16];
                    if (ao && ai == bw) t[bw][16*half +: 16] <= ay[16*half +: 16];
                    if (eo && ei == bw) t[bw][16*half +: 16] <= ey[16*half +: 16];
                    if (do_ && di == bw) t[bw][16*half +: 16] <= dy[16*half +: 16];
                    if (launch_local[48+2*bw+half]) b[bw][16*half +: 16] <= bases[32*bw+16*half +: 16];
                end
            end
        end
        for (genvar sw = 0; sw < 6; sw = sw + 1) begin : g_scale
            always @(posedge clk) if (launch_local[96+sw]) s[sw/2][16*(sw%2) +: 16] <= scales[16*sw +: 16];
        end
        for (genvar rw = 0; rw < 48; rw = rw + 1) begin : g_result
            if (rw < 16) begin : g_t
                always @(posedge clk) if (capture_local[rw]) final_result[16*rw +: 16] <= t[rw/2][16*(rw%2) +: 16];
            end else begin : g_s
                always @(posedge clk) if (capture_local[rw]) final_result[16*rw +: 16] <= sy[16*(rw-16) +: 16];
            end
        end
    end else begin : g_legacy_storage
    always @(posedge clk) begin
        if (launch) begin
            for (integer j = 0; j < 24; j = j + 1) begin t[j] <= mixes[j * 32 +: 32]; b[j] <= bases[j * 32 +: 32]; end
            for (integer j = 0; j < 3; j = j + 1) s[j] <= scales[j * 32 +: 32];
        end
        if (mo) t[mi] <= my;
        if (ao) t[ai] <= ay;
        if (eo) t[ei] <= ey;
        if (do_) t[di] <= dy;
    end
    end endgenerate
    always @(posedge clk) begin
        if (active && age == 10'(MAX)) for (integer r = 0; r < 4; r = r + 1) begin : pairs
            mp[2 * r]     <= greater(t[8 + 4 * r + 1], t[8 + 4 * r])     ? t[8 + 4 * r + 1] : t[8 + 4 * r];
            mp[2 * r + 1] <= greater(t[8 + 4 * r + 3], t[8 + 4 * r + 2]) ? t[8 + 4 * r + 3] : t[8 + 4 * r + 2];
        end
        if (active && age == 10'(MAX + 1)) for (integer r = 0; r < 4; r = r + 1)
            mx[r] <= greater(mp[2 * r + 1], mp[2 * r]) ? mp[2 * r + 1] : mp[2 * r];
        if (!CONTROL_SAFE && capture_q) begin
            for (integer j = 0; j < 8; j = j + 1) final_result[j * 32 +: 32] <= t[j];
            final_result[256 +: 512] <= sy;
        end
    end
endmodule
// Width is fixed deliberately: SYNTH_KEEP_MODULES must match the exact name,
// without Yosys paramod rewriting. Data remain unreset, as in the legacy path.
(* keep_hierarchy = 1 *) module dsdv_gunit_operand_pin32 (
    input wire clk, input wire [31:0] d, output reg [31:0] q
);
    always @(posedge clk) q <= d;
endmodule
// Fixed kept boundaries prevent opt_merge from collapsing equal enable FF.
(* keep_hierarchy = 1 *) module dsdv_gunit_control_first(input wire clk, rst_n, d, output reg q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
(* keep_hierarchy = 1 *) module dsdv_gunit_control_bit(input wire clk, d, output reg q);
    always @(posedge clk) q <= d;
endmodule
(* keep_hierarchy = 1 *) module dsdv_gunit_capture_bank24(
    input wire clk, armed, captured, input wire [9:0] sage, deadline, output wire [23:0] q);
    wire fire = armed && !captured && sage == deadline;
    for (genvar k = 0; k < 24; k = k + 1) begin : g_q
        (* keep = 1 *) dsdv_gunit_control_bit u_q (.clk(clk), .d(fire), .q(q[k]));
    end
endmodule
`default_nettype wire
