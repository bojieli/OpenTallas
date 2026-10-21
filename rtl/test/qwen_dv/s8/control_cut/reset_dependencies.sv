`timescale 1ns/1ps
module qfd_dv_s6_rst2x4 (input wire ck, input wire rst_n, output wire [3:0] rst);
    reg rs1;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    qfd_dv_s6_rk u_k0 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[0]));
    qfd_dv_s6_rk u_k1 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[1]));
    qfd_dv_s6_rk u_k2 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[2]));
    qfd_dv_s6_rk u_k3 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[3]));
endmodule
module qfd_dv_s6_rk (input wire ck, input wire rst_n, input wire d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
module qfd_dv_s5_rst2 (input wire ck, input wire rst_n, output wire rst);
    reg rs1, rs2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    assign rst = rs2;
endmodule
