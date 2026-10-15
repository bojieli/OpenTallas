`timescale 1ns/1ps
`default_nettype none
// ot_hfd_coll_q (HBM peer-to-peer step 1, owner approval 2026-10-14 09:00 PT; study results/arch/hbm_p2p_1014/STUDY.md):
// ONE parameterised QUADRANT collective engine.  Four instances replace the single central hfd_coll
// (ot_hfd_coll_r25gq): each sits at its quadrant's link edge and owns the links of its rail (switch routing by die and
// quadrant): SW S0-S2 (NPT 3), SE S3-S4, NW N0-N1, NE N2-N3 (NPT 2).  Two masters (NPT 3 / NPT 2), each hardened once.
//   * body: ot_hgi_coll_qep (the central block body with quadrant quarters, see ot_hgi_coll_qrec): the same normative
//     record reaches all four engines; engine q runs element quarter q of it on its NPT links and delivers its words to
//     its own slice (lanes del_*), injects from its own SU quarter (inj_*).  ARGMAX / TOPK / ROW_GATHER run whole on
//     quadrant QSOLO (SW).  Bit-exact against the central engine by construction (bench tb_hgi_coll_p2p).
//   * record queue (RQD deep): the broadcast record is captured whenever it arrives (the four copies cross different
//     relay counts); the HOME engine (SW) holds a credit per queue slot of every quadrant and is the only one that
//     answers the command processor: ret = {fault, done, ready}: ready while every quadrant has a free slot, done once
//     all four quadrants retired the record (in order), fault if any did.
//   * peer ring stop ot_hgi_coll_pring: record credits / completions / faults to HOME and the bit-exact reduction carry
//     (RED_CARRY, B2 section 4) for the quadrant's SU (rc_* / rr_*).  No wide vector crosses quadrants.
//   * RGX memory lanes as ot_hfd_coll_r25gq (owner-row source, used by the QSOLO engine); the ROW_GATHER write sink is
//     its own master ot_hgi_coll_rgx_snkm beside the SW slice (a client station of the VM lane arbiter can not sit
//     across relays): rgx_t_* / rgx_f_* credit-flow die nets (2,213 b out, 5 b back) instead of the 8,961-b W2 client.
// Every die output leaves a flop (ring, ret, session, status); die inputs are captured by the block's input stations.
module ot_hfd_coll_q #(
    parameter integer TKM_NATIVE = 0,
    parameter integer PR_SPLIT_CLOCKS = 0,
    parameter integer NPT = 3,              // links of this quadrant's rail (3 SW, 2 SE / NW / NE)
    parameter integer SWCRED = 32,
    parameter integer RGX_CRD = 16,         // ROW_GATHER write credits a delivery lane (= the slice-side FIFO depth)
    parameter integer TKW_CRD = 8,          // TOPK line write credits (ot_hgi_coll_vmport)
    parameter integer SESSION_W0 = 47,
    parameter integer INJ = 2,
    parameter integer DEL = 4,
    parameter integer LANES = 16,
    parameter integer FW = 32 * LANES,
    parameter integer PWT = FW + 33,
    parameter integer RQD = 2,              // record queue depth a quadrant
    parameter integer INJLAT = 12,          // SU inject answer latency (die relays out + SU fixed VM read + relays back)
    parameter integer HOME = 0,
    parameter integer QSOLO = 0,
    parameter integer SOLO_CAP = 1,         // 0: never QSOLO (NPT-2 master): no RGX lanes, no whole ops
    parameter integer TKM = 0,              // 1: the TOPK_MERGE sink (QSOLO master only)
    parameter integer TKM_KMAX = 2048,
    parameter integer RW = 280,
    parameter integer MUT_Q = 0,            // bench mutants
    parameter integer MUT_CARRY = 0,
    parameter integer MUT_ORDER = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [7:0]           pr_clk_state,
    input  wire [7:0]           pr_clk_add,
    input wire tkm_clk_core, tkm_clk_buffer, tkm_clk_packer,
    input wire [3:0] tkm_clk_lane,
    input wire [31:0] tkm_clk_tile,
    input  wire [1:0]           qid,        // die strap: 0 SW, 1 SE, 2 NW, 3 NE
    // command processor (broadcast record; only HOME's ret is bound)
    input  wire [967:0]         hgi_rec,
    input  wire [553:0]         hgi_recx,
    output reg  [2:0]           hgi_ret,
    input  wire [39:0]          hgi_cfg,
    output wire [79:0]          hgi_vmaddr,
    output reg  [INJ*80-1:0]    hgi_inj_addr,
    // this quadrant's SU quarter: inject (request registered at the pins; the SU answers on inj_d INJLAT edges after the
    // engine's request edge, i.e. INJLAT - 1 edges after it sees the request) and delivery
    output reg  [INJ*16-1:0]    inj_idx,
    output reg  [INJ-1:0]       inj_rd,
    input  wire [INJ*FW-1:0]    inj_d,
    output wire [DEL-1:0]       del_valid,
    output wire [DEL*PWT-1:0]   del_flit,
    output wire [DEL*40-1:0]    hgi_del_obase,
    output reg                  fault,
    output wire [31:0]          stat_credit_stall,
    // rail links (hfd_lk_ep k of this quadrant)
    output wire [NPT-1:0]       lk_tx_v,
    output wire [NPT*PWT-1:0]   lk_tx_flit,
    output wire [NPT-1:0]       lk_rx_credit,
    input  wire [NPT-1:0]       lk_rx_v,
    input  wire [NPT*PWT-1:0]   lk_rx_flit,
    input  wire [NPT-1:0]       lk_sw_cr,
    output reg  [NPT*24-1:0]    lk_session,
    input  wire [NPT-1:0]       lk_fault,
    input  wire [NPT-1:0]       lk_locked,
    output reg  [2*NPT-1:0]     lk_status,
    // peer ring (2 x 2, registered)
    input  wire [RW-1:0]        pr_cw_i,
    output wire [RW-1:0]        pr_cw_o,
    input  wire [RW-1:0]        pr_ccw_i,
    output wire [RW-1:0]        pr_ccw_o,
    // RED_CARRY client (this quadrant's SU)
    input  wire                 rc_v,
    output wire                 rc_rdy,
    input  wire [2:0]           rc_tag,
    input  wire                 rc_mode,
    input  wire [255:0]         rc_d,
    output wire                 rr_v,
    output wire [2:0]           rr_tag,
    output wire [255:0]         rr_d,
    // TOPK_MERGE sink line writes (TKM = 1) -> ot_hgi_coll_vmport beside the SW slice, credit flow
    output wire                 tkw_t_v,
    output wire [FW+55:0]       tkw_t_d,        // {addr 40, mask 16, data FW}
    input  wire                 tkw_f_cr,
    // RGX memory lanes
    output wire [75:0]          rgx_xq,
    input  wire [513:0]         rgx_xr,
    output wire [337:0]         rgx_vmq,
    input  wire [273:0]         rgx_vmr,
    // ROW_GATHER writes -> ot_hgi_coll_rgx_snkm beside the SW slice (credit flow, any relay count; ot_hgi_coll_rgx_wtx)
    output wire [DEL-1:0]       rgx_t_v,
    output wire [DEL*40-1:0]    rgx_t_addr,
    output wire [DEL*FW-1:0]    rgx_t_data,
    output wire                 rgx_t_vm,
    input  wire [DEL-1:0]       rgx_f_cr,
    input  wire                 rgx_f_fault
);
    // ---- record queue -------------------------------------------------------------------------------------------
    localparam integer RQW = 967 + 554;      // record without its valid bit, plus recx
    reg [RQW-1:0] rq [0:RQD-1]; reg [$clog2(RQD+1)-1:0] rq_n; reg [$clog2(RQD)-1:0] rq_h, rq_t;
    reg rq_ovf;
    wire [2:0] e_ret;                        // the body's {fault, done, ready}
    wire       head_v = (rq_n != 0);
    wire       pop = head_v && e_ret[0];
    reg  [1:0] qid_q; always @(posedge clk) qid_q <= qid;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rq_n <= '0; rq_h <= '0; rq_t <= '0; rq_ovf <= 1'b0; end
        else begin : rqs
            reg [$clog2(RQD+1)-1:0] n;
            n = rq_n;
            if (hgi_rec[0]) begin
                if (n == RQD[$clog2(RQD+1)-1:0]) rq_ovf <= 1'b1;
                else begin rq[rq_t] <= {hgi_recx, hgi_rec[967:1]}; rq_t <= (rq_t == RQD - 1) ? '0 : rq_t + 1'b1; n = n + 1'b1; end
            end
            if (pop) begin rq_h <= (rq_h == RQD - 1) ? '0 : rq_h + 1'b1; n = n - 1'b1; end
            rq_n <= n;
        end
    wire [RQW-1:0] hd = rq[rq_h];
    // ---- body ---------------------------------------------------------------------------------------------------------
    wire ep_fault, snk_fault;
    wire [INJ*16-1:0] e_inj_idx; wire [INJ-1:0] e_inj_rd; wire [INJ*80-1:0] e_inj_addr;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin inj_rd <= '0; inj_idx <= '0; hgi_inj_addr <= '0; end
        else begin inj_rd <= e_inj_rd; inj_idx <= e_inj_idx; hgi_inj_addr <= e_inj_addr; end
    wire tk_w_v, tk_w_rdy, tk_w_idle, tkw_fault; wire [39:0] tk_w_addr; wire [15:0] tk_w_mask; wire [FW-1:0] tk_w_data;
    wire rg_lq_v, rg_lq_rdy, rg_lr_v, rg_w_vm, rg_w_idle;
    wire [31:0] rg_lq_addr; wire [511:0] rg_lr_data, rg_hr_data;
    wire [1:0] rg_hq_v, rg_hq_rdy, rg_hr_v; wire [69:0] rg_hq_addr; wire [15:0] rg_hq_tag, rg_hr_tag;
    wire [DEL-1:0] rg_w_v, rg_w_rdy; wire [DEL*40-1:0] rg_w_addr; wire [DEL*FW-1:0] rg_w_data;
    wire [93:0] rowfmt_o;
    ot_hgi_coll_qep #(.TKM_NATIVE(TKM_NATIVE), .INJLAT(INJLAT), .QSOLO(QSOLO), .SOLO_CAP(SOLO_CAP), .MUT_Q(MUT_Q), .NPT(NPT), .SWCRED(SWCRED), .RXAW(8), .QAW(7), .TXAW(3), .PIPE(1),
                      .RGXHW(1), .RFMT(0), .TKM(TKM), .TKM_KMAX(TKM_KMAX), .INJ(INJ), .DEL(DEL), .LANES(LANES)) u_ep (
        .clk(clk), .rst_n(rst_n), .tkm_clk_core(tkm_clk_core), .tkm_clk_buffer(tkm_clk_buffer), .tkm_clk_packer(tkm_clk_packer), .tkm_clk_lane(tkm_clk_lane), .tkm_clk_tile(tkm_clk_tile), .pclk(clk), .prst_n(rst_n), .qid(qid_q), .rank(8'd0), .pf(16'd0), .go(1'b0),
        .inj_idx(e_inj_idx), .inj_rd(e_inj_rd), .inj_q({{(3*INJ*FW){1'b0}}, inj_d}),
        .ph_tx_v(lk_tx_v), .ph_tx_flit(lk_tx_flit), .sw_cr_ret(lk_sw_cr), .ph_rx_v(lk_rx_v), .ph_rx_flit(lk_rx_flit),
        .rx_credit(lk_rx_credit), .del_valid(del_valid), .del_flit(del_flit), .fault(ep_fault),
        .stat_credit_stall(stat_credit_stall), .hgi_rec({hd[966:0], head_v}), .hgi_ret(e_ret), .hgi_cfg(hgi_cfg),
        .hgi_rowfmt_o(rowfmt_o), .hgi_rowfmt_i(3'b000), .hgi_vmaddr(hgi_vmaddr), .hgi_del_obase(hgi_del_obase),
        .rg_lq_v(rg_lq_v), .rg_lq_rdy(rg_lq_rdy), .rg_lq_addr(rg_lq_addr), .rg_lr_v(rg_lr_v), .rg_lr_data(rg_lr_data),
        .rg_hq_v(rg_hq_v), .rg_hq_rdy(rg_hq_rdy), .rg_hq_addr(rg_hq_addr), .rg_hq_tag(rg_hq_tag),
        .rg_hr_v(rg_hr_v), .rg_hr_tag(rg_hr_tag), .rg_hr_data(rg_hr_data),
        .rg_w_v(rg_w_v), .rg_w_addr(rg_w_addr), .rg_w_vm(rg_w_vm), .rg_w_data(rg_w_data), .rg_w_rdy(rg_w_rdy), .rg_w_idle(rg_w_idle),
        .hgi_recx(hd[RQW-1 -: 554]), .hgi_inj_addr(e_inj_addr),
        .tk_w_v(tk_w_v), .tk_w_addr(tk_w_addr), .tk_w_mask(tk_w_mask), .tk_w_data(tk_w_data), .tk_w_rdy(tk_w_rdy),
        .tk_w_idle(tk_w_idle));
    // TOPK line writes: credit flow to the VM port (a valid / ready pair can not cross relays)
    generate if (TKM != 0) begin : g_tkw
        ot_hgi_coll_crl_tx #(.W(FW + 56), .CRD(TKW_CRD)) u_tkw (.clk(clk), .rst_n(rst_n), .in_v(tk_w_v),
            .in_d({tk_w_addr, tk_w_mask, tk_w_data}), .in_rdy(tk_w_rdy), .idle(tk_w_idle), .t_v(tkw_t_v), .t_d(tkw_t_d),
            .f_cr(tkw_f_cr), .fault(tkw_fault));
    end else begin : g_notkw
        assign tk_w_rdy = 1'b0; assign tk_w_idle = 1'b1; assign tkw_fault = 1'b0; assign tkw_t_v = 1'b0; assign tkw_t_d = '0;
    end endgenerate
    generate if (SOLO_CAP != 0) begin : g_rgx
        ot_hgi_coll_rgx_hbm u_rh (.clk(clk), .rst_n(rst_n),
            .rg_hq_v(rg_hq_v), .rg_hq_rdy(rg_hq_rdy), .rg_hq_addr(rg_hq_addr), .rg_hq_tag(rg_hq_tag),
            .rg_hr_v(rg_hr_v), .rg_hr_tag(rg_hr_tag), .rg_hr_data(rg_hr_data),
            .rg_lq_v(rg_lq_v), .rg_lq_rdy(rg_lq_rdy), .rg_lq_addr(rg_lq_addr), .rg_lr_v(rg_lr_v), .rg_lr_data(rg_lr_data),
            .xq(rgx_xq), .xr(rgx_xr), .vmq(rgx_vmq), .vmr(rgx_vmr));
        ot_hgi_coll_rgx_wtx #(.DEL(DEL), .FW(FW), .CRD(RGX_CRD)) u_rw (.clk(clk), .rst_n(rst_n),
            .rg_w_v(rg_w_v), .rg_w_addr(rg_w_addr), .rg_w_vm(rg_w_vm), .rg_w_data(rg_w_data), .rg_w_rdy(rg_w_rdy), .idle(rg_w_idle),
            .t_v(rgx_t_v), .t_addr(rgx_t_addr), .t_data(rgx_t_data), .t_vm(rgx_t_vm), .f_cr(rgx_f_cr), .f_fault(rgx_f_fault),
            .fault(snk_fault));
    end else begin : g_norgx
        // never QSOLO: the body issues no RGX request (qrec solo = 0), so the memory lanes do not exist on this master
        assign rg_hq_rdy = 2'b00; assign rg_hr_v = 2'b00; assign rg_hr_tag = 16'd0; assign rg_hr_data = 512'd0;
        assign rg_lq_rdy = 1'b0; assign rg_lr_v = 1'b0; assign rg_lr_data = 512'd0; assign rg_w_rdy = {DEL{1'b0}}; assign rg_w_idle = 1'b1;
        assign snk_fault = 1'b0;
        assign rgx_xq = 76'd0; assign rgx_vmq = 338'd0; assign rgx_t_v = '0; assign rgx_t_addr = '0; assign rgx_t_data = '0; assign rgx_t_vm = 1'b0;
    end endgenerate
    wire [31:0] sess_w;
    ot_hgi_cfg_rx #(.W0(SESSION_W0), .NW(1), .RST(32'd0)) u_sess (.clk(clk), .rst_n(rst_n), .bus(hgi_cfg), .act(sess_w));
    always @(posedge clk) lk_session <= {NPT{sess_w[23:0]}};
    // ---- peer ring stop ---------------------------------------------------------------------------------------------
    wire [3:0] h_pop, h_done, h_fault; wire ring_fault;
    reg e_fault;
    ot_hgi_coll_pring #(.SPLIT_CLOCKS(PR_SPLIT_CLOCKS), .HOME(HOME), .MUT_CARRY(MUT_CARRY), .MUT_ORDER(MUT_ORDER), .RW(RW)) u_ring (
        .clk(clk), .rst_n(rst_n), .clk_state(pr_clk_state), .clk_add(pr_clk_add), .qid(qid_q), .cw_i(pr_cw_i), .cw_o(pr_cw_o), .ccw_i(pr_ccw_i), .ccw_o(pr_ccw_o),
        .ev_pop(pop), .ev_done(e_ret[1]), .ev_fault(e_fault), .h_pop(h_pop), .h_done(h_done), .h_fault(h_fault),
        .rc_v(rc_v), .rc_rdy(rc_rdy), .rc_tag(rc_tag), .rc_mode(rc_mode), .rc_d(rc_d),
        .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d), .fault(ring_fault));
    // ---- HOME: credits and in-order completion of all four quadrants ------------------------------------------------
    reg [$clog2(RQD+1)-1:0] cr [0:3];
    reg [7:0] dn [0:3];                       // completions not yet combined, per quadrant
    wire      all_cr = (cr[0] != 0) && (cr[1] != 0) && (cr[2] != 0) && (cr[3] != 0);
    wire      all_dn = (dn[0] != 0) && (dn[1] != 0) && (dn[2] != 0) && (dn[3] != 0);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (integer q = 0; q < 4; q = q + 1) begin cr[q] <= RQD[$clog2(RQD+1)-1:0]; dn[q] <= 8'd0; end
            hgi_ret <= 3'b000; fault <= 1'b0; lk_status <= '0; e_fault <= 1'b0;
        end else begin
            e_fault <= e_fault | ep_fault | snk_fault | tkw_fault | (|lk_fault) | rq_ovf | ring_fault | e_ret[2];   // sticky until rst_n
            fault <= e_fault | ((qid_q == 2'(HOME)) ? (|h_fault) : 1'b0);
            lk_status <= {lk_locked, lk_fault};
            for (integer q = 0; q < 4; q = q + 1) begin
                cr[q] <= cr[q] - ((hgi_rec[0] && qid_q == 2'(HOME)) ? 1'b1 : 1'b0) + (h_pop[q] ? 1'b1 : 1'b0);
                dn[q] <= dn[q] + (h_done[q] ? 8'd1 : 8'd0) - (all_dn ? 8'd1 : 8'd0);
            end
            // ready is registered: it already accounts for a record arriving this edge (two back-to-back records need
            // two free slots everywhere)
            hgi_ret <= {(|h_fault) | e_fault, all_dn, all_cr && !(hgi_rec[0] && (cr[0] == 1 || cr[1] == 1 || cr[2] == 1 || cr[3] == 1))};
        end
endmodule
`default_nettype wire
