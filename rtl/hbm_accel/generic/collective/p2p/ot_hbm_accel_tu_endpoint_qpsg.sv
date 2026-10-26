`timescale 1ns/1ps
// HISTORICAL (OWNER 2026-10-14T23:16 HANDOFF 0an): credit/ready flow control on an on-chip HBM path. Diagnostic/component
// evidence only; NOT the production schedule. Being replaced by compiler-assigned fixed transfer slots (H-COLL plan, el1014-hbm-p2p-coll.log).
// ---------------------------------------------------------------------------
// ot_hbm_accel_tu_endpoint_qpsg (HBM peer-to-peer step 1, 2026-10-14): the quadrant engine's endpoint, derived from
// rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv @ main d2940fc0a (that file is untouched).  ONE difference, the die-
// level SU inject contract (AUDIT N11): the original reads inj_data in the SAME edge as inj_rd / inj_idx (an SU adjacent
// to the hub, zero latency), which no die net through relays can provide.  INJLAT = L > 0: the SU answers each
// {inj_rd, inj_idx} with its data exactly L edges later (fixed latency, no back-pressure: L = relays out + the SU's
// fixed VM read + relays back); the flit's {ordinal, index} enters the HUBW wire-stage line at the request as before and
// its data joins at stage L (a HUBW - L line), so the flit leaves the hub at the same edge as with L = 0: ZERO added
// cycles, the transport is already priced in HUBW.  RGX source data (internal, rs_data) is delayed L edges to the same
// join.  L = 0 elaborates the original.  Legal 0 <= L <= HUBW - 4.
// ---------------------------------------------------------------------------
module ot_hbm_accel_tu_endpoint_qpsg #(
    parameter integer ENABLE = 0,
    parameter integer REARM = 0, // opt-in; production pclk must equal clk
    parameter integer RGX = 0,     // 1: ROW_GATHER hardware mode available (rgx pin, stream inject, K*F delivery set)
    parameter integer DELCRED = 0, // 1: delivery lanes dispatched only with del_permit (sink credits)
    parameter integer MUT_NOGATE = 0, // bench mutant: no own-queue inject gate

    parameter integer NC     = 8,
    parameter integer NOG    = 8,
    parameter integer PFMAX  = 64,
    parameter integer LANES  = 16,
    parameter integer BF16   = 1,
    parameter integer BF16RT = 0,   // hgi-takeover F2: 1 = the result packing follows the bf16 pin per collective (O.fmt)
    parameter integer NPT    = 8,
    parameter integer INJ    = 2,
    parameter integer DEL    = 4,
    parameter integer HUBW   = 35,
    parameter integer INJLAT = 0,   // P2P: SU inject data latency (edges after inj_rd); 0 = same edge (original)
    parameter integer WSTG   = 14,
    parameter integer BITS_X100 = 72000,
    parameter integer PWB    = 545,
    parameter integer RXAW   = 8,
    parameter integer QAW    = 7,
    parameter integer TXAW   = 3,
    parameter integer SYNCPHY = 0,   // 1: pclk IS clk (the hfd_coll die view): 2-entry sync FIFOs replace the CDC FIFOs
    parameter integer SWCRED = 256,
    parameter integer LAT    = 7,
    parameter integer FW     = 32 * LANES,
    parameter integer PWT    = FW + 33,
    parameter integer PIPE   = 0    // hgi-unitrate: 1 = pipelined gather bypass (epoch-tagged multicast, see below)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 pclk,            // this die's PHY (serializer) clock
    input  wire                 prst_n,
    input  wire [7:0]           rank,
    input  wire [7:0]           mcast_group_size, // static outer membership 2/4/8/96, ignored when mcast_all=0
    input  wire                 mcast_all, // validated GROUP_REDUCE_MCAST
    input  wire [3:0]           gsz,      // static: 4'hF legacy (DS, reset), 0..3 = log2 group size
    input  wire                 byp,      // static: 1 = exact gather bypass (no adder), see the header
    input  wire                 res_bf16, // BF16RT = 1: reduced results packed BF16 (1) or FP32 (0) this collective
    input  wire [15:0]          pf,              // flits per contributor this collective (runtime)
    input  wire                 go,
    output wire                 start_ready,
    output wire                 done_valid,
    input  wire                 done_ready,
    input  wire                 fault_ack,
    output wire [INJ*16-1:0]    inj_idx,
    output wire [INJ-1:0]       inj_rd,
    input  wire [INJ*FW-1:0]    inj_data,
    // switch side, PHY clock: one flit a pclk at most per port, after the serializer
    output wire [NPT-1:0]       ph_tx_v,
    output wire [NPT*PWT-1:0]   ph_tx_flit,
    input  wire [NPT-1:0]       sw_cr_ret,       // switch ingress credit return (core clock)
    input  wire [NPT-1:0]       ph_rx_v,         // from the switch egress (PHY clock)
    input  wire [NPT*PWT-1:0]   ph_rx_flit,
    output wire [NPT-1:0]       rx_credit,       // receive-buffer pop (core clock) -> switch egress credit
    output wire [DEL-1:0]       del_valid,
    output wire [DEL*PWT-1:0]   del_flit,
    // ROW_GATHER hardware mode (RGX = 1) and delivery credits (DELCRED = 1); unused otherwise
    input  wire                 rgx,             // static (latched at go): ROW_GATHER stream mode, needs byp
    input  wire [16:0]          rgx_total,       // K * F: flits every rank of the group receives
    input  wire                 rs_v,
    input  wire [15:0]          rs_gi,
    input  wire [FW-1:0]        rs_data,
    output wire                 rs_rdy,
    input  wire                 rs_end,          // the source has no further flit this collective (level)
    input  wire [DEL-1:0]       del_permit,
    output wire [DEL-1:0]       del_reserve,
    output wire                 fault,
    output wire [31:0]          stat_credit_stall,
    // PIPELINED GATHER BYPASS (PIPE = 1, hgi-unitrate 2026-10-10).  A bypass collective started with pipe = 1 carries
    // the epoch tag pipe_tag (latched at go) in every flit it sends: dst = {5'b11110, tag} (multicast: the switch
    // tier multicasts every dst >= 0xF0; reductions keep 0xFF).  This endpoint only INJECTS it: start_ready_p is high
    // again once its pf flits have left the hub (pipe_inj_done pulses with the tag), while its flits are still
    // crossing; every received or own flit with a pipe dst is delivered unconditionally (no group filter, no
    // completion accounting here): the block above (ot_hgi_coll_ep PIPE) owns per-epoch delivery, parking of
    // early epochs, completion and in-order retirement.  Classic collectives are unchanged (and run only when the
    // block has no pipelined epoch open).
    input  wire                 pipe,
    input  wire [2:0]           pipe_tag,
    output wire                 start_ready_p,
    output reg                  pipe_inj_done,
    output reg  [2:0]           pipe_inj_tag
);
    localparam integer LV   = $clog2(NC);
    localparam integer OFMX = PFMAX / NC;

    generate if (ENABLE == 0) begin : g_off
        assign inj_idx = '0; assign inj_rd = '0; assign ph_tx_v = '0; assign ph_tx_flit = '0;
        assign rx_credit = '0; assign del_valid = '0; assign del_flit = '0; assign fault = 1'b0;
        assign stat_credit_stall = 0; assign start_ready = 0; assign done_valid = 0; assign start_ready_p = 0;
        assign rs_rdy = 1'b0; assign del_reserve = '0;
        always @* begin pipe_inj_done = 1'b0; pipe_inj_tag = 3'd0; end
    end else begin : g_on
        reg [7:0] run_rank; reg [15:0] run_pf; reg [3:0] run_gsz; reg run_mcast; reg[7:0]run_outer; reg run_byp; reg run_bf16;
        reg run_pipe; reg [2:0] run_tag;          // PIPE: this run is a pipelined bypass, its epoch tag
        wire [7:0] PDST = {5'b11110, run_tag};
        reg run_rgx; reg [16:0] run_total;
        reg pending_start, completed, started;
        reg [15:0] rx_pending;
        wire active_desc = REARM && (started || pending_start || completed);
        wire [7:0] eff_rank = active_desc ? run_rank : rank;
        wire [15:0] eff_pf = active_desc ? run_pf : pf;
        wire [3:0] eff_gsz = active_desc ? run_gsz : gsz;
        wire ALL_DEST = active_desc ? run_mcast : mcast_all;
        wire BYP = active_desc ? run_byp : byp;
        wire RGXM = (RGX != 0) && (active_desc ? run_rgx : rgx);
        wire [16:0] RTOT = active_desc ? run_total : rgx_total;
        wire BFX = BF16RT ? (active_desc ? run_bf16 : res_bf16) : (BF16 != 0);
        wire[7:0] OUTER_G = active_desc ? run_outer : mcast_group_size;
        wire[3:0] OUTER_LG = (OUTER_G==2) ? 1 : (OUTER_G==4) ? 2 : 3;
        wire [31:0] RANK = {24'b0, eff_rank};
        wire LEG = (eff_gsz == 4'hF);
        wire[31:0] OUTER_BASE = (OUTER_G==96) ? 0 : ((RANK >> OUTER_LG) << OUTER_LG);
        wire MODE_OK = (LEG || ((eff_gsz <= 3) && ((32'd1 << eff_gsz) <= NC))) && (!ALL_DEST || (!LEG && eff_gsz >= 1 && eff_gsz <= 3 &&
            (OUTER_G==2 || OUTER_G==4 || OUTER_G==8 || OUTER_G==96) && OUTER_G <= NOG*NC && (32'd1<<eff_gsz)<=OUTER_G));
        // gather bypass group: GN ranks from GBASE (outer group with mcast_all, else the 2^gsz aligned group)
        wire [31:0] GN = ALL_DEST ? {24'd0, OUTER_G} : (32'd1 << eff_gsz[1:0]);
        wire [31:0] GBASE = ALL_DEST ? OUTER_BASE : ((RANK >> eff_gsz[1:0]) << eff_gsz[1:0]);
        wire BYP_OK = !LEG && (ALL_DEST ? ((OUTER_G==2 || OUTER_G==4 || OUTER_G==8 || OUTER_G==96) && OUTER_G <= NOG*NC) :
                                          (eff_gsz <= 3 && (32'd1 << eff_gsz) <= NOG*NC));
        wire BYP_PAY_OK = RGXM ? (BYP && RTOT != 0 && RTOT <= 17'h10000 && RANK < NOG * NC) :
                                 ((eff_pf != 0) && (eff_pf <= PFMAX) && (RANK < NOG * NC));
        wire [31:0] REQ_NA = LEG ? NC : (MODE_OK ? (32'd1 << eff_gsz) : 1);
        // Valid small groups have power-of-two NA. Avoid synthesizing a general32-bit divider
        // merely to validate a descriptor; legacy NC remains a constant-expression divisor.
        wire [31:0] req_of = LEG ? ({16'd0,eff_pf} / NC) : ({16'd0,eff_pf} >> eff_gsz);
        wire req_aligned = LEG ? (({16'd0,eff_pf} % NC) == 0) :
                                 (({16'd0,eff_pf} & ((32'd1 << eff_gsz) - 1)) == 0);
        wire PAYLOAD_OK = (eff_pf != 0) && (eff_pf <= PFMAX) && (RANK < NOG * NC) && req_aligned &&
                         (req_of <= OFMX) && (!BFX || !req_of[0]);
`ifdef OT_COLL_MUT_MODE_GUARD
        wire ACCEPT_MODE = 1'b1;
