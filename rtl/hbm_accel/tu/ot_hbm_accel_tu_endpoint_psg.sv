`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_tu_endpoint_psg (hbm-forks 2026-10-09, HGI-1 coll_group_size, iface-review C6 / review-0412 S4):
// ot_hbm_accel_tu_endpoint_ps with the reduction GROUP SIZE a static mode: gsz = 4'hF (reset = DS) is the legacy
// NC / NOG parameter behaviour bit for bit; gsz = 0..3 is a group of n = 2^gsz in {1, 2, 4, 8} (<= NC) aligned dies:
// J = rank & (n-1), OG = rank >> gsz, every rank contributes, OF = pf >> gsz, partial for owner s goes to die OG*n + s,
// and the operand columns >= n are PRESENT with +0 operands, so the unchanged NC-wide pairwise tree computes
// ((p0+p1)+(p2+p3)) + (+0 ...) = the rank-order pairwise tree of the n contributors exactly (x + (+0) = x; every zero
// result is +0 in this datapath, as in the golden), at the same latency as DS.  16 / 32 / 64 are rejected encodings
// (review-0412).  gsz is quasi-static (set before `go`, false-path from the cfg_act register).
// GATHER BYPASS (hgi-takeover 2026-10-09, review 10:45 decision 1): byp = 1 (latched at go) is an exact gather on the same
// links, credits, ports and delivery lanes: every rank of the group (2^gsz aligned ranks, or with mcast_all the outer
// group 2 / 4 / 8 / 96) sends each of its pf flits once, unchanged, as a multicast result {1, FF, src = rank,
// gi = (rank - group base) * pf + f, data}; its own flits go to its own delivery queue; receivers drop other groups'
// flits.  No adder, no BF16 packing: ALL_GATHER / TOPK_MERGE / ARGMAX_MERGE / ROW_GATHER payloads are bit-exact
// (-0, NaN payloads).  Done after pf sent and group * pf delivered with count, sum and xor of gi equal to the
// 0 .. group * pf - 1 set (a duplicate or a lost flit faults); a partial flit in bypass faults.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// ot_hbm_accel_tu_endpoint_ps (stream hbm-coll-rtl, 2026-10-08): the PER-PORT SPLIT of ot_hbm_accel_tu_endpoint_sr for
// the hfd_coll die view (pclk = clk only: SYNCPHY behaviour, pclk / prst_n unused).  Everything per port (queues,
// arbiter + switch credit, TX/RX wire stages, pacing, receive buffer) is ONE hard block ot_hcoll_port replicated 8x;
// this module is the core (hub, slots, 112-adder tree, delivery, own queue) plus the slice boundary flops and K = 8
// landing heads (credit flow, ot_hcoll_sfifo_x).  Transaction-exact against the same bench; extra cost per flit:
// +1 edge transmit (core out flop), +1 receive (slice in flop), +3 receive-buffer export (out flop, core in flop,
// landing), +1 on switch credit returns.  Below: the ot_hbm_accel_tu_endpoint_sr text, ports section replaced.
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// ot_hbm_accel_tu_endpoint_sr (stream hbm-coll-rtl, 2026-10-08): ot_hbm_accel_tu_endpoint restructured for the
// hfd_coll die view.  Same ports, same flit format, same golden reduction tree / to_bf16 / delivery: transaction-
// exact (every delivered word bit-identical; tb_hbm_accel_tu_endpoint with +define+TU_DUT=..._sr); cycle timing differs.
//   * deep FIFOs (port partial / result queues, receive buffers, own-delivery queue) -> ot_hcoll_sfifo: SRAM
//     (ot_sram_1r1w_128x256 x 3 a bank) with pin-flopped writes, a credit-gated fixed read pipeline, a captured macro output
//     and a 4-entry flop head (+4 edges a queue crossing);
//   * HUBW / WSTG wire-stage delay lines (were circular buffers with a D-way x 545 b read mux) -> ot_hcoll_sdelay:
//     SRAM with a fixed read offset, same latency D; the 16-bit tree-index delay -> plain shift line;
//   * CDC FIFOs stay ot_link_afifo flops, TXAW 6 -> 3 (8 entries: at pclk = clk the occupancy is <= 6); SYNCPHY = 1
//     (only legal when pclk is clk, as hfd_coll wires it) replaces them with 2-entry flop FIFOs (occupancy <= 1);
//   * the runtime multiplies and f / OF, f % OF divisions -> compares against registered m * OF constants;
//   * operand-slot writes: one writer per contributor column per cycle (a second partial for the same column waits
//     a cycle in its receive buffer), so each column has one one-hot 10-source write select instead of a demux of
//     every port into every slot; delivery lanes likewise use constant-index one-hot selects.
// Primitive instance sites carry (* keep_hierarchy *) (as the coll _kh endpoint): one ABC run per unique module.
// Defaults: RXAW 8 (256-entry receive buffers = the switch egress credit pool, two 128-deep banks), QAW 7 (128-deep
// queues); the flop original ran the die view at 16 entries.  TXAW 3.
// ---------------------------------------------------------------------------
// ot_hbm_accel_tu_endpoint: one DS-V4.1 TP-96 die's collective endpoint on a
// SWITCHED scale-up tier (Tomahawk-Ultra class: NPT Ethernet ports a die into
// the switch tier, in-switch multicast, no in-switch reduction) -- the
// "endpoint bridge NoC <-> Ethernet" of the TU-protocol design, in RTL.
// Accelerator (ours).  ENABLE = 0 (default): every output tied off.
//
// Successor of rtl/hbm_accel/ha2_ar/ot_ha2_ar_endpoint (byte-identical, not
// edited): the hub injection / HUBW wire stages / operand slots / golden
// pairwise reduction tree (ot_hdc_fp32_add_lat #(LAT) per lane) / golden
// to_bf16 packing / delivery and the primitives (ot_ha2_delay, ot_ha2_fifo,
// ot_link_afifo) are HA2's.  What changes is the port side: instead of 20
// direct die-to-die links (15 local + 5 global, 2-level relay) the die has
// NPT ports into the switch tier; a partial carries its destination die in
// the header and the switch routes it; a result is sent ONCE and the switch
// multicasts it (no relay queues).  Flits are striped over the NPT ports.
//
// OPERATION (runtime size: pf flits per contributor, pf <= PFMAX, pf % NC == 0)
//   NC > 1  all-reduce: NOG reduction groups of NC contributor dies (ranks
//           og*NC .. og*NC+NC-1).  RS: partial flit f of a contributor goes to
//           owner s of its group (of = pf / NC flits a slice; injection order
//           is rotated by the contributor index so that every die issues in
//           the same relative order).  REDUCE as soon as all NC operands of an
//           owned flit are slotted: ((p0+p1)+(p2+p3))+... in rank order, then
//           (BF16 = 1) the golden to_bf16, two reduced flits per result flit.
//           AG: each result flit is sent once (switch multicast) and delivered
//           locally.
//   NC = 1  all-gather (every rank NOG = R contributes pf flits): each injected
//           flit is sent once (switch multicast); the die's own segment is
//           resident (not re-delivered); peers' flits are delivered.
//
// Ports: per port a transmit queue (partial > result, one flit a cycle, with
// a credit for the switch ingress buffer), the TX half of the link (WSTG wire
// stages, TX CDC ot_link_afifo core -> PHY clock, serializer pacing of
// BITS_X100/100 payload bits a PHY cycle per PWB-bit flit), and the RX half
// (RX CDC PHY -> core, WSTG wire stages, a receive buffer of 2^RXAW flits that
// is the credit pool the switch egress spends).  Everything past the
// serializer (Ethernet PHY/FEC, cable, switch) is OUTSIDE this module.
//
// Flit = {kind[1], dst[8], src[8], idx[16], data[FW]}: kind 0 partial (dst =
// owner die, src = contributor index j, idx = flit within the owned slice),
// kind 1 result (dst = 0xFF multicast, src = group, idx = global result index).
// ---------------------------------------------------------------------------
module ot_hbm_accel_tu_endpoint_psg #(
    parameter integer ENABLE = 0,
    parameter integer REARM = 0, // opt-in; production pclk must equal clk

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
    parameter integer PWT    = FW + 33
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
    output wire                 fault,
    output wire [31:0]          stat_credit_stall
);
    localparam integer LV   = $clog2(NC);
    localparam integer OFMX = PFMAX / NC;

    generate if (ENABLE == 0) begin : g_off
        assign inj_idx = '0; assign inj_rd = '0; assign ph_tx_v = '0; assign ph_tx_flit = '0;
        assign rx_credit = '0; assign del_valid = '0; assign del_flit = '0; assign fault = 1'b0;
        assign stat_credit_stall = 0; assign start_ready = 0; assign done_valid = 0;
    end else begin : g_on
        reg [7:0] run_rank; reg [15:0] run_pf; reg [3:0] run_gsz; reg run_mcast; reg[7:0]run_outer; reg run_byp; reg run_bf16;
        reg pending_start, completed, started;
        reg [15:0] rx_pending;
        wire active_desc = REARM && (started || pending_start || completed);
        wire [7:0] eff_rank = active_desc ? run_rank : rank;
        wire [15:0] eff_pf = active_desc ? run_pf : pf;
        wire [3:0] eff_gsz = active_desc ? run_gsz : gsz;
        wire ALL_DEST = active_desc ? run_mcast : mcast_all;
        wire BYP = active_desc ? run_byp : byp;
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
        wire BYP_PAY_OK = (eff_pf != 0) && (eff_pf <= PFMAX) && (RANK < NOG * NC);
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
            else if (go && (!REARM || start_ready) && !ACCEPT_MODE) mode_error <= 1'b1;
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
        reg [15:0] cOGPF, cGI0, cBYP0, cBYPT;
        always @(posedge clk) begin
            for (integer m = 0; m <= NC; m = m + 1) mOF[m] <= 16'(m * OF);
            cOGPF <= 16'(OG * PF);
            cGI0  <= 16'((OG * NA + J) * ROF);
`ifdef OT_COLL_MUT_BYP_GI
            cBYP0 <= 16'd0;                                   // NEGATIVE: every rank's segment at gi 0 .. pf-1
