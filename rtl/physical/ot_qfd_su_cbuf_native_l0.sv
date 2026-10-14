`timescale 1ns/1ps
// Layer0-compatible native TP8/GT3072 CROM address profile.
// Original generic/closed masters are byte-identical. HEAD36 retained; full head
// and remaining layer payload qualification are outstanding.
module qfd_su_cbuf_native_l0 #(parameter integer MUT=0) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        crom_re,
    input  wire [8*24-1:0]   crom_addr,
    input  wire [5:0]        crom_stage,
    output wire [8*64-1:0]   crom_q,
    input  wire [5:0]        stage,
    input  wire              tok_start,
    input  wire [17:0]       tpos,
    input  wire [2:0]        grp,              // strap: lanes 8 grp .. 8 grp + 7
    output wire              st_rdy,
    output wire [5:0]        st_rdy_stage,
    output wire [7:0]        f_re,
    output wire [8*24-1:0]   f_addr,
    output wire [5:0]        f_stage,
    input  wire [8*64-1:0]   f_q,
    input  wire              f_fault,
    input  wire [4:0]        f_lat,            // strap: far ROM strobe -> answer edges at the pins (r22k: 11)
    output wire              fault,
    output wire [1:0]        fault_code
);
`ifndef OT_CBUF_G_MUT
`define OT_CBUF_G_MUT 0
`endif
    reg [2:0] grp_q;                           // strap pin flop
    always @(posedge clk) grp_q <= grp;
    ot_qfd_crom_lbuf #(.SW(8), .QK0(4096), .POST0(4736), .QSCALE(8832), .ROPE0(8833), .OSC0(533121), .DSC0(537217), .END(541313), .QKR(10), .NWIN(138), .HEAD(36), .SRAM(2), .FLP(11), .PINREG(1), .FLS(1), .FLMAX(31), .FLW(5), .RSTR(1), .MUT(MUT)) u_b (
        .clk(clk), .rst_n(rst_n), .crom_re(crom_re), .crom_addr(crom_addr),
        .crom_stage(crom_stage), .crom_q(crom_q), .stage(stage), .tok_start(tok_start), .tpos(tpos),
        .lane_base({18'd0, grp_q, 3'd0}), .st_rdy(st_rdy), .st_rdy_stage(st_rdy_stage), .f_re(f_re), .f_addr(f_addr), .f_stage(f_stage), .f_q(f_q),
        .f_fault(f_fault), .f_lat(f_lat), .fault(fault), .fault_code(fault_code));
endmodule
