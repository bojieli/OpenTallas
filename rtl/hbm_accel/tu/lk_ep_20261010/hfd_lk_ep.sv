`timescale 1ns/1ps
// hfd_lk_ep ([link] 2026-10-10): die master of the per-link endpoint (R25GQ, [fp] f0624cc33: 9 slots,
// pins physical/hbm_accel_die_views/ports_r25gqn/hfd_lk_ep).  Thin wrapper of ot_hbm_lk_ep (NS = 3, lead decision
// 10-10) onto the die buses:
//   f_lk[1093:0] (to / from hb_coll):  [0] t_v, [545:1] t_flit, [546] r_cr       (inputs: coll -> link)
//                                      [547] r_v, [1092:548] r_flit, [1093] t_cr (outputs: link -> coll)
//                                      [1117:1094] session (in, from coll), [1119:1118] {locked, fault} (out, to coll)
//   phy[973:0]   (to / from ot_pdie_serdes): [486:0] x_tx (out), [973:487] x_rx (in)
// clk = clk_link (the SerDes ck tree), rst_n = rst_link (hb_coll por_link)  ([fp] f3eeffcbf).
// Every die-side input lands in a single-fanout pin register (io_flop_at_pins anchors it at its pin) followed by one
// relay register; every die-side output leaves from a single-fanout pin register fed by the core's output register
// ([link] 2026-10-10: 304cd8c93 preroute had f_lk -> t_f_q -1,013 ps (the pin flop fanned out to the 32-deep queue) and
// r_flit -> f_lk -504 ps).  rst_n reaches a 2-flop synchroniser; the wrapper's registers use a replicated copy.
// +1 edge each way on the die credit loop (TXQ 32 covers it: tb_lk_rate).
module hfd_lk_ep #(parameter integer HARD_CLOCKS=0, parameter integer MUT_FACE=0)(
    input wire [0:0] clk, input wire [0:0] clk_face,
    inout wire [1119:0] f_lk, inout wire [973:0] phy, input wire [0:0] rst_n);
    wire face_clock = HARD_CLOCKS != 0 ? clk_face[0] : clk[0];
    wire t_v_s,r_cr_s,t_cr,r_v,fault,locked;
    wire [544:0] t_f_s,r_flit; wire [23:0] session; wire [486:0] x_tx;
    hfd_lk_ep_face #(.MUT_FACE(MUT_FACE)) u_face(.clk(face_clock), .rst_n(rst_n[0]), .f_lk(f_lk), .core_t_v(t_v_s),
        .core_t_flit(t_f_s), .core_r_cr(r_cr_s), .core_session(session),
        .t_cr(t_cr), .r_v(r_v), .r_flit(r_flit), .fault(fault), .locked(locked));
    ot_hbm_lk_ep #(.NS(3), .LW(487), .TXQ(32), .FCR(256)) u (.clk(clk), .rst_n(rst_n), .session(session),
        .t_v(t_v_s), .t_flit(t_f_s), .t_cr(t_cr), .r_v(r_v), .r_flit(r_flit), .r_cr(r_cr_s),
        .x_tx(x_tx), .x_rx(phy[973:487]), .fault(fault), .locked(locked));
    assign phy[486:0]=x_tx;
endmodule
