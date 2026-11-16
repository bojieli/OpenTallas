module ot_s81sl_cst1 #(parameter integer W = 1, parameter integer V = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, input wire [V-1:0] dv, output reg [W-1:0] q, output reg [V-1:0] qv
);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n) if (!rst_n) qv <= {V{1'b0}}; else qv <= dv;
endmodule

module ot_s81sl_cst #(parameter integer W = 1, parameter integer V = 1, parameter integer D = 0) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, input wire [V-1:0] dv, output wire [W-1:0] q, output wire [V-1:0] qv
);
    generate if (D <= 0) begin : g0
        assign q = d; assign qv = dv;
    end else begin : gd
        wire [W-1:0] cd [0:D]; wire [V-1:0] cv [0:D];
        assign cd[0] = d; assign cv[0] = dv;
        genvar j;
        for (j = 0; j < D; j = j + 1) begin : s
            ot_s81sl_cst1 #(.W(W), .V(V)) u (.clk(clk), .rst_n(rst_n), .d(cd[j]), .dv(cv[j]), .q(cd[j + 1]), .qv(cv[j + 1]));
        end
        assign q = cd[D]; assign qv = cv[D];
    end endgenerate
endmodule
