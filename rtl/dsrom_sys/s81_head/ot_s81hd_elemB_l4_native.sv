`timescale 1ns/1ps
// New B master: only actual B inputs, root result and fail-closed fault.
// GO is the explicit command START after the delivered reset is ready. The
// native source builder adds parallel one-edge local reset captures to every
// reset-control block. GO at the first ready edge is accepted; earlier GO
// raises a sticky protocol fault. No payload register is reset here.
module ot_s81hd_elemB_l4_native #(parameter INSTANCE="") (
    input wire clk, rst_n, go,
    input wire [255:0] x,
    output wire o_v,
    output wire [31:0] o_d,
    output wire fault
);
    reg ready, early_start;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) ready<=1'b0; else ready<=1'b1;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) early_start<=1'b0; else if(go && !ready) early_start<=1'b1;
    wire mv,mf;wire [31:0] md;
    wire command_go;
`ifdef OT_S81HD_MUT_START_EARLY
    assign command_go=go;
`else
    assign command_go=go && ready;
`endif
    ot_s81hd_elem #(.LV(6),.PAD(2),.JOIN(0),.ROWS(128),.CUT(9'h1ff),.SPLIT9(1),
        .FADD_L4(1),.IOREG(1),.SAFE(1),.INSTANCE(INSTANCE)) u_m (
        .clk(clk),.rst_n(rst_n),.go(command_go),.x(x),.row0(17'd0),.b_v(1'b0),.b_d(32'd0),
        .o_v(mv),.o_d(md),.fault(mf),.l_v(),.l_d(),.head_v(),.head_d(),.head_row(),
        .done(),.best_row(),.best_bits(),.best_key());
    (* keep="yes" *) reg ov_q, fault_q;
    (* keep="yes" *) reg [31:0] od_q;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin ov_q<=1'b0;fault_q<=1'b0;end
        else begin ov_q<=ready && mv;fault_q<=early_start || (ready && mf);end
    always @(posedge clk) od_q<=md;
    assign o_v=ov_q;assign o_d=od_q;assign fault=fault_q;
endmodule
