`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_ha2_ar_endpoint: HA2 cut-through all-reduce endpoint of one die
// (accelerator (ours); ENABLE = 0 by default: every output tied off).
//
// TOPOLOGY  N = GS x NG dies.  Die RANK is lane L = RANK % GS of group
//   G = RANK / GS.  Ports 0 .. GS-2 are LOCAL (direct link to every other
//   lane of the group: port p <-> lane p + (p >= L)); ports GS-1 .. GS+NG-3
//   are GLOBAL (port GS-1+q <-> the same lane of group q + (q >= G)).
//   DS-V4.1 TP-96: GS 16, NG 6 -> 15 + 5 = 20 ports a die.
//
// OPERATION (one all-reduce, one stream, flit cut-through everywhere)
//   NOG reduction groups of NC contributors (ranks og*NC .. og*NC+NC-1);
//   each contributor holds E FP32 partials (PF = E / LANES flits).
//   RS   (ONESHOT = 0) partial flit f belongs to owner s = f / OF of the
//        group (OF = PF / NC); the hub injects INJ flits a cycle in
//        slice-interleaved order, each goes straight to its owner's port.
//        (ONESHOT = 1) every contributor owns every flit: each flit goes to
//        all NC-1 peers (TP-2 one-shot).
//   REDUCE per owned flit, as soon as all NC operands are present: the
//        golden's fixed pairwise tree ((p0+p1)+(p2+p3))+((p4+p5)+(p6+p7))
//        over contributors in rank order, ot_hdc_fp32_add_lat #(LAT) per
//        lane (bit-equal to ot_hdc_fp32_add_fast), then (BF16 = 1) the
//        golden's to_bf16 RNE; two reduced flits pack into one result flit.
//   AG   (ONESHOT = 0) each result flit is sent on all 20 ports at once;
//        a result arriving on a GLOBAL port is delivered AND relayed on all
//        local ports (2-level multicast); one arriving on a LOCAL port is
//        delivered.  Delivery to the hub is DEL flits a cycle.
// Arrival order never changes a result: operands are slotted by
// (contributor, flit) and reduced in the fixed order.
//
// Flit = {kind[1], src[8], idx[16], data[FW]}: kind 0 partial (src =
//   contributor j, idx = owned-flit index), kind 1 result (idx = global
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
    parameter integer RXAW    = 5,       // receive buffer / credit pool 2^RXAW flits a port
    parameter integer QAW     = 5,       // transmit queue depth 2^QAW
    parameter integer LAT     = 7,
    parameter integer FW      = 32 * LANES,
    parameter integer PWT     = FW + 25,
    parameter integer NP      = (GS - 1) + (NG - 1)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [7:0]           rank,            // die index (strap; one module for every die)
    input  wire                 go,              // level: start the all-reduce (hub issue)
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
    wire [31:0] RANK = {24'b0, rank};
    wire [31:0] L = RANK % GS;
    wire [31:0] OG = RANK / NC, J = RANK % NC;
    wire CONTRIB = RANK < NOG * NC;
    localparam integer PF   = E / LANES;
    localparam integer OF   = ONESHOT ? PF : PF / NC;
    localparam integer RPF  = BF16 ? 2 : 1;
    localparam integer ROF  = OF / RPF;
    localparam integer LV   = $clog2(NC);
    localparam integer HDR  = 25;
    localparam integer RXD  = 1 << RXAW;

    generate if (ENABLE == 0) begin : g_off
        assign inj_idx = '0; assign inj_rd = '0; assign tx_valid = '0; assign tx_flit = '0;
        assign rx_credit = '0; assign del_valid = '0; assign del_flit = '0; assign fault = 1'b0;
        assign stat_credit_stall = 0;
    end else begin : g_on
        // ================= hub issue -> HUBW wire stages -> endpoint ================================
        integer k;                          // next injected flit
        reg started;
        reg [INJ*16-1:0] r_idx;
        reg [INJ-1:0] r_rd;
        always @* begin
            r_idx = '0; r_rd = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (CONTRIB && started && k + i < PF) begin
                    r_rd[i] = 1'b1;
                    r_idx[16*i +: 16] = ONESHOT ? 16'(k + i) : 16'(((k + i) % NC) * OF + (k + i) / NC);
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
        wire [INJ*(16+FW)-1:0] h_d;
        for (genvar i = 0; i < INJ; i = i + 1) begin : g_hub
            ot_ha2_delay #(.W(16 + FW), .D(HUBW)) u_h (.clk(clk), .rst_n(rst_n), .v_in(r_rd[i]),
                .d_in({r_idx[16*i +: 16], inj_data[FW*i +: FW]}), .v_out(h_v[i]),
                .d_out(h_d[(16+FW)*i +: 16+FW]));
        end

        // ================= per-port transmit queues, arbiters, credits =============================
        // q_part: partials to the owner(s); q_res: own result flits; q_rly: relayed results (local ports)
        reg  [NP-1:0] qp_push, qr_push, ql_push;
        reg  [PWT-1:0] qp_din [0:NP-1];
        reg  [PWT-1:0] qr_din, ql_din;
        wire [NP-1:0] qp_empty, qr_empty, ql_empty, qp_ovf, qr_ovf, ql_ovf;
        wire [PWT-1:0] qp_head [0:NP-1];
        wire [PWT-1:0] qr_head [0:NP-1];
        wire [PWT-1:0] ql_head [0:NP-1];
        reg  [NP-1:0] qp_pop, qr_pop, ql_pop;
        integer credit [0:NP-1];
        reg [31:0] cstall;
        reg [NP-1:0] tv;
        reg [PWT-1:0] tf [0:NP-1];
        for (genvar p = 0; p < NP; p = p + 1) begin : g_txq
            wire [QAW:0] c0, c1, c2;
            ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_qp (.clk(clk), .rst_n(rst_n), .push(qp_push[p]), .din(qp_din[p]),
                .pop(qp_pop[p]), .empty(qp_empty[p]), .dout(qp_head[p]), .ovf(qp_ovf[p]), .count(c0));
            ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_qr (.clk(clk), .rst_n(rst_n), .push(qr_push[p]), .din(qr_din),
                .pop(qr_pop[p]), .empty(qr_empty[p]), .dout(qr_head[p]), .ovf(qr_ovf[p]), .count(c1));
            if (p < NL) begin : g_rly
                ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_ql (.clk(clk), .rst_n(rst_n), .push(ql_push[p]),
                    .din(ql_din), .pop(ql_pop[p]), .empty(ql_empty[p]), .dout(ql_head[p]), .ovf(ql_ovf[p]),
                    .count(c2));
            end else begin : g_norly
                assign ql_empty[p] = 1'b1; assign ql_head[p] = '0; assign ql_ovf[p] = 1'b0;
            end
            assign tx_valid[p] = tv[p];
            assign tx_flit[p*PWT +: PWT] = tf[p];
        end
        // arbiter: partial > own result > relay, one flit a cycle a port, only with a credit
        always @* begin
            qp_pop = '0; qr_pop = '0; ql_pop = '0; tv = '0;
            for (integer p = 0; p < NP; p = p + 1) begin
                tf[p] = '0;
                if (credit[p] > 0) begin
                    if (!qp_empty[p]) begin qp_pop[p] = 1'b1; tv[p] = 1'b1; tf[p] = qp_head[p]; end
                    else if (!qr_empty[p]) begin qr_pop[p] = 1'b1; tv[p] = 1'b1; tf[p] = qr_head[p]; end
                    else if (!ql_empty[p]) begin ql_pop[p] = 1'b1; tv[p] = 1'b1; tf[p] = ql_head[p]; end
                end
            end
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (integer p = 0; p < NP; p = p + 1) credit[p] <= RXD;
                cstall <= 0;
            end else begin
                for (integer p = 0; p < NP; p = p + 1) begin
                    credit[p] <= credit[p] - (tv[p] ? 1 : 0) + (cr_ret[p] ? 1 : 0);
                    if (credit[p] == 0 && !(qp_empty[p] && qr_empty[p] && ql_empty[p])) cstall <= cstall + 1;
                end
            end
        assign stat_credit_stall = cstall;

        // ================= receive buffers (the credit pools) ======================================
        reg  [NP-1:0] rb_pop;
        wire [NP-1:0] rb_empty, rb_ovf;
        wire [PWT-1:0] rb_head [0:NP-1];
        for (genvar p = 0; p < NP; p = p + 1) begin : g_rxb
            wire [RXAW:0] cnt;
            ot_ha2_fifo #(.W(PWT), .AW(RXAW)) u_rb (.clk(clk), .rst_n(rst_n), .push(rx_valid[p]),
                .din(rx_flit[p*PWT +: PWT]), .pop(rb_pop[p]), .empty(rb_empty[p]), .dout(rb_head[p]),
                .ovf(rb_ovf[p]), .count(cnt));
        end
        assign rx_credit = rb_pop;

        // ================= operand slots and the reduction tree ====================================
        reg [FW-1:0] opd [0:NC-1][0:OF-1];
        reg [OF-1:0] pres [0:NC-1];
        reg dupe;
        integer rptr;
        wire all_here;
        reg  [NC-1:0] col;
        always @* for (integer c = 0; c < NC; c = c + 1) col[c] = (rptr < OF) ? pres[c][rptr] : 1'b0;
        assign all_here = &col;
        wire issue = all_here;
        // owner / port of an injected partial flit
        function automatic integer lport(input integer lane);     // local port index of a lane of my group
            lport = lane - (lane > L ? 1 : 0);
        endfunction

        // tree
        wire [FW-1:0] lvl [0:LV][0:NC-1];
        wire [LV:0] lvv;
        wire [LV:0] lerr;
        reg  [FW-1:0] opsel [0:NC-1];
        always @* for (integer c = 0; c < NC; c = c + 1) opsel[c] = opd[c][rptr < OF ? rptr : 0];
        for (genvar c = 0; c < NC; c = c + 1) begin : g_l0
            assign lvl[0][c] = opsel[c];
        end
        assign lvv[0] = issue;
        assign lerr[0] = 1'b0;
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
            assign lerr[l] = lerr[l-1];
        end
        // the flit index rides beside the tree
        wire        ti_v;
        wire [15:0] ti_d;
        ot_ha2_delay #(.W(16), .D(LAT * LV)) u_tidx (.clk(clk), .rst_n(rst_n), .v_in(issue), .d_in(16'(rptr)),
            .v_out(ti_v), .d_out(ti_d));
        // golden to_bf16: (b + 0x7FFF + ((b >> 16) & 1)) >> 16
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
        wire [15:0] my_gi = ONESHOT ? r_m : 16'((OG * NC + J) * ROF + integer'(r_m));
        wire [PWT-1:0] res_flit = {1'b1, 8'(J), my_gi, r_d};

        // ================= delivery queues ==========================================================
        wire dq_own_empty, dq_own_ovf, dq_rly_empty, dq_rly_ovf;
        wire [PWT-1:0] dq_own_head, dq_rly_head;
        reg dq_own_pop, dq_rly_pop, dq_rly_push;
        reg [PWT-1:0] dq_rly_din;
        wire [QAW:0] dc0, dc1;
        ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_dqo (.clk(clk), .rst_n(rst_n), .push(r_v), .din(res_flit),
            .pop(dq_own_pop), .empty(dq_own_empty), .dout(dq_own_head), .ovf(dq_own_ovf), .count(dc0));
        ot_ha2_fifo #(.W(PWT), .AW(QAW)) u_dqr (.clk(clk), .rst_n(rst_n), .push(dq_rly_push), .din(dq_rly_din),
            .pop(dq_rly_pop), .empty(dq_rly_empty), .dout(dq_rly_head), .ovf(dq_rly_ovf), .count(dc1));

        // ================= receive-side dispatch, relay, delivery arbitration =======================
        integer drot;                        // delivery round-robin start
        integer grot;                        // relay round-robin start
        reg [DEL-1:0] dv;
        reg [PWT-1:0] dfl [0:DEL-1];
        always @* begin : dispatch
            integer n, s, src, gsel;
            rb_pop = '0; dq_own_pop = 1'b0; dq_rly_pop = 1'b0; dq_rly_push = 1'b0; dq_rly_din = '0;
            ql_push = '0; ql_din = '0;
            dv = '0;
            for (integer i = 0; i < DEL; i = i + 1) dfl[i] = '0;
            // partials: always accepted into their operand slot
            for (integer p = 0; p < NP; p = p + 1)
                if (!rb_empty[p] && !rb_head[p][PWT-1]) rb_pop[p] = 1'b1;
            // relay: one global-port result a cycle -> own delivery queue + every local port
            gsel = -1;
            if (!ONESHOT) for (integer q = 0; q < NP - NL; q = q + 1) begin
                s = NL + (grot + q) % (NP - NL);
                if (gsel < 0 && !rb_empty[s] && rb_head[s][PWT-1]) gsel = s;
            end
            if (gsel >= 0) begin
                rb_pop[gsel] = 1'b1;
                dq_rly_push = 1'b1; dq_rly_din = rb_head[gsel];
                for (integer p = 0; p < NL; p = p + 1) ql_push[p] = 1'b1;
                ql_din = rb_head[gsel];
            end
            // delivery: up to DEL a cycle over {own, relayed, local ports}
            n = 0;
            for (integer i = 0; i < NL + 2; i = i + 1) begin
                src = (drot + i) % (NL + 2);
                if (n < DEL) begin
                    if (src == NL) begin
                        if (!dq_own_empty) begin dq_own_pop = 1'b1; dv[n] = 1'b1; dfl[n] = dq_own_head; n = n + 1; end
                    end else if (src == NL + 1) begin
                        if (!dq_rly_empty) begin dq_rly_pop = 1'b1; dv[n] = 1'b1; dfl[n] = dq_rly_head; n = n + 1; end
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

        // ================= state updates: injection dispatch, operand writes, reducer pointer ======
        always @* begin
            qp_push = '0;
            for (integer p = 0; p < NP; p = p + 1) qp_din[p] = '0;
            for (integer i = 0; i < INJ; i = i + 1)
                if (h_v[i]) begin : inj
                    integer f, s, own, lane;
                    f = integer'(h_d[(16+FW)*i + FW +: 16]);
                    if (ONESHOT) begin
                        for (integer c = 0; c < NC; c = c + 1)
                            if (c != J) begin
                                lane = (OG * NC + c) % GS;
                                qp_push[lport(lane)] = 1'b1;
                                qp_din[lport(lane)] = {1'b0, 8'(J), 16'(f), h_d[(16+FW)*i +: FW]};
                            end
                    end else begin
                        s = f / OF;
                        if (s != J) begin
                            lane = (OG * NC + s) % GS;
                            qp_push[lport(lane)] = 1'b1;
                            qp_din[lport(lane)] = {1'b0, 8'(J), 16'(f % OF), h_d[(16+FW)*i +: FW]};
                        end
                    end
                end
            qr_push = '0; qr_din = res_flit;
            if (r_v && !ONESHOT) qr_push = '1;
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (integer c = 0; c < NC; c = c + 1) pres[c] <= '0;
                rptr <= 0; dupe <= 1'b0; drot <= 0; grot <= 0;
            end else begin
                drot <= (drot + 1) % (NL + 2);
                grot <= (NP > NL) ? (grot + 1) % (NP - NL) : 0;
                // own partials
                for (integer i = 0; i < INJ; i = i + 1)
                    if (h_v[i]) begin : own
                        integer f, fl;
                        f = integer'(h_d[(16+FW)*i + FW +: 16]);
                        if (ONESHOT || f / OF == J) begin
                            fl = ONESHOT ? f : f % OF;
                            if (pres[J][fl]) dupe <= 1'b1;
                            pres[J][fl] <= 1'b1;
                            opd[J][fl] <= h_d[(16+FW)*i +: FW];
                        end
                    end
                // peer partials
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
            anyovf = dq_own_ovf | dq_rly_ovf;
            for (integer p = 0; p < NP; p = p + 1) anyovf = anyovf | qp_ovf[p] | qr_ovf[p] | ql_ovf[p] | rb_ovf[p];
        end
        assign fault = anyovf | dupe;
    end endgenerate
endmodule
