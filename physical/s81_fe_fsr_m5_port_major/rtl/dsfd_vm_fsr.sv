// Exact default-configuration canonical module; source receipt alongside.
module dsfd_vm_fsr (
    input  wire          ck,
    input  wire          rn,
    input  wire [27:0]   i_v,  input wire [27:0]  i_we, input wire [391:0] i_row, input wire [111:0] i_mask,
    input  wire [3583:0] i_d,  input wire [3:0]   i_rf,
    output reg  [27:0]   o_v,  output reg [27:0]  o_we, output reg [391:0] o_row, output reg [111:0] o_mask,
    output reg  [3583:0] o_d,  output reg [3:0]   o_rf
);
    reg rn_q;
    reg [27:0] v1, we1; reg [391:0] row1; reg [111:0] m1; reg [3583:0] d1;
    always @(posedge ck) begin
        rn_q <= rn;
        if (!rn_q) begin v1 <= 28'd0; o_v <= 28'd0; end else begin v1 <= i_v; o_v <= v1; end
        we1 <= i_we; row1 <= i_row; m1 <= i_mask; d1 <= i_d;
        o_we <= we1; o_row <= row1; o_mask <= m1; o_d <= d1;
        o_rf <= i_rf;
    end
endmodule