`else
            cBYP0 <= 16'((RANK - GBASE) * PF);
`endif
            cBYPT <= 16'(GN * PF);
        end

        // ================= hub issue -> HUBW wire stages ==========================================
        integer k;
        assign start_ready = !started && (!REARM || (!pending_start && !completed && !fault && rx_pending == 0 && !(|ph_rx_v)));
        assign done_valid = REARM && completed;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin pending_start<=0; run_rank<=0;run_pf<=0;run_gsz<=15;run_mcast<=0;run_outer<=96;run_byp<=0;run_bf16<=1;end
            else if (REARM) begin
                if (go && start_ready && ACCEPT_MODE) begin
                    run_rank<=rank;run_pf<=pf;run_gsz<=gsz;run_mcast<=mcast_all;run_outer<=mcast_group_size;run_byp<=byp;run_bf16<=res_bf16;pending_start<=1;
                end else if(pending_start) pending_start<=0;
            end
        reg [INJ*16-1:0] r_idx;
        reg [INJ-1:0] r_rd;
        always @* begin
            r_idx = '0; r_rd = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (CONTRIB && started && k + i < PF && ((!BYP && (LEG || NA > 1)) || i == 0)) begin
                    r_rd[i] = 1'b1;           // rotated slice order: own slice last in each round
                    r_idx[16*i +: 16] = (NC == 1 || BYP) ? 16'(k + i) : LEG ?
                        16'(mOF[(J + 1 + 32'((k + i) % NC)) % NC] + 16'((k + i) / NC)) :
                        16'(mOF[(J + 1 + (32'(k + i) & (NA - 1))) & (NA - 1)] + 16'(32'(k + i) >> LG));
                end
        end
        assign inj_idx = r_idx;
        assign inj_rd  = r_rd;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin k <= 0; started <= 1'b0; end
            else begin
                if (REARM) begin
                    if(pending_start) started<=1'b1;
                    if(completed && done_ready) begin started<=0;k<=0;end
                end else if (go && !started && ACCEPT_MODE) started <= 1'b1;
                if (|r_rd) k <= k + ((!BYP && (LEG || NA > 1)) ? INJ : 1);
            end
        wire [INJ-1:0] h_v;
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
            (* keep_hierarchy *) ot_hcoll_sdelay #(.W(32 + FW), .D(HUBW)) u_h (.clk(clk), .rst_n(rst_n), .v_in(r_rd[i]),
                .d_in({16'(k + i), r_idx[16*i +: 16], inj_data[FW*i +: FW]}), .v_out(h_v[i]),
                .d_out(h_d[(32+FW)*i +: 32+FW]));
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
        initial if (PWT != 545 || QAW != 7 || RXAW != 8 || WSTG != 14 || BITS_X100 != 72000 || PWB != 545 || SWCRED != 256)
            $fatal(1, "ot_hbm_accel_tu_endpoint_ps: the hardened ot_hcoll_port is built for PWT 545 QAW 7 RXAW 8 WSTG 14 SWCRED 256");
`endif
        for (genvar p = 0; p < NPT; p = p + 1) begin : g_port
            // the slice is ONE hardened view: instantiated at its defaults (a hard macro takes no parameters)
            ot_hcoll_port u_port (.clk(clk), .rst_n(rst_n),
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
        wire [QAW:0] dc0;
        // bypass: the rank's own flits (hub output, one a cycle) enter the own delivery queue unchanged
        wire own_byp_v = BYP && h_v[0];
`ifdef OT_COLL_MUT_BYP_OWNSIGN
        wire [PWT-1:0] own_byp_f = {1'b1, 8'hFF, 8'(RANK), cBYP0 + h_d[FW +: 16], h_d[FW-1:0] & ~{LANES{32'h80000000}}};  // NEGATIVE: sign dropped
