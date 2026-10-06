`timescale 1ns/1ps
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
module ot_hbm_accel_tu_endpoint #(
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
    parameter integer QAW    = 6,
    parameter integer TXAW   = 6,
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
                        16'(((J + 1 + 32'((k + i) % NC)) % NC) * OF + 32'((k + i) / NC));
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
        for (genvar i = 0; i < INJ; i = i + 1) begin : g_hub
            ot_ha2_delay #(.W(32 + FW), .D(HUBW)) u_h (.clk(clk), .rst_n(rst_n), .v_in(r_rd[i]),
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
            ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_qp (.clk(clk), .rst_n(rst_n), .push(qp_push[p]), .din(qp_din[p]),
                .pop(qp_pop[p]), .empty(qp_empty[p]), .dout(qp_head[p]), .ovf(qp_ovf[p]), .count(c0));
            ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_qr (.clk(clk), .rst_n(rst_n), .push(qr_push[p]), .din(qr_din[p]),
                .pop(qr_pop[p]), .empty(qr_empty[p]), .dout(qr_head[p]), .ovf(qr_ovf[p]), .count(c1));
            // TX half of the link: wire stages -> TX CDC -> serializer pacing
            wire         w1_v;
            wire [PWT-1:0] w1_d;
            ot_ha2_delay #(.W(PWT), .D(WSTG)) u_wtx (.clk(clk), .rst_n(rst_n), .v_in(tv[p]), .d_in(tf[p]),
                .v_out(w1_v), .d_out(w1_d));
            wire tx_empty, tx_ovf, tx_full;
            wire [PWT-1:0] tx_head;
            wire [TXAW:0] tx_freed, tx_cnt;
            reg  tx_pop;
            ot_link_afifo #(.W(PWT), .AW(TXAW)) u_txcdc (.wclk(clk), .wrst_n(rst_n), .wr(w1_v), .wdata(w1_d),
                .wfull(tx_full), .wfreed(tx_freed), .ovf(tx_ovf), .rclk(pclk), .rrst_n(prst_n), .rd(tx_pop),
                .rempty(tx_empty), .rdata(tx_head), .rcount(tx_cnt));
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
            ot_link_afifo #(.W(PWT), .AW(TXAW)) u_rxcdc (.wclk(pclk), .wrst_n(prst_n), .wr(ph_rx_v[p]),
                .wdata(ph_rx_flit[p*PWT +: PWT]), .wfull(rx_full), .wfreed(rx_freed), .ovf(rx_ovf[p]),
                .rclk(clk), .rrst_n(rst_n), .rd(!rx_empty), .rempty(rx_empty), .rdata(rx_head), .rcount(rx_cnt));
            wire         w2_v;
            wire [PWT-1:0] w2_d;
            ot_ha2_delay #(.W(PWT), .D(WSTG)) u_wrx (.clk(clk), .rst_n(rst_n), .v_in(!rx_empty), .d_in(rx_head),
                .v_out(w2_v), .d_out(w2_d));
            wire [RXAW:0] cnt;
            ot_ha2_fifo #(.W(PWT), .AW(RXAW)) u_rb (.clk(clk), .rst_n(rst_n), .push(w2_v), .din(w2_d),
                .pop(rb_pop[p]), .empty(rb_empty[p]), .dout(rb_head[p]), .ovf(rb_ovf[p]), .count(cnt));
        end
        assign rx_credit = rb_pop;

        // ================= operand slots and the golden reduction tree (HA2) ======================
        reg [FW-1:0] opd [0:NC-1][0:OFMX-1];
        reg [OFMX-1:0] pres [0:NC-1];
        reg dupe;
        integer rptr;
        reg  [NC-1:0] col;
        always @* for (integer c = 0; c < NC; c = c + 1) col[c] = (NC > 1 && rptr < OF) ? pres[c][rptr] : 1'b0;
        wire issue = &col;
        wire [FW-1:0] lvl [0:LV][0:NC-1];
        wire [LV:0] lvv;
        reg  [FW-1:0] opsel [0:NC-1];
        always @* for (integer c = 0; c < NC; c = c + 1) opsel[c] = opd[c][rptr < OF ? rptr : 0];
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
                    ot_hdc_fp32_add_lat #(.LAT(LAT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(lvv[l-1]),
                        .a(lvl[l-1][2*i][32*ln +: 32]), .b(lvl[l-1][2*i+1][32*ln +: 32]),
                        .y(lvl[l][i][32*ln +: 32]), .err(ee[(i*LANES+ln)*2 +: 2]), .valid_out(vv[i*LANES+ln]));
                end
            end
            assign lvv[l] = vv[0];
        end
        wire        ti_v;
        wire [15:0] ti_d;
        ot_ha2_delay #(.W(16), .D(LAT * LV)) u_tidx (.clk(clk), .rst_n(rst_n), .v_in(issue), .d_in(16'(rptr)),
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
        wire [15:0] my_gi = 16'((OG * NC + J) * ROF + {16'b0, r_m});
        wire [PWT-1:0] res_flit = {1'b1, 8'hFF, 8'(OG), my_gi, r_d};

        // ================= own delivery queue =====================================================
        wire dq_own_empty, dq_own_ovf;
        wire [PWT-1:0] dq_own_head;
        reg dq_own_pop;
        wire [QAW:0] dc0;
        ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_dqo (.clk(clk), .rst_n(rst_n), .push(r_v), .din(res_flit),
            .pop(dq_own_pop), .empty(dq_own_empty), .dout(dq_own_head), .ovf(dq_own_ovf), .count(dc0));

        // ================= receive dispatch and delivery =========================================
        integer drot;
        reg [DEL-1:0] dv;
        reg [PWT-1:0] dfl [0:DEL-1];
        always @* begin : dispatch
            integer n, src;
            rb_pop = '0; dq_own_pop = 1'b0; dv = '0;
            for (integer i = 0; i < DEL; i = i + 1) dfl[i] = '0;
            for (integer p = 0; p < NPT; p = p + 1)
                if (!rb_empty[p] && !rb_head[p][PWT-1]) rb_pop[p] = 1'b1;        // partials -> slots
            n = 0;
            for (integer i = 0; i < NPT + 1; i = i + 1) begin
                src = (drot + i) % (NPT + 1);
                if (n < DEL) begin
                    if (src == NPT) begin
                        if (!dq_own_empty) begin dq_own_pop = 1'b1; dv[n] = 1'b1; dfl[n] = dq_own_head; n = n + 1; end
                    end else if (!rb_empty[src] && rb_head[src][PWT-1]) begin
                        rb_pop[src] = 1'b1; dv[n] = 1'b1; dfl[n] = rb_head[src]; n = n + 1;
                    end
                end
            end
        end
        for (genvar i = 0; i < DEL; i = i + 1) begin : g_del
            ot_ha2_delay #(.W(PWT), .D(HUBW)) u_d (.clk(clk), .rst_n(rst_n), .v_in(dv[i]), .d_in(dfl[i]),
                .v_out(del_valid[i]), .d_out(del_flit[i*PWT +: PWT]));
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
                        qr_din[pt] = {1'b1, 8'hFF, 8'(OG), 16'(OG * PF + f), h_d[(32+FW)*i +: FW]};
                    end else begin
                        s = f / OF;
                        if (s != J) begin
                            qp_push[pt] = 1'b1;
                            qp_din[pt] = {1'b0, 8'(OG * NC + s), 8'(J), 16'(f % OF), h_d[(32+FW)*i +: FW]};
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
                    for (integer i = 0; i < INJ; i = i + 1)
                        if (h_v[i]) begin : own
                            integer f;
                            f = integer'(h_d[(32+FW)*i + FW +: 16]);
                            if (f / OF == J) begin
                                if (pres[J][f % OF]) dupe <= 1'b1;
                                pres[J][f % OF] <= 1'b1;
                                opd[J][f % OF] <= h_d[(32+FW)*i +: FW];
                            end
                        end
                    for (integer p = 0; p < NPT; p = p + 1)
                        if (rb_pop[p] && !rb_head[p][PWT-1]) begin : peer
                            integer c, fl;
                            c  = integer'(rb_head[p][FW+16 +: 8]);
                            fl = integer'(rb_head[p][FW +: 16]);
                            if (c >= NC || fl >= OF || pres[c][fl] || rb_head[p][FW+24 +: 8] != 8'(RANK)) dupe <= 1'b1;
                            else begin pres[c][fl] <= 1'b1; opd[c][fl] <= rb_head[p][FW-1:0]; end
                        end
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
