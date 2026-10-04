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
//      M6 feeds the multiplier.  The request therefore leads the result by
//      LEAD = 7 cycles instead of 2.  The request depends only on the
//      instruction tag, which the top already holds that early (pre_tag is a
//      tap of the s3 tag line, SD - LEAD + OD + XDD >= 0 for SD = MUL_LAT +
//      ACC_LAT >= 10), so this adds no cycle to an op.
//   2. Multiplier.  ot_hdc_fp32_mul_lat #(MUL_LAT) in place of ot_hdc_fmul
//      (ot_hdc_fp32_mul_pipe, LAT 5): bit-identical (ot_hdc_fp32_mul_lat ==
//      ot_hdc_fp32_mul_fast, rtl/test/tb_w11_fp32_mul_lat; ot_hdc_fp32_mul_fast
//      == ot_hdc_fp32_mul_pipe, rtl/test/tb_hdc_fastfp_equiv), and LAT 6 is the
//      smallest that closed 0.833 ns at SS alone (w11_fp_latency_sweep); the
//      LAT 5 pipe routes at ~1.0 GHz SS.  MUL_LAT - 5 cycles are added once per
//      ME op (the post-scale is on the op's result path).
//   3. Boundary registers.  Every input is registered once at the element
//      boundary (one of the spine wire stages TWS/ORD the die already counts).
//   4. Tag line.  The instruction tag arrives once (at request time) and is
//      delayed locally to the multiplier and result times; the top carries one
//      shared copy, so this is conservative in area.
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
    parameter integer BW_FIFO = 1
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
    localparam integer LEAD = 7;              // request -> multiplier input (see header, 1.)
    localparam integer TGW = 7 + 4 + 3 * (NW + 1) + 3 * AW;

    // ---- boundary registers ----------------------------------------------------------------------
    reg  rst_q;
    always @(posedge clk) rst_q <= rst_n;     // registered reset release (the element's own)
    wire rs = rst_q;
    reg              t_v;
    reg  [TGW-1:0]   t_tag;
    reg  [W*32-1:0]  res_q;
    always @(posedge clk) begin
        t_v <= rs ? p_v : 1'b0;
        t_tag <= {p_last, p_oen, p_amax, p_rmax, p_wsrc, p_mmode, 1'b0, p_split, p_nb, p_lb, p_nout,
                  p_sbase, p_oa, p_ots};
        res_q <= res_in;
    end

    // ---- tag line: request time (0) -> multiplier time (LEAD) -> result time (LEAD + MUL_LAT) -----
    wire [TGW-1:0] m_tag, r_tag;
    wire [LEAD+MUL_LAT:0] vl;
    reg  [LEAD+MUL_LAT:1] vline;
    always @(posedge clk) vline <= rs ? {vline[LEAD+MUL_LAT-1:1], t_v} : {(LEAD+MUL_LAT){1'b0}};
    assign vl = {vline, t_v};
    ot_hdc_delay #(.W(TGW), .D(LEAD)) u_mt (.clk(clk), .rst_n(rs), .d(t_tag), .q(m_tag));
    ot_hdc_delay #(.W(TGW), .D(MUL_LAT)) u_rt (.clk(clk), .rst_n(rs), .d(m_tag), .q(r_tag));

    // ---- scale request (RTL: pre_scale_active / scale_addr), R1 ----------------------------------
    wire q_last, q_oen, q_amax, q_rmax, q_wsrc, q_mmode, q_pad;
    wire [3:0] q_split;
    wire [NW:0] q_nb, q_lb, q_nout;
    wire [AW-1:0] q_sbase, q_oa, q_ots;
    assign {q_last, q_oen, q_amax, q_rmax, q_wsrc, q_mmode, q_pad, q_split, q_nb, q_lb, q_nout,
            q_sbase, q_oa, q_ots} = t_tag;
    wire [$clog2(GT):0] q_ports = GT >> q_split;
    wire q_active = t_v && q_last && !q_wsrc && (GID < q_ports) &&
        (q_mmode ? (q_lb + GID * W < q_nout) : (q_nb + GID * (W * IL) < q_nout));
    reg          gre1;
    reg [AW-1:0] addr1;
    always @(posedge clk) begin
        gre1 <= rs && q_active;
        addr1 <= !q_active ? q_sbase : q_sbase + (q_nb >> LW) + GID * IL;
    end

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
                reg [255:0] cap4;
                wire [265:0] rd;
                always @(posedge clk) begin
                    sel4 <= ce3;             // with the macro's sampling edge
                    sel5 <= sel4;            // with the capture
                    cap4 <= rd[255:0];
                end
                ot_rom_4096x266_m8 u_rom (.clk(clk), .ce_in(ce3), .addr_in(a3), .rd_out(rd));
                assign cor[b+1] = cor[b] | (cap4 & {256{sel5}});
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
    wire m_last, m_oen, m_amax, m_rmax, m_wsrc, m_mmode, m_pad;
    wire [3:0] m_split;
    wire [NW:0] m_nb, m_lb, m_nout;
    wire [AW-1:0] m_sbase, m_oa, m_ots;
    assign {m_last, m_oen, m_amax, m_rmax, m_wsrc, m_mmode, m_pad, m_split, m_nb, m_lb, m_nout,
            m_sbase, m_oa, m_ots} = m_tag;
    wire m_v = vl[LEAD];
    wire [$clog2(GT):0] m_ports = GT >> m_split;
    wire [W*32-1:0] scaled;
    wire [W-1:0]    mfault;
    generate
        for (si = 0; si < W; si = si + 1) begin : g_mul
            wire active_lane = (GID < m_ports) &&
                (m_mmode ? (m_lb + GID * W + si < m_nout) : (m_nb + GID * (W * IL) + si < m_nout));
            wire [1:0] err;
            wire       vo;
            ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_mul (.clk(clk), .rst_n(rs),
                .valid_in(m_v && m_last && active_lane),
                .a(res_q[32*si +: 32]), .b({m_wsrc ? 16'h3F80 : m6[16*si +: 16], 16'd0}),
                .y(scaled[32*si +: 32]), .err(err), .valid_out(vo));
            assign mfault[si] = vo && (err != 2'd0);
        end
    endgenerate
    reg fault_q;
    always @(posedge clk) fault_q <= rs && (|mfault);
    assign fault = fault_q;

    // ---- results (RTL o_*1 / o_*2), result time ---------------------------------------------------
    wire r_last, r_oen, r_amax, r_rmax, r_wsrc, r_mmode, r_pad;
    wire [3:0] r_split;
    wire [NW:0] r_nb, r_lb, r_nout;
    wire [AW-1:0] r_sbase, r_oa, r_ots;
    assign {r_last, r_oen, r_amax, r_rmax, r_wsrc, r_mmode, r_pad, r_split, r_nb, r_lb, r_nout,
            r_sbase, r_oa, r_ots} = r_tag;
    wire r_v = vl[LEAD + MUL_LAT];
    wire [$clog2(GT):0] r_ports = GT >> r_split;
    reg [W-1:0] r_mask;
    integer ql;
    always @(*) begin
        for (ql = 0; ql < W; ql = ql + 1)
            r_mask[ql] = (GID < r_ports) &&
                (r_mmode ? (r_lb + GID * W + ql < r_nout) : (r_nb + GID * (W * IL) + ql < r_nout));
    end
    reg ov1, ov2, we1, we2;
    reg [AW-1:0] oa1, oa2;
    reg [W-1:0] om1, om2;
    reg [W*32-1:0] od1, od2;
    always @(posedge clk) begin
        ov1 <= rs && r_v && r_last;
        we1 <= rs && r_v && r_last && r_oen && (GID < r_ports);
        ov2 <= rs && ov1;
        we2 <= rs && we1;
        oa1 <= r_oa + GID * r_ots;
        om1 <= r_mask;
        od1 <= scaled;
        oa2 <= oa1; om2 <= om1; od2 <= od1;
    end
    assign ov = ov2; assign o_we = we2; assign o_addr = oa2; assign o_mask = om2; assign o_data = od2;

    // ---- argmax leaves and the group's 4 compare levels (RTL g_leaf / g_alvl) ----------------------
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    localparam integer CW = 1 + 32 + NW;
    localparam integer LV = LW;
    wire [CW*W-1:0] alv [0:LV];
    reg  [LV:0] tv;
    reg  [LV:0] trm;
    always @(posedge clk) begin
        tv  <= rs ? {tv[LV-1:0], r_v && r_last && (r_amax || r_rmax)} : {(LV+1){1'b0}};
        trm <= {trm[LV-1:0], r_rmax};
    end
    genvar e, lv;
    generate
        for (e = 0; e < W; e = e + 1) begin : g_leaf
            reg [CW-1:0] cq;
            wire [NW-1:0] row = r_nb[NW-1:0] + GID * (W * IL) + e;
            always @(posedge clk) cq <= {r_mask[e], okey(scaled[32*e +: 32]), row};
            assign alv[0][CW*e +: CW] = cq;
        end
        for (lv = 1; lv <= LV; lv = lv + 1) begin : g_alvl
            for (e = 0; e < (W >> lv); e = e + 1) begin : g_node
                wire [CW-1:0] x0 = alv[lv-1][CW*(2*e) +: CW];
                wire [CW-1:0] x1 = alv[lv-1][CW*(2*e+1) +: CW];
                wire x0_wins = x0[CW-1] && (!x1[CW-1] || x0[CW-2 -: 32] > x1[CW-2 -: 32] ||
                               (x0[CW-2 -: 32] == x1[CW-2 -: 32] && x0[NW-1:0] < x1[NW-1:0]));
                reg [CW-1:0] cq;
                always @(posedge clk) cq <= x0_wins ? x0 : x1;
                assign alv[lv][CW*e +: CW] = cq;
            end
            if ((W >> lv) < W) begin : g_pad
                assign alv[lv][CW*W-1 : CW*(W >> lv)] = 0;
            end
        end
    endgenerate
    assign am_top = alv[LV][CW-1:0];
    assign am_tv = tv[LV];
    assign am_rmax = trm[LV];

    // ---- block-word crossing FIFO (decision C) ----------------------------------------------------
    generate if (BW_FIFO != 0) begin : g_bw
        ot_meso_fifo #(.W(W*32), .ENABLE(1)) u_bw (
            .wclk(bw_clk), .wrst_n(bw_rst_n), .w_v(bw_v), .w_rdy(bw_rdy), .w_d(bw_d),
            .rclk(clk), .rrst_n(rs), .r_v(tw_v), .r_rdy(tw_rdy), .r_d(tw_d),
            .w_live(bw_w_live), .r_live(bw_r_live), .w_fault(bw_w_fault), .r_fault(bw_r_fault));
    end else begin : g_nobw
        assign bw_rdy = 1'b0; assign tw_v = 1'b0; assign tw_d = {W*32{1'b0}};
        assign bw_w_live = 1'b0; assign bw_r_live = 1'b0; assign bw_w_fault = 1'b0; assign bw_r_fault = 1'b0;
    end endgenerate
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
