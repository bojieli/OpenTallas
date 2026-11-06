`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HBM-REFORM-B d44v part 20 (OWNER 11-03 conservative form): HBM ot_pdie_serdes split into plan designs inside its slot,
// on the natural boundaries of the module, same line as HEAD hd_serdes (claude/dh58-rfrtl-1103) and S81's KP4 form:
//   ot_pdie_serdes_tx = reset sync + ot_s81_kp4_enc + PMA TX model
//   ot_pdie_serdes_rx = reset syncs + PMA RX model + dsyn + ddly + dout + unc flag + rate matcher + status
//   ot_s81_kp4_dchn   = Chien / Forney, the signed KP4 core, unchanged RTL, no face shell (its pins are registered)
// The instances, parameters and nets are those of ot_pdie_serdes, except:
//   * ddly DD = 55 + SEAM.  The kit face shell of rx adds SEAM = 2 edges on the correction path (k_* out + 1, cw_q /
//     apply / o_unc / o_ne / fs in + 1), and the words stay inside rx, so the words wait 2 more edges.  DC does not
//     change: cw_q, apply and fs share the seam.
//   * so every decoded beat and the uncorrectable flag reach rx / st 2 edges later than in ot_pdie_serdes; e_flt
//     (tx out + 1, rx in + 1) reaches st[0] 2 edges later.  pma_tx, the tx input and st[1] (lock) do not move.
//   * the recovered clock port is named rck_clk so the kit passes it as a clock pin (COORD ruling 11-04 23:2x).  The
//     HBM kit carries one core clock (face_shell.apply), so all three designs run on the slot's clock entry.
//   * pma_tck leaves tx: it is the core clock with no die-level consumer, and a tile output pin would be shelled as
//     data (OT_CLOCK_FAMILY stop at CTS).  The composition keeps ot_pdie_serdes.pma_tck = clk, wire only.
//   * ELA (HBM-GAPS-3 11-05, opt-in, default 1 = unchanged): ELA = 2 builds the encoder as ot_s81_kp4_enc_la #(.LA(2))
//     (two-step parity lookahead, the rem_q loop gets two cycles; serdes_tx routed TT -180.76 on rem_q -> rem_q in the
//     ELA = 1 form).  pma_tx is then the ELA = 1 stream delayed by exactly one edge, e_flt is unchanged (tb_kp4_enc_la.sv, tb_pdie_tx_ela.sv).
//   * EFF (default 0): LA2 feed-forward partial stage, pma_tx delayed exactly one further edge.
//   * BMTHC (opt-in, default 0; recipe ot_pdie_serdes_rx sets 1): RiBM theta_45 reachable form (ot_s81_kp4_bm THC),
//     so the X power-up of the unloaded theta_45 bits matches the folded netlist under LEC.
// The face registers are the kit's; this file adds none.  dchn rst_n is the slot reset (no consumer before k_v).
// ---------------------------------------------------------------------------------------------------------------------
module ot_pdie_serdes_tx #(parameter integer PMA_LAT = 4, parameter integer EMUT = 0, parameter integer ELA = 1, parameter integer EFF = 0) (
    input  wire          clk,
    input  wire          rst,
    input  wire [511:0]  tx,
    output wire [543:0]  pma_tx,
    output wire          e_flt_o
);
    reg [1:0] rs_t;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    wire rn_t = rs_t[1];
    wire e_v; wire [543:0] e_d;
    generate if (ELA == 1) begin : g_e1
        ot_s81_kp4_enc #(.MUT(EMUT)) u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t), .tx_d(tx), .p_v(e_v), .p_d(e_d), .fault(e_flt_o));
    end else begin : g_ela
        ot_s81_kp4_enc_la #(.MUT(EMUT), .LA(ELA), .FF(EFF)) u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t), .tx_d(tx), .p_v(e_v), .p_d(e_d),
                                                        .fault(e_flt_o));
    end endgenerate
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_ptx (.clk(clk), .d_v(e_v), .d(e_d), .q(pma_tx));
endmodule

module ot_pdie_serdes_rx #(parameter integer PMA_LAT = 4, parameter integer DMUT = 0, parameter integer SEAM = 2,
    parameter integer BMTHC = 0) (
    input  wire          clk,
    input  wire          rck_clk,
    input  wire          rst,
    output wire [511:0]  rx,
    output wire [1:0]    st,
    input  wire [543:0]  pma_rx,
    input  wire          e_flt_i,
    output wire [3:0]    k_v,
    output wire [309:0]  k_lo,
    output wire [4:0]    k_L,
    output wire          k_any,
    input  wire [543:0]  cw_q,
    input  wire [7:0]    apply,
    input  wire          o_unc,
    input  wire [4:0]    o_ne,
    input  wire          fs
);
    reg [1:0] rs_t, rs_r;
    always @(posedge clk or negedge rst) if (!rst) rs_t <= 2'b00; else rs_t <= {rs_t[0], 1'b1};
    always @(posedge rck_clk or negedge rst) if (!rst) rs_r <= 2'b00; else rs_r <= {rs_r[0], 1'b1};
    wire rn_t = rs_t[1], rn_r = rs_r[1];
    wire [543:0] r_d, x_q, d_q;
    ot_s81_pma_bm #(.W(544), .LAT(PMA_LAT)) u_prx (.clk(rck_clk), .d_v(1'b1), .d(pma_rx), .q(r_d));
    wire q_v, q_first, q_unc, lock; wire [511:0] q_d; wire [4:0] q_nerr; wire [7:0] q_seq; wire [31:0] n_rl;
    ot_s81_kp4_dsyn #(.MUT(DMUT), .BMTHC(BMTHC)) u_syn (.clk(rck_clk), .rst_n(rn_r), .p_v(rn_r), .p_d(r_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo),
        .k_L(k_L), .k_any(k_any), .lock(lock), .n_relock(n_rl));
    ot_s81_kp4_ddly #(.DD(55 + SEAM)) u_dly (.clk(rck_clk), .rst_n(rn_r), .w_d(x_q), .r_d(d_q));
    ot_s81_kp4_dout u_out (.clk(rck_clk), .rst_n(rn_r), .d_q(d_q), .cw(cw_q), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq));
    reg unc_r; always @(posedge rck_clk or negedge rn_r) if (!rn_r) unc_r <= 1'b0; else if (q_v && q_first && q_unc) unc_r <= 1'b1;
    wire rm_flt;
    ot_s81_rate_match u_rm (.wclk(rck_clk), .wrst_n(rn_r), .w_v(q_v), .w_d(q_d), .rclk(clk), .rrst_n(rn_t), .r_d(rx),
        .fault(rm_flt));
    reg [1:0] lk_s, uf_s;
    always @(posedge clk or negedge rn_t)
        if (!rn_t) begin lk_s <= 2'b00; uf_s <= 2'b00; end
        else begin lk_s <= {lk_s[0], lock}; uf_s <= {uf_s[0], unc_r}; end
    reg [1:0] st_q;
    always @(posedge clk or negedge rn_t) if (!rn_t) st_q <= 2'b00; else st_q <= {lk_s[1], st_q[0] | uf_s[1] | rm_flt | e_flt_i};
    assign st = st_q;
endmodule
