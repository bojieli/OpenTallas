`timescale 1ns/1ps
`default_nettype none
// Native ABI successor: distinct master; no inherited strap physical view.
module hfd_vms_bank_native_q2(
    input wire [16:0] rq0,
    output wire [256:0] rr0,
    input wire [16:0] rq1,
    output wire [256:0] rr1,
    input wire [16:0] rq2,
    output wire [256:0] rr2,
    input wire [16:0] rq3,
    output wire [256:0] rr3,
    input wire [16:0] rq4,
    output wire [256:0] rr4,
    input wire [280:0] wq0,
    output wire wq_done0,
    input wire [280:0] wq1,
    output wire wq_done1,
    input wire [280:0] wq2,
    output wire wq_done2,
strap identity: bid / sid pins, die constants per instance; 8 banks = 1 master). Literal physical ABI, valid-select static bank core (H-ELEM-A r2 2026-10-15, successor of hfd_vms_bank_ft_rg6wg3
);
 wire [1284:0] rr;wire [2:0] wq_done;
 assign rr0=rr[0+:257];
 assign rr1=rr[257+:257];
 assign rr2=rr[514+:257];
 assign rr3=rr[771+:257];
 assign rr4=rr[1028+:257];
 assign wq_done0=wq_done[0];
 assign wq_done1=wq_done[1];
 assign wq_done2=wq_done[2];
 ot_vms_bank_static_strap #(.RG(5),.WG(3)) bank(
,
 .rq({rq4,rq3,rq2,rq1,rq0}),.rr(rr),
 .wq({wq2,wq1,wq0}),.wq_done(wq_done));
endmodule
`default_nettype wire
