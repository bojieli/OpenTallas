`timescale 1ns/1ps
// dsfd_bk_selector_c (s81-ctl-1011, 2026-10-11): the selector slab master WITH the sel (engine 5) command / done
// endpoint (ADAPTER_CONTRACT_1011 v2; generator --ctrl-adapters).  = dsfd_bk_selector UNCHANGED + ot_s81_slab_ep (JQ 2).
// The selector's input lanes are valid-only (no back-pressure): its work is issued in-band by the VM's scans, so the
// descriptor ARMS the job ahead of its data and carries the segment tag (arg[7:0]).
//   start: descriptor accepted into the job queue (e_inputs_present = the slab is out of reset: vd[0], its rst_n);
//   done : the selector's DONE word (vd type 4) of the job, tag [507:500] == the head descriptor's arg[7:0]
//          (mismatch = fault, no done).  The DONE word sent once after reset (count 0) precedes any job and is not a
//          completion.  A DONE with no armed job is a fault (ep j_done with an empty queue).
// Done latency: +1 (vd snoop flop) + the adapter's.  The vd lane to the VM is unchanged.
module dsfd_bk_selector_c (
    input wire [0:0] ck,
    input wire [514:0] iNE, input wire [514:0] iNW, input wire [514:0] iSE, input wire [514:0] iSW,
    input wire [0:0] rst,
    output wire [513:0] vd,
    output wire [0:0] vf,
    input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st
);
    dsfd_bk_selector u_s (.ck(ck), .iNE(iNE), .iNW(iNW), .iSE(iSE), .iSW(iSW), .rst(rst), .vd(vd), .vf(vf));
    // the endpoint TILE dsfd_dw_ep_s (rtl/dsrom_sys/s81_ctrl/dsfd_dw_ep.sv) on a snoop of vd
    dsfd_dw_ep_s u_dw (.ck(ck), .rst(rst), .vh({vd[513:502], vd[493:482], vd[1], vd[0]}), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st));
endmodule
