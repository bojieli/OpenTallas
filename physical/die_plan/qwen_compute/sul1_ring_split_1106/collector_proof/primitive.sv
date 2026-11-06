module ot_dp_landing_collect #(parameter integer N=1) (
    input wire clk, rst_n,
    input wire [N-1:0] ready_i, fault_i,
    output reg ready_o, fault_o
);
    always @(posedge clk) begin
        if (!rst_n) begin ready_o <= 0; fault_o <= 0; end
        else begin ready_o <= &ready_i; fault_o <= |fault_i; end
    end
endmodule
