`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// q13-kvleaves 2026-10-13 (coordinator: KV-end parent qkd_d2d_pf_ref-q13 NEEDS_RTL, 11,497 parent registers on one root,
// boundary clock reference 2,072 ps TT = a diverged spine).  Structural fix: ALL of ot_qkvd_d2d's own logic at the KV
// end (HT=1, IRL=1, ORL=1, PQ=2, PF=1) is hardened into small pin-registered tiles with their own clock roots, so the
// kv_end cluster (ot_qkvd_ke_cluster, ot_qkvd_kv_end SPL=1) holds no register: it wires hard children and distributes
// the clock to their clock pins.  Register for register this is the ot_qkvd_d2d datapath / control (same cycle
// behaviour), except that three face signals cross one more tile seam and therefore one more register:
//   r_cr  -> credit counters   +1 cycle        tx_up -> link slot   +1 cycle        fault / fault_cause  +1 cycle
// (credit flow is latency-insensitive; tb_qkvd_ke_eq checks every output cycle-exact against ot_qkvd_kv_end SPL=0 fed
// r_cr / tx_up one cycle late.)
//
//   ot_qkvd_ke_ti   x3  die TX face lane: t_v/t_d pin flops (ci), IRL relay (ci2), push pin flop, t_cr face flop
//   ot_qkvd_ke_rq   x1  FDI RX capture: rx_v/rx_flit pin flops (rq), the four per-buffer word relays (rw) and push flops
//   ot_qkvd_ke_tm   x1  link TX head mux (grant-selected) -> tf0 relay, next to the TX buffers
//   ot_qkvd_ke_tf   x1  link TX face: tx_up pin flop, tx_flit / tx_v face flops
//   ot_qkvd_ke_ro   x4  die RX face lane: head capture rd0 (enable = the pop in effect), r_d / r_v face flops, r_cr pin flop
//   ot_qkvd_ke_ctl  x1  credits, round-robin grant, buffer shadows, sequence / fault logic; every pin registered
//   ot_qkvd_ke_wf   x1  W face: reset synchroniser for the cluster and the fault face flops
// Fixed width W 528 / FW 548, NT 3 (classes 4-6), NR 4 (classes 0-3): hard tiles carry no parameters.  The three
// configuration values that ot_qkvd_kv_end takes as parameters (UCX, QD, FCR_RES) reach ot_qkvd_ke_ctl as strap pins.
// Mutants (bench only): KVD_KE_MUT_TI / _RQ / _TM / _TF / _RO / _CTL / _WF, one per tile.
// ---------------------------------------------------------------------------------------------------------------------

// die TX face lane (class i): ci_d / ci2_d are ot_qkvd_d2d's ci_d / g_irl.ci2_d, pf its g_pf push pin flop, t_cr its t_cr
module ot_qkvd_ke_ti (
    input  wire         clk,
    input  wire         rst_n,           // cluster reset copy (synchronous release)
    input  wire         t_v,             // S face
    input  wire [527:0] t_d,
    output reg          t_cr,
    input  wire         tcr_i,           // from ctl: gq2 (the pop in effect) = next cycle's t_cr
    output wire         civ,             // to ctl: ci_v (ctl's pin flop is ci2_v = ce_v)
    output wire         psh,             // to the TX buffer: push, same cycle as ce_d
    output wire [527:0] ce_d             // to the TX buffer: din
);
    reg         ci_v;
    reg [527:0] ci_d, ci2_d;
    always @(posedge clk) begin
        ci_d  <= t_d;
`ifdef KVD_KE_MUT_TI
        ci2_d <= t_d;                    // mutant: the relay stage is skipped (word one cycle early against its push)
`else
        ci2_d <= ci_d;
`endif
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin ci_v <= 1'b0; t_cr <= 1'b0; end
        else begin ci_v <= t_v; t_cr <= tcr_i; end
    ot_qkvd_pop_ff u_cv (.clk(clk), .rst_n(rst_n), .d(t_v),  .q(civ));     // own copy for the seam to ctl
    ot_qkvd_pop_ff u_pf (.clk(clk), .rst_n(rst_n), .d(ci_v), .q(psh));     // push pin flop
    assign ce_d = ci2_d;
endmodule

