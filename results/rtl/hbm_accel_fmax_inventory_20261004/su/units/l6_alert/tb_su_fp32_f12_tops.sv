`timescale 1ns/1ps
// the FIXED TOP modules (as integrations instantiate them) against the fast units delayed to the declared LAT
module tb_su_fp32_f12_tops (input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
                            output wire [3:0] mism);
    wire [31:0] ya, ym; wire [1:0] ea, em; wire va, vm;
    ot_hdc_fp32_add_fast u_ra (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya), .err(ea), .valid_out(va));
    ot_hdc_fp32_mul_fast u_rm (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym), .err(em), .valid_out(vm));
    reg [34:0] da [1:4]; reg [34:0] dm [1:4]; integer i;
    always @(posedge clk) begin da[1] <= {va, ea, ya}; dm[1] <= {vm, em, ym};
        for (i = 2; i <= 4; i = i + 1) begin da[i] <= da[i-1]; dm[i] <= dm[i-1]; end end
    wire [31:0] y0,y1,y2,y3; wire [1:0] e0,e1,e2,e3; wire v0,v1,v2,v3;
    ot_hdc_fp32_add_f12_l4  t0 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y0), .err(e0), .valid_out(v0));
    ot_hdc_fp32_add_f12_l5x t1 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y1), .err(e1), .valid_out(v1));
    ot_hdc_fp32_mul_f12_l5  t2 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y2), .err(e2), .valid_out(v2));
    ot_hdc_fp32_mul_f12_l6  t3 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y3), .err(e3), .valid_out(v3));
    assign mism = {rst_n && ({v3,e3,y3} != dm[3]), rst_n && ({v2,e2,y2} != dm[2]),
                   rst_n && ({v1,e1,y1} != da[2]), rst_n && ({v0,e0,y0} != da[1])};
endmodule
