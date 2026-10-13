// Qwen ROM TP8 die: the four slot-shaped corridor cells of contract v3 (results/arch/hier_contract_1012/qwen_rom_tp8.json),
// each hardened ONCE under its die master name so the die binds the view by name (LEF + ETM of the cell itself):
//
//   qfd_cst_s    corridor station, south half   in  a (N)   out b (S), tap (W)       384 instances
//   qfd_cst_n    corridor station, north half   in  b (S)   out a (N), tap (W)       384 instances
//   qfd_chead_w  column head, west chain        in  e (E)   out w (W), n (N), s (S)   24 instances
//   qfd_chead_e  column head, east chain        in  w (W)   out e (E), n (N), s (S)   24 instances
//
// Flow directions: tools/qwen_die_seam/extract.py (OUTP) and the head chains of tools/qwen_rom_fulldie.py.
// A contract bundle x[508:0] is x_d[507:0] (data, flow direction) + x_r (ready, against the flow): one RTL port
// cannot carry both directions, so every bundle is the port pair x_d / x_r on the bundle's face.
// The body is ot_qwen_die_station unchanged: every data output its own kept flop copy of the input word (a pure
// one-cycle delay), every ready captured at its pin and the AND registered at the upstream pin (two cycles).
// Every port is register-at-the-pin; 1,020 (station) / 1,528 (head) clock sinks on the one root ck.
//
// OT_QFD_STATION_MUT (bench mutant only, never synthesized): one tap / north data bit inverted.
`ifdef OT_QFD_STATION_MUT
  `define OT_QFD_STATION_MUTX(w) ({{((w)-1){1'b0}}, 1'b1} << 77)
`else
  `define OT_QFD_STATION_MUTX(w) {(w){1'b0}}
`endif

module qfd_cst_s #(parameter integer DW = 508) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [DW-1:0] a_d,
    output wire          a_r,
    output wire [DW-1:0] b_d,
    input  wire          b_r,
    output wire [DW-1:0] tap_d,
    input  wire          tap_r
);
    wire [DW-1:0] t;
    wire          c_nc;
    ot_qwen_die_station #(.DW(DW), .TAP(1), .SPLIT(0)) u_st (.clk(ck), .rst_n(rst_n), .a_d(a_d), .a_r(a_r),
        .b_d(b_d), .b_r(b_r), .t_d(t), .t_r(tap_r), .c_d(c_nc), .c_r(1'b1));
    assign tap_d = t ^ `OT_QFD_STATION_MUTX(DW);
endmodule

module qfd_cst_n #(parameter integer DW = 508) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [DW-1:0] b_d,
    output wire          b_r,
    output wire [DW-1:0] a_d,
    input  wire          a_r,
    output wire [DW-1:0] tap_d,
    input  wire          tap_r
);
    wire [DW-1:0] t;
    wire          c_nc;
    ot_qwen_die_station #(.DW(DW), .TAP(1), .SPLIT(0)) u_st (.clk(ck), .rst_n(rst_n), .a_d(b_d), .a_r(b_r),
        .b_d(a_d), .b_r(a_r), .t_d(t), .t_r(tap_r), .c_d(c_nc), .c_r(1'b1));
    assign tap_d = t ^ `OT_QFD_STATION_MUTX(DW);
endmodule

module qfd_chead_w #(parameter integer DW = 508) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [DW-1:0] e_d,
    output wire          e_r,
    output wire [DW-1:0] w_d,
    input  wire          w_r,
    output wire [DW-1:0] n_d,
    input  wire          n_r,
    output wire [DW-1:0] s_d,
    input  wire          s_r
);
    wire [DW-1:0] t;
    ot_qwen_die_station #(.DW(DW), .TAP(1), .SPLIT(1)) u_st (.clk(ck), .rst_n(rst_n), .a_d(e_d), .a_r(e_r),
        .b_d(w_d), .b_r(w_r), .t_d(t), .t_r(n_r), .c_d(s_d), .c_r(s_r));
    assign n_d = t ^ `OT_QFD_STATION_MUTX(DW);
endmodule

module qfd_chead_e #(parameter integer DW = 508) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [DW-1:0] w_d,
    output wire          w_r,
    output wire [DW-1:0] e_d,
    input  wire          e_r,
    output wire [DW-1:0] n_d,
    input  wire          n_r,
    output wire [DW-1:0] s_d,
    input  wire          s_r
);
    wire [DW-1:0] t;
    ot_qwen_die_station #(.DW(DW), .TAP(1), .SPLIT(1)) u_st (.clk(ck), .rst_n(rst_n), .a_d(w_d), .a_r(w_r),
        .b_d(e_d), .b_r(e_r), .t_d(t), .t_r(n_r), .c_d(s_d), .c_r(s_r));
    assign n_d = t ^ `OT_QFD_STATION_MUTX(DW);
endmodule
