// el1011-ds-misc/pqc 2026-10-11: black-box stubs of the hardened v15 spine tiles for the screen composition (the
// views' LEF / liberty carry the implementation).  Read FIRST: it also sets the screen's ROM-port define.
`ifndef OT_PQ_ROM_PORTS
`define OT_PQ_ROM_PORTS
`endif
(* blackbox *) module ot_dsrom_aq12t (input clk, rst_n, v, input [1023:0] x, output vo, output [255:0] q,
                                     output [9:0] e, output [511:0] y, output fault);
endmodule
(* blackbox *) module ot_pqc_t_ix (input clk, rst_n, par, input [1023:0] xw, input ba_v, input [2:0] ba_blk,
                                  input [35:0] h_hi, input [6:0] hw7, output [255:0] bt_d);
endmodule
(* blackbox *) module ot_pqc_t_qb (input clk, rst_n, input [4:0] aqi_d, input [511:0] aq_q, input [19:0] aq_e,
                                  input [15:0] h_b0, h_b1, input [1:0] hw_sv, output [255:0] hq0, hq1,
                                  output [9:0] he0, he1);
endmodule
(* blackbox *) module ot_pqc_t_ret (input clk, rst_n, input [7:0] r_v, input [127:0] r_row, input [23:0] r_pos,
                                   input [255:0] r_fp32, input [127:0] r_bf16, input [7:0] r_e, input [457:0] mdr,
                                   output [7:0] w_we, output [151:0] w_addr, output [255:0] w_data, output q2f,
                                   output [15:0] ga);
endmodule
(* blackbox *) module ot_pqc_t_bc (input clk, rst_n, input [1629:0] d, output [1629:0] q);
endmodule
(* blackbox *) module ot_pqc_t_srom (input clk, rst_n, we, input [7:0] wa, input [47:0] wd, input [7:0] ra,
                                    output [47:0] q);
endmodule
(* blackbox *) module ot_pqc_t_prom (input clk, rst_n, we, input [6:0] wa, input [63:0] wd, input [6:0] ra,
                                    output [63:0] q);
endmodule
(* blackbox *) module ot_pqc_t_ctl16 (input clk, rst_n, output aq_vin, input [1:0] aqf, output [4:0] aqi_o,
    output ba_v_o, output [2:0] ba_blk_o, output [47:0] hw_o, output [35:0] h_hi_o, output [15:0] h_b0_o, h_b1_o,
    output [457:0] mdr_o, input [1:0] q2f_i, input [31:0] ga_i, output [605:0] bc_hr_o, input go, input [5:0] i_ph,
    input [2:0] i_np, input [18:0] i_xbase, i_xps, i_obase, i_ops, input [1:0] i_fmt, input x_rv, f_fault,
    output o_ready, o_idle, o_x_re, output [18:0] o_x_addr, output o_fault, o_ev, output [6:0] rom_pa0, rom_pa1,
    input [63:0] rom_pq0, rom_pq1, output [7:0] rom_sa, input [47:0] rom_sq);
endmodule
(* blackbox *) module ot_pqc_t_xin (input clk, input [1023:0] d, output [1023:0] q);
endmodule
