`timescale 1ns/1ps
// el1011-q-kvd-head 2026-10-11: the two HARDENED SUB-TILES of the hierarchical head ot_qwen_nearhbm_head_hs
// (rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv has the structure notes).  The head routes them as macros
// (blackbox view rtl/hdc/nearhbm/ot_qkh_subtiles_bb.v).

// ---------------------------------------------------------------------------------------------------------------------
// ot_qkh_lane8: lanes 8t .. 8t + 7 of a head (hardened sub-tile; every instance identical, the beat column is a strap)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkh_lane8 #(
    parameter integer ADD_LAT = 7,
    parameter integer LTW = 12,
    // KV-CORES 10-25 (COORD ruling 5): LT_COPY = 1 duplicates the LAST flop of the decision-word delay line u_ltd per lane
    // (g_d[d].g_ltc.u_ltl, bits [8:0] = the lane's P.V tree controls) plus one shared copy of the node-slice bits [LTW-1:9]
    // (g_ltn.u_ltn): the 8-lane x 32-bit broadcast of lal / lsel (head_eighth e6 TT -12 ps from u_ltd line[39]) becomes
    // eight short lane nets.  Same D (PLAT) edges, 0 added cycles (u_ltd is one stage shorter).  LT_COPY = 0 (default) is
    // the unchanged RTL (u_ltd D = PLAT drives every lane).
    parameter integer LT_COPY = 0,
    // PATH-KV-HEAD 10-25 (head6ff TT -71.6: u_l8 g3g / e3 S3 pin flops broadcast to 8 lanes x (16-bit a mux + valid) through
    // a 3-level BUFx2 fanout tree, ~240 ps): S3_COPY = 1 gives every lane its own S3 pin-flop copy of {c_in[3:2], c_in[0],
    // e_in, q_valid_in, q_beat_in, hid, bsel} (31 FF / lane, same D as the shared S3 flops, same edges, 0 added cycles) and
    // its own q0/q1 16-bit slice write enables, so each copy drives one lane (~17-34 loads).  The shared c3[3:1] still feeds
    // u_ctl.  S3_COPY = 0 (default) is the unchanged RTL (odd heads e1/e3/e5/e7 signed).
    parameter integer S3_COPY = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      c_in,          // {k issue, v issue of a real row, first round, g}
    input  wire [63:0]     row_in,        // row bytes of lanes 8t .. 8t + 7
    input  wire [15:0]     e_in,
    input  wire [LTW-1:0]  lt_in,
    input  wire [1:0]      hid,           // head strap (0..3)
    input  wire [1:0]      bsel,          // beat column strap: t / 4 (lanes 8t .. are bits 128 (t % 4) .. of beat t / 4)
    input  wire            q_valid_in,
    input  wire [5:0]      q_beat_in,
    input  wire [127:0]    q_data_in,     // bits 128 (t % 4) .. + 127 of the q beat
    output reg  [31:0]     kp,            // the level-3 K node of products 8t .. 8t + 7
    output reg             kpv,
    output reg  [63:0]     nb,            // node-slice words 2t, 2t + 1
    output reg             gf             // lane / bank faults, ORed
);
    localparam integer PLAT = 4;
    // ---- reset relay: the port drives only the relay; control flops reset from its outputs ---------------------------
    // idle1012 textbook class 2: one reset copy per lane (the shared lane copy drove 952 flops) + one for the tile control
    wire [8:0] rr;
    ot_rst_relay #(.REGIONS(9), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rc = rr[8];          // tile control / pins
    // ---- S3: the pin flops ---------------------------------------------------------------------------------------------
    reg  [3:0]      c3;
    reg  [63:0]     row3;
    reg  [15:0]     e3;
    reg  [LTW-1:0]  lt3;
    reg             qv3;
    reg  [5:0]      qb3;
    reg  [127:0]    qd3;
    reg  [1:0]      hid3, bs3;
    always @(posedge clk or negedge rc)
        if (!rc) begin c3[3:1] <= 3'd0; lt3 <= {LTW{1'b0}}; qv3 <= 1'b0; end
        else begin c3[3:1] <= c_in[3:1]; lt3 <= lt_in; qv3 <= q_valid_in; end
    always @(posedge clk) begin
        c3[0] <= c_in[0]; row3 <= row_in; e3 <= e_in; qb3 <= q_beat_in; qd3 <= q_data_in; hid3 <= hid; bs3 <= bsel;
    end
    // q rows of heads hid (q0) and 4 + hid (q1): beat 4 hid + t / 4, resp. 4 (4 + hid) + t / 4 (HD 128: 4 beats a row)
    reg  [127:0] q0, q1;
    wire w0 = qv3 && (qb3 == {2'b00, hid3, bs3});
    wire w1 = qv3 && (qb3 == {2'b01, hid3, bs3});
    always @(posedge clk) begin
        if (w0) q0 <= qd3;
        if (w1) q1 <= qd3;
    end
    // ---- the control delay lines (one copy for 8 lanes) ----------------------------------------------------------------
    wire [2:0]     kvz_d;
    wire [LTW-1:0] lt_d;
    wire [3:0]     kl;                    // kt of levels 1, 2, 3; kl[3] = the level-3 result's valid
    ot_hdc_delay #(.W(3), .D(PLAT), .RESET(1)) u_ctl (.clk(clk), .rst_n(rc), .d(c3[3:1]), .q(kvz_d));
`ifdef KVD_HMUT
    ot_hdc_delay #(.W(LTW), .D(PLAT + 1 - (LT_COPY != 0)), .RESET(1)) u_ltd (.clk(clk), .rst_n(rc), .d(lt3), .q(lt_d));
