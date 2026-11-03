module ot_hdc_v41x_faddl #(
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire [1:0]  err,
    output wire        valid_out
);
    generate
        if (LAT == 3) begin : g_fast
            ot_hdc_fp32_add_fast u (.clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b), .y(y), .err(err),
                                    .valid_out(valid_out));
        end else begin : g_lat
             
             
            /*verilator lint_off TIMESCALEMOD*/
            ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b), .y(y),
                                                .err(err), .valid_out(valid_out));
            /*verilator lint_on TIMESCALEMOD*/
        end
    endgenerate
endmodule
