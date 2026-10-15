`timescale 1ns/1ps
module ot_qwen_tt_core_ctl #(
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
    parameter integer AMR = 0,            // ot_qwen_me_spctl_w12 AMR (safe-qwen S-D1: argmax top registered at the accumulator)
    parameter integer SPRE = 0,           // ot_qwen_me_spctl_w12 SPRE (redesign-qwen: registered scale request)
    parameter integer XADDR = 1,          // el1011-q-seq: spctl XADDR (0: no per-port x_re / x_addr; this module uses the descriptor form)
    parameter integer RDMEM = 0,          // el1011-q-seq: spctl RDMEM (tag delay lines in SRAM)
    parameter integer OKEEP = 0,          // el1011-q-seq: output stations through (* keep *) wires (no merge with internal flops)
    parameter integer PK = 0,             // el1011-q-seq: spctl PK (exact path cuts: KS progress subtract, registered u_ttag read)
    parameter integer SC = 0,             // el1011-q-seq: spctl SC (exact setup cuts: pre-scale compare, mx write, scale_addr)
    parameter integer AMI = 0             // el1011-q-seq: spctl AMI (1 = p_am pin register, argmax loop +1 cycle; 2 = uncompensated mutant)
) (
    input  wire              clk,
    input  wire              rst_n,
    output wire [(1+1+1+1+1+4+AW+AW+3*(NW+1)+1+3+1+AW+AW)-1:0] scale_tag,
    output wire scale_v,
    output wire [NW-1:0] scale_t,

    // the upper sub-tiles' fault (OR over the tiles, relayed): registered here into the control element's fault
    input  wire              up_fault,
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
    // x read descriptor (to the vector memory, the x root) and the VM's new-op gate
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
    wire go_q, fab_q;
    wire [W-1:0] trf_q;
    wire [NPE*CW-1:0] pam_q;
    wire [NPE-1:0] pf_q;
    wire [15:0] land_q;
    ot_hdc_delay #(.W(IBW + NPE*CW + 16), .D(IS)) u_id (.clk(clk), .rst_n(rst_n), .d({ib, p_am, land_cnt}),
        .q({ib_q, pam_q, land_q}));
    ot_hdc_delay #(.W(2 + W + NPE), .D(IS), .RESET(1)) u_is (.clk(clk), .rst_n(rs),
        .d({go, fab_fault, tr_fault, p_fault}), .q({go_q, fab_q, trf_q, pf_q}));
    wire [NW-1:0] q_nout, q_tiles, q_k;
    wire q_wsrc, q_round, q_mmode, q_oen, q_amax, q_rmax;
    wire [AW-1:0] q_wbase, q_ts, q_ks, q_js, q_xbase, q_xks, q_xjs, q_xcs, q_wcs, q_obase, q_ots, q_ojs, q_mbase;
    wire [2:0] q_jsh;
    wire [3:0] q_split;
    assign {q_nout, q_tiles, q_k, q_wsrc, q_wbase, q_ts, q_ks, q_js, q_xbase, q_xks, q_xjs, q_xcs,
            q_jsh, q_split, q_wcs, q_round, q_obase, q_ots, q_ojs, q_mmode, q_oen, q_amax, q_rmax, q_mbase} = ib_q;
    // ---- the control element ----
    wire c_ready, c_idle, c_wrom_re, c_kv_re, c_xdv, c_pv, c_ov, c_amany, c_mxwe, c_fault;
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
    ot_qwen_tt_core_spctl #(.XADDR(XADDR), .RDMEM(RDMEM), .PK(PK), .SC(SC), .W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .GT(GT),
        .TG(TG), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .XD((BAND != 0) ? XD - CLNK : XD), .XVM(XVM), .ORD(ORD),
        .SCALE_LOCAL(SCALE_LOCAL), .PQ(PQ), .ACC_LAT(ACC_LAT), .TREE_LAT(TREE_LAT), .FAST_ISSUE(FAST_ISSUE),
        .KV_PREP(KV_PREP), .MUL_LAT(MUL_LAT), .SCALE_LAT(SCALE_LAT), .LANDED(LANDED),
        .RX((BAND != 0) ? 5 + 2 * LNK + CLNK : 0), .RXA((BAND != 0) ? 5 + 2 * LNK : 0), .BANDF(BAND), .AMR(AMR), .SPRE(SPRE), .AMI(AMI)) u_ctl (
        .clk(clk), .rst_n(rs), .go(go_q), .ready(c_ready), .idle(c_idle), .land_cnt(land_q),
        .i_nout(q_nout), .i_tiles(q_tiles), .i_k(q_k), .i_wsrc(q_wsrc),
        .i_wbase(q_wbase), .i_ts(q_ts), .i_ks(q_ks), .i_js(q_js),
        .i_xbase(q_xbase), .i_xks(q_xks), .i_xjs(q_xjs), .i_xcs(q_xcs),
        .i_jsh(q_jsh), .i_split(q_split), .i_wcs(q_wcs), .i_round(q_round),
        .i_obase(q_obase), .i_ots(q_ots), .i_ojs(q_ojs),
        .i_mmode(q_mmode), .i_oen(q_oen), .i_amax(q_amax), .i_rmax(q_rmax), .i_mbase(q_mbase),
        .wrom_re(c_wrom_re), .wrom_addr(c_wrom_addr), .kv_re(c_kv_re),
        .scale_tag(scale_tag), .scale_v(scale_v), .scale_t(scale_t),
        .x_re(), .x_addr(), .x_q({((1<<SMAX)*32){1'b0}}), .xl0(),
        .x_dv(c_xdv), .x_dc(c_xdc), .x_dcs(c_xdcs), .x_dsp(c_xdsp),
        .t_sel_e(c_sel), .t_tv_e(c_tv), .tr_fault(trf_q | {{(W-1){1'b0}}, u_fault}),
        .p_v_e2(c_pv), .p_f_e2(c_pf), .p_am(pam_q), .p_fault(pf_q), .fab_fault(fab_q),
        .ov(c_ov), .am_idx(c_amidx), .am_val(c_amval), .am_any(c_amany),
        .mx_we(c_mxwe), .mx_addr(c_mxaddr), .mx_mask(c_mxmask), .mx_data(c_mxdata),
        .progress(c_prog), .fault(c_fault));
    wire [AW-1:0] c_xdcs_m = (MUT != 0) ? (c_xdcs ^ {{(AW-1){1'b0}}, 1'b1}) : c_xdcs;
    // ---- the upper tree levels live in the sub-tiles (ot_qfd_band_upper x NU); their fault lands in a pin flop ----
    reg uf_q;
    always @(posedge clk or negedge rs) if (!rs) uf_q <= 1'b0; else uf_q <= up_fault;
    assign u_fault = uf_q;
    // ---- output stations: strobes / valids on reset lines, fields plain ----
    wire [8 + 2*(LG+1)-1:0] os_q;
    wire [2 + AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16-1:0] od_q;
    generate if (OKEEP != 0 && OS == 1) begin : g_osk
        // el1011-q-seq: kept station registers (an ot_hdc_delay station was merged with an identical internal flop)
        wire [8 + 2*(LG+1)-1:0] os_d = {c_ready, c_idle, c_wrom_re, c_kv_re, c_xdv, c_pv, c_ov, c_mxwe, c_sel, c_tv};
        (* keep = "true", dont_touch = "true" *) reg [8 + 2*(LG+1)-1:0] os_r;
        always @(posedge clk or negedge rs) if (!rs) os_r <= '0; else os_r <= os_d;
        assign os_q = os_r;
    end else begin : g_osd
    ot_hdc_delay #(.W(8 + 2*(LG+1)), .D(OS), .RESET(1)) u_os (.clk(clk), .rst_n(rs),
            .d({c_ready, c_idle, c_wrom_re, c_kv_re, c_xdv, c_pv, c_ov, c_mxwe, c_sel, c_tv}),
            .q(os_q));
    end endgenerate
    generate if (OKEEP != 0 && OS == 1) begin : g_odk
        wire [2 + AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16-1:0] od_d = {c_amany, c_fault, c_wrom_addr, c_xdc, c_xdcs_m, c_xdsp, c_pf, c_amidx, c_amval, c_mxaddr,
            c_mxmask, c_mxdata, c_prog};
        (* keep = "true", dont_touch = "true" *) reg [2 + AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16-1:0] od_r;
        always @(posedge clk) od_r <= od_d;
        assign od_q = od_r;
    end else begin : g_odd
    ot_hdc_delay #(.W(2 + AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16), .D(OS)) u_od (
            .clk(clk), .rst_n(rst_n),
            .d({c_amany, c_fault, c_wrom_addr, c_xdc, c_xdcs_m, c_xdsp, c_pf, c_amidx, c_amval, c_mxaddr,
                c_mxmask, c_mxdata, c_prog}),
            .q(od_q));
    end endgenerate
    // el1011-q-seq OKEEP: the stations' flops must drive the pins themselves (ctlm_i-f62cd33ac: x_dv was driven by
    // u_ctl.u_mv.line[1] -- yosys merged the station with an identical internal delay-line flop deep in the block)
    localparam integer OSW = 8 + 2*(LG+1);
    localparam integer ODW = 2 + AW + AW + AW + 4 + FW + NW + 32 + AW + W + W*32 + 16;
    generate if (OKEEP != 0) begin : g_okeep
        (* keep = "true" *) wire [OSW-1:0] os_k = os_q;
        (* keep = "true" *) wire [ODW-1:0] od_k = od_q;
        assign {ready, idle, wrom_re, kv_re, x_dv, p_v_e2, ov, mx_we, t_sel_e, t_tv_e} = os_k;
        assign {am_any, fault, wrom_addr, x_dc, x_dcs, x_dsp, p_f_e2, am_idx, am_val, mx_addr,
                mx_mask, mx_data, progress} = od_k;
    end else begin : g_oplain
        assign {ready, idle, wrom_re, kv_re, x_dv, p_v_e2, ov, mx_we, t_sel_e, t_tv_e} = os_q;
        assign {am_any, fault, wrom_addr, x_dc, x_dcs, x_dsp, p_f_e2, am_idx, am_val, mx_addr,
                mx_mask, mx_data, progress} = od_q;
    end endgenerate
endmodule
