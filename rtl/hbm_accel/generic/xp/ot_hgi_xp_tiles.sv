`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SM.MATVEC x plane as HARDENED LEAVES (owner 10-13 redesign, step 7; budget + cuts in el1013-hbm-redesign-smmv.log).
// The measured join ot_hgi_xp_load (cursor + ot_hgi_xp_rd + ot_hgi_xp_pack, ~100 k flops on two clock roots) cut into
// leaves of <= 15 k sinks, one root each, EVERY pin a flop (in -> flop, flop -> out, no logic at a pin):
//   ot_hgi_xp_rd_ln  x4  lane pair: VM response pin flops, 2 x 16 x 256 landing FIFO, wave register, request relay
//   ot_hgi_xp_rdc    x1  command skid, cursor, tag FIFO, lane / landing credits, wave meta, strobes, x_done line
//   ot_hdc_actquant  x2  UNCHANGED (rtl/hdc/v41/ot_hdc_actquant.sv)
//   ot_hgi_xp_bfm    x1  wave pin flops, BF16 RNE, quantiser pin flops, tag line, merge, buffer select
//   ot_hgi_xp_buf    x3  ONE master: write pin flops, unit buffer 8,192 b, beat register, own emitter, ring token
//   ot_hgi_xp_xwm    x1  beat pin flops of the 3 buffers, OR, xw pin flops
//   ot_hgi_xp_sps    xN  ONE spine stage (in -> flop -> out; the SM taps the stage output net)
//   ot_hgi_xp_load_t     wires only: the port list of ot_hgi_xp_load (drop-in for tb_hgi_smmv_tput, +define+XPT)
//   ot_hgi_xp_spine_t    wires only: PRE + NS stages of ot_hgi_xp_sps (port list of ot_hgi_xp_spine)
// Function = ot_hgi_xp_load (same wave order, units, refusals, mutants).  What the pin registers change is LATENCY only
// (rate: one wave an edge, one beat an edge, unchanged):
//   command: pin flops + a 2-place skid (x_rdy is a flop; up to two transfers land before it falls)          +1
//   request: control flop -> lane leaf flop -> VM pin                                                         +1
//   landing: the lane leaf forwards its registered strobe; the control leaf counts it one edge later (stale LOW)
//   pop:     control flop -> lane leaf pin flop -> wave register                                              +2
//   block-dot: quantiser outputs land in bfm pin flops before the merge                                      +1
//   BF16:    the wave lands in bfm pin flops before the RNE                                                   +1
//   beat:    buffer beat register -> xwm pin flops -> xw pin flops                                            +1
// EMISSION WITHOUT A SHARED EMITTER: the buffers fill and emit in ring order.  A buffer emits when it holds the ring
// token and is complete; it sends the token on 2 edges before its last beat (a unit is >= 4 beats, the hop is two
// flops), so the next buffer's first beat follows the last one with no gap = the timing of the single emitter of
// ot_hgi_xp_pack, and its NBF = 3 rate proof stands.
// ---------------------------------------------------------------------------------------------------------------------

// ============================================================================================================ rd_ln
module ot_hgi_xp_rd_ln #(parameter integer CR = 16) (
    input  wire              clk,
    input  wire              rst_n,
    // VM lane face (2 lanes)
    output reg  [2*16-1:0]   wrq,        // {v, sector 15} a lane
    input  wire [1:0]        wrq_cr,
    input  wire [2*257-1:0]  wrr,        // {v, data 256} a lane
    // control leaf face
    input  wire [2*16-1:0]   rq_i,
    output reg  [1:0]        cr_o,       // request-credit returns, relayed
    output reg  [1:0]        rsv_o,      // landing strobes (registered)
    input  wire              pop_i,
    input  wire [1:0]        lpop_i,
    output reg               fault,
    // pack face
    output reg  [2*256-1:0]  wave_d
);
    reg rs; always @(posedge clk) rs <= !rst_n;
    reg [1:0] rs_vq, lpop_q; reg pop_q; reg [255:0] rs_dq [0:1];
    reg [255:0] lf [0:31];                          // lane l entry e at 16 l + e
    reg [3:0] lf_r [0:1]; reg [3:0] lf_w [0:1]; reg [4:0] lf_n [0:1];
    // four kept copies of a lane's read pointer, one a 64-b quarter of the 256-b read mux (one copy drove 3,578 loads)
    (* keep = 1 *) reg [3:0] lf_ra [0:1]; (* keep = 1 *) reg [3:0] lf_rb [0:1]; (* keep = 1 *) reg [3:0] lf_rc [0:1]; (* keep = 1 *) reg [3:0] lf_rd [0:1];
    integer l;
    always @(posedge clk) begin
        wrq <= rq_i; cr_o <= wrq_cr; rsv_o <= rs_vq; pop_q <= pop_i; lpop_q <= lpop_i;
        rs_vq <= {wrr[513], wrr[256]}; rs_dq[0] <= wrr[255:0]; rs_dq[1] <= wrr[512:257];
        for (l = 0; l < 2; l = l + 1) begin
            if (rs_vq[l]) begin
                lf[{l[0], lf_w[l]}] <= rs_dq[l]; lf_w[l] <= lf_w[l] + 4'd1;
                if (lf_n[l] >= 5'(CR)) fault <= 1'b1;                       // landing overrun (credits broken)
            end
            lf_n[l] <= lf_n[l] + {4'd0, rs_vq[l]} - {4'd0, lpop_q[l]};
            if (lpop_q[l]) begin
                lf_r[l] <= lf_r[l] + 4'd1; lf_ra[l] <= lf_ra[l] + 4'd1; lf_rb[l] <= lf_rb[l] + 4'd1;
                lf_rc[l] <= lf_rc[l] + 4'd1; lf_rd[l] <= lf_rd[l] + 4'd1;
                if (lf_n[l] == 5'd0) fault <= 1'b1;                         // pop of an empty lane
            end
            if (pop_q) begin
                wave_d[256*l +: 64]       <= lpop_q[l] ? lf[{l[0], lf_ra[l]}][63:0]    : 64'd0;
                wave_d[256*l + 64 +: 64]  <= lpop_q[l] ? lf[{l[0], lf_rb[l]}][127:64]  : 64'd0;
                wave_d[256*l + 128 +: 64] <= lpop_q[l] ? lf[{l[0], lf_rc[l]}][191:128] : 64'd0;
                wave_d[256*l + 192 +: 64] <= lpop_q[l] ? lf[{l[0], lf_rd[l]}][255:192] : 64'd0;
            end
        end
        if (rs) begin
            wrq[15] <= 1'b0; wrq[31] <= 1'b0; cr_o <= 2'd0; rsv_o <= 2'd0; pop_q <= 1'b0; lpop_q <= 2'd0; rs_vq <= 2'd0;
            fault <= 1'b0;
            for (l = 0; l < 2; l = l + 1) begin
                lf_r[l] <= 4'd0; lf_ra[l] <= 4'd0; lf_rb[l] <= 4'd0; lf_rc[l] <= 4'd0; lf_rd[l] <= 4'd0; lf_w[l] <= 4'd0; lf_n[l] <= 5'd0;
            end
        end
    end
endmodule

// ============================================================================================================== rdc
module ot_hgi_xp_rdc #(
    parameter integer CR = 16,            // landing credits a lane
    parameter integer RQC = 10,           // lane request credits (B2 bank request queue)
    parameter integer XQ = 4,             // wave commands queued between the cursor and the reader
    parameter integer XDD = 12,           // x_done after the last beat left xwm
    parameter integer PD = 24,            // edges a wave may still be in the pack leaves (class change waits this long)
    parameter integer MUT_WDROP = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x_v,
    output reg                x_rdy,
    input  wire [17:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    input  wire [6:0]         x_xb,
    output reg                x_done,
    output reg                x_fault,
    // lane leaves
    output reg  [8*16-1:0]    rq_o,
    input  wire [7:0]         cr_i,
    input  wire [7:0]         rsv_i,
    output reg                pop_o,
    output reg  [7:0]         lpop_o,
    // pack leaves
    output reg  [1:0]         aq_v,       // block-dot wave: quantiser lo / hi strobes
    output reg                bd_v,       // a block-dot wave (also a NULL wave)
    output reg                bf_v,       // a BF16 wave
    output reg  [24:0]        wave_t,     // {tp 2, ab 7, nel 7, jw 3, hi, lo, bf, lastc, last, first}
    input  wire               xw_eop_i,
    input  wire [8:0]         fault_i
);
    localparam integer TW = 25, TD = 32, QW = 78;
    reg rst; always @(posedge clk) rst <= !rst_n;
    // ---- command pin flops, decode, 2-place skid (q = the command the cursor takes next, sk behind it)
    reg xi_v, xr_q; reg [17:0] xi_base; reg [20:0] xi_n; reg [3:0] xi_p; reg [1:0] xi_space, xi_fmt; reg [6:0] xi_xb;
    wire got = xi_v && xr_q;
    wire i_bd = xi_fmt == 2'd1 || xi_fmt == 2'd2;
    wire i_bad = xi_space != 2'd1 || (|xi_base[5:0]) || xi_p != 4'd1 || xi_n == 21'd0 || (i_bd && (|xi_n[4:0]));
    wire [7:0] i_gn = !i_bd ? 8'((xi_n + 21'd511) >> 9) : (xi_fmt == 2'd1) ? 8'(({5'd0, xi_n[20:5]} + 21'd31) >> 5)
                                                                             : 8'(({5'd0, xi_n[20:5]} + 21'd63) >> 6);
    // {bf, la 4, nbk 16, nsk 18, k 21, gn 8, bs 15, ab 7} = 90 b
    wire [89:0] dec = {!i_bd, (xi_fmt == 2'd1) ? 4'd4 : 4'd8, xi_n[20:5], 18'((xi_n + 21'd7) >> 3), xi_n, i_gn, xi_base[17:3], xi_xb};
    reg q_v, sk_v; reg [89:0] q, sk;
    wire q_bf = q[89]; wire [3:0] q_la = q[88:85]; wire [15:0] q_nbk = q[84:69]; wire [17:0] q_nsk = q[68:51];
    wire [20:0] q_k = q[50:30]; wire [7:0] q_gn = q[29:22]; wire [14:0] q_bs = q[21:7]; wire [6:0] q_ab = q[6:0];
    // ---- cursor
    reg c_act, c_bf, c_cls_v, c_cls; reg [3:0] c_la; reg [15:0] c_nbk; reg [17:0] c_nsk; reg [20:0] c_k; reg [7:0] c_gn, c_g;
    reg [14:0] c_bs; reg [6:0] c_ab; reg [1:0] c_tp; reg [3:0] c_j; reg [12:0] c_gj, c_g0;
    // ---- tag FIFO (cursor -> pop)
    reg [TW-1:0] tq [0:TD-1]; reg [4:0] tqh, tqt; reg [5:0] tqn;
    wire [TW-1:0] th = tq[tqh];
    reg [2:0] pace; reg [15:0] nwave;
    // ---- reader control (ot_hgi_xp_rd without its landing FIFOs)
    reg [29:0] cq [0:XQ-1]; reg [$clog2(XQ):0] cq_n; reg [$clog2(XQ)-1:0] cq_r, cq_w;
    reg act; reg [14:0] r_sec; reg [10:0] r_rem;
    reg [4:0] cr [0:7]; reg [5:0] qc [0:7]; reg [4:0] lf_n [0:7];
    reg [3:0] mq [0:15]; reg [4:0] mq_n; reg [3:0] mq_r, mq_w;
    reg [7:0] cr_q, rsv_q; reg eop_q, flt_q; reg rd_fault;
    wire rd_rdy = cq_n < XQ[$clog2(XQ):0];
    // block-dot step
    wire [15:0] b0 = {c_gj, 3'd0} + {13'd0, c_tp, 1'b0};
    wire d_lo = b0 < c_nbk, d_hi = (b0 + 16'd1) < c_nbk;
    wire d_lastu = (c_j == c_la - 4'd1) || ((b0 + 16'd8) >= c_nbk);
    // BF16 step
    wire [17:0] s0 = {4'd0, c_g, 6'd0} + {11'd0, c_j, 3'd0};
    wire f_val = s0 < c_nsk; wire [17:0] f_rem = c_nsk - s0; wire [20:0] f_kel = c_k - {s0, 3'd0};
    wire f_lastu = (c_j == 4'd7) || ((s0 + 18'd8) >= c_nsk);
    wire lastu = c_bf ? f_lastu : d_lastu;
    wire lastg = c_g == c_gn - 8'd1;
    wire lastc = lastu && lastg && (c_bf || c_tp == 2'd3);
    wire [3:0] nsec = c_bf ? (!f_val ? 4'd0 : (f_rem >= 18'd8) ? 4'd8 : f_rem[3:0]) : (d_hi ? 4'd8 : d_lo ? 4'd4 : 4'd0);
    wire [6:0] nel = !f_val ? 7'd0 : (f_kel >= 21'd64) ? 7'd64 : f_kel[6:0];
    wire [14:0] sec = c_bs + (c_bf ? s0[14:0] : {b0[12:0], 2'd0});
    wire step = c_act && rd_rdy && tqn < 6'(TD - 1);
    wire [TW-1:0] tag = {c_tp, c_ab, c_bf ? nel : 7'd0, c_j[2:0], !c_bf && d_hi, !c_bf && d_lo, c_bf, lastc, lastu, c_j == 4'd0};
    // wave strobe line: pv0 / t0 = the pop (ot_hgi_xp_rd's wave_v / the loader's t_r), pv1 one edge later, then the pins
    reg pv0, pv1; reg [TW-1:0] t0, t1; reg [PD-1:0] bsr;
    wire drained = tqn == 6'd0 && !pv0 && bsr == '0;
    wire c_load = q_v && !c_act && (!c_cls_v || c_cls == q_bf || drained);
    wire wave_rdy = !(th[1] && pace != 3'd0);
    // reader combinational decisions
    reg [3:0] n_now, m_n; reg last_now, can, take_cmd, pop;
    integer l;
    always @* begin
        n_now = (r_rem > 11'd8) ? 4'd8 : r_rem[3:0];
        last_now = r_rem <= 11'd8;
        can = act && (mq_n < 5'd16);
        for (l = 0; l < 8; l = l + 1) if (4'(l) < n_now && (cr[l] == 5'd0 || (RQC != 0 && qc[l] == 6'd0))) can = 1'b0;
        take_cmd = (cq_n != '0) && (!act || (can && last_now));
        m_n = mq[mq_r];
        pop = (mq_n != 5'd0) && wave_rdy;
        for (l = 0; l < 8; l = l + 1) if (4'(l) < m_n && lf_n[l] == 5'd0) pop = 1'b0;
    end
    wire put = got && !i_bad;
    reg [XDD-2:0] dd;
    always @(posedge clk) begin
        // ---------------------------------------------------------------- pin flops
        xi_v <= x_v; xr_q <= x_rdy; xi_base <= x_base; xi_n <= x_n; xi_p <= x_p; xi_space <= x_space; xi_fmt <= x_fmt; xi_xb <= x_xb;
        cr_q <= cr_i; rsv_q <= rsv_i; eop_q <= xw_eop_i; flt_q <= |fault_i;
        // ---------------------------------------------------------------- command skid
        if (got && i_bad) x_fault <= 1'b1;
        if (c_load) begin
            if (sk_v) begin q <= sk; q_v <= 1'b1; sk_v <= put; if (put) sk <= dec; end
            else begin q_v <= put; if (put) q <= dec; end
        end else if (put) begin
            if (!q_v) begin q <= dec; q_v <= 1'b1; end
            else begin sk <= dec; sk_v <= 1'b1; if (sk_v) x_fault <= 1'b1; end
        end
        // ready while the worst case fits the two places: commands held after this edge + the transfer of the cycle just
        // ended (not seen yet, possible only if x_rdy was up) + the one this ready invites <= 2.  Flops only.
        x_rdy <= ({1'b0, q_v} + {1'b0, sk_v} + {1'b0, put} - {1'b0, c_load} + {1'b0, x_rdy}) <= 2'd1;
        // ---------------------------------------------------------------- cursor
        if (c_load) begin
            c_act <= 1'b1; c_bf <= q_bf; c_cls_v <= 1'b1; c_cls <= q_bf; c_la <= q_la; c_nbk <= q_nbk; c_nsk <= q_nsk;
            c_k <= q_k; c_gn <= q_gn; c_bs <= q_bs; c_ab <= q_ab; c_g <= 8'd0; c_tp <= 2'd0; c_j <= 4'd0; c_gj <= 13'd0; c_g0 <= 13'd0;
        end
        if (step) begin
            tq[tqt] <= tag; tqt <= tqt + 5'd1;
            if (!lastu) begin c_j <= c_j + 4'd1; c_gj <= c_gj + 13'd1; end
            else begin
                c_j <= 4'd0;
                if (c_bf || c_tp == 2'd3) begin
                    c_tp <= 2'd0; c_g <= c_g + 8'd1; c_ab <= c_ab + 7'd8; c_g0 <= c_g0 + {9'd0, c_la}; c_gj <= c_g0 + {9'd0, c_la};
                    if (lastg) c_act <= 1'b0;
                end else begin c_tp <= c_tp + 2'd1; c_gj <= c_g0; end
            end
        end
        tqn <= tqn + {5'd0, step} - {5'd0, pop};
        if (pop) begin
            tqh <= tqh + 5'd1; t0 <= th;
            if (th[1]) pace <= th[3] ? 3'd7 : 3'd3;
        end
        if (pace != 3'd0 && !(pop && th[1])) pace <= pace - 3'd1;
        // ---------------------------------------------------------------- reader control
        rq_o <= {8{16'd0}};
        if (step) begin
            cq[cq_w] <= {4'd0, 7'd0, nsec, sec}; cq_w <= (cq_w == XQ - 1) ? '0 : cq_w + 1'b1;
            if (sec[2:0] != 3'd0 && nsec != 4'd0) rd_fault <= 1'b1;
        end
        cq_n <= cq_n + (step ? 1'b1 : 1'b0) - (take_cmd ? 1'b1 : 1'b0);
        if (can) begin
            for (l = 0; l < 8; l = l + 1) if (4'(l) < n_now) rq_o[16*l +: 16] <= {1'b1, r_sec + 15'(l)};
            mq[mq_w] <= n_now; mq_w <= mq_w + 4'd1;
            r_sec <= r_sec + 15'd8; r_rem <= r_rem - {7'd0, n_now};
            if (last_now) act <= 1'b0;
        end
        if (take_cmd) begin
            r_rem <= cq[cq_r][25:15]; r_sec <= cq[cq_r][14:0]; act <= 1'b1; cq_r <= (cq_r == XQ - 1) ? '0 : cq_r + 1'b1;
        end
        mq_n <= mq_n + {4'd0, can} - {4'd0, pop};
        for (l = 0; l < 8; l = l + 1) begin
            cr[l] <= cr[l] - {4'd0, can && (4'(l) < n_now)} + {4'd0, pop && (4'(l) < m_n)};
            qc[l] <= qc[l] - {5'd0, can && (4'(l) < n_now)} + {5'd0, cr_q[l]};
            lf_n[l] <= lf_n[l] + {4'd0, rsv_q[l]} - {4'd0, pop && (4'(l) < m_n)};
        end
        if (pop) mq_r <= mq_r + 4'd1;
        pop_o <= pop;
        for (l = 0; l < 8; l = l + 1) lpop_o[l] <= pop && (4'(l) < m_n);
        // ---------------------------------------------------------------- wave strobes (aligned with the lane leaves' wave)
        pv0 <= pop;
        pv1 <= pv0 && !(MUT_WDROP != 0 && nwave == 16'd10); t1 <= t0;
        if (pv0) nwave <= nwave + 16'd1;
        aq_v <= {pv1 && !t1[3] && t1[5], pv1 && !t1[3] && t1[4]}; bd_v <= pv1 && !t1[3]; bf_v <= pv1 && t1[3]; wave_t <= t1;
        bsr <= {bsr[PD-2:0], pv0};
        // ---------------------------------------------------------------- done line, faults
        x_done <= dd[XDD-2]; dd <= {dd[XDD-3:0], eop_q};
        if (rd_fault || flt_q) x_fault <= 1'b1;
        if (rst) begin
            xi_v <= 1'b0; xr_q <= 1'b0; x_rdy <= 1'b0; q_v <= 1'b0; sk_v <= 1'b0;
            c_act <= 1'b0; c_cls_v <= 1'b0; tqh <= 5'd0; tqt <= 5'd0; tqn <= 6'd0; pace <= 3'd0; nwave <= 16'd0;
            cq_n <= '0; cq_r <= '0; cq_w <= '0; act <= 1'b0; mq_n <= 5'd0; mq_r <= 4'd0; mq_w <= 4'd0; rd_fault <= 1'b0;
            pop_o <= 1'b0; lpop_o <= 8'd0; pv0 <= 1'b0; pv1 <= 1'b0; aq_v <= 2'd0; bd_v <= 1'b0; bf_v <= 1'b0; bsr <= '0;
            x_done <= 1'b0; dd <= '0; eop_q <= 1'b0; flt_q <= 1'b0; cr_q <= 8'd0; rsv_q <= 8'd0; x_fault <= 1'b0;
            for (l = 0; l < 8; l = l + 1) begin cr[l] <= 5'(CR); qc[l] <= 6'(RQC); lf_n[l] <= 5'd0; end
        end
    end
endmodule

// ============================================================================================================== bfm
module ot_hgi_xp_bfm #(parameter integer NBF = 3, parameter integer TW = 25) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [2047:0]     wave_d,
    input  wire              bd_v,
    input  wire              bf_v,
    input  wire [TW-1:0]     wave_t,
    input  wire [1:0]        aq_vo,
    input  wire [1:0]        aq_f,
    input  wire [255:0]      aq_q0, aq_q1,
    input  wire [9:0]        aq_e0, aq_e1,
    output reg  [NBF-1:0]    m_v,        // one-hot: the buffer this wave goes to
    output reg  [TW-1:0]     m_t,
    output reg  [1023:0]     m_d,
    output reg               fault
);
    localparam integer AQL = 13;
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) bf16 = x[31:16] | 16'h0040;
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; bf16 = r[31:16]; end
        end
    endfunction
    function automatic [1:0] nx(input [1:0] b); nx = (b == 2'(NBF - 1)) ? 2'd0 : b + 2'd1; endfunction
    reg rs; always @(posedge clk) rs <= !rst_n;
    // ---- pin flops
    reg [2047:0] wd_q; reg bdv_q, bfv_q; reg [TW-1:0] t_q;
    reg [1:0] qvo_q, qf_q; reg [255:0] qq0_q, qq1_q; reg [9:0] qe0_q, qe1_q;
    // ---- block-dot tag line (the quantiser's fixed latency), BF16 stage, merge
    reg [AQL-1:0] tv; reg [TW-1:0] tt [0:AQL-1];
    reg b_v; reg [TW-1:0] b_t; reg [1023:0] b_d;
    reg m_any, m_f; reg [1:0] wb;
    wire mvn = tv[AQL-1] || b_v;
    wire [1:0] wbx = (m_any && m_t[1]) ? nx(wb) : wb;      // the write pointer moves with a unit's last wave
    integer l, t, b;
    always @(posedge clk) begin
        wd_q <= wave_d; bdv_q <= bd_v; bfv_q <= bf_v; t_q <= wave_t;
        qvo_q <= aq_vo; qf_q <= aq_f; qq0_q <= aq_q0; qq1_q <= aq_q1; qe0_q <= aq_e0; qe1_q <= aq_e1;
        tv <= {tv[AQL-2:0], bdv_q};
        tt[0] <= t_q;
        for (l = 1; l < AQL; l = l + 1) tt[l] <= tt[l-1];
        b_v <= bfv_q; b_t <= t_q;
        for (l = 0; l < 8; l = l + 1) for (t = 0; t < 8; t = t + 1)
            b_d[t*128 + l*16 +: 16] <= ({1'b0, 3'(l), 3'(t)} < t_q[15:9]) ? bf16(wd_q[l*256 + t*32 +: 32]) : 16'd0;
        m_any <= mvn;
        m_t <= b_v ? b_t : tt[AQL-1];
        m_d <= b_v ? b_d : {492'd0, qe1_q, qq1_q, qe0_q, qq0_q};
        for (b = 0; b < NBF; b = b + 1) m_v[b] <= mvn && wbx == 2'(b);
        wb <= wbx;
        m_f <= (tv[AQL-1] && b_v) || (tv[AQL-1] && (qvo_q != {tt[AQL-1][5], tt[AQL-1][4]} || (|qf_q))) || (!tv[AQL-1] && (|qvo_q));
        if (m_f) fault <= 1'b1;
        if (rs) begin
            bdv_q <= 1'b0; bfv_q <= 1'b0; qvo_q <= 2'd0; qf_q <= 2'd0; tv <= '0; b_v <= 1'b0; m_any <= 1'b0; m_v <= '0; m_f <= 1'b0;
            wb <= 2'd0; fault <= 1'b0;
        end
    end
endmodule

// ============================================================================================================== buf
module ot_hgi_xp_buf #(parameter integer TW = 25, parameter integer MUT_LANE = 0) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              tok0,       // strap: this buffer holds the ring token after reset (buffer 0)
    input  wire              w_v_i,
    input  wire [TW-1:0]     w_t_i,
    input  wire [1023:0]     w_d_i,
    input  wire              tok_i,
    output reg               tok_o,
    output reg               ob_v,
    output reg               ob_eop,
    output reg  [6:0]        ob_addr,
    output reg  [6:0]        ob_grp,
    output reg  [2047:0]     ob_d,
    output reg               fault
);
    reg rs; always @(posedge clk) rs <= !rst_n;
    reg t0_q, ti_q, w_v; reg [TW-1:0] w_t; reg [1023:0] w_d;
    reg [8191:0] fl; reg [1:0] st;                  // st 0 free, 1 filling, 2 complete (waiting / emitting)
    reg [6:0] mab; reg [1:0] mtp; reg mbf, mlc, have_tok, e_act; reg [2:0] ecnt;
    // kept copies of the emit enable and the format bit, one a 1,024-b slice of the unit image (+ one for the beat
    // register): one copy each drove 15,400 loads
    (* keep = 1 *) reg [8:0] e_act_c; (* keep = 1 *) reg [8:0] mbf_c;
    integer c;
    wire [2:0] elast = mbf ? 3'd7 : 3'd3;
    wire start = !e_act && (have_tok || ti_q) && st == 2'd2;
    integer j, t;
    always @(posedge clk) begin
        t0_q <= tok0; ti_q <= tok_i; w_v <= w_v_i; w_t <= w_t_i; w_d <= w_d_i;
        // emission (block-dot 2,048 b a beat, BF16 1,024 b at bit 80)
        ob_v <= 1'b0; ob_d <= 2048'd0; tok_o <= 1'b0;
        if (e_act) begin
            ob_v <= 1'b1; ob_eop <= (ecnt == elast) && mlc;
            ob_addr <= mbf ? mab + {4'd0, ecnt} : mab + {4'd0, mtp, ecnt[1]};
            ob_grp <= mbf ? 7'd1 : {6'd0, ecnt[0]};
            ob_d <= mbf_c[8] ? {944'd0, fl[1023:0], 80'd0} : fl[2047:0];
            if (ecnt == elast - 3'd2) tok_o <= 1'b1;                       // the next buffer may follow with no gap
            if (ecnt == elast) begin st <= 2'd0; e_act <= 1'b0; e_act_c <= 9'd0; ecnt <= 3'd0; end
            else ecnt <= ecnt + 3'd1;
        end else if (start) begin e_act <= 1'b1; e_act_c <= 9'h1FF; ecnt <= 3'd0; end
        // the unit image shifts a beat out while emitting (slice i by its own copies; before the buffer write below)
        for (c = 0; c < 8; c = c + 1) if (e_act_c[c])
            fl[1024*c +: 1024] <= mbf_c[c] ? ((c < 7) ? fl[(1024*(c+1)) % 8192 +: 1024] : 1024'd0)
                                           : ((c < 6) ? fl[(1024*(c+2)) % 8192 +: 1024] : 1024'd0);
        if (ti_q) have_tok <= 1'b1;
        if (start) have_tok <= 1'b0;
        // buffer write (a unit's first wave opens the buffer cleared)
        if (w_v) begin
            if (w_t[0]) begin
                if (st != 2'd0) fault <= 1'b1;
                mab <= w_t[22:16]; mtp <= w_t[24:23]; mbf <= w_t[3]; mbf_c <= {9{w_t[3]}}; mlc <= 1'b0;
            end else if (st != 2'd1) fault <= 1'b1;
            if (w_t[2]) mlc <= 1'b1;
            st <= w_t[1] ? 2'd2 : 2'd1;
            if (w_t[3]) begin
                for (j = 0; j < 8; j = j + 1) for (t = 0; t < 8; t = t + 1)
                    if (w_t[8:6] == 3'(j)) fl[t*1024 + j*128 +: 128] <= w_d[t*128 +: 128];
                    else if (w_t[0]) fl[t*1024 + j*128 +: 128] <= 128'd0;
            end else begin
                if (w_t[0]) fl <= 8192'd0;
                for (j = 0; j < 8; j = j + 1) if ((w_t[8:6] ^ 3'(MUT_LANE != 0)) == 3'(j)) begin
                    if (w_t[4]) fl[266*j +: 266] <= w_d[265:0];
                    if (w_t[5]) fl[4096 + 266*j +: 266] <= w_d[531:266];
                end
            end
        end
        if (rs) begin
            ti_q <= 1'b0; w_v <= 1'b0; e_act <= 1'b0; ecnt <= 3'd0; st <= 2'd0; ob_v <= 1'b0; ob_eop <= 1'b0; tok_o <= 1'b0;
            have_tok <= t0_q; fault <= 1'b0; mbf <= 1'b0; mbf_c <= 9'd0; e_act_c <= 9'd0; mlc <= 1'b0;
        end
    end
endmodule

// ============================================================================================================== xwm
module ot_hgi_xp_xwm #(parameter integer MUT_BEAT = 0) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              a_v, a_eop, input wire [6:0] a_addr, a_grp, input wire [2047:0] a_d,
    input  wire              b_v, b_eop, input wire [6:0] b_addr, b_grp, input wire [2047:0] b_d,
    input  wire              c_v, c_eop, input wire [6:0] c_addr, c_grp, input wire [2047:0] c_d,
    output reg               xw_en,
    output reg  [6:0]        xw_addr,
    output reg  [6:0]        xw_grp,
    output reg  [2047:0]     xw_data,
    output reg               xw_eop      // with xw_en: the command's last beat
);
    reg rs; always @(posedge clk) rs <= !rst_n;
    reg [2:0] v_q, e_q; reg [6:0] ad_q [0:2]; reg [6:0] gr_q [0:2]; reg [2047:0] d_q [0:2];
    reg [15:0] nbeat;
    wire any = |v_q;
    always @(posedge clk) begin
        v_q <= {c_v, b_v, a_v}; e_q <= {c_eop, b_eop, a_eop};
        ad_q[0] <= a_addr; ad_q[1] <= b_addr; ad_q[2] <= c_addr; gr_q[0] <= a_grp; gr_q[1] <= b_grp; gr_q[2] <= c_grp;
        d_q[0] <= a_d; d_q[1] <= b_d; d_q[2] <= c_d;
        xw_en <= any && !(MUT_BEAT != 0 && nbeat == 16'd36);
        xw_eop <= |(v_q & e_q);
        xw_addr <= ({7{v_q[0]}} & ad_q[0]) | ({7{v_q[1]}} & ad_q[1]) | ({7{v_q[2]}} & ad_q[2]);
        xw_grp <= ({7{v_q[0]}} & gr_q[0]) | ({7{v_q[1]}} & gr_q[1]) | ({7{v_q[2]}} & gr_q[2]);
        xw_data <= d_q[0] | d_q[1] | d_q[2];            // a buffer that does not emit holds its beat register at 0
        if (any) nbeat <= nbeat + 16'd1;
        if (rs) begin v_q <= 3'd0; xw_en <= 1'b0; xw_eop <= 1'b0; nbeat <= 16'd0; end
    end
endmodule

// ============================================================================================================== sps
// ONE spine stage: in -> flop -> out.  The stage output net feeds the next stage's pin flop and the SM's x-write pin
// flops (<= 500 um a hop by placement).
module ot_hgi_xp_sps (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              i_en,
    input  wire [6:0]        i_addr,
    input  wire [6:0]        i_grp,
    input  wire [2047:0]     i_data,
    output reg               o_en,
    output reg  [6:0]        o_addr,
    output reg  [6:0]        o_grp,
    output reg  [2047:0]     o_data
);
    reg rs; always @(posedge clk) rs <= !rst_n;
    always @(posedge clk) begin o_en <= i_en && !rs; o_addr <= i_addr; o_grp <= i_grp; o_data <= i_data; end
endmodule

// ========================================================================================================== spine_t
module ot_hgi_xp_spine_t #(parameter integer NS = 8, parameter integer PRE = 0) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 i_en,
    input  wire [6:0]           i_addr,
    input  wire [6:0]           i_grp,
    input  wire [2047:0]        i_data,
    output wire [NS-1:0]        o_en,
    output wire [NS*7-1:0]      o_addr,
    output wire [NS*7-1:0]      o_grp,
    output wire [NS*2048-1:0]   o_data
);
    localparam integer NT = PRE + NS;
    wire [NT:0] en; wire [7*(NT+1)-1:0] ad, gr; wire [2048*(NT+1)-1:0] da;
    assign en[0] = i_en; assign ad[6:0] = i_addr; assign gr[6:0] = i_grp; assign da[2047:0] = i_data;
    genvar s;
    generate for (s = 0; s < NT; s = s + 1) begin : g_s
        ot_hgi_xp_sps u_s (.clk(clk), .rst_n(!rst), .i_en(en[s]), .i_addr(ad[7*s +: 7]), .i_grp(gr[7*s +: 7]),
            .i_data(da[2048*s +: 2048]), .o_en(en[s+1]), .o_addr(ad[7*(s+1) +: 7]), .o_grp(gr[7*(s+1) +: 7]),
            .o_data(da[2048*(s+1) +: 2048]));
    end endgenerate
    generate for (s = 0; s < NS; s = s + 1) begin : g_o
        assign o_en[s] = en[PRE + s + 1]; assign o_addr[s*7 +: 7] = ad[7*(PRE + s + 1) +: 7];
        assign o_grp[s*7 +: 7] = gr[7*(PRE + s + 1) +: 7]; assign o_data[s*2048 +: 2048] = da[2048*(PRE + s + 1) +: 2048];
    end endgenerate
endmodule

// =========================================================================================================== load_t
// Wires only: ot_hgi_xp_load's port list over the leaves.
module ot_hgi_xp_load_t #(
    parameter integer NXC = 4,
    parameter integer CR = 16,
    parameter integer RQC = 10,
    parameter integer XDD = 12,
    parameter integer MUT_WDROP = 0,
    parameter integer MUT_BEAT = 0,
    parameter integer MUT_LANE = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x_v,
    output wire               x_rdy,
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    input  wire [6:0]         x_xb,
    output wire               x_done,
    output wire               x_fault,
    output wire               xw_en,
    output wire [6:0]         xw_addr,
    output wire [6:0]         xw_grp,
    output wire [2047:0]      xw_data,
    output wire [NXC*338-1:0] vmq,
    input  wire [NXC*274-1:0] vmr,
    output wire               rg_req,
    input  wire               rg_gnt,
    output wire [32*16-1:0]   wrq,
    input  wire [31:0]        wrq_cr,
    input  wire [32*257-1:0]  wrr
);
    localparam integer TW = 25;
    assign vmq = '0; assign rg_req = 1'b0; assign wrq[32*16-1:8*16] = '0;
    wire [8*16-1:0] rq; wire [7:0] crr, rsv, lpop; wire pop; wire [3:0] ln_f;
    wire [2047:0] wave_d; wire [1:0] aq_v; wire bd_v, bf_v; wire [TW-1:0] wave_t;
    wire [1:0] aq_vo, aq_f; wire [255:0] aq_q [0:1]; wire signed [9:0] aq_e [0:1];
    wire [2:0] m_v; wire [TW-1:0] m_t; wire [1023:0] m_d; wire bfm_f;
    wire [2:0] tok, ob_v, ob_eop, buf_f; wire [6:0] ob_addr [0:2]; wire [6:0] ob_grp [0:2]; wire [2047:0] ob_d [0:2];
    wire xw_eop;
    ot_hgi_xp_rdc #(.CR(CR), .RQC(RQC), .XQ(4), .XDD(XDD), .MUT_WDROP(MUT_WDROP)) u_rdc (
        .clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base[17:0]), .x_n(x_n), .x_p(x_p), .x_space(x_space),
        .x_fmt(x_fmt), .x_xb(x_xb), .x_done(x_done), .x_fault(x_fault), .rq_o(rq), .cr_i(crr), .rsv_i(rsv), .pop_o(pop),
        .lpop_o(lpop), .aq_v(aq_v), .bd_v(bd_v), .bf_v(bf_v), .wave_t(wave_t), .xw_eop_i(xw_eop),
        .fault_i({1'b0, buf_f, bfm_f, ln_f}));
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_ln
        ot_hgi_xp_rd_ln #(.CR(CR)) u_ln (.clk(clk), .rst_n(rst_n), .wrq(wrq[32*g +: 32]), .wrq_cr(wrq_cr[2*g +: 2]),
            .wrr(wrr[514*g +: 514]), .rq_i(rq[32*g +: 32]), .cr_o(crr[2*g +: 2]), .rsv_o(rsv[2*g +: 2]), .pop_i(pop),
            .lpop_i(lpop[2*g +: 2]), .fault(ln_f[g]), .wave_d(wave_d[512*g +: 512]));
    end endgenerate
    generate for (g = 0; g < 2; g = g + 1) begin : g_aq
        ot_hdc_actquant u_aq (.clk(clk), .rst_n(rst_n), .v(aq_v[g]), .fp4(1'b0), .x(wave_d[1024*g +: 1024]), .vo(aq_vo[g]),
            .q(aq_q[g]), .e(aq_e[g]), .y(), .fault(aq_f[g]));
    end endgenerate
    ot_hgi_xp_bfm #(.NBF(3), .TW(TW)) u_bfm (.clk(clk), .rst_n(rst_n), .wave_d(wave_d), .bd_v(bd_v), .bf_v(bf_v),
        .wave_t(wave_t), .aq_vo(aq_vo), .aq_f(aq_f), .aq_q0(aq_q[0]), .aq_q1(aq_q[1]), .aq_e0(aq_e[0]), .aq_e1(aq_e[1]),
        .m_v(m_v), .m_t(m_t), .m_d(m_d), .fault(bfm_f));
    generate for (g = 0; g < 3; g = g + 1) begin : g_bf
        ot_hgi_xp_buf #(.TW(TW), .MUT_LANE(MUT_LANE)) u_buf (.clk(clk), .rst_n(rst_n), .tok0(g == 0 ? 1'b1 : 1'b0),
            .w_v_i(m_v[g]), .w_t_i(m_t), .w_d_i(m_d), .tok_i(tok[(g + 2) % 3]), .tok_o(tok[g]), .ob_v(ob_v[g]),
            .ob_eop(ob_eop[g]), .ob_addr(ob_addr[g]), .ob_grp(ob_grp[g]), .ob_d(ob_d[g]), .fault(buf_f[g]));
    end endgenerate
    ot_hgi_xp_xwm #(.MUT_BEAT(MUT_BEAT)) u_xwm (.clk(clk), .rst_n(rst_n),
        .a_v(ob_v[0]), .a_eop(ob_eop[0]), .a_addr(ob_addr[0]), .a_grp(ob_grp[0]), .a_d(ob_d[0]),
        .b_v(ob_v[1]), .b_eop(ob_eop[1]), .b_addr(ob_addr[1]), .b_grp(ob_grp[1]), .b_d(ob_d[1]),
        .c_v(ob_v[2]), .c_eop(ob_eop[2]), .c_addr(ob_addr[2]), .c_grp(ob_grp[2]), .c_d(ob_d[2]),
        .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .xw_eop(xw_eop));
endmodule
`default_nettype wire
