`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-GUNIT whole-model successor (2026-10-19): dsdv_gunit_tail_fs -- dsdv_gunit_tail (CONTROL_SAFE, Q4, PIN_COPY) with
// the same function, bit for bit, and the same fixed calendar (L = EREADY + CAP + 3, CAP = SLAT + 1, SLAT 642), rebuilt
// FANOUT-SAFE (SAFE-DESIGN item 3) on ot_hdc_sinkhorn_fs:
//   * the 24:1 operand reads t[i] / b[i] / mx[..] are AND-OR trees on REGISTERED one-hot selects, predicted one edge
//     ahead from the age counter's next state (16 kept copies of the 24 read selects: 4 operand registers x 4 bytes);
//   * the unit write-backs t[mi] <= my (etc.) use registered one-hot indices (2 kept copies, one per 16-bit half)
//     decoded from the current age (fidx(age - LX) of dsdv_gunit_tail), ANDed with kept copies of the unit valids;
//   * age decodes use two replicas of the {active, age} counter (one decodes the next state, one the current state),
//     each a 16-line low / 64-line high predecode with active folded into the high lines;
//   * the row-max compares are computed in two kept instances (one per 16-bit half of the selected word);
//   * the Sinkhorn input valid has 8 kept copies (vin of ot_hdc_sinkhorn_fs);
//   * resets: rst_n + 8 regional roots (rst_v), each <= 24 asynchronous pins.
// Exactness holds for every fault-free schedule (no launch while active); on a faulting schedule the sticky fault is
// raised exactly as in dsdv_gunit_tail (operand registers outside an issue window hold 0, not the old garbage index).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_tail_fs #(
    parameter integer ITERS = 20,
    parameter [31:0] HC_EPS = 32'h358637bd,
    parameter integer MUT_PRE = 0,
    parameter integer MUT_SK = 0,
    parameter integer PIN_COPY = 1,
    // S81-GUVE 10-20 (L5 ro3 native census FAIL 621 non-clock): 1 = native-32 tail -- ve-local binary32 units
    // (ot_s81sl_ve_qmul / _qadd: bit- and cycle-exact to the f12 LAT 5 / 4 units, valid-only reset) fed by two kept
    // same-edge operand copies; payload write gates per byte; one-hot Sinkhorn shifters (ot_hdc_sinkhorn_fs OH).
    // 0 edges added; 0 = the reviewed L5 ro3 source.
    parameter integer NAT32 = 0,
    // S81-KITS-RTLC 10-24: seam stages of the L5f round trip (operand out .. result in); L5 lands ye/yd in a pin register (+1)
    parameter integer XS = 3
) (
    input  wire          clk, rst_n,
    input  wire [7:0]    rst_v,
    input  wire          launch,
    input  wire [11:0]   launch_pre,          // kept copies of launch, one edge early (== ln0)
    input  wire [767:0]  mixes, bases,
    input  wire [95:0]   scales,
    output reg           result_v,
    output wire [767:0]  result,
    output wire          fault,
    output wire          xe_v, output wire [31:0] xe_x, input wire [3:0] xe_vo, input wire [31:0] xe_y, input wire xe_f,
    output wire          xd_v, output wire [31:0] xd_b, input wire [3:0] xd_vo, input wire [31:0] xd_y, input wire xd_f
);
    localparam integer LM = 5, LA = 4, LE = 7 * LM + 6 * LA + 2 * 6 + 5 + XS, LD = 21 + XS;
    localparam integer LMe = LM + 1, LAe = LA + 1, LEe = LE + 1, LDe = LD + 1;
    localparam integer P1 = 1, P2 = P1 + 24 + LMe, MAX = P2 + 24 + LAe, P3 = MAX + 2, P4 = P3 + 16 + LAe;
    localparam integer P5 = P4 + 24 + LEe, P6 = P5 + 8 + LAe, P7 = P6 + 8 + LDe;
    localparam integer EREADY = P7 + 8 + ((LMe > LAe) ? LMe : LAe);
    localparam integer SLAT = 18 + (2 * ITERS - 1) * 16;     // ot_hdc_sinkhorn_fs LAT (Q4: D0 18, DS 16): 642
    localparam integer CAP = SLAT + 1;
    localparam integer L = EREADY + CAP + 3;
    localparam integer NA = 272;                               // decoded ages 0 .. NA-1 (every issue / write-back age)
    genvar b, h, k, a;

    // ---------------------------------------------------------------- age counter: master + two decode replicas
    reg active; reg [9:0] age;
    reg sl, armed, captured, capture_q, flt; reg [9:0] sage;
    function automatic [10:0] nxt(input act, input [9:0] ag, input ln);      // {active, age} next, as dsdv_gunit_tail
        reg na; reg [9:0] nag;
        begin
            na = act; nag = ag;
            if (act) nag = ag + 10'd1;
            if (ln) begin na = 1'b1; nag = 10'd1; end
            if (act && ag == 10'(L - 1)) na = 1'b0;
            nxt = {na, nag};
        end
    endfunction
    // replica A: decodes the NEXT state (registered selects for the next edge); replica B: the CURRENT state
    reg actA, actB; reg [9:0] ageA, ageB;
    // launch copies (== launch: launch_pre[8..10] registered once more), one per counter
    wire lnA, lnB, lnM;
    (* keep = 1 *) ot_skf_kr #(.W(1)) u_lnA (.clk(clk), .d(launch_pre[8]), .q(lnA));
    (* keep = 1 *) ot_skf_kr #(.W(1)) u_lnB (.clk(clk), .d(launch_pre[9]), .q(lnB));
    (* keep = 1 *) ot_skf_kr #(.W(1)) u_lnM (.clk(clk), .d(launch_pre[10]), .q(lnM));
    wire [10:0] nA = nxt(actA, ageA, lnA), nB = nxt(actB, ageB, lnB);
    always @(posedge clk or negedge rst_v[1])
        if (!rst_v[1]) begin actA <= 1'b0; ageA <= 10'd0; actB <= 1'b0; ageB <= 10'd0; end
        else begin {actA, ageA} <= nA; {actB, ageB} <= nB; end
    wire [15:0] loA, loB; wire [63:0] hiA, hiB;
    generate for (k = 0; k < 16; k = k + 1) begin : g_lo
        assign loA[k] = (nA[3:0] == 4'(k)); assign loB[k] = (ageB[3:0] == 4'(k));
    end
    for (k = 0; k < 64; k = k + 1) begin : g_hi
        assign hiA[k] = nA[10] && (nA[9:4] == 6'(k)); assign hiB[k] = actB && (ageB[9:4] == 6'(k));
    end endgenerate
    wire [NA-1:0] dA, dB;                       // dA[x]: active && age == x at the NEXT edge; dB[x]: now
    generate for (a = 0; a < NA; a = a + 1) begin : g_age
        assign dA[a] = loA[a % 16] & hiA[a / 16];
        assign dB[a] = loB[a % 16] & hiB[a / 16];
    end endgenerate

    // ---------------------------------------------------------------- operand selects (next edge), kept copies
    wire [23:0] rsel_d;                          // t[i] read: i at the next edge (any issue window)
    wire [23:0] bsel_d;                          // p2: b[i]
    wire [3:0]  msel_d;                          // p3: mx[(i - 8) >> 2]
    wire p5_d, eps_d, s0_d, s1_d, s2_d, ineg_d, pmax_d, pmax1_d;
    generate for (b = 0; b < 24; b = b + 1) begin : g_rs
        wire w1 = dA[P1 + b] | dA[P2 + b] | dA[P4 + b];
        wire w3 = (b >= 8) ? dA[P3 + b - 8] : 1'b0;
        wire w7 = (b < 8) ? (dA[P5 + b] | dA[P6 + b] | dA[P7 + b]) : 1'b0;
        assign rsel_d[b] = w1 | w3 | w7;
        assign bsel_d[b] = dA[P2 + b];
    end endgenerate
    function automatic rng(input [NA-1:0] d, input integer lo, input integer n);
        integer x; begin rng = 1'b0; for (x = 0; x < n; x = x + 1) rng = rng | d[lo + x]; end
    endfunction
    generate for (k = 0; k < 4; k = k + 1) begin : g_ms
        assign msel_d[k] = rng(dA, P3 + 4 * k, 4);
    end endgenerate
    assign p5_d = rng(dA, P5, 8);
    assign eps_d = !(rng(dA, P2, 24) | rng(dA, P3, 16) | p5_d);
    assign s0_d = rng(dA, P1, 4); assign s1_d = rng(dA, P1 + 4, 4); assign s2_d = rng(dA, P1 + 8, 16);
    assign ineg_d = rng(dA, P1, 8) | rng(dA, P2, 8) | rng(dA, P4, 8) | rng(dA, P5, 8) | rng(dA, P6, 8) | rng(dA, P7, 8);
    assign pmax_d = dA[MAX]; assign pmax1_d = dA[MAX + 1];
    // copies: rsel 16 (operand register o = 0 ma, 1 aa, 2 ex, 3 db; byte y), bsel / msel / p5 / eps / s* 2 (halves)
    wire [23:0] rsel [0:15]; wire [23:0] bsel [0:1]; wire [3:0] msel [0:1]; wire [1:0] p5s, epss, s0s, s1s, s2s;
    wire ineg; wire [15:0] pmx; wire [7:0] pmx1;
    generate
        for (k = 0; k < 16; k = k + 1) begin : g_rc
            (* keep = 1 *) ot_skf_kr #(.W(24)) u_r (.clk(clk), .d(rsel_d), .q(rsel[k]));
        end
        for (k = 0; k < 2; k = k + 1) begin : g_ac
            (* keep = 1 *) ot_skf_kr #(.W(33)) u_a (.clk(clk), .d({bsel_d, msel_d, p5_d, eps_d, s0_d, s1_d, s2_d}),
                                                    .q({bsel[k], msel[k], p5s[k], epss[k], s0s[k], s1s[k], s2s[k]}));
        end
        (* keep = 1 *) ot_skf_kr #(.W(1)) u_ineg (.clk(clk), .d(ineg_d), .q(ineg));
        for (k = 0; k < 16; k = k + 1) begin : g_px
            (* keep = 1 *) ot_skf_kr #(.W(1)) u_p (.clk(clk), .d(pmax_d), .q(pmx[k]));
        end
        for (k = 0; k < 8; k = k + 1) begin : g_px1
            (* keep = 1 *) ot_skf_kr #(.W(1)) u_p (.clk(clk), .d(pmax1_d), .q(pmx1[k]));
        end
    endgenerate

    // ---------------------------------------------------------------- write-back indices (current age), kept copies
    wire [23:0] wm_d, wa_d, we_d, wd_d;
    generate for (b = 0; b < 24; b = b + 1) begin : g_wb
        assign wm_d[b] = dB[P1 + b + LM] | ((b >= 4 && b < 8) ? dB[P7 + b + LM] : 1'b0);
        assign wa_d[b] = dB[P2 + b + LA] | ((b >= 8) ? dB[P3 + b - 8 + LA] : 1'b0) | ((b < 8) ? dB[P5 + b + LA] : 1'b0)
                       | ((b < 4) ? dB[P7 + b + LA] : 1'b0);
        assign we_d[b] = dB[P4 + b + LE];
        assign wd_d[b] = (b < 8) ? dB[P6 + b + LD] : 1'b0;
    end endgenerate
    wire [23:0] mi_oh [0:1], ai_oh [0:1], ei_oh [0:1], di_oh [0:1];
    generate for (h = 0; h < 2; h = h + 1) begin : g_wc
        (* keep = 1 *) ot_skf_kr #(.W(96)) u_w (.clk(clk), .d({wm_d, wa_d, we_d, wd_d}), .q({mi_oh[h], ai_oh[h], ei_oh[h], di_oh[h]}));
    end endgenerate

    // ---------------------------------------------------------------- storage
    reg [31:0] t [0:23], bb [0:23], s [0:2], mx [0:3], mp [0:7];
    reg [767:0] final_result;
    assign result = final_result;

    // ---------------------------------------------------------------- operand registers (one stage in front of every unit)
    wire mv = (age >= 10'(P1) && age < 10'(P1 + 24)) || (age >= 10'(P7 + 4) && age < 10'(P7 + 8));
    wire av = (age >= 10'(P2) && age < 10'(P2 + 24)) || (age >= 10'(P3) && age < 10'(P3 + 16)) ||
              (age >= 10'(P5) && age < 10'(P5 + 8))  || (age >= 10'(P7) && age < 10'(P7 + 4));
    wire p4 = age >= 10'(P4) && age < 10'(P4 + 24), p6 = age >= 10'(P6) && age < 10'(P6 + 8);
    reg mv_q, av_q, ev_q, dv_q; reg [31:0] ma_q, mb_q, aa_q, ab_q;
    wire [31:0] ex_q, db_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin mv_q <= 1'b0; av_q <= 1'b0; ev_q <= 1'b0; dv_q <= 1'b0; end
        else begin mv_q <= active && mv; av_q <= active && av; ev_q <= active && p4; dv_q <= active && p6; end
    // AND-OR reads: t[i] for operand register o, byte y, with select copy 4 o + y; b[i] / mx[..] per 16-bit half
    wire [31:0] rd [0:3];                       // 0 ma, 1 aa, 2 ex, 3 db
    wire [31:0] ab_d, mb_d;
    localparam [31:0] EPSV = MUT_PRE ? 32'd0 : HC_EPS;
    generate
        for (k = 0; k < 4; k = k + 1) begin : g_rd
            for (genvar y = 0; y < 4; y = y + 1) begin : g_y
                wire [8*24-1:0] terms;
                for (b = 0; b < 24; b = b + 1) begin : g_b
                    assign terms[8*b +: 8] = {8{rsel[4*k + y][b]}} & t[b][8*y +: 8];
                end
                ot_skf_or #(.W(8), .N(24)) u_or (.x(terms), .y(rd[k][8*y +: 8]));
            end
        end
        for (h = 0; h < 2; h = h + 1) begin : g_abh
            wire [16*29-1:0] terms;
            for (b = 0; b < 24; b = b + 1) begin : g_b
                assign terms[16*b +: 16] = {16{bsel[h][b]}} & bb[b][16*h +: 16];
            end
            for (genvar x = 0; x < 4; x = x + 1) begin : g_m
                wire [31:0] w = mx[x] ^ 32'h80000000;
                assign terms[16*(24 + x) +: 16] = {16{msel[h][x]}} & w[16*h +: 16];
            end
            assign terms[16*28 +: 16] = ({16{p5s[h]}} & 16'(32'h3f800000 >> (16*h))) | ({16{epss[h]}} & 16'(EPSV >> (16*h)));
            ot_skf_or #(.W(16), .N(29)) u_or (.x(terms), .y(ab_d[16*h +: 16]));
            assign mb_d[16*h +: 16] = ({16{s0s[h]}} & s[0][16*h +: 16]) | ({16{s1s[h]}} & s[1][16*h +: 16])
                                    | ({16{s2s[h]}} & s[2][16*h +: 16])
                                    | ({16{!(s0s[h] | s1s[h] | s2s[h])}} & 16'(32'h40000000 >> (16*h)));
        end
    endgenerate
    wire [31:0] rd_ma = rd[0], rd_aa = rd[1], rd_ex = rd[2], rd_db = rd[3];
    always @(posedge clk) begin ma_q <= rd_ma; mb_q <= mb_d; aa_q <= rd_aa; ab_q <= ab_d; end
    generate if (PIN_COPY) begin : g_pin_copy
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_exp (.clk(clk), .d(rd_ex ^ {ineg, 31'd0}), .q(ex_q));
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_div (.clk(clk), .d(rd_db), .q(db_q));
    end else begin : g_legacy_operand
        reg [31:0] ex, db;
        always @(posedge clk) begin ex <= rd_ex ^ {ineg, 31'd0}; db <= rd_db; end
        assign ex_q = ex; assign db_q = db;
    end endgenerate

    // ---------------------------------------------------------------- units
    wire [31:0] my, ay; wire mf, af;
    wire [LM:0] vm; wire [LA:0] va;
    generate if (NAT32 != 0) begin : g_nu
        wire [31:0] ma2, mb2, aa2, ab2, my2, ay2; wire mvo, avo;
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_ma2 (.clk(clk), .d(rd_ma), .q(ma2));
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_mb2 (.clk(clk), .d(mb_d), .q(mb2));
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_aa2 (.clk(clk), .d(rd_aa), .q(aa2));
        (* keep = 1 *) dsdv_gunit_operand_pin32 u_ab2 (.clk(clk), .d(ab_d), .q(ab2));
        ot_s81sl_ve_qmul #(.LAT(LM)) u_mul (clk, rst_v[2], mv_q, ma_q, ma2, mb_q, mb2, my, my2, mvo, mf);
        ot_s81sl_ve_qadd #(.LAT(LA)) u_add (clk, rst_v[5], av_q, aa_q, aa2, ab_q, ab2, ay, ay2, avo, af);
    end else begin : g_lu
        ot_hdc_qmul_lat #(.LAT(LM)) u_mul (clk, rst_v[2], mv_q, ma_q, mb_q, my, mf);
        ot_hdc_qadd_lat #(.KEEP(1), .LAT(LA)) u_add (clk, rst_v[5], av_q, aa_q, ab_q, ay, af);
    end endgenerate
    ot_hdc_vline #(.D(LM)) u_vm (.clk(clk), .rst_n(rst_v[0]), .v(mv_q), .vd(vm));
    ot_hdc_vline #(.D(LA)) u_va (.clk(clk), .rst_n(rst_v[0]), .v(av_q), .vd(va));
    wire mo = vm[LM], ao = va[LA], eo = xe_vo[0], do_ = xd_vo[0];
    assign xe_v = ev_q; assign xe_x = ex_q;
    assign xd_v = dv_q; assign xd_b = db_q;
    wire [3:0] mo_c, ao_c;                      // kept same-edge copies of the unit valid taps (D = the previous tap)
    generate for (k = 0; k < 4; k = k + 1) begin : g_vc
        (* keep = 1 *) ot_skf_kr #(.W(2)) u_v (.clk(clk), .d({vm[LM-1], va[LA-1]}), .q({mo_c[k], ao_c[k]}));
    end endgenerate
    // launch_local: 102 kept enables from launch_pre (8 copies); launch replicas use launch_pre[8..11]
    wire [101:0] launch_local;
    generate for (k = 0; k < 102; k = k + 1) begin : g_launch
        (* keep = 1 *) dsdv_gunit_control_bit u_en (.clk(clk), .d(launch_pre[k % 8]), .q(launch_local[k]));
    end endgenerate
    generate for (b = 0; b < 24; b = b + 1) begin : g_payload
        for (h = 0; h < 2; h = h + 1) begin : g_half
            localparam integer C = (2 * b + h) % 4;
            if (NAT32 != 0) begin : g_byte       // S81-GUVE: one kept gate per byte (L5 ro3 census: 16-bit gate 33-34 loads)
                for (genvar y = 0; y < 2; y = y + 1) begin : g_y
                    wire wm, wa, we, wd;
                    (* keep = 1 *) ot_skf_and2 u_wm (.a(mo_c[C]), .b(mi_oh[h][b]), .y(wm));
                    (* keep = 1 *) ot_skf_and2 u_wa (.a(ao_c[C]), .b(ai_oh[h][b]), .y(wa));
                    (* keep = 1 *) ot_skf_and2 u_we (.a(xe_vo[C]), .b(ei_oh[h][b]), .y(we));
                    (* keep = 1 *) ot_skf_and2 u_wd (.a(xd_vo[C]), .b(di_oh[h][b]), .y(wd));
                    always @(posedge clk) begin
                        if (launch_local[2*b+h]) t[b][16*h+8*y +: 8] <= mixes[32*b+16*h+8*y +: 8];
                        if (wm) t[b][16*h+8*y +: 8] <= my[16*h+8*y +: 8];
                        if (wa) t[b][16*h+8*y +: 8] <= ay[16*h+8*y +: 8];
                        if (we) t[b][16*h+8*y +: 8] <= xe_y[16*h+8*y +: 8];
                        if (wd) t[b][16*h+8*y +: 8] <= xd_y[16*h+8*y +: 8];
                    end
                end
                always @(posedge clk) if (launch_local[48+2*b+h]) bb[b][16*h +: 16] <= bases[32*b+16*h +: 16];
            end else begin : g_word
            wire wm, wa, we, wd;                 // kept gates: the valid copy drives 12 gates, each gate 16 bits
            (* keep = 1 *) ot_skf_and2 u_wm (.a(mo_c[C]), .b(mi_oh[h][b]), .y(wm));
            (* keep = 1 *) ot_skf_and2 u_wa (.a(ao_c[C]), .b(ai_oh[h][b]), .y(wa));
            (* keep = 1 *) ot_skf_and2 u_we (.a(xe_vo[C]), .b(ei_oh[h][b]), .y(we));
            (* keep = 1 *) ot_skf_and2 u_wd (.a(xd_vo[C]), .b(di_oh[h][b]), .y(wd));
            always @(posedge clk) begin
                if (launch_local[2*b+h]) t[b][16*h +: 16] <= mixes[32*b+16*h +: 16];
                if (wm) t[b][16*h +: 16] <= my[16*h +: 16];
                if (wa) t[b][16*h +: 16] <= ay[16*h +: 16];
                if (we) t[b][16*h +: 16] <= xe_y[16*h +: 16];
                if (wd) t[b][16*h +: 16] <= xd_y[16*h +: 16];
                if (launch_local[48+2*b+h]) bb[b][16*h +: 16] <= bases[32*b+16*h +: 16];
            end
            end
        end
    end endgenerate
    generate for (k = 0; k < 6; k = k + 1) begin : g_scale
        always @(posedge clk) if (launch_local[96+k]) s[k/2][16*(k%2) +: 16] <= scales[16*k +: 16];
    end endgenerate

    // ---------------------------------------------------------------- row max (two-stage tree), kept compare halves
    generate for (k = 0; k < 4; k = k + 1) begin : g_max
        for (h = 0; h < 2; h = h + 1) begin : g_pair     // mp[2k + h] = max(t[8 + 4k + 2h + 1], t[8 + 4k + 2h])
            for (genvar hh = 0; hh < 2; hh = hh + 1) begin : g_half
                wire gt;
                (* keep = 1 *) dsdv_gunit_gt32 u_gt (.a(t[8 + 4*k + 2*h + 1]), .c(t[8 + 4*k + 2*h]), .gt(gt));
                always @(posedge clk) if (pmx[4*k + 2*h + hh])
                    mp[2*k + h][16*hh +: 16] <= gt ? t[8 + 4*k + 2*h + 1][16*hh +: 16] : t[8 + 4*k + 2*h][16*hh +: 16];
            end
        end
        for (genvar hh = 0; hh < 2; hh = hh + 1) begin : g_root
            wire gt;
            (* keep = 1 *) dsdv_gunit_gt32 u_gt (.a(mp[2*k + 1]), .c(mp[2*k]), .gt(gt));
            always @(posedge clk) if (pmx1[2*k + hh]) mx[k][16*hh +: 16] <= gt ? mp[2*k + 1][16*hh +: 16] : mp[2*k][16*hh +: 16];
        end
    end endgenerate

    // ---------------------------------------------------------------- Sinkhorn (fanout-safe), 8 kept valid copies
    wire [511:0] se, sy; wire sr, sv, sf, sbusy;
    generate for (k = 0; k < 16; k = k + 1) begin : g_se assign se[32 * k +: 32] = t[k + 8]; end endgenerate
    wire sl_d = active && !armed && age == 10'(EREADY + 1);
    wire [7:0] slc;
    generate for (k = 0; k < 8; k = k + 1) begin : g_slc
        (* keep = 1 *) ot_skf_kr #(.W(1)) u_s (.clk(clk), .d(sl_d), .q(slc[k]));
    end endgenerate
    ot_hdc_sinkhorn_fs #(.ITERS(ITERS), .EPS(HC_EPS), .MUT(MUT_SK), .NVIN(8), .OH(NAT32)) u_sinkh (.clk(clk), .rst_n(rst_v[3]), .rst_n2(rst_v[4]),
        .in_valid(sl), .vin(slc), .in_ready(sr), .in_e(se), .out_valid(sv), .y(sy), .fault(sf), .busy(sbusy));

    // ---------------------------------------------------------------- control, fixed latency (dsdv_gunit_tail)
    assign fault = flt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            active <= 1'b0; age <= 10'd0; sl <= 1'b0; armed <= 1'b0; captured <= 1'b0; capture_q <= 1'b0;
            result_v <= 1'b0; flt <= 1'b0;
        end else begin
            capture_q <= 1'b0; result_v <= 1'b0;
            if (active) age <= age + 1'b1;
            if (lnM) begin
                if (active) flt <= 1'b1;
                active <= 1'b1; age <= 10'd1; armed <= 1'b0; captured <= 1'b0;
            end
            if ((mo && mf) || (ao && af) || (eo && xe_f) || (do_ && xd_f)) flt <= 1'b1;
            if (sl && !sr) flt <= 1'b1;
            if (sl_d) begin sl <= 1'b1; armed <= 1'b1; end
            else sl <= 1'b0;
            if (armed && !captured && sage == 10'(CAP)) begin capture_q <= 1'b1; captured <= 1'b1; end
            if (capture_q && (!sv || sf)) flt <= 1'b1;
            if (active && age == 10'(L - 1)) begin
                result_v <= 1'b1; active <= 1'b0;
                if (!captured) flt <= 1'b1;
            end
        end
    always @(posedge clk or negedge rst_v[0])
        if (!rst_v[0]) sage <= 10'd0;
        else if (sl_d) sage <= 10'd1;
        else if (armed && !captured) sage <= sage + 1'b1;
    wire [47:0] capture_local;
    generate for (k = 0; k < 2; k = k + 1) begin : g_capture
        (* keep = 1 *) dsdv_gunit_capture_bank24 u_en (.clk(clk), .armed(armed), .captured(captured),
            .sage(sage), .deadline(10'(CAP)), .q(capture_local[24*k +: 24]));
    end endgenerate
    generate for (k = 0; k < 48; k = k + 1) begin : g_result
        if (k < 16) begin : g_t
            always @(posedge clk) if (capture_local[k]) final_result[16*k +: 16] <= t[k/2][16*(k%2) +: 16];
        end else begin : g_s
            always @(posedge clk) if (capture_local[k]) final_result[16*k +: 16] <= sy[16*(k-16) +: 16];
        end
    end endgenerate
endmodule
// OR of N W-bit terms (balanced by synthesis)
module ot_skf_or #(parameter integer W = 8, parameter integer N = 2) (input wire [W*N-1:0] x, output reg [W-1:0] y);
    integer i;
    always @* begin y = {W{1'b0}}; for (i = 0; i < N; i = i + 1) y = y | x[W*i +: W]; end
endmodule
// kept FP32 'greater' (dsdv_gunit_tail.greater): one instance per 16-bit half of the selected word
(* keep_hierarchy = 1 *) module dsdv_gunit_gt32 (input wire [31:0] a, input wire [31:0] c, output wire gt);
    assign gt = (a[30:0] == 31'd0 && c[30:0] == 31'd0) ? 1'b0 :
                (a[31] != c[31]) ? !a[31] :
                a[31] ? (a[30:0] < c[30:0]) : (a[30:0] > c[30:0]);
endmodule
`default_nettype wire
