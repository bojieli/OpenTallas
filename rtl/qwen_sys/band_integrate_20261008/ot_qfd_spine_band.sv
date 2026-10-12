`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// qwen-band-integrate 2026-10-08: the W12 ME spine assembled from the r21m band-lane die masters, with the ports of
// ot_qwen_me_spine_h_w12 / ot_qfd_spine_part:
//
//   qfd_sp_tree_top (BAND 1)  ot_qfd_sp_tree_top: the control element (RX = 5 + 2 LNK, BANDF) + ot_qfd_band_upper
//                             (tree levels TCUT+4 / TCUT+5 over the 6 band words);
//   qfd_sp_band_lanes x 6     ot_qfd_band_lanes: levels TCUT+1..TCUT+3 of the band's 8 level-TCUT positions x W lanes,
//                             band word to the tree top, the band's 8 result slots (band-local frame) to its slab;
//   port groups x 48          ot_qwen_me_spport_w12 BANDF 1 (12 elements x PQ 4, two a band): position p = 8b + k
//                             holds group g(split, p) (rows, lane-vector base, result address, in-range mask);
//   links                     LNK relay stages on each band <-> tree-top word link (both ways), CLNK on the control
//                             link (t_sel_e / t_tv_e) to the bands; the tree top makes the selects CLNK edges early
//                             (control element XD - CLNK), so they reach the bands with the tree words (unchanged).
//
// Every result-side output (ov, o_*, am_*, mx_*, scale requests, progress) is the monolithic spine's delayed
// RX = 5 + 2 LNK edges; the result positions are band-local (o_we / o_addr / o_mask / o_data of position p carry
// group g(split, p)), so a burst writes the same rows in the same group order (band-major slot order = ascending g)
// through the band serializers (ot_qfd_res_ser) and the merge.  Issue-side outputs are cycle-identical.
// Bench: rtl/test/qwen_band_integrate/tb_qfd_spine_band.sv.  BMUT / UMUT: the band / upper combine-order mutants;
// PBANDF 0: the port groups index by position (the pre-fix slab), a mutant.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_spine_band #(
    parameter integer W  = 16,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer INT8_SCALE_WCS_BASE = 1,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMIN = 3,
    parameter integer SMAX = 5,
    parameter integer TCUT = 3,
    parameter integer BD = 0,
    parameter integer XVM = 0,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer MEM_EXTRA = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer ACC_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer PQ = 4,
    parameter integer SCALE_LAT = 5,
    parameter integer LANDED = 0,          // qwen-vm-me: the tree top counts landed result bursts (land_cnt)
    parameter integer MUT = 0,
    parameter integer LNK = 0,
    parameter integer CLNK = 0,
    parameter integer BMUT = 0,
    parameter integer UMUT = 0,
    parameter integer PBANDF = 1,          // 0: port groups indexed by position, not the band-local group (mutant)
    parameter integer DMUT = 0             // 1: the tree top's upper control delay without the CLNK relays (mutant)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       land_cnt,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_tiles, i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase, i_ts, i_ks, i_js,
    input  wire [AW-1:0]     i_xbase, i_xks, i_xjs, i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase, i_ots, i_ojs,
    input  wire              i_mmode, i_oen, i_amax, i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output wire              scale_re,
    output wire [(GT >> SMIN)-1:0]     scale_gre,
    output wire [(GT >> SMIN)*AW-1:0]  scale_addr,
    input  wire [(GT >> SMIN)*W*16-1:0] scale_q,
    output wire [(1<<SMAX)-1:0]    x_re,
    output wire [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    output wire              kv_re,
    output wire              tgo,
    output wire [3*NW+13*AW+13-1:0] tb,
    output wire [(1<<SMAX)*32-1:0] xl_d,
    input  wire [(GT >> TCUT)*W*32-1:0] t_lvl,
    input  wire              fab_fault,
    output wire              ov,
    output wire [(GT >> SMIN)-1:0]     o_we,
    output wire [(GT >> SMIN)*AW-1:0]  o_addr,
    output wire [(GT >> SMIN)*W-1:0]   o_mask,
    output wire [(GT >> SMIN)*W*32-1:0] o_data,
    output wire [NW-1:0]     am_idx,
    output wire [31:0]       am_val,
    output wire              am_any,
    output wire              mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output wire [15:0]       progress,
    output wire              fault
);
    localparam integer LT  = $clog2(TG);
    localparam integer LG  = $clog2(GT);
    localparam integer NXC = 1 << SMAX;
    localparam integer XD  = BD + (TCUT - LT) * NWS + TWS + MEM_EXTRA;
    localparam integer NPT = GT >> TCUT;
    localparam integer GI  = NPT;
    localparam integer NPG = GT >> SMIN;
    localparam integer NPE = NPG / PQ;
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer IREG = (BD > XVM && BD > 0) ? 1 : 0;
    localparam integer XNS = BD - XVM - IREG;
    localparam integer CW = 1 + 32 + NW;
    localparam integer FW = 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1);
    localparam integer NB = NPT / 8;       // bands of 8 level-TCUT positions (6 at GT = 48 << TCUT)
    // ---- band <-> tree-top links ----
    wire [NB*W*32-1:0] b_pw, u_pw;
    wire [NB-1:0] b_pv, u_pv, b_lf, u_lf;
    wire [3*W*32-1:0] tt_ty, tt_ty_b;
    wire tt_use, tt_v, tt_use_b, tt_v_b;
    ot_hdc_delay #(.W(NB*W*32), .D(LNK)) u_lpw (.clk(clk), .rst_n(rst_n), .d(b_pw), .q(u_pw));
    ot_hdc_delay #(.W(2*NB), .D(LNK), .RESET(1)) u_lpv (.clk(clk), .rst_n(rst_n), .d({b_pv, b_lf}), .q({u_pv, u_lf}));
    ot_hdc_delay #(.W(3*W*32), .D(LNK)) u_lty (.clk(clk), .rst_n(rst_n), .d(tt_ty), .q(tt_ty_b));
    ot_hdc_delay #(.W(2), .D(LNK), .RESET(1)) u_ltv (.clk(clk), .rst_n(rst_n), .d({tt_use, tt_v}), .q({tt_use_b, tt_v_b}));
    // ---- tree top (die master qfd_sp_tree_top, BAND), stations 0 ----
    wire [LG:0] t_sel_e, t_tv_e;
    wire [W-1:0] tr_fault;
    wire p_v_e2;
    wire [FW-1:0] p_f_e2;
    wire [NPE*CW-1:0] p_am;
    wire [NPE-1:0] p_fault;
    wire x_dv;
    wire [AW-1:0] x_dc, x_dcs;
    wire [3:0] x_dsp;
    ot_qfd_sp_tree_top #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .GT(GT), .TG(TG),
        .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .XD(XD), .XVM(XVM), .ORD(ORD), .SCALE_LOCAL(SCALE_LOCAL), .PQ(PQ),
        .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE), .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT),
        .SCALE_LAT(SCALE_LAT), .IS(0), .OS(0), .LANDED(LANDED), .MUT(MUT), .BAND(1), .NB(NB), .LNK(LNK),
        .CLNK((DMUT != 0) ? 0 : CLNK), .UMUT(UMUT)) u_tt (
        .clk(clk), .rst_n(rst_n), .b_pw(u_pw), .b_pv(u_pv), .b_lf(u_lf), .tt_ty(tt_ty), .tt_use(tt_use), .tt_v(tt_v),
        .land_cnt(land_cnt), .go(go), .ready(ready), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .kv_re(kv_re),
        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr),
        .x_rdy(1'b1), .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp),
        .t_sel_e(t_sel_e), .t_tv_e(t_tv_e), .tr_fault(tr_fault),
        .p_v_e2(p_v_e2), .p_f_e2(p_f_e2), .p_am(p_am), .p_fault(p_fault), .fab_fault(fab_fault),
        .ov(ov), .am_idx(am_idx), .am_val(am_val), .am_any(am_any),
        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),
        .progress(progress), .fault(fault));
    // ---- x root (in die master qfd_sp_vector_memory) ----
    wire [NXC*32-1:0] xl0;
    ot_qfd_vm_xroot #(.AW(AW), .GT(GT), .TG(TG), .SMAX(SMAX), .XVM(XVM)) u_xr (
        .clk(clk), .rst_n(rst_n), .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp),
        .x_re(x_re), .x_addr(x_addr), .x_q(x_q), .xl0(xl0));
    // ---- wire stages: instruction broadcast, x network (as ot_qwen_me_spine_h_w12) ----
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    ot_hdc_delay #(.W(IBW), .D(BD - IREG)) u_ib (.clk(clk), .rst_n(rst_n), .d(ib), .q(tb));
    ot_hdc_delay #(.W(1), .D(BD - IREG), .RESET(1)) u_go (.clk(clk), .rst_n(rst_n), .d(go && ready), .q(tgo));
    ot_hdc_delay #(.W(NXC*32), .D(XNS - 1)) u_xnet (.clk(clk), .rst_n(rst_n), .d(xl0), .q(xl_d));
    // ---- band-lane blocks (die masters qfd_sp_band_lanes): the control link (CLNK relays), the tree words ----
    wire [LG:0] c_sel_b, c_tv_b;
    ot_hdc_delay #(.W(LG+1), .D(CLNK)) u_csel (.clk(clk), .rst_n(rst_n), .d(t_sel_e), .q(c_sel_b));
    ot_hdc_delay #(.W(LG+1), .D(CLNK), .RESET(1)) u_ctv (.clk(clk), .rst_n(rst_n), .d(t_tv_e), .q(c_tv_b));
    wire [NPT*W*32-1:0] t_in;
    ot_hdc_delay #(.W(NPT*W*32), .D(TWS - 1)) u_tws (.clk(clk), .rst_n(rst_n), .d(t_lvl), .q(t_in));
    assign tr_fault = {W{1'b0}};            // the band faults reach the control element through the upper (b_lf)
    wire [NPG*W*32-1:0] lvt;
    genvar b, q;
    generate
        for (b = 0; b < NB; b = b + 1) begin : g_band
            ot_qfd_band_lanes #(.NL(W), .LNK(LNK), .TREE_LAT(TREE_LAT), .MUT(BMUT), .TCUT(TCUT), .LG(LG)) u_bl (
                .clk(clk), .rst_n(rst_n), .b0(b == 0), .tw(t_in[b*8*W*32 +: 8*W*32]), .sel_e(c_sel_b), .tv_e(c_tv_b),
                .tt_ty(b == 0 ? tt_ty_b : {3*W*32{1'b0}}), .tt_use(b == 0 ? tt_use_b : 1'b0),
                .tt_v(b == 0 ? tt_v_b : 1'b0), .pw(b_pw[b*W*32 +: W*32]), .pw_v(b_pv[b]),
                .ty(lvt[b*8*W*32 +: 8*W*32]), .fault(b_lf[b]));
        end
    endgenerate
    // ---- port elements, then the ORD result-write wire stages ----
    wire [NPG-1:0]      we2;
    wire [NPG*AW-1:0]   addr2;
    wire [NPG*W-1:0]    mask2;
    wire [NPG*W*32-1:0] data2;
    generate
        for (q = 0; q < NPE; q = q + 1) begin : g_port
            ot_qwen_me_spport_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .SMIN(SMIN), .PQ(PQ),
                .TREE_LAT(TREE_LAT), .SCALE_LAT(SCALE_LAT), .BANDF(PBANDF), .TCUT(TCUT)) u_pt (
                .clk(clk), .rst_n(rst_n), .pt_id(q[15:0]),
                .lv_in(lvt[q*PQ*W*32 +: PQ*W*32]), .a_v_e2(p_v_e2), .a_f_e2(p_f_e2),
                .scale_q(scale_q[q*PQ*W*16 +: PQ*W*16]),
                .o_we(we2[q*PQ +: PQ]), .o_addr(addr2[q*PQ*AW +: PQ*AW]), .o_mask(mask2[q*PQ*W +: PQ*W]),
                .o_data(data2[q*PQ*W*32 +: PQ*W*32]), .am(p_am[q*CW +: CW]), .fault(p_fault[q]));
        end
        if (ORD > 0) begin : g_ord
            ot_hdc_delay #(.W(NPG), .D(ORD), .RESET(1)) u_owe (.clk(clk), .rst_n(rst_n), .d(we2), .q(o_we));
            ot_hdc_delay #(.W(NPG*AW + NPG*W + NPG*W*32), .D(ORD)) u_od (.clk(clk), .rst_n(rst_n),
                .d({addr2, mask2, data2}), .q({o_addr, o_mask, o_data}));
        end else begin : g_no_ord
            assign o_we = we2; assign o_addr = addr2; assign o_mask = mask2; assign o_data = data2;
        end
    endgenerate
endmodule
