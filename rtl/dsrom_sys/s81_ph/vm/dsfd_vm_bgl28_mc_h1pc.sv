// Fixed no-ACK physical interface of the default-off H1 pin-copy probe.
module dsfd_vm_bgl28_mc_h1pc #(parameter integer FORWARD_HOP = 0, parameter integer PIN_OUTPUT_COPY = 0) (
    input wire ck, input wire ck_req, input wire ck_ret, input wire [0:0] rs, input wire [1:0] grp, input wire [2:0] bi,
    input  wire [27:0] i_v, input wire [27:0] i_we, input wire [28*14-1:0] i_row, input wire [28*4-1:0] i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0] f_v, output wire [27:0] f_we, output wire [28*14-1:0] f_row, output wire [28*4-1:0] f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0] r_v, input wire [10*128-1:0] r_d, input wire [3:0] r_f, input wire [2:0] r_o,
    output wire [9:0] o_v, output wire [10*128-1:0] o_d, output wire [3:0] o_f, output wire [2:0] o_o
);
`ifdef OT_VMBGL_FLOPMEM
    localparam integer MACRO = 0;
`else
    localparam integer MACRO = 1;
`endif
    dsfd_vm_bgl #(.NP(28), .NPR(10), .NB(32), .NBL(8), .QD(4), .RQ(8), .MACRO(MACRO), .DW(128), .CLOCK_SPLIT(1), .BAL_PREFIX(0), .PREHIT(1), .FAST4(1), .FORWARD_HOP(FORWARD_HOP), .PIN_OUTPUT_COPY(PIN_OUTPUT_COPY)) u (
        .ck(ck), .ck_req(ck_req), .ck_ret(ck_ret), .rs(rs), .grp(grp), .bi(bi), .i_v(i_v), .i_we(i_we), .i_row(i_row), .i_mask(i_mask), .i_d(i_d),
        .f_v(f_v), .f_we(f_we), .f_row(f_row), .f_mask(f_mask), .f_d(f_d), .r_v(r_v), .r_d(r_d), .r_f(r_f), .r_o(r_o),
        .o_v(o_v), .o_d(o_d), .o_f(o_f), .o_o(o_o)
    );
endmodule
