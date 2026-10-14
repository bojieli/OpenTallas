// q13-kvleaves 2026-10-13: blackbox views of the hard KV-end tiles (ot_qkvd_ke_tiles.sv) for the thin-cluster route.
(* blackbox *)
module ot_qkvd_ke_ti (input wire clk, input wire rst_n, input wire t_v, input wire [527:0] t_d, output wire t_cr,
    input wire tcr_i, output wire civ, output wire psh, output wire [527:0] ce_d);
endmodule
(* blackbox *)
module ot_qkvd_ke_rq (input wire clk, input wire rst_n, input wire rx_v, input wire [547:0] rx_flit, output wire rqv,
    output wire [19:0] rqh, output wire [3:0] psh, output wire [527:0] w0, output wire [527:0] w1,
    output wire [527:0] w2, output wire [527:0] w3);
endmodule
(* blackbox *)
module ot_qkvd_ke_tm (input wire clk, input wire rst_n, input wire [2:0] gq_i, input wire [527:0] h0,
    input wire [527:0] h1, input wire [527:0] h2, output wire [527:0] tw);
endmodule
(* blackbox *)
module ot_qkvd_ke_tf (input wire clk, input wire rst_n, input wire tx_up, output wire tx_v, output wire [547:0] tx_flit,
    output wire upq, input wire [19:0] tf0h, input wire tv0_i, input wire [527:0] tw);
endmodule
(* blackbox *)
module ot_qkvd_ke_ro (input wire clk, input wire rst_n, input wire en_i, input wire [527:0] head, input wire r_cr,
    output wire r_v, output wire [527:0] r_d, output wire crq);
endmodule
(* blackbox *)
module ot_qkvd_ke_wf (input wire clk, input wire rst_n, output wire rsw, input wire [5:0] flt_i, output wire fault,
    output wire [4:0] fault_cause);
endmodule
(* blackbox *)
module ot_qkvd_ke_ctl (input wire clk, input wire rst_n, input wire [7:0] cfg_ucx, input wire [7:0] cfg_qd,
    input wire [7:0] cfg_fcr0, input wire [2:0] civ, input wire rqv, input wire [19:0] rqh, input wire [3:0] crq,
    input wire upq, output wire [2:0] pp_t, output wire [3:0] pp_r, output wire [2:0] gq_o, output wire [2:0] gq2_o,
    output wire [3:0] rqq_o, output wire [19:0] tf0h, output wire tv0, output wire [5:0] flt, output wire rs_s,
    output wire rs_n, output wire rs_ta, output wire rs_tb);
endmodule
