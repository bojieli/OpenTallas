`timescale 1ns/1ps
// Class-11 branch of the die host dispatcher. RoPE stays on the class-10
// branch. Bind rq[0:32*341-1] to ctrl_SW and the upper half to ctrl_SE;
// concatenate their actual wd ports. This path owns these controllers during
// its boot phase; shared runtime arbitration is outside this boot-only path.
module ot_dsrom_engram_boot_path #(
    parameter integer EXPECT_SECTORS=1
) (
    input wire ck,rst_n,
    input wire i_v,
    input wire [31:0] i_addr,
    input wire [255:0] i_d,
    output wire i_cred,
    output wire [64*341-1:0] rq,
    input wire [63:0] wd,
    output wire ready,fault
);
    wire [1:0] wv,dv;
    wire [28:0] wa;
    wire [2:0] wt;
    wire [255:0] data;
    wire [5:0] dt;
    wire dispatch_ready,dispatch_fault,map_fault;
    ot_dsrom_engram_boot_dispatch #(.EXPECT_SECTORS(EXPECT_SECTORS)) u_dispatch(
        .ck(ck),.rst_n(rst_n),.i_v(i_v),.i_addr(i_addr),.i_d(i_d),.i_cred(i_cred),
        .w_v(wv),.w_atom(wa),.w_tag(wt),.w_d(data),.done_v(dv),.done_tag(dt),
        .ready(dispatch_ready),.fault(dispatch_fault));
    ot_dsrom_engram_boot_ctrl_map u_map(
        .ck(ck),.rst_n(rst_n),.i_v(wv),.i_atom(wa),.i_tag(wt),.i_d(data),
        .rq(rq),.wd(wd),.done_v(dv),.done_tag(dt),.fault(map_fault));
    assign fault=dispatch_fault|map_fault;
    assign ready=dispatch_ready&&!fault;
endmodule
