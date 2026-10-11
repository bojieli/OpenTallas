`timescale 1ns/1ps
// dsfd_coll_job (s81-ctl-1011, 2026-10-11): the coll engine endpoint TILE of the split3cr collective slab
// (ADAPTER_CONTRACT_1011 engine 3; physical/s81_ph_views/ports/contract/dsfd_coll_job, tools/s81_ph/s81_ph_coll_job_plan.py).
// A thin row under dsfd_coll_cb (the slab's VM-side tile) at the slab's S edge, so the closed cb stays unchanged:
//   S face (slab edge): f_vm 592 in, t_vm 2100 out, c_cmd 85 in, c_done 9 out, c_st 2 out, ck / rs
//   N face (abuts cb's S face): cf_vm 592 out (to cb f_vm), ct_vm 2100 in (from cb t_vm)
// f_vm: pin flop -> ot_s81_coll_job (records held until their coll descriptor, cut-through +1) -> cf_vm (from its register).
// t_vm: pin flop -> t_vm out flop (+2 cycles on t_vm, +2 on f_vm incl. the endpoint register); the endpoint observes
// the header [13:0] of the t_vm OUTPUT flops (the beat is on the slab pins: a done is never early).
// Controller clock = the die stream clock (ck), as every slab endpoint.
// Flow control: t_vm is sent by the slab when the VM-side CDC end block reports room (ts[0]); this tile puts 2 more
// words in flight, so that end block must report room >= 6 words (was >= 4; CDC depth >= 8 unchanged).
module dsfd_coll_job #(parameter integer MUT = 0) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rs,
    input  wire [591:0]  f_vm,
    output wire [591:0]  cf_vm,
    input  wire [2099:0] ct_vm,
    output reg  [2099:0] t_vm,
    input  wire [84:0]   c_cmd,
    output wire [8:0]    c_done,
    output wire [1:0]    c_st
);
    reg [1:0] rs_s;
    always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rs_s <= 2'b00; else rs_s <= {rs_s[0], 1'b1};
    wire rn = rs_s[1];
    reg [591:0] fv_q; reg [2099:0] tv_q;
    always @(posedge ck[0] or negedge rn)
        if (!rn) begin fv_q <= 592'd0; tv_q <= 2100'd0; t_vm <= 2100'd0; end
        else begin fv_q <= f_vm; tv_q <= ct_vm; t_vm <= tv_q; end
    wire jf;
    ot_s81_coll_job #(.MUT(MUT)) u_job (.c_clk(ck[0]), .c_rst_n(rs[0]), .c_cmd(c_cmd), .c_done(c_done), .c_st(c_st),
        .ck(ck[0]), .rs_n(rn), .vm_f(fv_q), .core_f(cf_vm), .core_h(t_vm[13:0]), .fault(jf));
endmodule
