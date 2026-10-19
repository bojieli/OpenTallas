`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-GUNIT whole-model successor (2026-10-19): ot_hdc_sinkhorn_fs -- ot_hdc_sinkhorn_p (CONTROL_SAFE predecode, Q4
// paid range/correction stage) bit for bit and edge for edge, rebuilt FANOUT-SAFE (SAFE-DESIGN item 3): no register and
// no select net drives more than ~24 logical loads.  Same schedule as ot_hdc_sinkhorn_p with Q4 = 1: D0 18, DS 16,
// LAT = D0 + (2 ITERS - 1) DS (642 for ITERS 20); same ports plus in_valid copies (vin: the tail's kept sl copies).
//
// Method (no added edge anywhere; every copy is a same-edge KEPT register of the same D):
//   * one combinational D per state word (st, T, x, quotient, step-0 result), registered into N kept copies; each copy
//     feeds one consumer slice (an adder slice, a Q1 row group, a Q3 row group, a final slice, the output);
//   * every wide select (the st update, the step-0 mode, the fault zeroing) comes from per-group kept registers;
//     the controller (ph / c / cnt) is replicated (ot_hdc_skf_ctl, kept) and each replica registers PREDICTED decodes
//     (ph_next == Z, zcap / scap / idle of the next edge) for <= 16 consumers; the mode bit zm == (ph == Z) exactly;
//   * adders (ot_hdc_skf_add) are sliced: NS mantissa slices of stage A (each with its own operand copy, so its own
//     exponent difference / swap / shifter selects) + one exponent / sticky slice; stage B is replicated per output
//     slice (NB copies of the stage-A registers and of the 24-bit sum);
//   * normalisers are sliced per 8 output bits; quotient Q2 grid shifts are sliced per 8 / 9 output bits with their
//     own E / mode copies; Q4 correction predicates are registered once per final slice.
// Predicted / copy registers are unreset: they hold decodes of the reset state after one clock edge inside reset (the
// relay holds reset for >= 3 edges with the clock running), exactly as the reset state of ot_hdc_sinkhorn_p.
// ---------------------------------------------------------------------------------------------------------------------

// kept same-edge register copy (fixed hierarchy: synthesis never merges two instances)
(* keep_hierarchy = 1 *) module ot_skf_kr #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule

// ---- controller replica: ph / c / cnt and predicted decodes ---------------------------------------------------------
(* keep_hierarchy = 1 *) module ot_hdc_skf_ctl #(
    parameter integer D0 = 18, parameter integer DS = 16, parameter integer STEPS = 39, parameter integer MUT = 0,
    parameter integer NZ = 1, parameter integer NG = 1
) (
    input  wire          clk, rst_n, in_valid,
    output wire [NZ-1:0] zm,                    // == (ph == P_Z)
    output wire [NG-1:0] idle, zc, sc,          // == (ph == P_IDLE), zcap, scap
    output wire [1:0]    ph_o, output wire [4:0] c_o, output wire [7:0] cnt_o
);
    localparam [1:0] P_IDLE = 2'd0, P_Z = 2'd1, P_RUN = 2'd2;
    reg [1:0] ph; reg [4:0] c; reg [7:0] cnt;
    assign ph_o = ph; assign c_o = c; assign cnt_o = cnt;
    wire zcap = (ph == P_Z) && (c == 5'(D0 - 1));
    wire scap = (ph == P_RUN) && (c == 5'(DS - 1 - MUT));
    reg [1:0] ph_n; reg [4:0] c_n; reg [7:0] cnt_n;
    always @* begin
        ph_n = ph; c_n = c; cnt_n = cnt;
        case (ph)
            P_IDLE: if (in_valid) begin ph_n = P_Z; c_n = 5'd0; end
            P_Z: begin
                c_n = c + 5'd1;
                if (zcap) begin c_n = 5'd0; cnt_n = STEPS[7:0]; ph_n = (STEPS == 0) ? P_IDLE : P_RUN; end
            end
            default: begin
                c_n = c + 5'd1;
                if (scap) begin c_n = 5'd0; cnt_n = cnt - 8'd1; if (cnt == 8'd1) ph_n = P_IDLE; end
            end
        endcase
    end
    // c / cnt are never read in P_IDLE (c is cleared on IDLE -> Z, cnt is loaded at zcap): only ph is reset
    always @(posedge clk or negedge rst_n) if (!rst_n) ph <= P_IDLE; else ph <= ph_n;
    always @(posedge clk) begin c <= c_n; cnt <= cnt_n; end
    wire zn = (ph_n == P_Z), in_ = (ph_n == P_IDLE);
    wire zcn = (ph_n == P_Z) && (c_n == 5'(D0 - 1)), scn = (ph_n == P_RUN) && (c_n == 5'(DS - 1 - MUT));
    reg [NZ-1:0] zm_q; reg [NG-1:0] id_q, zc_q, sc_q;
    always @(posedge clk) begin zm_q <= {NZ{zn}}; id_q <= {NG{in_}}; zc_q <= {NG{zcn}}; sc_q <= {NG{scn}}; end
    assign zm = zm_q; assign idle = id_q; assign zc = zc_q; assign sc = sc_q;
endmodule

// ---- fanout-safe positive add (ot_hdc_skp_add with ua = 0, bit for bit) ----------------------------------------------
// Operand copy c < NS feeds mantissa slice c of stage A; copy NS feeds the exponent / guard / sticky slice.
module ot_hdc_skf_add #(parameter integer NS = 4, parameter integer NB = 3) (
    input  wire                 clk,
    input  wire [(NS+1)*8-1:0]  ea,
    input  wire [(NS+1)*24-1:0] ma,
    input  wire [(NS+1)*8-1:0]  eb,
    input  wire [(NS+1)*24-1:0] mb,
    output wire [7:0]           e,
    output wire [23:0]          m,
    output wire                 ovf
);
    localparam integer SW = 24 / NS;           // stage-A mantissa slice width
    localparam integer BW = 24 / NB;           // stage-B output slice width
    localparam integer RW = 24 + 24 + 3 + 8;   // stage-A register word: mg, ahi, {g, any, st}, eg
    wire [RW-1:0] ad [0:NS];                   // stage-A D slices (zero outside the slice)
    genvar c, i, k;
    generate
        for (c = 0; c <= NS; c = c + 1) begin : g_a
            wire [7:0]  ea_c = ea[8*c +: 8], eb_c = eb[8*c +: 8];
            wire [23:0] ma_c = ma[24*c +: 24], mb_c = mb[24*c +: 24];
            wire [8:0] ab0, ab1, ba0, ba1;
            ot_hdc_sk_cadd #(.W(8)) u_dab (.a(ea_c), .b(~eb_c), .s0(ab0), .s1(ab1));   // ea - eb
            ot_hdc_sk_cadd #(.W(8)) u_dba (.a(eb_c), .b(~ea_c), .s0(ba0), .s1(ba1));   // eb - ea
            wire swap = !ab1[8];
            wire [7:0] dab = ab1[7:0], dba = ba1[7:0];
            wire [24:0] shb = (dab >= 8'd25) ? 25'd0 : ({mb_c, 1'b0} >> dab[4:0]);
            wire [24:0] sha = (dba >= 8'd25) ? 25'd0 : ({ma_c, 1'b0} >> dba[4:0]);
            if (c < NS) begin : g_slice
                wire [SW-1:0] mg = swap ? mb_c[SW*c +: SW] : ma_c[SW*c +: SW];
                wire [SW-1:0] ah = swap ? sha[1 + SW*c +: SW] : shb[1 + SW*c +: SW];
                wire [23:0] mg24 = {{(24-SW){1'b0}}, mg} << (SW*c);
                wire [23:0] ah24 = {{(24-SW){1'b0}}, ah} << (SW*c);
                assign ad[c] = {8'd0, 3'd0, ah24, mg24};
            end else begin : g_exp
                wire [23:0] mk_any, mk_st, mk_a_any, mk_a_st;
                for (i = 0; i < 24; i = i + 1) begin : g_mk
                    assign mk_any[i] = (dab > i);   assign mk_st[i] = (dab > i + 1);
                    assign mk_a_any[i] = (dba > i); assign mk_a_st[i] = (dba > i + 1);
                end
                wire b_any = |(mb_c & mk_any), b_st = |(mb_c & mk_st);
                wire a_any = |(ma_c & mk_a_any), a_st = |(ma_c & mk_a_st);
                wire [7:0] eg = swap ? eb_c : ea_c;
                wire g = swap ? sha[0] : shb[0];
                wire an = swap ? a_any : b_any;
                wire st = swap ? a_st : b_st;
                assign ad[c] = {eg, st, an, g, 48'd0};
            end
        end
    endgenerate
    reg [RW-1:0] adw;
    integer s;
    always @* begin adw = {RW{1'b0}}; for (s = 0; s <= NS; s = s + 1) adw = adw | ad[s]; end
    // stage B, NB copies; copy k produces m[BW k +: BW]; copy NB-1 (the top slice) also e / ovf
    wire [23:0] mk [0:NB-1];
    wire [7:0] ek; wire ok;
    generate
        for (k = 0; k < NB; k = k + 1) begin : g_b
            wire [RW-1:0] q;
            (* keep = 1 *) ot_skf_kr #(.W(RW)) u_q (.clk(clk), .d(adw), .q(q));
            wire [23:0] mg_q = q[23:0], ahi_q = q[47:24];
            wire g_q = q[48], any_q = q[49], st_q = q[50];
            wire [7:0] eg_q = q[58:51];
            wire [24:0] s0, s1;
            ot_hdc_sk_cadd #(.W(24)) u_sum (.a(mg_q), .b(ahi_q), .s0(s0), .s1(s1));
            wire carry = s0[24];
            wire rnc = g_q & (st_q | s0[0]);
            wire rc  = s0[0] & (any_q | s0[1]);
            wire [23:0] mp = carry ? (rc ? s1[24:1] : s0[24:1]) : (rnc ? s1[23:0] : s0[23:0]);
            wire ovm = !carry & rnc & s1[24];
            assign mk[k] = {mp[23] | ovm, mp[22:0]};
            if (k == NB - 1) begin : g_top
                wire [8:0] eg1 = {1'b0, eg_q} + 9'd1;
                wire up = carry | ovm;
                assign ek = up ? eg1[7:0] : eg_q;
                assign ok = up & (eg1[7:0] == 8'hFF);
            end
        end
        for (k = 0; k < NB; k = k + 1) begin : g_m
            assign m[BW*k +: BW] = mk[k][BW*k +: BW];
        end
    endgenerate
    assign e = ek; assign ovf = ok;
endmodule

// ---- fanout-safe normaliser slice: m bits [8 s +: 8] of ot_hdc_sk_norm (and e / z) ----------------------------------
module ot_hdc_skf_norm_slice #(parameter integer S = 0) (
    input wire [30:0] x, output wire [7:0] m, output wire signed [9:0] e, output wire z
);
    wire [23:0] mf; wire signed [9:0] ef;
    ot_hdc_sk_norm u_n (.x(x), .m(mf), .e(ef), .z(z));
    assign m = mf[8*S +: 8]; assign e = ef;
endmodule

// ---- reciprocal seed, 3 registered stages, copies for every wide consumer -------------------------------------------
module ot_hdc_skf_seed (
    input  wire          clk,
    input  wire [13:0]   h,              // T bits [13:0] from the seed's own T copy
    input  wire [82:0]   decoded,        // {sq, c2, c1, c0} from the predecode banks (registered at the T edge)
    output wire [8*29-1:0] r             // copy 2k: quotient k, X bits 0..11; copy 2k+1: X bits 12..23
);
    wire [32:0] c0 = decoded[32:0]; wire [22:0] c1 = decoded[55:33]; wire [12:0] c2 = decoded[68:56];
    wire [13:0] sq = decoded[82:69];
    reg [32:0] c0_q;
    always @(posedge clk) c0_q <= c0;
    wire [22:0] c1_q [0:1]; wire [12:0] c2_q [0:1]; wire [13:0] sq_q [0:1]; wire [13:0] h_q [0:3];
    genvar j, b;
    generate
        for (j = 0; j < 2; j = j + 1) begin : g_cc
            (* keep = 1 *) ot_skf_kr #(.W(23)) u_c1 (.clk(clk), .d(c1), .q(c1_q[j]));
            (* keep = 1 *) ot_skf_kr #(.W(13)) u_c2 (.clk(clk), .d(c2), .q(c2_q[j]));
            (* keep = 1 *) ot_skf_kr #(.W(14)) u_sq (.clk(clk), .d(sq), .q(sq_q[j]));
        end
        for (j = 0; j < 4; j = j + 1) begin : g_hc
            (* keep = 1 *) ot_skf_kr #(.W(14)) u_h (.clk(clk), .d(h), .q(h_q[j]));
        end
    endgenerate
    localparam integer W = 48;
    localparam integer NR = 2 + 14 + 14 + 1;
    wire [NR*W-1:0] rows;
    assign rows[0*W +: W] = {{(W-47){1'b0}}, c0_q, 14'd0};
    assign rows[1*W +: W] = {{(W-37){1'b0}}, c1_q[0], 14'd0};
    generate
        for (j = 0; j < 14; j = j + 1) begin : g_c1
            wire [22:0] gc;                      // c1 bit b gated by h copy b / 6
            for (b = 0; b < 23; b = b + 1) begin : g_b
                assign gc[b] = h_q[b / 6][j] & c1_q[(j < 7) ? 0 : 1][b];
            end
            wire [W-1:0] v = {{(W-23){1'b0}}, gc} << (j + 1);
            assign rows[(2 + j)*W +: W] = ~v;
        end
        for (j = 0; j < 14; j = j + 1) begin : g_c2
            wire [12:0] gc;
            for (b = 0; b < 13; b = b + 1) begin : g_b
                assign gc[b] = sq_q[(b < 7) ? 0 : 1][j] & c2_q[(j < 7) ? 0 : 1][b];
            end
            assign rows[(16 + j)*W +: W] = {{(W-13){1'b0}}, gc} << j;
        end
    endgenerate
    assign rows[30*W +: W] = 48'd14 - 48'd262144;
    wire [W-1:0] s, cc;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(s), .c(cc));
    reg [W-1:0] s_q, c_q;
    always @(posedge clk) begin s_q <= s; c_q <= cc; end
    wire [W:0] s0, s1;
    ot_hdc_sk_cadd #(.W(W)) u_cpa (.a(s_q), .b(c_q), .s0(s0), .s1(s1));
    generate
        for (j = 0; j < 8; j = j + 1) begin : g_r
            (* keep = 1 *) ot_skf_kr #(.W(29)) u_r (.clk(clk), .d(s0[46:18]), .q(r[29*j +: 29]));
        end
    endgenerate
endmodule

// ---- correctly rounded X / T, Q1..Q4 + final (ot_hdc_skp_quot Q4 = 1, bit for bit) ----------------------------------
module ot_hdc_skf_quot #(parameter integer MUT_Q4 = 0) (
    input  wire              clk,
    input  wire [6:0]        subn,       // mode copies: [2:0] M' slices, [5:3] X' slices, [6] Q4 low
    input  wire [4*24-1:0]   xm,         // [0..2] Q1 row groups (rows 0-9 / 10-19 / 20-28), [3] compare + X'
    input  wire signed [9:0] xe,
    input  wire              xz,
    input  wire [3*24-1:0]   tm,         // [0] Q3 rows, M' bits 0-11; [1] M' bits 12-23; [2] compare / -T / final
    input  wire signed [9:0] te,
    input  wire [2*29-1:0]   r,          // [0] gates X bits 0-11, [1] X bits 12-23
    output wire [30:0]       y,
    output wire              range
);
    localparam integer WP = 53, DROP = 20;
    genvar j, p, s;
    // ---- Q1
    wire [29*WP-1:0] prow;
    generate
        for (j = 0; j < 29; j = j + 1) begin : g_pp
            for (p = 0; p < WP; p = p + 1) begin : g_p
                if (p >= DROP && p - j >= 0 && p - j < 24) begin : g_on
                    assign prow[j*WP + p] = r[29*((p - j < 12) ? 0 : 1) + j] & xm[24*((j < 10) ? 0 : (j < 20) ? 1 : 2) + (p - j)];
                end else begin : g_off
                    assign prow[j*WP + p] = 1'b0;
                end
            end
        end
    endgenerate
    wire [WP-1:0] ps, pc;
    ot_hdc_sk_csa #(.N(29), .W(WP)) u_xr (.rows(prow), .s(ps), .c(pc));
    wire [23:0] xm3 = xm[72 +: 24], tm2 = tm[48 +: 24];
    wire [24:0] cmp_s0, cmp_s1;
    ot_hdc_sk_cadd #(.W(24)) u_cmp (.a(xm3), .b(~tm2), .s0(cmp_s0), .s1(cmp_s1));
    wire lt = !cmp_s1[24];
    wire signed [10:0] e0 = $signed({xe[9], xe}) - $signed({te[9], te});
    wire signed [10:0] E  = lt ? (e0 - 11'sd1) : e0;
    reg [WP-1:0] ps_q, pc_q;
    always @(posedge clk) begin ps_q <= ps; pc_q <= pc; end
    wire [3:0] lt_q; wire [10:0] E_q [0:7];
    generate
        for (j = 0; j < 4; j = j + 1) begin : g_lt
            (* keep = 1 *) ot_skf_kr #(.W(1)) u_lt (.clk(clk), .d(lt), .q(lt_q[j]));
        end
        for (j = 0; j < 8; j = j + 1) begin : g_e
            (* keep = 1 *) ot_skf_kr #(.W(11)) u_e (.clk(clk), .d(E), .q(E_q[j]));
        end
    endgenerate
    // ---- Q2: CPA, M', grid shift (sliced: own E / mode copy per output slice)
    wire [WP:0] pr0, pr1;
    ot_hdc_sk_cadd #(.W(WP)) u_xrc (.a(ps_q), .b(pc_q), .s0(pr0), .s1(pr1));
    wire [23:0] mp = {lt_q[0] ? pr0[50:39] : pr0[51:40], lt_q[1] ? pr0[38:27] : pr0[39:28]};
    wire [24:0] xpl = {xm3, 1'b0}, xpr = {1'b0, xm3};
    wire [24:0] xp = {lt_q[2] ? xpl[24:12] : xpr[24:12], lt_q[3] ? xpl[11:0] : xpr[11:0]};
    wire [23:0] msd; wire [26:0] xsd; wire [4:0] sh0; wire zs0;
    generate
        for (s = 0; s < 6; s = s + 1) begin : g_sh
            wire signed [10:0] sfull = -11'sd126 - $signed(E_q[s]);
            wire [4:0] sh = (!subn[s] || sfull <= 11'sd0 || sfull > 11'sd24) ? 5'd0 : sfull[4:0];
            if (s < 3) begin : g_m
                wire [23:0] v = mp >> sh;
                assign msd[8*s +: 8] = v[8*s +: 8];
            end else begin : g_x
                wire [26:0] v = {2'b00, xp} << (5'd24 - sh);
                assign xsd[9*(s-3) +: 9] = v[9*(s-3) +: 9];
            end
            if (s == 0) begin : g_s0
                assign sh0 = sh; assign zs0 = subn[0] && (sfull > 11'sd24);
            end
        end
    endgenerate
    wire [23:0] ms_q [0:6]; wire [4:0] s_q [0:1];
    reg [26:0] xs_q; reg zs_q;
    always @(posedge clk) begin xs_q <= xsd; zs_q <= zs0; end
    generate
        for (j = 0; j < 7; j = j + 1) begin : g_ms     // 0..2 Q3 row groups, 3..6 final slices
            (* keep = 1 *) ot_skf_kr #(.W(24)) u_m (.clk(clk), .d(msd), .q(ms_q[j]));
        end
        for (j = 0; j < 2; j = j + 1) begin : g_s
            (* keep = 1 *) ot_skf_kr #(.W(5)) u_s (.clk(clk), .d(sh0), .q(s_q[j]));
        end
    endgenerate
    // ---- Q3: r1 = xs - T - sum_j T_j (ms << (j+1))  (mod 2^27) carry-save
    localparam integer W = 27;
    localparam integer NR = 24 + 3;
    wire [NR*W-1:0] rows;
    generate
        for (j = 0; j < 24; j = j + 1) begin : g_rr
            wire [23:0] gm;
            for (p = 0; p < 24; p = p + 1) begin : g_b
                assign gm[p] = tm[24*((p < 12) ? 0 : 1) + j] & ms_q[j / 8][p];
            end
            wire [W-1:0] v = {3'b000, gm} << (j + 1);
            assign rows[j*W +: W] = ~v;
        end
    endgenerate
    assign rows[24*W +: W] = xs_q;
    assign rows[25*W +: W] = ~{3'b000, tm2};
    assign rows[26*W +: W] = 27'd25;
    wire [W-1:0] ts, tc;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(ts), .c(tc));
    reg [W-1:0] ts_q, tc_q;
    always @(posedge clk) begin ts_q <= ts; tc_q <= tc; end
    // ---- Q4: remainder signs -> correction / range predicates, registered per final slice
    wire [W-1:0] t2 = ~{2'b00, tm2, 1'b0};
    wire [W-1:0] u_s = ts_q ^ tc_q ^ t2;
    wire [W-1:0] u_maj = (ts_q & tc_q) | (ts_q & t2) | (tc_q & t2);
    wire [W-1:0] u_cs = {u_maj[W-2:0], 1'b0};
    wire [W:0] a1, a1p, a2, a2p;
    ot_hdc_sk_cadd #(.W(W)) u_r1 (.a(ts_q), .b(tc_q), .s0(a1), .s1(a1p));
    ot_hdc_sk_cadd #(.W(W)) u_r2 (.a(u_s), .b(u_cs), .s0(a2), .s1(a2p));
    wire neg1 = a1[W-1];
    wire neg2 = a2p[W-1];
    wire z1 = ((ts_q ^ tc_q) == {(ts_q[W-2:0] | tc_q[W-2:0]), 1'b0});
    wire z2 = ((u_s ^ u_cs) == {(u_s[W-2:0] | u_cs[W-2:0]), 1'b1});
    wire [23:0] m30 = ms_q[3];
    wire inc1 = (!neg1 & !z1) | (z1 & m30[0]);
    wire inc2 = (!neg2 & !z2) | (z2 & !m30[0]);
    wire signed [10:0] eq4 = E_q[6];
    wire signed [10:0] eb4 = eq4 + 11'sd127, eb41 = eq4 + 11'sd128;
    wire sub4 = s_q[0] != 5'd0;
    wire hi0 = !sub4 && (eb4 > 11'sd254);
    wire hi1 = !sub4 && (eb41 > 11'sd254);
    wire low = !subn[6] && (eb4 < 11'sd1);
    wire zero = xz | zs_q;
    wire [2:0] pack_q [0:3]; wire [5:0] range_q;
    generate
        for (j = 0; j < 4; j = j + 1) begin : g_pk
            (* keep = 1 *) ot_skf_kr #(.W(3)) u_p (.clk(clk), .d({inc1, inc2, zero}), .q(pack_q[j]));
        end
    endgenerate
    (* keep = 1 *) ot_skf_kr #(.W(6)) u_rng (.clk(clk), .d({inc1, inc2, hi0, hi1, low ^ (MUT_Q4 != 0), zero}), .q(range_q));
    // ---- final, sliced: f 0 = exponent field [30:23], f 1..3 = mantissa [22:15] [14:7] [6:0]
    wire signed [10:0] ef = E_q[7];
    wire signed [10:0] ebf = ef + 11'sd127, ebf1 = ef + 11'sd128;
    wire subf = s_q[1] != 5'd0;
    wire [30:0] yv [0:3];
    generate
        for (j = 0; j < 4; j = j + 1) begin : g_fin
            wire [23:0] m3 = ms_q[3 + j];
            wire [2:0] pk = pack_q[j];
            wire [24:0] m1_s0, m1_s1;
            ot_hdc_sk_cadd #(.W(24)) u_inc (.a(m3), .b(24'd0), .s0(m1_s0), .s1(m1_s1));
            wire [23:0] m2_s0, m2_s1;
            ot_hdc_sk_cadd #(.W(23)) u_inc2 (.a(m3[23:1]), .b(23'd0), .s0(m2_s0), .s1(m2_s1));
            wire [24:0] mf = pk[1] ? {m2_s1, m3[0]} : (pk[2] ? m1_s1 : {1'b0, m3});
            wire ovm = mf[24];
            if (j == 0) begin : g_field
                wire [7:0] field = subf ? {7'd0, mf[23]} : (ovm ? ebf1[7:0] : ebf[7:0]);
                assign yv[j] = pk[0] ? 31'd0 : {field, 23'd0};
            end else begin : g_mant
                wire [22:0] mv = ovm ? 23'd0 : mf[22:0];
                assign yv[j] = pk[0] ? 31'd0 : {8'd0, mv};
            end
        end
    endgenerate
    assign y = {yv[0][30:23], yv[1][22:15], yv[2][14:7], yv[3][6:0]};
    wire [23:0] m31 = ms_q[4];
    wire range_ovm = range_q[4] ? (&m31[23:1]) : (range_q[5] && (&m31[23:0]));
    assign range = !range_q[0] && ((range_ovm ? range_q[2] : range_q[3]) || range_q[1]);
endmodule

// ---- the Sinkhorn ---------------------------------------------------------------------------------------------------
module ot_hdc_sinkhorn_fs #(
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD,
    parameter integer MUT_Q4 = 0,
    parameter integer MUT = 0,                  // bench only: 1 = a steady step lands one stage early
    parameter integer NVIN = 8                  // in_valid copies (vin)
) (
    input  wire            clk,
    input  wire            rst_n,               // master + st-select replicas (11 asynchronous pins)
    input  wire            rst_n2,              // mode replicas (18)
    input  wire            in_valid,            // the master copy (== every vin bit)
    input  wire [NVIN-1:0] vin,                 // kept same-edge copies of in_valid
    output wire            in_ready,
    input  wire [511:0]    in_e,                // element (r, c) at [32 (4r + c) +: 32]
    output reg             out_valid,
    output wire [511:0]    y,
    output reg             fault,
    output wire            busy
);
    localparam integer STEPS = 2 * ITERS - 1;
    localparam integer D0 = 18, DS = 16;
    localparam integer LAT = D0 + STEPS * DS;
    localparam [1:0] P_IDLE = 2'd0, P_Z = 2'd1, P_RUN = 2'd2;
    localparam [7:0]  EPS_E = (EPS[30:23] == 8'd0) ? 8'd1 : EPS[30:23];
    localparam [23:0] EPS_M = {EPS[30:23] != 8'd0, EPS[22:0]};
    localparam integer NS = 4, NA = NS + 1;      // adder operand copies
    localparam integer NG = 32;                  // st select groups of 16 bits
    localparam integer NCS = 4;                  // controller replicas for the st selects (8 groups each)
    localparam integer NZR = 9;                  // controller replicas for the mode copies (16 each)
    genvar r, k, g, n;

    // ---- controller replicas ---------------------------------------------------------------------------------------
    wire [NG-1:0] g_idle, g_zc, g_sc;
    wire [NZR*16-1:0] zmv;
    wire [1:0] ph; wire [4:0] c; wire [7:0] cnt;
    generate
        for (n = 0; n < NCS; n = n + 1) begin : g_cs
            wire [0:0] zm_u; wire [1:0] ph_u; wire [4:0] c_u; wire [7:0] cnt_u;
            (* keep = 1 *) ot_hdc_skf_ctl #(.D0(D0), .DS(DS), .STEPS(STEPS), .MUT(MUT), .NZ(1), .NG(8)) u_c (.clk(clk), .rst_n(rst_n),
                .in_valid(vin[n % NVIN]), .zm(zm_u), .idle(g_idle[8*n +: 8]), .zc(g_zc[8*n +: 8]), .sc(g_sc[8*n +: 8]),
                .ph_o(ph_u), .c_o(c_u), .cnt_o(cnt_u));
            if (n == 0) begin : g_master
                assign ph = ph_u; assign c = c_u; assign cnt = cnt_u;
            end
        end
        for (n = 0; n < NZR; n = n + 1) begin : g_zr
            wire [0:0] id_u, zc_u, sc_u; wire [1:0] ph_u; wire [4:0] c_u; wire [7:0] cnt_u;
            (* keep = 1 *) ot_hdc_skf_ctl #(.D0(D0), .DS(DS), .STEPS(STEPS), .MUT(MUT), .NZ(16), .NG(1)) u_c (.clk(clk), .rst_n(rst_n2),
                .in_valid(vin[(NCS + n) % NVIN]), .zm(zmv[16*n +: 16]), .idle(id_u), .zc(zc_u), .sc(sc_u),
                .ph_o(ph_u), .c_o(c_u), .cnt_o(cnt_u));
        end
    endgenerate
    assign in_ready = (ph == P_IDLE);
    assign busy = (ph != P_IDLE);
    wire zcap = (ph == P_Z) && (c == 5'(D0 - 1));
    wire scap = (ph == P_RUN) && (c == 5'(DS - 1 - MUT));
    // mode copy allocation: element e (row r = e / 4... storage index) gets 8 copies: subn[6:0] + xz gate; row r gets 4
    // more (T mux x 3, b4).  zmv[8 e +: 8] for e = 0..15 (128), zmv[128 + 4 r +: 4] for r = 0..3 (16): 144 = 9 x 16.
    function automatic integer ZE(input integer e, input integer i); ZE = 8 * e + i; endfunction
    function automatic integer ZR(input integer rr, input integer i); ZR = 128 + 4 * rr + i; endfunction

    // ---- the state: one D, kept copies ------------------------------------------------------------------------------
    // copies: 0 = hold / output / input checks; 1..NA = adder operand copies; NA+1..NA+3 = X normaliser slices
    localparam integer NSTC = 1 + NA + 3;
    wire [511:0] stc [0:NSTC-1];
    wire [30:0] q [0:15];
    wire [15:0] q_rng;
    wire [31:0] z_out [0:15];
    wire [511:0] std_d;
    generate
        for (g = 0; g < NG; g = g + 1) begin : g_std
            wire acc_g = g_idle[g] & vin[g % NVIN];
            wire [15:0] zo, qo;
            for (k = 0; k < 16; k = k + 1) begin : g_b
                localparam integer B = 16 * g + k;
                assign zo[k] = z_out[B / 32][B % 32];
                assign qo[k] = (B % 32 == 31) ? 1'b0 : q[B / 32][B % 32];
            end
            assign std_d[16*g +: 16] = acc_g ? in_e[16*g +: 16] : g_zc[g] ? zo : g_sc[g] ? qo : stc[0][16*g +: 16];
        end
        for (n = 0; n < NSTC; n = n + 1) begin : g_stc
            (* keep = 1 *) ot_skf_kr #(.W(512)) u_st (.clk(clk), .d(std_d), .q(stc[n]));
        end
    endgenerate

    // ---- S1 (side): X operand = normalised state word (3 slice copies), input checks (copy 0) ----------------------
    wire [23:0] x_m [0:15][0:3]; wire signed [9:0] x_e [0:15]; wire x_z [0:15];
    reg sub_any, bin_any;
    wire [15:0] w_sub, w_bad;
    generate for (k = 0; k < 16; k = k + 1) begin : g_x
        wire [31:0] w0 = stc[0][32*k +: 32];
        assign w_sub[k] = (w0[30:23] == 8'd0);
        assign w_bad[k] = (w0[31] && (w0[30:0] != 31'd0)) || (w0[30:23] == 8'hFF);
        wire [23:0] nm; wire signed [9:0] ne [0:2]; wire nz [0:2];
        for (n = 0; n < 3; n = n + 1) begin : g_ns
            ot_hdc_skf_norm_slice #(.S(n)) u_n (.x(stc[NA + 1 + n][32*k +: 31]), .m(nm[8*n +: 8]), .e(ne[n]), .z(nz[n]));
        end
        reg signed [9:0] xe_q; reg xz_q;
        always @(posedge clk) begin xe_q <= ne[0]; xz_q <= nz[0]; end
        assign x_e[k] = xe_q; assign x_z[k] = xz_q;
        for (n = 0; n < 4; n = n + 1) begin : g_xm
            (* keep = 1 *) ot_skf_kr #(.W(24)) u_xm (.clk(clk), .d(nm), .q(x_m[k][n]));
        end
    end endgenerate
    always @(posedge clk) begin sub_any <= |w_sub; bin_any <= |w_bad; end

    // ---- per row: S1..S6 adds, S7..S8 T, seed, 4 quotients ----------------------------------------------------------
    wire [3:0] bad4;
    generate for (r = 0; r < 4; r = r + 1) begin : g_row
        // decoded operand copies of the row's four state words
        wire [NA*8-1:0] ee [0:3]; wire [NA*24-1:0] mm [0:3];
        for (k = 0; k < 4; k = k + 1) begin : g_dec
            for (n = 0; n < NA; n = n + 1) begin : g_c
                wire [31:0] w = stc[1 + n][32*(4*r + k) +: 32];
                assign ee[k][8*n +: 8] = (w[30:23] == 8'd0) ? 8'd1 : w[30:23];
                assign mm[k][24*n +: 24] = {w[30:23] != 8'd0, w[22:0]};
            end
        end
        // S1
        wire [7:0] e1; wire o1; wire [23:0] m1;
        ot_hdc_skf_add #(.NS(NS)) u_s1 (.clk(clk), .ea(ee[0]), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]), .e(e1), .m(m1), .ovf(o1));
        wire [NA*8-1:0] e1_q; wire [NA*24-1:0] m1_q; reg b1_q;
        for (n = 0; n < NA; n = n + 1) begin : g_r1
            (* keep = 1 *) ot_skf_kr #(.W(32)) u_r (.clk(clk), .d({e1, m1}), .q({e1_q[8*n +: 8], m1_q[24*n +: 24]}));
        end
        always @(posedge clk) b1_q <= o1;
        // S2
        wire [7:0] e2; wire o2; wire [23:0] m2;
        ot_hdc_skf_add #(.NS(NS)) u_s2 (.clk(clk), .ea(e1_q), .ma(m1_q), .eb(ee[2]), .mb(mm[2]), .e(e2), .m(m2), .ovf(o2));
        wire [NA*8-1:0] e2_q; wire [NA*24-1:0] m2_q; reg b2_q;
        for (n = 0; n < NA; n = n + 1) begin : g_r2
            (* keep = 1 *) ot_skf_kr #(.W(32)) u_r (.clk(clk), .d({e2, m2}), .q({e2_q[8*n +: 8], m2_q[24*n +: 24]}));
        end
        always @(posedge clk) b2_q <= b1_q | o2;
        // S3 (copies 0..NA-1 for S4, NA..NA+2 for the step-0 normaliser slices)
        wire [7:0] e3; wire o3; wire [23:0] m3;
        ot_hdc_skf_add #(.NS(NS)) u_s3 (.clk(clk), .ea(e2_q), .ma(m2_q), .eb(ee[3]), .mb(mm[3]), .e(e3), .m(m3), .ovf(o3));
        wire [(NA+3)*8-1:0] e3_q; wire [(NA+3)*24-1:0] m3_q; reg b3_q;
        for (n = 0; n < NA + 3; n = n + 1) begin : g_r3
            (* keep = 1 *) ot_skf_kr #(.W(32)) u_r (.clk(clk), .d({e3, m3}), .q({e3_q[8*n +: 8], m3_q[24*n +: 24]}));
        end
        always @(posedge clk) b3_q <= b2_q | o3;
        // S4: steady T = sum + eps (normal); step 0 T = normalised sum
        wire [7:0] et; wire ot_; wire [23:0] mt;
        ot_hdc_skf_add #(.NS(NS)) u_ae (.clk(clk), .ea(e3_q[0 +: NA*8]), .ma(m3_q[0 +: NA*24]), .eb({NA{EPS_E}}), .mb({NA{EPS_M}}),
                                         .e(et), .m(mt), .ovf(ot_));
        wire signed [9:0] te_s = $signed({2'b00, et}) - 10'sd127;
        wire [23:0] nt_m; wire signed [9:0] nt_e [0:2]; wire tz [0:2];
        for (n = 0; n < 3; n = n + 1) begin : g_nt
            wire [7:0] e3n = e3_q[8*(NA + n) +: 8]; wire [23:0] m3n = m3_q[24*(NA + n) +: 24];
            ot_hdc_skf_norm_slice #(.S(n)) u_n (.x({m3n[23] ? e3n : 8'd0, m3n[22:0]}), .m(nt_m[8*n +: 8]), .e(nt_e[n]), .z(tz[n]));
        end
        reg [23:0] nt_m_q; reg signed [9:0] nt_e_q; reg tz_q;
        always @(posedge clk) begin nt_m_q <= nt_m; nt_e_q <= nt_e[0]; tz_q <= tz[0]; end
        reg b4_q;
        always @(posedge clk) b4_q <= b3_q | (zmv[ZR(r, 3)] ? tz_q : (ot_ | !mt[23]));
        assign bad4[r] = b4_q;
        // T: one mux (mode copies per 12 bits), registered into the per-consumer copies
        wire [23:0] tm_d = {zmv[ZR(r, 0)] ? nt_m_q[23:12] : mt[23:12], zmv[ZR(r, 1)] ? nt_m_q[11:0] : mt[11:0]};
        wire [9:0]  te_d = zmv[ZR(r, 2)] ? nt_e_q : te_s;
        // predecode banks (registered at the T edge; source-exact ROM truth tables)
        wire [82:0] decoded;
        wire [8:0] ix = tm_d[22:14];
        wire [8:0] sx = tm_d[13] ? tm_d[12:4] : ~tm_d[12:4];
        wire [23:0] pd, sd;
        for (genvar pg = 0; pg < 3; pg = pg + 1) begin : g_group
            for (genvar pv = 0; pv < 8; pv = pv + 1) begin : g_value
                assign pd[pg*8+pv] = ix[pg*3 +: 3] == pv;
                assign sd[pg*8+pv] = sx[pg*3 +: 3] == pv;
            end
        end
        (* keep = 1 *) ot_hdc_skf_decode_c0lo u_c0l (.clk(clk), .d(pd), .q(decoded[16:0]));
        (* keep = 1 *) ot_hdc_skf_decode_c0hi u_c0h (.clk(clk), .d(pd), .q(decoded[32:17]));
        (* keep = 1 *) ot_hdc_skf_decode_c1 u_c1 (.clk(clk), .d(pd), .q(decoded[55:33]));
        (* keep = 1 *) ot_hdc_skf_decode_c2 u_c2 (.clk(clk), .d(pd), .q(decoded[68:56]));
        (* keep = 1 *) ot_hdc_skf_decode_sq u_sq (.clk(clk), .d(sd), .q(decoded[82:69]));
        // T copies: per quotient {tm x 3, te}; seed h
        wire [13:0] th;
        (* keep = 1 *) ot_skf_kr #(.W(14)) u_th (.clk(clk), .d(tm_d[13:0]), .q(th));
        wire [8*29-1:0] rs;
        ot_hdc_skf_seed u_seed (.clk(clk), .h(th), .decoded(decoded), .r(rs));
        for (k = 0; k < 4; k = k + 1) begin : g_q
            wire [3*24-1:0] tmc; wire [9:0] tec;
            for (n = 0; n < 3; n = n + 1) begin : g_tc
                (* keep = 1 *) ot_skf_kr #(.W(24)) u_t (.clk(clk), .d(tm_d), .q(tmc[24*n +: 24]));
            end
            (* keep = 1 *) ot_skf_kr #(.W(10)) u_te (.clk(clk), .d(te_d), .q(tec));
            localparam integer EL = 4*r + k;     // element (r, k); result stored at 4k + r (transposed)
            wire [6:0] sn;
            for (n = 0; n < 7; n = n + 1) begin : g_sn
                assign sn[n] = zmv[ZE(EL, n)];
            end
            ot_hdc_skf_quot #(.MUT_Q4(MUT_Q4)) u_q (.clk(clk), .subn(sn),
                .xm({x_m[EL][3], x_m[EL][2], x_m[EL][1], x_m[EL][0]}), .xe(x_e[EL]),
                .xz(x_z[EL] & zmv[ZE(EL, 7)]), .tm(tmc), .te($signed(tec)), .r(rs[2*29*k +: 2*29]),
                .y(q[4*k + r]), .range(q_rng[4*k + r]));
        end
    end endgenerate

    // ---- step 0 final: register the quotient (adder operand copies), + eps -> state --------------------------------
    reg [15:0] zr;
    wire [15:0] z_ov;
    generate for (k = 0; k < 16; k = k + 1) begin : g_z
        always @(posedge clk) zr[k] <= q_rng[k];
        wire [NA*8-1:0] qe; wire [NA*24-1:0] qm;
        for (n = 0; n < NA; n = n + 1) begin : g_zc
            wire [30:0] zq;
            (* keep = 1 *) ot_skf_kr #(.W(31)) u_zq (.clk(clk), .d(q[k]), .q(zq));
            assign qe[8*n +: 8] = (zq[30:23] == 8'd0) ? 8'd1 : zq[30:23];
            assign qm[24*n +: 24] = {zq[30:23] != 8'd0, zq[22:0]};
        end
        wire [7:0] oe; wire [23:0] om;
        ot_hdc_skf_add #(.NS(NS)) u_eps (.clk(clk), .ea(qe), .ma(qm), .eb({NA{EPS_E}}), .mb({NA{EPS_M}}),
                                          .e(oe), .m(om), .ovf(z_ov[k]));
        assign z_out[k] = {1'b0, om[23] ? oe : 8'd0, om[22:0]};
    end endgenerate
    wire zbad = bin_any | (|bad4) | (|zr) | (|z_ov);
    wire sbad = sub_any | (|bad4) | (|q_rng);

    // ---- master control (fixed schedule): flt / fault / out_valid from replica 0's state ----------------------------
    reg flt;
    reg flt_n, fault_n, ov_n;
    always @* begin
        flt_n = flt; fault_n = fault; ov_n = 1'b0;
        case (ph)
            P_IDLE: if (in_valid) flt_n = 1'b0;
            P_Z: if (zcap) begin
                flt_n = flt | zbad;
                if (STEPS == 0) begin ov_n = 1'b1; fault_n = flt | zbad; end
            end
            default: if (scap) begin
                flt_n = flt | sbad;
                if (cnt == 8'd1) begin ov_n = 1'b1; fault_n = flt | sbad; end
            end
        endcase
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin flt <= 1'b0; out_valid <= 1'b0; fault <= 1'b0; end
        else begin flt <= flt_n; out_valid <= ov_n; fault <= fault_n; end
    // fault copies (zero the output, 16 bits each); fault_n == fault during reset
    wire [31:0] fc;
    generate for (g = 0; g < 32; g = g + 1) begin : g_fc
        (* keep = 1 *) ot_skf_kr #(.W(1)) u_f (.clk(clk), .d(fault_n), .q(fc[g]));
        assign y[16*g +: 16] = fc[g] ? 16'd0 : stc[0][16*g +: 16];
    end endgenerate
`ifndef SYNTHESIS
    initial if (D0 > 31 || DS > 31) $error("ot_hdc_sinkhorn_fs: stage counter is 5 bits");
`endif
endmodule
`default_nettype wire
