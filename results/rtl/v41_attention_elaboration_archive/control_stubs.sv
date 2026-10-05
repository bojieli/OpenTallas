// CONTROL CADENCE ONLY. Arithmetic replaced by zero outputs; no numeric claim.
module ot_hdc_v41x_dly #(parameter integer W = 1, parameter integer D = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else begin : g_reg
            reg [W-1:0] r [0:D-1];
            integer i;
            always @(posedge clk) begin
                r[0] <= d;
                for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
            end
            assign q = r[D-1];
        end
    endgenerate
endmodule

// Valid delay line with reset.
module ot_hdc_v41x_vdly #(parameter integer D = 1) (
    input  wire clk,
    input  wire rst_n,
    input  wire d,
    output wire q
);
    reg [D:0] r;
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) r[D:1] <= {D{1'b0}};
        else for (i = 1; i <= D; i = i + 1) r[i] <= (i == 1) ? d : r[i-1];
    end
    assign q = r[D];
endmodule

// ---------------------------------------------------------------------------
module ot_hdc_v41x_attn_tile #(
    parameter integer H = 16,          // heads
    parameter integer TD = 64,         // products per head per beat (multiple of 8, TD/8 a power of two)
    parameter integer NBANK = 3,       // stationary-operand banks
    parameter integer BW = 2           // bank index width
) (
    input  wire              clk,
    input  wire              rst_n,
    // stationary operand load
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [BW-1:0]     ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [TD*16-1:0]  ld_w,
    // issue
    input  wire              iv,
    input  wire [BW-1:0]     ibank,
    input  wire [TD*18-1:0]  ib,
    // result
    output reg               ov,
    output reg  [H*32-1:0]   oy,
    output reg  [H-1:0]      oflt
);
    localparam integer LAT=27+3*$clog2(TD/8);
    wire valid_out;
    ot_hdc_v41x_vdly #(.D(LAT)) delay(.clk(clk),.rst_n(rst_n),.d(iv),.q(valid_out));
    always @* begin ov=valid_out; oy=0; oflt=0; end
endmodule
module ot_hdc_qadd(input clk,rst_n,v,input [31:0] a,b,output [31:0] y,output fault);
assign y=0; assign fault=0;
endmodule