// FDI RX capture: rq_v / rq_f are ot_qkvd_d2d's rq_v / rq_f, w<j> its g_irl.g_rw[j].rw, psh[j] its g_rx[j] g_pf push flop
module ot_qkvd_ke_rq (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         rx_v,            // N face (PHY FDI)
    input  wire [547:0] rx_flit,
    output wire         rqv,             // to ctl: rq_v and the flit header rq_f[547:528] (ctl's pin flops are rq2_v / rq2_h)
    output wire [19:0]  rqh,
    output wire [3:0]   psh,             // to RX buffer j: push, same cycle as w<j>
    output wire [527:0] w0,
    output wire [527:0] w1,
    output wire [527:0] w2,
    output wire [527:0] w3
);
    reg         rq_v;
    reg [547:0] rq_f;
    always @(posedge clk) rq_f <= rx_flit;
    always @(posedge clk or negedge rst_n) if (!rst_n) rq_v <= 1'b0; else rq_v <= rx_v;
    assign rqv = rq_v;
    assign rqh = rq_f[547:528];
    (* keep *) reg [527:0] rw0, rw1, rw2, rw3;                             // one copy per receive buffer
    always @(posedge clk) begin rw0 <= rq_f[527:0]; rw1 <= rq_f[527:0]; rw2 <= rq_f[527:0]; rw3 <= rq_f[527:0]; end
    assign w0 = rw0; assign w1 = rw1; assign w2 = rw2; assign w3 = rw3;
`ifdef KVD_KE_MUT_RQ
    wire dv = rq_v;                                                        // mutant: idle flits (dv 0) are pushed too
`else
    wire dv = rq_v && rq_f[531];
`endif
    genvar j;
    generate for (j = 0; j < 4; j = j + 1) begin : g_pf
        ot_qkvd_pop_ff u_pf (.clk(clk), .rst_n(rst_n), .d(dv && (rq_f[530:528] == j)), .q(psh[j]));
    end endgenerate
endmodule

// link TX head mux, next to the TX buffers: the mux is ot_qkvd_d2d's sel_word (select = local copies of gq2), tf0w its
// g_torl.tf0 word bits (the tf0 header bits are held by ctl)
module ot_qkvd_ke_tm (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [2:0]   gq_i,            // from ctl: gq (decided last cycle); gq2 is taken here, next to the mux
    input  wire [527:0] h0,              // TX buffer heads (registered inside the buffer tiles)
    input  wire [527:0] h1,
    input  wire [527:0] h2,
    output wire [527:0] tw               // to ot_qkvd_ke_tf: tf0 word
);
    // select copies: 4 groups of 132 bits, each with its own kept gq2 (fan-out 132 per flop)
    wire [527:0] sel_word;
    genvar c;
    generate for (c = 0; c < 4; c = c + 1) begin : g_sel
        wire [2:0] g2;
        ot_qkvd_pop_ff u_g0 (.clk(clk), .rst_n(rst_n), .d(gq_i[0]), .q(g2[0]));
        ot_qkvd_pop_ff u_g1 (.clk(clk), .rst_n(rst_n), .d(gq_i[1]), .q(g2[1]));
`ifdef KVD_KE_MUT_TM
        assign g2[2] = gq_i[2];                                            // mutant: class 6 selected one cycle early
`else
        ot_qkvd_pop_ff u_g2 (.clk(clk), .rst_n(rst_n), .d(gq_i[2]), .q(g2[2]));
`endif
        assign sel_word[132*c +: 132] = ({132{g2[0]}} & h0[132*c +: 132]) | ({132{g2[1]}} & h1[132*c +: 132]) |
                                        ({132{g2[2]}} & h2[132*c +: 132]);
    end endgenerate
    reg [527:0] tf0w;
    always @(posedge clk) tf0w <= sel_word;
    assign tw = tf0w;
endmodule

// link TX face: up_q is ot_qkvd_d2d's up_q, tx_flit / tx_v its tx_flit / tx_v
module ot_qkvd_ke_tf (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         tx_up,           // N face (PHY FDI)
    output reg          tx_v,
    output reg  [547:0] tx_flit,
    output wire         upq,             // to ctl: up_q
    input  wire [19:0]  tf0h,            // from ctl: tf0 header {seq 8, credit return 8, dv, class 3}
    input  wire         tv0_i,           // from ctl: tv0
    input  wire [527:0] tw               // from ot_qkvd_ke_tm: tf0 word
);
    reg up_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin up_q <= 1'b0; tx_v <= 1'b0; end
        else begin up_q <= tx_up; tx_v <= tv0_i; end
    assign upq = up_q;
