`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-SAFE-FIX/GUNIT (2026-10-19): ot_hdc_sinkhorn_p -- the hyper-connection Sinkhorn of ot_hdc_sinkhorn.sv, bit for bit
// (same function, same fail-closed rules, same port list), PIPELINED on the core clock: no gated clock, no multicycle
// exception.  ot_hdc_sinkhorn does one whole normalisation per unit edge (state -> 4 chained adds -> seed -> quotient ->
// state: 138 logic levels, ~5.3 ns) and ran in the G-unit as a 9-cycle multicycle path behind an ICG
// (gunit_sinkh_mcp.sdc) -- a masked path (SAFE-DESIGN item 4).  Here every normalisation is cut into registered stages
// of <= ~20 levels at the operation boundaries of tools/gen_hdc_sinkhorn_recip_rom.py's integer specification:
//
//   S1..S6  the row's three chained two-stage POSITIVE adds (ot_hdc_sk_add; the chained exponent eg + up is resolved into e and
//           registered, which ot_hdc_sk_add's ua = 0 form reproduces exactly)
//   S7..S8 steady: + eps (the denominator T);  step 0: normalise the row sum (subnormal T)          -> T, kept copies
//   S9..S11 seed R ~ 1/T: ROM read | carry-save tree | carry-propagate                              -> R, kept copies
//   Q1..Q3  quotient: X*R carry-save | CPA, M' (+ step-0 grid shift) | exact-remainder carry-save
//   final   remainder signs, M' + {0,1,2}, pack  -> state (steady), or -> register -> + eps -> state (step 0)
//
// One step is in flight at a time (the recurrence is dependent), so a stage register is valid from the edge that
// fills it until the next step's value reaches it; the state (st) and the X operands are stable for the whole step and
// are read directly by the later stages (ordinary single-cycle reg -> reg paths, nothing held across edges by SDC).
// Step 0 (subnormal-capable) and the steady steps share ONE datapath: st takes in_e at accept, the step-0 row sums are
// the same three adds, and a mode bit (zm, kept copies per element) selects S4 (norm vs + eps), the quotient's grid
// shift / range rule (SUBN) and the final + eps.  In steady mode an X operand is the normalised word; it differs from
// ot_hdc_sinkhorn's raw significand only for a subnormal state word, which both units flag as a fault (y = 0).
//
// SCHEDULE (fixed, no handshake moves it): accept (in_valid & in_ready) at edge a0; step 0 lands in st at a0 + D0,
// steady step k at a0 + D0 + k DS; out_valid pulses one edge at a0 + LAT, LAT = D0 + (2 ITERS - 1) DS (602 for
// ITERS 20).  y and fault hold until the next accept (y = 0 on fault).
// ---------------------------------------------------------------------------------------------------------------------

module ot_hdc_skp_add (
    input wire clk,
    input  wire [7:0]  ea,
    input  wire        ua,
    input  wire [23:0] ma,
    input  wire [7:0]  eb,
    input  wire [23:0] mb,
    output wire [7:0]  eg,
    output wire        up,
    output wire [7:0]  e,
    output wire [23:0] m,
    output wire        ovf
);
    wire [8:0] ea1 = {1'b0, ea} + 9'd1;
    wire [7:0] ea_c [0:1];
    assign ea_c[0] = ea;
    assign ea_c[1] = ea1[7:0];
    wire [1:0]  age_c;
    wire [7:0]  dba_c [0:1];
    wire [24:0] shb_c [0:1];
    wire [1:0]  bany_c, bst_c;
    genvar u, i;
    generate
        for (u = 0; u < 2; u = u + 1) begin : g_u
            wire [8:0] ab0, ab1, ba0, ba1;
            ot_hdc_sk_cadd #(.W(8)) u_dab (.a(ea_c[u]), .b(~eb), .s0(ab0), .s1(ab1));   // ea - eb
            ot_hdc_sk_cadd #(.W(8)) u_dba (.a(eb), .b(~ea_c[u]), .s0(ba0), .s1(ba1));   // eb - ea
            assign age_c[u] = ab1[8];
            assign dba_c[u] = ba1[7:0];                  // valid when b > a
            // b aligned under a, and its shifted-out bits (all early); dab valid when a >= b
            assign shb_c[u] = (ab1[7:0] >= 8'd25) ? 25'd0 : ({mb, 1'b0} >> ab1[4:0]);
            wire [23:0] mk_any, mk_st;
            for (i = 0; i < 24; i = i + 1) begin : g_mk
                assign mk_any[i] = (ab1[7:0] > i);
                assign mk_st[i]  = (ab1[7:0] > i + 1);
            end
            assign bany_c[u] = |(mb & mk_any);
            assign bst_c[u]  = |(mb & mk_st);
        end
    endgenerate
    wire        a_ge  = ua ? age_c[1] : age_c[0];
    wire        swap  = !a_ge;                   // b strictly larger exponent
    wire [7:0]  dba   = ua ? dba_c[1] : dba_c[0];
    wire [24:0] shb   = ua ? shb_c[1] : shb_c[0];
    wire        b_any = ua ? bany_c[1] : bany_c[0];
    wire        b_st  = ua ? bst_c[1] : bst_c[0];

    // a aligned under b (a is the late operand)
    wire [24:0] sha = (dba >= 8'd25) ? 25'd0 : ({ma, 1'b0} >> dba[4:0]);
    wire [23:0] mk_a_any, mk_a_st;
    generate
        for (i = 0; i < 24; i = i + 1) begin : g_mka
            assign mk_a_any[i] = (dba > i);
            assign mk_a_st[i]  = (dba > i + 1);
        end
    endgenerate
    wire a_any = |(ma & mk_a_any), a_st = |(ma & mk_a_st);

    wire [7:0]  eA   = ua ? ea1[7:0] : ea;
    wire [7:0] eg_a = swap ? eb : eA;
    wire [23:0] mg_a   = swap ? mb : ma;
    wire [23:0] ahi_a  = swap ? sha[24:1] : shb[24:1];
    wire        g_a    = swap ? sha[0] : shb[0];
    wire        any_a  = swap ? a_any : b_any;
    wire        st_a   = swap ? a_st : b_st;

    // Arithmetic boundary: align/exponent/sticky in one stage; sum/round/pack in the next.
    reg [23:0] mg_q, ahi_q;
    reg g_q, any_q, st_q;
    reg [7:0] eg_q;
    always @(posedge clk) begin
        mg_q <= mg_a; ahi_q <= ahi_a; g_q <= g_a; any_q <= any_a; st_q <= st_a; eg_q <= eg_a;
    end
    assign eg = eg_q;
    wire [24:0] s0, s1;
    ot_hdc_sk_cadd #(.W(24)) u_sum (.a(mg_q), .b(ahi_q), .s0(s0), .s1(s1));
    wire carry = s0[24];
    wire rnc = g_q & (st_q | s0[0]);
    wire rc  = s0[0] & (any_q | s0[1]);
    wire [23:0] mp = carry ? (rc ? s1[24:1] : s0[24:1]) : (rnc ? s1[23:0] : s0[23:0]);
    wire ovm = !carry & rnc & s1[24];          // S = 2^24 - 1 rounded up to 2^24
    wire [8:0] eg1 = {1'b0, eg_q} + 9'd1;
    assign up  = carry | ovm;
    assign e   = up ? eg1[7:0] : eg_q;
    assign m   = {mp[23] | ovm, mp[22:0]};
    assign ovf = up & (eg1[7:0] == 8'hFF);
endmodule

// ---- reciprocal seed, 3 registered stages (ROM | carry-save tree | CPA); NC kept output copies ------------------------
module ot_hdc_skp_seed #(
    parameter integer NC = 4,
    parameter integer CONTROL_SAFE = 0
) (
    input  wire              clk,
    input  wire [23:0]       tm,
    input wire [82:0] decoded,
    output wire [29*NC-1:0]  r
);
    wire [32:0] c0; wire [22:0] c1; wire [12:0] c2; wire [13:0] sq;
    wire [13:0] h  = tm[13:0];
    wire [12:0] dm = h[13] ? h[12:0] : ~h[12:0];
    generate if (CONTROL_SAFE) begin : g_decoded
        assign {sq, c2, c1, c0} = decoded;
    end else begin : g_case_rom
        ot_hdc_sk_recip_rom u_rom (.i(tm[22:14]), .c0(c0), .c1(c1), .c2(c2));
        ot_hdc_sk_sq_rom u_sq (.dmh(dm[12:4]), .sq(sq));
    end endgenerate
    (* keep = "true" *) reg [32:0] c0_q;
    (* keep = "true" *) reg [22:0] c1_q;
    (* keep = "true" *) reg [12:0] c2_q;
    (* keep = "true" *) reg [13:0] sq_q, h_q;
    always @(posedge clk) begin c0_q <= c0; c1_q <= c1; c2_q <= c2; sq_q <= sq; h_q <= h; end
    localparam integer W = 48;
    localparam integer NR = 2 + 14 + 14 + 1;
    wire [NR*W-1:0] rows;
    assign rows[0*W +: W] = {{(W-47){1'b0}}, c0_q, 14'd0};
    assign rows[1*W +: W] = {{(W-37){1'b0}}, c1_q, 14'd0};
    genvar j;
    generate
        for (j = 0; j < 14; j = j + 1) begin : g_c1
            wire [W-1:0] v = h_q[j] ? ({{(W-23){1'b0}}, c1_q} << (j + 1)) : {W{1'b0}};
            assign rows[(2 + j)*W +: W] = ~v;
        end
        for (j = 0; j < 14; j = j + 1) begin : g_c2
            assign rows[(16 + j)*W +: W] = sq_q[j] ? ({{(W-13){1'b0}}, c2_q} << j) : {W{1'b0}};
        end
    endgenerate
    assign rows[30*W +: W] = 48'd14 - 48'd262144;
    wire [W-1:0] s, c;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(s), .c(c));
    reg [W-1:0] s_q, c_q;
    always @(posedge clk) begin s_q <= s; c_q <= c; end
    wire [W:0] s0, s1;
    ot_hdc_sk_cadd #(.W(W)) u_cpa (.a(s_q), .b(c_q), .s0(s0), .s1(s1));
    generate
        for (j = 0; j < NC; j = j + 1) begin : g_r
            (* keep = "true" *) reg [28:0] rq;
            always @(posedge clk) rq <= s0[46:18];
            assign r[29*j +: 29] = rq;
        end
    endgenerate
endmodule

// ---- correctly rounded X / T from the seed, 3 registered stages + a combinational final ------------------------------
// Same integer construction as ot_hdc_sk_quot; subn (runtime) = its SUBN parameter.  Every input is stable for the
// whole step (xm/xe/xz/tm/te/subn from >= 4 edges before, r from the seed's output register).
module ot_hdc_skp_quot #(
    parameter integer Q4 = 0,
    parameter integer MUT_Q4 = 0  // source bench only: corrupt the range predicate
) (
    input  wire              clk,
    input  wire              subn,
    input  wire [23:0]       xm,
    input  wire signed [9:0] xe,
    input  wire              xz,
    input  wire [23:0]       tm,
    input  wire signed [9:0] te,
    input  wire [28:0]       r,
    output wire [30:0]       y,
    output wire              range
);
    // ---- Q1: X R carry-save (24 x 29, columns below 20 not built), X < T, exponent
    localparam integer WP = 53, DROP = 20;
    wire [29*WP-1:0] prow;
    genvar j;
    generate
        for (j = 0; j < 29; j = j + 1) begin : g_pp
            wire [WP-1:0] full = r[j] ? ({{29{1'b0}}, xm} << j) : {WP{1'b0}};
            assign prow[j*WP +: WP] = {full[WP-1:DROP], {DROP{1'b0}}};
        end
    endgenerate
    wire [WP-1:0] ps, pc;
    ot_hdc_sk_csa #(.N(29), .W(WP)) u_xr (.rows(prow), .s(ps), .c(pc));
    wire [24:0] cmp_s0, cmp_s1;
    ot_hdc_sk_cadd #(.W(24)) u_cmp (.a(xm), .b(~tm), .s0(cmp_s0), .s1(cmp_s1));
    wire lt = !cmp_s1[24];
    wire signed [10:0] e0 = $signed({xe[9], xe}) - $signed({te[9], te});
    wire signed [10:0] E  = lt ? (e0 - 11'sd1) : e0;
    reg [WP-1:0] ps_q, pc_q; reg lt_q; reg signed [10:0] E_q;
    always @(posedge clk) begin ps_q <= ps; pc_q <= pc; lt_q <= lt; E_q <= E; end
    // ---- Q2: CPA, M', grid shift for a subnormal result (step 0 only)
    wire [WP:0] pr0, pr1;
    ot_hdc_sk_cadd #(.W(WP)) u_xrc (.a(ps_q), .b(pc_q), .s0(pr0), .s1(pr1));
    wire [23:0] mp = lt_q ? pr0[50:27] : pr0[51:28];
    wire [24:0] xp = lt_q ? {xm, 1'b0} : {1'b0, xm};
    wire signed [10:0] sfull = -11'sd126 - E_q;
    wire zero_s = subn && (sfull > 11'sd24);
    wire [4:0] s = (!subn || sfull <= 11'sd0 || sfull > 11'sd24) ? 5'd0 : sfull[4:0];
    reg [23:0] ms_q; reg [26:0] xs_q; reg [4:0] s_q; reg zs_q;
    always @(posedge clk) begin
        ms_q <= mp >> s;
        xs_q <= {2'b00, xp} << (5'd24 - s);
        s_q <= s; zs_q <= zero_s;
    end
    // ---- Q3: r1 = xs - T - sum_j T_j (ms << (j+1))  (mod 2^27) carry-save
    localparam integer W = 27;
    localparam integer NR = 24 + 3;
    wire [NR*W-1:0] rows;
    generate
        for (j = 0; j < 24; j = j + 1) begin : g_rr
            wire [W-1:0] v = tm[j] ? ({3'b000, ms_q} << (j + 1)) : {W{1'b0}};
            assign rows[j*W +: W] = ~v;
        end
    endgenerate
    assign rows[24*W +: W] = xs_q;
    assign rows[25*W +: W] = ~{3'b000, tm};
    assign rows[26*W +: W] = 27'd25;
    wire [W-1:0] ts, tc;
    ot_hdc_sk_csa #(.N(NR), .W(W)) u_tree (.rows(rows), .s(ts), .c(tc));
    reg [W-1:0] ts_q, tc_q;
    always @(posedge clk) begin ts_q <= ts; tc_q <= tc; end
    // the final reads ms_q / s_q / zs_q / E_q directly: they hold this step's value from Q2 until the next step's Q2
    wire [23:0] m3_q = ms_q; wire [4:0] s3_q = s_q; wire z3_q = zs_q; wire signed [10:0] E3_q = E_q;
    // ---- final (combinational): remainder signs, M' + {0, 1, 2}, pack
    wire [W-1:0] t2 = ~{2'b00, tm, 1'b0};
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
    wire inc1 = (!neg1 & !z1) | (z1 & m3_q[0]);
    wire inc2 = (!neg2 & !z2) | (z2 & !m3_q[0]);
    generate if (Q4) begin : g_q4
        // Q4 captures correction and exact signed-11-bit range predicates.
        // ms_q/s_q/E_q remain this transaction's operands until next Q2;
        // D0 and DS below delay the recurrence by exactly one edge.
        wire signed [10:0] eb = E3_q + 11'sd127;
        wire signed [10:0] eb1 = E3_q + 11'sd128;
        wire sub = s3_q != 5'd0;
        wire hi0 = !sub && (eb > 11'sd254);
        wire hi1 = !sub && (eb1 > 11'sd254);
        wire low = !subn && (eb < 11'sd1);
        wire zero = xz | z3_q;
        wire [2:0] pack_q;
        wire [5:0] range_q;
        // Both copies do useful work. Packing needs only three predicates;
        // do not manufacture consumers for unused high/low predicate copies.
        (* keep = 1 *) ot_hdc_skp_q4_pack3 u_pack (.clk(clk), .d({inc1,inc2,zero}), .q(pack_q));
        (* keep = 1 *) ot_hdc_skp_q4_range6 u_range (.clk(clk),
            .d({inc1,inc2,hi0,hi1,low ^ (MUT_Q4 != 0),zero}), .q(range_q));
        wire [24:0] m1_s0, m1_s1;
        ot_hdc_sk_cadd #(.W(24)) u_inc (.a(m3_q), .b(24'd0), .s0(m1_s0), .s1(m1_s1));
        wire [23:0] m2_s0, m2_s1;
        ot_hdc_sk_cadd #(.W(23)) u_inc2 (.a(m3_q[23:1]), .b(23'd0), .s0(m2_s0), .s1(m2_s1));
        wire [24:0] mf = pack_q[1] ? {m2_s1,m3_q[0]} : (pack_q[2] ? m1_s1 : {1'b0,m3_q});
        wire ovm = mf[24];
        wire [7:0] field = sub ? {7'd0,mf[23]} : (ovm ? eb1[7:0] : eb[7:0]);
        wire range_ovm = range_q[4] ? (&m3_q[23:1]) : (range_q[5] && (&m3_q[23:0]));
        assign y = pack_q[0] ? 31'd0 : {field,ovm ? 23'd0 : mf[22:0]};
        assign range = !range_q[0] && ((range_ovm ? range_q[2] : range_q[3]) || range_q[1]);
    end else begin : g_legacy_final
    wire [24:0] m1_s0, m1_s1;
    ot_hdc_sk_cadd #(.W(24)) u_inc (.a(m3_q), .b(24'd0), .s0(m1_s0), .s1(m1_s1));
    wire [23:0] m2_s0, m2_s1;
    ot_hdc_sk_cadd #(.W(23)) u_inc2 (.a(m3_q[23:1]), .b(23'd0), .s0(m2_s0), .s1(m2_s1));
    wire [24:0] mf = inc2 ? {m2_s1, m3_q[0]} : (inc1 ? m1_s1 : {1'b0, m3_q});
    wire ovm = mf[24];
    wire signed [10:0] eb = E3_q + 11'sd127;
    wire signed [10:0] eb1 = E3_q + 11'sd128;
    wire sub = s3_q != 5'd0;                               // s = 0 whenever subn = 0
    wire [7:0] field = sub ? {7'd0, mf[23]} : (ovm ? eb1[7:0] : eb[7:0]);
    wire bad_hi = !sub && (ovm ? (eb1 > 11'sd254) : (eb > 11'sd254));
    wire bad_lo = !subn && (eb < 11'sd1);
    wire zero = xz | z3_q;
    assign y = zero ? 31'd0 : {field, ovm ? 23'd0 : mf[22:0]};
    assign range = !zero & (bad_hi | bad_lo);
    end endgenerate
endmodule

module ot_hdc_sinkhorn_p #(
    parameter integer ITERS = 20,
    parameter [31:0]  EPS = 32'h358637BD,
    parameter integer CONTROL_SAFE = 0,
    parameter integer Q4 = 0,
    parameter integer MUT_Q4 = 0,
    parameter integer MUT = 0                  // bench only: 1 = a steady step lands one stage early
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_valid,
    output wire         in_ready,
    input  wire [511:0] in_e,                  // element (r, c) at [32 (4r + c) +: 32]
    output reg          out_valid,
    output wire [511:0] y,
    output reg          fault,
    output wire         busy
);
    localparam integer STEPS = 2 * ITERS - 1;
    localparam integer D0 = 17 + (Q4 != 0), DS = 15 + (Q4 != 0);
    localparam integer LAT = D0 + STEPS * DS;
    localparam [1:0] P_IDLE = 2'd0, P_Z = 2'd1, P_RUN = 2'd2;
    localparam [7:0]  EPS_E = (EPS[30:23] == 8'd0) ? 8'd1 : EPS[30:23];
    localparam [23:0] EPS_M = {EPS[30:23] != 8'd0, EPS[22:0]};

    reg [1:0] ph; reg [4:0] c; reg [7:0] cnt; reg flt;
    reg [31:0] st [0:15];
    assign in_ready = (ph == P_IDLE);
    assign busy = (ph != P_IDLE);
    wire acc = in_ready && in_valid;
    // mode: 1 from the accept edge until step 0 lands (kept copy per element, <= ~40 loads each)
    wire zset = acc, zclr = (ph == P_Z) && (c == 5'(D0 - 1));
    wire [15:0] zm;
    genvar r, k;
    generate for (k = 0; k < 16; k = k + 1) begin : g_zm
        (* keep = "true" *) reg q;
        always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else if (zset) q <= 1'b1; else if (zclr) q <= 1'b0;
        assign zm[k] = q;
    end endgenerate

    // ---- S1 (side): per-element X operand = the normalised state word, input checks (stable for the step)
    reg [23:0] x_m [0:15]; reg signed [9:0] x_e [0:15]; reg x_z [0:15];
    reg sub_any, bin_any;
    wire [15:0] w_sub, w_bad;
    wire [23:0] nx_m [0:15]; wire signed [9:0] nx_e [0:15]; wire nx_z [0:15];
    generate for (k = 0; k < 16; k = k + 1) begin : g_x
        wire [31:0] w = st[k];
        assign w_sub[k] = (w[30:23] == 8'd0);
        assign w_bad[k] = (w[31] && (w[30:0] != 31'd0)) || (w[30:23] == 8'hFF);
        ot_hdc_sk_norm u_nx (.x(w[30:0]), .m(nx_m[k]), .e(nx_e[k]), .z(nx_z[k]));
        always @(posedge clk) begin x_m[k] <= nx_m[k]; x_e[k] <= nx_e[k]; x_z[k] <= nx_z[k]; end
    end endgenerate
    always @(posedge clk) begin sub_any <= |w_sub; bin_any <= |w_bad; end

    // ---- per row: S1..S6 adds, S7..S8 T, seed, 4 quotients
    wire [30:0] q [0:15];
    wire [15:0] q_rng;
    wire [3:0]  bad4;
    generate for (r = 0; r < 4; r = r + 1) begin : g_row
        wire [7:0]  ee [0:3];
        wire [23:0] mm [0:3];
        for (k = 0; k < 4; k = k + 1) begin : g_dec
            wire [31:0] w = st[4*r + k];
            assign ee[k] = (w[30:23] == 8'd0) ? 8'd1 : w[30:23];
            assign mm[k] = {w[30:23] != 8'd0, w[22:0]};
        end
        // S1
        wire [7:0] g1, e1; wire u1, o1; wire [23:0] m1;
        ot_hdc_skp_add u_s1 (.clk(clk), .ea(ee[0]), .ua(1'b0), .ma(mm[0]), .eb(ee[1]), .mb(mm[1]),
                            .eg(g1), .up(u1), .e(e1), .m(m1), .ovf(o1));
        reg [7:0] e1_q; reg [23:0] m1_q; reg b1_q;
        always @(posedge clk) begin e1_q <= e1; m1_q <= m1; b1_q <= o1; end
        // S2
        wire [7:0] g2, e2; wire u2, o2; wire [23:0] m2;
        ot_hdc_skp_add u_s2 (.clk(clk), .ea(e1_q), .ua(1'b0), .ma(m1_q), .eb(ee[2]), .mb(mm[2]),
                            .eg(g2), .up(u2), .e(e2), .m(m2), .ovf(o2));
        reg [7:0] e2_q; reg [23:0] m2_q; reg b2_q;
        always @(posedge clk) begin e2_q <= e2; m2_q <= m2; b2_q <= b1_q | o2; end
        // S3
        wire [7:0] g3, e3; wire u3, o3; wire [23:0] m3;
        ot_hdc_skp_add u_s3 (.clk(clk), .ea(e2_q), .ua(1'b0), .ma(m2_q), .eb(ee[3]), .mb(mm[3]),
                            .eg(g3), .up(u3), .e(e3), .m(m3), .ovf(o3));
        reg [7:0] e3_q; reg [23:0] m3_q; reg b3_q;
        always @(posedge clk) begin e3_q <= e3; m3_q <= m3; b3_q <= b2_q | o3; end
        // S4: steady T = sum + eps (normal); step 0 T = normalised sum
        wire [7:0] gt, et; wire ut, ot_; wire [23:0] mt;
        ot_hdc_skp_add u_ae (.clk(clk), .ea(e3_q), .ua(1'b0), .ma(m3_q), .eb(EPS_E), .mb(EPS_M),
                            .eg(gt), .up(ut), .e(et), .m(mt), .ovf(ot_));
        wire signed [9:0] te_s = $signed({2'b00, et}) - 10'sd127;
        wire [30:0] zsum = {m3_q[23] ? e3_q : 8'd0, m3_q[22:0]};
        wire [23:0] nt_m; wire signed [9:0] nt_e; wire tz;
        reg [23:0] nt_m_q; reg signed [9:0] nt_e_q; reg tz_q;
        always @(posedge clk) begin nt_m_q <= nt_m; nt_e_q <= nt_e; tz_q <= tz; end
        ot_hdc_sk_norm u_nt (.x(zsum), .m(nt_m), .e(nt_e), .z(tz));
        reg b4_q;
        always @(posedge clk) b4_q <= b3_q | (zm[4*r] ? tz_q : (ot_ | !mt[23]));
        assign bad4[r] = b4_q;
        wire [23:0] tm_d = zm[4*r] ? nt_m_q : mt;
        wire [82:0] decoded;
        if (CONTROL_SAFE) begin : g_safe_decode
            wire [8:0] ix = tm_d[22:14];
            wire [8:0] sx = tm_d[13] ? tm_d[12:4] : ~tm_d[12:4];
            wire [23:0] pd, sd;
            for (genvar pg = 0; pg < 3; pg = pg + 1) begin : g_group
                for (genvar pv = 0; pv < 8; pv = pv + 1) begin : g_value
                    assign pd[pg*8+pv] = ix[pg*3 +: 3] == pv;
                    assign sd[pg*8+pv] = sx[pg*3 +: 3] == pv;
                end
            end
            (* keep = 1 *) ot_hdc_skp_decode_c0lo u_c0l (.clk(clk), .d(pd), .q(decoded[16:0]));
            (* keep = 1 *) ot_hdc_skp_decode_c0hi u_c0h (.clk(clk), .d(pd), .q(decoded[32:17]));
            (* keep = 1 *) ot_hdc_skp_decode_c1 u_c1 (.clk(clk), .d(pd), .q(decoded[55:33]));
            (* keep = 1 *) ot_hdc_skp_decode_c2 u_c2 (.clk(clk), .d(pd), .q(decoded[68:56]));
            (* keep = 1 *) ot_hdc_skp_decode_sq u_sq (.clk(clk), .d(sd), .q(decoded[82:69]));
        end else assign decoded = 83'd0;
        wire [23:0] tmc [0:3]; wire signed [9:0] tec [0:3];
        for (k = 0; k < 4; k = k + 1) begin : g_t               // T copies: one per quotient (seed reads copy 0)
            if (CONTROL_SAFE) begin : g_kept
                (* keep = 1 *) ot_hdc_skp_denominator34 u_t (.clk(clk),
                    .d({zm[4*r+k] ? nt_e_q : te_s, zm[4*r+k] ? nt_m_q : mt}), .q({tec[k],tmc[k]}));
            end else begin : g_legacy
                (* keep = "true" *) reg [23:0] tm_q;
                (* keep = "true" *) reg [9:0] te_q;
                always @(posedge clk) begin
                    tm_q <= zm[4*r + k] ? nt_m_q : mt;
                    te_q <= zm[4*r + k] ? nt_e_q : te_s;
                end
                assign tmc[k] = tm_q; assign tec[k] = te_q;
            end
        end
        // S9..S11 seed
        wire [29*4-1:0] rs;
        ot_hdc_skp_seed #(.NC(4), .CONTROL_SAFE(CONTROL_SAFE)) u_seed (.clk(clk), .tm(tmc[0]), .decoded(decoded), .r(rs));
        // Q1..Q3 + final; element (r, k) -> storage 4k + r (transposed)
        for (k = 0; k < 4; k = k + 1) begin : g_q
            ot_hdc_skp_quot #(.Q4(Q4), .MUT_Q4(MUT_Q4)) u_q (.clk(clk), .subn(zm[4*r + k]), .xm(x_m[4*r + k]), .xe(x_e[4*r + k]),
                                 .xz(x_z[4*r + k] & zm[4*r + k]), .tm(tmc[k]), .te(tec[k]), .r(rs[29*k +: 29]),
                                 .y(q[4*k + r]), .range(q_rng[4*k + r]));
        end
    end endgenerate

    // ---- step 0 final: register the quotient, + eps -> state
    reg [30:0] zq [0:15]; reg [15:0] zr;
    wire [31:0] z_out [0:15]; wire [15:0] z_ov;
    generate for (k = 0; k < 16; k = k + 1) begin : g_z
        always @(posedge clk) begin zq[k] <= q[k]; zr[k] <= q_rng[k]; end
        wire [7:0]  qe = (zq[k][30:23] == 8'd0) ? 8'd1 : zq[k][30:23];
        wire [23:0] qm = {zq[k][30:23] != 8'd0, zq[k][22:0]};
        wire [7:0]  oe, og; wire [23:0] om; wire ou;
        ot_hdc_skp_add u_eps (.clk(clk), .ea(qe), .ua(1'b0), .ma(qm), .eb(EPS_E), .mb(EPS_M),
                             .eg(og), .up(ou), .e(oe), .m(om), .ovf(z_ov[k]));
        assign z_out[k] = {1'b0, om[23] ? oe : 8'd0, om[22:0]};
    end endgenerate
    wire zbad = bin_any | (|bad4) | (|zr) | (|z_ov);
    wire sbad = sub_any | (|bad4) | (|q_rng);
    wire zcap = (ph == P_Z) && (c == 5'(D0 - 1));
    wire scap = (ph == P_RUN) && (c == 5'(DS - 1 - MUT));

    // ---- control (fixed schedule)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph <= P_IDLE; c <= 5'd0; cnt <= 8'd0; flt <= 1'b0; out_valid <= 1'b0; fault <= 1'b0;
        end else begin
            out_valid <= 1'b0;
            case (ph)
                P_IDLE: if (in_valid) begin ph <= P_Z; c <= 5'd0; flt <= 1'b0; end
                P_Z: begin
                    c <= c + 5'd1;
                    if (zcap) begin
                        c <= 5'd0; cnt <= STEPS[7:0]; flt <= flt | zbad;
                        if (STEPS == 0) begin ph <= P_IDLE; out_valid <= 1'b1; fault <= flt | zbad; end
                        else ph <= P_RUN;
                    end
                end
                default: begin
                    c <= c + 5'd1;
                    if (scap) begin
                        c <= 5'd0; cnt <= cnt - 8'd1; flt <= flt | sbad;
                        if (cnt == 8'd1) begin ph <= P_IDLE; out_valid <= 1'b1; fault <= flt | sbad; end
                    end
                end
            endcase
        end
    end
    integer i;
    always @(posedge clk)
        for (i = 0; i < 16; i = i + 1) begin
            if (acc) st[i] <= in_e[32*i +: 32];
            else if (zcap) st[i] <= z_out[i];
            else if (scap) st[i] <= {1'b0, q[i]};
        end
    generate for (k = 0; k < 16; k = k + 1) begin : g_y
        assign y[32*k +: 32] = fault ? 32'd0 : st[k];
    end endgenerate
`ifndef SYNTHESIS
    initial if (D0 > 31 || DS > 31) $error("ot_hdc_sinkhorn_p: stage counter is 5 bits");
`endif
endmodule
(* keep_hierarchy = 1 *) module ot_hdc_skp_denominator34(input wire clk, input wire [33:0] d, output reg [33:0] q);
    always @(posedge clk) q <= d;
endmodule
// Fixed distinct useful consumer modules survive hierarchy-preserving mapping.
// Source has 16*(3+6)=144 predicate FF, below the 192-FF model reserve.
(* keep_hierarchy = 1 *) module ot_hdc_skp_q4_pack3(input wire clk, input wire [2:0] d, output reg [2:0] q);
    always @(posedge clk) q <= d;
endmodule
(* keep_hierarchy = 1 *) module ot_hdc_skp_q4_range6(input wire clk, input wire [5:0] d, output reg [5:0] q);
    always @(posedge clk) q <= d;
endmodule
`default_nettype wire
