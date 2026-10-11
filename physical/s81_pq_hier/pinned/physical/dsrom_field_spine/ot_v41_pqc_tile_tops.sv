`timescale 1ns/1ps
// The screen and its tiles always use the ROM macro ports (read before the spine file: defines persist).
`ifndef OT_PQ_ROM_PORTS
`define OT_PQ_ROM_PORTS
`endif
// el1011-ds-misc/pqc 2026-10-11: fixed-name, parameter-free tops of the v15 spine tiles at the physical-screen shape
// (PHW 6, SAW 8, VAW 19, VRD 64, KMAX 256, R 16, BW 1630, PQ 1, XRV 1, XCAP 16, RPT 2).  Each is routed as a hard
// macro (physical/qwen_die_masters/cfg/pqc_*), and the screen composition (spine TT = 1) instantiates these names so
// a synthesised instance binds to its view.  The bodies are the parameterised tiles of ot_v41_pqc_tiles.sv.
module ot_pqc_t_ix (input wire clk, rst_n, par, input wire [1023:0] xw, input wire ba_v, input wire [2:0] ba_blk,
                    input wire [35:0] h_hi, input wire [6:0] hw7, output wire [255:0] bt_d);
    ot_v41_pqc_ix #(.KMAX(256), .VRD(64)) u (.*);
endmodule
module ot_pqc_t_qb (input wire clk, rst_n, input wire [4:0] aqi_d, input wire [511:0] aq_q, input wire [19:0] aq_e,
                    input wire [15:0] h_b0, h_b1, input wire [1:0] hw_sv, output wire [255:0] hq0, hq1,
                    output wire [9:0] he0, he1);
    ot_v41_pqc_qb #(.KMAX(256)) u (.*);
endmodule
module ot_pqc_t_ret (input wire clk, rst_n, input wire [7:0] r_v, input wire [127:0] r_row, input wire [23:0] r_pos,
                     input wire [255:0] r_fp32, input wire [127:0] r_bf16, input wire [7:0] r_e, input wire [457:0] mdr,
                     output wire [7:0] w_we, output wire [151:0] w_addr, output wire [255:0] w_data, output wire q2f,
                     output wire [15:0] ga);
    ot_v41_pqc_ret #(.NR(8), .VAW(19), .PQ(1), .RPT(2), .PIN(1)) u (.*);
endmodule
module ot_pqc_t_bc (input wire clk, rst_n, input wire [1629:0] d, output wire [1629:0] q);
    ot_v41_pqc_bcrel #(.W(1630), .RT(15), .RB(1063)) u (.*);
endmodule
module ot_pqc_t_srom (input wire clk, rst_n, we, input wire [7:0] wa, input wire [47:0] wd, input wire [7:0] ra,
                      output wire [47:0] q);
    ot_v41_pqc_rom2_model #(.AW(8), .DW(48)) u (.*);
endmodule
module ot_pqc_t_prom (input wire clk, rst_n, we, input wire [6:0] wa, input wire [63:0] wd, input wire [6:0] ra,
                      output wire [63:0] q);
    ot_v41_pqc_rom2_model #(.AW(7), .DW(64)) u (.*);
endmodule
module ot_pqc_t_ctl16 (
    input  wire clk, rst_n,
    output wire aq_vin, input wire [1:0] aqf, output wire [4:0] aqi_o, output wire ba_v_o, output wire [2:0] ba_blk_o,
    output wire [47:0] hw_o, output wire [35:0] h_hi_o, output wire [15:0] h_b0_o, h_b1_o, output wire [457:0] mdr_o,
    input  wire [1:0] q2f_i, input wire [31:0] ga_i, output wire [605:0] bc_hr_o,
    input  wire go, input wire [5:0] i_ph, input wire [2:0] i_np, input wire [18:0] i_xbase, i_xps, i_obase, i_ops,
    input  wire [1:0] i_fmt, output wire ready, idle, x_re, output wire [18:0] x_addr, input wire x_rv, f_fault,
    output wire fault, output wire [31:0] phase_cycles, output wire ev_go, ev_end, output wire [1:0] ev_tag,
    output wire [6:0] rom_pa0, rom_pa1, input wire [63:0] rom_pq0, rom_pq1, output wire [7:0] rom_sa,
    input  wire [47:0] rom_sq);
    ot_v41_pqc_ctl #(.PHW(6), .SAW(8), .R(16), .VAW(19), .VRD(64), .KMAX(256), .BST(2), .PQ(1), .XRV(1), .XCAP(16))
        u (.*);
endmodule
