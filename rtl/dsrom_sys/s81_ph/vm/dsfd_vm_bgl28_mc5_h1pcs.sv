// Separate physical master with S-face output clock entries; same MC5 RTL/cycles.
// Fixed unconditional no-ACK physical intake interface.
module dsfd_vm_bgl28_mc5_h1pcs (
    input wire ck, input wire ck_req, input wire ck_ret, input wire ck_fwd0, input wire ck_fwd1, input wire [0:0] rs, input wire [1:0] grp, input wire [2:0] bi,
    input  wire [27:0] i_v, input wire [27:0] i_we, input wire [28*14-1:0] i_row, input wire [28*4-1:0] i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0] f_v, output wire [27:0] f_we, output wire [28*14-1:0] f_row, output wire [28*4-1:0] f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0] r_v, input wire [10*128-1:0] r_d, input wire [3:0] r_f, input wire [2:0] r_o,
    output wire [9:0] o_v, output wire [10*128-1:0] o_d, output wire [3:0] o_f, output wire [2:0] o_o
);
    dsfd_vm_bgl28_mc5 u_leaf (
        .ck(ck),
        .ck_req(ck_req),
        .ck_ret(ck_ret),
        .ck_fwd0(ck_fwd0),
        .ck_fwd1(ck_fwd1),
        .rs(rs),
        .grp(grp),
        .bi(bi),
        .i_v(i_v),
        .i_we(i_we),
        .i_row(i_row),
        .i_mask(i_mask),
        .i_d(i_d),
        .f_v(f_v),
        .f_we(f_we),
        .f_row(f_row),
        .f_mask(f_mask),
        .f_d(f_d),
        .r_v(r_v),
        .r_d(r_d),
        .r_f(r_f),
        .r_o(r_o),
        .o_v(o_v),
        .o_d(o_d),
        .o_f(o_f),
        .o_o(o_o)
    );
endmodule
