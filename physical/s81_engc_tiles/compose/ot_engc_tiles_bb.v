// el1011-ds-misc/engram 2026-10-11: black-box stubs of the hardened all-tile engram_c tiles for the composition's
// synthesis (the views' LEF / liberty carry the implementation; ports = rtl/dsrom_sys/engram/tiles/*).
(* blackbox *) module ot_engc_t_pbb (input ck, rst, input [5:0] w_oh, input [7:0] w_a, input [255:0] w_d, input [319:0] x_d,
    output [5:0] x_oh, output [7:0] x_a, output [319:0] x_do, input [5:0] r_oh, input [7:0] r_a, output [255:0] r_d);
endmodule
(* blackbox *) module ot_engc_t_pbc (input ck, rst, input [5:0] w_oh, input [7:0] w_a, input [255:0] w_d, input [63:0] x_d,
    output [5:0] x_oh, output [7:0] x_a, output [63:0] x_do, input [5:0] r_oh, input [7:0] r_a, output [255:0] r_d);
endmodule
(* blackbox *) module ot_engc_t_ws (input ck, rst, wr_v, input [10:0] wr_addr, input [511:0] wr_data, output werr,
    output [5:0] w_oh, output [7:0] w_a, output [255:0] b1_d, output [319:0] x_d, input lk_hqv, input [30:0] lk_hqa,
    input [2:0] lk_hqt, output [34:0] t_hq, input [264:0] f_hr, output [264:0] lk_hr);
endmodule
(* blackbox *) module ot_engc_t_win (input ck, rst, input [72:0] f_win, output t_collective, output lk_wv,
    output [67:0] lk_wid, input lk_wcred, output [3:0] lk_rel, input lk_ov, lk_stv, lk_stb, lk_fault, input [4:0] lk_oc,
    input [2:0] lk_ob, lk_os, lk_sts, input [263:0] lk_od, output [281:0] t_ag, input f_agc, output lk_ocred,
    input [2:0] cfg_i, output [2:0] cfg_o, output rn_lk, rn_sk, input [7:0] s_rdy, s_perr, output [7:0] rdy_o, perr_o,
    input [3:0] vrel_i, output [3:0] vrel_o, input [17:0] jn_i, output [15:0] wn_o, output jf_o, input werr_i,
    output werr_o);
endmodule
(* blackbox *) module ot_engc_t_io (input ck, rst, input [84:0] c_cmd, output [8:0] c_done, output [1:0] c_st,
    input [2:0] f_cfg, output [2:0] cfg_o, input [15:0] f_vm, output [531:0] t_vm, input [7:0] rdy_i, perr_i,
    output [3:0] vrel_o, output [17:0] jn_o, input [15:0] wn_i, input jf_i, werr_i, output [5:0] r0_oh, r1_oh, r2_oh,
    output [7:0] r0_a, r1_a, r2_a, input [255:0] rd0, rd1, input [63:0] rd2);
endmodule