`ifdef KVD_KE_MUT_TF
    always @(posedge clk) tx_flit <= {tf0h[19:4], 1'b1, tf0h[2:0], tw};    // mutant: every flit marked as carrying a word
`else
    always @(posedge clk) tx_flit <= {tf0h, tw};
`endif
endmodule

// die RX face lane (class j): rd0 / r_d are ot_qkvd_d2d's g_rorl.rd0 / r_d, en2 its rq2[j] (= rb_pop[j]), rv0 / r_v its
// rv0[j] / r_v[j], cr_q its cr_q[j]
module ot_qkvd_ke_ro (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         en_i,            // from ctl: rq_q[j] (pop decided last cycle)
    input  wire [527:0] head,            // RX buffer head (registered inside the tile)
    input  wire         r_cr,            // S face
    output reg          r_v,
    output reg  [527:0] r_d,
    output wire         crq              // to ctl: cr_q
);
    reg cr_q, rv0, e2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_q <= 1'b0; rv0 <= 1'b0; r_v <= 1'b0; e2 <= 1'b0; end
        else begin cr_q <= r_cr; e2 <= en_i; rv0 <= e2; r_v <= rv0; end
    assign crq = cr_q;
    reg [527:0] rd0;
    genvar c;
    generate for (c = 0; c < 4; c = c + 1) begin : g_en
        wire en2;                                                          // enable copy: 132 flops each
`ifdef KVD_KE_MUT_RO
        assign en2 = en_i;                                                 // mutant: head captured one cycle early
`else
        ot_qkvd_pop_ff u_e (.clk(clk), .rst_n(rst_n), .d(en_i), .q(en2));
`endif
        always @(posedge clk) if (en2) rd0[132*c +: 132] <= head[132*c +: 132];
    end endgenerate
    always @(posedge clk) r_d <= rd0;
endmodule

// W face: the cluster's reset synchroniser (rst_n pin -> rsw, synchronous release) and the fault face flops
module ot_qkvd_ke_wf (
    input  wire        clk,
    input  wire        rst_n,            // W face (async assert)
    output wire        rsw,              // to ctl: synchronised reset
    input  wire [5:0]  flt_i,            // from ctl: {fault_cause[4:0], fault}
    output reg         fault,            // W face
    output reg  [4:0]  fault_cause
);
    (* keep *) reg r0, r1;
    (* keep *) reg f0, f1;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin r0 <= 1'b0; r1 <= 1'b0; end else begin r0 <= 1'b1; r1 <= r0; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin f0 <= 1'b0; f1 <= 1'b0; end else begin f0 <= 1'b1; f1 <= f0; end
    assign rsw = r1;
    always @(posedge clk or negedge f1)
        if (!f1) begin fault <= 1'b0; fault_cause <= 5'd0; end
`ifdef KVD_KE_MUT_WF
        else begin fault <= flt_i[0]; fault_cause <= {flt_i[1], flt_i[5:2]}; end   // mutant: cause bits rotated
`else
        else begin fault <= flt_i[0]; fault_cause <= flt_i[5:1]; end
