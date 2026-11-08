`timescale 1ns/1ps
// Private KV Wi form. Exactly one input pin cycle on BOTH ordered half streams.
// The native join has valid-only ingress: it has no ready or credit interface.
module ot_kv_fdi_join_rf #(
    parameter integer WA = 522,
    parameter integer WB = 521,
    parameter integer DEPTH = 16,
    parameter integer MUT = 0
) (
    input wire clk, rst_n,
    input wire a_v,
    input wire [WA-1:0] a_d,
    input wire b_v,
    input wire [WB-1:0] b_d,
    output wire o_v,
    output wire [WA+WB-1:0] o_d
);
    (* keep = "true", face_keep = 1 *) reg a_v_q, b_v_q;
    (* keep = "true", face_keep = 1 *) reg [WA-1:0] a_d_q;
    (* keep = "true", face_keep = 1 *) reg [WB-1:0] b_d_q;
    always @(posedge clk) begin
        a_d_q <= a_d;
        b_d_q <= b_d;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin a_v_q <= 1'b0; b_v_q <= 1'b0; end
        else begin a_v_q <= a_v; b_v_q <= b_v; end
    end
    wire native_v;
    wire [WA+WB-1:0] native_d;
    (* keep_hierarchy = "yes" *) ot_fdi_join2 #(.WA(WA), .WB(WB), .DEPTH(DEPTH)) u_native (
        .clk(clk), .rst_n(rst_n), .a_v(a_v_q), .a_d(a_d_q),
        .b_v((MUT == 2) ? b_v : b_v_q), .b_d(b_d_q),
        .o_v(native_v), .o_d(native_d)
    );
    assign o_v = native_v;
    assign o_d = (MUT == 1) ? (native_d ^ {{(WA+WB-1){1'b0}}, 1'b1}) : native_d;
endmodule
