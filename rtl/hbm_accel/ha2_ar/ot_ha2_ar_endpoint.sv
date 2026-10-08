`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_ha2_ar_endpoint: HA2 cut-through collective endpoint of one die
// (accelerator (ours); ENABLE = 0 by default: every output tied off).
//
// r2 (2026-10-04): every producer is flow-controlled, so the payload size no
// longer sizes any queue, and the 1.2 GHz paths are registered:
//   * hub injection runs on credits (IQD-deep input FIFO a lane, credit return
//     over HUBW stages), so the hub never overruns the endpoint;
//   * the reducer issues only with room in the result FIFO (in-flight counted);
//   * own results and relayed results go through a duplicated staging
//     register (cycle 1: pick and pop, cycle 2: push to the port queues) and
//     are picked only when every destination queue has room for two;
//   * each port sends at most at its serializer rate (core-side pacing), so
//     the TX clock-crossing FIFO in the link never fills;
//   * delivery is DEL independent 1-of-k round-robin lanes (static source
//     partition) instead of one chained DEL-of-17 grant;
//   * every FIFO has a registered head (ot_ha2_fifo r2), so queue depth (flops
//     or SRAM) is off the arbitration paths; port outputs are registered.
//
// TOPOLOGY  N = GS x NG dies.  Die rank is lane L = rank % GS of group
//   G = rank / GS.  Ports 0 .. GS-2 are LOCAL (port p <-> lane p + (p >= L));
//   ports GS-1 .. GS+NG-3 are GLOBAL (port GS-1+q <-> the same lane of group
//   q + (q >= G)).  DS-V4.1 TP-96: GS 16, NG 6 -> 20 ports a die.
//
// OPERATION (one collective, one stream, flit cut-through everywhere)
//   NOG reduction groups of NC contributors (ranks og*NC .. og*NC+NC-1); each
//   contributor holds E FP32 values (PF = E / LANES flits).
//   RS     (ONESHOT = 0) partial flit f belongs to owner s = f / OF of the
//          group; slice-interleaved injection, straight to the owner's port.
//          (ONESHOT = 1) every flit to all NC-1 peers (TP-2 one-shot).
//   REDUCE per owned flit once all NC operands are slotted: the golden's
//          fixed pairwise tree over contributors in rank order with
//          ot_hdc_fp32_add_lat #(LAT), then (BF16 = 1) the golden to_bf16 and
//          two reduced flits per result flit.  NC = 1 is an all-gather.
//   AG     (ONESHOT = 0) a result flit goes to all 20 ports; one arriving on a
//          GLOBAL port is delivered AND relayed on every local port.
// Arrival order never changes a result: operands are slotted by
// (contributor, flit) and reduced in the fixed order.
//
// Flit = {kind[1], src[8], idx[16], data[FW]}: kind 0 partial (src =
//   contributor, idx = owned-flit index), kind 1 result (idx = global
//   result-flit index).
// ---------------------------------------------------------------------------
module ot_ha2_ar_endpoint #(
    parameter integer ENABLE  = 0,
    parameter integer GS      = 16,
    parameter integer NG      = 6,
    parameter integer NC      = 8,
    parameter integer NOG     = 8,
    parameter integer E       = 1024,
    parameter integer LANES   = 16,
    parameter integer ONESHOT = 0,
    parameter integer BF16    = 1,
    parameter integer INJ     = 2,
    parameter integer DEL     = 4,
    parameter integer HUBW    = 35,
    parameter integer RXAW    = 7,       // receive buffer = credit pool, 2^RXAW flits a port
    parameter integer QAW     = 4,       // transmit / staging queue depth 2^QAW
    parameter integer IQAW    = 5,       // hub input FIFO a lane (= hub credits)
    parameter integer LAT     = 7,
    parameter integer PACE_X100 = 17638, // serializer payload bits a core cycle x 100 (211.65 b/ns x 0.8333 ns)
    parameter integer PWB     = 551,     // wire bits charged a flit
    parameter integer FW      = 32 * LANES,
    parameter integer PWT     = FW + 25,
    parameter integer NP      = (GS - 1) + (NG - 1)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [7:0]           rank,            // die index (strap)
    input  wire                 go,              // level: start the collective (hub issue)
    output wire [INJ*16-1:0]    inj_idx,         // partial flits the hub reads this cycle
    output wire [INJ-1:0]       inj_rd,
    input  wire [INJ*FW-1:0]    inj_data,        // combinational read of the hub's partial buffer
    output wire [NP-1:0]        tx_valid,
    output wire [NP*PWT-1:0]    tx_flit,
    input  wire [NP-1:0]        cr_ret,
    input  wire [NP-1:0]        rx_valid,
    input  wire [NP*PWT-1:0]    rx_flit,
    output wire [NP-1:0]        rx_credit,
    output wire [DEL-1:0]       del_valid,       // results committed at the hub (after HUBW stages)
    output wire [DEL*PWT-1:0]   del_flit,
    output wire                 fault,
    output wire [31:0]          stat_credit_stall
);
    localparam integer NL   = GS - 1;
    localparam integer NGL  = NP - NL;
    localparam integer PF   = E / LANES;
    localparam integer OF   = ONESHOT ? PF : PF / NC;
    localparam integer RPF  = BF16 ? 2 : 1;
    localparam integer ROF  = OF / RPF;
    localparam integer LV   = $clog2(NC);
    localparam integer RXD  = 1 << RXAW;
    localparam integer QD   = 1 << QAW;
    localparam integer IQD  = 1 << IQAW;
    localparam integer NDS  = NL + 2;                 // delivery sources: local ports, own, relayed
    localparam integer CW   = RXAW + 2;
    localparam integer OFW  = (OF > 1) ? $clog2(OF) : 1;
    localparam integer NREP = 4;                      // duplicated staging registers (fan-out split)

    // golden to_bf16: (b + 0x7FFF + ((b >> 16) & 1)) >> 16
    function automatic [15:0] bf16(input [31:0] b);
        reg [32:0] s;
        s = {1'b0, b} + 33'h7FFF + {32'b0, b[16]};
        bf16 = s[31:16];
    endfunction

    generate if (ENABLE == 0) begin : g_off
        assign inj_idx = '0; assign inj_rd = '0; assign tx_valid = '0; assign tx_flit = '0;
        assign rx_credit = '0; assign del_valid = '0; assign del_flit = '0; assign fault = 1'b0;
        assign stat_credit_stall = 0;
    end else begin : g_on
        // ---- static configuration from the rank strap (registered) -----------------------------------
        reg [7:0] r_rank;
        reg [4:0] cfg_l;                              // my lane
        reg [7:0] cfg_og, cfg_j;
        reg       cfg_contrib;
        reg [4:0] cfg_port_of_owner [0:NC-1];         // local port of each group member
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                r_rank <= 0; cfg_l <= 0; cfg_og <= 0; cfg_j <= 0; cfg_contrib <= 1'b0;
                for (integer c = 0; c < NC; c = c + 1) cfg_port_of_owner[c] <= 0;
            end else begin : cfg
                integer rk, l, lane;
                rk = integer'(rank);
                l = rk % GS;
                r_rank <= rank;
                cfg_l <= 5'(l);
                cfg_og <= 8'(rk / NC);
                cfg_j <= 8'(rk % NC);
                cfg_contrib <= rk < NOG * NC;
                for (integer c = 0; c < NC; c = c + 1) begin
                    lane = ((rk / NC) * NC + c) % GS;
                    cfg_port_of_owner[c] <= 5'(lane - (lane > l ? 1 : 0));
                end
            end

        // ================= hub issue on credits -> HUBW wire stages -> input FIFOs ======================
        integer k;
        reg started;
        reg [7:0] icred [0:INJ-1];
        reg [INJ*16-1:0] r_idx;
        reg [INJ-1:0] r_rd;
        wire [INJ-1:0] icr_ret;
        always @* begin
            r_idx = '0; r_rd = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (cfg_contrib && started && k + i < PF && icred[i] != 0 && (i == 0 || r_rd[0])) begin
                    r_rd[i] = 1'b1;
                    r_idx[16*i +: 16] = ONESHOT ? 16'(k + i) : 16'(((k + i) % NC) * OF + (k + i) / NC);
                end
        end
        assign inj_idx = r_idx;
        assign inj_rd  = r_rd;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                k <= 0; started <= 1'b0;
                for (integer i = 0; i < INJ; i = i + 1) icred[i] <= 8'(IQD);
            end else begin : hubc
                integer n;
                if (go && !started) started <= 1'b1;
                n = 0;
                for (integer i = 0; i < INJ; i = i + 1) if (r_rd[i]) n = n + 1;
                k <= k + n;
                for (integer i = 0; i < INJ; i = i + 1)
                    icred[i] <= icred[i] - (r_rd[i] ? 8'd1 : 8'd0) + (icr_ret[i] ? 8'd1 : 8'd0);
            end
        wire [INJ-1:0] h_v;
        wire [INJ*(16+FW)-1:0] h_d;
        wire [INJ-1:0] iq_empty, iq_ovf;
        wire [16+FW-1:0] iq_head [0:INJ-1];
        reg  [INJ-1:0] iq_pop;
        for (genvar i = 0; i < INJ; i = i + 1) begin : g_hub
            ot_ha2_delay #(.W(16 + FW), .D(HUBW)) u_h (.clk(clk), .rst_n(rst_n), .v_in(r_rd[i]),
                .d_in({r_idx[16*i +: 16], inj_data[FW*i +: FW]}), .v_out(h_v[i]),
                .d_out(h_d[(16+FW)*i +: 16+FW]));
            wire [IQAW:0] c, sp;
            ot_ha2_fifo #(.W(16 + FW), .AW(IQAW)) u_iq (.clk(clk), .rst_n(rst_n), .push(h_v[i]),
                .din(h_d[(16+FW)*i +: 16+FW]), .pop(iq_pop[i]), .empty(iq_empty[i]), .dout(iq_head[i]),
                .ovf(iq_ovf[i]), .count(c), .space(sp));
            wire unused;
            ot_ha2_delay #(.W(1), .D(HUBW)) u_hc (.clk(clk), .rst_n(rst_n), .v_in(iq_pop[i]), .d_in(1'b1),
                .v_out(icr_ret[i]), .d_out(unused));
        end

        // ================= per-port transmit queues, pacing, credits, registered outputs ===============
        reg  [NP-1:0] qp_push, qr_push, ql_push;
        reg  [PWT-1:0] qp_din [0:NP-1];
        wire [NP-1:0] qp_empty, qr_empty, ql_empty, qp_ovf, qr_ovf, ql_ovf;
        wire [NP-1:0] qp_sp1, qr_sp2, ql_sp2;
        wire [PWT-1:0] qp_head [0:NP-1];
        wire [PWT-1:0] qr_head [0:NP-1];
        wire [PWT-1:0] ql_head [0:NP-1];
        reg  [NP-1:0] qp_pop, qr_pop, ql_pop;
        reg  [CW-1:0] credit [0:NP-1];
        reg  [NP-1:0] cr_ok;                          // registered: credit != 0
        integer pace [0:NP-1];
        reg  [NP-1:0] pace_ok;                        // registered: a flit's bits have accrued
        reg  [31:0] cstall;
        reg  [NP-1:0] tv;
        reg  [PWT-1:0] tf [0:NP-1];
        // duplicated staging registers for own results and relays (written below)
        (* keep *) reg [PWT-1:0] own_st [0:NREP-1];
        (* keep *) reg [PWT-1:0] rly_st [0:NREP-1];
        reg own_st_v, rly_st_v;
        for (genvar p = 0; p < NP; p = p + 1) begin : g_txq
            wire [QAW:0] c0, c1, c2, s0, s1, s2;
            ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_qp (.clk(clk), .rst_n(rst_n), .push(qp_push[p]), .din(qp_din[p]),
                .pop(qp_pop[p]), .empty(qp_empty[p]), .dout(qp_head[p]), .ovf(qp_ovf[p]), .count(c0), .space(s0));
            ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_qr (.clk(clk), .rst_n(rst_n), .push(qr_push[p]),
                .din(own_st[p % NREP]), .pop(qr_pop[p]), .empty(qr_empty[p]), .dout(qr_head[p]), .ovf(qr_ovf[p]),
                .count(c1), .space(s1));
            assign qp_sp1[p] = s0 >= 1;
            assign qr_sp2[p] = s1 >= 2;
            if (p < NL) begin : g_rly
                ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_ql (.clk(clk), .rst_n(rst_n), .push(ql_push[p]),
                    .din(rly_st[p % NREP]), .pop(ql_pop[p]), .empty(ql_empty[p]), .dout(ql_head[p]),
                    .ovf(ql_ovf[p]), .count(c2), .space(s2));
                assign ql_sp2[p] = s2 >= 2;
            end else begin : g_norly
                assign ql_empty[p] = 1'b1; assign ql_head[p] = '0; assign ql_ovf[p] = 1'b0;
                assign ql_sp2[p] = 1'b1; assign c2 = 0; assign s2 = 0;
            end
            assign tx_valid[p] = tv[p];
            assign tx_flit[p*PWT +: PWT] = tf[p];
        end
        // arbiter: partial > own result > relay; one flit a cycle a port, with a credit and the pace accrued
        always @* begin
            qp_pop = '0; qr_pop = '0; ql_pop = '0;
            for (integer p = 0; p < NP; p = p + 1)
                if (cr_ok[p] && pace_ok[p]) begin
                    if (!qp_empty[p]) qp_pop[p] = 1'b1;
                    else if (!qr_empty[p]) qr_pop[p] = 1'b1;
                    else if (!ql_empty[p]) ql_pop[p] = 1'b1;
                end
        end
        wire [NP-1:0] send = qp_pop | qr_pop | ql_pop;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (integer p = 0; p < NP; p = p + 1) begin
                    credit[p] <= CW'(RXD); pace[p] <= 0; tf[p] <= '0;
                end
                cr_ok <= '1; pace_ok <= '0; tv <= '0; cstall <= 0;
            end else begin
                for (integer p = 0; p < NP; p = p + 1) begin : port
                    reg [CW-1:0] cn;
                    integer a;
                    cn = credit[p] - (send[p] ? 1'b1 : 1'b0) + (cr_ret[p] ? 1'b1 : 1'b0);
                    credit[p] <= cn;
                    cr_ok[p] <= cn != 0;
                    a = pace[p] + PACE_X100;
                    if (a > PWB * 100) a = PWB * 100;
                    if (send[p]) a = a - PWB * 100;
                    pace[p] <= a;
                    pace_ok[p] <= (a + PACE_X100 >= PWB * 100);
                    tv[p] <= send[p];
                    tf[p] <= qp_pop[p] ? qp_head[p] : qr_pop[p] ? qr_head[p] : ql_head[p];
                    if (!cr_ok[p] && !(qp_empty[p] && qr_empty[p] && ql_empty[p])) cstall <= cstall + 1;
                end
            end
        assign stat_credit_stall = cstall;

        // ================= receive buffers (the credit pools) =========================================
        reg  [NP-1:0] rb_pop;
        wire [NP-1:0] rb_empty, rb_ovf;
        wire [PWT-1:0] rb_head [0:NP-1];
        for (genvar p = 0; p < NP; p = p + 1) begin : g_rxb
            wire [RXAW:0] cnt, sp;
            ot_ha2_fifo #(.W(PWT), .AW(RXAW)) u_rb (.clk(clk), .rst_n(rst_n), .push(rx_valid[p]),
                .din(rx_flit[p*PWT +: PWT]), .pop(rb_pop[p]), .empty(rb_empty[p]), .dout(rb_head[p]),
                .ovf(rb_ovf[p]), .count(cnt), .space(sp));
        end
        reg [NP-1:0] rx_credit_r;
        always @(posedge clk or negedge rst_n) if (!rst_n) rx_credit_r <= '0; else rx_credit_r <= rb_pop;
        assign rx_credit = rx_credit_r;

        // ================= operand slots, reducer, result FIFO =========================================
        reg [FW-1:0] opd [0:NC-1][0:OF-1];
        reg [OF-1:0] pres [0:NC-1];
        reg dupe;
        integer rptr;
        reg [NC-1:0] col;
        always @* for (integer c = 0; c < NC; c = c + 1) col[c] = (rptr < OF) ? pres[c][rptr] : 1'b0;
        integer inflight;                              // reduced flits issued, not yet in the result FIFO
        wire [QAW:0] rq_cnt, rq_sp;
        wire issue = (&col) && (integer'(rq_sp) * RPF > inflight + 2 * RPF);
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
        reg [FW-1:0] hold;
        reg          r_v;
        reg [15:0]   r_m;
        reg [FW-1:0] r_d;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) r_v <= 1'b0;
            else begin
                r_v <= 1'b0;
                if (lvv[LV]) begin
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
        always @(posedge clk or negedge rst_n)
            if (!rst_n) inflight <= 0;
            else inflight <= inflight + (issue ? 1 : 0) - ((lvv[LV]) ? 1 : 0);
        reg [15:0] my_gi;
        always @* my_gi = ONESHOT ? r_m : 16'((integer'(cfg_og) * NC + integer'(cfg_j)) * ROF + integer'(r_m));
        wire rq_empty, rq_ovf;
        wire [PWT-1:0] rq_head;
        reg rq_pop;
        ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_rq (.clk(clk), .rst_n(rst_n), .push(r_v),
            .din({1'b1, cfg_j, my_gi, r_d}), .pop(rq_pop), .empty(rq_empty), .dout(rq_head), .ovf(rq_ovf),
            .count(rq_cnt), .space(rq_sp));

        // ================= delivery queues ================================================================
        wire dq_own_empty, dq_own_ovf, dq_rly_empty, dq_rly_ovf;
        wire [PWT-1:0] dq_own_head, dq_rly_head;
        wire [QAW:0] dc0, dc1, ds0, ds1;
        reg dq_own_pop, dq_rly_pop;
        ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_dqo (.clk(clk), .rst_n(rst_n), .push(own_st_v), .din(own_st[0]),
            .pop(dq_own_pop), .empty(dq_own_empty), .dout(dq_own_head), .ovf(dq_own_ovf), .count(dc0), .space(ds0));
        ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_dqr (.clk(clk), .rst_n(rst_n), .push(rly_st_v), .din(rly_st[0]),
            .pop(dq_rly_pop), .empty(dq_rly_empty), .dout(dq_rly_head), .ovf(dq_rly_ovf), .count(dc1), .space(ds1));

        // ================= own-result stage and relay stage (pick + pop, then push) ====================
        wire own_room = (&qr_sp2) && (ds0 >= 2);
        wire rly_room = (&ql_sp2[NL-1:0]) && (ds1 >= 2);
        integer grot;
        reg [NGL-1:0] gglob;                          // relay grant (one-hot over global ports)
        always @* begin : rly_pick
            integer s, q;
            s = 0;
            gglob = '0;
            for (q = 0; q < NGL; q = q + 1) begin
                s = grot + q; if (s >= NGL) s = s - NGL;
                if (gglob == 0 && !rb_empty[NL + s] && rb_head[NL + s][PWT-1]) gglob[s] = 1'b1;
            end
            if (ONESHOT || !rly_room) gglob = '0;
        end
        always @* rq_pop = !rq_empty && own_room;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin own_st_v <= 1'b0; rly_st_v <= 1'b0; grot <= 0; end
            else begin
                own_st_v <= rq_pop;
                if (rq_pop) for (integer r = 0; r < NREP; r = r + 1) own_st[r] <= rq_head;
                rly_st_v <= |gglob;
                for (integer q = 0; q < NGL; q = q + 1)
                    if (gglob[q]) for (integer r = 0; r < NREP; r = r + 1) rly_st[r] <= rb_head[NL + q];
                grot <= (grot + 1 >= NGL) ? 0 : grot + 1;
            end
        always @* begin
            qr_push = '0; ql_push = '0;
            if (own_st_v && !ONESHOT) qr_push = '1;
            if (rly_st_v) for (integer p = 0; p < NL; p = p + 1) ql_push[p] = 1'b1;
        end

        // ================= delivery: DEL independent round-robin lanes over a static source split ======
        // source s: 0 .. NL-1 local port s, NL own results, NL+1 relayed results; lane j serves s % DEL == j
        localparam integer SPL = (NDS + DEL - 1) / DEL;
        reg [NDS-1:0] dgrant;
        reg [DEL-1:0] dv;
        reg [PWT-1:0] dfl [0:DEL-1];
        integer drot [0:DEL-1];
        // request vector over the sources, padded to DEL x SPL with zeros
        wire [DEL*SPL-1:0] dreq;
        wire [PWT-1:0] dsrc [0:DEL*SPL-1];
        for (genvar s = 0; s < DEL * SPL; s = s + 1) begin : g_dreq
            if (s < NL) begin : g_l
                assign dreq[s] = !rb_empty[s] && rb_head[s][PWT-1];
                assign dsrc[s] = rb_head[s];
            end else if (s == NL) begin : g_o
                assign dreq[s] = !dq_own_empty;
                assign dsrc[s] = dq_own_head;
            end else if (s == NL + 1) begin : g_r
                assign dreq[s] = !dq_rly_empty;
                assign dsrc[s] = dq_rly_head;
            end else begin : g_z
                assign dreq[s] = 1'b0;
                assign dsrc[s] = '0;
            end
        end
        reg [DEL*SPL-1:0] dg;                         // grants, at most one a lane
        always @* begin : dpick
            integer t, u;
            t = 0; u = 0;
            dg = '0;
            for (integer j = 0; j < DEL; j = j + 1)
                for (integer i = SPL - 1; i >= 0; i = i - 1) begin   // lowest rotated index wins
                    t = drot[j] + i; if (t >= SPL) t = t - SPL;
                    if (dreq[j + DEL * t]) begin
                        for (u = 0; u < SPL; u = u + 1) dg[j + DEL * u] = 1'b0;
                        dg[j + DEL * t] = 1'b1;
                    end
                end
        end
        always @* dgrant = dg[NDS-1:0];
        always @* begin
            dq_own_pop = dgrant[NL];
            dq_rly_pop = dgrant[NL + 1];
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                dv <= '0;
                for (integer j = 0; j < DEL; j = j + 1) begin drot[j] <= 0; dfl[j] <= '0; end
            end else
                for (integer j = 0; j < DEL; j = j + 1) begin
                    dv[j] <= 1'b0;
                    drot[j] <= (drot[j] + 1 >= SPL) ? 0 : drot[j] + 1;
                    for (integer t = 0; t < SPL; t = t + 1)
                        if (dg[j + DEL * t]) begin
                            dv[j] <= 1'b1;
                            dfl[j] <= dsrc[j + DEL * t];
                        end
                end
        for (genvar i = 0; i < DEL; i = i + 1) begin : g_del
            ot_ha2_delay #(.W(PWT), .D(HUBW)) u_d (.clk(clk), .rst_n(rst_n), .v_in(dv[i]), .d_in(dfl[i]),
                .v_out(del_valid[i]), .d_out(del_flit[i*PWT +: PWT]));
        end

        // ================= receive-side pops ==============================================================
        always @* begin
            rb_pop = '0;
            for (integer p = 0; p < NP; p = p + 1)
                if (!rb_empty[p] && !rb_head[p][PWT-1]) rb_pop[p] = 1'b1;          // partials: always slotted
            for (integer q = 0; q < NGL; q = q + 1) if (gglob[q]) rb_pop[NL + q] = 1'b1;
            for (integer s = 0; s < NL; s = s + 1) if (dgrant[s]) rb_pop[s] = 1'b1;
        end

        // ================= injected partials: own slot or the owner's port queue ========================
        always @* begin : idisp
            integer f, s, lane;
            reg [4:0] tp;
            reg [NP-1:0] used;
            f = 0; s = 0; lane = 0; tp = '0;
            qp_push = '0; iq_pop = '0; used = '0;
            for (integer p = 0; p < NP; p = p + 1) qp_din[p] = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (!iq_empty[i]) begin
                    f = integer'(iq_head[i][FW +: 16]);
                    if (ONESHOT) begin
                        if (&qp_sp1[NL-1:0] && used == 0) begin
                            iq_pop[i] = 1'b1;
                            for (integer c = 0; c < NC; c = c + 1)
                                if (c != integer'(cfg_j)) begin
                                    tp = cfg_port_of_owner[c];
                                    qp_push[tp] = 1'b1; used[tp] = 1'b1;
                                    qp_din[tp] = {1'b0, cfg_j, 16'(f), iq_head[i][FW-1:0]};
                                end
                        end
                    end else begin
                        s = f / OF;
                        if (s == integer'(cfg_j)) iq_pop[i] = 1'b1;
                        else begin
                            tp = cfg_port_of_owner[s];
                            if (qp_sp1[tp] && !used[tp]) begin
                                iq_pop[i] = 1'b1; qp_push[tp] = 1'b1; used[tp] = 1'b1;
                                qp_din[tp] = {1'b0, cfg_j, 16'(f % OF), iq_head[i][FW-1:0]};
                            end
                        end
                    end
                end
        end

        // ================= operand slot writes, reducer pointer ==========================================
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (integer c = 0; c < NC; c = c + 1) pres[c] <= '0;
                rptr <= 0; dupe <= 1'b0;
            end else begin
                for (integer i = 0; i < INJ; i = i + 1)
                    if (iq_pop[i]) begin : own
                        integer f, fl;
                        f = integer'(iq_head[i][FW +: 16]);
                        if (ONESHOT || f / OF == integer'(cfg_j)) begin
                            fl = ONESHOT ? f : f % OF;
                            if (pres[cfg_j][fl]) dupe <= 1'b1;
                            pres[cfg_j][fl] <= 1'b1;
                            opd[cfg_j][fl] <= iq_head[i][FW-1:0];
                        end
                    end
                for (integer p = 0; p < NP; p = p + 1)
                    if (rb_pop[p] && !rb_head[p][PWT-1]) begin : peer
                        integer c, fl;
                        c = integer'(rb_head[p][FW+16 +: 8]);
                        fl = integer'(rb_head[p][FW +: 16]);
                        if (c >= NC || fl >= OF || pres[c][fl]) dupe <= 1'b1;
                        else begin pres[c][fl] <= 1'b1; opd[c][fl] <= rb_head[p][FW-1:0]; end
                    end
                if (issue) begin
                    for (integer c = 0; c < NC; c = c + 1) pres[c][rptr] <= 1'b0;
                    rptr <= rptr + 1;
                end
            end
        reg anyovf;
        always @* begin
            anyovf = dq_own_ovf | dq_rly_ovf | rq_ovf | (|iq_ovf);
            for (integer p = 0; p < NP; p = p + 1) anyovf = anyovf | qp_ovf[p] | qr_ovf[p] | ql_ovf[p] | rb_ovf[p];
        end
        assign fault = anyovf | dupe;
    end endgenerate
endmodule

// Parameter-free physical top: the DS-V4.1 TP-96 endpoint (20 ports, NC 8, LAT 7) as routed.  Hub wire stages
// (35 a direction) are channel repeater flops priced in the floorplan, so HUBW = 1 here; the credit pool and
// queue stores are 4 deep (registered heads keep the store depth off every arbitration path; the 128-deep pool
// is an SRAM store priced separately).
module ot_ha2_ar_endpoint_ds_phys (
    input  wire clk, rst_n, input wire [7:0] rank, input wire go,
    output wire [31:0] inj_idx, output wire [1:0] inj_rd, input wire [1023:0] inj_data,
    output wire [19:0] tx_valid, output wire [20*537-1:0] tx_flit, input wire [19:0] cr_ret,
    input  wire [19:0] rx_valid, input wire [20*537-1:0] rx_flit, output wire [19:0] rx_credit,
    output wire [3:0] del_valid, output wire [4*537-1:0] del_flit, output wire fault,
    output wire [31:0] stat_credit_stall
);
    ot_ha2_ar_endpoint #(.ENABLE(1), .GS(16), .NG(6), .NC(8), .NOG(8), .E(1024), .LANES(16), .ONESHOT(0),
        .BF16(1), .INJ(2), .DEL(4), .HUBW(1), .RXAW(2), .QAW(2), .IQAW(2), .LAT(7))
      u (.clk(clk), .rst_n(rst_n), .rank(rank), .go(go), .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_data(inj_data),
         .tx_valid(tx_valid), .tx_flit(tx_flit), .cr_ret(cr_ret), .rx_valid(rx_valid), .rx_flit(rx_flit),
         .rx_credit(rx_credit), .del_valid(del_valid), .del_flit(del_flit), .fault(fault),
         .stat_credit_stall(stat_credit_stall));
endmodule
