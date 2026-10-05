`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_slab_port_group: ONE result-port group of the Qwen3-8B ROM die band
// slab (tools/qwen_rom_fulldie_b3r2.py --b3r3: each qfd_port_tiles_<b>[_f1]
// slab holds 8 of these), as a physical measurement vehicle for the M1-M5 slab
// abstract (results/rtl/qwen_slab_m5_20261004).  Default-off: nothing in the
// decode path instantiates it.
//
// Contents, per group, as the slab replicates them:
//   * the block-word crossing FIFO of clocking decision C (ot_meso_fifo,
//     W = 512, the block's forwarded clock bw_clk -> the spine clock clk);
//     its output word goes on to the tree top (tw_*);
//   * the group's dense scale image: SCALE_BANKS ot_rom_4096x266_m8 banks
//     (rp['scale_rom']['rtl_compatible']['banks_per_port_group'] = 16), bank b
//     holding words 4096b.. (ot_qwen_o4_g4_rommac g_scale addressing);
//   * the post-scale of ot_qwen_w12_matvec_part PART 2 g_post_scale for this
//     group: the scale request (active test and address), 16 FP32 multipliers,
//     the two result registers (o_*1, o_*2), the result mask and o_we/o_addr;
//   * the group's argmax leaves (ot_qwen_w12_matvec_part g_leaf) and the first
//     log2(W) = 4 levels of the argmax compare tree (the 16 leaves of this
//     group); levels 5.. combine groups and live with the tree top.
//
// Differences from the RTL slice, all timing only (values are unchanged):
//   1. Scale read pipeline.  The RTL registers the request, the ROM reads on the
//      next edge and the FP32 multiplier samples scale_q one cycle later, so the
//      macro's SS clk->q (739 ps of the 773 ps budget) would have to cover the
//      bank OR and the multiplier's first stage.  Here the request goes through
//      a column copy (R2) and a per-bank decode register (R3) that drive the
//      macro pins, the macro output is captured by a flop at its pins (C4), the
//      captured words are merged per column (M5) and across columns (M6), and
//      M6 feeds the multiplier.  With the tag arithmetic of 4. the request
//      leads the result by LEAD = 8 cycles at the pins instead of 2.  The
//      request depends only on the instruction tag, which the top already
//      holds that early (pre_tag is a tap of the s3 tag line, SD - LEAD + OD +
//      XDD >= 0 for SD = MUL_LAT + ACC_LAT >= 13), so this adds no cycle to an op.
//   2. Multiplier.  ot_hdc_fp32_mul_lat #(MUL_LAT) in place of ot_hdc_fmul
//      (ot_hdc_fp32_mul_pipe, LAT 5): bit-identical (ot_hdc_fp32_mul_lat ==
//      ot_hdc_fp32_mul_fast, rtl/test/tb_w11_fp32_mul_lat; ot_hdc_fp32_mul_fast
//      == ot_hdc_fp32_mul_pipe, rtl/test/tb_hdc_fastfp_equiv), and LAT 6 is the
//      smallest that closed 0.833 ns at SS alone (w11_fp_latency_sweep); the
//      LAT 5 pipe routes at ~1.0 GHz SS.  MUL_LAT - 5 cycles are added once per
//      ME op (the post-scale is on the op's result path).
//   3. Boundary registers.  Every input is registered once at the element
//      boundary (one of the spine wire stages TWS/ORD the die already counts),
//      and the reset is distributed through registered copies.
//   4. Tag arithmetic.  The per-group row tests (nb + GID*W*IL + l < nout, and
//      the lb form), the scale address and the result address are evaluated
//      once, two cycles ahead, on explicit prefix adders, and the lane masks and
//      addresses travel down the tag line (the same predicates; the RTL's
//      behavioural adds map to ripple chains, abc-re-ripples-adders).
//   5. Argmax node.  The RTL's node test is one 48-bit prefix compare of
//      {key, ~row} (identical predicate, see g_alvl).
// GID is the group's index (the RTL's gb + q, a constant per instance).
// ---------------------------------------------------------------------------
module ot_qwen_slab_port_group #(
    parameter integer W = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer GT = 6144,
    parameter integer GID = 95,
    parameter integer SCALE_BANKS = 16,
    parameter integer COLS = 4,             // macro columns: banks c*BPC .. c*BPC+BPC-1 share a column copy
    parameter integer MUL_LAT = 6,
    parameter integer BW_FIFO = 1,
    // Timing-only options (values and order unchanged; default off = the S3 RTL):
    //   IN_STAGE 1: one register stage in front of every multiplier (operands and valid, placed beside it), so
    //               the boundary register res_q -> multiplier wire is its own cycle.  +1 cycle per ME op.
    //   AM_SPLIT 1: each argmax node compares in one cycle and selects in the next (two kept select copies).
    //               +1 cycle per level (LW levels) on the argmax top only.
    //   S5_CTL   1: the scale-request range test d > 0 is registered at D1 from its own adders (d - 1 >= 0), and
    //               each bank's capture select drives the column OR through 8 kept copies of 32 loads.  0 cycles.
    parameter integer IN_STAGE = 0,
    parameter integer AM_SPLIT = 0,
    parameter integer S5_CTL = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // block word in (the block's forwarded clock) and on to the tree top
    input  wire              bw_clk,
    input  wire              bw_rst_n,
    input  wire              bw_v,
    output wire              bw_rdy,
    input  wire [W*32-1:0]   bw_d,
    output wire              tw_v,
    input  wire              tw_rdy,
    output wire [W*32-1:0]   tw_d,
    // instruction tag at request time (the RTL's pre_tag + its valid line tap)
    input  wire              p_v,
    input  wire              p_last, p_oen, p_amax, p_rmax, p_wsrc, p_mmode,
    input  wire [3:0]        p_split,
    input  wire [NW:0]       p_nb, p_lb, p_nout,
    input  wire [AW-1:0]     p_sbase, p_oa, p_ots,
    // the group's tree result, LEAD cycles after its tag
    input  wire [W*32-1:0]   res_in,
    // result write towards the vector memory
    output wire              o_we,
    output wire [AW-1:0]     o_addr,
    output wire [W-1:0]      o_mask,
    output wire [W*32-1:0]   o_data,
    output wire              ov,
    // the group's argmax subtree top {valid, key, row} and its valid line
    output wire              am_tv,
    output wire [1+32+NW-1:0] am_top,
    output wire              am_rmax,
    output wire              fault,
    output wire              bw_w_fault, bw_r_fault, bw_w_live, bw_r_live
);
    localparam integer LW = $clog2(W);
    localparam integer BPC = SCALE_BANKS / COLS;
    localparam integer LEAD = 8;              // tag pins -> multiplier input (see header, 1.)
    localparam integer DW = 20;               // signed width of the row-count differences
    localparam integer KR = 1 + 1 + 1 + 1 + 1 + 1 + W + AW + NW;   // tag carried past the request stage

    // ---- reset distribution: the pin's reset, registered, then one copy per consumer cluster ------------
    wire rs0, rs, rs_bw, bw_rs;
    ot_qwen_slab_pg_rcopy #(.AW(1)) u_rs0 (.clk(clk), .gre(rst_n), .addr(1'b0), .gre_q(rs0), .addr_q());
    ot_qwen_slab_pg_rcopy #(.AW(1)) u_rs  (.clk(clk), .gre(rs0), .addr(1'b0), .gre_q(rs), .addr_q());
    ot_qwen_slab_pg_rcopy #(.AW(1)) u_rsb (.clk(clk), .gre(rs0), .addr(1'b0), .gre_q(rs_bw), .addr_q());
    ot_qwen_slab_pg_rcopy #(.AW(1)) u_bwr (.clk(bw_clk), .gre(bw_rst_n), .addr(1'b0), .gre_q(bw_rs), .addr_q());

    // ---- boundary registers (cycle 1) ---------------------------------------------------------------
    reg              t_v, t_last, t_oen, t_amax, t_rmax, t_wsrc, t_mmode;
    reg  [3:0]       t_split;
    reg  [NW:0]      t_nb, t_lb, t_nout;
    reg  [AW-1:0]    t_sbase, t_oa, t_ots;
    reg  [W*32-1:0]  res_q;
    always @(posedge clk) begin
        t_v <= rs ? p_v : 1'b0;
        {t_last, t_oen, t_amax, t_rmax, t_wsrc, t_mmode, t_split} <= {p_last, p_oen, p_amax, p_rmax, p_wsrc, p_mmode, p_split};
        {t_nb, t_lb, t_nout, t_sbase, t_oa, t_ots} <= {p_nb, p_lb, p_nout, p_sbase, p_oa, p_ots};
        res_q <= res_in;
    end

    // ---- D1 (cycle 2): the group's row-count differences, scale address and result address terms -------
    // RTL: lane l of group GID is in range iff (mmode ? lb + GID*W : nb + GID*W*IL) + l < nout; here
    // dn / dl = nout - (nb + GID*W*IL) / nout - (lb + GID*W) (exact, DW-bit signed) and lane l iff d > l.
    localparam [DW-1:0] CDN = 1 - GID * W * IL, CDL = 1 - GID * W;
    localparam [AW-1:0] CSB = GID * IL;
    localparam [NW-1:0] CRB = GID * W * IL;
    wire [DW-1:0] dn, dl;
    wire [DW-1:0] nb_ext = {{(DW-NW-1){1'b0}}, t_nb};
    wire [DW-1:0] lb_ext = {{(DW-NW-1){1'b0}}, t_lb};
    wire [DW-1:0] nout_ext = {{(DW-NW-1){1'b0}}, t_nout};
    ot_qwen_slab_pg_add3 #(.W(DW)) u_dn (.a(nout_ext), .b(~nb_ext), .c(CDN), .s(dn));
    ot_qwen_slab_pg_add3 #(.W(DW)) u_dl (.a(nout_ext), .b(~lb_ext), .c(CDL), .s(dl));
    wire [AW-1:0] sb, ots95;
    ot_qwen_slab_pg_add3 #(.W(AW)) u_sb (.a(t_sbase), .b({{(AW-NW-1+LW){1'b0}}, t_nb[NW:LW]}), .c(CSB), .s(sb));
    // GID * ots for the result address (RTL o_addr1 = r_oa + (gb + q) * r_ots)
    wire [AW-1:0] gots;
    ot_qwen_slab_pg_cmul #(.W(AW), .K(GID)) u_gots (.a(t_ots), .p(gots));
    wire [NW-1:0] rb16;
    ot_hdc_ksadd_k #(.W(NW)) u_rb (.a(t_nb[NW-1:0]), .b(CRB), .cin(1'b0), .s(rb16), .cout());
    wire [$clog2(GT):0] t_ports = GT >> t_split;
    wire [DW-1:0] dnm1, dlm1;   // d - 1 (S5_CTL): d > 0  <=>  d - 1 >= 0
    ot_qwen_slab_pg_add3 #(.W(DW)) u_dnm (.a(nout_ext), .b(~nb_ext), .c(CDN - 1'b1), .s(dnm1));
    ot_qwen_slab_pg_add3 #(.W(DW)) u_dlm (.a(nout_ext), .b(~lb_ext), .c(CDL - 1'b1), .s(dlm1));
    reg d_pos_q;
    reg d_v, d_last, d_oen, d_amax, d_rmax, d_wsrc, d_portok;
    reg [DW-1:0] d_d;
    reg [AW-1:0] d_sb, d_sbase, d_oa, d_gots;
    reg [NW-1:0] d_rb;
    always @(posedge clk) begin
        d_v <= rs && t_v;
        {d_last, d_oen, d_amax, d_rmax, d_wsrc} <= {t_last, t_oen, t_amax, t_rmax, t_wsrc};
        d_portok <= GID < t_ports;
        d_d <= t_mmode ? dl : dn;
        d_pos_q <= !(t_mmode ? dlm1[DW-1] : dnm1[DW-1]);
        d_sb <= sb; d_sbase <= t_sbase; d_oa <= t_oa; d_gots <= gots; d_rb <= rb16;
    end

    // ---- D2 (cycle 3): lane masks, scale request R1 (RTL pre_scale_active / scale_addr), result address ----
    wire d_pos = (S5_CTL != 0) ? d_pos_q : (!d_d[DW-1] && (d_d != 0));
    wire [W-1:0] d_mask;
    genvar ml;
    generate for (ml = 0; ml < W; ml = ml + 1) begin : g_dm
        // d > ml  (d signed, ml < W)
        assign d_mask[ml] = d_portok && !d_d[DW-1] && ((|d_d[DW-2:LW]) || (d_d[LW-1:0] > ml));
    end endgenerate
    wire q_active = d_v && d_last && !d_wsrc && d_portok && d_pos;
    wire [AW-1:0] oa_sum;
    ot_hdc_ksadd_k #(.W(AW)) u_oa (.a(d_oa), .b(d_gots), .cin(1'b0), .s(oa_sum), .cout());
    reg          gre1;
    reg [AW-1:0] addr1;
    reg          k_v;
    reg [KR-1:0] k_tag;
    always @(posedge clk) begin
        gre1 <= rs && q_active;
        addr1 <= q_active ? d_sb : d_sbase;
        k_v <= rs && d_v;
        k_tag <= {d_last, d_oen, d_amax, d_rmax, d_wsrc, d_portok, d_mask, oa_sum, d_rb};
    end

    // ---- tag line: cycle 3 -> multiplier time (cycle LEAD + 1) -> result time (+ MUL_LAT) -----------------
    localparam integer KD = LEAD - 2;
    wire [KR-1:0] m_tag, r_tag;
    localparam integer XL = MUL_LAT + IN_STAGE;   // multiplier input -> result
    reg  [KD+XL:1] vline;
    always @(posedge clk) vline <= rs ? {vline[KD+XL-1:1], k_v} : {(KD+XL){1'b0}};
    // KD - 1 shared stages, then the last stage as per-lane copies (S3, timing only): each multiplier's valid and
    // operand select come from a kept register beside it instead of one tag register fanned out to 16 lanes
    // (twoface_570 post-CTS: u_mt line -> g_mul[*] 545 ps of buffering, -210 ps).  m_tag itself is unchanged.
    wire [KR-1:0] e_tag;
    reg  [KR-1:0] m_tag_q;
    ot_hdc_delay #(.W(KR), .D(KD - 1)) u_mt (.clk(clk), .rst_n(rs), .d(k_tag), .q(e_tag));
    always @(posedge clk) m_tag_q <= e_tag;
    assign m_tag = m_tag_q;
    ot_hdc_delay #(.W(KR), .D(XL)) u_rt (.clk(clk), .rst_n(rs), .d(m_tag), .q(r_tag));
    wire m_v = vline[KD];
    wire r_v = vline[KD + XL];

    // ---- scale ROM: column copies (R2), per-bank decode (R3), macros, pin capture (C4) ------------
    wire [255:0] colq [0:COLS-1];
    genvar c, b, si;
    generate
        for (c = 0; c < COLS; c = c + 1) begin : g_col
            wire          gre2;
            wire [AW-1:0] addr2;
            ot_qwen_slab_pg_rcopy #(.AW(AW)) u_r2 (.clk(clk), .gre(gre1), .addr(addr1), .gre_q(gre2), .addr_q(addr2));
            wire [255:0] cor [0:BPC];
            assign cor[0] = 256'd0;
            for (b = 0; b < BPC; b = b + 1) begin : g_bank
                localparam integer BK = c * BPC + b;
                wire        ce3;
                wire [11:0] a3;
                ot_qwen_slab_pg_bdec #(.AW(AW), .BK(BK)) u_r3 (.clk(clk), .gre(gre2), .addr(addr2), .ce_q(ce3), .a_q(a3));
                reg        sel4, sel5;
                (* keep *) reg [7:0] sel5c;   // S5_CTL: 8 copies of sel5, 32 loads each
                reg [255:0] cap4;
                wire [265:0] rd;
                always @(posedge clk) begin
                    sel4 <= ce3;             // with the macro's sampling edge
                    sel5 <= sel4;            // with the capture
                    sel5c <= {8{sel4}};
                    cap4 <= rd[255:0];
                end
                ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(ce3), .addr_in(a3), .rd_out(rd));
                wire [255:0] selv;
                genvar sk;
                for (sk = 0; sk < 8; sk = sk + 1) begin : g_sel
                    assign selv[32*sk +: 32] = {32{(S5_CTL != 0) ? sel5c[sk] : sel5}};
                end
                assign cor[b+1] = cor[b] | (cap4 & selv);
            end
            reg [255:0] m5;
            always @(posedge clk) m5 <= cor[BPC];
            assign colq[c] = m5;
        end
    endgenerate
    wire [255:0] cacc [0:COLS];
    assign cacc[0] = 256'd0;
    generate
        for (c = 0; c < COLS; c = c + 1) begin : g_cacc
            assign cacc[c+1] = cacc[c] | colq[c];
        end
    endgenerate
    reg [255:0] m6;
    always @(posedge clk) m6 <= cacc[COLS];

    // ---- post-scale multipliers (RTL g_scale), multiplier time ------------------------------------
    wire m_last, m_oen, m_amax, m_rmax, m_wsrc, m_portok;
    wire [W-1:0] m_mask;
    wire [AW-1:0] m_oa;
    wire [NW-1:0] m_rb;
    assign {m_last, m_oen, m_amax, m_rmax, m_wsrc, m_portok, m_mask, m_oa, m_rb} = m_tag;
    wire e_last, e_wsrc;
    wire [W-1:0] e_mask;
    assign {e_last, e_wsrc, e_mask} = {e_tag[KR-1], e_tag[KR-5], e_tag[KR-7 -: W]};
    wire [W*32-1:0] scaled;
    wire [W-1:0]    mfault;
    generate
        for (si = 0; si < W; si = si + 1) begin : g_mul
            wire [1:0] err;
            wire       vo, rsm, l_v, l_ws;
            ot_qwen_slab_pg_rcopy #(.AW(1)) u_rsm (.clk(clk), .gre(rs0), .addr(1'b0), .gre_q(rsm), .addr_q());
            // == m_v && m_last && m_mask[si] and m_wsrc (vline[KD] = rs ? vline[KD-1] : 0, one edge later)
            ot_qwen_slab_pg_rcopy #(.AW(1)) u_tc (.clk(clk), .gre(rs && vline[KD-1] && e_last && e_mask[si]),
                .addr(e_wsrc), .gre_q(l_v), .addr_q(l_ws));
            wire        i_v;
            wire [31:0] i_a;
            wire [15:0] i_b;
            if (IN_STAGE != 0) begin : g_in
                reg        v_q;
                reg [31:0] a_q;
                reg [15:0] b_q;
                always @(posedge clk) begin
                    v_q <= l_v;
                    a_q <= res_q[32*si +: 32];
                    b_q <= l_ws ? 16'h3F80 : m6[16*si +: 16];
                end
                assign i_v = v_q; assign i_a = a_q; assign i_b = b_q;
            end else begin : g_noin
                assign i_v = l_v; assign i_a = res_q[32*si +: 32]; assign i_b = l_ws ? 16'h3F80 : m6[16*si +: 16];
            end
            ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_mul (.clk(clk), .rst_n(rsm),
                .valid_in(i_v),
                .a(i_a), .b({i_b, 16'd0}),
                .y(scaled[32*si +: 32]), .err(err), .valid_out(vo));
            assign mfault[si] = vo && (err != 2'd0);
        end
    endgenerate
    reg fault_q;
    always @(posedge clk) fault_q <= rs && (|mfault);
    assign fault = fault_q;

    // ---- results (RTL o_*1 / o_*2), result time ---------------------------------------------------
    wire r_last, r_oen, r_amax, r_rmax, r_wsrc, r_portok;
    wire [W-1:0] r_mask;
    wire [AW-1:0] r_oa;
    wire [NW-1:0] r_rb;
    assign {r_last, r_oen, r_amax, r_rmax, r_wsrc, r_portok, r_mask, r_oa, r_rb} = r_tag;
    reg ov1, ov2, we1, we2;
    reg [AW-1:0] oa1, oa2;
    reg [W-1:0] om1, om2;
    reg [W*32-1:0] od1, od2;
    always @(posedge clk) begin
        ov1 <= rs && r_v && r_last;
        we1 <= rs && r_v && r_last && r_oen && r_portok;
        ov2 <= rs && ov1;
        we2 <= rs && we1;
        oa1 <= r_oa;
        om1 <= r_mask;
        od1 <= scaled;
        oa2 <= oa1; om2 <= om1; od2 <= od1;
    end
    assign ov = ov2; assign o_we = we2; assign o_addr = oa2; assign o_mask = om2; assign o_data = od2;

    // ---- argmax leaves and the group's 4 compare levels (RTL g_leaf / g_alvl) ----------------------
    // The RTL's node test  x0.v && (!x1.v || k0 > k1 || (k0 == k1 && row0 < row1))  is evaluated as one
    // 48-bit compare {k0, ~row0} > {k1, ~row1} on an explicit prefix carry (the same predicate).
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer CW = 1 + 32 + NW;
    localparam integer LV = LW;
    localparam integer TL = LV * (1 + AM_SPLIT);   // leaf -> top cycles after the leaf
    wire [CW*W-1:0] alv [0:LV];
    reg  [TL:0] tv;
    reg  [TL:0] trm;
    always @(posedge clk) begin
        tv  <= rs ? {tv[TL-1:0], r_v && r_last && (r_amax || r_rmax)} : {(TL+1){1'b0}};
        trm <= {trm[TL-1:0], r_rmax};
    end
    genvar e, lv;
    generate
        for (e = 0; e < W; e = e + 1) begin : g_leaf
            reg [CW-1:0] cq;
            localparam [NW-1:0] CE = e;
            wire [NW-1:0] row;
            ot_hdc_ksadd_k #(.W(NW)) u_row (.a(r_rb), .b(CE), .cin(1'b0), .s(row), .cout());
            always @(posedge clk) cq <= {r_mask[e], okey(scaled[32*e +: 32]), row};
            assign alv[0][CW*e +: CW] = cq;
        end
        for (lv = 1; lv <= LV; lv = lv + 1) begin : g_alvl
            for (e = 0; e < (W >> lv); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[lv-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[lv-1][CW*(2*e+1) +: CW];
                wire gt;
                ot_hdc_ksadd_k #(.W(32 + NW)) u_cmp (.a({x0[CW-2 -: 32], ~x0[NW-1:0]}),
                    .b(~{x1[CW-2 -: 32], ~x1[NW-1:0]}), .cin(1'b0), .s(), .cout(gt));
                wire x0_wins = x0[CW-1] && (!x1[CW-1] || gt);
                reg [CW-1:0] cq;
                if (AM_SPLIT != 0) begin : g_split
                    (* keep *) reg [1:0] w_q;   // two select copies, 25 / 24 loads
                    reg [CW-1:0] x0_q, x1_q;
                    always @(posedge clk) begin
                        w_q <= {2{x0_wins}};
                        x0_q <= x0; x1_q <= x1;
                        cq <= {w_q[1] ? x0_q[CW-1:25] : x1_q[CW-1:25], w_q[0] ? x0_q[24:0] : x1_q[24:0]};
                    end
                end else begin : g_one
                    always @(posedge clk) cq <= x0_wins ? x0 : x1;
                end
                assign alv[lv][CW*e +: CW] = cq;
            end
            if ((W >> lv) < W) begin : g_pad
                assign alv[lv][CW*W-1 : CW*(W >> lv)] = 0;
            end
        end
    endgenerate
    assign am_top = alv[LV][CW-1:0];
    assign am_tv = tv[TL];
    assign am_rmax = trm[TL];

    // ---- block-word crossing FIFO (decision C) ----------------------------------------------------
    generate if (BW_FIFO != 0) begin : g_bw
        ot_meso_fifo #(.W(W*32), .ENABLE(1)) u_bw (
            .wclk(bw_clk), .wrst_n(bw_rs), .w_v(bw_v), .w_rdy(bw_rdy), .w_d(bw_d),
            .rclk(clk), .rrst_n(rs_bw), .r_v(tw_v), .r_rdy(tw_rdy), .r_d(tw_d),
            .w_live(bw_w_live), .r_live(bw_r_live), .w_fault(bw_w_fault), .r_fault(bw_r_fault));
    end else begin : g_nobw
        assign bw_rdy = 1'b0; assign tw_v = 1'b0; assign tw_d = {W*32{1'b0}};
        assign bw_w_live = 1'b0; assign bw_r_live = 1'b0; assign bw_w_fault = 1'b0; assign bw_r_fault = 1'b0;
    end endgenerate
endmodule

// a + b + c (W bits): one carry-save row, then the explicit prefix adder.
module ot_qwen_slab_pg_add3 #(parameter integer W = 24) (
    input  wire [W-1:0] a, b, c,
    output wire [W-1:0] s
);
    wire [W-1:0] x = a ^ b ^ c;
    wire [W-1:0] y = {((a[W-2:0] & b[W-2:0]) | (a[W-2:0] & c[W-2:0]) | (b[W-2:0] & c[W-2:0])), 1'b0};
    ot_hdc_ksadd_k #(.W(W)) u (.a(x), .b(y), .cin(1'b0), .s(s), .cout());
endmodule

// p = a * K (W bits) for a constant K: the shifted copies of a for K's set bits, summed by a chain of
// carry-save rows and one explicit prefix adder (a behavioural constant multiply maps to ripple adders).
module ot_qwen_slab_pg_cmul #(parameter integer W = 24, parameter integer K = 95) (
    input  wire [W-1:0] a,
    output wire [W-1:0] p
);
    wire [W-1:0] sv [0:W];
    wire [W-1:0] cv [0:W];
    assign sv[0] = {W{1'b0}};
    assign cv[0] = {W{1'b0}};
    genvar i;
    generate
        for (i = 0; i < W; i = i + 1) begin : g_t
            if ((K >> i) & 1) begin : g_on
                wire [W-1:0] t = a << i;
                assign sv[i+1] = sv[i] ^ cv[i] ^ t;
                assign cv[i+1] = {((sv[i][W-2:0] & cv[i][W-2:0]) | (sv[i][W-2:0] & t[W-2:0]) | (cv[i][W-2:0] & t[W-2:0])), 1'b0};
            end else begin : g_off
                assign sv[i+1] = sv[i];
                assign cv[i+1] = cv[i];
            end
        end
    endgenerate
    ot_hdc_ksadd_k #(.W(W)) u (.a(sv[W]), .b(cv[W]), .cin(1'b0), .s(p), .cout());
endmodule

// Request copies (R2) and per-bank decode registers (R3): kept hierarchy keeps the replicated registers from being
// merged, so each macro column / bank is driven from a register placed beside it.
(* keep_hierarchy *)
module ot_qwen_slab_pg_rcopy #(parameter integer AW = 24) (
    input  wire          clk,
    input  wire          gre,
    input  wire [AW-1:0] addr,
    output reg           gre_q,
    output reg  [AW-1:0] addr_q
);
    always @(posedge clk) begin gre_q <= gre; addr_q <= addr; end
endmodule

(* keep_hierarchy *)
module ot_qwen_slab_pg_bdec #(parameter integer AW = 24, parameter integer BK = 0) (
    input  wire          clk,
    input  wire          gre,
    input  wire [AW-1:0] addr,
    output reg           ce_q,
    output reg  [11:0]   a_q
);
    always @(posedge clk) begin ce_q <= gre && (addr[AW-1:12] == BK); a_q <= addr[11:0]; end
endmodule
