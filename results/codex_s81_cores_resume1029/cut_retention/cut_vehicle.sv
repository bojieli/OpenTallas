module ot_v41_cut #(
    parameter integer W = 8,
    parameter EN = 1'b1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    if (EN) begin : g_r
        reg         v;
        reg [W-2:0] r;
        always @(posedge clk or negedge rst_n) if (!rst_n) v <= 1'b0; else v <= d[W-1];
        always @(posedge clk) r <= d[W-2:0];
        assign q = {v, r};
    end else begin : g_w
        assign q = d;
    end
endmodule
module cut_vehicle(input wire clk,rst_n,v,d, output wire [2:0] q);
wire [2:0] x[0:6];assign x[0]={v,d,1'b0};
genvar k;generate for(k=0;k<6;k=k+1)begin:g
ot_v41_cut #(.W(3),.EN(1'b1)) u(.clk(clk),.rst_n(rst_n),.d(x[k]),.q(x[k+1]));
end endgenerate
assign q=x[6];endmodule
