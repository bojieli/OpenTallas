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
module hfd_lk_ep (
    input  wire [0:0]    clk,                         // die record: 1-bit buses (pins clk[0] / rst_n[0])
    inout  wire [1119:0] f_lk,
    inout  wire [973:0]  phy,
    input  wire [0:0]    rst_n
);
    reg  [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [1:0] rw;                              // [0] input-side registers, [1] output-side registers
    always @(posedge clk) rw <= {2{rs[1]}};
    wire fault, locked;
    reg [23:0] session;                                   // pin register (changes only under the coordinated reset)
    always @(posedge clk) session <= f_lk[1117:1094];
    reg            t_v_q, r_cr_q, t_v_r, r_cr_r;
    reg  [544:0]   t_f_q, t_f_r;
    always @(posedge clk or negedge rw[0]) if (!rw[0]) begin t_v_q <= 1'b0; r_cr_q <= 1'b0; t_v_r <= 1'b0; r_cr_r <= 1'b0; end
                                           else begin t_v_q <= f_lk[0]; r_cr_q <= f_lk[546]; t_v_r <= t_v_q; r_cr_r <= r_cr_q; end
    always @(posedge clk) begin t_f_q <= f_lk[545:1]; t_f_r <= t_f_q; end
    wire           t_cr, r_v;
    wire [544:0]   r_flit;
    wire [486:0]   x_tx;
    ot_hbm_lk_ep #(.NS(3), .LW(487), .TXQ(32), .FCR(256)) u (.clk(clk), .rst_n(rst_n), .session(session),
        .t_v(t_v_r), .t_flit(t_f_r), .t_cr(t_cr), .r_v(r_v), .r_flit(r_flit), .r_cr(r_cr_r),
        .x_tx(x_tx), .x_rx(phy[973:487]), .fault(fault), .locked(locked));
    reg            r_v_o, t_cr_o, fault_q, locked_q;
    reg  [544:0]   r_flit_o;
    always @(posedge clk or negedge rw[1]) if (!rw[1]) begin r_v_o <= 1'b0; t_cr_o <= 1'b0; fault_q <= 1'b0; locked_q <= 1'b0; end
                                           else begin r_v_o <= r_v; t_cr_o <= t_cr; fault_q <= fault; locked_q <= locked; end
    always @(posedge clk) r_flit_o <= r_flit;
    assign f_lk[547] = r_v_o;
    assign f_lk[1092:548] = r_flit_o;
    assign f_lk[1093] = t_cr_o;
    assign f_lk[1119:1118] = {locked_q, fault_q};
    assign phy[486:0] = x_tx;
endmodule
