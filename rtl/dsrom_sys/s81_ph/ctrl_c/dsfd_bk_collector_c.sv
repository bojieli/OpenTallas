`timescale 1ns/1ps
// dsfd_bk_collector_c (s81-ctl-1011, 2026-10-11): the collector slab master WITH the col (engine 6) command / done
// endpoint (ADAPTER_CONTRACT_1011 v2; generator --ctrl-adapters).  = dsfd_bk_collector UNCHANGED + ot_s81_done_word:
// the descriptor arms the job (arg[7:0] = job tag); done = the collector's ONE DONE word of the job (emitted when all
// four stacks' DONE heads are present with equal tags, after every frame they sent before it), tag [507:500] checked.
module dsfd_bk_collector_c (
    input wire [514:0] cNE, input wire [514:0] cNW, input wire [514:0] cSE, input wire [514:0] cSW,
    input wire [0:0] ck, input wire [0:0] rst,
    output wire [513:0] vd,
    output wire [0:0] vf,
    input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st
);
    dsfd_bk_collector u_c (.cNE(cNE), .cNW(cNW), .cSE(cSE), .cSW(cSW), .ck(ck), .rst(rst), .vd(vd), .vf(vf));
    // the endpoint TILE dsfd_dw_ep_c (rtl/dsrom_sys/s81_ctrl/dsfd_dw_ep.sv) on a snoop of vd
    dsfd_dw_ep_c u_dw (.ck(ck), .rst(rst), .vh({vd[513:502], vd[493:482], vd[1], vd[0]}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
endmodule
