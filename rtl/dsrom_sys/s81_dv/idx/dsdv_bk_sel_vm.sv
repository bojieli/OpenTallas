`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// DRIVE-S81-IDX4 (10-20, MU.BAL.SX.3 / S81.BIND.2.P, dv_plan --idxrd 4): bk_sel master with the index ingress merge.
// dsdv_bk_sel_vm = dsdv_idx_vmux (dsdv_idx_tree.sv, unchanged) in front of dsdv_bk_sel (unchanged) vi_s:
//   i_r = vi_s    the column-4 rung from s_4S (tvN_s_4S, unchanged traffic, compiled slots)
//   i_s = vi_idx  the score-chain tail (is_tail: irg_07 so, relayed)
//   i_a = ca, i_b = cb  the two landed rank-tree child lanes (off-die tree links: die ports, lower_bk shard_tree;
//                 a die with no child gets its idle lane as a declared pad)
//   o -> u_sel.vi_s.  OR of registered inputs, 2 edges pin -> pin (the rung into bk_sel +2 edges: compiler SLAT);
//   two valid beats in one cycle = sticky vm_fault (a compile error), a separate status output (die status port).
// Same ports as dsdv_bk_sel plus vi_idx / ca / cb / vm_fault.  No credit / ready on any port.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_bk_sel_vm #(
    parameter integer V   = 276,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,
    input  wire [V-1:0]  vi_s,
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,
    output wire [V-1:0]  vo_s,
    input  wire [V-1:0]  vi_idx,
    input  wire [V-1:0]  ca,
    input  wire [V-1:0]  cb,
    output wire          fault,
    output wire          vm_fault
);
    wire [V-1:0] vi_m;
    dsdv_idx_vmux #(.V(V)) u_vm (.ck(clk), .rst(rst_n), .i_r(vi_s), .i_s(vi_idx), .i_a(ca), .i_b(cb), .o(vi_m), .fault(vm_fault));
    dsdv_bk_sel #(.V(V), .MUT(MUT)) u_sel (.clk(clk), .rst_n(rst_n), .tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek),
        .uid(uid), .eg_n(eg_n), .vi_s(vi_m), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .fault(fault));
endmodule
