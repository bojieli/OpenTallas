// Slab parent partition: existing parent registers in one core leaf; eight child clocks enter separately.
// Scale and multiplier return faces gain one capture clock each (+2 result clocks). Original slab module remains the independent reference.
// Supports production W16/COLS4; clock entries must receive die phase phi minus each child insertion.
module ot_qwen_slab_pg_core #(
    parameter integer W = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer SCALE_BANKS = 16,
    parameter integer COLS = 4,             // macro columns: banks c*BPC .. c*BPC+BPC-1 share a column copy
    parameter integer MUL_LAT = 6,
    parameter integer BW_FIFO = 0,
    // Timing-only options (values and order unchanged; default off = the S3 RTL):
    //   IN_STAGE 1: one register stage in front of every multiplier (operands and valid, placed beside it), so
    //               the boundary register res_q -> multiplier wire is its own cycle.  +1 cycle per ME op.
    //   AM_SPLIT 1: each argmax node compares in one cycle and selects in the next (two kept select copies).
    //               +1 cycle per level (LW levels) on the argmax top only.
    //   S5_CTL   1: the scale-request range test d > 0 is registered at D1 from its own adders (d - 1 >= 0), and
    //               each bank's capture select drives the column OR through 8 kept copies of 32 loads.  0 cycles.
    parameter integer IN_STAGE = 0,
    parameter integer AM_SPLIT = 0,
    //   SCALE_PAIR 1: each column's bank OR is registered per bank pair (south / north) before m5, a wire stage
    //               across the column height; the request then leads by LEAD = 9 (the tag is a tap of the top's
    //               s3 tag line, available that early -- header 1.), so an op gains no cycle.  res_in is due
    //               LEAD cycles after its tag, as before.
    parameter integer S5_CTL = 0,
    parameter integer SCALE_PAIR = 0,
    //   OREG 1 (owner margin rule 2026-10-06): every result / argmax output leaves through one more register, a kept
    //               per-bit module (ot_qwen_slab_pg_oreg1, SYNTH_KEEP_MODULES) the placer puts at the output pin.
    //               +1 cycle per ME op on the result path (values unchanged).
    parameter integer OREG = 0,
    //   MUL_KCP > 1 (margin m3 2026-10-06): the multiplier's C1 operand register as MUL_KCP kept copies (ot_hdc_fp32_mul_lat
    //               KCP), so the partial-product broadcast is local.  No cycle; values unchanged.
    parameter integer MUL_KCP = 1,
    //   BANDF 1 (qwen-band-integrate 2026-10-08, r21m band-lane spine): GID is the group's SLOT p = 8b + k (band b's
    //               slab, slot k) and the group it holds depends on the op's split (ot_qfd_band_lanes frame):
    //               g = b * 2^(TCUT+3-s) + k (k < 2^(TCUT+3-s)) at s <= TCUT+3, else g = k on band 0 (k < GT >> s).
    //               The row-count constants, the scale address term g*IL, the row base g*W*IL, g*ots and the in-range
    //               test are per-split constants selected by the registered split at D1 (one constant multiplier per
    //               split SMIN..SMAX).  0 cycles; values = the base's for group g.  The scale ROM holds, per matrix,
    //               the words of the group the slot carries at that matrix's split (the same count as before).
    parameter integer BANDF = 0,
    parameter integer TCUT = 7,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11
) (
    input wire [6:0]         gid, // static group identity, captured at the face
    input  wire              clk,
    input  wire              rst_n,
    // block word in (the block's forwarded clock) and on to the tree top
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
    output wire core_gre1,
    output wire [AW-1:0] core_addr1,
    input wire [COLS*256-1:0] col_m5,
    output wire core_rs0,
    output wire [W-1:0] lane_v, lane_ws,
    output wire [W*32-1:0] lane_a,
    output wire [255:0] lane_s,
    input wire [W*32-1:0] lane_y,
    input wire [W-1:0] lane_vo,
    input wire [2*W-1:0] lane_err);
    localparam integer LW = $clog2(W);
    localparam integer BPC = SCALE_BANKS / COLS;
    localparam integer LEAD = 8 + SCALE_PAIR; // tag pins -> multiplier input (see header, 1.)
    localparam integer DW = 20;               // signed width of the row-count differences
    localparam integer KR = 1 + 1 + 1 + 1 + 1 + 1 + W + AW + NW;   // tag carried past the request stage

    // ---- reset distribution: the pin's reset, registered, then one copy per consumer cluster ------------
    wire rs0, rs, rs_bw, bw_rs;
    ot_qwen_slab_pg_rcopy #(.AW(1)) u_rs0 (.clk(clk), .gre(rst_n), .addr(1'b0), .gre_q(rs0), .addr_q());
    ot_qwen_slab_pg_rcopy #(.AW(1)) u_rs  (.clk(clk), .gre(rs0), .addr(1'b0), .gre_q(rs), .addr_q());
    ot_qwen_slab_pg_rcopy #(.AW(1)) u_rsb (.clk(clk), .gre(rs0), .addr(1'b0), .gre_q(rs_bw), .addr_q());

    // ---- boundary registers (cycle 1) ---------------------------------------------------------------
    reg [6:0] t_gid;
    always @(posedge clk) t_gid <= gid;
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
    // BANDF: the group held at split s (constant per instance and split), its in-range flag
    localparam integer TB = TCUT + 3;
    wire [DW-1:0] CDN, CDL;
    wire [AW-1:0] CSB;
    wire [NW-1:0] CRB;
    wire [AW-1:0] gots;
    wire          gok;
    // Runtime group strap keeps ONE physical core view for every die group; all products are exact integers.
    wire [AW-1:0] gid_ext = {{(AW-7){1'b0}}, t_gid};
    wire [AW-1:0] group_id = (BANDF == 0) ? gid_ext :
        ((t_split <= TCUT+3) ? (((gid_ext >> 3) << (TCUT+3-t_split)) + (gid_ext & 7)) : (gid_ext & 7));
    assign CDN = 1 - group_id * W * IL;
    assign CDL = 1 - group_id * W;
    assign CSB = group_id * IL;
    assign CRB = group_id * W * IL;
    assign gok = (BANDF == 0) ? (gid_ext < (GT >> t_split)) :
        ((t_split < SMIN || t_split > SMAX) ? 1'b0 :
          ((t_split <= TCUT+3) ? (((gid_ext & 7) >> (TCUT+3-t_split)) == 0) :
             ((gid_ext >> 3) == 0 && (gid_ext & 7) < (GT >> t_split))));
    assign gots = t_ots * group_id;
    wire [DW-1:0] dn, dl;
    wire [DW-1:0] nb_ext = {{(DW-NW-1){1'b0}}, t_nb};
    wire [DW-1:0] lb_ext = {{(DW-NW-1){1'b0}}, t_lb};
    wire [DW-1:0] nout_ext = {{(DW-NW-1){1'b0}}, t_nout};
    ot_qwen_slab_pg_add3 #(.W(DW)) u_dn (.a(nout_ext), .b(~nb_ext), .c(CDN), .s(dn));
    ot_qwen_slab_pg_add3 #(.W(DW)) u_dl (.a(nout_ext), .b(~lb_ext), .c(CDL), .s(dl));
    wire [AW-1:0] sb, ots95;
    ot_qwen_slab_pg_add3 #(.W(AW)) u_sb (.a(t_sbase), .b({{(AW-NW-1+LW){1'b0}}, t_nb[NW:LW]}), .c(CSB), .s(sb));
    wire [NW-1:0] rb16;
    ot_hdc_ksadd_k #(.W(NW)) u_rb (.a(t_nb[NW-1:0]), .b(CRB), .cin(1'b0), .s(rb16), .cout());
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
        d_portok <= gok;
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
    localparam integer KD = LEAD - 2 + 1; // one clock at the scale-return capture face
    wire [KR-1:0] m_tag, r_tag;
    localparam integer XL = MUL_LAT + IN_STAGE + 1; // one clock at the multiplier-return capture face   // multiplier input -> result
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
    // HIER (qwen-tp8/slab3 2026-10-12): each macro column (R2 copy, 4 x R3 decode + ROM + C4 capture, the M5 merge)
    // is ONE hardened sub-tile ot_qwen_slab_pg_col (own pin-flop row, own local clock root), replicated COLS times;
    // its output m5 is registered at its face.  The bank index BK = c*BPC + b is now the column id on cid pins (tied).
    reg [COLS*256-1:0] col_capture;
    always @(posedge clk) col_capture <= col_m5;
    wire [255:0] colq [0:COLS-1];
    genvar c, b, si;
    assign core_gre1 = gre1;
    assign core_addr1 = addr1;
    generate for (c=0; c<COLS; c=c+1) begin : g_col_return
        assign colq[c] = col_capture[256*c +: 256];
    end endgenerate
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
    // HIER (qwen-tp8/slab3): the 16 multiplier lanes are 4 hardened lane sub-tiles ot_qwen_slab_pg_lanes (4 lanes each:
    // reset copy, IN_STAGE operand registers at the face, ot_hdc_fp32_mul_lat), replicated W/4 times.  The per-lane
    // valid/select copy u_tc stays in the cluster (a register at the sub-tile's face); the operand select moves from the
    // cluster side of the IN_STAGE register to the sub-tile side (same function, same cycle).
    localparam integer LN = 4;
    wire [W-1:0]   l_vv, l_wsv;
    wire [2*W-1:0] errv;
    wire [W-1:0]   vov;
    generate
        for (si = 0; si < W; si = si + 1) begin : g_tc
            // == m_v && m_last && m_mask[si] and m_wsrc (vline[KD] = rs ? vline[KD-1] : 0, one edge later)
            ot_qwen_slab_pg_rcopy #(.AW(1)) u_tc (.clk(clk), .gre(rs && vline[KD-1] && e_last && e_mask[si]),
                .addr(e_wsrc), .gre_q(l_vv[si]), .addr_q(l_wsv[si]));
            assign mfault[si] = vov[si] && (errv[2*si +: 2] != 2'd0);
        end
    endgenerate
    assign core_rs0 = rs0;
    assign lane_v = l_vv;
    assign lane_ws = l_wsv;
    reg [W*32-1:0] res_held;
    always @(posedge clk) res_held <= res_q;
    assign lane_a = res_held;
    assign lane_s = m6;
    reg [W*32-1:0] lane_y_capture;
    reg [W-1:0] lane_vo_capture;
    reg [2*W-1:0] lane_err_capture;
    always @(posedge clk) begin
        lane_y_capture <= lane_y;
        lane_vo_capture <= lane_vo;
        lane_err_capture <= lane_err;
    end
    assign scaled = lane_y_capture;
    assign vov = lane_vo_capture;
    assign errv = lane_err_capture;
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
    localparam integer NO = 1 + 1 + AW + W + W*32;
    wire [NO-1:0] o_pre = {ov2, we2, oa2, om2, od2};
    wire [NO-1:0] o_out;
    generate if (OREG != 0) begin : g_oreg
        for (genvar ob = 0; ob < NO; ob = ob + 1) begin : g_b
            ot_qwen_slab_pg_oreg1 u_r (.clk(clk), .d(o_pre[ob]), .q(o_out[ob]));
        end
    end else begin : g_nooreg
        assign o_out = o_pre;
    end endgenerate
    assign {ov, o_we, o_addr, o_mask, o_data} = o_out;

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
    wire [CW+1:0] am_pre = {tv[TL], trm[TL], alv[LV][CW-1:0]};
    wire [CW+1:0] am_out;
    generate if (OREG != 0) begin : g_amreg
        for (genvar ab = 0; ab < CW + 2; ab = ab + 1) begin : g_b
            ot_qwen_slab_pg_oreg1 u_r (.clk(clk), .d(am_pre[ab]), .q(am_out[ab]));
        end
    end else begin : g_noamreg
        assign am_out = am_pre;
    end endgenerate
    assign {am_tv, am_rmax, am_top} = am_out;

endmodule

module ot_qwen_slab_pg_entries #(
    parameter integer W = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer GT = 6144,
    parameter integer GID = 95,
    parameter integer SCALE_BANKS = 16,
    parameter integer COLS = 4,             // macro columns: banks c*BPC .. c*BPC+BPC-1 share a column copy
    parameter integer MUL_LAT = 6,
    parameter integer BW_FIFO = 0,
    // Timing-only options (values and order unchanged; default off = the S3 RTL):
    //   IN_STAGE 1: one register stage in front of every multiplier (operands and valid, placed beside it), so
    //               the boundary register res_q -> multiplier wire is its own cycle.  +1 cycle per ME op.
    //   AM_SPLIT 1: each argmax node compares in one cycle and selects in the next (two kept select copies).
    //               +1 cycle per level (LW levels) on the argmax top only.
    //   S5_CTL   1: the scale-request range test d > 0 is registered at D1 from its own adders (d - 1 >= 0), and
    //               each bank's capture select drives the column OR through 8 kept copies of 32 loads.  0 cycles.
    parameter integer IN_STAGE = 0,
    parameter integer AM_SPLIT = 0,
    //   SCALE_PAIR 1: each column's bank OR is registered per bank pair (south / north) before m5, a wire stage
    //               across the column height; the request then leads by LEAD = 9 (the tag is a tap of the top's
    //               s3 tag line, available that early -- header 1.), so an op gains no cycle.  res_in is due
    //               LEAD cycles after its tag, as before.
    parameter integer S5_CTL = 0,
    parameter integer SCALE_PAIR = 0,
    //   OREG 1 (owner margin rule 2026-10-06): every result / argmax output leaves through one more register, a kept
    //               per-bit module (ot_qwen_slab_pg_oreg1, SYNTH_KEEP_MODULES) the placer puts at the output pin.
    //               +1 cycle per ME op on the result path (values unchanged).
    parameter integer OREG = 0,
    //   MUL_KCP > 1 (margin m3 2026-10-06): the multiplier's C1 operand register as MUL_KCP kept copies (ot_hdc_fp32_mul_lat
    //               KCP), so the partial-product broadcast is local.  No cycle; values unchanged.
    parameter integer MUL_KCP = 1,
    //   BANDF 1 (qwen-band-integrate 2026-10-08, r21m band-lane spine): GID is the group's SLOT p = 8b + k (band b's
    //               slab, slot k) and the group it holds depends on the op's split (ot_qfd_band_lanes frame):
    //               g = b * 2^(TCUT+3-s) + k (k < 2^(TCUT+3-s)) at s <= TCUT+3, else g = k on band 0 (k < GT >> s).
    //               The row-count constants, the scale address term g*IL, the row base g*W*IL, g*ots and the in-range
    //               test are per-split constants selected by the registered split at D1 (one constant multiplier per
    //               split SMIN..SMAX).  0 cycles; values = the base's for group g.  The scale ROM holds, per matrix,
    //               the words of the group the slot carries at that matrix's split (the same count as before).
    parameter integer BANDF = 0,
    parameter integer TCUT = 7,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11
) (
    input wire ck_col0,
    input wire ck_col1,
    input wire ck_col2,
    input wire ck_col3,
    input wire ck_lane0,
    input wire ck_lane1,
    input wire ck_lane2,
    input wire ck_lane3,
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
`ifndef SYNTHESIS
    initial if (BW_FIFO != 0) $fatal(1, "slab entries core supports production BW_FIFO=0; FIFO path requires a separate leaf");
`endif
    assign bw_rdy=1'b0; assign tw_v=1'b0; assign tw_d={W*32{1'b0}};
    assign bw_w_fault=1'b0; assign bw_r_fault=1'b0; assign bw_w_live=1'b0; assign bw_r_live=1'b0;
    localparam integer BPC = SCALE_BANKS / COLS;
    wire [6:0] leaf_gid;
`ifdef OT_SLAB_GID_MUT
    assign leaf_gid = GID[6:0] ^ 7'd1;
`else
    assign leaf_gid = GID[6:0];
`endif
    wire core_gre1, core_rs0;
    wire [AW-1:0] core_addr1;
    wire [COLS*256-1:0] col_m5;
    wire [W-1:0] lane_v, lane_ws, lane_vo;
    wire [W*32-1:0] lane_a, lane_y;
    wire [255:0] lane_s;
    wire [2*W-1:0] lane_err;
    wire [COLS*256-1:0] core_col_m5;
`ifdef OT_SLAB_ENTRIES_MUT
    assign core_col_m5 = {col_m5[COLS*256-1:2],col_m5[0],col_m5[1]};
`else
    assign core_col_m5 = col_m5;
`endif
`ifdef OT_SLAB_PG_CORE_HARD
    ot_qwen_slab_pg_core u_core (
`else
    ot_qwen_slab_pg_core #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .SCALE_BANKS(SCALE_BANKS), .COLS(COLS), .MUL_LAT(MUL_LAT), .BW_FIFO(BW_FIFO), .IN_STAGE(IN_STAGE), .AM_SPLIT(AM_SPLIT), .S5_CTL(S5_CTL), .SCALE_PAIR(SCALE_PAIR), .OREG(OREG), .MUL_KCP(MUL_KCP), .BANDF(BANDF), .TCUT(TCUT), .SMIN(SMIN), .SMAX(SMAX)) u_core (
`endif
        .gid(leaf_gid), .clk(clk), .rst_n(rst_n), .p_v(p_v), .p_last(p_last), .p_oen(p_oen), .p_amax(p_amax), .p_rmax(p_rmax), .p_wsrc(p_wsrc), .p_mmode(p_mmode), .p_split(p_split), .p_nb(p_nb), .p_lb(p_lb), .p_nout(p_nout), .p_sbase(p_sbase), .p_oa(p_oa), .p_ots(p_ots), .res_in(res_in), .o_we(o_we), .o_addr(o_addr), .o_mask(o_mask), .o_data(o_data), .ov(ov), .am_tv(am_tv), .am_top(am_top), .am_rmax(am_rmax), .fault(fault), .core_gre1(core_gre1), .core_addr1(core_addr1), .col_m5(core_col_m5), .core_rs0(core_rs0), .lane_v(lane_v), .lane_ws(lane_ws), .lane_a(lane_a), .lane_s(lane_s), .lane_y(lane_y), .lane_vo(lane_vo), .lane_err(lane_err));
    wire [3:0] col_ck = {ck_col3,ck_col2,ck_col1,ck_col0};
    wire [3:0] lane_ck = {ck_lane3,ck_lane2,ck_lane1,ck_lane0};
    genvar c;
    generate for(c=0;c<COLS;c=c+1) begin:g_col
`ifdef OT_SLAB_PG_HARD
        ot_qwen_slab_pg_col u_col (
`else
        ot_qwen_slab_pg_col #(.AW(AW),.BPC(BPC),.S5_CTL(S5_CTL),.SCALE_PAIR(SCALE_PAIR)) u_col (
`endif
            .clk(col_ck[c]),.gre1(core_gre1),.addr1(core_addr1),.cid(c[3:0]),.m5(col_m5[256*c+:256]));
    end
    for(c=0;c<W/4;c=c+1) begin:g_mul
`ifdef OT_SLAB_PG_HARD
        ot_qwen_slab_pg_lanes u_ln (
`else
        ot_qwen_slab_pg_lanes #(.LN(4),.MUL_LAT(MUL_LAT),.MUL_KCP(MUL_KCP),.IN_STAGE(IN_STAGE)) u_ln (
`endif
            .clk(lane_ck[c]),.rs0(core_rs0),.l_v(lane_v[4*c+:4]),.l_ws(lane_ws[4*c+:4]),.a(lane_a[128*c+:128]),.s(lane_s[64*c+:64]),.y(lane_y[128*c+:128]),.vo(lane_vo[4*c+:4]),.err(lane_err[8*c+:8]));
    end endgenerate
endmodule
