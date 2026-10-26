module ot_dp_rsync #(parameter integer W = 1, parameter integer S = 2) (
    input  wire         clk,
    input  wire [W-1:0] a,
    output wire [W-1:0] q
);
    genvar g;
    generate for (g = 0; g < W; g = g + 1) begin : b
        reg [S-1:0] r;
        always @(posedge clk or negedge a[g])
            if (!a[g]) r <= {S{1'b0}}; else r <= {r[S-2:0], 1'b1};
        assign q[g] = r[S-1];
    end endgenerate
endmodule
module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
    end
    assign q = r[D-1];
endmodule
module qkd_astk_fault_join(input wire ck,rst_n,input wire a,b,output reg q);
    always @(posedge ck or negedge rst_n)
        if(!rst_n) q<=1'b0;
        else q<=a|b;
endmodule
