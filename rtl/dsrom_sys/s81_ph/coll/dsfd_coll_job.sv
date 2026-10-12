`timescale 1ns/1ps
// dsfd_coll_job (s81-ctl-1011, 2026-10-11): the coll engine endpoint TILE of the split3cr collective slab
// (ADAPTER_CONTRACT_1011 engine 3; physical/s81_ph_views/ports/contract/dsfd_coll_job, tools/s81_ph/s81_ph_coll_job_plan.py).
// A thin row under dsfd_coll_cb (the slab's VM-side tile) at the slab's S edge, so the closed cb stays unchanged:
//   S face (slab edge): f_vm 592 in, t_vm 2100 out, c_cmd 85 in, c_done 9 out, c_st 2 out, ck / rs
//   N face (abuts cb's S face): cf_vm 592 out (to cb f_vm), ct_vm 2100 in (from cb t_vm)
// f_vm: pin flop -> ot_s81_coll_job release mux (records held until their coll descriptor; cut-through) -> cf_vm, captured
// by cb's own f_vm pin flop: +1 cycle on f_vm.  t_vm: a feedthrough of cb's output flops (+0); the endpoint observes its
// header [13:0] (the beat is on the slab's VM-edge pins that cycle: a done is never early).
// Controller clock = the die stream clock (ck), as every slab endpoint.
// Flow control unchanged: t_vm adds no stage (the VM CDC end block's room rule stays room >= 4).
module dsfd_coll_job #(parameter integer MUT = `ifdef OT_S81PH_COLL_JOB_MUT `OT_S81PH_COLL_JOB_MUT `else 0 `endif) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rs,
    input  wire [591:0]  f_vm,
    output wire [591:0]  cf_vm,
    input  wire [2099:0] ct_vm,
    output wire [2099:0] t_vm,
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st
);
    reg [1:0] rs_s;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rs_s <= 2'b00; else rs_s <= {rs_s[0], 1'b1};
    wire rn = rs_s[1];
    reg [591:0] fv_q;
    always @(posedge ck[0] or negedge rn) if (!rn) fv_q <= 592'd0; else fv_q <= f_vm;
    assign t_vm = ct_vm;            // feedthrough: cb launches t_vm from its output flops (the slab's VM-edge pins)
    wire jf;
    ot_s81_coll_job #(.MUT(MUT)) u_job (.c_clk(ck[0]), .c_rst_n(rs[0]), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .ck(ck[0]), .rs_n(rn), .vm_f(fv_q), .core_f(cf_vm), .core_h(ct_vm[13:0]), .fault(jf));
endmodule
