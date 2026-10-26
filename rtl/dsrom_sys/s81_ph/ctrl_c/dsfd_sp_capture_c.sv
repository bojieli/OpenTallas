`timescale 1ns/1ps
// dsfd_sp_capture_c (s81-ctl-1011, 2026-10-11): the capture slab master with the fld DONE source for
// dsfd_sp_gather_c (ADAPTER_CONTRACT_1011 v2, non-PQ dies; generator --ctrl-adapters).  = dsfd_sp_capture UNCHANGED +
// t_cd = {toggle, fault, phase 10} (serial domain, from flops): the toggle flips when the capture's status lane shows
// phase_drained rising (st[2]) after the phase was live (st[0]); phase = st[13:4] (held phase id), fault = st[3] (sticky in the capture).  Real
// completion: drained = every root's quota of the phase written to the VM side.
module dsfd_sp_capture_c #(parameter integer LD = 4) (
    input wire [0:0] ck, input wire [0:0] rst, input wire [0:0] ckv, input wire [0:0] rsv,
    input wire [6946:0] f_gather,
    output wire [13375:0] t_vm,
    output reg [11:0] t_cd
);
    dsfd_sp_capture #(.LD(LD)) u_c (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(f_gather), .t_vm(t_vm));
    reg [1:0] rv_s;
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rv_s <= 2'b00; else rv_s <= {rv_s[0], 1'b1};
    wire [63:0] st = t_vm[13312 +: 64];
    // a drained event belongs to a phase that went live: the status lane's drained rises after reset too (the capture
    // resets drained), which is not a phase completion -- armed by phase_live (st[0], held >= 14 cycles), cleared by the event
    reg dr_q, armed;
    always @(posedge ckv[0] or negedge rv_s[1])
        if (!rv_s[1]) begin dr_q <= 1'b0; armed <= 1'b0; t_cd <= 12'd0; end
        else begin
            dr_q <= st[2];
            t_cd[10] <= st[3];
            if (st[0]) armed <= 1'b1;
            if (st[2] && !dr_q && armed && !st[0]) begin t_cd[9:0] <= st[13:4]; t_cd[11] <= ~t_cd[11]; armed <= 1'b0; end
        end
endmodule
