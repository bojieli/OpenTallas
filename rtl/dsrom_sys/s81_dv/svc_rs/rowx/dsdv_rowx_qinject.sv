// Zero-cycle static ROWX injection before one service entry's existing q pipeline.
// book reserves the WHOLE XM header/payload interval, including idle edges.
// The compiler must suppress normal q throughout that reservation; this is not an arbiter.
module dsdv_rowx_qinject #(parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire book,
    input wire normal_v, input wire [511:0] normal_d,
    input wire rowx_v, input wire [511:0] rowx_d,
    output wire q_v, output wire [511:0] q_d,
    output reg fault
);
    assign q_v = book ? rowx_v : normal_v;
    assign q_d = book ? (rowx_d ^ (MUT == 1 ? 512'd1 : 512'd0)) : normal_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if ((book && normal_v) || (!book && rowx_v)) fault <= 1'b1;
    end
endmodule
