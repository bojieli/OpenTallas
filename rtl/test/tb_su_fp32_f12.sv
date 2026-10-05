`timescale 1ns/1ps
// hbm-fmax-su: ot_hdc_fp32_add_f12 / ot_hdc_fp32_mul_f12 (rtl/hdc/ot_hdc_fp32_f12.sv) at several CUTS against
// ot_hdc_fp32_add_fast / ot_hdc_fp32_mul_fast, cycle-aligned at each LAT, every output bit ({valid_out, err, y}).
// Stimulus: rtl/test/tb_su_fp32_f12.cpp (random encodings biased to specials, subnormals, cancellation, ties).
module tb_su_fp32_f12 (input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
                       output wire [10:0] mism);
    wire [31:0] ya, ym; wire [1:0] ea, em; wire va, vm;
    ot_hdc_fp32_add_fast u_ra (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya), .err(ea), .valid_out(va));
    ot_hdc_fp32_mul_fast u_rm (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym), .err(em), .valid_out(vm));
    reg [34:0] da [1:4];
    reg [34:0] dm [1:4];
    integer i;
    always @(posedge clk) begin
        da[1] <= {va, ea, ya}; dm[1] <= {vm, em, ym};
        for (i = 2; i <= 4; i = i + 1) begin da[i] <= da[i-1]; dm[i] <= dm[i-1]; end
    end
    // adder: f12 LAT 4 (101010), LAT 5 (101011), LAT 5 (111010), LAT 6 (111011)
    localparam [4*6-1:0] AC = {6'b111011, 6'b111010, 6'b101011, 6'b101010};
    localparam [4*8-1:0] MC = {8'b01111011, 8'b01101011, 8'b01111010, 8'b01101010};
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : ga
        localparam [5:0] C = AC[6*g +: 6];
        localparam integer L = 1 + C[0] + C[1] + C[2] + C[3] + C[4] + C[5];
        wire [31:0] y; wire [1:0] e; wire vo;
        ot_hdc_fp32_add_f12 #(.CUTS(C)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(e), .valid_out(vo));
        assign mism[g] = rst_n && ({vo, e, y} != ((L == 3) ? {va, ea, ya} : da[L - 3]));
    end
    for (g = 0; g < 4; g = g + 1) begin : gm
        localparam [7:0] C = MC[8*g +: 8];
        localparam integer L = 1 + C[0] + C[1] + C[2] + C[3] + C[4] + C[5] + C[6] + C[7];
        wire [31:0] y; wire [1:0] e; wire vo;
        ot_hdc_fp32_mul_f12 #(.CUTS(C)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(e), .valid_out(vo));
        assign mism[4 + g] = rst_n && ({vo, e, y} != ((L == 3) ? {vm, em, ym} : dm[L - 3]));
    end endgenerate
    // the lane builds' input-register units (ALAT 5 / MLAT 6)
    wire [31:0] y5i, y6i; wire [1:0] e5i, e6i; wire v5i, v6i;
    ot_hdc_fp32_add_f12_l5i u5i (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y5i), .err(e5i), .valid_out(v5i));
    ot_hdc_fp32_mul_f12_l6i u6i (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y6i), .err(e6i), .valid_out(v6i));
    assign mism[8] = rst_n && ({v5i, e5i, y5i} != da[2]);
    assign mism[9] = rst_n && ({v6i, e6i, y6i} != dm[3]);
    wire [31:0] y5x; wire [1:0] e5x; wire v5x;
    ot_hdc_fp32_add_f12_l5x u5x (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y5x), .err(e5x), .valid_out(v5x));
    assign mism[10] = rst_n && ({v5x, e5x, y5x} != da[2]);
endmodule