`else
        wire ACCEPT_MODE = BYP ? (BYP_OK && BYP_PAY_OK) : (MODE_OK && PAYLOAD_OK);
`endif
        reg mode_error;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) mode_error <= 1'b0;
            else if (REARM && fault_ack && !started && !pending_start) mode_error <= 1'b0;
            else if (go && (!REARM || (pipe && PIPE != 0 ? start_ready_p : start_ready)) && !ACCEPT_MODE) mode_error <= 1'b1;
        wire [3:0] LG = LEG ? 4'($clog2(NC)) : (MODE_OK ? eff_gsz : 4'd0);
        wire [31:0] NA = LEG ? NC : (32'd1 << LG);              // active contributors
        wire [31:0] OG = LEG ? RANK / NC : RANK >> LG, J = LEG ? RANK % NC : RANK & (NA - 1);
        wire CONTRIB = LEG ? (RANK < NOG * NC) : 1'b1;
        wire [31:0] PF = {16'b0, eff_pf};
        wire [31:0] OF = LEG ? PF / NC : PF >> LG;
        wire [31:0] ROF = BFX ? OF / 2 : OF;
        // registered run constants (hbm-coll-rtl): rank and pf are static during a collective, so the runtime
        // multiplies and the f / OF, f % OF divisions become compares / adds against these flops (exact; they settle
        // one edge after rank / pf, before the first injection)
        reg [15:0] mOF [0:NC];
        reg [15:0] cOGPF, cGI0, cBYP0;
        reg [16:0] cBYPT;
        always @(posedge clk) begin
            for (integer m = 0; m <= NC; m = m + 1) mOF[m] <= 16'(m * OF);
            cOGPF <= 16'(OG * PF);
            cGI0  <= 16'((OG * NA + J) * ROF);
`ifdef OT_COLL_MUT_BYP_GI
            cBYP0 <= 16'd0;                                   // NEGATIVE: every rank's segment at gi 0 .. pf-1
`else
            cBYP0 <= RGXM ? 16'd0 : 16'((RANK - GBASE) * PF);     // ROW_GATHER: the source's gi is final
`endif
            cBYPT <= RGXM ? RTOT : 17'(GN * PF);
        end

        // ================= hub issue -> HUBW wire stages ==========================================
        integer k;
        assign start_ready = !started && (!REARM || (!pending_start && !completed && !fault && rx_pending == 0 && !(|ph_rx_v)));
        assign start_ready_p = (PIPE != 0) && REARM && !started && !pending_start && !completed && !fault;
        assign done_valid = REARM && completed;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin pending_start<=0; run_rank<=0;run_pf<=0;run_gsz<=15;run_mcast<=0;run_outer<=96;run_byp<=0;run_bf16<=1;run_pipe<=0;run_tag<=0;run_rgx<=0;run_total<=0;end
            else if (REARM) begin
                if (go && (pipe && PIPE != 0 ? start_ready_p : start_ready) && ACCEPT_MODE) begin
                    run_pipe <= (PIPE != 0) && pipe && byp; run_tag <= pipe_tag;
                    run_rank<=rank;run_pf<=pf;run_gsz<=gsz;run_mcast<=mcast_all;run_outer<=mcast_group_size;run_byp<=byp;run_bf16<=res_bf16;pending_start<=1;
                    run_rgx<=(RGX != 0) && rgx; run_total<=rgx_total;
                end else if(pending_start) pending_start<=0;
            end
        // own-queue inject gate (bypass): the own delivery queue (2^QAW SRAM + 4 head) must hold every flit in the hub flight
        wire [QAW:0] dc0;
        // hub flits in flight: injected (classic reads, or RGX source flits), not yet out of the HUBW stages.  RGX's own-
        // queue gate (bypass) and PIPE's injection-done both read it (merged: one counter over every injection lane)
        wire [INJ-1:0] h_v;
        reg  [7:0]   hub_fl;
        wire own_room = (MUT_NOGATE != 0) || (32'(dc0) + 32'(hub_fl) + 32'd6 < (32'd1 << QAW));
        reg  src_end;                            // RGX: the source closed its stream
        wire rs_fire = RGXM && BYP && started && !completed && !src_end && own_room && rs_v;
        assign rs_rdy = RGXM && BYP && started && !completed && !src_end && own_room;
        reg [INJ*16-1:0] r_idx;
        reg [INJ-1:0] r_rd;
        always @* begin
            r_idx = '0; r_rd = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (CONTRIB && started && !RGXM && k + i < PF && ((!BYP && (LEG || NA > 1)) || (i == 0 && own_room))) begin
                    r_rd[i] = 1'b1;           // rotated slice order: own slice last in each round
                    r_idx[16*i +: 16] = (NC == 1 || BYP) ? 16'(k + i) : LEG ?
                        16'(mOF[(J + 1 + 32'((k + i) % NC)) % NC] + 16'((k + i) / NC)) :
                        16'(mOF[(J + 1 + (32'(k + i) & (NA - 1))) & (NA - 1)] + 16'(32'(k + i) >> LG));
                end
        end
        assign inj_idx = r_idx;
        assign inj_rd  = r_rd;
        // PIPE: hub flits in flight (injected, not yet out of the HUBW stages); a pipelined run's injection is done
        // when all pf flits are read AND have left the hub (its run constants and tag are then free for the next)
        wire pipe_done_now = run_pipe && started && !pending_start && k >= PF && hub_fl == 8'd0 && !(|r_rd);
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin hub_fl <= 8'd0; pipe_inj_done <= 1'b0; pipe_inj_tag <= 3'd0; end
            else begin
                hub_fl <= hub_fl + 8'($countones(r_rd)) + 8'(rs_fire) - 8'($countones(h_v));
                pipe_inj_done <= pipe_done_now; pipe_inj_tag <= run_tag;
            end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin k <= 0; started <= 1'b0; end
            else begin
                if (REARM) begin
                    if(pending_start) started<=1'b1;
                    if(completed && done_ready) begin started<=0;k<=0;end
                    if(pipe_done_now) begin started<=0;k<=0;end
                end else if (go && !started && ACCEPT_MODE) started <= 1'b1;
                if (|r_rd) k <= k + ((!BYP && (LEG || NA > 1)) ? INJ : 1);
                if (rs_fire) k <= k + 1;
            end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) src_end <= 1'b0;
            else begin
                if (RGXM && started && rs_end && !rs_v) src_end <= 1'b1;
                if (REARM && completed && done_ready) src_end <= 1'b0;
            end
        wire [INJ*(16+16+FW)-1:0] h_d;   // {injection ordinal, flit index, data}
        // slice of each hub flit: hs = f / OF, hfo = f % OF (f < NC * OF) by compares against m * OF
        reg [7:0]  hs  [0:INJ-1];
        reg [15:0] hfo [0:INJ-1];
        always @* for (integer i = 0; i < INJ; i = i + 1) begin : slc
            reg [15:0] f;
            f = h_d[(32+FW)*i + FW +: 16];
            hs[i] = 8'd0;
            for (integer m = 1; m < NC; m = m + 1) if (f >= mOF[m]) hs[i] = 8'(m);
            hfo[i] = f - mOF[hs[i]];
        end
        for (genvar i = 0; i < INJ; i = i + 1) begin : g_hub
            wire hv_in = (i == 0) ? (r_rd[i] || rs_fire) : r_rd[i];
            if (INJLAT == 0) begin : g_l0
            wire [32+FW-1:0] hd_in = (i == 0 && RGXM) ? {16'(k), rs_gi, rs_data} : {16'(k + i), r_idx[16*i +: 16], inj_data[FW*i +: FW]};
            (* keep_hierarchy *) ot_hcoll_sdelay #(.W(32 + FW), .D(HUBW)) u_h (.clk(clk), .rst_n(rst_n), .v_in(hv_in),
                .d_in(hd_in), .v_out(h_v[i]),
                .d_out(h_d[(32+FW)*i +: 32+FW]));
            end else begin : g_lat
            // {ordinal, index}: the full HUBW line from the request edge; data: the SU's answer L edges later (classic) or
            // this lane's RGX source data delayed L edges, then a HUBW - L line: both leave at the same edge
            wire [31:0] hm_in = (i == 0 && RGXM) ? {16'(k), rs_gi} : {16'(k + i), r_idx[16*i +: 16]};
            reg  [INJLAT-1:0] lv; reg [INJLAT-1:0] lr;            // valid / "RGX flit" a stage, request -> data join
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin lv <= '0; lr <= '0; end
                else begin lv <= INJLAT'({lv, hv_in}); lr <= INJLAT'({lr, (i == 0) && RGXM}); end
            wire [FW-1:0] rs_late;
            if (i == 0) begin : g_rsl
                if (INJLAT >= 4) begin : g_sd
                    (* keep_hierarchy *) ot_hcoll_sdelay #(.W(FW), .D(INJLAT)) u_rl (.clk(clk), .rst_n(rst_n), .v_in(rs_fire),
                        .d_in(rs_data), .v_out(), .d_out(rs_late));
                end else begin : g_sh
                    reg [FW-1:0] sh [0:INJLAT-1];
                    always @(posedge clk) begin sh[0] <= rs_data; for (integer j = 1; j < INJLAT; j = j + 1) sh[j] <= sh[j-1]; end
                    assign rs_late = sh[INJLAT-1];
                end
            end else begin : g_nrs
                assign rs_late = {FW{1'b0}};
            end
            wire [FW-1:0] hdat_in = lr[INJLAT-1] ? rs_late : inj_data[FW*i +: FW];
            wire [31:0] hm_out; wire [FW-1:0] hdat_out;
            (* keep_hierarchy *) ot_hcoll_sdelay #(.W(32), .D(HUBW)) u_hm (.clk(clk), .rst_n(rst_n), .v_in(hv_in),
                .d_in(hm_in), .v_out(h_v[i]), .d_out(hm_out));
            (* keep_hierarchy *) ot_hcoll_sdelay #(.W(FW), .D(HUBW - INJLAT)) u_hd (.clk(clk), .rst_n(rst_n), .v_in(lv[INJLAT-1]),
                .d_in(hdat_in), .v_out(), .d_out(hdat_out));
            assign h_d[(32+FW)*i +: 32+FW] = {hm_out, hdat_out};
            end
        end

        // ================= per-port slices (ot_hcoll_port, hardened once, 8 instances) ===============
        // core side of each slice boundary: push / din leave core flops (+1 edge), the receive-buffer head lands in a
        // core input flop and a K = 8 head FIFO whose pops return credits through a core output flop.
        reg  [NPT-1:0] qp_push, qr_push;
        reg  [PWT-1:0] qp_din [0:NPT-1];
        reg  [PWT-1:0] qr_din [0:NPT-1];
        reg  [NPT-1:0] qp_push_q, qr_push_q, rbcr_q, lv_q, any_stall;
        reg  [PWT-1:0] qp_din_q [0:NPT-1];
        reg  [PWT-1:0] qr_din_q [0:NPT-1];
        reg  [PWT-1:0] ld_q [0:NPT-1];
        reg  [31:0] cstall;
        reg  [NPT-1:0] rb_pop;
        wire [NPT-1:0] rb_empty, rb_ovf, pstall, pfault, s_rbv;
        wire [PWT-1:0] rb_head [0:NPT-1];
        wire [PWT-1:0] s_rbd [0:NPT-1];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin qp_push_q <= '0; qr_push_q <= '0; rbcr_q <= '0; lv_q <= '0; cstall <= 0; end
            else begin
                qp_push_q <= qp_push; qr_push_q <= qr_push; rbcr_q <= rb_pop & ~rb_empty; lv_q <= s_rbv;
                if (|pstall) cstall <= cstall + 1;
            end
        always @(posedge clk)
            for (integer p = 0; p < NPT; p = p + 1) begin qp_din_q[p] <= qp_din[p]; qr_din_q[p] <= qr_din[p]; ld_q[p] <= s_rbd[p]; end
`ifndef SYNTHESIS
        // [link] 2026-10-10: SWCRED is the slice's switch-ingress credit pool = the downstream TX buffer (hfd_lk_ep TXQ); the
        // RTL slice takes it as a parameter, a hardened slice (OT_HCOLL_PORT_HARD) is built at OT_HCOLL_PORT_HARD_SWCRED
        // (default 256): a mismatch with SWCRED still fatals.  RXAW stays the slice's 8 (256-flit SRAM receive buffer).
`ifdef OT_HCOLL_PORT_HARD
`ifndef OT_HCOLL_PORT_HARD_SWCRED
`define OT_HCOLL_PORT_HARD_SWCRED 256
`endif
        initial if (SWCRED != `OT_HCOLL_PORT_HARD_SWCRED)
            $fatal(1, "ot_hbm_accel_tu_endpoint_psg: SWCRED %0d != the hardened ot_hcoll_port's %0d", SWCRED, `OT_HCOLL_PORT_HARD_SWCRED);
`endif
        initial if (PWT != 545 || QAW != 7 || RXAW != 8 || WSTG != 14 || BITS_X100 != 72000 || PWB != 545 || SWCRED < 1)
            $fatal(1, "ot_hbm_accel_tu_endpoint_ps: the ot_hcoll_port slice is built for PWT 545 QAW 7 RXAW 8 WSTG 14 (SWCRED >= 1)");
`endif
        for (genvar p = 0; p < NPT; p = p + 1) begin : g_port
            // the slice is ONE hardened view: instantiated at its defaults (a hard macro takes no parameters)
`ifdef OT_HCOLL_PORT_HARD
            ot_hcoll_port u_port (.clk(clk), .rst_n(rst_n),
`else
            ot_hcoll_port #(.SWCRED(SWCRED)) u_port (.clk(clk), .rst_n(rst_n),
`endif
                .qp_push(qp_push_q[p]), .qp_din(qp_din_q[p]), .qr_push(qr_push_q[p]), .qr_din(qr_din_q[p]),
                .sw_cr_ret(sw_cr_ret[p]), .ph_tx_v(ph_tx_v[p]), .ph_tx_flit(ph_tx_flit[p*PWT +: PWT]),
                .ph_rx_v(ph_rx_v[p]), .ph_rx_flit(ph_rx_flit[p*PWT +: PWT]),
                .rb_v(s_rbv[p]), .rb_d(s_rbd[p]), .rb_cr(rbcr_q[p]), .stall(pstall[p]), .fault(pfault[p]));
            wire [3:0] lc;
            (* keep_hierarchy *) ot_ha2_fifo #(.W(PWT), .AW(3)) u_land (.clk(clk), .rst_n(rst_n), .push(lv_q[p]), .din(ld_q[p]),
                .pop(rb_pop[p]), .empty(rb_empty[p]), .dout(rb_head[p]), .ovf(rb_ovf[p]), .count(lc));
        end
        assign stat_credit_stall = cstall;
        assign rx_credit = rb_pop & ~rb_empty;

        // ================= operand slots and the golden reduction tree (HA2) ======================
        reg [OFMX-1:0] pres [0:NC-1];
        reg dupe;
        integer rptr;
        reg  [NC-1:0] col;
`ifdef OT_COLL_MUT_GSZ_PAD
        always @* for (integer c = 0; c < NC; c = c + 1) col[c] = (NC > 1 && rptr < OF) ? pres[c][rptr] : 1'b0;  // NEGATIVE: no pad
`else
        always @* for (integer c = 0; c < NC; c = c + 1) col[c] = (NC > 1 && rptr < OF) ? (pres[c][rptr] || c >= NA) : 1'b0;
`endif
        wire issue = &col && !BYP;
        wire [FW-1:0] lvl [0:LV][0:NC-1];
        wire [LV:0] lvv;
        reg [NC-1:0] cw_v;
        reg [$clog2(OFMX)-1:0] cw_fl [0:NC-1];
        reg [FW-1:0] cw_d [0:NC-1];
        reg cw_dupe;
        // operand slots: one array per contributor column with ONE write port (cw_*: one writer per column a cycle)
        wire [FW-1:0] opsel [0:NC-1];
        for (genvar c = 0; c < NC; c = c + 1) begin : g_col
            reg [FW-1:0] slot [0:OFMX-1];
            always @(posedge clk) if (NC > 1 && cw_v[c]) slot[cw_fl[c]] <= cw_d[c];
            assign opsel[c] = (c >= NA) ? {FW{1'b0}} : slot[rptr < OF ? rptr : 0];   // inactive columns: +0
        end
        for (genvar c = 0; c < NC; c = c + 1) begin : g_l0
            assign lvl[0][c] = opsel[c];
        end
        assign lvv[0] = issue;
        for (genvar l = 1; l <= LV; l = l + 1) begin : g_lv
            localparam integer NN = NC >> l;
            wire [NN*LANES-1:0] vv;
            wire [NN*2*LANES-1:0] ee;
            for (genvar i = 0; i < NN; i = i + 1) begin : g_n
                for (genvar ln = 0; ln < LANES; ln = ln + 1) begin : g_ln
                    (* keep_hierarchy *) ot_hdc_fp32_add_lat #(.LAT(LAT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(lvv[l-1]),
                        .a(lvl[l-1][2*i][32*ln +: 32]), .b(lvl[l-1][2*i+1][32*ln +: 32]),
                        .y(lvl[l][i][32*ln +: 32]), .err(ee[(i*LANES+ln)*2 +: 2]), .valid_out(vv[i*LANES+ln]));
                end
            end
            assign lvv[l] = vv[0];
        end
        wire        ti_v;
        wire [15:0] ti_d;
        (* keep_hierarchy *) ot_hcoll_shdelay #(.W(16), .D(LAT * LV)) u_tidx (.clk(clk), .rst_n(rst_n), .v_in(issue), .d_in(16'(rptr)),
            .v_out(ti_v), .d_out(ti_d));
        function automatic [15:0] bf16(input [31:0] b);
            reg [32:0] s;
            s = {1'b0, b} + 33'h7FFF + {32'b0, b[16]};
            bf16 = s[31:16];
        endfunction
        reg [FW-1:0] hold;
        reg          r_v;
        reg [15:0]   r_m;
        reg [FW-1:0] r_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) r_v <= 1'b0;
            else begin
                r_v <= 1'b0;
                if (NC > 1 && lvv[LV]) begin
                    if (BFX) begin
                        if (!ti_d[0]) for (integer ln = 0; ln < LANES; ln = ln + 1)
                            hold[16*ln +: 16] <= bf16(lvl[LV][0][32*ln +: 32]);
                        else begin
                            r_v <= 1'b1;
                            r_m <= ti_d >> 1;
                            for (integer ln = 0; ln < LANES; ln = ln + 1) begin
                                r_d[16*ln +: 16] <= hold[16*ln +: 16];
                                r_d[16*(LANES+ln) +: 16] <= bf16(lvl[LV][0][32*ln +: 32]);
                            end
                        end
                    end else begin
                        r_v <= 1'b1; r_m <= ti_d; r_d <= lvl[LV][0];
                    end
                end
            end
        wire [15:0] my_gi = cGI0 + r_m;
        wire [PWT-1:0] res_flit = {1'b1, 8'hFF, 8'(OG), my_gi, r_d};

        // ================= own delivery queue =====================================================
        wire dq_own_empty, dq_own_ovf;
        wire [PWT-1:0] dq_own_head;
        reg dq_own_pop;
        // bypass: the rank's own flits (hub output, one a cycle) enter the own delivery queue unchanged
        wire own_byp_v = BYP && h_v[0];
`ifdef OT_COLL_MUT_BYP_OWNSIGN
        wire [PWT-1:0] own_byp_f = {1'b1, run_pipe ? PDST : 8'hFF, 8'(RANK), cBYP0 + h_d[FW +: 16], h_d[FW-1:0] & ~{LANES{32'h80000000}}};  // NEGATIVE: sign dropped
`else
        wire [PWT-1:0] own_byp_f = {1'b1, run_pipe ? PDST : 8'hFF, 8'(RANK), cBYP0 + h_d[FW +: 16], h_d[FW-1:0]};
`endif
        (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(QAW)) u_dqo (.clk(clk), .rst_n(rst_n), .push(r_v || own_byp_v), .din(own_byp_v ? own_byp_f : res_flit),
            .pop(dq_own_pop), .empty(dq_own_empty), .dout(dq_own_head), .ovf(dq_own_ovf), .count(dc0));

        // ================= receive dispatch and delivery =========================================
        wire[NPT-1:0] result_for_group;
        for(genvar pg=0;pg<NPT;pg=pg+1)begin:g_membership
            wire[31:0] producer_base = 32'(rb_head[pg][FW+16+:8]) << LG;
            wire[31:0] src_rank = {24'd0, rb_head[pg][FW+16+:8]};
            wire is_pipe = (PIPE != 0) && rb_head[pg][PWT-1] && rb_head[pg][FW+24+3 +: 5] == 5'b11110;
            assign result_for_group[pg] = is_pipe ? 1'b1 : BYP ? (src_rank >= GBASE && src_rank < GBASE + GN) : LEG || (ALL_DEST ?
                (producer_base>=OUTER_BASE && producer_base<OUTER_BASE+OUTER_G) :
                rb_head[pg][FW+16+:8]==8'(OG));
        end
        integer drot;
        reg [DEL-1:0] dv;
        reg [PWT-1:0] dfl [0:DEL-1];
        reg [NPT:0] rdy, dsel [0:DEL-1];
        reg [3:0] pos [0:NPT];
        reg taken;
        always @* begin : dispatch
            integer n, src, c;
            reg [NC-1:0] ctk;          // contributor columns written this cycle (one writer per column)
            rb_pop = '0; dq_own_pop = 1'b0; dv = '0; ctk = '0;
            for (integer i = 0; i < DEL; i = i + 1) dfl[i] = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (NC > 1 && !BYP && h_v[i] && integer'(hs[i]) == J) ctk[J % NC] = 1'b1;   // hub own slice first (cannot stall)
            for (integer p = 0; p < NPT; p = p + 1)
                if (!rb_empty[p] && !rb_head[p][PWT-1]) begin                    // partials -> slots
                    c = integer'(rb_head[p][FW+16 +: 8]);
                    if (c >= NA || BYP) rb_pop[p] = 1'b1;                          // malformed (or any partial in bypass): popped, flagged
                    else if (!ctk[c]) begin rb_pop[p] = 1'b1; ctk[c] = 1'b1; end   // else waits a cycle in rb
                end
            // Small static groups must not consume another group's multicast result.
            // Consume/drop its receive-buffer entry so credits keep moving; LEG preserves DS global assembly.
            for (integer p = 0; p < NPT; p = p + 1)
                if (!rb_empty[p] && rb_head[p][PWT-1] && !result_for_group[p]) rb_pop[p] = 1'b1;
            // delivery: the first DEL ready sources in the rotated order (drot, drot+1, ...) take lanes 0, 1, ...;
            // written as constant-index one-hot selects (lane of source s = ready sources ahead of it)
            for (integer s = 0; s <= NPT; s = s + 1) begin
                rdy[s] = (s == NPT) ? !dq_own_empty : (!rb_empty[s % NPT] && rb_head[s % NPT][PWT-1] &&
`ifdef OT_COLL_MUT_GROUP_ISOLATION
                    1'b1);
`else
                    result_for_group[s % NPT]);
`endif
                // bypass: the own delivery queue first (it is the only path of the rank's own flits and gates the
                // rank's injection; the ports back-pressure through their credits), the ports in rotation behind it
                pos[s] = BYP ? ((s == NPT) ? 4'd0 : 4'(1 + (s + NPT - (drot % NPT)) % NPT)) : 4'((s + (NPT + 1) - drot) % (NPT + 1));
            end
            for (integer s = 0; s <= NPT; s = s + 1) begin
                n = 0;
                for (integer t = 0; t <= NPT; t = t + 1) if (rdy[t] && pos[t] < pos[s]) n = n + 1;
                for (integer l = 0; l < DEL; l = l + 1) dsel[l][s] = rdy[s] && n == l && (DELCRED == 0 || del_permit[l]);
            end
            for (integer l = 0; l < DEL; l = l + 1) begin
                dv[l] = |dsel[l];
                for (integer s = 0; s <= NPT; s = s + 1)
                    if (dsel[l][s]) dfl[l] = dfl[l] | ((s == NPT) ? dq_own_head : rb_head[s % NPT]);
            end
            for (integer s = 0; s <= NPT; s = s + 1) begin
                taken = 1'b0;
                for (integer l = 0; l < DEL; l = l + 1) taken = taken | dsel[l][s];
                if (s == NPT) dq_own_pop = taken; else if (taken) rb_pop[s % NPT] = 1'b1;
            end
        end
        assign del_reserve = (DELCRED != 0) ? dv : '0;
        for (genvar i = 0; i < DEL; i = i + 1) begin : g_del
            (* keep_hierarchy *) ot_hcoll_sdelay #(.W(PWT), .D(HUBW)) u_d (.clk(clk), .rst_n(rst_n), .v_in(dv[i]), .d_in(dfl[i]),
                .v_out(del_valid[i]), .d_out(del_flit[i*PWT +: PWT]));
        end

        // ================= slot writes: one writer per contributor column (hub own slice, else one port) ===========
        always @* begin : colw
            integer c, fl;
            reg [INJ-1:0] hw;
            reg [NPT-1:0] pw;
            cw_v = '0; cw_dupe = 1'b0; hw = '0; pw = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (NC > 1 && !BYP && h_v[i] && integer'(hs[i]) == J) begin
                    hw[i] = 1'b1;
                    if (pres[J % NC][hfo[i]]) cw_dupe = 1'b1;
                end
            for (integer p = 0; p < NPT; p = p + 1)
                if (rb_pop[p] && !rb_head[p][PWT-1]) begin
                    c  = integer'(rb_head[p][FW+16 +: 8]);
                    fl = integer'(rb_head[p][FW +: 16]);
                    if (BYP || c >= NA || fl >= OF || pres[c % NC][fl[$clog2(OFMX)-1:0]] || rb_head[p][FW+24 +: 8] != 8'(RANK)) cw_dupe = 1'b1;
                    else pw[p] = 1'b1;
                end
            // one writer per column (dispatch arbitration): the column's word is the OR of its one-hot sources
            for (integer x = 0; x < NC; x = x + 1) begin
                cw_fl[x] = '0; cw_d[x] = '0;
                for (integer i = 0; i < INJ; i = i + 1)
                    if (hw[i] && J % NC == x) begin
                        cw_v[x] = 1'b1; cw_fl[x] = cw_fl[x] | hfo[i][$clog2(OFMX)-1:0]; cw_d[x] = cw_d[x] | h_d[(32+FW)*i +: FW];
                    end
                for (integer p = 0; p < NPT; p = p + 1)
                    if (pw[p] && rb_head[p][FW+16 +: 8] == 8'(x)) begin
                        cw_v[x] = 1'b1; cw_fl[x] = cw_fl[x] | rb_head[p][FW +: $clog2(OFMX)]; cw_d[x] = cw_d[x] | rb_head[p][FW-1:0];
                    end
            end
        end

        // ================= injection dispatch, result multicast, slot writes =====================
        integer rcnt;                       // results sent (stripe counter)
        always @* begin
            qp_push = '0; qr_push = '0;
            for (integer p = 0; p < NPT; p = p + 1) begin qp_din[p] = '0; qr_din[p] = '0; end
            for (integer i = 0; i < INJ; i = i + 1)
                if (h_v[i]) begin : inj
                    integer ord, f, s, pt;
                    ord = integer'(h_d[(32+FW)*i + FW + 16 +: 16]);
                    f   = integer'(h_d[(32+FW)*i + FW +: 16]);
                    pt  = ord % NPT;
                    if (NC == 1) begin            // gather: the flit IS the result; sent once, multicast
                        qr_push[pt] = 1'b1;
                        qr_din[pt] = {1'b1, 8'hFF, 8'(OG), cOGPF + 16'(f), h_d[(32+FW)*i +: FW]};
                    end else if (BYP) begin       // gather bypass: unchanged, multicast, src = rank
                        qr_push[pt] = 1'b1;
                        qr_din[pt] = {1'b1, run_pipe ? PDST : 8'hFF, 8'(RANK), cBYP0 + 16'(f), h_d[(32+FW)*i +: FW]};
                    end else begin
                        s = integer'(hs[i]);
                        if (s != J) begin
                            qp_push[pt] = 1'b1;
                            qp_din[pt] = {1'b0, 8'(OG * NA + s), 8'(J), hfo[i], h_d[(32+FW)*i +: FW]};
                        end
                    end
                end
            if (r_v) begin
                qr_push[rcnt % NPT] = 1'b1;
                qr_din[rcnt % NPT] = res_flit;
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (integer c = 0; c < NC; c = c + 1) pres[c] <= '0;
                rptr <= 0; dupe <= 1'b0; drot <= 0; rcnt <= 0;
            end else begin
                drot <= (drot + 1) % (NPT + 1);
                if (r_v) rcnt <= rcnt + 1;
                if (REARM && completed && done_ready) begin
                    for(integer c=0;c<NC;c=c+1)pres[c]<='0;
                    rptr<=0;
                end
                if (NC > 1) begin
                    if (cw_dupe) dupe <= 1'b1;
                    for (integer c = 0; c < NC; c = c + 1)
                        if (cw_v[c]) pres[c][cw_fl[c]] <= 1'b1;
                    if (issue) begin
                        for (integer c = 0; c < NC; c = c + 1) pres[c][rptr] <= 1'b0;
                        rptr <= rptr + 1;
                    end
                end
            end
        // Count actual endpoint events; port FIFOs, credits and serializer state are never reset at rearm.
        localparam integer RMX = NOG * PFMAX / ((NC>1 && BF16 && !BF16RT) ? 2 : 1);
        reg [RMX-1:0] result_seen;
        reg result_error;
        reg [16:0] tx_count, delivery_count;
        reg [15:0] own_count, produced_count;
        integer ntx, nrx, npop, ndel;
        reg [RMX-1:0] seen_next;
        reg bad_result;
        wire [31:0] expected_delivery = (NC==1) ? (NOG-1)*PF : BYP ? {15'd0, cBYPT} : (LEG ? NOG*NC : ALL_DEST ? OUTER_G : NA)*ROF;
        wire [31:0] expected_tx = RGXM ? k : (NC==1 || BYP) ? PF : PF-OF+ROF;
        wire        inj_done = RGXM ? src_end : (k >= PF);
        // bypass delivery set check: count (delivery_count), sum and xor of gi equal those of 0 .. T-1 (T = group * pf)
        reg  [31:0] byp_sum, byp_sum_n, byp_sum_exp;
        reg  [15:0] byp_xor, byp_xor_n, byp_xor_exp;
        always @(posedge clk) begin
            byp_sum_exp <= 32'(({17'd0, cBYPT} * ({17'd0, cBYPT} - 34'd1)) >> 1);
            case (cBYPT[1:0])     // xor of 0 .. T-1 = g(T-1): n % 4 = 0 -> n, 1 -> 1, 2 -> n+1, 3 -> 0
                2'd1: byp_xor_exp <= cBYPT[15:0] - 16'd1;
                2'd2: byp_xor_exp <= 16'd1;
                2'd3: byp_xor_exp <= cBYPT[15:0];
                default: byp_xor_exp <= 16'd0;
            endcase
        end
        always @* begin
            ntx=0;nrx=0;npop=0;ndel=0;seen_next=result_seen;bad_result=0;byp_sum_n=byp_sum;byp_xor_n=byp_xor;
            for(integer p=0;p<NPT;p=p+1)begin
                ntx=ntx+ph_tx_v[p];nrx=nrx+ph_rx_v[p];npop=npop+(rb_pop[p]&&!rb_empty[p]);
            end
            for(integer l=0;l<DEL;l=l+1)if(del_valid[l] && !(PIPE != 0 && del_flit[l*PWT+FW+24+3 +: 5] == 5'b11110))begin
                integer gi;gi=integer'(del_flit[l*PWT+FW+:16]);ndel=ndel+1;
                if(BYP)begin
                    if(gi>=integer'({15'd0, cBYPT}))bad_result=1;
                    byp_sum_n=byp_sum_n+32'(gi);byp_xor_n=byp_xor_n^16'(gi);
                end else if(gi>=RMX)bad_result=1;
                else if(seen_next[gi])bad_result=1;
                else begin
                    seen_next[gi]=1;
                    if(NC>1 && ((!LEG && !ALL_DEST && (gi<OG*NA*ROF || gi>=(OG+1)*NA*ROF)) || (LEG && gi>=expected_delivery) || (ALL_DEST && (gi<OUTER_BASE*ROF || gi>=(OUTER_BASE+OUTER_G)*ROF))))bad_result=1;
                end
            end
        end
        reg [31:0] dcnt32, ndel32;
        reg byp_over, byp_badset;
        always @* begin
            dcnt32 = {15'd0, delivery_count}; ndel32 = ndel;
            byp_over = BYP && (dcnt32 + ndel32 > expected_delivery);
            byp_badset = BYP && dcnt32 == expected_delivery && ndel32 == 0 && (byp_sum != byp_sum_exp || byp_xor != byp_xor_exp);
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin
                result_seen<=0;result_error<=0;tx_count<=0;delivery_count<=0;own_count<=0;produced_count<=0;rx_pending<=0;completed<=0;
                byp_sum<=0;byp_xor<=0;
            end else if(REARM)begin
                rx_pending<=rx_pending+16'(nrx)-16'(npop);
                if(started && !completed && !run_pipe)begin
                    tx_count<=tx_count+17'(ntx);delivery_count<=delivery_count+17'(ndel);
                    own_count<=own_count+16'(dq_own_pop&&!dq_own_empty);produced_count<=produced_count+16'(r_v);
                    result_seen<=seen_next;byp_sum<=byp_sum_n;byp_xor<=byp_xor_n;
                    if(bad_result || npop>rx_pending+nrx)result_error<=1;
                    // bypass: more deliveries than group * pf, or all of them with a wrong gi set (a duplicate + a loss)
                    if(byp_over || byp_badset)result_error<=1;
                    if(!fault && !bad_result && ntx==0 && nrx==0 && npop==0 && ndel==0 &&
                       inj_done && (NC==1 || (BYP && byp_sum==byp_sum_exp && byp_xor==byp_xor_exp) ||
                                 (!BYP && rptr>=OF && produced_count==ROF && own_count==ROF)) &&
                       {15'd0, tx_count}==expected_tx && {15'd0, delivery_count}==expected_delivery && rx_pending==0 &&
                       (&rb_empty) && dq_own_empty && !(|h_v) && !r_v && !(|del_valid) && !issue)
                        completed<=1;
`ifdef OT_COLL_MUT_PREMATURE_DONE
                    if(k>=PF)completed<=1;
`endif
                end
                if(completed && done_ready)begin
                    completed<=0;result_seen<=0;tx_count<=0;delivery_count<=0;own_count<=0;produced_count<=0;byp_sum<=0;byp_xor<=0;
                end
            end
        reg anyovf;
        always @* begin
            anyovf = dq_own_ovf;
            for (integer p = 0; p < NPT; p = p + 1)
                anyovf = anyovf | pfault[p] | rb_ovf[p];
        end
        assign fault = anyovf | dupe | mode_error | (REARM && result_error);
    end endgenerate
endmodule
