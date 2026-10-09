`timescale 1ns/1ps
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
module ot_hbm_accel_tu_endpoint_sr #(
    parameter integer ENABLE = 0,
    parameter integer NC     = 8,
    parameter integer NOG    = 8,
    parameter integer PFMAX  = 64,
    parameter integer LANES  = 16,
    parameter integer BF16   = 1,
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
    input  wire [15:0]          pf,              // flits per contributor this collective (runtime)
    input  wire                 go,
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
        assign stat_credit_stall = 0;
    end else begin : g_on
        wire [31:0] RANK = {24'b0, rank};
        wire [31:0] OG = RANK / NC, J = RANK % NC;
        wire CONTRIB = RANK < NOG * NC;
        wire [31:0] PF = {16'b0, pf};
        wire [31:0] OF = PF / NC;
        wire [31:0] ROF = BF16 ? OF / 2 : OF;
        // registered run constants (hbm-coll-rtl): rank and pf are static during a collective, so the runtime
        // multiplies and the f / OF, f % OF divisions become compares / adds against these flops (exact; they settle
        // one edge after rank / pf, before the first injection)
        reg [15:0] mOF [0:NC];
        reg [15:0] cOGPF, cGI0;
        always @(posedge clk) begin
            for (integer m = 0; m <= NC; m = m + 1) mOF[m] <= 16'(m * OF);
            cOGPF <= 16'(OG * PF);
            cGI0  <= 16'((OG * NC + J) * ROF);
        end

        // ================= hub issue -> HUBW wire stages ==========================================
        integer k;
        reg started;
        reg [INJ*16-1:0] r_idx;
        reg [INJ-1:0] r_rd;
        always @* begin
            r_idx = '0; r_rd = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (CONTRIB && started && k + i < PF) begin
                    r_rd[i] = 1'b1;           // rotated slice order: own slice last in each round
                    r_idx[16*i +: 16] = (NC == 1) ? 16'(k + i) :
                        16'(mOF[(J + 1 + 32'((k + i) % NC)) % NC] + 16'((k + i) / NC));
                end
        end
        assign inj_idx = r_idx;
        assign inj_rd  = r_rd;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin k <= 0; started <= 1'b0; end
            else begin
                if (go && !started) started <= 1'b1;
                if (|r_rd) k <= k + INJ;
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

        // ================= per-port transmit queues, arbiter, switch-ingress credits ==============
        reg  [NPT-1:0] qp_push, qr_push, qp_pop, qr_pop;
        reg  [PWT-1:0] qp_din [0:NPT-1];
        reg  [PWT-1:0] qr_din [0:NPT-1];
        wire [NPT-1:0] qp_empty, qr_empty, qp_ovf, qr_ovf;
        wire [PWT-1:0] qp_head [0:NPT-1];
        wire [PWT-1:0] qr_head [0:NPT-1];
        integer credit [0:NPT-1];
        reg [31:0] cstall;
        reg [NPT-1:0] tv;
        reg [PWT-1:0] tf [0:NPT-1];
        wire [NPT-1:0] lfault;
        for (genvar p = 0; p < NPT; p = p + 1) begin : g_txq
            wire [QAW:0] c0, c1;
            (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(QAW)) u_qp (.clk(clk), .rst_n(rst_n), .push(qp_push[p]), .din(qp_din[p]),
                .pop(qp_pop[p]), .empty(qp_empty[p]), .dout(qp_head[p]), .ovf(qp_ovf[p]), .count(c0));
            (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(QAW)) u_qr (.clk(clk), .rst_n(rst_n), .push(qr_push[p]), .din(qr_din[p]),
                .pop(qr_pop[p]), .empty(qr_empty[p]), .dout(qr_head[p]), .ovf(qr_ovf[p]), .count(c1));
            // TX half of the link: wire stages -> TX CDC -> serializer pacing
            wire         w1_v;
            wire [PWT-1:0] w1_d;
            (* keep_hierarchy *) ot_hcoll_sdelay #(.W(PWT), .D(WSTG)) u_wtx (.clk(clk), .rst_n(rst_n), .v_in(tv[p]), .d_in(tf[p]),
                .v_out(w1_v), .d_out(w1_d));
            wire tx_empty, tx_ovf, tx_full;
            wire [PWT-1:0] tx_head;
            wire [TXAW:0] tx_freed, tx_cnt;
            reg  tx_pop;
            if (SYNCPHY) begin : g_stx
                wire [1:0] sc;
                (* keep_hierarchy *) ot_ha2_fifo #(.W(PWT), .AW(1)) u_txq (.clk(clk), .rst_n(rst_n), .push(w1_v), .din(w1_d), .pop(tx_pop),
                    .empty(tx_empty), .dout(tx_head), .ovf(tx_ovf), .count(sc));
            end else begin : g_atx
                (* keep_hierarchy *) ot_link_afifo #(.W(PWT), .AW(TXAW)) u_txcdc (.wclk(clk), .wrst_n(rst_n), .wr(w1_v), .wdata(w1_d),
                    .wfull(tx_full), .wfreed(tx_freed), .ovf(tx_ovf), .rclk(pclk), .rrst_n(prst_n), .rd(tx_pop),
                    .rempty(tx_empty), .rdata(tx_head), .rcount(tx_cnt));
            end
            integer acc;
            always @* tx_pop = !tx_empty && (acc + BITS_X100 >= PWB * 100);
            always @(posedge pclk or negedge prst_n)
                if (!prst_n) acc <= 0;
                else begin : pace
                    integer a;
                    a = acc + BITS_X100;
                    if (a > PWB * 100) a = PWB * 100;
                    if (tx_pop) a = a - PWB * 100;
                    acc <= a;
                end
            assign ph_tx_v[p] = tx_pop;
            assign ph_tx_flit[p*PWT +: PWT] = tx_head;
            assign lfault[p] = tx_ovf;
        end
        always @* begin
            qp_pop = '0; qr_pop = '0; tv = '0;
            for (integer p = 0; p < NPT; p = p + 1) begin
                tf[p] = '0;
                if (credit[p] > 0) begin
                    if (!qp_empty[p]) begin qp_pop[p] = 1'b1; tv[p] = 1'b1; tf[p] = qp_head[p]; end
                    else if (!qr_empty[p]) begin qr_pop[p] = 1'b1; tv[p] = 1'b1; tf[p] = qr_head[p]; end
                end
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (integer p = 0; p < NPT; p = p + 1) credit[p] <= SWCRED;
                cstall <= 0;
            end else begin
                for (integer p = 0; p < NPT; p = p + 1) begin
                    credit[p] <= credit[p] - (tv[p] ? 1 : 0) + (sw_cr_ret[p] ? 1 : 0);
                    if (credit[p] == 0 && !(qp_empty[p] && qr_empty[p])) cstall <= cstall + 1;
                end
            end
        assign stat_credit_stall = cstall;

        // ================= RX half of each link + receive buffers ==================================
        reg  [NPT-1:0] rb_pop;
        wire [NPT-1:0] rb_empty, rb_ovf, rx_ovf;
        wire [PWT-1:0] rb_head [0:NPT-1];
        for (genvar p = 0; p < NPT; p = p + 1) begin : g_rx
            wire rx_empty, rx_full;
            wire [PWT-1:0] rx_head;
            wire [TXAW:0] rx_freed, rx_cnt;
            if (SYNCPHY) begin : g_srx
                wire [1:0] sc;
                (* keep_hierarchy *) ot_ha2_fifo #(.W(PWT), .AW(1)) u_rxq (.clk(clk), .rst_n(rst_n), .push(ph_rx_v[p]),
                    .din(ph_rx_flit[p*PWT +: PWT]), .pop(!rx_empty), .empty(rx_empty), .dout(rx_head), .ovf(rx_ovf[p]),
                    .count(sc));
            end else begin : g_arx
                (* keep_hierarchy *) ot_link_afifo #(.W(PWT), .AW(TXAW)) u_rxcdc (.wclk(pclk), .wrst_n(prst_n), .wr(ph_rx_v[p]),
                    .wdata(ph_rx_flit[p*PWT +: PWT]), .wfull(rx_full), .wfreed(rx_freed), .ovf(rx_ovf[p]),
                    .rclk(clk), .rrst_n(rst_n), .rd(!rx_empty), .rempty(rx_empty), .rdata(rx_head), .rcount(rx_cnt));
            end
            wire         w2_v;
            wire [PWT-1:0] w2_d;
            (* keep_hierarchy *) ot_hcoll_sdelay #(.W(PWT), .D(WSTG)) u_wrx (.clk(clk), .rst_n(rst_n), .v_in(!rx_empty), .d_in(rx_head),
                .v_out(w2_v), .d_out(w2_d));
            wire [RXAW:0] cnt;
            (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(RXAW)) u_rb (.clk(clk), .rst_n(rst_n), .push(w2_v), .din(w2_d),
                .pop(rb_pop[p]), .empty(rb_empty[p]), .dout(rb_head[p]), .ovf(rb_ovf[p]), .count(cnt));
        end
        assign rx_credit = rb_pop;

        // ================= operand slots and the golden reduction tree (HA2) ======================
        reg [OFMX-1:0] pres [0:NC-1];
        reg dupe;
        integer rptr;
        reg  [NC-1:0] col;
        always @* for (integer c = 0; c < NC; c = c + 1) col[c] = (NC > 1 && rptr < OF) ? pres[c][rptr] : 1'b0;
        wire issue = &col;
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
            assign opsel[c] = slot[rptr < OF ? rptr : 0];
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
                    if (BF16) begin
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
        (* keep_hierarchy *) ot_hcoll_sfifo #(.W(PWT), .AW(QAW)) u_dqo (.clk(clk), .rst_n(rst_n), .push(r_v), .din(res_flit),
            .pop(dq_own_pop), .empty(dq_own_empty), .dout(dq_own_head), .ovf(dq_own_ovf), .count(dc0));

        // ================= receive dispatch and delivery =========================================
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
                if (NC > 1 && h_v[i] && integer'(hs[i]) == J) ctk[J % NC] = 1'b1;   // hub own slice first (cannot stall)
            for (integer p = 0; p < NPT; p = p + 1)
                if (!rb_empty[p] && !rb_head[p][PWT-1]) begin                    // partials -> slots
                    c = integer'(rb_head[p][FW+16 +: 8]);
                    if (c >= NC) rb_pop[p] = 1'b1;                                 // malformed: popped, flagged
                    else if (!ctk[c]) begin rb_pop[p] = 1'b1; ctk[c] = 1'b1; end   // else waits a cycle in rb
                end
            // delivery: the first DEL ready sources in the rotated order (drot, drot+1, ...) take lanes 0, 1, ...;
            // written as constant-index one-hot selects (lane of source s = ready sources ahead of it)
            for (integer s = 0; s <= NPT; s = s + 1) begin
                rdy[s] = (s == NPT) ? !dq_own_empty : (!rb_empty[s % NPT] && rb_head[s % NPT][PWT-1]);
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
                if (NC > 1 && h_v[i] && integer'(hs[i]) == J) begin
                    hw[i] = 1'b1;
                    if (pres[J % NC][hfo[i]]) cw_dupe = 1'b1;
                end
            for (integer p = 0; p < NPT; p = p + 1)
                if (rb_pop[p] && !rb_head[p][PWT-1]) begin
                    c  = integer'(rb_head[p][FW+16 +: 8]);
                    fl = integer'(rb_head[p][FW +: 16]);
                    if (c >= NC || fl >= OF || pres[c % NC][fl[$clog2(OFMX)-1:0]] || rb_head[p][FW+24 +: 8] != 8'(RANK)) cw_dupe = 1'b1;
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
                    end else begin
                        s = integer'(hs[i]);
                        if (s != J) begin
                            qp_push[pt] = 1'b1;
                            qp_din[pt] = {1'b0, 8'(OG * NC + s), 8'(J), hfo[i], h_d[(32+FW)*i +: FW]};
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
        reg anyovf;
        always @* begin
            anyovf = dq_own_ovf;
            for (integer p = 0; p < NPT; p = p + 1)
                anyovf = anyovf | qp_ovf[p] | qr_ovf[p] | rb_ovf[p] | rx_ovf[p] | lfault[p];
        end
        assign fault = anyovf | dupe;
    end endgenerate
endmodule
