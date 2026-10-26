`timescale 1ns/1ps
// New B master: only actual B inputs, root result and fail-closed fault.
// GO is the explicit command START after the delivered reset is ready. The
// native source builder adds parallel one-edge local reset captures to every
// reset-control block. GO at the first ready edge is accepted; earlier GO
// raises a sticky protocol fault. No payload register is reset here.
// HEADB4 (2026-10-25): `go` is captured by ONE pin register go_q (unreset
// payload-style pin flop, single load on the port) and both the protocol check
// and the command start are derived from go_q against ready_d (= ready one edge
// later, so the accept/fault decision is the same as for the unregistered pin).
// Static schedule: GO is accepted one edge later than v3 (+1 cycle at GO); the
// x contract of u_m moves with it: physical word a at G+6+a (was G+5+a), first
// root at +1. o_v/fault leave ov_q/fault_q directly (no keep on these
// single-copy reset-flop wires: the kept alias hung a buffer off the port net).
module ot_s81hd_elemB_l4_native #(parameter INSTANCE="") (
    input wire clk, rst_n, go,
    input wire [255:0] x,
    output wire o_v,
    output wire [31:0] o_d,
    output wire fault
);
    reg go_q;
    always @(posedge clk) go_q <= go;
    reg ready, ready_d, early_start;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin ready<=1'b0; ready_d<=1'b0; end else begin ready<=1'b1; ready_d<=ready; end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) early_start<=1'b0; else if(go_q && !ready_d) early_start<=1'b1;
    wire mv,mf;wire [31:0] md;
    wire command_go;
`ifdef OT_S81HD_MUT_START_EARLY
    assign command_go=go_q;
`else
    assign command_go=go_q && ready_d;
`endif
    ot_s81hd_elem #(.LV(6),.PAD(2),.JOIN(0),.ROWS(128),.CUT(9'h1ff),.SPLIT9(1),
        .FADD_L4(1),.IOREG(1),.SAFE(1),.INSTANCE(INSTANCE)) u_m (
        .clk(clk),.rst_n(rst_n),.go(command_go),.x(x),.row0(17'd0),.b_v(1'b0),.b_d(32'd0),
        .o_v(mv),.o_d(md),.fault(mf),.l_v(),.l_d(),.head_v(),.head_d(),.head_row(),
        .done(),.best_row(),.best_bits(),.best_key());
    reg ov_q, fault_q;
    (* keep="yes" *) reg [31:0] od_q;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin ov_q<=1'b0;fault_q<=1'b0;end
        else begin ov_q<=ready && mv;fault_q<=early_start || (ready && mf);end
    always @(posedge clk) od_q<=md;
    assign o_v=ov_q;assign o_d=od_q;assign fault=fault_q;
endmodule