`else
    ot_hdc_delay #(.W(LTW), .D(PLAT - (LT_COPY != 0)), .RESET(1)) u_ltd (.clk(clk), .rst_n(rc), .d(lt3), .q(lt_d));
`endif
    assign kl[0] = kvz_d[2];
    genvar l, d;
    generate for (l = 1; l <= 3; l = l + 1) begin : g_kl
        ot_hdc_delay #(.W(1), .D(ADD_LAT), .RESET(1)) u_kl (.clk(clk), .rst_n(rc), .d(kl[l-1]), .q(kl[l]));
    end endgenerate
    wire        g3k = c3[3], g3v = c3[2], g3g = c3[0];
    wire        kd = kvz_d[2], vd = kvz_d[1], czd = kvz_d[0];
    // ---- the lanes -------------------------------------------------------------------------------------------------------
    wire [8*32-1:0] p_y, l_y, fb, obw;
    wire [7:0]      p_vo, p_f, l_vo, l_f, b_f;
    wire [LTW-1:9]  dn;                   // node-slice select of the decision word at PLAT
    generate if (LT_COPY == 0) begin : g_ltn0
        assign dn = lt_d[LTW-1:9];
    end else begin : g_ltn
        ot_hdc_delay #(.W(LTW - 9), .D(1), .RESET(1)) u_ltn (.clk(clk), .rst_n(rc), .d(lt_d[LTW-1:9]), .q(dn));
    end endgenerate
    generate for (d = 0; d < 8; d = d + 1) begin : g_d
        wire rl = rr[d];      // this lane's reset copy
        // tree role: 0 2 4 6 level 1 (own pair); 1: level 2 (0, 2); 5: level 2 (4, 6); 3: level 3 (1, 5); 7: none
        localparam integer TL = (d % 2 == 0) ? 1 : ((d == 1 || d == 5) ? 2 : ((d == 3) ? 3 : 0));
        localparam integer LA = (d == 3) ? 1 : d - 1;
        localparam integer LB = (d == 3) ? 5 : d + 1;
        wire        lk, lv, lg;           // this lane's view of the S3 controls
        wire [15:0] le, lq0, lq1;
        if (S3_COPY == 0) begin : g_s3s
            assign lk = g3k; assign lv = g3v; assign lg = g3g; assign le = e3;
            assign lq0 = q0[d * 16 +: 16]; assign lq1 = q1[d * 16 +: 16];
        end else begin : g_s3c       // this lane's own S3 pin-flop copy (S3_COPY)
            reg        ck3, cv3, qvl, cg3;
            reg [15:0] el3, ql0, ql1;
            reg [5:0]  qbl;
            reg [1:0]  hdl, bsl;
            always @(posedge clk or negedge rc)
                if (!rc) begin ck3 <= 1'b0; cv3 <= 1'b0; qvl <= 1'b0; end
                else begin ck3 <= c_in[3]; cv3 <= c_in[2]; qvl <= q_valid_in; end
            always @(posedge clk) begin
                cg3 <= c_in[0]; el3 <= e_in; qbl <= q_beat_in; hdl <= hid; bsl <= bsel;
            end
            wire lw0 = qvl && (qbl == {2'b00, hdl, bsl});
            wire lw1 = qvl && (qbl == {2'b01, hdl, bsl});
            always @(posedge clk) begin
                if (lw0) ql0 <= qd3[d * 16 +: 16];
                if (lw1) ql1 <= qd3[d * 16 +: 16];
            end
            assign lk = ck3; assign lv = cv3; assign lg = cg3; assign le = el3; assign lq0 = ql0; assign lq1 = ql1;
        end
        wire [15:0] qv = lg ? lq1 : lq0;
        (* keep_hierarchy *) ot_qwen_nearhbm_prod u_p (.clk(clk), .rst_n(rl), .valid_in(lk || lv),
            .a(lk ? qv : le), .k(row3[8*d +: 8]), .y(p_y[32*d +: 32]), .fault(p_f[d]), .valid_out(p_vo[d]));
        wire [31:0] va = czd ? 32'd0 : fb[32*d +: 32];
        wire [31:0] vb = vd ? p_y[32*d +: 32] : 32'd0;
        wire [31:0] la, lb;
        wire        kt;
        if (TL == 1) begin : g_l1
            assign kt = kd;
            assign la = kt ? p_y[32*d +: 32] : va;
            assign lb = kt ? p_y[32*(d+1) +: 32] : vb;
        end else if (TL >= 2) begin : g_ln
            assign kt = kl[TL - 1];
            assign la = kt ? l_y[32*LA +: 32] : va;
            assign lb = kt ? l_y[32*LB +: 32] : vb;
        end else begin : g_free
            assign kt = 1'b0;
            assign la = va;
            assign lb = vb;
        end
        wire [1:0] err;
        (* keep_hierarchy *) ot_hdc_fp32_add_lat_nr #(.LAT(ADD_LAT)) u_a (.clk(clk), .rst_n(rl), .valid_in(kt || vd),
            .a(la), .b(lb), .y(l_y[32*d +: 32]), .err(err), .valid_out(l_vo[d]));
        assign l_f[d] = l_vo[d] && (err != 2'd0);
        ot_hdc_delay #(.W(32), .D(8 - ADD_LAT)) u_pad (.clk(clk), .rst_n(rl), .d(l_y[32*d +: 32]), .q(fb[32*d +: 32]));
        // the local P.V tree (levels 1-3) of this lane, executing the decision word delayed PLAT
        wire [8:0]  dw;
        if (LT_COPY == 0) begin : g_lt0
            assign dw = lt_d[8:0];
        end else begin : g_ltc   // this lane's own copy of the last decision-word flop (LT_COPY)
            ot_hdc_delay #(.W(9), .D(1), .RESET(1)) u_ltl (.clk(clk), .rst_n(rl), .d(lt_d[8:0]), .q(dw));
        end
        wire        lis = dw[0], lsel = dw[1], lst0 = dw[4], lsty = dw[5], lob = dw[8];
        wire [1:0]  lal = dw[3:2], lsl = dw[7:6];
        reg  [31:0] lp0, lp1, lp2, obr;
        wire [31:0] ly;
        wire [31:0] lpa = (lal == 2'd0) ? lp0 : ((lal == 2'd1) ? lp1 : lp2);
        wire [1:0]  berr;
        wire        bvo;
        (* keep_hierarchy *) ot_hdc_fp32_add_lat_nr #(.LAT(ADD_LAT)) u_b (.clk(clk), .rst_n(rl), .valid_in(lis),
            .a(lpa), .b(lsel ? ly : fb[32*d +: 32]), .y(ly), .err(berr), .valid_out(bvo));
        assign b_f[d] = bvo && (berr != 2'd0);
        always @(posedge clk) begin
            if (lst0) lp0 <= fb[32*d +: 32];
            if (lsty && lsl == 2'd0) lp0 <= ly;
            if (lsty && lsl == 2'd1) lp1 <= ly;
            if (lsty && lsl == 2'd2) lp2 <= ly;
            if (lob) obr <= ly;
        end
        assign obw[32*d +: 32] = obr;
    end endgenerate
    // ---- registered outputs ----------------------------------------------------------------------------------------------
    // node slice (LFB 4): word k of this tile = lane 4k + beat
    always @(posedge clk) if (dn[9]) begin
        nb[31:0]  <= obw[32*(0 + dn[11:10]) +: 32];
        nb[63:32] <= obw[32*(4 + dn[11:10]) +: 32];
    end
    wire k3v;
    ot_hdc_delay #(.W(1), .D(ADD_LAT), .RESET(1)) u_k3v (.clk(clk), .rst_n(rc), .d(kl[2]), .q(k3v));
    always @(posedge clk) kp <= l_y[32*3 +: 32];
    always @(posedge clk or negedge rc)
        if (!rc) begin kpv <= 1'b0; gf <= 1'b0; end
        else begin kpv <= k3v; gf <= (|(p_f & p_vo)) || (|l_f) || (|b_f); end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qkh_ktree: K levels 4-7 of a head (16 level-3 partials, original pairing) + scale + fault OR (hardened sub-tile)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkh_ktree #(
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter [31:0]  SCALE = 32'h3DB504F3
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  kp_in,
    input  wire          kpv_in,
    input  wire [15:0]   gf_in,
    output reg  [31:0]   sc_d,
    output reg           sc_f,
    output reg           g_f,
    // KVG3-CORES 10-24: the kpv_in face register (kv_r) for a parent that compares other lanes against the REGISTERED
    // lane 0 (ot_qkh_ktree_lk PORT_REGS=1); unconnected elsewhere (no logic, timing or cycle change)
    output wire          kv_q
);
    // idle1012 textbook class 2: one reset copy per K-tree adder + one for the scale multiply / control (one copy drove 1,004)
    wire [16:0] rr;
    ot_rst_relay #(.REGIONS(17), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rc = rr[16];
    reg  [511:0] kp_r;
    reg          kv_r;
    reg  [15:0]  gf_r;
    always @(posedge clk) kp_r <= kp_in;
    always @(posedge clk or negedge rc)
        if (!rc) begin kv_r <= 1'b0; gf_r <= 16'd0; end
        else begin kv_r <= kpv_in; gf_r <= gf_in; end
    assign kv_q = kv_r;
    // node storage: level 4 nodes 0..7 at n[0..7], level 5 at n[8..11], level 6 at n[12..13], level 7 (root) at n[14]
    wire [15*32-1:0] n;
    wire [14:0]      nvo, nf;
`ifdef KVD_HSMUT
    // bench mutant (must FAIL): the level-4 adders see the partials one edge late (a seam without its valid)
    reg  [511:0] kp_m;
    always @(posedge clk) kp_m <= kp_r;
    wire [511:0] lv3 = kp_m;
`else
    wire [511:0] lv3 = kp_r;
`endif
    genvar i;
    generate for (i = 0; i < 15; i = i + 1) begin : g_n
        localparam integer LEV = (i < 8) ? 4 : ((i < 12) ? 5 : ((i < 14) ? 6 : 7));
        localparam integer IX  = (i < 8) ? i : ((i < 12) ? i - 8 : ((i < 14) ? i - 12 : 0));
        localparam integer CB  = (LEV == 5) ? 0 : ((LEV == 6) ? 8 : 12);     // first child node of the level below
        wire [31:0] a, b;
        wire        vin;
        if (LEV == 4) begin : g_l4
            assign a = lv3[32*(2*IX) +: 32];
            assign b = lv3[32*(2*IX + 1) +: 32];
            assign vin = kv_r;
        end else begin : g_lh
            assign a = n[32*(CB + 2*IX) +: 32];
            assign b = n[32*(CB + 2*IX + 1) +: 32];
            assign vin = nvo[CB + 2*IX];
        end
        wire [1:0] err;
        (* keep_hierarchy *) ot_hdc_fp32_add_lat_nr #(.LAT(ADD_LAT)) u_a (.clk(clk), .rst_n(rr[i]), .valid_in(vin),
            .a(a), .b(b), .y(n[32*i +: 32]), .err(err), .valid_out(nvo[i]));
        assign nf[i] = nvo[i] && (err != 2'd0);
    end endgenerate
    wire [31:0] scd0;
    wire [1:0]  merr;
    wire        sv;
    (* keep_hierarchy *) ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_scale (
        .clk(clk), .rst_n(rr[15]), .valid_in(nvo[14]), .a(n[32*14 +: 32]), .b(SCALE), .y(scd0), .err(merr), .valid_out(sv));
    reg kf;
    always @(posedge clk) sc_d <= scd0;
    always @(posedge clk or negedge rc)
        if (!rc) begin sc_f <= 1'b0; g_f <= 1'b0; kf <= 1'b0; end
        else begin sc_f <= sv && (merr != 2'd0); kf <= |nf; g_f <= (|gf_r) || kf; end
endmodule

