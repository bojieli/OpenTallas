`timescale 1ns/1ps
`default_nettype none
// Independent physical landing lane: one clock root, local input/output register banks and arm state.
// This candidate preserves the monolithic PINREG=1 age2 and startup, with four times replicated arm/reset capture.
// No arbitration, FIFO or ready; every valid input owns its statically assigned write edge.
module dsfd_vm_static_landing_lane #(parameter integer LANE=0) (
    input wire ck, rst_n,
    input wire larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input wire i_v, input wire [511:0] i_d,
    output reg o_v, output reg [13:0] o_row, output reg [511:0] o_d,
    output reg [2:0] fault
);
    reg rst_q; reg [1:0] rr; wire rn=rr[1];
    reg rn_d, p_larm_v, p_i_v; reg [3:0] p_larm_g; reg [13:0] p_larm_base;
    reg [511:0] p_d; reg armed; reg [14:0] nxt;
    always @(posedge ck) begin
        rst_q <= rst_n;
        if (!rst_q) rr <= 2'b00; else rr <= {rr[0],1'b1};
        rn_d <= rn;
        p_larm_v <= larm_v; p_larm_g <= larm_g; p_larm_base <= larm_base;
        p_i_v <= i_v; p_d <= i_d; o_d <= p_d;
    end
    wire q_larm_v = p_larm_v & rn_d;
`ifdef OT_VM_LANDING_LANE_MUT_ROWSKEW
    wire rv = i_v;
`else
    wire rv = p_i_v & rn_d;
`endif
    localparam [3:0] GROUP = (LANE < 2) ? 4'd0 : (LANE == 2 ? 4'd5 : 4'd6);
    localparam [14:0] OFFSET = (LANE == 1) ? 15'd1 : 15'd0;
    localparam [14:0] STRIDE = (LANE < 2) ? 15'd2 : 15'd1;
    always @(posedge ck) begin
        if (!rn) begin armed<=1'b0; o_v<=1'b0; fault<=3'b0; end
        else begin
            if (q_larm_v && p_larm_g!=0 && p_larm_g!=5 && p_larm_g!=6) fault[2]<=1'b1;
            o_v <= rv && armed && nxt<15'd16384;
            o_row <= nxt[13:0];
            if (rv && !armed) fault[0]<=1'b1;
            if (rv && armed && nxt>=15'd16384) fault[1]<=1'b1;
`ifdef OT_VM_LANDING_LANE_MUT_STRIDE
            if (rv && armed) nxt <= nxt + 15'd3;
`else
            if (rv && armed) nxt <= nxt + STRIDE;
`endif
            if (q_larm_v && p_larm_g==GROUP) begin armed<=1'b1; nxt<={1'b0,p_larm_base}+OFFSET; end
        end
    end
endmodule

// Thin composition only; these four clocks are phase-aligned die-delivered independent physical roots.
// Parent adoption and its four-bit clock ABI require the routed views and die pin grant.
module dsfd_vm_static_landing_split (
    input wire [3:0] ck, input wire rst_n,
    input wire larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input wire [3:0] i_v, input wire [1023:0] i_d01, i_d23,
    output wire [3:0] o_v, output wire [55:0] o_row,
    output wire [1023:0] o_d01, o_d23, output wire [2:0] fault
);
    wire [2:0] f[0:3]; wire [2047:0] d={i_d23,i_d01}; wire [2047:0] q;
    dsfd_vm_static_landing_lane0 u_lane0(.ck(ck[0]),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v[0]),.i_d(d[0+:512]),
        .o_v(o_v[0]),.o_row(o_row[0+:14]),.o_d(q[0+:512]),.fault(f[0]));
    dsfd_vm_static_landing_lane1 u_lane1(.ck(ck[1]),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v[1]),.i_d(d[512+:512]),
        .o_v(o_v[1]),.o_row(o_row[14+:14]),.o_d(q[512+:512]),.fault(f[1]));
    dsfd_vm_static_landing_lane2 u_lane2(.ck(ck[2]),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v[2]),.i_d(d[1024+:512]),
        .o_v(o_v[2]),.o_row(o_row[28+:14]),.o_d(q[1024+:512]),.fault(f[2]));
    dsfd_vm_static_landing_lane3 u_lane3(.ck(ck[3]),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v[3]),.i_d(d[1536+:512]),
        .o_v(o_v[3]),.o_row(o_row[42+:14]),.o_d(q[1536+:512]),.fault(f[3]));
    assign o_d01=q[1023:0]; assign o_d23=q[2047:1024];
    assign fault=f[0]|f[1]|f[2]|f[3];
endmodule
// Actual hardened master for lane0; each master has its own source-pinned routed view.
module dsfd_vm_static_landing_lane0 (
    input wire ck, rst_n,
    input wire larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input wire i_v, input wire [511:0] i_d,
    output wire o_v, output wire [13:0] o_row, output wire [511:0] o_d,
    output wire [2:0] fault
);
    dsfd_vm_static_landing_lane #(.LANE(0)) u_lane(.ck(ck),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v),.i_d(i_d),
        .o_v(o_v),.o_row(o_row),.o_d(o_d),.fault(fault));
endmodule

// Actual hardened master for lane1; each master has its own source-pinned routed view.
module dsfd_vm_static_landing_lane1 (
    input wire ck, rst_n,
    input wire larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input wire i_v, input wire [511:0] i_d,
    output wire o_v, output wire [13:0] o_row, output wire [511:0] o_d,
    output wire [2:0] fault
);
    dsfd_vm_static_landing_lane #(.LANE(1)) u_lane(.ck(ck),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v),.i_d(i_d),
        .o_v(o_v),.o_row(o_row),.o_d(o_d),.fault(fault));
endmodule

// Actual hardened master for lane2; each master has its own source-pinned routed view.
module dsfd_vm_static_landing_lane2 (
    input wire ck, rst_n,
    input wire larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input wire i_v, input wire [511:0] i_d,
    output wire o_v, output wire [13:0] o_row, output wire [511:0] o_d,
    output wire [2:0] fault
);
    dsfd_vm_static_landing_lane #(.LANE(2)) u_lane(.ck(ck),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v),.i_d(i_d),
        .o_v(o_v),.o_row(o_row),.o_d(o_d),.fault(fault));
endmodule

// Actual hardened master for lane3; each master has its own source-pinned routed view.
module dsfd_vm_static_landing_lane3 (
    input wire ck, rst_n,
    input wire larm_v, input wire [3:0] larm_g, input wire [13:0] larm_base,
    input wire i_v, input wire [511:0] i_d,
    output wire o_v, output wire [13:0] o_row, output wire [511:0] o_d,
    output wire [2:0] fault
);
    dsfd_vm_static_landing_lane #(.LANE(3)) u_lane(.ck(ck),.rst_n(rst_n),
        .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v),.i_d(i_d),
        .o_v(o_v),.o_row(o_row),.o_d(o_d),.fault(fault));
endmodule

`default_nettype wire
