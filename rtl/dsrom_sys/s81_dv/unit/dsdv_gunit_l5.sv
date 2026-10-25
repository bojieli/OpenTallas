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
`ifndef OT_S81_GUNIT_PIN_COPY
`define OT_S81_GUNIT_PIN_COPY 0
`endif
`ifndef OT_S81_GUNIT_CONTROL_SAFE
`define OT_S81_GUNIT_CONTROL_SAFE 0
`endif
`ifndef OT_S81_GUNIT_Q4
`define OT_S81_GUNIT_Q4 0
`endif
`ifndef OT_S81_GUNIT_FANOUT_SAFE
`define OT_S81_GUNIT_FANOUT_SAFE 0
`endif
`ifndef OT_S81_GUNIT_NAT32
`define OT_S81_GUNIT_NAT32 0
`endif
// S81-GUNIT whole model (10-19, FANOUT_SAFE, default 0 = legacy): (1) the 3,072-bit base table lives in 12 native
// ot_sram_1r1w2c_32x64_m1 banks (rows {set, which}, bank b = base words 2b, 2b + 1); each bank reads continuously
// (r_ce 1) at its own kept copy of the rank-2 job select, so its registered rd_out is the old `bases` capture register
// at the same edge (select a, rank1 a + 1, rank2 a + 2, rd_out a + 3): 0 edges.  COMPILER CONTRACT: the selected
// {set, which} word is never written between job select and launch and config settles before the first qualified read;
// a write to the selected word in the 4 edges before the tail takes the bases is a sticky fault (same-edge 1R1W ordering
// is never relied on).  Scales (384 b) stay flops, written by kept one-hot enables predicted from the cw pins (same
// edge as wv / wa).  (2) Reset: ot_rst_region16 -- the raw port drives 2 sync flops, 16 kept region roots release at
// edge 3 (as ot_rst_relay), <= 24 async-clear pins a root; the tail gets 1 + 8 roots (rst_n, rst_v).  (3) ln, c_on and
// the CTL row select, and the mix write decode are kept same-edge copies (no added edge; pins cycle-exact).
module dsdv_gunit_l5 #(
    parameter integer MUT = 0,
    parameter integer PIN_COPY = `OT_S81_GUNIT_PIN_COPY,
    parameter integer CONTROL_SAFE = `OT_S81_GUNIT_CONTROL_SAFE,
    parameter integer Q4 = `OT_S81_GUNIT_Q4,
    parameter integer FANOUT_SAFE = `OT_S81_GUNIT_FANOUT_SAFE,
    // S81-GUVE 10-20: 1 = native-32 tail (dsdv_gunit_tail_fs NAT32; needs FANOUT_SAFE 1); 0 edges added
    parameter integer NAT32 = `OT_S81_GUNIT_NAT32
) (
    input  wire          clk,
    input  wire          rst_n,
    // S face (L4)
    input  wire [275:0]  rs_i,  output wire [275:0] rs_o,
    input  wire          launch, input wire mx_v, input wire [4:0] mx_i, input wire [31:0] mx_y, input wire t_set, input wire t_w, input wire [9:0] t_row,
    input  wire [4:0]    t_lm, input wire [15:0] t_sm,
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8, no constant / unused pins): cw_a packed {a[9:8], a[5:0]} (a[7:6] not read); ct_b = the packed CTL row
    input  wire          cw_v, input wire [7:0] cw_a, input wire [255:0] cw_d, input wire [3:0] sid_i,
    output reg           ct_v, output reg [169:0] ct_b, output reg fault,
    // N face (unit pins, s_3N)
    output wire [275:0]  vo_n,  input wire [275:0] vi_n,
    // E face (L5f: exp / fdiv)
    output wire          xe_v, output wire [31:0] xe_x, input wire ye_v, input wire [31:0] ye_y, input wire ye_f,
    output wire          xd_v, output wire [31:0] xd_b, input wire yd_v, input wire [31:0] yd_y, input wire yd_f
);
    localparam integer V = 276, NSET = 2;
    integer j;
    wire [3:0] rq;
    wire [15:0] rr;                                     // FANOUT_SAFE region roots (see ot_rst_region16)
    // rr owners: 0 pass (4) | 1 ln0 wv qm_v qe_v qd_v + ln copies 3 (8) | 2 scale enables (16) | 3 c_on c_i ct_v fault
    // on copies 2 + table check 3 (11) | 4, 5 CTL row selects (18 each) | 6 tail rst_n | 7..14 tail rst_v | 15 launch
    // first rank 4 + mix enables 8 (12)
    generate if (FANOUT_SAFE) begin : g_rst16
        ot_rst_region16 u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
        assign rq = {rr[3], rr[6], rr[1], rr[0]};
    end else begin : g_rst4
        ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
        assign rr = 16'd0;
    end endgenerate
    dsdv_gunit_pass #(.W(V)) u_up (.clk(clk), .rst_n(rq[0]), .d(rs_i), .q(vo_n));
    dsdv_gunit_pass #(.W(V)) u_dn (.clk(clk), .rst_n(rq[0]), .d(vi_n), .q(rs_o));
    // ---------------------------------------------------------------- input flops
    reg ln0, ln, wv, qm_v; reg [4:0] qm_i; reg [31:0] qm_y; reg [767:0] mx; reg tj_set, tj_w; reg [9:0] tj_row; reg [4:0] tj_lm; reg [15:0] tj_sm;
    reg [9:0] wa; reg [255:0] wd; reg [3:0] sid_c; reg [9:0] rj_row; reg [4:0] rj_lm; reg [15:0] rj_sm;
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin ln0 <= 1'b0; ln <= 1'b0; wv <= 1'b0; qm_v <= 1'b0; end
        else begin ln0 <= launch; ln <= ln0; wv <= cw_v; qm_v <= mx_v; end
    wire [2:0] ln_c;                                    // ln: tail launch | rj_row/lm enable | rj_sm enable
    always @(posedge clk) begin
        qm_i <= mx_i; qm_y <= mx_y;
        tj_set <= t_set; tj_w <= t_w; tj_row <= t_row; tj_lm <= t_lm; tj_sm <= t_sm;
        wa <= {cw_a[7:6], 2'd0, cw_a[5:0]}; wd <= cw_d; sid_c <= sid_i;
    end
    generate if (FANOUT_SAFE) begin : g_in_safe
        // ln: three kept same-edge copies (D = ln0, same reset) replace the 76-load ln.
        for (genvar lc = 0; lc < 3; lc = lc + 1) begin : g_ln
            (* keep = 1 *) dsdv_gunit_control_first u_q (.clk(clk), .rst_n(rr[1]), .d(ln0), .q(ln_c[lc]));
        end
        always @(posedge clk) begin
            if (ln_c[1]) begin rj_row <= tj_row; rj_lm <= tj_lm; end
            if (ln_c[2]) rj_sm <= tj_sm;
        end
        // mix writes: 8 kept {qm_v, qm_i} copies, copy k = half k % 2 of words 6 (k / 2) .. 6 (k / 2) + 5 (16 loads a
        // decoded enable, 6 decode gates a copy bit).
        for (genvar mc = 0; mc < 8; mc = mc + 1) begin : g_mq
            wire qv; wire [4:0] qi;
            (* keep = 1 *) dsdv_gunit_control_first u_v (.clk(clk), .rst_n(rr[15]), .d(mx_v), .q(qv));
            (* keep = 1 *) dsdv_gunit_index5 u_i (.clk(clk), .d(mx_i), .q(qi));
            for (genvar mw = 6 * (mc / 2); mw < 6 * (mc / 2) + 6; mw = mw + 1) begin : g_w
                for (genvar mq = 0; mq < 2; mq = mq + 1) begin : g_q      // kept enable gate per 8 bits
                    wire en;
                    (* keep = 1 *) ot_skf_and2 u_en (.a(qv), .b(qi == 5'(mw)), .y(en));
                    always @(posedge clk) if (en) mx[32 * mw + 16 * (mc % 2) + 8 * mq +: 8] <= qm_y[16 * (mc % 2) + 8 * mq +: 8];
                end
            end
        end
    end else begin : g_in_legacy
        always @(posedge clk) begin
            if (qm_v) mx[32 * qm_i +: 32] <= qm_y;          // the 24 mixes, one a cycle
            if (ln) begin rj_row <= tj_row; rj_lm <= tj_lm; rj_sm <= tj_sm; end   // the launched job's rows
        end
        assign ln_c = {3{ln}};
    end endgenerate
    wire [3:0] launch_pre;
    generate if (CONTROL_SAFE) begin : g_launch_first
        for (genvar lc = 0; lc < 4; lc = lc + 1) begin : g_copy
            (* keep = 1 *) dsdv_gunit_control_first u_q (.clk(clk), .rst_n(FANOUT_SAFE ? rr[15] : rq[1]), .d(launch), .q(launch_pre[lc]));
        end
    end else assign launch_pre = {4{ln0}}; endgenerate
    // ---------------------------------------------------------------- tables: bases, scales
    reg [767:0] bases; reg [95:0] scales;
    wire tbl_f;                                         // FANOUT_SAFE table lifetime fault (0 in legacy)
    genvar g;
    generate if (FANOUT_SAFE) begin : g_tbl_safe
        // job select ranks: 8 kept rank-1 copies, then 25 kept rank-2 copies: 12 bank read addresses, 12 scale bytes
        // (8-bit 4:1 each), 1 for the lifetime check.  Each copy drives <= ~20 loads.
        for (g = 0; g < 8; g = g + 1) begin : g_tj1
            (* keep = "true" *) reg s, w;
            always @(posedge clk) begin s <= tj_set; w <= tj_w; end
        end
        wire [24:0] ss, sw;
        for (g = 0; g < 25; g = g + 1) begin : g_tj2
            (* keep = "true" *) reg s, w;
            always @(posedge clk) begin s <= g_tj1[g % 8].s; w <= g_tj1[g % 8].w; end
            assign ss[g] = s; assign sw[g] = w;
        end
        // base table: 12 banks.  Config row o = wa[5:0] - 56 (0..5): which = o >= 3, bank group o % 3 (banks 4 (o % 3)
        // .. + 3, bank 4 (o % 3) + k <- wd[64 k +: 64]), set = wa[8]; physical row {set, which}.
        wire [5:0] wo = wa[5:0] - 6'd56;
        wire wbase = wv && !wa[9] && wa[5:0] >= 6'd56 && wa[5:0] < 6'd62;
        wire [1:0] wrow = {wa[8], wo >= 6'd3};
        for (g = 0; g < 12; g = g + 1) begin : g_bank
            wire wce = wbase && (wo == 6'(g / 4) || wo == 6'(g / 4 + 3));
            wire [63:0] rd;
            ot_sram_1r1w2c_32x64_m1 u_m (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in({3'b000, ss[g], sw[g]}),
                .rd_out(rd), .w_ce_in(wce), .w_addr_in({3'b000, wrow}), .wd_in(wd[64 * (g % 4) +: 64]),
                .w_mask_in({64{1'b1}}));
            always @(*) bases[64 * g +: 64] = rd;          // the macro's read register IS the bases capture
        end
        // scales: 4 x 96 flops; 16 kept write enables (24 bits each) predicted from the cw pins (= wv && !wa[9] &&
        // wa[5:0] == 62 && wa[8] == set, one edge early, same reset region as wv's peers).
        reg [95:0] scl_t [0:NSET*2-1];
        wire scw_d0 = cw_v && !cw_a[7] && cw_a[5:0] == 6'd62 && !cw_a[6];     // packed: cw_a[7:6] = a[9:8]
        wire scw_d1 = cw_v && !cw_a[7] && cw_a[5:0] == 6'd62 &&  cw_a[6];
        for (g = 0; g < 32; g = g + 1) begin : g_scw
            wire we;
            (* keep = 1 *) dsdv_gunit_control_first u_q (.clk(clk), .rst_n((g % 2) ? rr[13] : rr[2]), .d((g / 16) ? scw_d1 : scw_d0), .q(we));
            // copy g: scale word (g / 8) = 2 set + half, bits 12 (g % 8) +: 12; half h <- wd[96 h +: 96]
            always @(posedge clk) if (we) scl_t[g / 8][12 * (g % 8) +: 12] <= wd[96 * ((g / 8) % 2) + 12 * (g % 8) +: 12];
        end
        for (g = 0; g < 12; g = g + 1) begin : g_sc
            always @(posedge clk) scales[8 * g +: 8] <= scl_t[2 * ss[12 + g] + sw[12 + g]][8 * g +: 8];
        end
        // lifetime check: a base write to the currently selected word arms a 4-edge window; the tail taking the bases
        // (ln) inside it is a sticky fault.
        reg [2:0] hit;
        always @(posedge clk or negedge rr[3])
            if (!rr[3]) hit <= 3'd0;
            else if (wbase && wrow == {ss[24], sw[24]}) hit <= 3'd4;
            else if (hit != 3'd0) hit <= hit - 3'd1;
        assign tbl_f = ln_c[0] && hit != 3'd0;
    end else begin : g_tbl_legacy
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
        assign tbl_f = 1'b0;
    end endgenerate
    // ---------------------------------------------------------------- the tail
    wire tl_v, tl_f; wire [767:0] coef;
    reg qe_v, qe_f, qd_v, qd_f; reg [31:0] qe_y, qd_y;   // L5f results: input flops
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin qe_v <= 1'b0; qd_v <= 1'b0; end else begin qe_v <= ye_v; qd_v <= yd_v; end
    always @(posedge clk) begin qe_y <= ye_y; qe_f <= ye_f; qd_y <= yd_y; qd_f <= yd_f; end
    generate if (FANOUT_SAFE) begin : g_tail_safe
    // dsdv_gunit_tail_fs (CONTROL_SAFE + Q4 built in): 12 kept launch copies one edge early (== ln0), 4 kept landing
    // copies of each L5f valid (same pin, same reset), so no launch / valid flop drives more than ~24 loads.
    wire [11:0] lp12; wire [3:0] qe_vc, qd_vc;
    for (genvar lc = 0; lc < 12; lc = lc + 1) begin : g_lp
        (* keep = 1 *) dsdv_gunit_control_first u_q (.clk(clk), .rst_n(lc < 6 ? rr[15] : rr[2]), .d(launch), .q(lp12[lc]));
    end
    for (genvar vc = 0; vc < 4; vc = vc + 1) begin : g_vc
        (* keep = 1 *) dsdv_gunit_control_first u_e (.clk(clk), .rst_n(rr[1]), .d(ye_v), .q(qe_vc[vc]));
        (* keep = 1 *) dsdv_gunit_control_first u_d (.clk(clk), .rst_n(rr[1]), .d(yd_v), .q(qd_vc[vc]));
    end
    dsdv_gunit_tail_fs #(.PIN_COPY(PIN_COPY), .NAT32(NAT32), .MUT_PRE(MUT == 8 ? 1 : 0), .MUT_SK(MUT == 10 ? 1 : 0)) u_tail (.clk(clk), .rst_n(rr[6]), .rst_v(rr[14:7]), .launch(ln_c[0]), .launch_pre(lp12), .mixes(mx), .bases(bases), .scales(scales),
        .result_v(tl_v), .result(coef), .fault(tl_f),
        .xe_v(xe_v), .xe_x(xe_x), .xe_vo(qe_vc), .xe_y(qe_y), .xe_f(qe_f),
        .xd_v(xd_v), .xd_b(xd_b), .xd_vo(qd_vc), .xd_y(qd_y), .xd_f(qd_f));
    end else begin : g_tail_legacy
    dsdv_gunit_tail #(.PIN_COPY(PIN_COPY), .CONTROL_SAFE(CONTROL_SAFE), .Q4(Q4), .MUT_PRE(MUT == 8 ? 1 : 0), .MUT_SK(MUT == 10 ? 1 : 0)) u_tail (.clk(clk), .rst_n(rq[2]), .launch(ln), .launch_pre(launch_pre), .mixes(mx), .bases(bases), .scales(scales),
        .result_v(tl_v), .result(coef), .fault(tl_f),
        .xe_v(xe_v), .xe_x(xe_x), .xe_vo(qe_v), .xe_y(qe_y), .xe_f(qe_f),
        .xd_v(xd_v), .xd_b(xd_b), .xd_vo(qd_v), .xd_y(qd_y), .xd_f(qd_f));
    end endgenerate
    // ---------------------------------------------------------------- coefficient CTL rows (target 5), output flops
    function automatic [V-1:0] ctl(input [9:0] a, input [127:0] d, input [15:0] sm, input [4:0] lm, input [3:0] s);
        reg [185:0] p;
        begin
            p = 186'd0; p[15:0] = sm; p[20:16] = 5'd5; p[25:21] = lm;
            p[26 +: 10] = a; p[36 +: 4] = 4'hf; p[40 +: 128] = d;
            ctl = {V{1'b0}}; ctl[0] = 1'b1; ctl[12:9] = s; ctl[21 +: 186] = p;
        end
    endfunction
    // S81-KITS-RTLC 10-24 (OWNER DECISION 8): the CTL row leaves packed (bits 1..8, 13..20, 38, 40, 41, 189..275 of ctl()
    // are constant 0; see dsdv_gunit_l3 / L2 unpacks before the vstop inject)
    function automatic [169:0] ctlpk(input [275:0] w); ctlpk = {w[188:42], w[39], w[37:21], w[12:9], w[0]}; endfunction
    reg c_on; reg [2:0] c_i;
    always @(posedge clk or negedge rq[3])
        if (!rq[3]) begin c_on <= 1'b0; c_i <= 3'd0; ct_v <= 1'b0; fault <= 1'b0; end
        else begin
            if (tl_v) begin c_on <= 1'b1; c_i <= 3'd0; end
            else if (c_on) begin c_i <= c_i + 3'd1; if (c_i == 3'd5) c_on <= 1'b0; end
            ct_v <= c_on;
            if (tl_f || (tl_v && c_on) || tbl_f) fault <= 1'b1;
        end
    generate if (FANOUT_SAFE) begin : g_ct_safe
        // Same-edge kept copies: on (2 x c_on, header gating) and the registered one-hot row select rs[r] = c_on &&
        // c_i == r, predicted from the c_on / c_i next state (6 copies a row, 22 data bits each).  Exact: after every
        // edge on == c_on and rs[r] == (c_on && c_i == r); both reset with c_on.
        wire on_d = tl_v ? 1'b1 : (c_on && c_i != 3'd5);
        wire [2:0] ci_d = tl_v ? 3'd0 : (c_on ? c_i + 3'd1 : c_i);
        wire [1:0] on;
        for (genvar oc = 0; oc < 2; oc = oc + 1) begin : g_on
            (* keep = 1 *) dsdv_gunit_control_first u_q (.clk(clk), .rst_n(rr[3]), .d(on_d), .q(on[oc]));
        end
        wire [127:0] cq;
        for (genvar dc = 0; dc < 6; dc = dc + 1) begin : g_dc                 // data slice dc: bits 22 dc +: 22 (last 18)
            localparam integer B0 = 22 * dc, NB = (dc == 5) ? 18 : 22;
            wire [5:0] rs;
            for (genvar r = 0; r < 6; r = r + 1) begin : g_r
                (* keep = 1 *) dsdv_gunit_control_first u_q (.clk(clk), .rst_n(dc < 3 ? rr[4] : rr[5]), .d(on_d && ci_d == 3'(r)), .q(rs[r]));
            end
            for (genvar b = B0; b < B0 + NB; b = b + 1) begin : g_b
                assign cq[b] = (rs[0] & coef[b]) | (rs[1] & coef[128 + b]) | (rs[2] & coef[256 + b]) |
                               (rs[3] & coef[384 + b]) | (rs[4] & coef[512 + b]) | (rs[5] & coef[640 + b]);
            end
        end
        // cq is already zero when idle; the header is gated by on copies (on[0]: bits 0..36 valid / sid / sm, 21
        // loads; on[1]: bits 37..60 target / lm / a / mask, 21 loads; the data field of hdr is constant 0)
        wire [V-1:0] hdr = ctl(rj_row + {7'd0, c_i}, 128'd0, rj_sm, rj_lm, sid_c);
        wire [V-1:0] gate = {{(V-37){on[1]}}, {37{on[0]}}};
`ifdef OT_RTLC_MUT_L5   // RTLC bench mutant: packed coefficient row loses data bit 0 (w[61])
        always @(posedge clk) ct_b <= ctlpk((hdr & gate) | {{(V-61-128){1'b0}}, cq, 61'd0}) & ~(170'd1 << 42);
`else
        always @(posedge clk) ct_b <= ctlpk((hdr & gate) | {{(V-61-128){1'b0}}, cq, 61'd0});
`endif
    end else begin : g_ct_legacy
    reg [127:0] cq;                                     // coefficient row c_i (decoded constant-index slices)
    always @(*) case (c_i)
        3'd0: cq = coef[127:0];   3'd1: cq = coef[255:128]; 3'd2: cq = coef[383:256];
        3'd3: cq = coef[511:384]; 3'd4: cq = coef[639:512]; default: cq = coef[767:640];
    endcase
`ifdef OT_RTLC_MUT_L5   // RTLC bench mutant: packed coefficient row loses data bit 0 (w[61])
    always @(posedge clk) ct_b <= ctlpk(c_on ? ctl(rj_row + {7'd0, c_i}, cq, rj_sm, rj_lm, sid_c) : {V{1'b0}}) & ~(170'd1 << 42);
`else
    always @(posedge clk) ct_b <= ctlpk(c_on ? ctl(rj_row + {7'd0, c_i}, cq, rj_sm, rj_lm, sid_c) : {V{1'b0}});
`endif
    end endgenerate
endmodule
// FANOUT_SAFE kept index copy (fixed width: the module name survives synthesis; instances are (* keep *)).
(* keep_hierarchy = 1 *) module dsdv_gunit_index5(input wire clk, input wire [4:0] d, output reg [4:0] q);
    always @(posedge clk) q <= d;
endmodule
