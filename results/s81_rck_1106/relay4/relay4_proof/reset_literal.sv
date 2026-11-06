module ot_s81_kp4_rst #(parameter integer NL = 4) (
    input  wire          clk,
    input  wire          rst_n,     // die reset copy (synchronous to clk)
    output wire [NL-1:0] rs_n       // leaf copies, 3 flops after the port
);
    reg r1, r2;
    (* keep *) reg [NL-1:0] lf;
    always @(posedge clk) begin r1 <= rst_n; r2 <= r1; lf <= {NL{r2}}; end
    assign rs_n = lf;
endmodule