`endif
endmodule

// control: ot_qkvd_d2d's credit / grant / shadow / sequence / fault logic for NT 3, NR 4, TXB 4, RXB 0, HT, PQ=2, PF,
// IBD {8, 4, UCX, UCX}, FCR {0, 4, 32, FCR_RES}, RBD {32, 8, 32, 4}, OCR {32, 8, QD, 4}.  Same registers and equations;
// the strap-dependent reset values (lcred[0] = cfg_fcr0, ocred[1] = cfg_qd) are taken on the first clock after reset
// (ini) instead of by the asynchronous reset.
module ot_qkvd_ke_ctl (
    input  wire        clk,
    input  wire        rst_n,            // rsw from ot_qkvd_ke_wf (synchronous release)
    input  wire [7:0]  cfg_ucx,          // straps (tied in the cluster): UCX, QD, FCR_RES (+1 with MUT 1)
    input  wire [7:0]  cfg_qd,
    input  wire [7:0]  cfg_fcr0,
    input  wire [2:0]  civ,              // ti: ci_v
    input  wire        rqv,              // rq: rq_v, header
    input  wire [19:0] rqh,
    input  wire [3:0]  crq,              // ro: cr_q
    input  wire        upq,              // tf: up_q
    output wire [2:0]  pp_t,             // TX buffer pop pins
    output wire [3:0]  pp_r,             // RX buffer pop pins
    output wire [2:0]  gq_o,             // tm: gq
    output wire [2:0]  gq2_o,            // ti: gq2 (-> t_cr)
    output wire [3:0]  rqq_o,            // ro: rq_q
    output reg  [19:0] tf0h,             // tf: tf0 header
    output reg         tv0,              // tf: tv0
    output wire [5:0]  flt,              // wf: {fault_cause, fault}
    output wire        rs_s,             // reset copies: S-face tiles, N-face tiles, TX buffers, RX buffers
    output wire        rs_n,
    output wire        rs_ta,
    output wire        rs_tb
);
    localparam integer NT = 3, NR = 4, TXB = 4, RXB = 0;
    // ---- reset copies (identical release cycle) ----
    (* keep *) reg rs0, rs, rs_t0, rs_t, rss0, rss, rsn0, rsn, rta0, rta, rtb0, rtb;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rs_t0 <= 1'b0; rs_t <= 1'b0; end else begin rs_t0 <= 1'b1; rs_t <= rs_t0; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rss0 <= 1'b0; rss <= 1'b0; end else begin rss0 <= 1'b1; rss <= rss0; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rsn0 <= 1'b0; rsn <= 1'b0; end else begin rsn0 <= 1'b1; rsn <= rsn0; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rta0 <= 1'b0; rta <= 1'b0; end else begin rta0 <= 1'b1; rta <= rta0; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rtb0 <= 1'b0; rtb <= 1'b0; end else begin rtb0 <= 1'b1; rtb <= rtb0; end
    assign rs_s = rss; assign rs_n = rsn; assign rs_ta = rta; assign rs_tb = rtb;
    // ---- pin capture ----
    reg [NT-1:0] ce_v;                   // = ot_qkvd_d2d ci2_v
    reg          re_v;                   // = rq2_v
    reg [19:0]   re_h;                   // = rq2_h
    reg [NR-1:0] cr_q;
    reg          up_q;
    always @(posedge clk) re_h <= rqh;
    always @(posedge clk or negedge rs)
        if (!rs) begin ce_v <= 0; re_v <= 1'b0; cr_q <= 0; up_q <= 1'b0; end
        else begin ce_v <= civ; re_v <= rqv; cr_q <= crq; up_q <= upq; end
    wire [7:0] rx_seq_f = re_h[19:12];
    wire [7:0] rx_crs   = re_h[11:4];
    wire       rx_dv    = re_v && re_h[3];
    wire [2:0] rx_cls   = re_h[2:0];
    // ---- configuration ----
    wire [7:0] IBD [0:NT-1];
    wire [7:0] FCR [0:NT-1];
    wire [7:0] RBD [0:NR-1];
    wire [7:0] OCR [0:NR-1];
    reg [7:0] s_ucx, s_qd, s_fcr0;       // strap pin flops (static values; no reset: valid before the reset releases)
    always @(posedge clk) begin s_ucx <= cfg_ucx; s_qd <= cfg_qd; s_fcr0 <= cfg_fcr0; end
    assign IBD[0] = s_ucx;    assign IBD[1] = s_ucx;   assign IBD[2] = 8'd4;
    assign FCR[0] = s_fcr0;   assign FCR[1] = 8'd32;   assign FCR[2] = 8'd4;
    assign RBD[0] = 8'd4;     assign RBD[1] = 8'd32;   assign RBD[2] = 8'd8;  assign RBD[3] = 8'd32;
    assign OCR[0] = 8'd4;     assign OCR[1] = s_qd;    assign OCR[2] = 8'd8;  assign OCR[3] = 8'd32;
    reg ini;                             // 0 on the first clock after reset: the strap reset values are in effect
    always @(posedge clk or negedge rs) if (!rs) ini <= 1'b0; else ini <= 1'b1;

    reg f_die, f_rb, f_seq, f_cred, f_cls;
    reg fault;
    reg [4:0] fault_cause;
    assign flt = {fault_cause, fault};
    // ---- TX side ----
    wire [NT-1:0] ib_full;
    reg  [NT-1:0] lc_nz;
    reg  [7:0]    lcred [0:NT-1];
    reg  [1:0]    rr;
    reg  [NT-1:0] gnt;
    reg           any;
    wire [NT-1:0] tx_ne;
    reg  [NT-1:0] gq, gq2;
    reg           up2, up3;
    wire [NT-1:0] gsel = gq2;
    wire          anys = |gsel;
    wire          up_s = up3;
    wire [NT-1:0] lc_nz_e;               // lc_nz with the reset value FCR != 0
    wire [NT-1:0] sh_e_t;                // shadow empties (simulation check in the cluster)
    integer k, c;
    always @* begin
        gnt = 0; any = 1'b0;
        for (k = 0; k < NT; k = k + 1) begin
            c = (rr + k) % NT;
            if (!any && up_q && tx_ne[c] && lc_nz_e[c]) begin gnt[c] = 1'b1; any = 1'b1; end
        end
    end
    genvar i, j;
    generate for (i = 0; i < NT; i = i + 1) begin : g_tx
        reg [7:0] oc;
        always @(posedge clk or negedge rs) if (!rs) oc <= 8'd0; else oc <= oc + (ce_v[i] ? 8'd1 : 8'd0) - (gsel[i] ? 8'd1 : 8'd0);
        assign ib_full[i] = (oc == IBD[i]);
        assign lc_nz_e[i] = ini ? lc_nz[i] : (FCR[i] != 8'd0);
        ot_qkvd_pop_ff u_pp  (.clk(clk), .rst_n(rs), .d(gnt[i]), .q(pp_t[i]));     // pop pin flop
        ot_qkvd_pop_ff u_gqo (.clk(clk), .rst_n(rs), .d(gnt[i]), .q(gq_o[i]));     // = gq, for the seam to ot_qkvd_ke_tm
        ot_qkvd_pop_ff u_g2o (.clk(clk), .rst_n(rs), .d(gq[i]),  .q(gq2_o[i]));    // = gq2, for the seam to ot_qkvd_ke_ti
        if (i < 2) begin : g_s
            ot_qkvd_sbuf_shadow #(.PIQ(1)) u_sh (.clk(clk), .rst_n(rs_t), .push(ce_v[i]), .pop(gq[i]), .empty(sh_e_t[i]), .ne_next(tx_ne[i]));
        end else begin : g_f
            ot_qkvd_fbuf8_shadow #(.PIQ(1)) u_sh (.clk(clk), .rst_n(rs_t), .push(ce_v[i]), .pop(gq[i]), .empty(sh_e_t[i]), .ne_next(tx_ne[i]));
        end
    end endgenerate
    reg [2:0] sel_cls;
    always @* begin
        sel_cls = 3'd0;
        for (k = 0; k < NT; k = k + 1) if (gsel[k]) sel_cls = 3'(TXB + k);
    end
    // ---- RX side ----
    wire [NR-1:0] rb_full;
    reg  [7:0]    ocred [0:NR-1];
    reg  [7:0]    owed  [0:NR-1];
    wire [NR-1:0] rb_push, rb_pop, rx_ne, rdec;
    reg  [NR-1:0] rq2, rq_q;
    wire [NR-1:0] sh_e_r;
    generate for (j = 0; j < NR; j = j + 1) begin : g_rx
        wire [7:0] ocb = ini ? ocred[j] : OCR[j];
        assign rb_push[j] = rx_dv && (rx_cls == 3'(RXB + j));
`ifdef KVD_KE_MUT_CTL
        assign rdec[j]    = rx_ne[j];                                      // mutant: pops issued without a die-face credit
