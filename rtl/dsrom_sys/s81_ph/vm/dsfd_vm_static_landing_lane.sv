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
    genvar l;
    generate for(l=0;l<4;l=l+1) begin:g_lane
        dsfd_vm_static_landing_lane #(.LANE(l)) u_lane(.ck(ck[l]),.rst_n(rst_n),
            .larm_v(larm_v),.larm_g(larm_g),.larm_base(larm_base),.i_v(i_v[l]),.i_d(d[512*l+:512]),
            .o_v(o_v[l]),.o_row(o_row[14*l+:14]),.o_d(q[512*l+:512]),.fault(f[l]));
    end endgenerate
    assign o_d01=q[1023:0]; assign o_d23=q[2047:1024];
    assign fault=f[0]|f[1]|f[2]|f[3];
endmodule
`default_nettype wire