`else
        wire [PWT-1:0] own_byp_f = {1'b1, 8'hFF, 8'(RANK), cBYP0 + h_d[FW +: 16], h_d[FW-1:0]};
`endif
        (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(QAW)) u_dqo (.clk(clk), .rst_n(rst_n), .push(r_v || own_byp_v), .din(own_byp_v ? own_byp_f : res_flit),
            .pop(dq_own_pop), .empty(dq_own_empty), .dout(dq_own_head), .ovf(dq_own_ovf), .count(dc0));

        // ================= receive dispatch and delivery =========================================
        wire[NPT-1:0] result_for_group;
        for(genvar pg=0;pg<NPT;pg=pg+1)begin:g_membership
            wire[31:0] producer_base = 32'(rb_head[pg][FW+16+:8]) << LG;
            wire[31:0] src_rank = {24'd0, rb_head[pg][FW+16+:8]};
            assign result_for_group[pg] = BYP ? (src_rank >= GBASE && src_rank < GBASE + GN) : LEG || (ALL_DEST ?
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
                pos[s] = 4'((s + (NPT + 1) - drot) % (NPT + 1));
            end
            for (integer s = 0; s <= NPT; s = s + 1) begin
                n = 0;
                for (integer t = 0; t <= NPT; t = t + 1) if (rdy[t] && pos[t] < pos[s]) n = n + 1;
                for (integer l = 0; l < DEL; l = l + 1) dsel[l][s] = rdy[s] && n == l;
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
                        qr_din[pt] = {1'b1, 8'hFF, 8'(RANK), cBYP0 + 16'(f), h_d[(32+FW)*i +: FW]};
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
        reg [15:0] tx_count, delivery_count, own_count, produced_count;
        integer ntx, nrx, npop, ndel;
        reg [RMX-1:0] seen_next;
        reg bad_result;
        wire [31:0] expected_delivery = (NC==1) ? (NOG-1)*PF : BYP ? {16'd0, cBYPT} : (LEG ? NOG*NC : ALL_DEST ? OUTER_G : NA)*ROF;
        wire [31:0] expected_tx = (NC==1 || BYP) ? PF : PF-OF+ROF;
        // bypass delivery set check: count (delivery_count), sum and xor of gi equal those of 0 .. T-1 (T = group * pf)
        reg  [31:0] byp_sum, byp_sum_n, byp_sum_exp;
        reg  [15:0] byp_xor, byp_xor_n, byp_xor_exp;
        always @(posedge clk) begin
            byp_sum_exp <= ({16'd0, cBYPT} * ({16'd0, cBYPT} - 32'd1)) >> 1;
            case (cBYPT[1:0])     // xor of 0 .. T-1 = g(T-1): n % 4 = 0 -> n, 1 -> 1, 2 -> n+1, 3 -> 0
                2'd1: byp_xor_exp <= cBYPT - 16'd1;
                2'd2: byp_xor_exp <= 16'd1;
                2'd3: byp_xor_exp <= cBYPT;
                default: byp_xor_exp <= 16'd0;
            endcase
        end
        always @* begin
            ntx=0;nrx=0;npop=0;ndel=0;seen_next=result_seen;bad_result=0;byp_sum_n=byp_sum;byp_xor_n=byp_xor;
            for(integer p=0;p<NPT;p=p+1)begin
                ntx=ntx+ph_tx_v[p];nrx=nrx+ph_rx_v[p];npop=npop+(rb_pop[p]&&!rb_empty[p]);
            end
            for(integer l=0;l<DEL;l=l+1)if(del_valid[l])begin
                integer gi;gi=integer'(del_flit[l*PWT+FW+:16]);ndel=ndel+1;
                if(BYP)begin
                    if(gi>=integer'(cBYPT))bad_result=1;
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
            dcnt32 = {16'd0, delivery_count}; ndel32 = ndel;
            byp_over = BYP && (dcnt32 + ndel32 > expected_delivery);
            byp_badset = BYP && dcnt32 == expected_delivery && ndel32 == 0 && (byp_sum != byp_sum_exp || byp_xor != byp_xor_exp);
        end
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin
                result_seen<=0;result_error<=0;tx_count<=0;delivery_count<=0;own_count<=0;produced_count<=0;rx_pending<=0;completed<=0;
                byp_sum<=0;byp_xor<=0;
            end else if(REARM)begin
                rx_pending<=rx_pending+16'(nrx)-16'(npop);
                if(started && !completed)begin
                    tx_count<=tx_count+16'(ntx);delivery_count<=delivery_count+16'(ndel);
                    own_count<=own_count+16'(dq_own_pop&&!dq_own_empty);produced_count<=produced_count+16'(r_v);
                    result_seen<=seen_next;byp_sum<=byp_sum_n;byp_xor<=byp_xor_n;
                    if(bad_result || npop>rx_pending+nrx)result_error<=1;
                    // bypass: more deliveries than group * pf, or all of them with a wrong gi set (a duplicate + a loss)
                    if(byp_over || byp_badset)result_error<=1;
                    if(!fault && !bad_result && ntx==0 && nrx==0 && npop==0 && ndel==0 &&
                       k>=PF && (NC==1 || (BYP && byp_sum==byp_sum_exp && byp_xor==byp_xor_exp) ||
                                 (!BYP && rptr>=OF && produced_count==ROF && own_count==ROF)) &&
                       tx_count==expected_tx && delivery_count==expected_delivery && rx_pending==0 &&
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