`else
        assign rdec[j]    = rx_ne[j] && (ocb != 8'd0);
`endif
        assign rb_pop[j]  = rq2[j];
        reg [7:0] oc;
        always @(posedge clk or negedge rs) if (!rs) oc <= 8'd0; else oc <= oc + (rb_push[j] ? 8'd1 : 8'd0) - (rb_pop[j] ? 8'd1 : 8'd0);
        assign rb_full[j] = (oc == RBD[j]);
        ot_qkvd_pop_ff u_pp  (.clk(clk), .rst_n(rs), .d(rdec[j]), .q(pp_r[j]));    // pop pin flop
        ot_qkvd_pop_ff u_rqo (.clk(clk), .rst_n(rs), .d(rdec[j]), .q(rqq_o[j]));   // = rq_q, for the seam to ot_qkvd_ke_ro
        if (j == 1 || j == 3) begin : g_s
            ot_qkvd_sbuf_shadow #(.PIQ(1)) u_sh (.clk(clk), .rst_n(rs_t), .push(rb_push[j]), .pop(rq_q[j]), .empty(sh_e_r[j]), .ne_next(rx_ne[j]));
        end else begin : g_f
            ot_qkvd_fbuf8_shadow #(.PIQ(1)) u_sh (.clk(clk), .rst_n(rs_t), .push(rb_push[j]), .pop(rq_q[j]), .empty(sh_e_r[j]), .ne_next(rx_ne[j]));
        end
    end endgenerate
    reg [7:0] cr_ret;
    reg [1:0] ret [0:3];
    always @* begin
        cr_ret = 8'd0;
        for (k = 0; k < 4; k = k + 1) begin
            ret[k] = (owed[k] > 8'd3) ? 2'd3 : owed[k][1:0];
            if (!up_s) ret[k] = 2'd0;
            cr_ret[2*k +: 2] = ret[k];
        end
    end
    reg [7:0] tx_seq, rx_seq;
    always @(posedge clk) tf0h <= {tx_seq, cr_ret, anys, sel_cls};         // datapath: no reset
    always @(posedge clk or negedge rs) begin
        if (!rs) begin
            tv0 <= 1'b0; gq <= 0; up2 <= 1'b0; rq_q <= 0; gq2 <= 0; up3 <= 1'b0; rq2 <= 0; tx_seq <= 8'd0; rx_seq <= 8'd0; rr <= 0;
            f_die <= 1'b0; f_rb <= 1'b0; f_seq <= 1'b0; f_cred <= 1'b0; f_cls <= 1'b0;
            fault <= 1'b0; fault_cause <= 5'd0;
            for (k = 0; k < NT; k = k + 1) begin lcred[k] <= 8'd0; lc_nz[k] <= 1'b0; end
            for (k = 0; k < NR; k = k + 1) begin ocred[k] <= 8'd0; owed[k] <= 8'd0; end
        end else begin
            // die TX face
            for (k = 0; k < NT; k = k + 1) if (ce_v[k] && ib_full[k] && !gsel[k]) f_die <= 1'b1;
            // link TX
            gq <= gnt; up2 <= up_q; rq_q <= rdec; gq2 <= gq; up3 <= up2; rq2 <= rq_q;
            tv0 <= up_s;
            if (up_s) tx_seq <= tx_seq + 1'b1;
            if (any) rr <= 2'((rr + 1) % NT);
            for (k = 0; k < NT; k = k + 1) begin : upd_lc
                reg [8:0] nxt;
                nxt = {1'b0, ini ? lcred[k] : FCR[k]} - (gnt[k] ? 9'd1 : 9'd0) + (re_v ? {7'd0, rx_crs[2*k +: 2]} : 9'd0);
                lcred[k] <= nxt[7:0];
                lc_nz[k] <= (nxt != 0);
                if (nxt > {1'b0, FCR[k]}) f_cred <= 1'b1;
            end
            // link RX
            if (re_v) begin
                rx_seq <= rx_seq + 1'b1;
                if (rx_seq_f != rx_seq) f_seq <= 1'b1;
            end
            if (rx_dv && (rx_cls >= 3'(RXB + NR))) f_cls <= 1'b1;
            for (k = 0; k < NR; k = k + 1) begin
                if (rb_push[k] && rb_full[k] && !rb_pop[k]) f_rb <= 1'b1;
                owed[k] <= owed[k] - (up_s ? {6'd0, ret[k]} : 8'd0) + (rb_pop[k] ? 8'd1 : 8'd0);
                ocred[k] <= (ini ? ocred[k] : OCR[k]) - (rdec[k] ? 8'd1 : 8'd0) + (cr_q[k] ? 8'd1 : 8'd0);
            end
            fault_cause <= {f_cls, f_cred, f_seq, f_rb, f_die};
            fault <= f_die | f_rb | f_seq | f_cred | f_cls;
        end
    end
endmodule
