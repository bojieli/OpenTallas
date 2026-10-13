`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.INDEX wide adapter, TILED form (ot_hgi_idx_index_wt): WR leaf.
// Four output sector packers (O, R, D ids, D values), the lane arbiter (fixed priority O, R, D ids, D values; one
// sector a lane a cycle; per-lane credits), the wwq launch and the write credit / done bookkeeping.  SPEC "Tiled redesign".
//   S3  T2 / D1 beats land in pin flops and a QT-deep queue a stream (one S3 credit a queue slot, returned at accept).
//   P0  accept (control only): the head beat of a queue is accepted when each packer it feeds has an emitted-sector slot
//       free (3 slots a packer, reserved at accept); P0 owns the running word address and the word mask, and registers
//       one word-level control set a 32-bit word (take / source word / emit / slot), so
//   P1  the datapath (queue head -> word placement -> partial sector b0 / emitted-sector slot) has no wide enable.
//   A0  lane arbitration over the four packers' head sectors (control only; registered grant selects, one a slice),
//   A1  the granted sector loads the lane's wwq register (free-running data, valid bit only).
// flush (QCORE, after the last beats): accepted once both queues are empty; done when every sector has left and every
// write done has returned.  Data words outside the sector mask are not specified (the reference leaves stale words).
module ot_hgi_idxw_wr #(
    parameter integer LQ = 8,       // VM lane queue credits a write lane
    parameter integer QT = 6        // S3 queue depth a stream (= BEAT's credits)
) (
    input  wire              clk,
    input  wire              rst_n,
    // P1: VM wide write group
    output wire [8*280-1:0]  wwq_o,
    input  wire [7:0]        wwq_cr_i,
    input  wire [7:0]        wwq_done_i,
    output reg               wg_req_o,
    input  wire              wg_gnt_i,
    // S3 (BEAT)
    input  wire              t2_v_i,
    input  wire [3:0]        t2_n_i,
    input  wire [255:0]      t2_o_i, t2_r_i,
    output reg               t2_cr_o,
    input  wire              d1_v_i,
    input  wire [3:0]        d1_n_i,
    input  wire [63:0]       d1_i_i, d1_x_i,
    output reg               d1_cr_o,
    // S4 (QCORE)
    input  wire              wstart_i, flush_i, wabort_i,
    input  wire              has_r_i,
    input  wire [17:0]       o_base_i, r_base_i, d_base_i, dv_base_i,
    output reg               w_done_o
);
    localparam integer CB = $clog2(LQ) + 1;
    integer i, l, x;
    genvar gc, ge, gk, gj, gs, gl, gr;
    // ---- reset
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    wire [2:0] rnc;
    generate for (gr = 0; gr < 3; gr = gr + 1) begin : g_rn
        reg r;
        (* keep = "true" *) always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rn;
        assign rnc[gr] = r;
    end endgenerate
    // ---- pin flops
    reg t_v, d_v, wstart_q, flush_q, wabort_q, wgnt_q, has_r; reg [7:0] wcr_q, wdn_q;
    reg [3:0] t_n, d_n; reg [511:0] t_d; reg [127:0] d_d; reg [71:0] base_q;
    always @(posedge clk or negedge rnc[0])
        if (!rnc[0]) begin t_v <= 1'b0; d_v <= 1'b0; wstart_q <= 1'b0; flush_q <= 1'b0; wabort_q <= 1'b0; wgnt_q <= 1'b0;
            wcr_q <= 8'd0; wdn_q <= 8'd0; end
        else begin t_v <= t2_v_i; d_v <= d1_v_i; wstart_q <= wstart_i; flush_q <= flush_i; wabort_q <= wabort_i;
            wgnt_q <= wg_gnt_i; wcr_q <= wwq_cr_i; wdn_q <= wwq_done_i; end
    always @(posedge clk) begin
        t_n <= t2_n_i; t_d <= {t2_r_i, t2_o_i}; d_n <= d1_n_i; d_d <= {d1_x_i, d1_i_i}; has_r <= has_r_i;
        base_q <= {dv_base_i, d_base_i, r_base_i, o_base_i};
    end
    function automatic [2:0] inc6(input [2:0] v); inc6 = (v == 3'(QT - 1)) ? 3'd0 : v + 3'd1; endfunction
    // ---- S3 queues: slice c has its own valid / start pin flops, write pointer and (P1) read pointer
    reg [3:0] tqn, dqn; reg [2:0] thp, dhp, twp, dwp; reg p1_t, p1_d;
    reg [3:0] tq_n [0:QT-1]; reg [3:0] dq_n [0:QT-1];
    wire [511:0] tq_rd; wire [127:0] dq_rd;        // the queue entry accepted in P0, read in P1
    generate for (gc = 0; gc < 8; gc = gc + 1) begin : g_tq
        reg v, s; reg [2:0] wpc, rpc; reg [63:0] rv; integer e;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) v <= 1'b0; else v <= t2_v_i;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) s <= 1'b0; else s <= wstart_i;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) wpc <= 3'd0; else if (v) wpc <= inc6(wpc);
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) rpc <= 3'd0; else if (p1_t) rpc <= inc6(rpc);
        wire [QT*64-1:0] ef;
        for (ge = 0; ge < QT; ge = ge + 1) begin : g_e
            reg [63:0] m;
            always @(posedge clk) if (v && wpc == 3'(ge)) m <= t_d[gc*64 +: 64];
            assign ef[ge*64 +: 64] = m;
        end
        always @* begin rv = 64'd0; for (e = 0; e < QT; e = e + 1) if (rpc == 3'(e)) rv = rv | ef[e*64 +: 64]; end
        assign tq_rd[gc*64 +: 64] = rv;
    end endgenerate
    generate for (gc = 0; gc < 2; gc = gc + 1) begin : g_dq
        reg v, s; reg [2:0] wpc, rpc; reg [63:0] rv; integer e;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) v <= 1'b0; else v <= d1_v_i;
        (* keep = "true" *) always @(posedge clk or negedge rnc[0]) if (!rnc[0]) s <= 1'b0; else s <= wstart_i;
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) wpc <= 3'd0; else if (v) wpc <= inc6(wpc);
        (* keep = "true" *) always @(posedge clk) if (!rnc[1] || s) rpc <= 3'd0; else if (p1_d) rpc <= inc6(rpc);
        wire [QT*64-1:0] ef;
        for (ge = 0; ge < QT; ge = ge + 1) begin : g_e
            reg [63:0] m;
            always @(posedge clk) if (v && wpc == 3'(ge)) m <= d_d[gc*64 +: 64];
            assign ef[ge*64 +: 64] = m;
        end
        always @* begin rv = 64'd0; for (e = 0; e < QT; e = e + 1) if (rpc == 3'(e)) rv = rv | ef[e*64 +: 64]; end
        assign dq_rd[gc*64 +: 64] = rv;
    end endgenerate
    always @(posedge clk) begin
        if (t_v) tq_n[twp] <= t_n;
        if (d_v) dq_n[dwp] <= d_n;
    end
    // ---- P0: accept and word-level controls
    reg [17:0] pa [0:3]; reg [7:0] pm0 [0:3]; reg [1:0] er [0:3], en [0:3], ewp [0:3], ehp [0:3];
    reg fl_pend, fl_wait;
    wire t_acc = tqn != 4'd0 && er[0] != 2'd3 && (!has_r || er[1] != 2'd3);
    wire d_acc = dqn != 4'd0 && er[2] != 2'd3 && er[3] != 2'd3;
    wire fl_go = fl_pend && tqn == 4'd0 && dqn == 4'd0 && !t_v && !d_v && !p1_t && !p1_d &&
                 er[0] != 2'd3 && er[1] != 2'd3 && er[2] != 2'd3 && er[3] != 2'd3;
    wire [3:0] tn_h = tq_n[thp], dn_h = dq_n[dhp];
    reg [3:0] pv; reg [3:0] pn [0:3]; reg [3:0] p_emit; reg [4:0] p_tot [0:3]; reg [15:0] p_mf [0:3];
    reg [7:0] p_em [0:3], p_m0 [0:3]; reg [15:0] p_tk [0:3];
    always @* begin
        pv = {d_acc, d_acc, t_acc && has_r, t_acc};
        pn[0] = tn_h; pn[1] = tn_h; pn[2] = dn_h; pn[3] = dn_h;
        for (i = 0; i < 4; i = i + 1) begin
            p_tot[i] = {2'd0, pa[i][2:0]} + {1'b0, pn[i]};
            p_tk[i] = 16'd0;
            for (x = 0; x < 16; x = x + 1)
                if (pv[i] && x >= {29'd0, pa[i][2:0]} && x < {27'd0, p_tot[i]}) p_tk[i][x] = 1'b1;
            p_mf[i] = {8'd0, pm0[i]} | p_tk[i];
            p_emit[i] = pv[i] ? p_tot[i] >= 5'd8 : (fl_go && pm0[i] != 8'd0);
            p_em[i] = p_mf[i][7:0];
            p_m0[i] = pv[i] ? (p_emit[i] ? p_mf[i][15:8] : p_mf[i][7:0]) : (fl_go ? 8'd0 : pm0[i]);
        end
    end
    // ---- P1 datapath: packer k, word j
    wire [4*256-1:0] in_w = {192'd0, dq_rd[127:64], 192'd0, dq_rd[63:0], tq_rd};
    wire [12*256-1:0] eqf;                  // emitted-sector slots, packer k slot s at (3k + s) * 256
    reg [3:0] p1_emit; reg [14:0] p1_sec [0:3]; reg [7:0] p1_m [0:3]; reg [1:0] p1_slot [0:3];
    reg [14:0] esec [0:11]; reg [7:0] emk [0:11];
    generate for (gk = 0; gk < 4; gk = gk + 1) begin : g_pk
        for (gj = 0; gj < 8; gj = gj + 1) begin : g_w
            reg act, em, tkl, tkh; reg [2:0] es, swl, swh; reg [31:0] b0, il, ih; integer e;
            (* keep = "true" *) always @(posedge clk) begin
                act <= pv[gk] || fl_go; em <= p_emit[gk];
                for (e = 0; e < 3; e = e + 1) es[e] <= p_emit[gk] && ewp[gk] == 2'(e);
                tkl <= p_tk[gk][gj]; tkh <= p_tk[gk][gj + 8];
                swl <= 3'(gj) - pa[gk][2:0]; swh <= 3'(gj) - pa[gk][2:0];
            end
            always @* begin
                il = 32'd0; ih = 32'd0;
                for (e = 0; e < 8; e = e + 1) begin
                    if (swl == 3'(e)) il = il | in_w[gk*256 + e*32 +: 32];
                    if (swh == 3'(e)) ih = ih | in_w[gk*256 + e*32 +: 32];
                end
            end
            wire [31:0] bl = tkl ? il : b0, bh = tkh ? ih : 32'd0;
            always @(posedge clk) if (act) b0 <= em ? bh : bl;
            for (gs = 0; gs < 3; gs = gs + 1) begin : g_s
                reg [31:0] q;
                always @(posedge clk) if (es[gs]) q <= bl;
                assign eqf[(gk*3 + gs)*256 + gj*32 +: 32] = q;
            end
        end
    end endgenerate
    // ---- A0: lane arbitration (the reference's fixed-priority loop over the packers' head sectors)
    reg [CB-1:0] wcred [0:7]; reg [11:0] w_out; reg [5:0] wdn_cnt;
    reg [7:0] w_used; reg [3:0] e_take; reg [2:0] e_ln; reg [3:0] w_sel [0:7]; reg [14:0] hsec;
    always @* begin
        w_used = 8'd0; e_take = 4'd0;
        for (l = 0; l < 8; l = l + 1) w_sel[l] = 4'd0;
        for (i = 0; i < 4; i = i + 1) begin
            hsec = esec[i*3 + {30'd0, ehp[i]}];
            e_ln = hsec[2:0];
            if (en[i] != 2'd0 && wgnt_q && wg_req_o && !w_used[e_ln] && wcred[e_ln] != '0) begin
                e_take[i] = 1'b1; w_used[e_ln] = 1'b1; w_sel[e_ln] = 4'(i*3) + {2'd0, ehp[i]};
            end
        end
        wdn_cnt = 6'd0;
        for (l = 0; l < 8; l = l + 1) wdn_cnt = wdn_cnt + {5'd0, wdn_q[l]};
    end
    // ---- A1: lane output registers (grant select as registered copies, one a slice)
    reg [7:0] a1_v, a2_v; reg dead;
    generate for (gl = 0; gl < 8; gl = gl + 1) begin : g_ln
        for (gc = 0; gc < 5; gc = gc + 1) begin : g_c
            reg [3:0] s; integer e;
            (* keep = "true" *) always @(posedge clk) s <= w_sel[gl];
            if (gc < 4) begin : g_d
                reg [63:0] v, d;
                always @* begin v = 64'd0; for (e = 0; e < 12; e = e + 1) if (s == 4'(e)) v = v | eqf[e*256 + gc*64 +: 64]; end
                always @(posedge clk) d <= v;
                assign wwq_o[gl*280 + 8 + gc*64 +: 64] = d;
            end else begin : g_m
                reg [22:0] v, d;
                always @* begin v = 23'd0; for (e = 0; e < 12; e = e + 1) if (s == 4'(e)) v = v | {esec[e], emk[e]}; end
                always @(posedge clk) d <= v;
                assign wwq_o[gl*280 + 264 +: 15] = d[22:8]; assign wwq_o[gl*280 +: 8] = d[7:0];
            end
        end
        assign wwq_o[gl*280 + 279] = a2_v[gl];
    end endgenerate
    always @(posedge clk) for (i = 0; i < 4; i = i + 1) begin
        p1_sec[i] <= pa[i][17:3]; p1_m[i] <= p_em[i]; p1_slot[i] <= ewp[i];
        if (p1_emit[i]) begin esec[i*3 + {30'd0, p1_slot[i]}] <= p1_sec[i]; emk[i*3 + {30'd0, p1_slot[i]}] <= p1_m[i]; end
    end
    wire all_out = er[0] == 2'd0 && er[1] == 2'd0 && er[2] == 2'd0 && er[3] == 2'd0 && a1_v == 8'd0 && a2_v == 8'd0 && w_out == 12'd0;
    always @(posedge clk) begin
        if (!rnc[2]) begin
            tqn <= 4'd0; dqn <= 4'd0; thp <= 3'd0; dhp <= 3'd0; twp <= 3'd0; dwp <= 3'd0; p1_t <= 1'b0; p1_d <= 1'b0;
            fl_pend <= 1'b0; fl_wait <= 1'b0; p1_emit <= 4'd0; a1_v <= 8'd0; a2_v <= 8'd0; dead <= 1'b0; w_out <= 12'd0; wg_req_o <= 1'b0;
            t2_cr_o <= 1'b0; d1_cr_o <= 1'b0; w_done_o <= 1'b0;
            for (i = 0; i < 4; i = i + 1) begin pm0[i] <= 8'd0; er[i] <= 2'd0; en[i] <= 2'd0; ewp[i] <= 2'd0; ehp[i] <= 2'd0; end
            for (l = 0; l < 8; l = l + 1) wcred[l] <= CB'(LQ);
        end else begin
            w_done_o <= 1'b0;
            tqn <= tqn + {3'd0, t_v} - {3'd0, t_acc}; dqn <= dqn + {3'd0, d_v} - {3'd0, d_acc};
            if (t_v) twp <= inc6(twp);
            if (d_v) dwp <= inc6(dwp);
            if (t_acc) thp <= inc6(thp);
            if (d_acc) dhp <= inc6(dhp);
            p1_t <= t_acc; p1_d <= d_acc; t2_cr_o <= t_acc; d1_cr_o <= d_acc;
            p1_emit <= p_emit; a1_v <= w_used; a2_v <= a1_v;
            for (i = 0; i < 4; i = i + 1) begin
                if (pv[i]) pa[i] <= pa[i] + {14'd0, pn[i]};
                pm0[i] <= p_m0[i];
                er[i] <= er[i] + 2'(p_emit[i]) - 2'(e_take[i]);
                en[i] <= en[i] + 2'(p1_emit[i]) - 2'(e_take[i]);
                if (p_emit[i]) ewp[i] <= (ewp[i] == 2'd2) ? 2'd0 : ewp[i] + 2'd1;
                if (e_take[i]) ehp[i] <= (ehp[i] == 2'd2) ? 2'd0 : ehp[i] + 2'd1;
            end
            for (l = 0; l < 8; l = l + 1) wcred[l] <= wcred[l] + CB'(wcr_q[l]) - CB'(w_used[l]);
            w_out <= w_out + 12'(e_take[0]) + 12'(e_take[1]) + 12'(e_take[2]) + 12'(e_take[3]) - 12'(wdn_cnt);
            if ((t_v || d_v || flush_q) && !dead) wg_req_o <= 1'b1;
            if (flush_q) fl_pend <= 1'b1;
            if (fl_go) begin fl_pend <= 1'b0; fl_wait <= 1'b1; end
            if (fl_wait && all_out && p1_emit == 4'd0) begin fl_wait <= 1'b0; w_done_o <= 1'b1; wg_req_o <= 1'b0; end
            if (wabort_q) begin wg_req_o <= 1'b0; fl_pend <= 1'b0; fl_wait <= 1'b0; dead <= 1'b1; end
            if (wstart_q) begin
                tqn <= 4'd0; dqn <= 4'd0; thp <= 3'd0; dhp <= 3'd0; twp <= 3'd0; dwp <= 3'd0; p1_t <= 1'b0; p1_d <= 1'b0;
                fl_pend <= 1'b0; fl_wait <= 1'b0; p1_emit <= 4'd0; dead <= 1'b0;
                for (i = 0; i < 4; i = i + 1) begin
                    pa[i] <= base_q[i*18 +: 18]; pm0[i] <= 8'd0; er[i] <= 2'd0; en[i] <= 2'd0; ewp[i] <= 2'd0; ehp[i] <= 2'd0;
                end
            end
        end
    end
endmodule
`default_nettype wire
