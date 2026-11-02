module ot_hdc_v41x_bf16 (
    input  wire [31:0] x,
    output wire [15:0] y,
    output wire        ovf      
);
    wire [32:0] r = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
    assign y = r[31:16];
    assign ovf = (y[14:7] == 8'hFF);
endmodule
