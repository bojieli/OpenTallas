`timescale 1ns/1ps
`default_nettype none
// Native candidate composition: five ACTUAL hard masters and wires only, with five independent die clock roots.
// The old dsfd_vm_static_landing_split is only the historical functional equivalence vehicle (its fault OR is soft).
// Data remains age2 / II1; joined diagnostic faults have two additional edges. No production/default adoption.
module dsfd_vm_static_landing_joined (
    input wire [4:0] ck, input wire rst_n,
    input wire larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input wire [3:0] i_v, input wire [1023:0] i_d01, i_d23,
    output wire [3:0] o_v, output wire [55:0] o_row,
    output wire [1023:0] o_d01, o_d23, output wire [2:0] fault
);
    wire [11:0] f; wire [2047:0] d={i_d23,i_d01}; wire [2047:0] q;
    dsfd_vm_static_landing_lane0 u_lane0(.ck(ck[0]),.rst_n(rst_n),.larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),
        .i_v(i_v[0]),.i_d(d[0+:512]),.o_v(o_v[0]),.o_row(o_row[0+:14]),.o_d(q[0+:512]),.fault(f[0+:3]));
    dsfd_vm_static_landing_lane1 u_lane1(.ck(ck[1]),.rst_n(rst_n),.larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),
        .i_v(i_v[1]),.i_d(d[512+:512]),.o_v(o_v[1]),.o_row(o_row[14+:14]),.o_d(q[512+:512]),.fault(f[3+:3]));
    dsfd_vm_static_landing_lane2 u_lane2(.ck(ck[2]),.rst_n(rst_n),.larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),
        .i_v(i_v[2]),.i_d(d[1024+:512]),.o_v(o_v[2]),.o_row(o_row[28+:14]),.o_d(q[1024+:512]),.fault(f[6+:3]));
    dsfd_vm_static_landing_lane3 u_lane3(.ck(ck[3]),.rst_n(rst_n),.larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),
        .i_v(i_v[3]),.i_d(d[1536+:512]),.o_v(o_v[3]),.o_row(o_row[42+:14]),.o_d(q[1536+:512]),.fault(f[9+:3]));
    dsfd_vm_static_landing_fault_join u_fault(.ck(ck[4]),.i_fault(f),.o_fault(fault));
    assign o_d01=q[1023:0]; assign o_d23=q[2047:1024];
endmodule
`default_nettype wire
