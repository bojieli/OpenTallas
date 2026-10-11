`timescale 1ns/1ps
// hfd_lk_ep ([link] 2026-10-10): die master of the per-link endpoint (R25GQ, [fp] f0624cc33: 9 slots 1,503.36 x 993.6,
// pins physical/hbm_accel_die_views/ports_r25gqn/hfd_lk_ep).  Thin wrapper of ot_hbm_lk_ep (NS = 3, lead decision
// 10-10) onto the die buses, every die-side input landing in a pin register:
//   f_lk[1093:0] (to / from hb_coll):  [0] t_v, [545:1] t_flit, [546] r_cr       (inputs: coll -> link)
//                                      [547] r_v, [1092:548] r_flit, [1093] t_cr (outputs: link -> coll)
//   phy[973:0]   (to / from ot_pdie_serdes): [486:0] x_tx (out), [973:487] x_rx (in)
// NOT YET DIE PINS (asked of [fp]): clk (clk_link), rst_n, session[23:0] (coordinated-reset epoch from hb_coll), fault /
// locked (to the coll status aggregation).
module hfd_lk_ep (
    inout  wire [1093:0] f_lk,
    inout  wire [973:0]  phy,
    /* NOT A GENERATOR PORT */ input  wire        clk,
    /* NOT A GENERATOR PORT */ input  wire        rst_n,
    /* NOT A GENERATOR PORT */ input  wire [23:0] session,
    /* NOT A GENERATOR PORT */ output wire        fault,
    /* NOT A GENERATOR PORT */ output wire        locked
);
    reg            t_v_q, r_cr_q;
    reg  [544:0]   t_f_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin t_v_q <= 1'b0; r_cr_q <= 1'b0; end
                                          else begin t_v_q <= f_lk[0]; r_cr_q <= f_lk[546]; end
    always @(posedge clk) t_f_q <= f_lk[545:1];
    wire           t_cr, r_v;
    wire [544:0]   r_flit;
    wire [486:0]   x_tx;
    ot_hbm_lk_ep #(.NS(3), .LW(487)) u (.clk(clk), .rst_n(rst_n), .session(session),
        .t_v(t_v_q), .t_flit(t_f_q), .t_cr(t_cr), .r_v(r_v), .r_flit(r_flit), .r_cr(r_cr_q),
        .x_tx(x_tx), .x_rx(phy[973:487]), .fault(fault), .locked(locked));
    assign f_lk[547] = r_v;
    assign f_lk[1092:548] = r_flit;
    assign f_lk[1093] = t_cr;
    assign phy[486:0] = x_tx;
endmodule
