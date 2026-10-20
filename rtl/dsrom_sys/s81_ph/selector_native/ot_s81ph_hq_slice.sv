`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// S81-TOPK7 (2026-10-20) HIERARCHICAL-QUARTER slice (opt-in OT_S81PH_SEL_HQ; dsfd_selt_q_hq).  The function, every
// edge and every port timing are those of ot_s81ph_native_sel_slice in the dsfd_selt_q2 configuration (W 16, IW 20,
// K 512, AW 8, DG 8, OD 4, CMP_RETIME 1, MREG 1, PIPE2 1, ILD 1, FIFO_SRAM 1, FAN32 + ACC32, OMERGE 0); see that file
// for the algorithm.  Changes are structural only (0 added edges), one per native-census family of the OMERGE quarter
// (evidence 89ba149e4, lanes/S81-TOPK6.md), so that no driver of the mapped netlist reaches > 32 loads:
//  H1 state machine: one combinational next-state block + the state registers in <= 12-bit groups, each with its OWN
//     registered copy of seg_clr (sc[g] <= c_hclr | init >= 2: = r_hclr | init != 0 on the next edge, reset 1): the
//     old seg_clr net drove 283 synchronous-clear muxes;
//  H2 r1_d (the sweep read register, 592 b): one-hot AND-OR of {i0 lane, mem_rdata} with registered one-hot select
//     copies (rpb / memb, 22 each, D = the next rp_beat / !(rp_beat | tq_fl)): was sq[839]/i0_rp 595/593 + 593;
//  H3 output stage o0 (PIPE2): the data candidates {tq_last, mem_rdata} / {d_fin_push, pend} are registered as two
//     planes and the one-hot AND-OR with registered select copies is AFTER o0 (same edge into the FIFO): was 1184;
//  H4 pend (direct-delivery line): pend_eff = registered capture one edge later + one-hot bypass (exact: pend_eff(t)
//     = original pend(t)), no 592-bit load enable on {rst_n, seg_clr, dmode, ...};
//  H5 mem_wdata: one-hot AND-OR (ingest line / FQ head) with selects built from DISTINCT flops (packer-plane o_v copies,
//     kept head-full copies), and two identical register copies, one per depth bank of macros (wd_in launched beside
//     its macros; mem_wdata1 drives bank 1): was 608;
//  H6 histograms: 2 x ot_s81ph_hq_hist (8 hardened 32-bin banks each); the fine histogram's input mux is selected by
//     kept i1_v copies (exact: i1_v and the pass-2 sweep never overlap; a bank counts only valid beats);
//  H7 packers: ot_s81ph_hq_pack planes (NP 6) with per-plane kept select copies;
//  H8 keys: fkey(v) = {sign-flip of v} except v = -0 (0x8000 -> 0x8000): computed as key' (no zero-detect broadcast) and
//     a per-lane nz (v == 0x8000) override of each compare result against scalar functions of the bound; sign, bound,
//     rem and sw_T are read through kept copies (<= 4 lanes per copy);
//  H9 FQ / OFQ stores: two identical pointer copies drive ot_sram_showahead_1r1w_h2 (hit nets <= 19 flags).
// Resets: the slice's flops reset from rst_n (the quarter's landed reset); datapath registers carry no reset.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_hq_slice #(
    parameter integer W  = 16,
    parameter integer IW = 20,
    parameter integer K  = 512,
    parameter integer AW = 8,
    parameter integer DG = 8,
    parameter integer OD = 4,
    parameter integer KW = 10,
    parameter integer CB = 11,
    parameter integer NP = 6,         // packer planes
    parameter integer MUT = 0         // causal witnesses (each must FAIL the production bench): 1 r1_d memory select
                                      // copy 7 stuck 0; 2 mem_wdata ingest select of group 3 stuck 0; 3 every coarse bank
                                      // reads the wrong group; 4 o0 select copies of group 2 stuck 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  in_valid,
    output wire                  in_ready,
    input  wire                  in_last,
    input  wire [W-1:0]          in_lv,
    input  wire [W*16-1:0]       in_val,
    input  wire [W*IW-1:0]       in_idx,
    input  wire [W*4-1:0]        in_sg,      // kept copies of each lane's sign bit (one per key nibble)
    input  wire [15:0]           c_T,
    input  wire [4*16-1:0]       c_Tc,       // kept copies of c_T, one per 4-lane group
    input  wire [7:0]            c_Bt,
    input  wire [4*8-1:0]        c_Btc,
    input  wire                  c_fclr,
    input  wire [8*4-1:0]        c_cgc,      // kept copies of c_cg / c_fg, one per histogram bank
    input  wire [8*4-1:0]        c_fgc,
    input  wire                  c_ing,
    input  wire                  c_stop,
    input  wire                  c_p2,
    input  wire                  c_p3,
    input  wire                  c_rep,
    input  wire [15:0]           c_st,
    input  wire [KW:0]           c_rem,
    input  wire                  c_hclr,
    output wire [16*(CB+4)-1:0]  s_gc,
    output wire [16*(CB+4)-1:0]  s_gf,
    output wire [16*CB-1:0]      s_bc,
    output wire [16*CB-1:0]      s_bf,
    output wire                  s_last,
    output wire                  s_hfin,
    output wire                  s_stopped,
    output wire                  s_done2,
    output wire                  s_emitted,
    output wire                  s_ovf,
    output reg                   mem_we,
    output reg  [AW-1:0]         mem_waddr,
    output wire [W*(17+IW)-1:0]  mem_wdata,
    output wire [W*(17+IW)-1:0]  mem_wdata1,
    output reg                   mem_re,
    output reg  [AW-1:0]         mem_raddr,
    input  wire [W*(17+IW)-1:0]  mem_rdata,
    output wire                  out_valid,
    input  wire                  out_ready,
    output wire                  out_last,
    output wire [W-1:0]          out_lv,
    output wire [W*16-1:0]       out_val,
    output wire [W*IW-1:0]       out_idx,
    output wire [W-1:0]          out_ninf
);
    localparam integer EW   = 17 + IW;             // lane {lv, value, index}
    localparam integer MW   = W * EW;              // 592
    localparam integer LW   = (W > 1) ? $clog2(W) : 1;
    localparam integer CAPI = 1 << AW;
    localparam [AW:0]  CAP  = CAPI[AW:0];
    localparam integer FW   = (DG > 1) ? $clog2(DG) : 1;
    localparam integer OCW  = $clog2(OD + 1);
    localparam integer NG   = 22;                  // one-hot select copies per wide mux (<= 27 bits each)
    localparam integer GB   = (MW + NG - 1) / NG;  // 27
    localparam integer GBO  = (MW + 1 + NG - 1) / NG;
    localparam [2:0] P_ING = 3'd0, P_STOP = 3'd1, P_P2 = 3'd2, P_P3 = 3'd3, P_EM = 3'd4, P_DONE = 3'd5;
    localparam [2:0] SW_IDLE = 3'd0, SW_RD = 3'd1, SW_FL = 3'd2, SW_DR = 3'd3, SW_WB = 3'd4;
    localparam [1:0] K_GC = 2'd0, K_P2 = 2'd1, K_P3 = 2'd2;
    localparam [2:0] SETTLE = 3'd5;
    genvar gl, gg;
    integer ll;

    // key' = fkey(v) for every v except -0 (0x8000), whose fkey is 0x8000 (nz override below)
    function automatic [15:0] kp(input [15:0] v);
        kp = v[15] ? ~v : {1'b1, v[14:0]};
    endfunction

    // -- command registers (as the original) ------------------------------------------------------------------------
    reg [15:0] r_T, r_st;
    reg [7:0]  r_Bt;
    reg [KW:0] r_rem;
    reg        r_fclr, r_ing, r_stop, r_p2, r_p3, r_rep, r_hclr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            r_fclr <= 1'b0; r_ing <= 1'b0; r_stop <= 1'b0; r_p2 <= 1'b0; r_p3 <= 1'b0; r_rep <= 1'b0; r_hclr <= 1'b0;
            r_T <= 16'h0000;
        end else begin
            r_fclr <= c_fclr; r_ing <= c_ing; r_stop <= c_stop; r_p2 <= c_p2; r_p3 <= c_p3; r_rep <= c_rep;
            r_hclr <= c_hclr; r_T <= c_T;
        end
    end
    always @(posedge clk) begin r_st <= c_st; r_Bt <= c_Bt; r_rem <= c_rem; end

    reg [2:0] init;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) init <= 3'd7;
        else if (init != 0) init <= init - 1'b1;
    end
    wire seg_clr = r_hclr || (init != 0);
    // H1: registered seg_clr copies (identical to seg_clr every edge)
    localparam integer NSC = 48;
    wire [NSC-1:0] sc;
    (* keep = "true" *) reg [2:0] init_b;           // identical copy of init (second seg_clr copy source)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) init_b <= 3'd7;
        else if (init_b != 0) init_b <= init_b - 1'b1;
    end
    wire sc_d0 = c_hclr || (init > 3'd1);
    wire sc_d1 = c_hclr || (init_b > 3'd1);
    generate for (gg = 0; gg < NSC; gg = gg + 1) begin : g_sc
        (* keep = "true" *) reg r;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) r <= 1'b1;
            else r <= (gg < NSC/2) ? sc_d0 : sc_d1;
        assign sc[gg] = r;
    end endgenerate

    // -- state (registered in H1 groups below) ------------------------------------------------------------------------
    wire [2:0]  ph, sw_st, ph_b, sw_st_b;
    wire [1:0]  sw_k, sw_seg, ab_seg, sw_k_b;
    wire [AW:0] a_end_f;
    wire        sw_rp, sw_all, ab;
    wire [AW:0] rd, w, rd_ab, rd_stop, a_end, b_st, b_end, y_st, head;
    wire [15:0] sw_T, t_last;
    wire        ovf, last_seen, ing_fl_done;
    wire [4:0]  infl;
    wire [AW:0] e_rd;
    wire [2:0]  e_infl;
    wire        p2h, dmode, pend_v;
    wire [AW:0] dcnt;
    wire        e_go, e_empty;
    wire [KW:0] rem;
    wire        q_s_last, q_s_hfin, q_s_stopped, q_s_done2, q_s_emitted, q_s_ovf;
    assign s_last = q_s_last; assign s_hfin = q_s_hfin; assign s_stopped = q_s_stopped;
    assign s_done2 = q_s_done2; assign s_emitted = q_s_emitted; assign s_ovf = q_s_ovf;

    // -- input ----------------------------------------------------------------------------------------------------------
    wire rp_acc = (sw_st == SW_RD) && sw_rp;
    assign in_ready = (init == 0) && !last_seen && (((ph == P_ING) && r_ing && !r_stop) || rp_acc);
    wire acc = in_valid && in_ready;
    reg            i0_v, i0_last, i0_rp;
    reg [W-1:0]    i0_lv;
    reg [W*16-1:0] i0_val;
    reg [W*IW-1:0] i0_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i0_v <= 1'b0;
        else i0_v <= acc;
    end
    always @(posedge clk) begin
        i0_last <= in_last; i0_lv <= in_lv; i0_val <= in_val; i0_idx <= in_idx; i0_rp <= rp_acc;
    end

    // -- ingest: filter (CMP_RETIME, H8) ----------------------------------------------------------------------------
    wire [W-1:0]    i1_s_d, i1_fm_d;
    wire [W*16-1:0] i1_k_d;
    wire [W*EW-1:0] i0_lane;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_i1
            // i1_k = fkey(i0_val): key' with the -0 override
            wire [15:0] v0  = i0_val[16*gl +: 16];
            wire        nz0 = (v0 == 16'h8000);
            assign i1_k_d[16*gl +: 16] = nz0 ? 16'h8000 : kp(v0);
            // compare nibbles on the edge in_val becomes i0_val (as the original CMP_RETIME): key' nibble n uses
            // sign copy n, the bound copy of the lane's 4-lane group; nz lanes take the 0x8000 results
            wire [15:0] vx  = in_val[16*gl +: 16];
            wire [15:0] cT  = c_Tc[16*(gl / 4) +: 16];
            wire [7:0]  cB  = c_Btc[8*(gl / 4) +: 8];
            wire        nzx = (vx == 16'h8000);
            wire [15:0] ik;
            assign ik[15]   = ~in_sg[4*gl + 3];
            assign ik[14:12] = vx[14:12] ^ {3{in_sg[4*gl + 3]}};
            assign ik[11:8] = vx[11:8] ^ {4{in_sg[4*gl + 2]}};
            assign ik[7:4]  = vx[7:4]  ^ {4{in_sg[4*gl + 1]}};
            assign ik[3:0]  = vx[3:0]  ^ {4{in_sg[4*gl + 0]}};
            reg [3:0] cmp_gt, cmp_eq;
            reg hi_match;
            integer nib;
            always @(posedge clk) begin
                for (nib = 0; nib < 4; nib = nib + 1) begin
                    cmp_gt[nib] <= nzx ? ((nib == 3) ? (4'h8 > cT[15:12]) : 1'b0) : (ik[4*nib +: 4] > cT[4*nib +: 4]);
                    cmp_eq[nib] <= nzx ? ((nib == 3) ? (cT[15:12] == 4'h8) : (cT[4*nib +: 4] == 4'h0))
                                       : (ik[4*nib +: 4] == cT[4*nib +: 4]);
                end
                hi_match <= nzx ? (cB == 8'h80) : (ik[15:8] == cB);
            end
            wire ge_lo = cmp_gt[1] || (cmp_eq[1] && (cmp_gt[0] || cmp_eq[0]));
            wire ge = cmp_gt[3] || (cmp_eq[3] && cmp_gt[2]) || (cmp_eq[3] && cmp_eq[2] && ge_lo);
            assign i1_s_d[gl] = i0_lv[gl] && ge;
            assign i1_fm_d[gl] = i0_lv[gl] && ge && hi_match;
            assign i0_lane[EW*gl +: EW] = {i0_lv[gl], i0_val[16*gl +: 16], i0_idx[IW*gl +: IW]};
        end
    endgenerate
    reg            i1_v, i1_fl;
    reg [W-1:0]    i1_fm;
    reg [W*16-1:0] i1_k;
    reg [W*EW-1:0] i1_p;
    wire i_ing = i0_v && !i0_rp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin i1_v <= 1'b0; i1_fl <= 1'b0; end
        else begin i1_v <= i_ing; i1_fl <= i_ing && i0_last; end
    end
    always @(posedge clk) begin i1_fm <= i1_fm_d; i1_k <= i1_k_d; i1_p <= i0_lane; end
    // kept copies: i1_s per packer plane + one for the coarse banks; i1_v per packer plane, for the banks and as the
    // fine-histogram input selects (HFS of each polarity)
    localparam integer HFS = 6;
    wire [NP*W-1:0] i1_s_pl, i1_s_plg, i1_s_plh;
    wire [W-1:0]    i1_s_hc;
    wire [NP-1:0]   i1_v_pl, i1_fl_pl;
    wire [HFS-1:0]  hf_s1, hf_s0;
    generate
        for (gg = 0; gg < NP; gg = gg + 1) begin : g_i1c
            (* keep = "true" *) reg [W-1:0] s, sg, sh;
            (* keep = "true" *) reg v, f;
            always @(posedge clk) begin s <= i1_s_d; sg <= i1_s_d; sh <= i1_s_d; end
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin v <= 1'b0; f <= 1'b0; end else begin v <= i_ing; f <= i_ing && i0_last; end
            assign i1_s_pl[W*gg +: W] = s; assign i1_s_plg[W*gg +: W] = sg; assign i1_s_plh[W*gg +: W] = sh; assign i1_v_pl[gg] = v; assign i1_fl_pl[gg] = f;
        end
        for (gg = 0; gg < HFS; gg = gg + 1) begin : g_hfs
            (* keep = "true" *) reg a, b;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin a <= 1'b0; b <= 1'b1; end else begin a <= i_ing; b <= !i_ing; end
            assign hf_s1[gg] = a; assign hf_s0[gg] = b;
        end
    endgenerate
    (* keep = "true" *) reg [W-1:0] i1_s_hcr;
    always @(posedge clk) i1_s_hcr <= i1_s_d;
    assign i1_s_hc = i1_s_hcr;

    // -- sweep read path ----------------------------------------------------------------------------------------------
    reg          t1_v, t1_fl, t1_em, t1_last, t2_v, t2_fl, t2_em, t2_last;
    reg          t3_v, t3_fl, t3_em, t3_last;
    (* keep = "true" *) reg t3b_v, t3b_em;       // distinct copy for the second o0 select source
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin t3_v <= 1'b0; t3_fl <= 1'b0; t3_em <= 1'b0; t3b_v <= 1'b0; t3b_em <= 1'b0; end
        else begin t3_v <= t2_v; t3_fl <= t2_fl; t3_em <= t2_em; t3b_v <= t2_v; t3b_em <= t2_em; end
    always @(posedge clk) t3_last <= t2_last;
    wire tq_v = t3_v, tq_fl = t3_fl, tq_em = t3_em, tq_last = t3_last;
    reg          r1_v, r1_fl;
    wire [MW-1:0] r1_d;
    wire rp_beat = i0_v && i0_rp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r1_v <= 1'b0; r1_fl <= 1'b0; t2_v <= 1'b0; t2_fl <= 1'b0; t2_em <= 1'b0; end
        else begin
            t2_v <= t1_v; t2_fl <= t1_fl; t2_em <= t1_em;
            r1_v  <= (tq_v && !tq_em) || tq_fl || rp_beat;
            r1_fl <= tq_fl || (rp_beat && i0_last);
        end
    end
    always @(posedge clk) t2_last <= t1_last;
    // H2: r1_d = rp_beat ? i0_lane : tq_fl ? 0 : mem_rdata, as a one-hot AND-OR with registered select copies
    wire rpd = acc && rp_acc;                    // rp_beat on the next edge
    wire mbd = !rpd && !t2_fl;                   // memory line on the next edge (tq_fl = t3_fl <= t2_fl)
    wire [NG-1:0] rpb_v, memb_v;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_r1
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        (* keep = "true" *) reg rpb, memb;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rpb <= 1'b0; memb <= 1'b1; end
            else begin rpb <= rpd; memb <= (MUT == 1 && gg == 7) ? 1'b0 : mbd; end
        assign rpb_v[gg] = rpb; assign memb_v[gg] = memb;
        reg [SW-1:0] q;
        always @(posedge clk) q <= (i0_lane[LO +: SW] & {SW{rpb}}) | (mem_rdata[LO +: SW] & {SW{memb}});
        assign r1_d[LO +: SW] = q;
    end endgenerate
    // tsw: the sweep bound, registered (PIPE2), with kept copies per 4-lane group
    wire [15:0] tsw_c = (sw_k_b == K_GC) ? r_T : sw_T;
    wire [4*16-1:0] tswc;
    wire [7:0]  swTh [0:1];                      // lagging sw_T[15:8] copies (pass-2 bucket; see header)
    generate for (gg = 0; gg < 4; gg = gg + 1) begin : g_tsw
        (* keep = "true" *) reg [15:0] r;
        always @(posedge clk) r <= tsw_c;
        assign tswc[16*gg +: 16] = r;
    end
    for (gg = 0; gg < 2; gg = gg + 1) begin : g_swth
        (* keep = "true" *) reg [7:0] r;
        always @(posedge clk) r <= sw_T[15:8];
        assign swTh[gg] = r;
    end endgenerate
    // r1_d per-lane sign copies (same D as the r1_d sign register)
    wire [W*2-1:0] r1sg;
    generate for (gl = 0; gl < W; gl = gl + 1) begin : g_r1sg
        localparam integer SB = EW*gl + IW + 15;
        localparam integer GS = SB / GB;
        localparam integer GO = SB - GS * GB;
        (* keep = "true" *) reg [1:0] r;
        always @(posedge clk) r <= {2{(i0_lane[SB] & rpb_v[GS]) | (mem_rdata[SB] & memb_v[GS])}};
        assign r1sg[2*gl +: 2] = r;
    end endgenerate
    wire [W-1:0]    c1_gt_d, c1_eq_d, p2_en;
    wire [W*8-1:0]  p2_dg;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_c1
            wire        lv = r1_d[EW*gl + EW - 1];
            wire [15:0] v  = r1_d[EW*gl + IW +: 16];
            wire        nz = (v == 16'h8000);
            wire [15:0] t  = tswc[16*(gl / 4) +: 16];
            wire [7:0]  th = swTh[gl / 8];
            wire [15:0] k;
            assign k[15]   = ~r1sg[2*gl + 1];
            assign k[14:8] = v[14:8] ^ {7{r1sg[2*gl + 1]}};
            assign k[7:0]  = v[7:0]  ^ {8{r1sg[2*gl + 0]}};
            assign c1_gt_d[gl] = lv && (nz ? (16'h8000 > t) : (k > t));
            assign c1_eq_d[gl] = lv && (nz ? (t == 16'h8000) : (k == t));
            assign p2_en[gl]   = lv && (nz ? (th == 8'h80) : (k[15:8] == th));
            assign p2_dg[8*gl +: 8] = nz ? 8'h00 : k[7:0];
        end
    endgenerate
    reg            c1_v, c1_fl, c2_v, c2_fl, c3_v, c3_fl;
    reg [W-1:0]    c1_gt, c1_eq, c2_gt, c2_eq;
    reg [W*EW-1:0] c1_p, c2_p, c3_p;
    reg [W*(LW+1)-1:0] c2_pre;
    reg [LW:0]     c2_cnt;
    wire [W*(LW+1)-1:0] eq_inc;
    ot_s81ph_native_sel_prefix #(.N(W), .OW(LW + 1)) u_eqpre (.x(c1_eq), .y(eq_inc));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c1_v <= 1'b0; c1_fl <= 1'b0; c2_v <= 1'b0; c2_fl <= 1'b0; c3_v <= 1'b0; c3_fl <= 1'b0; end
        else begin
            c1_v <= r1_v; c1_fl <= r1_fl; c2_v <= c1_v; c2_fl <= c1_fl; c3_v <= c2_v; c3_fl <= c2_fl;
        end
    end
    always @(posedge clk) begin
        c1_gt <= c1_gt_d; c1_eq <= c1_eq_d; c1_p <= r1_d;
        c2_gt <= c1_gt; c2_eq <= c1_eq; c2_p <= c1_p;
        c2_pre <= {eq_inc[(LW+1)*(W-1)-1:0], {(LW+1){1'b0}}};
        c2_cnt <= eq_inc[(LW+1)*(W-1) +: LW+1];
        c3_p <= c2_p;
    end
    // c3_sel: one kept copy per packer plane (same D)
    wire [KW:0] rem_c [0:1];
    wire [W-1:0] c3_sel_d;
    generate for (gl = 0; gl < W; gl = gl + 1) begin : g_c3d
        wire [KW:0] rr = rem_c[gl / 8];
        assign c3_sel_d[gl] = c2_gt[gl] || (c2_eq[gl] && (sw_all || ({{(KW-LW){1'b0}}, c2_pre[(LW+1)*gl +: LW+1]} < rr)));
    end endgenerate
    wire [NP*W-1:0] c3_sel_pl, c3_sel_plg, c3_sel_plh;
    wire [NP-1:0]   c3_v_pl, c3_fl_pl;
    generate for (gg = 0; gg < NP; gg = gg + 1) begin : g_c3c
        (* keep = "true" *) reg [W-1:0] s, sg, sh;
        (* keep = "true" *) reg v, f;
        always @(posedge clk) begin s <= c3_sel_d; sg <= c3_sel_d; sh <= c3_sel_d; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin v <= 1'b0; f <= 1'b0; end else begin v <= c2_v; f <= c2_fl; end
        assign c3_sel_pl[W*gg +: W] = s; assign c3_sel_plg[W*gg +: W] = sg; assign c3_sel_plh[W*gg +: W] = sh; assign c3_v_pl[gg] = v; assign c3_fl_pl[gg] = f;
    end endgenerate

    // -- histograms (H6) ------------------------------------------------------------------------------------------------
    wire p2m = (sw_k_b == K_P2) && (sw_st_b != SW_IDLE);
    wire sw_start;
    wire hc_busy, hf_busy;
    wire [W*8-1:0] hi_dg, lo_dg;
    generate for (gl = 0; gl < W; gl = gl + 1) begin : g_dg
        assign hi_dg[8*gl +: 8] = i1_k[16*gl + 8 +: 8];
        assign lo_dg[8*gl +: 8] = i1_k[16*gl +: 8];
    end endgenerate
    // per-bank clears from distinct seg_clr copies (a bank's clear pin feeds its 17 kept clear registers)
    wire p2q, p3q;
    wire f_clr_x = r_fclr || (sw_start && p2q);
    wire [7:0] hc_clr = sc[NSC/2 +: 8];
    wire [7:0] hf_clr = sc[NSC/2 + 8 +: 8] | {8{f_clr_x}};
    ot_s81ph_hq_hist #(.MUT((MUT == 3) ? 1 : 0)) u_hc (
        .clk(clk), .rst_n(rst_n), .clr(hc_clr), .i_v(i1_v), .i_en(i1_s_hc), .i_dg(hi_dg), .gsel_d(c_cgc),
        .gsum(s_gc), .gbin(s_bc), .busy(hc_busy));
    // fine input: i1_v ? {i1_fm, lo digits} : {p2_en, p2 digits}; valid = i1_v | (p2m & r1_v) (exact, see header)
    wire [W+W*8-1:0] hf_a = {i1_fm, lo_dg}, hf_b = {p2_en, p2_dg}, hf_x;
    localparam integer HB = (W + W*8 + HFS - 1) / HFS;
    generate for (gg = 0; gg < HFS; gg = gg + 1) begin : g_hfx
        localparam integer LO = gg * HB;
        localparam integer SW = (W + W*8 - LO < HB) ? (W + W*8 - LO) : HB;
        assign hf_x[LO +: SW] = (hf_a[LO +: SW] & {SW{hf_s1[gg]}}) | (hf_b[LO +: SW] & {SW{hf_s0[gg]}});
    end endgenerate
    ot_s81ph_hq_hist u_hf (
        .clk(clk), .rst_n(rst_n), .clr(hf_clr), .i_v(i1_v || (p2m && r1_v)), .i_en(hf_x[W*8 +: W]),
        .i_dg(hf_x[0 +: W*8]), .gsel_d(c_fgc), .gsum(s_gf), .gbin(s_bf), .busy(hf_busy));

    // -- packers (H7) ---------------------------------------------------------------------------------------------------
    wire [NP-1:0]   pi_vp, ps_vp;
    wire            pi_v = pi_vp[0], ps_v = ps_vp[0];
    wire            pi_bv, pi_fl, ps_bv, ps_fl;
    wire [W-1:0]    pi_lv, ps_lv;
    wire [W*EW-1:0] pi_line, ps_line;
    ot_s81ph_hq_pack #(.W(W), .PW(EW), .NP(NP)) u_pi (
        .clk(clk), .rst_n(rst_n), .i_v(i1_v_pl), .i_fl(i1_fl_pl), .i_sel(i1_s_pl), .i_selg(i1_s_plg), .i_selh(i1_s_plh), .i_p(i1_p),
        .o_v(pi_vp), .o_lv(pi_lv), .o_line(pi_line), .o_bv(pi_bv), .o_fl(pi_fl));
    ot_s81ph_hq_pack #(.W(W), .PW(EW), .NP(NP)) u_ps (
        .clk(clk), .rst_n(rst_n), .i_v(c3_v_pl), .i_fl(c3_fl_pl), .i_sel(c3_sel_pl), .i_selg(c3_sel_plg), .i_selh(c3_sel_plh), .i_p(c3_p),
        .o_v(ps_vp), .o_lv(ps_lv), .o_line(ps_line), .o_bv(ps_bv), .o_fl(ps_fl));

    // -- write-back queue and the write port (H5, H9) ------------------------------------------------------------------
    wire [W*EW-1:0] fq_head;
    reg [FW-1:0]   fwp, frp;
    (* keep = "true" *) reg [FW-1:0] fwp_b, frp_b;
    reg [FW:0]     fcnt;
    reg            wpend;
    wire discard  = sw_rp && (sw_k == K_P2);
    wire f_push   = ps_v && !discard;
    wire f_push_b = ps_vp[1] && !discard;
    wire ing_wr   = pi_v && !head[AW];
    wire f_pop    = (fcnt != 0) && !ing_wr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin fwp <= 0; frp <= 0; fwp_b <= 0; frp_b <= 0; fcnt <= 0; mem_we <= 1'b0; wpend <= 1'b0; end
        else begin
            if (f_push)   fwp   <= (fwp == DG - 1) ? {FW{1'b0}} : fwp + 1'b1;
            if (f_push_b) fwp_b <= (fwp_b == DG - 1) ? {FW{1'b0}} : fwp_b + 1'b1;
            if (f_pop)    frp   <= (frp == DG - 1) ? {FW{1'b0}} : frp + 1'b1;
            if (f_pop)    frp_b <= (frp_b == DG - 1) ? {FW{1'b0}} : frp_b + 1'b1;
            fcnt <= fcnt + {{FW{1'b0}}, f_push} - {{FW{1'b0}}, f_pop};
            mem_we <= ing_wr || f_pop;
            wpend <= f_pop;
        end
    end
    wire [FW-1:0] next_rp   = f_pop ? ((frp == DG-1) ? {FW{1'b0}} : frp+1'b1) : frp;
    wire [FW-1:0] next_rp_b = f_pop ? ((frp_b == DG-1) ? {FW{1'b0}} : frp_b+1'b1) : frp_b;
    ot_sram_showahead_1r1w_h2 #(.W(W*EW), .AW(FW)) u_fq (
        .clk(clk), .rst_n(rst_n), .we({f_push_b, f_push}), .wa({fwp_b, fwp}), .wd(ps_line), .ra({next_rp_b, next_rp}),
        .q(fq_head));
    // mem_wdata = ing_wr ? pi_line : fq_head, one-hot AND-OR: group g selects with
    //   sp = pi_v(plane a) & !full_g,  sq = !pi_v(plane b) | full_g   (a != b: distinct flops, not one net + inverter)
    wire [NG-1:0] hfull;                           // kept copies of head[AW] (defined with the state groups)
    reg  [MW-1:0] wd0, wd1;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_wd
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        localparam integer PA = gg % NP, PB = (gg + 1) % NP;
        wire sp = (MUT == 2 && gg == 3) ? 1'b0 : (pi_vp[PA] && !hfull[gg]);
        wire sq = !pi_vp[PB] || hfull[gg];
        wire [SW-1:0] d = (pi_line[LO +: SW] & {SW{sp}}) | (fq_head[LO +: SW] & {SW{sq}});
        always @(posedge clk) begin wd0[LO +: SW] <= d; wd1[LO +: SW] <= d; end
    end endgenerate
    assign mem_wdata = wd0;
    assign mem_wdata1 = wd1;
    always @(posedge clk) begin
        mem_waddr <= ing_wr ? head[AW-1:0] : w[AW-1:0];
    end

    // -- sweep engine: combinational next state (H1) ---------------------------------------------------------------------
    wire [AW:0] a_end_e;                           // kept copy of a_end for the emit side
    wire [1:0]  sw_seg_l;                          // kept copy of sw_seg for lim
    wire [AW:0] lim = (sw_seg_l == 2'd0) ? a_end : (sw_seg_l == 2'd1) ? b_end : head;
    wire have      = rd < lim;
    wire credit    = (sw_k != K_GC) || (({{(4-FW){1'b0}}, fcnt} + infl) < DG);
    wire abort_now = (sw_k == K_GC) && r_stop;
    wire rd_issue  = (sw_st == SW_RD) && !sw_rp && !abort_now && have && credit;
    wire fl_issue  = (sw_st == SW_FL) && credit;
    wire sw_fin    = (sw_st == SW_WB) && (fcnt == 0) && !f_push && !wpend;
    wire gc_go     = (ph == P_ING) && r_ing && !r_stop && !seg_clr && (sw_st == SW_IDLE) &&
                     ((head != y_st) || (r_T != t_last));
    assign sw_start = (sw_st == SW_IDLE) && !seg_clr && (gc_go || (((ph == P_STOP) && (p2q || p3q))));
    wire gc_go_b    = (ph_b == P_ING) && r_ing && !r_stop && !sc[NSC-4] && (sw_st_b == SW_IDLE) &&
                      ((head != y_st) || (r_T != t_last));
    wire sw_start_b = (sw_st_b == SW_IDLE) && !sc[NSC-4] && (gc_go_b || (((ph_b == P_STOP) && (p2q || p3q))));
    reg            o0_v;
    reg [OCW-1:0]  ocnt;
    wire [OCW-1:0] occ = ocnt + {{(OCW-1){1'b0}}, o0_v};
    wire em_issue = (ph_b == P_EM) && e_go && (e_rd < a_end_e) &&
                    ({{(8-OCW){1'b0}}, occ} + {5'd0, e_infl} < OD);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            t1_v <= 1'b0; t1_fl <= 1'b0; t1_em <= 1'b0; mem_re <= 1'b0;
        end else begin
            t1_v <= rd_issue || em_issue; t1_fl <= fl_issue; t1_em <= em_issue;
            mem_re <= rd_issue || em_issue;
        end
    end
    // second emit-issue copy (ph / a_end copies) for the read address and t1_last (same value as em_issue)
    wire em_issue_b = (ph == P_EM) && e_go && (e_rd < a_end_f) &&
                      ({{(8-OCW){1'b0}}, occ} + {5'd0, e_infl} < OD);
    always @(posedge clk) begin
        mem_raddr <= em_issue_b ? e_rd[AW-1:0] : rd[AW-1:0];
        t1_last <= em_issue_b && (e_rd + 1'b1 == a_end_f);
    end
    wire [2:0] hf_cnt, hs_cnt;
    wire hs_quiet = (hs_cnt == 0) && !i0_v && !i1_v && !hc_busy && !hf_busy;
    // direct delivery from pass 3
    wire d_room     = (occ < OD);
    wire d_mid      = (sw_k == K_P3) && (sw_st != SW_IDLE) && dmode && f_push && pend_v && d_room;
    wire d_fin_push = sw_fin && (sw_k == K_P3) && dmode && pend_v && d_room;
    wire d_fin      = sw_fin && (sw_k == K_P3) && dmode && (pend_v ? d_room : 1'b1) && (w != 0);
    wire d_push     = d_mid || d_fin_push;
    wire o_last_hd;
    wire out_fire   = (ocnt != 0) && out_ready;

    reg [2:0]  n_ph, n_sw_st;
    reg [1:0]  n_sw_k, n_sw_seg, n_ab_seg;
    reg        n_sw_rp, n_sw_all, n_ab;
    reg [AW:0] n_rd, n_w, n_rd_ab, n_rd_stop, n_a_end, n_b_st, n_b_end, n_y_st, n_head, n_e_rd, n_dcnt;
    reg [15:0] n_sw_T, n_t_last;
    reg        n_ovf, n_last_seen, n_ing_fl_done, n_p2h, n_dmode, n_pend_v, n_e_go, n_e_empty;
    reg [4:0]  n_infl;
    reg [2:0]  n_e_infl;
    reg [KW:0] n_rem;
    reg        n_s_last, n_s_hfin, n_s_stopped, n_s_done2, n_s_emitted, n_s_ovf;
    reg        cap;                                 // pend capture (H4)
    always @(*) begin
        n_ph = ph; n_sw_st = sw_st; n_sw_k = sw_k; n_sw_seg = sw_seg; n_ab_seg = ab_seg; n_sw_rp = sw_rp;
        n_sw_all = sw_all; n_ab = ab; n_rd = rd; n_w = w; n_rd_ab = rd_ab; n_rd_stop = rd_stop; n_a_end = a_end;
        n_b_st = b_st; n_b_end = b_end; n_y_st = y_st; n_head = head; n_e_rd = e_rd; n_dcnt = dcnt; n_sw_T = sw_T;
        n_t_last = t_last; n_ovf = ovf; n_last_seen = last_seen; n_ing_fl_done = ing_fl_done; n_p2h = p2h;
        n_dmode = dmode; n_pend_v = pend_v; n_e_go = e_go; n_e_empty = e_empty; n_infl = infl; n_e_infl = e_infl;
        n_rem = rem; n_s_last = q_s_last; n_s_hfin = q_s_hfin; n_s_stopped = q_s_stopped; n_s_done2 = q_s_done2;
        n_s_emitted = q_s_emitted; n_s_ovf = q_s_ovf; cap = 1'b0;
        // input bookkeeping
        if (sw_start && (p2q || p3q) && r_rep) n_last_seen = 1'b0;
        else if (acc && in_last) n_last_seen = 1'b1;
        if (pi_fl) n_ing_fl_done = 1'b1;
        if (pi_v) begin
            if (head[AW]) n_ovf = 1'b1;
            else n_head = head + 1'b1;
        end
        if (f_pop) n_w = w + 1'b1;
        n_infl = infl + {4'd0, rd_issue || fl_issue} - {4'd0, ps_bv && !sw_rp};
        if (ph == P_ING && r_stop) n_ph = P_STOP;
        // sweep start
        if (sw_start) begin
            n_sw_st = SW_RD; n_sw_seg = 2'd0; n_rd = 0; n_w = 0; n_ab = 1'b0;
            if (gc_go) begin
                n_sw_k = K_GC; n_sw_rp = 1'b0; n_sw_all = 1'b1;
            end else begin
                n_sw_k = p2q ? K_P2 : K_P3; n_sw_rp = r_rep; n_sw_all = p2q; n_rem = r_rem;
                n_ph = p2q ? P_P2 : P_P3;
                if (p2q) begin n_p2h = 1'b0; end else begin n_dmode = 1'b1; n_dcnt = 0; n_pend_v = 1'b0; end
            end
        end
        if (c2_v && !sw_all) n_rem = (rem > {{(KW-LW){1'b0}}, c2_cnt}) ? rem - {{(KW-LW){1'b0}}, c2_cnt} : {(KW+1){1'b0}};
        case (sw_st)
            SW_RD: begin
                if (sw_rp) begin
                    if (acc && in_last) n_sw_st = SW_DR;
                end else if (abort_now) begin
                    n_ab = 1'b1; n_ab_seg = sw_seg; n_rd_ab = rd; n_sw_st = SW_FL;
                end else if (have) begin
                    if (credit) n_rd = rd + 1'b1;
                end else if (sw_seg == 2'd0) begin
                    n_sw_seg = 2'd1; n_rd = b_st;
                end else if (sw_seg == 2'd1) begin
                    n_sw_seg = 2'd2; n_rd = y_st;
                end else begin
                    n_rd_stop = rd; n_sw_st = SW_FL;
                end
            end
            SW_FL: if (credit) n_sw_st = SW_DR;
            SW_DR: if (ps_fl) n_sw_st = SW_WB;
            SW_WB: if (sw_fin) begin
                n_sw_st = SW_IDLE;
                case (sw_k)
                    K_GC: begin
                        n_a_end = w;
                        if (!ab) begin n_b_st = 0; n_b_end = 0; n_y_st = rd_stop; end
                        else if (ab_seg == 2'd0) begin n_b_st = rd_ab; n_b_end = a_end; end
                        else if (ab_seg == 2'd1) n_b_st = rd_ab;
                        else begin n_b_st = 0; n_b_end = 0; n_y_st = rd_ab; end
                    end
                    K_P2: begin
                        if (!sw_rp) begin n_a_end = w; n_b_st = 0; n_b_end = 0; n_y_st = head; end
                        n_ph = P_STOP;
                    end
                    default: begin
                        n_a_end = w; n_b_st = 0; n_b_end = 0; n_y_st = head;
                        n_ph = P_EM; n_e_rd = dcnt; n_e_go = !d_fin; n_e_empty = (w == 0);
                    end
                endcase
            end
            default: ;
        endcase
        if (sw_k == K_P2 && sw_st != SW_IDLE && r1_v && r1_fl) n_p2h = 1'b1;
        if (p2h && hf_cnt == 0 && !hf_busy && !q_s_done2) n_s_done2 = 1'b1;
        if (d_push) n_dcnt = dcnt + 1'b1;
        if (sw_k == K_P3 && sw_st != SW_IDLE && dmode && f_push) begin
            if (pend_v && !d_room) n_dmode = 1'b0;
            else begin cap = 1'b1; n_pend_v = 1'b1; end
        end
        if (d_fin_push) n_pend_v = 1'b0;
        if (sw_fin && sw_k == K_P3 && dmode && pend_v && !d_room) n_dmode = 1'b0;
        n_e_infl = e_infl + {2'd0, em_issue} - {2'd0, tq_v && tq_em};
        if (em_issue) n_e_rd = e_rd + 1'b1;
        if (ph == P_EM && e_go && (e_rd == a_end_f) && !e_empty) n_e_go = 1'b0;
        if (ph == P_EM && e_empty && occ < OD) begin n_e_empty = 1'b0; n_e_go = 1'b0; end
        if (ph == P_EM && out_fire && o_last_hd) begin n_ph = P_DONE; n_s_emitted = 1'b1; end
        n_s_last    = (ph == P_ING) && (last_seen || (acc && in_last));
        n_s_hfin    = last_seen && hs_quiet;
        n_s_stopped = (ph == P_STOP) && (sw_st == SW_IDLE) && !sw_start && ing_fl_done && hs_quiet && !pi_v;
        n_s_ovf     = ovf || (pi_v && head[AW]);
        // sw_T / t_last: the sweep-start loads, from the state-copy decode (same values as sw_start / gc_go)
        if (sw_start_b) begin
            if (gc_go_b) n_t_last = r_T;
            else n_sw_T = r_st;
        end
    end
    // register groups: {reset value} = {seg_clr value}; one seg_clr copy per <= 12 bits
    localparam integer STW = 3+3+2+2+2+1+1+1 + 9*12 + 16*2 + 1+1+1+1+1+1+1+1 + 5 + 3 + (KW+1) + 6 + 3+3+2 + 9;
    wire [STW-1:0] st_n = {n_ph, n_sw_st, n_sw_k, n_sw_seg, n_ab_seg, n_sw_rp, n_sw_all, n_ab,
                           n_rd, n_w, n_rd_ab, n_rd_stop, n_a_end, n_b_st, n_b_end, n_y_st, n_head, n_e_rd, n_dcnt, n_a_end,
                           n_sw_T, n_t_last, n_ovf, n_last_seen, n_ing_fl_done, n_p2h, n_dmode, n_pend_v, n_e_go, n_e_empty,
                           n_infl, n_e_infl, n_rem,
                           n_s_last, n_s_hfin, n_s_stopped, n_s_done2, n_s_emitted, n_s_ovf,
                           n_ph, n_sw_st, n_sw_k, n_a_end};
    wire [STW-1:0] st_r = {P_ING, SW_IDLE, K_GC, 2'd0, 2'd0, 1'b0, 1'b1, 1'b0, {(9*12){1'b0}}, 32'd0,
                           8'd0, 5'd0, 3'd0, {(KW+1){1'b0}}, 6'd0, P_ING, SW_IDLE, K_GC, 9'd0};
    wire [STW-1:0] st;
    localparam integer NSG = (STW + 11) / 12;
    generate for (gg = 0; gg < NSG; gg = gg + 1) begin : g_st
        localparam integer LO = gg * 12;
        localparam integer SW = (STW - LO < 12) ? (STW - LO) : 12;
        reg [SW-1:0] q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) q <= st_r[LO +: SW];
            else if (sc[gg % NSC]) q <= st_r[LO +: SW];
            else q <= st_n[LO +: SW];
        assign st[LO +: SW] = q;
    end endgenerate
    wire [AW:0] a_end_x;
    assign {ph, sw_st, sw_k, sw_seg, ab_seg, sw_rp, sw_all, ab,
            rd, w, rd_ab, rd_stop, a_end, b_st, b_end, y_st, head, e_rd, dcnt, a_end_x,
            sw_T, t_last, ovf, last_seen, ing_fl_done, p2h, dmode, pend_v, e_go, e_empty,
            infl, e_infl, rem,
            q_s_last, q_s_hfin, q_s_stopped, q_s_done2, q_s_emitted, q_s_ovf,
            ph_b, sw_st_b, sw_k_b, a_end_f} = st;
    assign a_end_e = a_end_x;                       // the a_end copy (same D, same clear) for the emit side
    // kept copies: sw_seg for lim, rem per 8 lanes, head[AW] per wdata group (all same D / reset / clear)
    generate
        begin : g_swsl
            (* keep = "true" *) reg [1:0] r;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) r <= 2'd0; else if (sc[NSC-1]) r <= 2'd0; else r <= n_sw_seg;
            assign sw_seg_l = r;
        end
        for (gg = 0; gg < 2; gg = gg + 1) begin : g_remc
            (* keep = "true" *) reg [KW:0] r;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) r <= 0; else if (sc[NSC-2-gg]) r <= 0; else r <= n_rem;
            assign rem_c[gg] = r;
        end
        for (gg = 0; gg < NG; gg = gg + 1) begin : g_hf
            (* keep = "true" *) reg r;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) r <= 1'b0; else if (sc[gg]) r <= 1'b0; else r <= n_head[AW];
            assign hfull[gg] = r;
        end
    endgenerate
    // statistics counters (the original's s_nhead / s_n2 / s_n3) are unobserved by the quarter: not built.

    // pass requests (as the original)
    reg p2q_r, p3q_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin p2q_r <= 1'b0; p3q_r <= 1'b0; end
        else if (sc[0]) begin p2q_r <= 1'b0; p3q_r <= 1'b0; end
        else begin
            if (r_p2) p2q_r <= 1'b1; else if (sw_start) p2q_r <= 1'b0;
            if (r_p3) p3q_r <= 1'b1; else if (sw_start) p3q_r <= 1'b0;
        end
    end
    assign p2q = p2q_r; assign p3q = p3q_r;
    reg [2:0] hf_cnt_r, hs_cnt_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) hf_cnt_r <= SETTLE;
        else if (hf_busy || (p2m && r1_v)) hf_cnt_r <= SETTLE;
        else if (hf_cnt_r != 0) hf_cnt_r <= hf_cnt_r - 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) hs_cnt_r <= SETTLE;
        else if (i0_v || i1_v || hc_busy || hf_busy) hs_cnt_r <= SETTLE;
        else if (hs_cnt_r != 0) hs_cnt_r <= hs_cnt_r - 1'b1;
    end
    assign hf_cnt = hf_cnt_r; assign hs_cnt = hs_cnt_r;

    // -- pend (H4): pend_eff(t) == the original pend(t) -------------------------------------------------------------
    // capture condition from two distinct f_push copies (plane 0 / plane 1 o_v) for the two one-hot select families
    wire cap_b = (sw_k_b == K_P3) && (sw_st_b != SW_IDLE) && dmode && f_push_b && !(pend_v && !d_room) && !seg_clr;
    wire cap_a = cap && !seg_clr;
    reg  [MW-1:0] pend_d1, pend_q;
    wire [MW-1:0] pend_eff;
    always @(posedge clk) pend_d1 <= ps_line;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_pe
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        (* keep = "true" *) reg e1, e0;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin e1 <= 1'b0; e0 <= 1'b1; end
            else begin e1 <= cap_a; e0 <= !cap_b; end
        assign pend_eff[LO +: SW] = (pend_d1[LO +: SW] & {SW{e1}}) | (pend_q[LO +: SW] & {SW{e0}});
        always @(posedge clk) pend_q[LO +: SW] <= pend_eff[LO +: SW];
    end endgenerate

    // -- output stage o0 (H3) and FIFO -----------------------------------------------------------------------------------
    // o0 candidates: emit = {tq_last, mem_rdata}; direct = {d_fin_push, pend}; else {1, 0}
    wire em_a = tq_v && tq_em;
    wire em_b = t3b_v && t3b_em;
    wire d_mid_b      = (sw_k_b == K_P3) && (sw_st_b != SW_IDLE) && dmode && f_push_b && pend_v && d_room;
    wire sw_fin_b     = (sw_st_b == SW_WB) && (fcnt == 0) && !f_push_b && !wpend;
    wire d_fin_push_b = sw_fin_b && (sw_k_b == K_P3) && dmode && pend_v && d_room;
    wire d_push_b     = d_mid_b || d_fin_push_b;
    wire o_push_c = em_a || (ph == P_EM && e_empty && occ < OD) || d_push;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) o0_v <= 1'b0;
        else if (sc[1]) o0_v <= 1'b0;
        else o0_v <= o_push_c;
    (* keep = "true" *) reg o0_vb;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) o0_vb <= 1'b0;
        else if (sc[2]) o0_vb <= 1'b0;
        else o0_vb <= o_push_c;
    reg [MW-1:0] o0_m, o0_p;
    reg          o0_last;
    always @(posedge clk) begin
        o0_m <= mem_rdata; o0_p <= pend_eff;
        o0_last <= em_a ? tq_last : d_push ? d_fin_push : 1'b1;
    end
    wire [MW:0] o_in;
    assign o_in[MW] = o0_last;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_o0
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        (* keep = "true" *) reg sm, sp;
        always @(posedge clk) begin
            sm <= (MUT == 4 && gg == 2) ? 1'b0 : (gg % 2 == 0) ? em_a : em_b;
            sp <= (MUT == 4 && gg == 2) ? 1'b0 : (gg % 2 == 0) ? (!em_b && d_push_b) : (!em_a && d_push);
        end
        assign o_in[LO +: SW] = (o0_m[LO +: SW] & {SW{sm}}) | (o0_p[LO +: SW] & {SW{sp}});
    end endgenerate
    wire           o_push = o0_v;
    wire           o_pop  = (ocnt != 0) && out_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ocnt <= 0;
        else if (sc[3]) ocnt <= 0;
        else ocnt <= ocnt + {{(OCW-1){1'b0}}, o_push} - {{(OCW-1){1'b0}}, o_pop};
    end
    localparam integer OPW = (OD > 1) ? $clog2(OD) : 1;
    reg [OPW-1:0] rp, wp;
    (* keep = "true" *) reg [OPW-1:0] rp_b, wp_b;
    wire [OPW-1:0] nrp   = o_pop ? ((rp == OD-1) ? {OPW{1'b0}} : rp+1'b1) : rp;
    wire [OPW-1:0] nrp_b = o_pop ? ((rp_b == OD-1) ? {OPW{1'b0}} : rp_b+1'b1) : rp_b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rp <= 0; wp <= 0; rp_b <= 0; wp_b <= 0; end
        else if (sc[4]) begin rp <= 0; wp <= 0; rp_b <= 0; wp_b <= 0; end
        else begin
            if (o_pop) begin rp <= nrp; rp_b <= nrp_b; end
            if (o_push) wp <= (wp == OD-1) ? {OPW{1'b0}} : wp + 1'b1;
            if (o0_vb) wp_b <= (wp_b == OD-1) ? {OPW{1'b0}} : wp_b + 1'b1;
        end
    end
    wire [MW:0] o_head;
    ot_sram_showahead_1r1w_h2 #(.W(MW + 1), .AW(OPW)) u_ofq (
        .clk(clk), .rst_n(rst_n), .we({o0_vb, o_push}), .wa({wp_b, wp}), .wd(o_in), .ra({nrp_b, nrp}), .q(o_head));
    assign out_valid = (ocnt != 0);
    assign out_last  = o_head[MW];
    assign o_last_hd = o_head[MW];
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_out
            wire [EW-1:0] ln = o_head[EW*gl +: EW];
            assign out_lv[gl]             = ln[EW-1];
            assign out_val[16*gl +: 16]   = ln[IW +: 16];
            assign out_idx[IW*gl +: IW]   = ln[IW-1:0];
            assign out_ninf[gl]           = ln[EW-1] && (ln[IW +: 16] == 16'hFF80);
        end
    endgenerate
endmodule
