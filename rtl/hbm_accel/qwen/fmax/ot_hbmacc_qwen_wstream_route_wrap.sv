`timescale 1ps/1fs
// Route-only parameter-free tops of the HA8 prefetch stream (vehicle parameters ENABLE=1 NSTK=4 REF_MODE=1 WINW=160
// SPW=24 CRED=32): yosys 0.68 asserts while re-deriving a PARAMETERIZED top whose generate loop instantiates the
// 128 differently-parameterized ot_hbm_r14_stream_pc; a fixed top avoids the re-derive.
`define OT_QCW_PORTS \
    input wire clk, input wire rst_n, input wire go, input wire [31:0] cfg_words, input wire [31:0] c_gray, \
    output wire [31:0] a_gray, output wire fault, output wire [31:0] st_cycles, output wire [31:0] st_rd, \
    output wire [31:0] st_room_block, output wire [31:0] st_desc_gap, output wire [31:0] st_words
`define OT_QCW_CONN .clk(clk), .rst_n(rst_n), .go(go), .cfg_words(cfg_words), .c_gray(c_gray), .a_gray(a_gray), \
    .fault(fault), .st_cycles(st_cycles), .st_rd(st_rd), .st_room_block(st_room_block), .st_desc_gap(st_desc_gap), \
    .st_words(st_words)
module ot_qcw_route_base (`OT_QCW_PORTS);
    ot_hbmacc_qwen_wstream #(.ENABLE(1), .NSTK(4), .REF_MODE(1), .WINW(160), .SPW(24), .CRED(32)) u (`OT_QCW_CONN);
endmodule
module ot_qcw_route_f12 (`OT_QCW_PORTS);
    ot_hbmacc_qwen_wstream_f12 #(.ENABLE(1), .NSTK(4), .REF_MODE(1), .WINW(160), .SPW(24), .CRED(32)) u (`OT_QCW_CONN);
endmodule
`undef OT_QCW_PORTS
`undef OT_QCW_CONN
