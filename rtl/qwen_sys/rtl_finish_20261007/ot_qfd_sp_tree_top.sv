`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_sp_tree_top (qwen-rtl-finish 2026-10-07): the W12 ME spine re-partitioned so the die-level master has a
// buildable face.
//
// The spine RTL (ot_qwen_me_spine_w12 / its hardened successor ot_qwen_me_spine_h_w12) as ONE master has ~200 k signal
// pins at G = 6,144: the 2,048-port x read (x_re / x_addr 51 k out, x_q 65.5 k in), the x network (xl_d 65.5 k out), the
// tree words (t_lvl 24.6 k in), the results (o_* 26.4 k out) and the scale port (13.4 k).  The r21 abstract has 3.6 k.
// The partition below keeps every value and every cycle (ot_qfd_spine_part == ot_qwen_me_spine_h_w12, all outputs,
// every cycle, at IS = OS = 0: tb_qfd_tree_top) and moves the wide data to the elements that own it:
//
//   qfd_sp_tree_top        ot_qfd_sp_tree_top: the spine CONTROL element ot_qwen_me_spctl_w12 (issue loop, element tags,
//                          per-level tree selects, scale requests, argmax top levels, per-slot maxima, progress, idle,
//                          fault) with IS / OS pin stations.  The x read leaves as a 53-bit DESCRIPTOR (x_dv, x_dc,
//                          x_dcs, x_dsp) instead of 2,048 addresses: every port's address is x_dc + (c mod 2^x_dsp) *
//                          x_dcs, so the vector memory expands it (ot_qfd_vm_xroot) and is the x-network root (the r21
//                          head chains already start at the VM).  Face: ~3.3 k bits (see the abstract in
//                          tools/qwen_rtl_finish/tree_top_abstract.py).
//   qfd_sp_tree_lane x 16  ot_qwen_spine_lane / _credit (existing masters): one LANE of tree levels TCUT+1..LG-1 each
//                          (t_lvl lane slice in, level LG-1 lane slice out; lanes never mix), taking t_sel_e / t_tv_e.
//   port elements x 12     ot_qwen_me_spport_w12 (PQ = 4 result-port groups: post-scale, result registers, argmax
//                          leaves; in r21 the band port slabs qfd_port_tiles_* hold the slab equivalent), taking the
//                          element tags p_v_e2 / p_f_e2 and returning their argmax node p_am and fault.
//   qfd_sp_vector_memory   the x root: descriptor expansion + the x-network select stage (ot_qfd_vm_xroot) + the
//                          banked read service (ot_qfd_sp_vector_memory).
//
// x_rdy (from the vector memory): the tree top reports ready only when the VM can take a new op's first tuple (its
// beats must not overlap the previous op's, ot_qfd_sp_vector_memory); <= BMAX - 2 edges per back-to-back op, priced.
// Station semantics (IS / OS > 0): every tree-top input lands IS edges late and every output leaves OS edges late
// (ot_hdc_delay; strobes on reset lines), reset released IS late.  The go / ready loop with the sequencer is closed by
// the split controller's issue shell (ot_qfd_issue_shell, RT = DCU + DUC); the descriptor / tag / select outputs feed
// elements that take the SAME OS shift on every one of their control inputs (the broadcast BD and the tree-word wire
// stages TWS absorb OS: a die integration sets BD' = BD - OS, TWS' = TWS - OS - IS, so the tree words still arrive
// XD edges after the issue).  MUT = 1: the descriptor stride's bit 0 is inverted (the bench must FAIL).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_sp_tree_top #(
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
    parameter integer XD = 0,
    parameter integer XVM = 0,
    parameter integer ORD = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer PQ = 4,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer MUL_LAT = 5,
    parameter integer SCALE_LAT = 5,
    parameter integer IS = 1,
    parameter integer OS = 1,
    parameter integer LANDED = 0,          // qwen-vm-me: progress / idle on the vector memory's landed result bursts
    parameter integer MUT = 0,
    // qwen-band-integrate 2026-10-08: BAND 1 = the r21m band-lane spine (ot_qfd_band_lanes x 6 beside the slabs): the
    // tree top hosts the upper tree levels TCUT+4 / TCUT+5 (ot_qfd_band_upper) over the 6 band words (b_pw / b_pv / b_lf
    // in, straight into its pin flops) and returns the split-(TCUT+4 / TCUT+5) words to band 0 (tt_ty / tt_use / tt_v,
    // from its station).  The control element runs with RX = 5 + 2 LNK (the band round trip: element tags, scale
    // requests and every result-side output move RX edges later) and BANDF (band-local result positions).
    // LNK: relay stages on each band <-> tree-top word link; CLNK: relay stages on the control link (t_sel_e / t_tv_e)
    // from this block's output station to the bands.  The control element makes the per-level selects CLNK edges
    // EARLY (its XD is XD - CLNK: the selects depend only on the op's tag, known that early), so they reach the bands
    // with the tree words (lane-timed, XD edges after issue as before); its result tags then carry RX = 5 + 2 LNK + CLNK,
    // i.e. the results stay 5 + 2 LNK edges behind the monolithic spine's (CLNK costs no cycle).  The upper's control
    // delay DLY = OS + CLNK + 2 + LNK: the bands use the selects OS + CLNK edges after the control element makes them,
    // and the band word reaches the upper's pin flop 2 + LNK edges after that.
    parameter integer BAND = 0,
    parameter integer NB = 6,
    parameter integer LNK = 0,
    parameter integer CLNK = 0,
    parameter integer UMUT = 0,           // ot_qfd_band_upper MUT (negative mutant)
    parameter integer AMR = 0             // ot_qwen_me_spctl_w12 AMR (safe-qwen S-D1: argmax top registered at the accumulator)
) (
    input  wire              clk,
    input  wire              rst_n,
    // BAND: the band words (level TCUT+3, lane-major per band), their valids and the bands' faults; band 0's return
    input  wire [NB*W*32-1:0] b_pw,
    input  wire [NB-1:0]     b_pv,
    input  wire [NB-1:0]     b_lf,
    output wire [3*W*32-1:0] tt_ty,
    output wire              tt_use,
    output wire              tt_v,
    input  wire [15:0]       land_cnt,     // LANDED: the memory's landed-burst count (ot_qfd_res_merge), IS-stationed
    // issue (from the sequencer)
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
    // engine ROM / KV strobes (observation for the controller), scale requests (to the port elements' scale ROM)
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    output wire              kv_re,
    output wire              scale_re,
    output wire [(GT >> SMIN)-1:0]     scale_gre,
    output wire [(GT >> SMIN)*AW-1:0]  scale_addr,
    // x read descriptor (to the vector memory, the x root) and the VM's new-op gate
    input  wire              x_rdy,
    output wire              x_dv,
    output wire [AW-1:0]     x_dc,
    output wire [AW-1:0]     x_dcs,
    output wire [3:0]        x_dsp,
    // tree lanes
    output wire [$clog2(GT):0] t_sel_e,
    output wire [$clog2(GT):0] t_tv_e,
    input  wire [W-1:0]        tr_fault,
    // port elements
    output wire              p_v_e2,
    output wire [1+1+1+1+4+AW+AW+3*(NW+1)-1:0] p_f_e2,
    input  wire [((GT >> SMIN) / PQ)*(1+32+NW)-1:0] p_am,
    input  wire [((GT >> SMIN) / PQ)-1:0]   p_fault,
    input  wire              fab_fault,
    // results the top owns: op valid, argmax, per-slot maxima write, progress, fault
    output wire              ov,
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
    localparam integer LG  = $clog2(GT);
    localparam integer NPG = GT >> SMIN;
    localparam integer NPE = NPG / PQ;
    localparam integer CW  = 1 + 32 + NW;
    localparam integer FW  = 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1);
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    wire rs;
    wire u_fault;          // BAND: the upper levels' fault (adders, bands, lockstep), into the control element's fault
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));
    // ---- input stations ----
    wire [IBW-1:0] ib = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                         i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax,
                         i_mbase};
    wire [IBW-1:0] ib_q;
    wire go_q, fab_q, xr_q;
    wire [W-1:0] trf_q;
    wire [NPE*CW-1:0] pam_q;
    wire [NPE-1:0] pf_q;
    wire [15:0] land_q;
    ot_hdc_delay #(.W(IBW + NPE*CW + 16), .D(IS)) u_id (.clk(clk), .rst_n(rst_n), .d({ib, p_am, land_cnt}),
        .q({ib_q, pam_q, land_q}));
    ot_hdc_delay #(.W(3 + W + NPE), .D(IS), .RESET(1)) u_is (.clk(clk), .rst_n(rst_n),
        .d({go, fab_fault, x_rdy, tr_fault, p_fault}), .q({go_q, fab_q, xr_q, trf_q, pf_q}));
    wire [NW-1:0] q_nout, q_tiles, q_k;
    wire q_wsrc, q_round, q_mmode, q_oen, q_amax, q_rmax;
    wire [AW-1:0] q_wbase, q_ts, q_ks, q_js, q_xbase, q_xks, q_xjs, q_xcs, q_wcs, q_obase, q_ots, q_ojs, q_mbase;
    wire [2:0] q_jsh;
    wire [3:0] q_split;
    assign {q_nout, q_tiles, q_k, q_wsrc, q_wbase, q_ts, q_ks, q_js, q_xbase, q_xks, q_xjs, q_xcs,
            q_jsh, q_split, q_wcs, q_round, q_obase, q_ots, q_ojs, q_mmode, q_oen, q_amax, q_rmax, q_mbase} = ib_q;
    // ---- the control element ----
    wire c_ready, c_idle, c_wrom_re, c_kv_re, c_scale_re, c_xdv, c_pv, c_ov, c_amany, c_mxwe, c_fault;
    wire [AW-1:0] c_wrom_addr, c_xdc, c_xdcs, c_mxaddr;
    wire [3:0] c_xdsp;
    wire [NPG-1:0] c_sgre;
    wire [NPG*AW-1:0] c_saddr;
    wire [LG:0] c_sel, c_tv;
    wire [FW-1:0] c_pf;
    wire [NW-1:0] c_amidx;
    wire [31:0] c_amval;
    wire [W-1:0] c_mxmask;
    wire [W*32-1:0] c_mxdata;
    wire [15:0] c_prog;
    ot_qwen_me_spctl_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .GT(GT),
        .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .XD((BAND != 0) ? XD - CLNK : XD), .XVM(XVM), .ORD(ORD),
        .SCALE_LOCAL(SCALE_LOCAL), .PQ(PQ), .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE),
        .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT), .SCALE_LAT(SCALE_LAT), .LANDED(LANDED),
        .RX((BAND != 0) ? 5 + 2 * LNK + CLNK : 0), .RXA((BAND != 0) ? 5 + 2 * LNK : 0), .BANDF(BAND), .AMR(AMR)) u_ctl (
        .clk(clk), .rst_n(rs), .go(go_q), .ready(c_ready), .idle(c_idle), .land_cnt(land_q),
        .i_nout(q_nout), .i_tiles(q_tiles), .i_k(q_k), .i_wsrc(q_wsrc),
        .i_wbase(q_wbase), .i_ts(q_ts), .i_ks(q_ks), .i_js(q_js),
        .i_xbase(q_xbase), .i_xks(q_xks), .i_xjs(q_xjs), .i_xcs(q_xcs),
        .i_jsh(q_jsh), .i_split(q_split), .i_wcs(q_wcs), .i_round(q_round),
        .i_obase(q_obase), .i_ots(q_ots), .i_ojs(q_ojs),
        .i_mmode(q_mmode), .i_oen(q_oen), .i_amax(q_amax), .i_rmax(q_rmax), .i_mbase(q_mbase),
        .wrom_re(c_wrom_re), .wrom_addr(c_wrom_addr), .kv_re(c_kv_re),
        .scale_re(c_scale_re), .scale_gre(c_sgre), .scale_addr(c_saddr),
        .x_re(), .x_addr(), .x_q({((1<<SMAX)*32){1'b0}}), .xl0(),
        .x_dv(c_xdv), .x_dc(c_xdc), .x_dcs(c_xdcs), .x_dsp(c_xdsp),
        .t_sel_e(c_sel), .t_tv_e(c_tv), .tr_fault(trf_q | {{(W-1){1'b0}}, u_fault}),
        .p_v_e2(c_pv), .p_f_e2(c_pf), .p_am(pam_q), .p_fault(pf_q), .fab_fault(fab_q),
        .ov(c_ov), .am_idx(c_amidx), .am_val(c_amval), .am_any(c_amany),
        .mx_we(c_mxwe), .mx_addr(c_mxaddr), .mx_mask(c_mxmask), .mx_data(c_mxdata),
        .progress(c_prog), .fault(c_fault));
    wire [AW-1:0] c_xdcs_m = (MUT != 0) ? (c_xdcs ^ {{(AW-1){1'b0}}, 1'b1}) : c_xdcs;
    // ---- BAND: the upper tree levels (reset as the control element: the IS-stationed reset) ----
    generate if (BAND != 0) begin : g_band
        ot_qfd_band_upper #(.NL(W), .NB(NB), .LNK(LNK), .DLY(OS + CLNK + 2 + LNK), .TREE_LAT(TREE_LAT), .MUT(UMUT),
            .TCUT(TCUT), .LG(LG)) u_up (
            .clk(clk), .rst_n(rs), .pw(b_pw), .pw_v(b_pv), .lf(b_lf), .sel_e(c_sel), .tv_e(c_tv),
            .tt_ty(tt_ty), .tt_use(tt_use), .tt_v(tt_v), .fault(u_fault));
    end else begin : g_noband
        assign u_fault = 1'b0;
        assign tt_ty = {3*W*32{1'b0}}; assign tt_use = 1'b0; assign tt_v = 1'b0;
    end endgenerate
    // ---- output stations: strobes / valids on reset lines, fields plain ----
    ot_hdc_delay #(.W(9 + NPG + 2*(LG+1)), .D(OS), .RESET(1)) u_os (.clk(clk), .rst_n(rst_n),
        .d({c_ready && xr_q, c_idle, c_wrom_re, c_kv_re, c_scale_re, c_xdv, c_pv, c_ov, c_mxwe, c_sgre, c_sel, c_tv}),
        .q({ready, idle, wrom_re, kv_re, scale_re, x_dv, p_v_e2, ov, mx_we, scale_gre, t_sel_e, t_tv_e}));
    ot_hdc_delay #(.W(2 + AW + NPG*AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16), .D(OS)) u_od (
        .clk(clk), .rst_n(rst_n),
        .d({c_amany, c_fault, c_wrom_addr, c_saddr, c_xdc, c_xdcs_m, c_xdsp, c_pf, c_amidx, c_amval, c_mxaddr,
            c_mxmask, c_mxdata, c_prog}),
        .q({am_any, fault, wrom_addr, scale_addr, x_dc, x_dcs, x_dsp, p_f_e2, am_idx, am_val, mx_addr,
            mx_mask, mx_data, progress}));
endmodule


// The vector memory's x root (inside die master qfd_sp_vector_memory): the descriptor expanded to the per-port read
// (x_re / x_addr, the form the token bench's behavioural memory and ot_qfd_sp_vector_memory's reference take) and the
// x network's select stage (ot_qwen_me_spctl_w12 xl0: quad line r carries chunks TG*(r mod S/TG) .. +TG-1, S = 2^split
// of the element whose x arrives, the split delayed 2 + XVM edges).
module ot_qfd_vm_xroot #(
    parameter integer AW = 24,
    parameter integer GT = 80,
    parameter integer TG = 4,
    parameter integer SMAX = 5,
    parameter integer XVM = 0
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    x_dv,
    input  wire [AW-1:0]           x_dc,
    input  wire [AW-1:0]           x_dcs,
    input  wire [3:0]              x_dsp,
    output wire [(1<<SMAX)-1:0]    x_re,
    output wire [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    output reg  [(1<<SMAX)*32-1:0] xl0
);
    localparam integer NX = 1 << SMAX;
    localparam integer NPX = (NX < GT) ? NX : GT;
    localparam integer NXL = NX / TG;
    genvar c;
    generate for (c = 0; c < NX; c = c + 1) begin : g_x
        if (c < NPX) begin : g_p
            wire [AW-1:0] off = (c & ((1 << x_dsp) - 1)) * x_dcs;
            assign x_re[c] = x_dv && ((c >> x_dsp) < (GT >> x_dsp));
            assign x_addr[c*AW +: AW] = x_dc + off;
        end else begin : g_z
            assign x_re[c] = 1'b0;
            assign x_addr[c*AW +: AW] = {AW{1'b0}};
        end
    end endgenerate
    wire [3:0] x_split;
    ot_hdc_delay #(.W(4), .D(2 + XVM)) u_xs (.clk(clk), .rst_n(rst_n), .d(x_dsp), .q(x_split));
    genvar r, i;
    generate
        for (r = 0; r < NXL; r = r + 1) begin : g_line
            wire [SMAX:0] quads = (1 << x_split) / TG;
            wire [SMAX:0] src = r & (quads - 1);
            for (i = 0; i < TG; i = i + 1) begin : g_e
                always @(posedge clk) xl0[(r*TG + i)*32 +: 32] <= x_q[(src*TG + i)*32 +: 32];
            end
        end
    endgenerate
endmodule


// The spine re-assembled from the die masters (tree top + x root + 16 lanes + port elements + the wire stages), with the
// ports of ot_qwen_me_spine_h_w12.  IS = OS = 0: cycle- and bit-identical to it (tb_qfd_tree_top).
module ot_qfd_spine_part #(
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
    parameter integer MUT = 0
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
    // ---- tree top (die master qfd_sp_tree_top), stations 0 ----
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
        .SCALE_LAT(SCALE_LAT), .IS(0), .OS(0), .LANDED(LANDED), .MUT(MUT)) u_tt (
        .clk(clk), .rst_n(rst_n), .land_cnt(land_cnt), .go(go), .ready(ready), .idle(idle),
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
    // ---- tree lanes (die masters qfd_sp_tree_lane) ----
    wire [NPT*W*32-1:0] t_in;
    ot_hdc_delay #(.W(NPT*W*32), .D(TWS - 1)) u_tws (.clk(clk), .rst_n(rst_n), .d(t_lvl), .q(t_in));
    wire [NPG*W*32-1:0] lvt;
    genvar l, p, q;
    generate
        for (l = 0; l < W; l = l + 1) begin : g_tree
            wire [GI*32-1:0] tl;
            wire [NPG*32-1:0] yl;
            for (p = 0; p < GI; p = p + 1) begin : g_in
                assign tl[p*32 +: 32] = t_in[(p*W + l)*32 +: 32];
            end
            ot_qwen_me_sptree_w12 #(.GT(GT), .SMIN(SMIN), .TCUT(TCUT), .TREE_LAT(TREE_LAT), .TINREG(1)) u_tr (
                .clk(clk), .rst_n(rst_n), .t_in(tl), .sel_e(t_sel_e), .tv_e(t_tv_e), .y(yl), .fault(tr_fault[l]));
            for (p = 0; p < NPG; p = p + 1) begin : g_out
                assign lvt[(p*W + l)*32 +: 32] = yl[p*32 +: 32];
            end
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
                .TREE_LAT(TREE_LAT), .SCALE_LAT(SCALE_LAT)) u_pt (
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
